"""
API Security Enhancements for The HIVE Translation Services

Comprehensive API security layer including request validation, response filtering,
CORS management, and service-specific security configurations.
"""

import os
import re
import json
import time
import logging
from typing import Dict, List, Optional, Any, Set, Pattern
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request, Response, HTTPException, Depends, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, validator
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib
import hmac
import base64

from .security_middleware import SecurityMiddleware, SecurityConfig
from .security_monitor import SecurityMonitor, SecurityEvent, EventType, AlertSeverity, create_security_event

logger = logging.getLogger(__name__)

@dataclass
class APISecurityConfig:
    """API-specific security configuration"""
    # Request validation
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_json_depth: int = 10
    max_array_length: int = 1000
    max_string_length: int = 10000
    
    # Response filtering
    filter_sensitive_headers: bool = True
    hide_server_info: bool = True
    mask_error_details: bool = True
    
    # CORS configuration
    allowed_origins: List[str] = None
    allowed_methods: List[str] = None
    allowed_headers: List[str] = None
    expose_headers: List[str] = None
    allow_credentials: bool = True
    max_age: int = 86400
    
    # API versioning
    api_version: str = "v1"
    version_header: str = "X-API-Version"
    
    # Request signing
    require_signed_requests: bool = False
    signature_header: str = "X-Request-Signature"
    signature_algorithm: str = "hmac-sha256"
    
    # Content security
    allowed_content_types: Set[str] = None
    require_content_type: bool = True

class RequestValidator:
    """Advanced request validation and sanitization"""
    
    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        # SQL injection patterns
        re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b', re.IGNORECASE),
        re.compile(r'[\'";]\s*;\s*--', re.IGNORECASE),
        re.compile(r'\b(OR|AND)\s+[\'"]?\d+[\'"]?\s*=\s*[\'"]?\d+[\'"]?', re.IGNORECASE),
        
        # XSS patterns
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe[^>]*>', re.IGNORECASE),
        
        # Command injection patterns
        re.compile(r'[;&|]\s*\w+', re.IGNORECASE),
        re.compile(r'`[^`]*`', re.IGNORECASE),
        re.compile(r'\$\([^)]*\)', re.IGNORECASE),
        
        # Path traversal patterns
        re.compile(r'\.\.[\\/]', re.IGNORECASE),
        re.compile(r'[\\/]etc[\\/]', re.IGNORECASE),
        re.compile(r'[\\/]proc[\\/]', re.IGNORECASE),
    ]
    
    # Allowed file extensions for uploads
    ALLOWED_FILE_EXTENSIONS = {
        '.txt', '.json', '.csv', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.wav', '.mp3'
    }
    
    def __init__(self, config: APISecurityConfig):
        self.config = config
    
    def validate_request_size(self, content_length: Optional[int]) -> bool:
        """Validate request size"""
        if content_length is None:
            return True
        return content_length <= self.config.max_request_size
    
    def validate_content_type(self, content_type: Optional[str]) -> bool:
        """Validate request content type"""
        if not self.config.require_content_type:
            return True
        
        if not content_type:
            return False
        
        if self.config.allowed_content_types:
            # Extract media type (ignore charset etc.)
            media_type = content_type.split(';')[0].strip().lower()
            return media_type in self.config.allowed_content_types
        
        return True
    
    def scan_for_threats(self, text: str) -> List[str]:
        """Scan text for security threats"""
        threats = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(text):
                threats.append(f"dangerous_pattern_{pattern.pattern[:20]}...")
        
        return threats
    
    def validate_json_structure(self, obj: Any, depth: int = 0) -> List[str]:
        """Validate JSON object structure"""
        issues = []
        
        if depth > self.config.max_json_depth:
            issues.append("json_depth_exceeded")
            return issues
        
        if isinstance(obj, dict):
            if len(obj) > 100:  # Limit number of keys
                issues.append("too_many_object_keys")
            
            for value in obj.values():
                issues.extend(self.validate_json_structure(value, depth + 1))
        
        elif isinstance(obj, list):
            if len(obj) > self.config.max_array_length:
                issues.append("array_too_long")
            
            for item in obj[:100]:  # Limit validation to first 100 items
                issues.extend(self.validate_json_structure(item, depth + 1))
        
        elif isinstance(obj, str):
            if len(obj) > self.config.max_string_length:
                issues.append("string_too_long")
            
            # Check for dangerous patterns in strings
            threats = self.scan_for_threats(obj)
            issues.extend(threats)
        
        return issues
    
    def validate_filename(self, filename: str) -> bool:
        """Validate uploaded filename"""
        if not filename:
            return False
        
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check file extension
        file_path = Path(filename)
        if file_path.suffix.lower() not in self.ALLOWED_FILE_EXTENSIONS:
            return False
        
        # Check for dangerous characters
        dangerous_chars = set('<>:"|?*')
        if any(char in filename for char in dangerous_chars):
            return False
        
        return True

class ResponseFilter:
    """Filter and sanitize API responses"""
    
    SENSITIVE_HEADERS = {
        'server', 'x-powered-by', 'x-aspnet-version', 'x-framework-version',
        'x-runtime', 'x-version', 'x-generator', 'x-debug'
    }
    
    def __init__(self, config: APISecurityConfig):
        self.config = config
    
    def filter_response_headers(self, response: Response):
        """Remove sensitive headers from response"""
        if not self.config.filter_sensitive_headers:
            return
        
        headers_to_remove = []
        for header in response.headers:
            if header.lower() in self.SENSITIVE_HEADERS:
                headers_to_remove.append(header)
        
        for header in headers_to_remove:
            del response.headers[header]
        
        # Add security headers
        if self.config.hide_server_info:
            response.headers["Server"] = "HIVE-API"
        
        # Add API version header
        response.headers[self.config.version_header] = self.config.api_version
    
    def sanitize_error_response(self, error_detail: str) -> str:
        """Sanitize error messages to prevent information disclosure"""
        if not self.config.mask_error_details:
            return error_detail
        
        # Common patterns to mask
        sensitive_patterns = [
            (r'File "([^"]+)"', 'File "[REDACTED]"'),
            (r'line \d+', 'line [REDACTED]'),
            (r'Traceback \(most recent call last\):.*', 'Internal server error'),
            (r'Database.*connection.*failed', 'Database error'),
            (r'Authentication.*failed.*user.*', 'Authentication failed'),
            (r'No such file.*directory.*', 'Resource not found'),
        ]
        
        sanitized = error_detail
        for pattern, replacement in sensitive_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        return sanitized

class RequestSigner:
    """Handle request signing and verification"""
    
    def __init__(self, secret_key: str, algorithm: str = "hmac-sha256"):
        self.secret_key = secret_key.encode()
        self.algorithm = algorithm
    
    def sign_request(self, method: str, path: str, body: str, timestamp: str) -> str:
        """Create request signature"""
        # Create canonical string
        canonical_string = f"{method.upper()}\n{path}\n{body}\n{timestamp}"
        
        # Create signature
        if self.algorithm == "hmac-sha256":
            signature = hmac.new(
                self.secret_key,
                canonical_string.encode(),
                hashlib.sha256
            ).hexdigest()
        else:
            raise ValueError(f"Unsupported signature algorithm: {self.algorithm}")
        
        return f"{self.algorithm}={signature}"
    
    def verify_signature(
        self,
        signature: str,
        method: str,
        path: str,
        body: str,
        timestamp: str,
        max_age_seconds: int = 300
    ) -> bool:
        """Verify request signature"""
        try:
            # Check timestamp age
            request_time = float(timestamp)
            current_time = time.time()
            
            if abs(current_time - request_time) > max_age_seconds:
                return False
            
            # Verify signature
            expected_signature = self.sign_request(method, path, body, timestamp)
            
            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(signature, expected_signature)
            
        except (ValueError, TypeError):
            return False

class APISecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive API security middleware"""
    
    def __init__(
        self,
        app,
        config: APISecurityConfig,
        security_monitor: Optional[SecurityMonitor] = None,
        request_signer: Optional[RequestSigner] = None
    ):
        super().__init__(app)
        self.config = config
        self.validator = RequestValidator(config)
        self.response_filter = ResponseFilter(config)
        self.security_monitor = security_monitor
        self.request_signer = request_signer
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware logic"""
        start_time = time.time()
        
        try:
            # Validate request size
            content_length = request.headers.get("content-length")
            if content_length and not self.validator.validate_request_size(int(content_length)):
                if self.security_monitor:
                    event = create_security_event(
                        EventType.MALICIOUS_INPUT,
                        AlertSeverity.MEDIUM,
                        request,
                        "api",
                        {"reason": "request_too_large", "size": content_length}
                    )
                    await self.security_monitor.process_event(event)
                
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request too large"}
                )
            
            # Validate content type
            content_type = request.headers.get("content-type")
            if not self.validator.validate_content_type(content_type):
                if self.security_monitor:
                    event = create_security_event(
                        EventType.MALICIOUS_INPUT,
                        AlertSeverity.LOW,
                        request,
                        "api",
                        {"reason": "invalid_content_type", "content_type": content_type}
                    )
                    await self.security_monitor.process_event(event)
                
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid content type"}
                )
            
            # Verify request signature if required
            if self.config.require_signed_requests and self.request_signer:
                signature = request.headers.get(self.config.signature_header)
                timestamp = request.headers.get("X-Request-Timestamp")
                
                if not signature or not timestamp:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Missing request signature or timestamp"}
                    )
                
                body = await request.body()
                if not self.request_signer.verify_signature(
                    signature,
                    request.method,
                    str(request.url.path),
                    body.decode(),
                    timestamp
                ):
                    if self.security_monitor:
                        event = create_security_event(
                            EventType.AUTHENTICATION_FAILURE,
                            AlertSeverity.HIGH,
                            request,
                            "api",
                            {"reason": "invalid_signature"}
                        )
                        await self.security_monitor.process_event(event)
                    
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid request signature"}
                    )
                
                # Recreate request with body
                request._body = body
            
            # Validate JSON content
            if content_type and "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        body_text = body.decode()
                        
                        # Check for dangerous patterns
                        threats = self.validator.scan_for_threats(body_text)
                        if threats:
                            if self.security_monitor:
                                event = create_security_event(
                                    EventType.MALICIOUS_INPUT,
                                    AlertSeverity.HIGH,
                                    request,
                                    "api",
                                    {"threats": threats}
                                )
                                await self.security_monitor.process_event(event)
                            
                            return JSONResponse(
                                status_code=400,
                                content={"error": "Malicious input detected"}
                            )
                        
                        # Validate JSON structure
                        try:
                            json_data = json.loads(body_text)
                            issues = self.validator.validate_json_structure(json_data)
                            
                            if issues:
                                if self.security_monitor:
                                    event = create_security_event(
                                        EventType.MALICIOUS_INPUT,
                                        AlertSeverity.MEDIUM,
                                        request,
                                        "api",
                                        {"validation_issues": issues}
                                    )
                                    await self.security_monitor.process_event(event)
                                
                                return JSONResponse(
                                    status_code=400,
                                    content={"error": "Invalid request structure"}
                                )
                        
                        except json.JSONDecodeError:
                            # Let the application handle JSON parsing errors
                            pass
                        
                        # Recreate request with validated body
                        request._body = body
                
                except Exception as e:
                    logger.error(f"Error validating JSON content: {e}")
            
            # Process request
            response = await call_next(request)
            
            # Filter response
            self.response_filter.filter_response_headers(response)
            
            # Add timing header for debugging (in development only)
            if os.getenv("ENVIRONMENT") == "development":
                duration = int((time.time() - start_time) * 1000)
                response.headers["X-Response-Time"] = f"{duration}ms"
            
            return response
            
        except Exception as e:
            logger.error(f"API security middleware error: {e}")
            
            # Log security incident
            if self.security_monitor:
                event = create_security_event(
                    EventType.SERVICE_ERROR,
                    AlertSeverity.HIGH,
                    request,
                    "api",
                    {"error": str(e)}
                )
                await self.security_monitor.process_event(event)
            
            # Return sanitized error response
            error_message = "Internal server error"
            if not self.config.mask_error_details:
                error_message = str(e)
            else:
                error_message = self.response_filter.sanitize_error_response(str(e))
            
            return JSONResponse(
                status_code=500,
                content={"error": error_message}
            )

class ServiceSpecificSecurity:
    """Service-specific security configurations"""
    
    SECURITY_CONFIGS = {
        "auth-service": APISecurityConfig(
            max_request_size=1024 * 1024,  # 1MB for auth requests
            allowed_content_types={"application/json"},
            require_content_type=True,
            require_signed_requests=True,
            mask_error_details=True
        ),
        
        "stt-service": APISecurityConfig(
            max_request_size=50 * 1024 * 1024,  # 50MB for audio files
            allowed_content_types={"application/json", "audio/wav", "audio/mp3", "multipart/form-data"},
            require_content_type=True,
            max_json_depth=5,
            mask_error_details=True
        ),
        
        "mt-service": APISecurityConfig(
            max_request_size=5 * 1024 * 1024,  # 5MB for text translation
            allowed_content_types={"application/json", "text/plain"},
            require_content_type=True,
            max_string_length=50000,  # Large texts for translation
            mask_error_details=True
        ),
        
        "tts-service": APISecurityConfig(
            max_request_size=2 * 1024 * 1024,  # 2MB for TTS requests
            allowed_content_types={"application/json"},
            require_content_type=True,
            max_string_length=10000,  # Long text for synthesis
            mask_error_details=True
        ),
        
        "livekit": APISecurityConfig(
            max_request_size=10 * 1024 * 1024,  # 10MB for room management
            allowed_content_types={"application/json", "application/x-protobuf"},
            require_content_type=False,  # LiveKit uses various protocols
            mask_error_details=True
        )
    }
    
    @classmethod
    def get_config(cls, service_name: str) -> APISecurityConfig:
        """Get security configuration for a service"""
        return cls.SECURITY_CONFIGS.get(service_name, APISecurityConfig())

# Factory functions for easy integration
def create_api_security_middleware(
    app: FastAPI,
    service_name: str,
    security_monitor: Optional[SecurityMonitor] = None,
    request_signing_key: Optional[str] = None
) -> APISecurityMiddleware:
    """Create API security middleware for a service"""
    config = ServiceSpecificSecurity.get_config(service_name)
    
    # Setup request signer if key provided
    request_signer = None
    if request_signing_key:
        request_signer = RequestSigner(request_signing_key)
    
    return APISecurityMiddleware(
        app,
        config,
        security_monitor,
        request_signer
    )

def setup_cors_middleware(app: FastAPI, service_name: str):
    """Setup CORS middleware with secure defaults"""
    config = ServiceSpecificSecurity.get_config(service_name)
    
    # Default allowed origins for The HIVE services
    default_origins = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "https://localhost:5173",
        "https://localhost:3000",
        "https://thehive.app",
        "https://www.thehive.app",
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins or default_origins,
        allow_credentials=config.allow_credentials,
        allow_methods=config.allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=config.allowed_headers or ["Authorization", "Content-Type", "X-API-Version"],
        expose_headers=config.expose_headers or ["X-API-Version", "X-Response-Time"],
        max_age=config.max_age
    )

def setup_service_security(
    app: FastAPI,
    service_name: str,
    security_monitor: Optional[SecurityMonitor] = None,
    request_signing_key: Optional[str] = None
) -> APISecurityMiddleware:
    """
    Setup comprehensive security for a FastAPI service
    
    Args:
        app: FastAPI application
        service_name: Name of the service
        security_monitor: Security monitoring instance
        request_signing_key: Key for request signing (optional)
        
    Returns:
        Configured API security middleware
    """
    # Setup CORS
    setup_cors_middleware(app, service_name)
    
    # Setup API security middleware
    api_middleware = create_api_security_middleware(
        app, service_name, security_monitor, request_signing_key
    )
    
    app.add_middleware(type(api_middleware), dispatch=api_middleware.dispatch)
    
    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
    
    logger.info(f"Security configured for service: {service_name}")
    
    return api_middleware

# Request/Response models for security
class SecureRequest(BaseModel):
    """Base model for secure API requests"""
    timestamp: Optional[str] = Field(None, description="Request timestamp")
    nonce: Optional[str] = Field(None, description="Request nonce for replay protection")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        if v:
            try:
                timestamp = float(v)
                # Check if timestamp is within acceptable range (5 minutes)
                current_time = time.time()
                if abs(current_time - timestamp) > 300:
                    raise ValueError("Timestamp outside acceptable range")
            except ValueError:
                raise ValueError("Invalid timestamp format")
        return v

class SecureResponse(BaseModel):
    """Base model for secure API responses"""
    timestamp: str = Field(default_factory=lambda: str(time.time()))
    api_version: str = Field(default="v1")

if __name__ == "__main__":
    # Example usage
    from fastapi import FastAPI
    
    app = FastAPI()
    
    # Setup security for STT service
    middleware = setup_service_security(app, "stt-service")
    
    @app.post("/transcribe")
    async def transcribe(request: Request):
        return {"message": "Transcription endpoint"}
    
    print("API security configured for STT service")
    print("Security features enabled:")
    print("- Request validation and sanitization")
    print("- Response filtering")
    print("- CORS protection")
    print("- Security headers")
    print("- Content type validation")
    print("- Size limits")
    print("- JSON structure validation")