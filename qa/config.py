"""
QA Testing Configuration
Centralized configuration management for The HIVE QA testing framework
"""

import os
import json
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ServiceEndpoints:
    """Service endpoint configuration"""
    stt_service_url: str = "http://localhost:8001"
    mt_service_url: str = "http://localhost:8002"
    tts_service_url: str = "http://localhost:8003"
    livekit_url: str = "ws://localhost:7880"
    livekit_api_url: str = "http://localhost:7880"
    redis_url: str = "redis://localhost:6379"
    prometheus_url: str = "http://localhost:9090"
    grafana_url: str = "http://localhost:3001"
    jaeger_url: str = "http://localhost:16686"

@dataclass
class SLOTargets:
    """Service Level Objective targets"""
    ttft_p95_ms: float = 450.0
    caption_latency_p95_ms: float = 250.0
    retraction_rate_max: float = 0.05
    end_to_end_latency_p95_ms: float = 500.0
    success_rate_min: float = 0.95

@dataclass
class PerformanceTargets:
    """Performance testing targets"""
    max_cpu_usage_percent: float = 80.0
    max_memory_usage_percent: float = 85.0
    max_response_time_ms: float = 1000.0
    min_throughput_rps: float = 10.0
    max_concurrent_sessions: int = 16

@dataclass
class QualityTargets:
    """Quality assurance targets"""
    min_translation_accuracy_bleu: float = 0.5
    min_translation_accuracy_semantic: float = 0.7
    min_audio_quality_snr: float = 20.0
    min_audio_quality_pesq: float = 3.0
    max_word_error_rate: float = 0.15
    min_voice_naturalness: float = 3.5

@dataclass
class TestConfiguration:
    """Test execution configuration"""
    # Test modes
    quick_mode_sample_count: int = 20
    comprehensive_mode_sample_count: int = 100
    
    # Timeouts (seconds)
    test_timeout_seconds: int = 1800  # 30 minutes
    service_health_timeout_seconds: int = 30
    
    # Languages and pairs
    supported_languages: List[str] = None
    test_language_pairs: List[Tuple[str, str]] = None
    
    # Load testing
    load_test_ramp_up_seconds: int = 30
    load_test_sustained_seconds: int = 300
    load_test_session_duration_seconds: int = 180
    
    # Network testing
    network_test_conditions: List[str] = None
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = ["en", "es", "fr", "de", "ja", "zh"]
        
        if self.test_language_pairs is None:
            self.test_language_pairs = [
                ("en", "es"), ("en", "fr"), ("en", "de"), ("en", "ja"),
                ("es", "en"), ("fr", "en"), ("de", "en"), ("ja", "en"),
                ("es", "fr"), ("fr", "es")
            ]
        
        if self.network_test_conditions is None:
            self.network_test_conditions = [
                "baseline",
                "light_packet_loss",
                "moderate_latency",
                "combined_light"
            ]

class QAConfig:
    """Main QA configuration manager"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.services = ServiceEndpoints()
        self.slo_targets = SLOTargets()
        self.performance_targets = PerformanceTargets()
        self.quality_targets = QualityTargets()
        self.test_config = TestConfiguration()
        
        # Load configuration from various sources
        self._load_from_environment()
        
        if config_file:
            self._load_from_file(config_file)
        else:
            # Try to load default config file
            default_config = Path(__file__).parent / "qa_config.json"
            if default_config.exists():
                self._load_from_file(str(default_config))
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Service endpoints
        if os.getenv("STT_SERVICE_URL"):
            self.services.stt_service_url = os.getenv("STT_SERVICE_URL")
        if os.getenv("MT_SERVICE_URL"):
            self.services.mt_service_url = os.getenv("MT_SERVICE_URL")
        if os.getenv("TTS_SERVICE_URL"):
            self.services.tts_service_url = os.getenv("TTS_SERVICE_URL")
        if os.getenv("LIVEKIT_URL"):
            self.services.livekit_url = os.getenv("LIVEKIT_URL")
        
        # SLO targets
        if os.getenv("QA_TTFT_TARGET_MS"):
            self.slo_targets.ttft_p95_ms = float(os.getenv("QA_TTFT_TARGET_MS"))
        if os.getenv("QA_CAPTION_LATENCY_TARGET_MS"):
            self.slo_targets.caption_latency_p95_ms = float(os.getenv("QA_CAPTION_LATENCY_TARGET_MS"))
        if os.getenv("QA_RETRACTION_RATE_MAX"):
            self.slo_targets.retraction_rate_max = float(os.getenv("QA_RETRACTION_RATE_MAX"))
        
        # Test configuration
        if os.getenv("QA_SAMPLE_COUNT"):
            self.test_config.comprehensive_mode_sample_count = int(os.getenv("QA_SAMPLE_COUNT"))
        if os.getenv("QA_MAX_CONCURRENT"):
            self.performance_targets.max_concurrent_sessions = int(os.getenv("QA_MAX_CONCURRENT"))
        if os.getenv("QA_TEST_DURATION"):
            self.test_config.load_test_sustained_seconds = int(os.getenv("QA_TEST_DURATION"))
    
    def _load_from_file(self, config_file: str):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update service endpoints
            if "services" in config_data:
                for key, value in config_data["services"].items():
                    if hasattr(self.services, key):
                        setattr(self.services, key, value)
            
            # Update SLO targets
            if "slo_targets" in config_data:
                for key, value in config_data["slo_targets"].items():
                    if hasattr(self.slo_targets, key):
                        setattr(self.slo_targets, key, value)
            
            # Update performance targets
            if "performance_targets" in config_data:
                for key, value in config_data["performance_targets"].items():
                    if hasattr(self.performance_targets, key):
                        setattr(self.performance_targets, key, value)
            
            # Update quality targets
            if "quality_targets" in config_data:
                for key, value in config_data["quality_targets"].items():
                    if hasattr(self.quality_targets, key):
                        setattr(self.quality_targets, key, value)
            
            # Update test configuration
            if "test_config" in config_data:
                for key, value in config_data["test_config"].items():
                    if hasattr(self.test_config, key):
                        setattr(self.test_config, key, value)
                        
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file}: {e}")
    
    def get_slo_test_config(self, quick_mode: bool = False):
        """Get SLO test configuration"""
        from .slo_tests import SLOTestConfig
        
        return SLOTestConfig(
            ttft_target_ms=self.slo_targets.ttft_p95_ms,
            caption_latency_target_ms=self.slo_targets.caption_latency_p95_ms,
            retraction_rate_target=self.slo_targets.retraction_rate_max,
            sample_count=self.test_config.quick_mode_sample_count if quick_mode 
                        else self.test_config.comprehensive_mode_sample_count,
            test_duration_minutes=2 if quick_mode else 5,
            stt_service_url=self.services.stt_service_url,
            mt_service_url=self.services.mt_service_url,
            tts_service_url=self.services.tts_service_url,
            livekit_url=self.services.livekit_url
        )
    
    def get_load_test_config(self, quick_mode: bool = False):
        """Get load test configuration"""
        from .load_tests import LoadTestConfig
        
        return LoadTestConfig(
            max_concurrent_sessions=4 if quick_mode else self.performance_targets.max_concurrent_sessions,
            ramp_up_duration_seconds=15 if quick_mode else self.test_config.load_test_ramp_up_seconds,
            sustained_load_duration_seconds=30 if quick_mode else self.test_config.load_test_sustained_seconds,
            session_duration_seconds=60 if quick_mode else self.test_config.load_test_session_duration_seconds,
            max_cpu_usage_percent=self.performance_targets.max_cpu_usage_percent,
            max_memory_usage_percent=self.performance_targets.max_memory_usage_percent,
            max_response_time_ms=self.performance_targets.max_response_time_ms,
            min_success_rate=self.slo_targets.success_rate_min,
            stt_service_url=self.services.stt_service_url,
            mt_service_url=self.services.mt_service_url,
            tts_service_url=self.services.tts_service_url,
            livekit_url=self.services.livekit_url
        )
    
    def get_integration_test_config(self, quick_mode: bool = False):
        """Get integration test configuration"""
        from .integration_tests import IntegrationTestConfig
        
        return IntegrationTestConfig(
            test_duration_seconds=60 if quick_mode else 180,
            max_concurrent_participants=2 if quick_mode else 4,
            language_pairs=self.test_config.test_language_pairs[:2] if quick_mode 
                          else self.test_config.test_language_pairs,
            stt_service_url=self.services.stt_service_url,
            mt_service_url=self.services.mt_service_url,
            tts_service_url=self.services.tts_service_url,
            livekit_url=self.services.livekit_url,
            livekit_api_url=self.services.livekit_api_url
        )
    
    def get_quality_test_config(self, quick_mode: bool = False):
        """Get quality test configuration"""
        from .quality_tests import QualityTestConfig
        
        config = QualityTestConfig(
            stt_service_url=self.services.stt_service_url,
            mt_service_url=self.services.mt_service_url,
            tts_service_url=self.services.tts_service_url,
            min_translation_accuracy_bleu=self.quality_targets.min_translation_accuracy_bleu,
            min_translation_accuracy_semantic=self.quality_targets.min_translation_accuracy_semantic,
            min_audio_quality_snr=self.quality_targets.min_audio_quality_snr,
            min_audio_quality_pesq=self.quality_targets.min_audio_quality_pesq,
            max_word_error_rate=self.quality_targets.max_word_error_rate,
            min_voice_naturalness=self.quality_targets.min_voice_naturalness
        )
        
        if quick_mode:
            config.test_languages = self.test_config.supported_languages[:2]
            config.language_pairs = self.test_config.test_language_pairs[:2]
        else:
            config.test_languages = self.test_config.supported_languages
            config.language_pairs = self.test_config.test_language_pairs
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration to dictionary"""
        return {
            "services": {
                "stt_service_url": self.services.stt_service_url,
                "mt_service_url": self.services.mt_service_url,
                "tts_service_url": self.services.tts_service_url,
                "livekit_url": self.services.livekit_url,
                "livekit_api_url": self.services.livekit_api_url,
                "redis_url": self.services.redis_url
            },
            "slo_targets": {
                "ttft_p95_ms": self.slo_targets.ttft_p95_ms,
                "caption_latency_p95_ms": self.slo_targets.caption_latency_p95_ms,
                "retraction_rate_max": self.slo_targets.retraction_rate_max,
                "end_to_end_latency_p95_ms": self.slo_targets.end_to_end_latency_p95_ms,
                "success_rate_min": self.slo_targets.success_rate_min
            },
            "performance_targets": {
                "max_cpu_usage_percent": self.performance_targets.max_cpu_usage_percent,
                "max_memory_usage_percent": self.performance_targets.max_memory_usage_percent,
                "max_response_time_ms": self.performance_targets.max_response_time_ms,
                "max_concurrent_sessions": self.performance_targets.max_concurrent_sessions
            },
            "quality_targets": {
                "min_translation_accuracy_bleu": self.quality_targets.min_translation_accuracy_bleu,
                "min_translation_accuracy_semantic": self.quality_targets.min_translation_accuracy_semantic,
                "min_audio_quality_snr": self.quality_targets.min_audio_quality_snr,
                "min_audio_quality_pesq": self.quality_targets.min_audio_quality_pesq,
                "max_word_error_rate": self.quality_targets.max_word_error_rate,
                "min_voice_naturalness": self.quality_targets.min_voice_naturalness
            },
            "test_config": {
                "quick_mode_sample_count": self.test_config.quick_mode_sample_count,
                "comprehensive_mode_sample_count": self.test_config.comprehensive_mode_sample_count,
                "supported_languages": self.test_config.supported_languages,
                "test_language_pairs": self.test_config.test_language_pairs,
                "load_test_ramp_up_seconds": self.test_config.load_test_ramp_up_seconds,
                "load_test_sustained_seconds": self.test_config.load_test_sustained_seconds,
                "network_test_conditions": self.test_config.network_test_conditions
            }
        }
    
    def save_to_file(self, filename: str):
        """Save configuration to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate_services(self) -> Dict[str, bool]:
        """Validate service endpoints are accessible"""
        import asyncio
        import aiohttp
        
        async def check_service(url: str) -> bool:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        return response.status < 400
            except:
                return False
        
        async def check_all():
            services = {
                "STT": self.services.stt_service_url + "/health",
                "MT": self.services.mt_service_url + "/health", 
                "TTS": self.services.tts_service_url + "/health",
                "LiveKit": self.services.livekit_api_url + "/"
            }
            
            results = {}
            for name, url in services.items():
                results[name] = await check_service(url)
            
            return results
        
        return asyncio.run(check_all())

# Global configuration instance
_global_config = None

def get_qa_config(config_file: Optional[str] = None) -> QAConfig:
    """Get global QA configuration instance"""
    global _global_config
    
    if _global_config is None or config_file is not None:
        _global_config = QAConfig(config_file)
    
    return _global_config

def create_default_config_file(filename: str = "qa_config.json"):
    """Create a default configuration file"""
    config = QAConfig()
    config.save_to_file(filename)
    print(f"Default configuration file created: {filename}")

if __name__ == "__main__":
    # Create default config file if run directly
    import sys
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "qa_config.json"
    
    create_default_config_file(filename)