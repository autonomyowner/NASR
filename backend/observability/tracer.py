"""
Distributed Tracing Infrastructure for The HIVE Translation Pipeline
Implements end-to-end tracing across STT→MT→TTS services with correlation IDs
"""

import time
import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
import threading
from datetime import datetime, timezone

# Thread-local storage for trace context
_trace_context = threading.local()

@dataclass
class TraceSpan:
    """Represents a single span in the translation pipeline trace"""
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    operation: str
    service: str
    timestamp: str
    duration_ms: Optional[float]
    metadata: Dict[str, Any]
    status: str = "started"  # started, completed, error
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class TranslationTracer:
    """
    Distributed tracer for The HIVE translation pipeline
    Tracks end-to-end latency from audio capture to translated output
    """
    
    def __init__(self, service_name: str, jaeger_endpoint: str = "http://localhost:14268/api/traces"):
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint
        self.spans: Dict[str, TraceSpan] = {}
        
        # Initialize OpenTelemetry
        self._setup_opentelemetry()
        
    def _setup_opentelemetry(self):
        """Configure OpenTelemetry with Jaeger exporter"""
        resource = Resource.create({"service.name": self.service_name})
        trace.set_tracer_provider(TracerProvider(resource=resource))
        
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(__name__)
    
    def create_trace(self, operation: str, metadata: Dict[str, Any] = None) -> str:
        """Create new trace for translation session"""
        trace_id = str(uuid.uuid4())
        span_id = f"{operation}_{int(time.time() * 1000)}"
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=None,
            operation=operation,
            service=self.service_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=None,
            metadata=metadata or {}
        )
        
        self.spans[span_id] = span
        _trace_context.current_trace_id = trace_id
        _trace_context.current_span_id = span_id
        
        return trace_id
    
    def start_span(self, operation: str, parent_span_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """Start a new span within current trace"""
        trace_id = getattr(_trace_context, 'current_trace_id', str(uuid.uuid4()))
        span_id = f"{operation}_{int(time.time() * 1000000)}"  # Microsecond precision
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_span_id or getattr(_trace_context, 'current_span_id', None),
            operation=operation,
            service=self.service_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=None,
            metadata=metadata or {}
        )
        
        self.spans[span_id] = span
        _trace_context.current_span_id = span_id
        
        # Create OpenTelemetry span
        with self.tracer.start_as_current_span(operation) as otel_span:
            otel_span.set_attributes({
                "trace.id": trace_id,
                "span.id": span_id,
                "service.name": self.service_name,
                **(metadata or {})
            })
        
        return span_id
    
    def finish_span(self, span_id: str, status: str = "completed", metadata: Dict[str, Any] = None):
        """Complete a span with final status and metadata"""
        if span_id not in self.spans:
            return
            
        span = self.spans[span_id]
        start_time = datetime.fromisoformat(span.timestamp.replace('Z', '+00:00'))
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        span.duration_ms = duration_ms
        span.status = status
        if metadata:
            span.metadata.update(metadata)
    
    def get_trace_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get complete trace summary with all spans"""
        trace_spans = [span for span in self.spans.values() if span.trace_id == trace_id]
        trace_spans.sort(key=lambda x: x.timestamp)
        
        if not trace_spans:
            return {}
            
        start_time = datetime.fromisoformat(trace_spans[0].timestamp.replace('Z', '+00:00'))
        end_time = start_time
        
        for span in trace_spans:
            if span.duration_ms:
                span_end = datetime.fromisoformat(span.timestamp.replace('Z', '+00:00')) + \
                          timedelta(milliseconds=span.duration_ms)
                if span_end > end_time:
                    end_time = span_end
        
        total_duration_ms = (end_time - start_time).total_seconds() * 1000
        
        return {
            "trace_id": trace_id,
            "total_duration_ms": total_duration_ms,
            "span_count": len(trace_spans),
            "spans": [span.to_dict() for span in trace_spans],
            "start_timestamp": start_time.isoformat(),
            "end_timestamp": end_time.isoformat()
        }
    
    @contextmanager
    def trace_operation(self, operation: str, metadata: Dict[str, Any] = None):
        """Context manager for automatic span lifecycle management"""
        span_id = self.start_span(operation, metadata=metadata)
        start_time = time.time()
        
        try:
            yield span_id
            self.finish_span(span_id, "completed", {"duration_ms": (time.time() - start_time) * 1000})
        except Exception as e:
            self.finish_span(span_id, "error", {
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            })
            raise

# Global tracer instances for each service
_service_tracers: Dict[str, TranslationTracer] = {}

def get_tracer(service_name: str) -> TranslationTracer:
    """Get or create tracer for service"""
    if service_name not in _service_tracers:
        _service_tracers[service_name] = TranslationTracer(service_name)
    return _service_tracers[service_name]

def trace_translation_pipeline(func):
    """Decorator for tracing translation pipeline operations"""
    def wrapper(*args, **kwargs):
        service_name = kwargs.get('service_name', 'unknown')
        operation = kwargs.get('operation', func.__name__)
        
        tracer = get_tracer(service_name)
        with tracer.trace_operation(operation) as span_id:
            kwargs['span_id'] = span_id
            return func(*args, **kwargs)
    
    return wrapper

# Predefined trace schemas for translation pipeline
TRANSLATION_TRACE_SCHEMA = {
    "mic_capture": {
        "service": "frontend",
        "metadata_fields": ["sample_rate", "channels", "audio_format"]
    },
    "stt_first_token": {
        "service": "stt-service", 
        "metadata_fields": ["model", "confidence", "chunk_size_ms", "agreement_score"]
    },
    "mt_start": {
        "service": "mt-service",
        "metadata_fields": ["src_lang", "tgt_lang", "context_size", "model_version"]
    },
    "mt_end": {
        "service": "mt-service",
        "metadata_fields": ["tokens_translated", "translation_score", "context_updated"]
    },
    "tts_first_sample": {
        "service": "tts-service",
        "metadata_fields": ["voice_id", "sample_rate", "streaming_enabled", "synthesis_model"]
    },
    "sfu_publish": {
        "service": "livekit-sfu",
        "metadata_fields": ["track_id", "bitrate", "codec", "participant_count"]
    },
    "client_playout": {
        "service": "frontend",
        "metadata_fields": ["total_latency_ms", "buffer_health", "audio_quality_score"]
    }
}

async def export_trace_to_jaeger(trace_summary: Dict[str, Any], jaeger_endpoint: str):
    """Export trace summary to Jaeger for visualization"""
    # This would typically use Jaeger's HTTP API
    # For now, we'll log the trace for debugging
    print(f"TRACE_EXPORT: {json.dumps(trace_summary, indent=2)}")