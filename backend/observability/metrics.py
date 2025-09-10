"""
Comprehensive Metrics Collection for The HIVE Translation Pipeline
Implements custom Prometheus metrics for SLO monitoring and performance analytics
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from prometheus_client import CollectorRegistry, Histogram, Counter, Gauge, Summary, Info
from prometheus_client.exposition import generate_latest
import threading
import statistics
from datetime import datetime, timedelta

class TranslationMetrics:
    """
    Custom metrics collector for The HIVE translation system
    Tracks SLO-critical metrics: TTFT, caption latency, word retractions
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.registry = CollectorRegistry()
        self._setup_metrics()
        
        # Thread-safe metric storage
        self._lock = threading.Lock()
        self._ttft_samples: List[float] = []
        self._caption_latency_samples: List[float] = []
        self._word_stats = {"total": 0, "retractions": 0}
        
    def _setup_metrics(self):
        """Initialize all Prometheus metrics"""
        
        # Time-to-First-Token (TTFT) - Critical SLO metric
        self.ttft_histogram = Histogram(
            'translation_ttft_duration_seconds',
            'Time from audio input to first translated token',
            buckets=[0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.75, 1.0, 2.0],
            labelnames=['language_pair', 'model_version'],
            registry=self.registry
        )
        
        # Caption Latency - Critical SLO metric
        self.caption_latency_histogram = Histogram(
            'caption_latency_seconds',
            'Time from speech to caption display',
            buckets=[0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 1.0],
            labelnames=['language_pair'],
            registry=self.registry
        )
        
        # Word-level tracking for retraction rates
        self.words_total = Counter(
            'words_total',
            'Total words processed',
            labelnames=['service', 'language'],
            registry=self.registry
        )
        
        self.word_retractions = Counter(
            'word_retractions_total', 
            'Words that were retracted/corrected',
            labelnames=['service', 'language', 'retraction_type'],
            registry=self.registry
        )
        
        # Service-level performance metrics
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            labelnames=['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            labelnames=['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        # Audio quality metrics
        self.audio_quality_score = Gauge(
            'audio_quality_score',
            'Audio quality score (0-1)',
            labelnames=['direction', 'codec'],
            registry=self.registry
        )
        
        # Translation quality metrics
        self.translation_confidence = Histogram(
            'translation_confidence_score',
            'Translation confidence scores',
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            labelnames=['service', 'language_pair'],
            registry=self.registry
        )
        
        # Pipeline stage latencies
        self.stt_latency = Histogram(
            'stt_processing_duration_seconds',
            'STT processing duration',
            buckets=[0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5],
            labelnames=['model', 'chunk_size'],
            registry=self.registry
        )
        
        self.mt_latency = Histogram(
            'mt_processing_duration_seconds',
            'MT processing duration', 
            buckets=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5],
            labelnames=['model', 'language_pair'],
            registry=self.registry
        )
        
        self.tts_latency = Histogram(
            'tts_processing_duration_seconds',
            'TTS processing duration',
            buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0],
            labelnames=['engine', 'voice_id'],
            registry=self.registry
        )
        
        # LiveKit/WebRTC metrics
        self.participant_count = Gauge(
            'livekit_participants_active',
            'Active participants in translation session',
            labelnames=['room_id'],
            registry=self.registry
        )
        
        self.audio_packets_sent = Counter(
            'livekit_audio_packets_sent_total',
            'Audio packets sent via LiveKit',
            labelnames=['track_type', 'language'],
            registry=self.registry
        )
        
        self.audio_packets_received = Counter(
            'livekit_audio_packets_received_total',
            'Audio packets received via LiveKit',
            labelnames=['track_type', 'language'],
            registry=self.registry
        )
        
        # System resource metrics
        self.cpu_usage = Gauge(
            'service_cpu_usage_percent',
            'CPU usage percentage',
            labelnames=['service'],
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'service_memory_usage_bytes',
            'Memory usage in bytes',
            labelnames=['service'],
            registry=self.registry
        )
        
        self.gpu_usage = Gauge(
            'service_gpu_usage_percent',
            'GPU usage percentage', 
            labelnames=['service', 'gpu_id'],
            registry=self.registry
        )
        
        # Service health metrics
        self.service_up = Gauge(
            'service_up',
            'Service health status (1=up, 0=down)',
            labelnames=['service'],
            registry=self.registry
        )
        
        self.last_successful_request = Gauge(
            'last_successful_request_timestamp',
            'Timestamp of last successful request',
            labelnames=['service'],
            registry=self.registry
        )
        
    def record_ttft(self, duration_seconds: float, language_pair: str, model_version: str):
        """Record Time-to-First-Token measurement"""
        self.ttft_histogram.labels(
            language_pair=language_pair,
            model_version=model_version
        ).observe(duration_seconds)
        
        with self._lock:
            self._ttft_samples.append(duration_seconds)
            # Keep only recent samples for local percentile calculation
            if len(self._ttft_samples) > 1000:
                self._ttft_samples = self._ttft_samples[-500:]
    
    def record_caption_latency(self, duration_seconds: float, language_pair: str):
        """Record caption display latency"""
        self.caption_latency_histogram.labels(
            language_pair=language_pair
        ).observe(duration_seconds)
        
        with self._lock:
            self._caption_latency_samples.append(duration_seconds)
            if len(self._caption_latency_samples) > 1000:
                self._caption_latency_samples = self._caption_latency_samples[-500:]
    
    def record_word_processed(self, language: str, service: str = "stt"):
        """Record a word being processed"""
        self.words_total.labels(service=service, language=language).inc()
        
        with self._lock:
            self._word_stats["total"] += 1
    
    def record_word_retraction(self, language: str, retraction_type: str = "correction", service: str = "stt"):
        """Record a word retraction/correction"""
        self.word_retractions.labels(
            service=service,
            language=language,
            retraction_type=retraction_type
        ).inc()
        
        with self._lock:
            self._word_stats["retractions"] += 1
    
    def record_stt_processing(self, duration_seconds: float, model: str, chunk_size: str):
        """Record STT processing time"""
        self.stt_latency.labels(model=model, chunk_size=chunk_size).observe(duration_seconds)
    
    def record_mt_processing(self, duration_seconds: float, model: str, language_pair: str):
        """Record MT processing time"""
        self.mt_latency.labels(model=model, language_pair=language_pair).observe(duration_seconds)
    
    def record_tts_processing(self, duration_seconds: float, engine: str, voice_id: str):
        """Record TTS processing time"""
        self.tts_latency.labels(engine=engine, voice_id=voice_id).observe(duration_seconds)
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float):
        """Record HTTP request metrics"""
        labels = {'method': method, 'endpoint': endpoint, 'status_code': str(status_code)}
        self.requests_total.labels(**labels).inc()
        self.request_duration.labels(**labels).observe(duration_seconds)
    
    def update_participant_count(self, room_id: str, count: int):
        """Update active participant count"""
        self.participant_count.labels(room_id=room_id).set(count)
    
    def update_audio_quality(self, score: float, direction: str, codec: str):
        """Update audio quality score"""
        self.audio_quality_score.labels(direction=direction, codec=codec).set(score)
    
    def record_translation_confidence(self, score: float, service: str, language_pair: str):
        """Record translation confidence score"""
        self.translation_confidence.labels(service=service, language_pair=language_pair).observe(score)
    
    def update_resource_usage(self, cpu_percent: float, memory_bytes: int, gpu_percent: float = None, gpu_id: str = "0"):
        """Update system resource usage"""
        self.cpu_usage.labels(service=self.service_name).set(cpu_percent)
        self.memory_usage.labels(service=self.service_name).set(memory_bytes)
        if gpu_percent is not None:
            self.gpu_usage.labels(service=self.service_name, gpu_id=gpu_id).set(gpu_percent)
    
    def update_service_health(self, is_healthy: bool):
        """Update service health status"""
        self.service_up.labels(service=self.service_name).set(1 if is_healthy else 0)
        if is_healthy:
            self.last_successful_request.labels(service=self.service_name).set(time.time())
    
    def get_slo_metrics(self) -> Dict[str, Any]:
        """Get current SLO metric values"""
        with self._lock:
            ttft_p95 = statistics.quantiles(self._ttft_samples, n=20)[18] if len(self._ttft_samples) >= 20 else 0
            caption_p95 = statistics.quantiles(self._caption_latency_samples, n=20)[18] if len(self._caption_latency_samples) >= 20 else 0
            retraction_rate = (self._word_stats["retractions"] / max(self._word_stats["total"], 1)) * 100
            
            return {
                "ttft_p95_ms": ttft_p95 * 1000,
                "caption_latency_p95_ms": caption_p95 * 1000,
                "word_retraction_rate_percent": retraction_rate,
                "slo_status": {
                    "ttft_within_target": ttft_p95 <= 0.45,  # 450ms
                    "caption_within_target": caption_p95 <= 0.25,  # 250ms
                    "retractions_within_target": retraction_rate < 5.0
                }
            }
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')

# Global metrics instances
_service_metrics: Dict[str, TranslationMetrics] = {}

def get_metrics(service_name: str) -> TranslationMetrics:
    """Get or create metrics collector for service"""
    if service_name not in _service_metrics:
        _service_metrics[service_name] = TranslationMetrics(service_name)
    return _service_metrics[service_name]

def metrics_middleware(service_name: str):
    """HTTP middleware for automatic request metrics collection"""
    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            start_time = time.time()
            metrics = get_metrics(service_name)
            
            try:
                response = await func(request, *args, **kwargs)
                status_code = getattr(response, 'status_code', 200)
                
                metrics.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=status_code,
                    duration_seconds=time.time() - start_time
                )
                
                return response
                
            except Exception as e:
                metrics.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=500,
                    duration_seconds=time.time() - start_time
                )
                raise
        
        return wrapper
    return decorator

# Metric collection tasks for resource monitoring
async def collect_system_metrics(service_name: str, interval_seconds: int = 15):
    """Background task to collect system resource metrics"""
    import psutil
    import GPUtil
    
    metrics = get_metrics(service_name)
    
    while True:
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # GPU (if available)
            try:
                gpus = GPUtil.getGPUs()
                gpu_percent = gpus[0].load * 100 if gpus else None
            except:
                gpu_percent = None
            
            metrics.update_resource_usage(
                cpu_percent=cpu_percent,
                memory_bytes=memory.used,
                gpu_percent=gpu_percent
            )
            
            await asyncio.sleep(interval_seconds)
            
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
            await asyncio.sleep(interval_seconds)