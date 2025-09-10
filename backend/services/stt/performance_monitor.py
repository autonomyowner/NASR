"""
Performance Monitoring for STT Service
Tracks latency, accuracy, and system metrics
"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict
import statistics
import logging
import psutil
import torch

logger = logging.getLogger(__name__)


@dataclass
class LatencyMeasurement:
    """Individual latency measurement"""
    timestamp: float
    processing_time_ms: float
    chunk_duration_ms: float
    queue_time_ms: float = 0.0
    model_time_ms: float = 0.0
    post_processing_time_ms: float = 0.0
    session_id: str = ""


@dataclass
class STTMetrics:
    """Complete STT performance metrics"""
    # Latency metrics
    avg_processing_time: float = 0.0
    p95_processing_time: float = 0.0
    p99_processing_time: float = 0.0
    min_processing_time: float = 0.0
    max_processing_time: float = 0.0
    
    # Throughput metrics
    chunks_per_second: float = 0.0
    total_chunks_processed: int = 0
    active_sessions: int = 0
    
    # Quality metrics
    average_confidence: float = 0.0
    speech_detection_rate: float = 0.0
    error_rate: float = 0.0
    
    # System metrics
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    gpu_usage_percent: float = 0.0
    gpu_memory_mb: float = 0.0
    
    # LocalAgreement-2 metrics
    word_retraction_rate: float = 0.0
    confirmation_rate: float = 0.0
    agreement_efficiency: float = 0.0


class PerformanceMonitor:
    """Real-time performance monitoring for STT service"""
    
    def __init__(self, history_size: int = 1000, metrics_window_seconds: int = 60):
        self.history_size = history_size
        self.metrics_window = metrics_window_seconds
        
        # Thread-safe data structures
        self._lock = threading.RLock()
        
        # Latency tracking
        self.latency_history: deque = deque(maxlen=history_size)
        self.processing_times: deque = deque(maxlen=history_size)
        
        # Quality tracking
        self.confidence_scores: deque = deque(maxlen=history_size)
        self.speech_chunks = 0
        self.total_chunks = 0
        self.error_count = 0
        
        # Session tracking
        self.active_sessions: Dict[str, float] = {}  # session_id -> start_time
        self.session_metrics: Dict[str, List] = defaultdict(list)
        
        # LocalAgreement-2 tracking
        self.word_retractions = 0
        self.total_words_confirmed = 0
        self.total_word_candidates = 0
        
        # System monitoring
        self.start_time = time.time()
        self.last_metrics_update = time.time()
        
        logger.info(f"PerformanceMonitor initialized with {history_size} sample history")
    
    def record_processing_time(
        self, 
        processing_time_ms: float,
        chunk_duration_ms: float = 0.0,
        session_id: str = "",
        confidence: float = 0.0,
        has_speech: bool = True,
        queue_time_ms: float = 0.0,
        model_time_ms: float = 0.0
    ):
        """Record processing time and related metrics"""
        with self._lock:
            timestamp = time.time()
            
            # Record latency
            measurement = LatencyMeasurement(
                timestamp=timestamp,
                processing_time_ms=processing_time_ms,
                chunk_duration_ms=chunk_duration_ms,
                queue_time_ms=queue_time_ms,
                model_time_ms=model_time_ms,
                session_id=session_id
            )
            
            self.latency_history.append(measurement)
            self.processing_times.append(processing_time_ms)
            
            # Record quality metrics
            if confidence > 0:
                self.confidence_scores.append(confidence)
            
            # Track speech detection
            self.total_chunks += 1
            if has_speech:
                self.speech_chunks += 1
            
            # Session-specific metrics
            if session_id:
                self.session_metrics[session_id].append(measurement)
    
    def record_error(self, error_type: str = "processing", session_id: str = ""):
        """Record processing error"""
        with self._lock:
            self.error_count += 1
            logger.warning(f"STT error recorded: {error_type} (session: {session_id})")
    
    def record_session_start(self, session_id: str):
        """Record new session start"""
        with self._lock:
            self.active_sessions[session_id] = time.time()
            logger.debug(f"Session started: {session_id}")
    
    def record_session_end(self, session_id: str):
        """Record session end and cleanup"""
        with self._lock:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Keep session metrics for a while for analysis
            # but limit to prevent memory growth
            if session_id in self.session_metrics:
                if len(self.session_metrics) > 100:  # Keep last 100 sessions
                    oldest_session = min(self.session_metrics.keys())
                    del self.session_metrics[oldest_session]
            
            logger.debug(f"Session ended: {session_id}")
    
    def record_word_confirmation(self, candidates_count: int, confirmed_count: int, retractions: int = 0):
        """Record LocalAgreement-2 word processing metrics"""
        with self._lock:
            self.total_word_candidates += candidates_count
            self.total_words_confirmed += confirmed_count
            self.word_retractions += retractions
    
    def get_current_metrics(self) -> STTMetrics:
        """Get current performance metrics"""
        with self._lock:
            current_time = time.time()
            
            # Calculate latency metrics
            recent_times = [
                m.processing_time_ms for m in self.latency_history
                if current_time - m.timestamp < self.metrics_window
            ]
            
            if recent_times:
                avg_time = statistics.mean(recent_times)
                p95_time = self._percentile(recent_times, 0.95)
                p99_time = self._percentile(recent_times, 0.99)
                min_time = min(recent_times)
                max_time = max(recent_times)
            else:
                avg_time = p95_time = p99_time = min_time = max_time = 0.0
            
            # Calculate throughput
            recent_chunks = len(recent_times)
            chunks_per_second = recent_chunks / self.metrics_window if recent_chunks > 0 else 0.0
            
            # Calculate quality metrics
            recent_confidences = [
                c for c in self.confidence_scores
                if len(self.confidence_scores) > 0
            ]
            avg_confidence = statistics.mean(recent_confidences) if recent_confidences else 0.0
            
            speech_rate = self.speech_chunks / self.total_chunks if self.total_chunks > 0 else 0.0
            error_rate = self.error_count / self.total_chunks if self.total_chunks > 0 else 0.0
            
            # System metrics
            system_metrics = self._get_system_metrics()
            
            # LocalAgreement-2 metrics
            retraction_rate = (
                self.word_retractions / self.total_words_confirmed 
                if self.total_words_confirmed > 0 else 0.0
            )
            confirmation_rate = (
                self.total_words_confirmed / self.total_word_candidates 
                if self.total_word_candidates > 0 else 0.0
            )
            agreement_efficiency = 1.0 - retraction_rate  # Higher is better
            
            return STTMetrics(
                # Latency
                avg_processing_time=avg_time,
                p95_processing_time=p95_time,
                p99_processing_time=p99_time,
                min_processing_time=min_time,
                max_processing_time=max_time,
                
                # Throughput
                chunks_per_second=chunks_per_second,
                total_chunks_processed=self.total_chunks,
                active_sessions=len(self.active_sessions),
                
                # Quality
                average_confidence=avg_confidence,
                speech_detection_rate=speech_rate,
                error_rate=error_rate,
                
                # System
                cpu_usage_percent=system_metrics["cpu"],
                memory_usage_mb=system_metrics["memory"],
                gpu_usage_percent=system_metrics["gpu_usage"],
                gpu_memory_mb=system_metrics["gpu_memory"],
                
                # LocalAgreement-2
                word_retraction_rate=retraction_rate,
                confirmation_rate=confirmation_rate,
                agreement_efficiency=agreement_efficiency
            )
    
    def get_session_metrics(self, session_id: str) -> Optional[Dict]:
        """Get metrics for specific session"""
        with self._lock:
            if session_id not in self.session_metrics:
                return None
            
            measurements = self.session_metrics[session_id]
            if not measurements:
                return None
            
            times = [m.processing_time_ms for m in measurements]
            
            return {
                "session_id": session_id,
                "total_chunks": len(measurements),
                "avg_processing_time": statistics.mean(times),
                "p95_processing_time": self._percentile(times, 0.95),
                "min_processing_time": min(times),
                "max_processing_time": max(times),
                "duration_seconds": measurements[-1].timestamp - measurements[0].timestamp,
                "is_active": session_id in self.active_sessions
            }
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        metrics = self.get_current_metrics()
        
        prometheus_lines = [
            f"stt_processing_time_ms_avg {metrics.avg_processing_time}",
            f"stt_processing_time_ms_p95 {metrics.p95_processing_time}",
            f"stt_processing_time_ms_p99 {metrics.p99_processing_time}",
            f"stt_chunks_per_second {metrics.chunks_per_second}",
            f"stt_total_chunks {metrics.total_chunks_processed}",
            f"stt_active_sessions {metrics.active_sessions}",
            f"stt_average_confidence {metrics.average_confidence}",
            f"stt_speech_detection_rate {metrics.speech_detection_rate}",
            f"stt_error_rate {metrics.error_rate}",
            f"stt_cpu_usage_percent {metrics.cpu_usage_percent}",
            f"stt_memory_usage_mb {metrics.memory_usage_mb}",
            f"stt_gpu_usage_percent {metrics.gpu_usage_percent}",
            f"stt_gpu_memory_mb {metrics.gpu_memory_mb}",
            f"stt_word_retraction_rate {metrics.word_retraction_rate}",
            f"stt_confirmation_rate {metrics.confirmation_rate}",
            f"stt_agreement_efficiency {metrics.agreement_efficiency}"
        ]
        
        return "\n".join(prometheus_lines)
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile
        f = int(k)
        c = k - f
        
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        else:
            return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
    
    def _get_system_metrics(self) -> Dict:
        """Get current system resource usage"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            
            # GPU metrics (if available)
            gpu_usage = 0.0
            gpu_memory = 0.0
            
            if torch.cuda.is_available():
                try:
                    gpu_memory = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
                    # GPU utilization requires nvidia-ml-py
                    try:
                        import pynvml
                        pynvml.nvmlInit()
                        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        info = pynvml.nvmlDeviceGetUtilizationRates(handle)
                        gpu_usage = info.gpu
                    except ImportError:
                        pass
                except Exception as e:
                    logger.debug(f"GPU metrics unavailable: {e}")
            
            return {
                "cpu": cpu_percent,
                "memory": memory_mb,
                "gpu_usage": gpu_usage,
                "gpu_memory": gpu_memory
            }
            
        except Exception as e:
            logger.error(f"System metrics error: {e}")
            return {"cpu": 0.0, "memory": 0.0, "gpu_usage": 0.0, "gpu_memory": 0.0}
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        with self._lock:
            self.latency_history.clear()
            self.processing_times.clear()
            self.confidence_scores.clear()
            self.session_metrics.clear()
            self.active_sessions.clear()
            
            self.speech_chunks = 0
            self.total_chunks = 0
            self.error_count = 0
            self.word_retractions = 0
            self.total_words_confirmed = 0
            self.total_word_candidates = 0
            
            self.start_time = time.time()
            
            logger.info("Performance metrics reset")
    
    def get_stats(self) -> Dict:
        """Get basic statistics for health checks"""
        metrics = self.get_current_metrics()
        
        return {
            "avg_processing_time": metrics.avg_processing_time,
            "p95_processing_time": metrics.p95_processing_time,
            "total_chunks": metrics.total_chunks_processed,
            "error_rate": metrics.error_rate,
            "active_sessions": metrics.active_sessions,
            "uptime_seconds": time.time() - self.start_time
        }