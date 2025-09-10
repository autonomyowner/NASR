"""
LiveKit JWT Authentication Service

Provides secure JWT token generation for LiveKit rooms with proper scoping
and role-based access control optimized for translation workflows.

Features:
- Secure JWT generation with configurable expiration
- Role-based permissions (speaker, listener, translator, admin)
- Room-specific scoping and access control
- TURN credential generation integration
- Audit logging for security events
"""

import jwt
import time
import secrets
import hashlib
import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import json
import redis
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

logger = logging.getLogger(__name__)

class ParticipantRole(Enum):
    """Participant roles with specific permissions"""
    SPEAKER = "speaker"           # Can publish audio, request translation
    LISTENER = "listener"         # Can subscribe to audio, receive translations
    TRANSLATOR = "translator"     # Worker role, can subscribe to all, publish translations
    MODERATOR = "moderator"       # Can manage room, kick participants
    ADMIN = "admin"              # Full room control


@dataclass
class SecurityPolicy:
    """Security policies for JWT tokens"""
    max_tokens_per_user: int = 10
    max_tokens_per_ip: int = 100
    token_reuse_window_seconds: int = 300
    ip_whitelist: Optional[List[str]] = None
    require_secure_transport: bool = True
    enable_audit_logging: bool = True
    max_room_participants: int = 100

@dataclass
class JWTConfig:
    """Enhanced JWT service configuration with security policies"""
    api_key: str
    secret_key: str
    issuer: str = "thehive-sfu"
    default_ttl_hours: int = 6
    max_ttl_hours: int = 24
    algorithm: str = "HS256"
    # Security enhancements
    security_policy: SecurityPolicy = field(default_factory=SecurityPolicy)
    use_rsa_signing: bool = False
    private_key_path: Optional[str] = None
    public_key_path: Optional[str] = None
    redis_url: Optional[str] = None
    rate_limit_window_seconds: int = 3600
    rate_limit_max_requests: int = 100


@dataclass
class ParticipantPermissions:
    """Granular participant permissions for translation workflows"""
    # Publishing permissions
    can_publish_audio: bool = False
    can_publish_video: bool = False
    can_publish_data: bool = False
    can_publish_screen: bool = False
    
    # Subscription permissions
    can_subscribe_audio: bool = True
    can_subscribe_video: bool = False
    can_subscribe_data: bool = True
    
    # Translation-specific permissions
    can_request_translation: bool = False
    can_receive_translation: bool = True
    can_publish_translation: bool = False
    
    # Room management permissions
    can_update_metadata: bool = False
    can_kick_participants: bool = False
    can_lock_room: bool = False
    
    # Data channel permissions
    can_send_captions: bool = False
    can_receive_captions: bool = True


@dataclass
class TokenSecurityContext:
    """Security context for token generation and validation"""
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    issued_at: Optional[datetime] = None
    is_secure_transport: bool = False

class SecurityException(Exception):
    """Security-related exception"""
    pass

class RateLimitExceeded(SecurityException):
    """Rate limit exceeded exception"""
    pass

class TokenRevocationStore:
    """Token revocation and tracking store"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        
    def is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        if not self.redis:
            return False
        return self.redis.exists(f"revoked_token:{jti}") > 0
    
    def revoke_token(self, jti: str, expires_at: datetime) -> bool:
        """Revoke a token"""
        if not self.redis:
            return False
        
        ttl = max(1, int((expires_at - datetime.utcnow()).total_seconds()))
        return self.redis.setex(f"revoked_token:{jti}", ttl, "revoked")
    
    def track_token_usage(self, user_id: str, ip: str, jti: str) -> None:
        """Track token usage for rate limiting"""
        if not self.redis:
            return
            
        pipe = self.redis.pipeline()
        timestamp = int(time.time())
        
        # Track per-user tokens
        pipe.zadd(f"user_tokens:{user_id}", {jti: timestamp})
        pipe.expire(f"user_tokens:{user_id}", 86400)  # 24 hours
        
        # Track per-IP tokens
        pipe.zadd(f"ip_tokens:{ip}", {jti: timestamp})
        pipe.expire(f"ip_tokens:{ip}", 86400)  # 24 hours
        
        pipe.execute()
    
    def check_rate_limits(self, user_id: str, ip: str, policy: SecurityPolicy) -> None:
        """Check rate limits for user and IP"""
        if not self.redis:
            return
        
        current_time = int(time.time())
        window_start = current_time - policy.token_reuse_window_seconds
        
        # Check user token limit
        user_count = self.redis.zcount(f"user_tokens:{user_id}", window_start, current_time)
        if user_count >= policy.max_tokens_per_user:
            raise RateLimitExceeded(f"User {user_id} exceeded token limit")
        
        # Check IP token limit
        ip_count = self.redis.zcount(f"ip_tokens:{ip}", window_start, current_time)
        if ip_count >= policy.max_tokens_per_ip:
            raise RateLimitExceeded(f"IP {ip} exceeded token limit")

class LiveKitJWTService:
    """Enhanced JWT token generation service with comprehensive security features"""
    
    # Pre-configured role permissions for translation use cases
    ROLE_PERMISSIONS = {
        ParticipantRole.SPEAKER: ParticipantPermissions(
            can_publish_audio=True,
            can_publish_data=True,
            can_request_translation=True,
            can_update_metadata=True,
        ),
        
        ParticipantRole.LISTENER: ParticipantPermissions(
            can_publish_audio=False,
            can_receive_translation=True,
            can_receive_captions=True,
        ),
        
        ParticipantRole.TRANSLATOR: ParticipantPermissions(
            can_publish_audio=True,  # Publish translated audio
            can_subscribe_audio=True,  # Subscribe to all speaker audio
            can_publish_data=True,   # Send captions via data channel
            can_publish_translation=True,
            can_send_captions=True,
            can_update_metadata=True,  # Update translation status
        ),
        
        ParticipantRole.MODERATOR: ParticipantPermissions(
            can_publish_audio=True,
            can_publish_data=True,
            can_request_translation=True,
            can_kick_participants=True,
            can_update_metadata=True,
        ),
        
        ParticipantRole.ADMIN: ParticipantPermissions(
            can_publish_audio=True,
            can_publish_video=True,
            can_publish_data=True,
            can_publish_screen=True,
            can_request_translation=True,
            can_publish_translation=True,
            can_kick_participants=True,
            can_lock_room=True,
            can_update_metadata=True,
            can_send_captions=True,
        )
    }
    
    def __init__(self, config: JWTConfig):
        self.config = config
        self._validate_config()
        
        # Initialize security components
        self.redis_client = None
        if config.redis_url:
            try:
                self.redis_client = redis.from_url(config.redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Connected to Redis for token management")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
        
        self.revocation_store = TokenRevocationStore(self.redis_client)
        
        # Load RSA keys if configured
        self.private_key = None
        self.public_key = None
        if config.use_rsa_signing:
            self._load_rsa_keys()
    def _load_rsa_keys(self) -> None:
        """Load RSA private and public keys for signing"""
        try:
            if self.config.private_key_path and os.path.exists(self.config.private_key_path):
                with open(self.config.private_key_path, 'rb') as f:
                    self.private_key = load_pem_private_key(f.read(), password=None)
                logger.info("Loaded RSA private key for JWT signing")
            
            if self.config.public_key_path and os.path.exists(self.config.public_key_path):
                with open(self.config.public_key_path, 'rb') as f:
                    self.public_key = load_pem_public_key(f.read())
                logger.info("Loaded RSA public key for JWT validation")
                
        except Exception as e:
            logger.error(f"Failed to load RSA keys: {e}")
            raise ValueError("Failed to load RSA keys for signing")
    
    def _validate_config(self) -> None:
        """Enhanced JWT configuration validation"""
        if not self.config.api_key or len(self.config.api_key) < 16:
            raise ValueError("API key must be at least 16 characters long")
        
        if not self.config.secret_key or len(self.config.secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        
        # Validate security policy
        policy = self.config.security_policy
        if policy.max_tokens_per_user < 1:
            raise ValueError("max_tokens_per_user must be at least 1")
        
        if policy.max_tokens_per_ip < 1:
            raise ValueError("max_tokens_per_ip must be at least 1")
        
        # Validate RSA configuration
        if self.config.use_rsa_signing:
            if not self.config.private_key_path:
                raise ValueError("RSA private key path required when RSA signing is enabled")
    
    def _validate_security_context(self, context: TokenSecurityContext) -> None:
        """Validate security context and enforce policies"""
        policy = self.config.security_policy
        
        # Check secure transport requirement
        if policy.require_secure_transport and not context.is_secure_transport:
            raise SecurityException("Secure transport (HTTPS) required")
        
        # Validate IP whitelist
        if policy.ip_whitelist and context.client_ip:
            ip = ipaddress.ip_address(context.client_ip)
            allowed = False
            
            for allowed_range in policy.ip_whitelist:
                try:
                    if ip in ipaddress.ip_network(allowed_range, strict=False):
                        allowed = True
                        break
                except ValueError:
                    if context.client_ip == allowed_range:
                        allowed = True
                        break
            
            if not allowed:
                raise SecurityException(f"IP {context.client_ip} not allowed")
        
        # Check rate limits
        if context.client_ip:
            self.revocation_store.check_rate_limits(
                user_id="anonymous",  # Would be actual user ID in production
                ip=context.client_ip,
                policy=policy
            )
    
    def generate_room_token(
        self,
        room_name: str,
        participant_name: str,
        role: ParticipantRole,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_hours: Optional[int] = None,
        custom_permissions: Optional[ParticipantPermissions] = None,
        allowed_languages: Optional[List[str]] = None,
        security_context: Optional[TokenSecurityContext] = None
    ) -> str:
        """
        Generate LiveKit JWT token for room access with enhanced security
        
        Args:
            room_name: Name of the LiveKit room
            participant_name: Unique participant identifier
            role: Participant role (defines permissions)
            metadata: Custom participant metadata
            ttl_hours: Token time-to-live in hours
            custom_permissions: Override default role permissions
            allowed_languages: List of languages this participant can access
            security_context: Security context for additional validation
            
        Returns:
            Signed JWT token string
            
        Raises:
            SecurityException: If security policies are violated
            RateLimitExceeded: If rate limits are exceeded
        """
        # Validate security context
        if security_context:
            self._validate_security_context(security_context)
        
        now = int(time.time())
        ttl = ttl_hours or self.config.default_ttl_hours
        
        if ttl > self.config.max_ttl_hours:
            raise ValueError(f"TTL cannot exceed {self.config.max_ttl_hours} hours")
        
        exp = now + (ttl * 3600)
        
        # Generate unique token ID
        jti = self._generate_jti()
        
        # Get permissions for role
        permissions = custom_permissions or self.ROLE_PERMISSIONS.get(role)
        if not permissions:
            raise ValueError(f"Unknown role: {role}")
        
        # Build video grants (LiveKit permissions)
        video_grants = self._build_video_grants(
            room_name=room_name,
            permissions=permissions,
            allowed_languages=allowed_languages
        )
        
        # Build participant metadata
        participant_metadata = self._build_participant_metadata(
            role=role,
            metadata=metadata or {},
            allowed_languages=allowed_languages
        )
        
        # Build JWT payload
        payload = {
            "iss": self.config.issuer,
            "sub": participant_name,
            "aud": "livekit",
            "exp": exp,
            "nbf": now,
            "iat": now,
            "jti": self._generate_jti(),
            "video": video_grants,
            "metadata": json.dumps(participant_metadata)
        }
        
        # Sign token with appropriate algorithm
        if self.config.use_rsa_signing and self.private_key:
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm="RS256"
            )
        else:
            token = jwt.encode(
                payload,
                self.config.secret_key,
                algorithm=self.config.algorithm
            )
        
        # Track token usage for rate limiting
        if security_context and security_context.client_ip:
            self.revocation_store.track_token_usage(
                user_id=participant_name,
                ip=security_context.client_ip,
                jti=jti
            )
        
        # Enhanced audit logging
        self._log_token_generation(
            room_name=room_name,
            participant_name=participant_name,
            role=role,
            ttl_hours=ttl,
            token_hash=self._hash_token(token),
            security_context=security_context,
            jti=jti
        )
        
        return token
    
    def _build_video_grants(
        self,
        room_name: str,
        permissions: ParticipantPermissions,
        allowed_languages: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Build LiveKit video grants from permissions"""
        grants = {
            "room": room_name,
            "roomJoin": True,
            
            # Publishing permissions
            "canPublish": permissions.can_publish_audio or permissions.can_publish_video,
            "canPublishData": permissions.can_publish_data,
            "canPublishSources": [],
            
            # Subscription permissions  
            "canSubscribe": permissions.can_subscribe_audio or permissions.can_subscribe_video,
            
            # Administrative permissions
            "canUpdateOwnMetadata": permissions.can_update_metadata,
            
            # Translation-specific grants
            "hidden": False,  # Translator workers might be hidden
            "recorder": False,  # Not a recording participant
        }
        
        # Build publishable sources list
        if permissions.can_publish_audio:
            grants["canPublishSources"].append("microphone")
        
        if permissions.can_publish_video:
            grants["canPublishSources"].append("camera")
            
        if permissions.can_publish_screen:
            grants["canPublishSources"].append("screen_share")
        
        # Room management permissions (admin only)
        if permissions.can_kick_participants:
            grants["roomAdmin"] = True
            
        # Translation workflow optimizations
        if permissions.can_publish_translation:
            grants["canPublishSources"].append("microphone")  # For translated audio
            grants["hidden"] = False  # Translator participants visible
            
        return grants
    
    def _build_participant_metadata(
        self,
        role: ParticipantRole,
        metadata: Dict[str, Any],
        allowed_languages: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Build participant metadata with role and language information"""
        participant_metadata = {
            "role": role.value,
            "joinedAt": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            **metadata  # Custom metadata
        }
        
        # Add language information for translation workflows
        if allowed_languages:
            participant_metadata["allowedLanguages"] = allowed_languages
            
        if role == ParticipantRole.TRANSLATOR:
            participant_metadata["isTranslator"] = True
            participant_metadata["translationCapabilities"] = allowed_languages or []
            
        return participant_metadata
    
    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return secrets.token_urlsafe(16)
    
    def _hash_token(self, token: str) -> str:
        """Generate hash of token for audit logging"""
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    def _log_token_generation(
        self,
        room_name: str,
        participant_name: str,
        role: ParticipantRole,
        ttl_hours: int,
        token_hash: str,
        security_context: Optional[TokenSecurityContext] = None,
        jti: Optional[str] = None
    ) -> None:
        """Enhanced audit logging for token generation"""
        log_data = {
            "event": "jwt_token_generated",
            "room_name": room_name,
            "participant_name": participant_name,
            "role": role.value,
            "ttl_hours": ttl_hours,
            "token_hash": token_hash,
            "jti": jti,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if security_context:
            log_data.update({
                "client_ip": security_context.client_ip,
                "user_agent": security_context.user_agent,
                "request_id": security_context.request_id,
                "is_secure_transport": security_context.is_secure_transport
            })
        
        logger.info(f"JWT token generated", extra={"security_audit": log_data})
    
    def validate_token(self, token: str, security_context: Optional[TokenSecurityContext] = None) -> Dict[str, Any]:
        """
        Enhanced token validation with revocation checking
        
        Args:
            token: JWT token to validate
            security_context: Security context for validation
            
        Returns:
            Decoded token payload
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
            SecurityException: If token is revoked or security checks fail
        """
        try:
            # Choose decoding key based on signing method
            if self.config.use_rsa_signing and self.public_key:
                payload = jwt.decode(
                    token,
                    self.public_key,
                    algorithms=["RS256"],
                    audience="livekit"
                )
            else:
                payload = jwt.decode(
                    token,
                    self.config.secret_key,
                    algorithms=[self.config.algorithm],
                    audience="livekit"
                )
            
            # Additional validation
            if payload.get("iss") != self.config.issuer:
                raise jwt.InvalidTokenError("Invalid issuer")
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and self.revocation_store.is_token_revoked(jti):
                raise SecurityException("Token has been revoked")
            
            # Log successful validation
            self._log_token_validation(token, payload, security_context, success=True)
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired token validation attempt: {self._hash_token(token)}")
            self._log_token_validation(token, None, security_context, success=False, error="expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token validation attempt: {e}")
            self._log_token_validation(token, None, security_context, success=False, error=str(e))
            raise
        except SecurityException as e:
            logger.warning(f"Security violation during token validation: {e}")
            self._log_token_validation(token, None, security_context, success=False, error=str(e))
            raise
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a JWT token
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successfully revoked
        """
        try:
            payload = self.validate_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if not jti or not exp:
                logger.error("Cannot revoke token: missing jti or exp")
                return False
            
            expires_at = datetime.fromtimestamp(exp)
            success = self.revocation_store.revoke_token(jti, expires_at)
            
            if success:
                logger.info(f"Token revoked: jti={jti}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def _log_token_validation(
        self,
        token: str,
        payload: Optional[Dict[str, Any]],
        security_context: Optional[TokenSecurityContext],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log token validation attempts"""
        log_data = {
            "event": "jwt_token_validation",
            "token_hash": self._hash_token(token),
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if payload:
            log_data.update({
                "room_name": payload.get("video", {}).get("room"),
                "participant_name": payload.get("sub"),
                "jti": payload.get("jti")
            })
        
        if security_context:
            log_data.update({
                "client_ip": security_context.client_ip,
                "user_agent": security_context.user_agent,
                "request_id": security_context.request_id
            })
        
        if error:
            log_data["error"] = error
        
        level = logging.INFO if success else logging.WARNING
        logger.log(level, f"JWT token validation", extra={"security_audit": log_data})
    
    def generate_translator_token(
        self,
        room_name: str,
        worker_id: str,
        target_languages: List[str],
        ttl_hours: Optional[int] = None
    ) -> str:
        """
        Generate specialized JWT token for translator workers
        
        Args:
            room_name: Target room name
            worker_id: Unique worker identifier  
            target_languages: Languages this worker can translate to
            ttl_hours: Token TTL (defaults to 24 hours for workers)
            
        Returns:
            JWT token for translator worker
        """
        return self.generate_room_token(
            room_name=room_name,
            participant_name=f"translator-{worker_id}",
            role=ParticipantRole.TRANSLATOR,
            ttl_hours=ttl_hours or 24,  # Longer TTL for workers
            metadata={
                "workerId": worker_id,
                "workerType": "translator",
                "targetLanguages": target_languages,
                "isAutomated": True
            },
            allowed_languages=target_languages
        )
    
    def generate_turn_credentials(
        self,
        username: str,
        ttl_seconds: int = 3600
    ) -> Dict[str, str]:
        """
        Generate TURN server credentials using time-based algorithm
        Compatible with CoTURN REST API authentication
        
        Args:
            username: TURN username
            ttl_seconds: Credential time-to-live
            
        Returns:
            Dictionary with username and password for TURN server
        """
        timestamp = int(time.time()) + ttl_seconds
        turn_username = f"{timestamp}:{username}"
        
        # Generate HMAC password using shared secret
        import hmac
        turn_password = hmac.new(
            self.config.secret_key.encode(),
            turn_username.encode(),
            hashlib.sha1
        ).hexdigest()
        
        return {
            "username": turn_username,
            "password": turn_password,
            "ttl": ttl_seconds,
            "uris": [
                f"turn:{os.getenv('TURN_SERVER_HOST', 'localhost')}:3478?transport=udp",
                f"turn:{os.getenv('TURN_SERVER_HOST', 'localhost')}:3478?transport=tcp"
            ]
        }


# Factory function for easy service creation
def create_jwt_service() -> LiveKitJWTService:
    """Create JWT service from environment variables"""
    config = JWTConfig(
        api_key=os.getenv("LIVEKIT_API_KEY", ""),
        secret_key=os.getenv("LIVEKIT_SECRET_KEY", ""),
        issuer=os.getenv("JWT_ISSUER", "thehive-sfu"),
        default_ttl_hours=int(os.getenv("JWT_DEFAULT_TTL_HOURS", "6")),
        max_ttl_hours=int(os.getenv("JWT_MAX_TTL_HOURS", "24"))
    )
    
    return LiveKitJWTService(config)


# CLI utility for token generation (development/testing)
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate LiveKit JWT tokens")
    parser.add_argument("--room", required=True, help="Room name")
    parser.add_argument("--participant", required=True, help="Participant name")
    parser.add_argument("--role", choices=[r.value for r in ParticipantRole], 
                       default="listener", help="Participant role")
    parser.add_argument("--languages", nargs="*", help="Allowed languages")
    parser.add_argument("--ttl", type=int, default=6, help="TTL in hours")
    
    args = parser.parse_args()
    
    # Create service
    service = create_jwt_service()
    
    # Generate token
    try:
        token = service.generate_room_token(
            room_name=args.room,
            participant_name=args.participant,
            role=ParticipantRole(args.role),
            allowed_languages=args.languages,
            ttl_hours=args.ttl
        )
        
        print(f"Generated JWT token:")
        print(token)
        print(f"\nToken valid for {args.ttl} hours")
        
    except Exception as e:
        print(f"Error generating token: {e}")
        exit(1)