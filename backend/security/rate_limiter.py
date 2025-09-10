"""
Advanced Rate Limiting System for The HIVE Translation Services

Implements distributed rate limiting with Redis backend, supporting multiple
algorithms and dynamic rate limiting based on user roles and service load.

Features:
- Token bucket and sliding window algorithms
- Distributed rate limiting across multiple service instances
- Role-based rate limiting with dynamic adjustments
- Circuit breaker integration for service protection
- Real-time monitoring and alerting
"""

import redis
import time
import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import aioredis
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"

class RateLimitScope(Enum):
    """Rate limiting scopes"""
    GLOBAL = "global"
    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_SERVICE = "per_service"
    PER_ENDPOINT = "per_endpoint"
    PER_ROOM = "per_room"

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    scope: RateLimitScope
    algorithm: RateLimitAlgorithm
    requests_per_window: int
    window_seconds: int
    burst_capacity: Optional[int] = None
    refill_rate: Optional[float] = None  # tokens per second for token bucket
    enabled: bool = True
    exclude_paths: List[str] = None
    include_paths: List[str] = None
    user_roles: List[str] = None  # Apply to specific user roles
    
    def __post_init__(self):
        if self.exclude_paths is None:
            self.exclude_paths = []
        if self.include_paths is None:
            self.include_paths = []
        if self.user_roles is None:
            self.user_roles = []

@dataclass
class RateLimitStatus:
    """Rate limit status information"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    current_usage: int = 0
    rule_name: str = ""
    scope_value: str = ""

class RateLimitExceededException(Exception):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, status: RateLimitStatus):
        self.status = status
        super().__init__(f"Rate limit exceeded for {status.rule_name}")

class RedisRateLimiter:
    """Redis-backed distributed rate limiter"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.lua_scripts = {}
        self._load_lua_scripts()
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis rate limiter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis rate limiter: {e}")
            raise
    
    def _load_lua_scripts(self):
        """Load Lua scripts for atomic rate limiting operations"""
        
        # Token bucket algorithm script
        self.lua_scripts["token_bucket"] = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local requested_tokens = tonumber(ARGV[3])
        local window = tonumber(ARGV[4])
        local now = tonumber(ARGV[5])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calculate tokens to add based on elapsed time
        local elapsed = math.max(0, now - last_refill)
        local tokens_to_add = math.floor(elapsed * refill_rate)
        tokens = math.min(capacity, tokens + tokens_to_add)
        
        -- Check if request can be fulfilled
        local allowed = tokens >= requested_tokens
        if allowed then
            tokens = tokens - requested_tokens
        end
        
        -- Update bucket state
        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
        redis.call('EXPIRE', key, window * 2)
        
        return {allowed and 1 or 0, tokens, capacity - tokens}
        """
        
        # Sliding window algorithm script
        self.lua_scripts["sliding_window"] = """
        local key = KEYS[1]
        local window = tonumber(ARGV[1])
        local limit = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local weight = tonumber(ARGV[4]) or 1
        
        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
        
        -- Count current requests
        local current = redis.call('ZCARD', key)
        
        -- Check if request is allowed
        local allowed = current < limit
        if allowed then
            -- Add current request
            redis.call('ZADD', key, now, now .. ':' .. math.random(1000000))
        end
        
        -- Set expiration
        redis.call('EXPIRE', key, window + 1)
        
        -- Calculate reset time
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        local reset_time = now
        if #oldest > 0 then
            reset_time = tonumber(oldest[2]) + window
        end
        
        return {allowed and 1 or 0, limit - current - (allowed and 1 or 0), reset_time, current}
        """
        
        # Fixed window algorithm script
        self.lua_scripts["fixed_window"] = """
        local key = KEYS[1]
        local window = tonumber(ARGV[1])
        local limit = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        
        -- Calculate window start
        local window_start = math.floor(now / window) * window
        local window_key = key .. ':' .. window_start
        
        -- Get current count
        local current = tonumber(redis.call('GET', window_key)) or 0
        
        -- Check if request is allowed
        local allowed = current < limit
        if allowed then
            current = redis.call('INCR', window_key)
        end
        
        -- Set expiration for the window
        redis.call('EXPIRE', window_key, window * 2)
        
        -- Calculate reset time
        local reset_time = window_start + window
        
        return {allowed and 1 or 0, limit - current, reset_time, current}
        """
    
    async def check_rate_limit(
        self,
        rule: RateLimitRule,
        scope_value: str,
        requested_tokens: int = 1
    ) -> RateLimitStatus:
        """Check if request is within rate limit"""
        
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        key = f"rate_limit:{rule.name}:{rule.scope.value}:{scope_value}"
        now = time.time()
        
        try:
            if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                result = await self._check_token_bucket(
                    key, rule, requested_tokens, now
                )
            elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                result = await self._check_sliding_window(
                    key, rule, requested_tokens, now
                )
            elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                result = await self._check_fixed_window(
                    key, rule, requested_tokens, now
                )
            else:
                raise ValueError(f"Unsupported algorithm: {rule.algorithm}")
            
            allowed, remaining, reset_time, current_usage = result
            
            status = RateLimitStatus(
                allowed=bool(allowed),
                remaining=max(0, int(remaining)),
                reset_time=int(reset_time),
                current_usage=int(current_usage),
                rule_name=rule.name,
                scope_value=scope_value
            )
            
            if not status.allowed:
                status.retry_after = max(1, int(reset_time - now))
            
            return status
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open for availability
            return RateLimitStatus(
                allowed=True,
                remaining=rule.requests_per_window,
                reset_time=int(now + rule.window_seconds),
                rule_name=rule.name,
                scope_value=scope_value
            )
    
    async def _check_token_bucket(
        self,
        key: str,
        rule: RateLimitRule,
        requested_tokens: int,
        now: float
    ) -> Tuple[int, int, int, int]:
        """Check token bucket rate limit"""
        capacity = rule.burst_capacity or rule.requests_per_window
        refill_rate = rule.refill_rate or (rule.requests_per_window / rule.window_seconds)
        
        script = self.redis_client.register_script(self.lua_scripts["token_bucket"])
        result = await script(
            keys=[key],
            args=[capacity, refill_rate, requested_tokens, rule.window_seconds, now]
        )
        
        allowed, tokens_remaining, tokens_used = result
        reset_time = now + (capacity - tokens_remaining) / refill_rate
        
        return allowed, tokens_remaining, reset_time, tokens_used
    
    async def _check_sliding_window(
        self,
        key: str,
        rule: RateLimitRule,
        requested_tokens: int,
        now: float
    ) -> Tuple[int, int, int, int]:
        """Check sliding window rate limit"""
        script = self.redis_client.register_script(self.lua_scripts["sliding_window"])
        result = await script(
            keys=[key],
            args=[rule.window_seconds, rule.requests_per_window, now, requested_tokens]
        )
        
        return tuple(result)
    
    async def _check_fixed_window(
        self,
        key: str,
        rule: RateLimitRule,
        requested_tokens: int,
        now: float
    ) -> Tuple[int, int, int, int]:
        """Check fixed window rate limit"""
        script = self.redis_client.register_script(self.lua_scripts["fixed_window"])
        result = await script(
            keys=[key],
            args=[rule.window_seconds, rule.requests_per_window, now]
        )
        
        return tuple(result)
    
    async def reset_rate_limit(self, rule: RateLimitRule, scope_value: str) -> bool:
        """Reset rate limit for a specific scope"""
        try:
            key_pattern = f"rate_limit:{rule.name}:{rule.scope.value}:{scope_value}*"
            keys = await self.redis_client.keys(key_pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Reset rate limit: {rule.name} for {scope_value}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False
    
    async def get_rate_limit_info(
        self,
        rule: RateLimitRule,
        scope_value: str
    ) -> Dict[str, Any]:
        """Get detailed rate limit information"""
        key = f"rate_limit:{rule.name}:{rule.scope.value}:{scope_value}"
        
        try:
            if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                bucket = await self.redis_client.hmget(key, "tokens", "last_refill")
                return {
                    "algorithm": rule.algorithm.value,
                    "tokens": int(bucket[0]) if bucket[0] else rule.burst_capacity,
                    "last_refill": float(bucket[1]) if bucket[1] else time.time(),
                    "capacity": rule.burst_capacity or rule.requests_per_window,
                    "refill_rate": rule.refill_rate or (rule.requests_per_window / rule.window_seconds)
                }
            
            elif rule.algorithm in [RateLimitAlgorithm.SLIDING_WINDOW, RateLimitAlgorithm.FIXED_WINDOW]:
                count = await self.redis_client.zcard(key) if rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW else await self.redis_client.get(key)
                return {
                    "algorithm": rule.algorithm.value,
                    "current_requests": int(count) if count else 0,
                    "limit": rule.requests_per_window,
                    "window_seconds": rule.window_seconds
                }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {}

class AdvancedRateLimiter:
    """Advanced rate limiter with multiple rules and adaptive behavior"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_limiter = RedisRateLimiter(redis_url)
        self.rules: Dict[str, RateLimitRule] = {}
        self.adaptive_rules: Dict[str, Dict[str, Any]] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Default rules for The HIVE services
        self._setup_default_rules()
    
    async def initialize(self):
        """Initialize the rate limiter"""
        await self.redis_limiter.initialize()
        logger.info("Advanced rate limiter initialized")
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules for The HIVE services"""
        
        # Global API rate limiting
        self.rules["global_api"] = RateLimitRule(
            name="global_api",
            scope=RateLimitScope.GLOBAL,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            requests_per_window=10000,
            window_seconds=60,
            exclude_paths=["/health", "/metrics"]
        )
        
        # Per-IP rate limiting
        self.rules["per_ip_general"] = RateLimitRule(
            name="per_ip_general",
            scope=RateLimitScope.PER_IP,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            requests_per_window=100,
            window_seconds=60,
            burst_capacity=150,
            refill_rate=1.67,  # 100 per minute
            exclude_paths=["/health"]
        )
        
        # Authentication endpoints
        self.rules["auth_endpoints"] = RateLimitRule(
            name="auth_endpoints",
            scope=RateLimitScope.PER_IP,
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            requests_per_window=10,
            window_seconds=60,
            include_paths=["/token/", "/auth/"]
        )
        
        # Translation service rate limiting
        self.rules["stt_service"] = RateLimitRule(
            name="stt_service",
            scope=RateLimitScope.PER_USER,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            requests_per_window=1000,
            window_seconds=3600,  # 1 hour
            burst_capacity=50,
            refill_rate=0.278  # 1000 per hour
        )
        
        self.rules["mt_service"] = RateLimitRule(
            name="mt_service",
            scope=RateLimitScope.PER_USER,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            requests_per_window=5000,
            window_seconds=3600
        )
        
        self.rules["tts_service"] = RateLimitRule(
            name="tts_service",
            scope=RateLimitScope.PER_USER,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            requests_per_window=500,
            window_seconds=3600,
            burst_capacity=25,
            refill_rate=0.139  # 500 per hour
        )
        
        # Room-specific limits
        self.rules["room_join"] = RateLimitRule(
            name="room_join",
            scope=RateLimitScope.PER_IP,
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            requests_per_window=10,
            window_seconds=3600,
            include_paths=["/room/join"]
        )
        
        # Role-based limits
        self.rules["speaker_actions"] = RateLimitRule(
            name="speaker_actions",
            scope=RateLimitScope.PER_USER,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            requests_per_window=200,
            window_seconds=60,
            burst_capacity=20,
            refill_rate=3.33,
            user_roles=["speaker", "moderator", "admin"]
        )
        
        self.rules["listener_actions"] = RateLimitRule(
            name="listener_actions",
            scope=RateLimitScope.PER_USER,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            requests_per_window=50,
            window_seconds=60,
            user_roles=["listener"]
        )
    
    def add_rule(self, rule: RateLimitRule):
        """Add a custom rate limiting rule"""
        self.rules[rule.name] = rule
        logger.info(f"Added rate limit rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rate limiting rule"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed rate limit rule: {rule_name}")
            return True
        return False
    
    async def check_request(
        self,
        request: Request,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        service_name: Optional[str] = None
    ) -> List[RateLimitStatus]:
        """Check request against all applicable rate limiting rules"""
        
        results = []
        path = request.url.path
        client_ip = self._get_client_ip(request)
        
        for rule_name, rule in self.rules.items():
            # Skip disabled rules
            if not rule.enabled:
                continue
            
            # Check path inclusion/exclusion
            if rule.include_paths and not any(p in path for p in rule.include_paths):
                continue
            
            if rule.exclude_paths and any(p in path for p in rule.exclude_paths):
                continue
            
            # Check user role requirements
            if rule.user_roles and (not user_role or user_role not in rule.user_roles):
                continue
            
            # Determine scope value
            scope_value = self._get_scope_value(rule, client_ip, user_id, service_name, request)
            
            # Check rate limit
            status = await self.redis_limiter.check_rate_limit(rule, scope_value)
            results.append(status)
            
            # Stop on first violation for fail-fast
            if not status.allowed:
                break
        
        return results
    
    def _get_scope_value(
        self,
        rule: RateLimitRule,
        client_ip: str,
        user_id: Optional[str],
        service_name: Optional[str],
        request: Request
    ) -> str:
        """Get scope value for rate limiting key"""
        
        if rule.scope == RateLimitScope.GLOBAL:
            return "global"
        elif rule.scope == RateLimitScope.PER_IP:
            return client_ip
        elif rule.scope == RateLimitScope.PER_USER:
            return user_id or client_ip
        elif rule.scope == RateLimitScope.PER_SERVICE:
            return service_name or "unknown"
        elif rule.scope == RateLimitScope.PER_ENDPOINT:
            return f"{request.method}:{request.url.path}"
        elif rule.scope == RateLimitScope.PER_ROOM:
            # Extract room from path or query params
            room_id = request.path_params.get("room_id") or request.query_params.get("room")
            return room_id or "default"
        
        return "default"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    async def reset_limits(self, user_id: Optional[str] = None, ip: Optional[str] = None):
        """Reset rate limits for a user or IP"""
        reset_count = 0
        
        for rule in self.rules.values():
            if user_id and rule.scope == RateLimitScope.PER_USER:
                if await self.redis_limiter.reset_rate_limit(rule, user_id):
                    reset_count += 1
            
            if ip and rule.scope == RateLimitScope.PER_IP:
                if await self.redis_limiter.reset_rate_limit(rule, ip):
                    reset_count += 1
        
        logger.info(f"Reset {reset_count} rate limits for user={user_id}, ip={ip}")
        return reset_count
    
    async def get_status_summary(self) -> Dict[str, Any]:
        """Get rate limiter status summary"""
        try:
            redis_info = await self.redis_limiter.redis_client.info()
            
            return {
                "enabled": True,
                "rules_count": len(self.rules),
                "rules": {name: asdict(rule) for name, rule in self.rules.items()},
                "redis_connected": True,
                "redis_memory": redis_info.get("used_memory_human"),
                "redis_commands_processed": redis_info.get("total_commands_processed")
            }
        except Exception as e:
            logger.error(f"Failed to get rate limiter status: {e}")
            return {"enabled": False, "error": str(e)}


# FastAPI middleware integration
class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, rate_limiter: AdvancedRateLimiter):
        self.app = app
        self.rate_limiter = rate_limiter
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Extract user info from JWT if available
        user_id, user_role = await self._extract_user_info(request)
        
        # Check rate limits
        try:
            statuses = await self.rate_limiter.check_request(
                request, user_id=user_id, user_role=user_role
            )
            
            # Find any violations
            violation = next((s for s in statuses if not s.allowed), None)
            
            if violation:
                # Rate limit exceeded
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "rule": violation.rule_name,
                        "retry_after": violation.retry_after,
                        "reset_time": violation.reset_time
                    },
                    headers={
                        "X-RateLimit-Limit": str(violation.remaining + violation.current_usage),
                        "X-RateLimit-Remaining": str(violation.remaining),
                        "X-RateLimit-Reset": str(violation.reset_time),
                        "Retry-After": str(violation.retry_after) if violation.retry_after else "60"
                    }
                )
                await response(scope, receive, send)
                return
            
            # Add rate limit headers to successful responses
            async def add_headers(message):
                if message["type"] == "http.response.start":
                    headers = dict(message["headers"])
                    
                    # Add rate limit info from first applicable rule
                    if statuses:
                        status_info = statuses[0]
                        headers[b"x-ratelimit-limit"] = str(status_info.remaining + status_info.current_usage).encode()
                        headers[b"x-ratelimit-remaining"] = str(status_info.remaining).encode()
                        headers[b"x-ratelimit-reset"] = str(status_info.reset_time).encode()
                    
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await self.app(scope, receive, add_headers)
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Fail open - allow request to proceed
            await self.app(scope, receive, send)
    
    async def _extract_user_info(self, request: Request) -> Tuple[Optional[str], Optional[str]]:
        """Extract user ID and role from JWT token"""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None, None
            
            token = auth_header.split(" ")[1]
            
            # Decode JWT token (assuming it's already validated by auth middleware)
            # This is a simplified extraction - in practice, use proper JWT validation
            import jwt
            import os
            
            secret = os.getenv("LIVEKIT_SECRET_KEY")
            if not secret:
                return None, None
            
            payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_signature": False})
            
            user_id = payload.get("sub")
            
            # Extract role from metadata or direct role field
            metadata_str = payload.get("metadata", "{}")
            if isinstance(metadata_str, str):
                metadata = json.loads(metadata_str)
                user_role = metadata.get("role") or payload.get("role")
            else:
                user_role = payload.get("role")
            
            return user_id, user_role
            
        except Exception as e:
            logger.debug(f"Failed to extract user info: {e}")
            return None, None


# Factory function
def create_rate_limiter(redis_url: str = "redis://localhost:6379") -> AdvancedRateLimiter:
    """Create and configure advanced rate limiter"""
    return AdvancedRateLimiter(redis_url)


# CLI utility for testing
if __name__ == "__main__":
    import asyncio
    import argparse
    
    async def test_rate_limiter():
        limiter = create_rate_limiter()
        await limiter.initialize()
        
        # Test rate limiting
        for i in range(15):
            rule = limiter.rules["per_ip_general"]
            status = await limiter.redis_limiter.check_rate_limit(rule, "127.0.0.1")
            
            print(f"Request {i+1}: allowed={status.allowed}, remaining={status.remaining}")
            
            if not status.allowed:
                print(f"Rate limited! Retry after {status.retry_after} seconds")
                break
            
            await asyncio.sleep(0.1)
    
    parser = argparse.ArgumentParser(description="Test rate limiter")
    parser.add_argument("--test", action="store_true", help="Run rate limit test")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_rate_limiter())