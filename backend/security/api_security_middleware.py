"""
API Security Middleware for The HIVE Translation Services

Comprehensive security middleware providing rate limiting, input validation,
security headers, and threat detection for all API endpoints.
"""

import time
import json
import hashlib
import logging
import ipaddress
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import redis
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import user_agents
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Security threat levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityConfig:
    """Security middleware configuration"""
    # Rate limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_requests_per_hour: int = 1000
    rate_limit_burst_allowance: int = 10
    
    # Input validation
    max_request_size_mb: int = 10
    max_header_size: int = 8192
    max_url_length: int = 2048
    max_query_params: int = 50
    
    # Security headers
    enable_security_headers: bool = True
    enable_cors_protection: bool = True
    allowed_origins: List[str] = field(default_factory=list)
    
    # Content security
    enable_content_type_validation: bool = True
    allowed_content_types: List[str] = field(default_factory=lambda: [
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "audio/wav",
        "audio/mp3",
        "audio/webm"
    ])
    
    # Threat detection
    enable_threat_detection: bool = True
    max_failed_requests_per_ip: int = 10
    threat_detection_window_minutes: int = 15
    
    # IP filtering
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None
    
    # Request filtering
    blocked_user_agents: List[str] = field(default_factory=lambda: [
        r".*bot.*",
        r".*crawler.*",
        r".*spider.*",
        r".*scanner.*",
        r".*sqlmap.*",
        r".*nikto.*"
    ])
    
    # Path filtering
    blocked_paths: List[str] = field(default_factory=lambda: [
        r"\.env",
        r"\.git",
        r"admin",
        r"phpmyadmin",
        r"wp-admin",
        r"\.php$",
        r"\.asp$",
        r"\.jsp$"
    ])

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: str
    threat_level: ThreatLevel
    client_ip: str
    user_agent: str
    request_path: str
    timestamp: datetime
    details: Dict[str, Any]
    request_id: str

class RateLimiter:
    """Redis-based rate limiter with sliding window"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        burst_allowance: int = 0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed within rate limits
        
        Args:
            identifier: Unique identifier (IP, user, etc.)
            limit: Number of requests allowed in window
            window_seconds: Time window in seconds
            burst_allowance: Additional requests allowed for bursts
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        now = time.time()
        pipeline = self.redis.pipeline()
        
        # Sliding window with burst allowance
        key = f"rate_limit:{identifier}"
        
        try:
            # Remove expired entries
            pipeline.zremrangebyscore(key, 0, now - window_seconds)
            
            # Count current requests
            pipeline.zcard(key)
            
            # Add current request
            pipeline.zadd(key, {str(now): now})
            
            # Set expiration
            pipeline.expire(key, window_seconds)
            
            results = pipeline.execute()
            current_count = results[1]
            
            # Calculate if allowed
            effective_limit = limit + burst_allowance
            allowed = current_count < effective_limit
            
            rate_limit_info = {
                "limit": limit,
                "remaining": max(0, effective_limit - current_count - 1),
                "reset_time": int(now + window_seconds),
                "burst_allowance": burst_allowance,
                "current_count": current_count
            }
            
            if not allowed:
                # Remove the request we just added since it's not allowed
                pipeline = self.redis.pipeline()
                pipeline.zrem(key, str(now))
                pipeline.execute()
            
            return allowed, rate_limit_info
            
        except Exception as e:
            logger.error(f"Rate limiting error for {identifier}: {e}")
            # Fail open - allow request if Redis is down
            return True, {"error": "rate_limiter_unavailable"}

class ThreatDetector:
    """Advanced threat detection system"""
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"union.*select",
        r"select.*from.*information_schema",
        r"insert.*into",
        r"delete.*from",
        r"update.*set",
        r"drop.*table",
        r"exec\s*\(",
        r"script.*alert",
        r"<script",
        r"javascript:",
        r"onload\s*=",
        r"onerror\s*=",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onfocus\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%252e%252e%252f",
        r"..%c0%af",
        r"..%c1%9c",
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r";\s*(cat|ls|pwd|id|whoami)",
        r"\|\s*(cat|ls|pwd|id|whoami)",
        r"&&\s*(cat|ls|pwd|id|whoami)",
        r"`.*`",
        r"\$\(.*\)",
        r"nc\s+-",
        r"curl\s+",
        r"wget\s+",
    ]
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        
        # Compile regex patterns for performance
        self.sql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.XSS_PATTERNS]
        self.path_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.PATH_TRAVERSAL_PATTERNS]
        self.cmd_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.COMMAND_INJECTION_PATTERNS]
    
    def analyze_request(self, request: Request) -> List[SecurityEvent]:
        """Analyze request for security threats"""
        events = []
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        request_id = request.headers.get("x-request-id", "unknown")
        
        # Check URL for threats
        url_threats = self._check_url_threats(request.url.path, request.url.query)
        for threat_type, details in url_threats:
            events.append(SecurityEvent(
                event_type=threat_type,
                threat_level=ThreatLevel.HIGH,
                client_ip=client_ip,
                user_agent=user_agent,
                request_path=request.url.path,
                timestamp=datetime.utcnow(),
                details=details,
                request_id=request_id
            ))
        
        # Check headers for threats
        header_threats = self._check_header_threats(request.headers)
        for threat_type, details in header_threats:
            events.append(SecurityEvent(
                event_type=threat_type,
                threat_level=ThreatLevel.MEDIUM,
                client_ip=client_ip,
                user_agent=user_agent,
                request_path=request.url.path,
                timestamp=datetime.utcnow(),
                details=details,
                request_id=request_id
            ))
        
        return events
    
    def _check_url_threats(self, path: str, query: Optional[str]) -> List[Tuple[str, Dict[str, Any]]]:
        """Check URL path and query for threats"""
        threats = []
        full_url = f"{path}?{query}" if query else path
        decoded_url = unquote(full_url)
        
        # SQL injection check
        for pattern in self.sql_patterns:
            if pattern.search(decoded_url):
                threats.append(("sql_injection_attempt", {
                    "pattern": pattern.pattern,
                    "url": decoded_url[:200]  # Limit logged URL length
                }))
        
        # XSS check
        for pattern in self.xss_patterns:
            if pattern.search(decoded_url):
                threats.append(("xss_attempt", {
                    "pattern": pattern.pattern,
                    "url": decoded_url[:200]
                }))
        
        # Path traversal check
        for pattern in self.path_patterns:
            if pattern.search(decoded_url):
                threats.append(("path_traversal_attempt", {
                    "pattern": pattern.pattern,
                    "url": decoded_url[:200]
                }))
        
        # Command injection check
        for pattern in self.cmd_patterns:
            if pattern.search(decoded_url):
                threats.append(("command_injection_attempt", {
                    "pattern": pattern.pattern,
                    "url": decoded_url[:200]
                }))
        
        return threats
    
    def _check_header_threats(self, headers) -> List[Tuple[str, Dict[str, Any]]]:
        """Check request headers for threats"""
        threats = []
        
        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "x-originating-ip",
            "x-cluster-client-ip"
        ]
        
        for header_name, header_value in headers.items():
            if header_name.lower() in suspicious_headers:
                # Check for header injection
                if '\n' in header_value or '\r' in header_value:
                    threats.append(("header_injection_attempt", {
                        "header": header_name,
                        "value": header_value[:100]
                    }))
        
        return threats
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support"""
        # Check various headers in order of preference
        headers_to_check = [
            "cf-connecting-ip",      # Cloudflare
            "x-forwarded-for",       # Standard proxy header
            "x-real-ip",             # Nginx
            "x-cluster-client-ip",   # Cluster proxy
            "forwarded",             # RFC 7239
        ]
        
        for header in headers_to_check:
            if header in request.headers:
                # Take the first IP if multiple
                ip = request.headers[header].split(',')[0].strip()
                try:
                    ipaddress.ip_address(ip)
                    return ip
                except ValueError:
                    continue
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

class SecurityHeadersMiddleware:
    """Middleware to add security headers"""
    
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        ),
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Embedder-Policy": "require-corp",
        "Cross-Origin-Resource-Policy": "same-origin"
    }
    
    def __init__(self, config: SecurityConfig):
        self.config = config
    
    def add_security_headers(self, response: Response) -> Response:
        """Add security headers to response"""
        if not self.config.enable_security_headers:
            return response
        
        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "media-src 'self' blob:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Add Strict Transport Security (if HTTPS)
        if hasattr(response, 'url') and str(response.url).startswith('https'):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response

class APISecurityMiddleware(BaseHTTPMiddleware):
    """Main API security middleware"""
    
    def __init__(self, app, config: SecurityConfig, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.config = config
        self.redis = redis_client
        self.rate_limiter = RateLimiter(redis_client) if redis_client else None
        self.threat_detector = ThreatDetector(redis_client)
        self.security_headers = SecurityHeadersMiddleware(config)
        
        # Compile blocked patterns
        self.blocked_ua_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in config.blocked_user_agents
        ]
        self.blocked_path_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in config.blocked_paths
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method"""
        start_time = time.time()
        
        try:
            # Generate request ID
            request_id = self._generate_request_id()
            request.state.request_id = request_id
            
            # Pre-request security checks
            security_check = await self._pre_request_security_check(request)
            if security_check is not None:
                return security_check
            
            # Process request
            response = await call_next(request)
            
            # Post-request processing
            response = self._post_request_processing(request, response, start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"}
            )
    
    async def _pre_request_security_check(self, request: Request) -> Optional[Response]:
        """Perform pre-request security validations"""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # IP filtering
        if not self._check_ip_allowed(client_ip):
            self._log_security_event("ip_blocked", ThreatLevel.HIGH, request, {
                "reason": "IP address not allowed",
                "ip": client_ip
            })
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied"}
            )
        
        # User agent filtering
        if not self._check_user_agent_allowed(user_agent):
            self._log_security_event("user_agent_blocked", ThreatLevel.MEDIUM, request, {
                "user_agent": user_agent[:100]
            })
            return JSONResponse(
                status_code=403,
                content={"error": "User agent not allowed"}
            )
        
        # Path filtering
        if not self._check_path_allowed(request.url.path):
            self._log_security_event("path_blocked", ThreatLevel.HIGH, request, {
                "path": request.url.path
            })
            return JSONResponse(
                status_code=404,
                content={"error": "Not found"}
            )
        
        # Request size validation
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.config.max_request_size_mb:
                    self._log_security_event("request_too_large", ThreatLevel.MEDIUM, request, {
                        "size_mb": size_mb,
                        "max_allowed": self.config.max_request_size_mb
                    })
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request entity too large"}
                    )
            except ValueError:
                pass
        
        # Rate limiting
        if self.rate_limiter:
            minute_allowed, minute_info = self.rate_limiter.is_allowed(
                f"ip:{client_ip}:minute",
                self.config.rate_limit_requests_per_minute,
                60,
                self.config.rate_limit_burst_allowance
            )
            
            hour_allowed, hour_info = self.rate_limiter.is_allowed(
                f"ip:{client_ip}:hour",
                self.config.rate_limit_requests_per_hour,
                3600
            )
            
            if not minute_allowed or not hour_allowed:
                self._log_security_event("rate_limit_exceeded", ThreatLevel.MEDIUM, request, {
                    "minute_limit": minute_info,
                    "hour_limit": hour_info
                })
                
                response = JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded"}
                )
                
                # Add rate limit headers
                info = minute_info if not minute_allowed else hour_info
                response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
                response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
                response.headers["X-RateLimit-Reset"] = str(info.get("reset_time", 0))
                
                return response
        
        # Threat detection
        if self.config.enable_threat_detection:
            threats = self.threat_detector.analyze_request(request)
            for threat in threats:
                if threat.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                    self._log_security_event(threat.event_type, threat.threat_level, request, threat.details)
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Malicious request detected"}
                    )
        
        return None  # All checks passed
    
    def _post_request_processing(self, request: Request, response: Response, start_time: float) -> Response:
        """Post-request processing"""
        # Add security headers
        response = self.security_headers.add_security_headers(response)
        
        # Add timing header
        processing_time = time.time() - start_time
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
        
        # Add request ID header
        if hasattr(request.state, 'request_id'):
            response.headers["X-Request-ID"] = request.state.request_id
        
        return response
    
    def _check_ip_allowed(self, client_ip: str) -> bool:
        """Check if IP address is allowed"""
        try:
            ip = ipaddress.ip_address(client_ip)
            
            # Check blacklist first
            if self.config.ip_blacklist:
                for blocked_range in self.config.ip_blacklist:
                    if ip in ipaddress.ip_network(blocked_range, strict=False):
                        return False
            
            # Check whitelist if configured
            if self.config.ip_whitelist:
                for allowed_range in self.config.ip_whitelist:
                    if ip in ipaddress.ip_network(allowed_range, strict=False):
                        return True
                return False  # Not in whitelist
            
            return True  # No restrictions
            
        except ValueError:
            logger.warning(f"Invalid IP address: {client_ip}")
            return False
    
    def _check_user_agent_allowed(self, user_agent: str) -> bool:
        """Check if user agent is allowed"""
        if not user_agent:
            return False
        
        for pattern in self.blocked_ua_patterns:
            if pattern.search(user_agent):
                return False
        
        return True
    
    def _check_path_allowed(self, path: str) -> bool:
        """Check if request path is allowed"""
        for pattern in self.blocked_path_patterns:
            if pattern.search(path):
                return False
        
        return True
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        return self.threat_detector._get_client_ip(request)
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        return hashlib.sha256(f"{time.time()}{id(self)}".encode()).hexdigest()[:16]
    
    def _log_security_event(
        self,
        event_type: str,
        threat_level: ThreatLevel,
        request: Request,
        details: Dict[str, Any]
    ):
        """Log security event"""
        event_data = {
            "event_type": event_type,
            "threat_level": threat_level.value,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "request_path": request.url.path,
            "request_method": request.method,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, 'request_id', 'unknown'),
            "details": details
        }
        
        logger.warning(f"Security event: {event_type}", extra={"security_event": event_data})

# Factory function for easy integration
def create_security_middleware(
    app,
    redis_url: Optional[str] = None,
    config: Optional[SecurityConfig] = None
) -> APISecurityMiddleware:
    """Create API security middleware with default configuration"""
    if config is None:
        config = SecurityConfig()
    
    redis_client = None
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url, decode_responses=True)
            redis_client.ping()
            logger.info("Connected to Redis for security middleware")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for security: {e}")
    
    return APISecurityMiddleware(app, config, redis_client)

# Example usage for FastAPI integration
def setup_api_security(app, redis_url: Optional[str] = None) -> None:
    """
    Setup API security for a FastAPI application
    
    Args:
        app: FastAPI application instance
        redis_url: Redis connection URL for rate limiting
    """
    config = SecurityConfig(
        # Customize configuration as needed
        rate_limit_requests_per_minute=100,
        rate_limit_requests_per_hour=2000,
        enable_threat_detection=True,
        enable_security_headers=True
    )
    
    security_middleware = create_security_middleware(app, redis_url, config)
    app.add_middleware(APISecurityMiddleware, config=config, redis_client=security_middleware.redis)