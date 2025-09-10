"""
Security Middleware for The HIVE Translation Services

Comprehensive security layer providing:
- Request rate limiting and DDoS protection
- Input validation and sanitization
- Security headers and CORS management
- Audit logging and threat detection
- IP-based access control
- Request/response encryption validation
"""

import time
import json
import hashlib
import ipaddress
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import logging
import asyncio
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import redis
from pydantic import BaseModel, ValidationError
import jwt

logger = logging.getLogger(__name__)

# Security configuration
@dataclass
class SecurityConfig:
    """Centralized security configuration"""
    # Rate limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst: int = 20
    rate_limit_window_seconds: int = 60
    
    # IP filtering
    allowed_ips: Optional[List[str]] = None
    blocked_ips: Optional[List[str]] = None
    allow_private_ips: bool = True
    
    # Input validation
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_json_depth: int = 10
    max_array_length: int = 1000
    
    # Security headers
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    enable_csp: bool = True
    csp_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    # Audit logging
    log_all_requests: bool = False
    log_failed_requests: bool = True
    log_suspicious_activity: bool = True
    
    # Redis for distributed rate limiting
    redis_url: str = "redis://localhost:6379"
    redis_key_prefix: str = "hive:security:"

# Threat detection patterns
class ThreatPatterns:
    """Security threat detection patterns"""
    
    # SQL Injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"('.*OR.*'.*')",
        r"(;.*--)",
        r"(\bEXEC\b.*\()",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"(<script[^>]*>.*</script>)",
        r"(<iframe[^>]*>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<svg[^>]*onload)",
        r"(<img[^>]*onerror)",
        r"(eval\s*\()",
        r"(alert\s*\()",
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"(;\s*\w+)",
        r"(\|\s*\w+)",
        r"(`\w+`)",
        r"(\$\(\w+\))",
        r"(&\s*\w+)",
        r"(\|\|\s*\w+)",
        r"(&&\s*\w+)",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\./)",
        r"(\.\.\\)",
        r"(%2e%2e%2f)",
        r"(%2e%2e\\)",
        r"(\.\.%2f)",
        r"(\.\.%5c)",
    ]

class SecurityAuditEvent:
    """Security audit event model"""
    def __init__(
        self,
        event_type: str,
        severity: str,
        client_ip: str,
        user_agent: str,
        endpoint: str,
        details: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        self.event_type = event_type
        self.severity = severity  # low, medium, high, critical
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.endpoint = endpoint
        self.details = details
        self.timestamp = timestamp or datetime.utcnow()
        self.event_id = hashlib.sha256(
            f"{self.timestamp.isoformat()}{client_ip}{endpoint}{event_type}".encode()
        ).hexdigest()[:16]

class RateLimiter:
    """Advanced rate limiter with burst support and distributed storage"""
    
    def __init__(self, config: SecurityConfig, redis_client: Optional[redis.Redis] = None):
        self.config = config
        self.redis = redis_client
        self.local_counters: Dict[str, deque] = defaultdict(deque)
        self.local_lock = asyncio.Lock()
    
    async def is_allowed(self, identifier: str, endpoint: str = "global") -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed under rate limits
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        key = f"{self.config.redis_key_prefix}rate_limit:{identifier}:{endpoint}"
        now = time.time()
        window_start = now - self.config.rate_limit_window_seconds
        
        if self.redis:
            return await self._check_distributed_rate_limit(key, now, window_start)
        else:
            return await self._check_local_rate_limit(identifier, now, window_start)
    
    async def _check_distributed_rate_limit(self, key: str, now: float, window_start: float) -> Tuple[bool, Dict[str, int]]:
        """Check rate limit using Redis for distributed tracking"""
        try:
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, self.config.rate_limit_window_seconds + 10)
            
            results = pipe.execute()
            current_count = results[1]
            
            # Check limits
            allowed = current_count <= self.config.rate_limit_requests_per_minute
            
            return allowed, {
                "requests": current_count,
                "limit": self.config.rate_limit_requests_per_minute,
                "window": self.config.rate_limit_window_seconds,
                "reset_time": int(now + self.config.rate_limit_window_seconds)
            }
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fall back to local rate limiting
            return await self._check_local_rate_limit(key, now, window_start)
    
    async def _check_local_rate_limit(self, identifier: str, now: float, window_start: float) -> Tuple[bool, Dict[str, int]]:
        """Local in-memory rate limiting fallback"""
        async with self.local_lock:
            requests = self.local_counters[identifier]
            
            # Remove old requests
            while requests and requests[0] < window_start:
                requests.popleft()
            
            # Check limit
            allowed = len(requests) < self.config.rate_limit_requests_per_minute
            
            if allowed:
                requests.append(now)
            
            return allowed, {
                "requests": len(requests),
                "limit": self.config.rate_limit_requests_per_minute,
                "window": self.config.rate_limit_window_seconds,
                "reset_time": int(now + self.config.rate_limit_window_seconds)
            }

class InputValidator:
    """Advanced input validation and sanitization"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.threat_patterns = ThreatPatterns()
    
    def validate_request_size(self, content_length: Optional[int]) -> bool:
        """Validate request size limits"""
        if content_length is None:
            return True
        return content_length <= self.config.max_request_size
    
    def scan_for_threats(self, text: str) -> List[Dict[str, Any]]:
        """Scan text for security threats"""
        threats = []
        
        # Check for SQL injection
        for pattern in self.threat_patterns.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append({
                    "type": "sql_injection",
                    "pattern": pattern,
                    "severity": "high"
                })
        
        # Check for XSS
        for pattern in self.threat_patterns.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append({
                    "type": "xss",
                    "pattern": pattern,
                    "severity": "high"
                })
        
        # Check for command injection
        for pattern in self.threat_patterns.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append({
                    "type": "command_injection",
                    "pattern": pattern,
                    "severity": "critical"
                })
        
        # Check for path traversal
        for pattern in self.threat_patterns.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append({
                    "type": "path_traversal",
                    "pattern": pattern,
                    "severity": "medium"
                })
        
        return threats
    
    def validate_json_depth(self, obj: Any, depth: int = 0) -> bool:
        """Validate JSON object depth to prevent DoS"""
        if depth > self.config.max_json_depth:
            return False
        
        if isinstance(obj, dict):
            return all(self.validate_json_depth(v, depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if len(obj) > self.config.max_array_length:
                return False
            return all(self.validate_json_depth(item, depth + 1) for item in obj)
        
        return True

class IPFilter:
    """IP-based access control"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.allowed_networks = self._parse_networks(config.allowed_ips or [])
        self.blocked_networks = self._parse_networks(config.blocked_ips or [])
    
    def _parse_networks(self, ip_list: List[str]) -> List[ipaddress.IPv4Network]:
        """Parse IP addresses and CIDR ranges"""
        networks = []
        for ip_str in ip_list:
            try:
                if '/' not in ip_str:
                    ip_str += '/32'  # Single IP
                networks.append(ipaddress.IPv4Network(ip_str, strict=False))
            except Exception as e:
                logger.warning(f"Invalid IP address/range: {ip_str} - {e}")
        return networks
    
    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        try:
            client_ip = ipaddress.IPv4Address(ip)
            
            # Check blocked list first
            for network in self.blocked_networks:
                if client_ip in network:
                    return False
            
            # If no allowed list is specified, allow by default (except blocked)
            if not self.allowed_networks:
                # Check if private IP is allowed
                if client_ip.is_private and not self.config.allow_private_ips:
                    return False
                return True
            
            # Check allowed list
            for network in self.allowed_networks:
                if client_ip in network:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"IP validation error for {ip}: {e}")
            return False

class SecurityAuditor:
    """Security event auditing and logging"""
    
    def __init__(self, config: SecurityConfig, redis_client: Optional[redis.Redis] = None):
        self.config = config
        self.redis = redis_client
    
    async def log_event(self, event: SecurityAuditEvent):
        """Log security event"""
        event_data = asdict(event)
        event_data['timestamp'] = event.timestamp.isoformat()
        
        # Log to application logger
        log_level = self._get_log_level(event.severity)
        logger.log(log_level, f"Security Event: {json.dumps(event_data)}")
        
        # Store in Redis for analysis
        if self.redis:
            try:
                key = f"{self.config.redis_key_prefix}audit:{event.event_type}"
                await self.redis.lpush(key, json.dumps(event_data))
                await self.redis.expire(key, 86400 * 7)  # 7 days retention
            except Exception as e:
                logger.error(f"Failed to store audit event: {e}")
    
    def _get_log_level(self, severity: str) -> int:
        """Convert severity to log level"""
        severity_map = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }
        return severity_map.get(severity, logging.INFO)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware for FastAPI applications"""
    
    def __init__(
        self,
        app,
        config: SecurityConfig,
        redis_client: Optional[redis.Redis] = None,
        exempt_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.config = config
        self.rate_limiter = RateLimiter(config, redis_client)
        self.input_validator = InputValidator(config)
        self.ip_filter = IPFilter(config)
        self.auditor = SecurityAuditor(config, redis_client)
        self.exempt_paths = set(exempt_paths or ['/health', '/metrics'])
    
    async def dispatch(self, request: Request, call_next):
        """Main security middleware logic"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        try:
            # Skip security checks for exempt paths
            if request.url.path in self.exempt_paths:
                return await call_next(request)
            
            # IP filtering
            if not self.ip_filter.is_allowed(client_ip):
                await self._log_security_event(
                    "ip_blocked",
                    "medium",
                    client_ip,
                    user_agent,
                    request.url.path,
                    {"reason": "IP not in allowed list"}
                )
                return JSONResponse(
                    status_code=403,
                    content={"error": "Access denied"}
                )
            
            # Rate limiting
            allowed, rate_info = await self.rate_limiter.is_allowed(
                client_ip,
                request.url.path
            )
            
            if not allowed:
                await self._log_security_event(
                    "rate_limit_exceeded",
                    "medium",
                    client_ip,
                    user_agent,
                    request.url.path,
                    rate_info
                )
                
                response = JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded"}
                )
                self._add_rate_limit_headers(response, rate_info)
                return response
            
            # Request size validation
            content_length = request.headers.get('Content-Length')
            if content_length and not self.input_validator.validate_request_size(int(content_length)):
                await self._log_security_event(
                    "request_too_large",
                    "medium",
                    client_ip,
                    user_agent,
                    request.url.path,
                    {"content_length": content_length}
                )
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request too large"}
                )
            
            # Input validation for JSON requests
            if request.headers.get('Content-Type') == 'application/json':
                try:
                    body = await request.body()
                    if body:
                        # Scan for threats
                        body_text = body.decode('utf-8')
                        threats = self.input_validator.scan_for_threats(body_text)
                        
                        if threats:
                            await self._log_security_event(
                                "malicious_input_detected",
                                "high",
                                client_ip,
                                user_agent,
                                request.url.path,
                                {"threats": threats}
                            )
                            return JSONResponse(
                                status_code=400,
                                content={"error": "Malicious input detected"}
                            )
                        
                        # Validate JSON structure
                        try:
                            json_data = json.loads(body_text)
                            if not self.input_validator.validate_json_depth(json_data):
                                await self._log_security_event(
                                    "json_depth_exceeded",
                                    "medium",
                                    client_ip,
                                    user_agent,
                                    request.url.path,
                                    {"max_depth": self.config.max_json_depth}
                                )
                                return JSONResponse(
                                    status_code=400,
                                    content={"error": "JSON structure too deep"}
                                )
                        except json.JSONDecodeError:
                            # Let the application handle JSON parsing errors
                            pass
                        
                        # Recreate request with validated body
                        request._body = body
                
                except Exception as e:
                    logger.error(f"Error validating request: {e}")
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            self._add_rate_limit_headers(response, rate_info)
            
            # Log successful request if configured
            if self.config.log_all_requests:
                await self._log_security_event(
                    "request_processed",
                    "low",
                    client_ip,
                    user_agent,
                    request.url.path,
                    {
                        "status_code": response.status_code,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                )
            
            return response
            
        except Exception as e:
            # Log security middleware errors
            await self._log_security_event(
                "middleware_error",
                "high",
                client_ip,
                user_agent,
                request.url.path,
                {"error": str(e)}
            )
            
            # Return generic error
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP considering proxies"""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        # HSTS
        if self.config.enable_hsts:
            response.headers['Strict-Transport-Security'] = f'max-age={self.config.hsts_max_age}; includeSubDomains'
        
        # CSP
        if self.config.enable_csp:
            response.headers['Content-Security-Policy'] = self.config.csp_policy
        
        # Other security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    def _add_rate_limit_headers(self, response: Response, rate_info: Dict[str, int]):
        """Add rate limiting headers"""
        response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(max(0, rate_info['limit'] - rate_info['requests']))
        response.headers['X-RateLimit-Reset'] = str(rate_info['reset_time'])
    
    async def _log_security_event(
        self,
        event_type: str,
        severity: str,
        client_ip: str,
        user_agent: str,
        endpoint: str,
        details: Dict[str, Any]
    ):
        """Log security event"""
        event = SecurityAuditEvent(
            event_type=event_type,
            severity=severity,
            client_ip=client_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            details=details
        )
        await self.auditor.log_event(event)

# Utility functions for easy integration
def create_security_middleware(
    app,
    redis_url: str = "redis://localhost:6379",
    **config_kwargs
) -> SecurityMiddleware:
    """Factory function to create security middleware with Redis"""
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Using local storage.")
        redis_client = None
    
    config = SecurityConfig(**config_kwargs)
    return SecurityMiddleware(app, config, redis_client)

def add_security_to_app(
    app,
    config: Optional[SecurityConfig] = None,
    redis_url: str = "redis://localhost:6379"
):
    """Add security middleware to FastAPI app"""
    if config is None:
        config = SecurityConfig()
    
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
    except Exception:
        redis_client = None
    
    middleware = SecurityMiddleware(app, config, redis_client)
    app.add_middleware(type(middleware), dispatch=middleware.dispatch)
    
    return middleware