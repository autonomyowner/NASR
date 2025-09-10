"""
LiveKit JWT Authentication API Service

FastAPI service providing secure JWT token generation and TURN credentials
for The HIVE translation system.

Endpoints:
- POST /token/room - Generate room access token
- POST /token/translator - Generate translator worker token  
- POST /credentials/turn - Generate TURN server credentials
- GET /health - Health check
"""

import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import uvicorn

from jwt_service import LiveKitJWTService, ParticipantRole, create_jwt_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Request/Response models
class RoomTokenRequest(BaseModel):
    """Request model for room token generation"""
    room_name: str
    participant_name: str
    role: str = "listener"
    metadata: Optional[Dict[str, Any]] = None
    ttl_hours: Optional[int] = None
    allowed_languages: Optional[List[str]] = None
    
    @validator('role')
    def validate_role(cls, v):
        """Validate participant role"""
        try:
            ParticipantRole(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid role. Must be one of: {[r.value for r in ParticipantRole]}")
    
    @validator('room_name')
    def validate_room_name(cls, v):
        """Validate room name format"""
        if not v or len(v) < 3 or len(v) > 64:
            raise ValueError("Room name must be 3-64 characters")
        # Allow alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Room name can only contain letters, numbers, hyphens, and underscores")
        return v
    
    @validator('participant_name')  
    def validate_participant_name(cls, v):
        """Validate participant name format"""
        if not v or len(v) < 2 or len(v) > 64:
            raise ValueError("Participant name must be 2-64 characters")
        return v


class TranslatorTokenRequest(BaseModel):
    """Request model for translator worker token generation"""
    room_name: str
    worker_id: str
    target_languages: List[str]
    ttl_hours: Optional[int] = 24
    
    @validator('target_languages')
    def validate_languages(cls, v):
        """Validate language codes"""
        if not v or len(v) == 0:
            raise ValueError("At least one target language is required")
        
        # Basic language code validation (2-5 character codes)
        import re
        for lang in v:
            if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', lang):
                logger.warning(f"Potentially invalid language code: {lang}")
        
        return v


class TurnCredentialsRequest(BaseModel):
    """Request model for TURN credentials generation"""
    username: str
    ttl_seconds: Optional[int] = 3600
    
    @validator('ttl_seconds')
    def validate_ttl(cls, v):
        """Validate TTL bounds"""
        if v < 300 or v > 86400:  # 5 minutes to 24 hours
            raise ValueError("TTL must be between 300 and 86400 seconds")
        return v


class TokenResponse(BaseModel):
    """Response model for token generation"""
    token: str
    expires_at: datetime
    participant_name: str
    room_name: str
    role: str
    metadata: Optional[Dict[str, Any]] = None


class TurnCredentialsResponse(BaseModel):
    """Response model for TURN credentials"""
    username: str
    password: str
    ttl: int
    uris: List[str]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    service: str


# Global JWT service instance
jwt_service: Optional[LiveKitJWTService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global jwt_service
    
    # Startup
    logger.info("Starting LiveKit JWT Authentication Service")
    try:
        jwt_service = create_jwt_service()
        logger.info("JWT service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize JWT service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down JWT Authentication Service")


# Create FastAPI app
app = FastAPI(
    title="LiveKit JWT Authentication Service",
    description="JWT token generation service for The HIVE translation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite dev server
        "http://localhost:3000",      # Alternative dev port
        "https://localhost:5173",     # HTTPS dev
        "https://localhost:3000",     # HTTPS dev alt
        "https://thehive.app",        # Production
        "https://www.thehive.app",    # Production www
        "https://*.vercel.app",       # Vercel deployments
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def get_jwt_service() -> LiveKitJWTService:
    """Dependency to get JWT service instance"""
    if jwt_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT service not initialized"
        )
    return jwt_service


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify API key from Authorization header"""
    api_key = os.getenv("AUTH_SERVICE_API_KEY")
    
    if not api_key:
        # Development mode - allow without auth
        if os.getenv("ENVIRONMENT") == "development":
            logger.warning("Running in development mode - API key verification disabled")
            return "development"
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return credentials.credentials


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        service="livekit-jwt-auth"
    )


@app.post("/token/room", response_model=TokenResponse)
async def generate_room_token(
    request: RoomTokenRequest,
    service: LiveKitJWTService = Depends(get_jwt_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate JWT token for room access
    
    This endpoint creates a properly scoped JWT token for participants
    to join LiveKit rooms with role-based permissions.
    """
    try:
        # Parse role
        role = ParticipantRole(request.role)
        
        # Generate token
        token = service.generate_room_token(
            room_name=request.room_name,
            participant_name=request.participant_name,
            role=role,
            metadata=request.metadata,
            ttl_hours=request.ttl_hours,
            allowed_languages=request.allowed_languages
        )
        
        # Calculate expiration
        import time
        ttl_hours = request.ttl_hours or 6
        expires_at = datetime.fromtimestamp(time.time() + (ttl_hours * 3600))
        
        logger.info(
            f"Generated room token: room={request.room_name} "
            f"participant={request.participant_name} role={request.role}"
        )
        
        return TokenResponse(
            token=token,
            expires_at=expires_at,
            participant_name=request.participant_name,
            room_name=request.room_name,
            role=request.role,
            metadata=request.metadata
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating room token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate token"
        )


@app.post("/token/translator", response_model=TokenResponse)
async def generate_translator_token(
    request: TranslatorTokenRequest,
    service: LiveKitJWTService = Depends(get_jwt_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate JWT token for translator workers
    
    This endpoint creates specialized tokens for translator worker processes
    that need to subscribe to all audio tracks and publish translated streams.
    """
    try:
        # Generate translator token
        token = service.generate_translator_token(
            room_name=request.room_name,
            worker_id=request.worker_id,
            target_languages=request.target_languages,
            ttl_hours=request.ttl_hours
        )
        
        # Calculate expiration
        import time
        expires_at = datetime.fromtimestamp(time.time() + (request.ttl_hours * 3600))
        
        logger.info(
            f"Generated translator token: room={request.room_name} "
            f"worker={request.worker_id} languages={request.target_languages}"
        )
        
        return TokenResponse(
            token=token,
            expires_at=expires_at,
            participant_name=f"translator-{request.worker_id}",
            room_name=request.room_name,
            role="translator",
            metadata={
                "workerId": request.worker_id,
                "targetLanguages": request.target_languages
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating translator token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate translator token"
        )


@app.post("/credentials/turn", response_model=TurnCredentialsResponse)
async def generate_turn_credentials(
    request: TurnCredentialsRequest,
    service: LiveKitJWTService = Depends(get_jwt_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate TURN server credentials
    
    This endpoint creates time-based TURN server credentials compatible
    with CoTURN's REST API authentication mechanism.
    """
    try:
        credentials = service.generate_turn_credentials(
            username=request.username,
            ttl_seconds=request.ttl_seconds
        )
        
        logger.info(f"Generated TURN credentials for user: {request.username}")
        
        return TurnCredentialsResponse(**credentials)
        
    except Exception as e:
        logger.error(f"Error generating TURN credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate TURN credentials"
        )


@app.post("/token/validate")
async def validate_token(
    token: str,
    service: LiveKitJWTService = Depends(get_jwt_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Validate JWT token and return decoded payload
    
    This endpoint validates token signatures and expiration,
    useful for debugging and monitoring.
    """
    try:
        payload = service.validate_token(token)
        return {"valid": True, "payload": payload}
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# Development/debugging endpoints
if os.getenv("ENVIRONMENT") == "development":
    
    @app.get("/dev/roles")
    async def list_roles():
        """List available participant roles (development only)"""
        return {
            "roles": [
                {
                    "name": role.value,
                    "permissions": service.ROLE_PERMISSIONS[role].__dict__
                }
                for role in ParticipantRole
                for service in [get_jwt_service()]
            ]
        }
    
    @app.post("/dev/token/quick")
    async def quick_token_generation(
        room: str,
        participant: str,
        role: str = "listener"
    ):
        """Quick token generation for development testing"""
        request = RoomTokenRequest(
            room_name=room,
            participant_name=participant,
            role=role
        )
        return await generate_room_token(request, get_jwt_service(), "development")


def create_app() -> FastAPI:
    """Factory function for creating the FastAPI app"""
    return app


if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8003"))
    debug = os.getenv("ENVIRONMENT") == "development"
    
    logger.info(f"Starting JWT Auth Service on {host}:{port}")
    
    # Run server
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
        access_log=True
    )