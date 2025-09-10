"""
Configuration management for The HIVE translation system
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

@dataclass
class ServiceConfig:
    """Configuration for external services"""
    stt_url: str
    mt_url: str
    tts_url: str
    livekit_url: str
    livekit_api_key: str
    livekit_secret: str

@dataclass
class ModelConfig:
    """ML model configuration"""
    stt_model: str = "base"
    stt_language: str = "auto"
    mt_models: Dict[str, str] = None
    tts_voices: Dict[str, str] = None
    
    def __post_init__(self):
        if self.mt_models is None:
            self.mt_models = {
                "en-es": "Helsinki-NLP/opus-mt-en-es",
                "en-fr": "Helsinki-NLP/opus-mt-en-fr",
                "en-de": "Helsinki-NLP/opus-mt-en-de",
                "es-en": "Helsinki-NLP/opus-mt-es-en",
                "fr-en": "Helsinki-NLP/opus-mt-fr-en",
                "de-en": "Helsinki-NLP/opus-mt-de-en"
            }
            
        if self.tts_voices is None:
            self.tts_voices = {
                "en": "en-us-female-1",
                "es": "es-mx-female-1", 
                "fr": "fr-fr-male-1",
                "de": "de-de-female-1",
                "it": "it-it-male-1",
                "pt": "pt-br-female-1"
            }

@dataclass
class PerformanceConfig:
    """Performance and latency configuration"""
    chunk_duration_ms: int = 250
    context_length: int = 512
    max_concurrent_sessions: int = 4
    stt_timeout_ms: int = 5000
    mt_timeout_ms: int = 2000
    tts_timeout_ms: int = 5000
    
    # SLO targets
    ttft_target_ms: int = 450
    caption_latency_target_ms: int = 250
    max_retraction_rate: float = 0.05

@dataclass  
class SecurityConfig:
    """Security and authentication configuration"""
    jwt_secret: str
    token_expiry_hours: int = 24
    allowed_origins: List[str] = None
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["https://localhost:3000", "https://thehive.app"]

@dataclass
class ObservabilityConfig:
    """Monitoring and observability configuration"""
    jaeger_endpoint: Optional[str] = None
    prometheus_port: int = 9090
    log_level: str = "INFO"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    sampling_rate: float = 0.1

class Config:
    """Main configuration class that loads and validates all settings"""
    
    def __init__(self):
        self.services = self._load_service_config()
        self.models = self._load_model_config()
        self.performance = self._load_performance_config()
        self.security = self._load_security_config()
        self.observability = self._load_observability_config()
        
    def _load_service_config(self) -> ServiceConfig:
        """Load service configuration from environment"""
        return ServiceConfig(
            stt_url=self._get_required_env("STT_SERVICE_URL"),
            mt_url=self._get_required_env("MT_SERVICE_URL"),
            tts_url=self._get_required_env("TTS_SERVICE_URL"),
            livekit_url=self._get_required_env("LIVEKIT_URL"),
            livekit_api_key=self._get_required_env("LIVEKIT_API_KEY"),
            livekit_secret=self._get_required_env("LIVEKIT_SECRET")
        )
    
    def _load_model_config(self) -> ModelConfig:
        """Load model configuration from environment"""
        return ModelConfig(
            stt_model=os.getenv("STT_MODEL", "base"),
            stt_language=os.getenv("STT_LANGUAGE", "auto")
        )
    
    def _load_performance_config(self) -> PerformanceConfig:
        """Load performance configuration from environment"""
        return PerformanceConfig(
            chunk_duration_ms=int(os.getenv("CHUNK_DURATION_MS", "250")),
            context_length=int(os.getenv("CONTEXT_LENGTH", "512")),
            max_concurrent_sessions=int(os.getenv("MAX_CONCURRENT_SESSIONS", "4")),
            stt_timeout_ms=int(os.getenv("STT_TIMEOUT_MS", "5000")),
            mt_timeout_ms=int(os.getenv("MT_TIMEOUT_MS", "2000")),
            tts_timeout_ms=int(os.getenv("TTS_TIMEOUT_MS", "5000")),
            ttft_target_ms=int(os.getenv("TTFT_TARGET_MS", "450")),
            caption_latency_target_ms=int(os.getenv("CAPTION_LATENCY_TARGET_MS", "250")),
            max_retraction_rate=float(os.getenv("MAX_RETRACTION_RATE", "0.05"))
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration from environment"""
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        if not allowed_origins or allowed_origins == [""]:
            allowed_origins = None
            
        return SecurityConfig(
            jwt_secret=self._get_required_env("JWT_SECRET"),
            token_expiry_hours=int(os.getenv("TOKEN_EXPIRY_HOURS", "24")),
            allowed_origins=allowed_origins,
            tls_cert_path=os.getenv("TLS_CERT_PATH"),
            tls_key_path=os.getenv("TLS_KEY_PATH")
        )
    
    def _load_observability_config(self) -> ObservabilityConfig:
        """Load observability configuration from environment"""
        return ObservabilityConfig(
            jaeger_endpoint=os.getenv("JAEGER_ENDPOINT"),
            prometheus_port=int(os.getenv("PROMETHEUS_PORT", "9090")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            tracing_enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
            sampling_rate=float(os.getenv("TRACING_SAMPLING_RATE", "0.1"))
        )
    
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate URLs
        service_urls = [
            ("STT_SERVICE_URL", self.services.stt_url),
            ("MT_SERVICE_URL", self.services.mt_url),
            ("TTS_SERVICE_URL", self.services.tts_url),
            ("LIVEKIT_URL", self.services.livekit_url)
        ]
        
        for name, url in service_urls:
            if not url.startswith(("http://", "https://", "ws://", "wss://")):
                errors.append(f"{name} must be a valid URL: {url}")
        
        # Validate performance settings
        if self.performance.chunk_duration_ms < 100 or self.performance.chunk_duration_ms > 1000:
            errors.append("CHUNK_DURATION_MS must be between 100 and 1000ms")
            
        if self.performance.ttft_target_ms < 100:
            errors.append("TTFT_TARGET_MS must be at least 100ms")
            
        if self.performance.max_retraction_rate < 0 or self.performance.max_retraction_rate > 1:
            errors.append("MAX_RETRACTION_RATE must be between 0 and 1")
        
        # Validate security settings
        if len(self.security.jwt_secret) < 32:
            errors.append("JWT_SECRET must be at least 32 characters long")
            
        # Validate TLS configuration
        if self.security.tls_cert_path and not Path(self.security.tls_cert_path).exists():
            errors.append(f"TLS certificate file not found: {self.security.tls_cert_path}")
            
        if self.security.tls_key_path and not Path(self.security.tls_key_path).exists():
            errors.append(f"TLS key file not found: {self.security.tls_key_path}")
        
        return errors

# Global config instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
        
        # Validate configuration
        errors = _config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    return _config

def reload_config():
    """Force reload of configuration (useful for testing)"""
    global _config
    _config = None
    return get_config()