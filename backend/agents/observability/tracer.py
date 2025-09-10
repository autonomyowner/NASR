"""
Translation Pipeline Tracer

Distributed tracing implementation for monitoring TTFT and end-to-end latency
across the STT→MT→TTS pipeline.
"""

import time
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

@dataclass
class TraceSpan:
    """Individual trace span"""
    span_id: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    parent_span_id: Optional[str] = None

@dataclass
class TraceContext:
    """Complete trace context"""
    trace_id: str
    start_time: float
    end_time: Optional[float] = None
    total_duration_ms: Optional[float] = None
    spans: List[TraceSpan] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.spans is None:
            self.spans = []
        if self.metadata is None:
            self.metadata = {}

class TranslationTracer:
    """Main tracer for translation pipeline"""
    
    def __init__(self):
        self.active_traces: Dict[str, TraceContext] = {}
        self.completed_traces: List[TraceContext] = []
        self.max_completed_traces = 1000  # Keep last 1000 traces
        
    def start_trace(self, trace_id: str, metadata: Dict[str, Any] = None) -> str:
        """Start a new trace"""
        if not trace_id:
            trace_id = f"trace_{uuid.uuid4().hex[:8]}"
            
        trace = TraceContext(
            trace_id=trace_id,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        self.active_traces[trace_id] = trace
        logger.debug(f"Started trace: {trace_id}")
        return trace_id
    
    def add_span(
        self, 
        trace_id: str, 
        operation: str, 
        start_time: float,
        duration_ms: float,
        metadata: Dict[str, Any] = None,
        parent_span_id: Optional[str] = None
    ) -> str:
        """Add a span to an active trace"""
        if trace_id not in self.active_traces:
            logger.warning(f"Trace {trace_id} not found, creating new trace")
            self.start_trace(trace_id)
            
        span_id = f"{operation}_{int(start_time * 1000)}"
        span = TraceSpan(
            span_id=span_id,
            operation=operation,
            start_time=start_time,
            end_time=start_time + (duration_ms / 1000),
            duration_ms=duration_ms,
            metadata=metadata or {},
            parent_span_id=parent_span_id
        )
        
        self.active_traces[trace_id].spans.append(span)
        logger.debug(f"Added span {span_id} to trace {trace_id}: {operation} ({duration_ms}ms)")
        return span_id
    
    def add_error(self, trace_id: str, error: str, span_id: Optional[str] = None):
        """Add an error to a trace or span"""
        if trace_id not in self.active_traces:
            return
            
        if span_id:
            # Find the span and add error
            for span in self.active_traces[trace_id].spans:
                if span.span_id == span_id:
                    span.metadata = span.metadata or {}
                    span.metadata["error"] = error
                    break
        else:
            # Add error to trace metadata
            self.active_traces[trace_id].metadata["error"] = error
            
        logger.error(f"Added error to trace {trace_id}: {error}")
    
    def complete_trace(self, trace_id: str, metadata: Dict[str, Any] = None) -> Optional[TraceContext]:
        """Complete and finalize a trace"""
        if trace_id not in self.active_traces:
            logger.warning(f"Cannot complete trace {trace_id}: not found")
            return None
            
        trace = self.active_traces[trace_id]
        trace.end_time = time.time()
        trace.total_duration_ms = (trace.end_time - trace.start_time) * 1000
        
        if metadata:
            trace.metadata.update(metadata)
        
        # Calculate TTFT and other metrics
        self._calculate_metrics(trace)
        
        # Move to completed traces
        del self.active_traces[trace_id]
        self.completed_traces.append(trace)
        
        # Trim completed traces if needed
        if len(self.completed_traces) > self.max_completed_traces:
            self.completed_traces = self.completed_traces[-self.max_completed_traces:]
        
        logger.info(f"Completed trace {trace_id}: {trace.total_duration_ms:.1f}ms total")
        return trace
    
    def _calculate_metrics(self, trace: TraceContext):
        """Calculate key metrics for a trace"""
        spans_by_operation = {}
        for span in trace.spans:
            spans_by_operation[span.operation] = span
            
        # Calculate TTFT (Time to First Translated audio)
        ttft_ms = None
        if "tts_first_sample" in spans_by_operation:
            ttft_span = spans_by_operation["tts_first_sample"]
            ttft_ms = (ttft_span.start_time - trace.start_time) * 1000
            
        # Calculate caption latency
        caption_latency_ms = None
        if "stt_first_token" in spans_by_operation:
            stt_span = spans_by_operation["stt_first_token"]
            caption_latency_ms = stt_span.duration_ms
            
        # Add metrics to trace metadata
        trace.metadata.update({
            "ttft_ms": ttft_ms,
            "caption_latency_ms": caption_latency_ms,
            "pipeline_stages": len(trace.spans),
            "processing_stages": [
                {
                    "operation": span.operation,
                    "duration_ms": span.duration_ms,
                    "start_offset_ms": (span.start_time - trace.start_time) * 1000
                }
                for span in trace.spans
            ]
        })
    
    def get_trace(self, trace_id: str) -> Optional[TraceContext]:
        """Get a trace by ID"""
        if trace_id in self.active_traces:
            return self.active_traces[trace_id]
            
        for trace in self.completed_traces:
            if trace.trace_id == trace_id:
                return trace
                
        return None
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary metrics from recent traces"""
        if not self.completed_traces:
            return {"error": "No completed traces available"}
            
        recent_traces = self.completed_traces[-100:]  # Last 100 traces
        
        ttft_values = [t.metadata.get("ttft_ms") for t in recent_traces if t.metadata.get("ttft_ms")]
        caption_latencies = [t.metadata.get("caption_latency_ms") for t in recent_traces if t.metadata.get("caption_latency_ms")]
        total_latencies = [t.total_duration_ms for t in recent_traces if t.total_duration_ms]
        
        def percentile(values, p):
            if not values:
                return None
            sorted_vals = sorted(values)
            index = int(len(sorted_vals) * p / 100)
            return sorted_vals[min(index, len(sorted_vals) - 1)]
        
        return {
            "total_traces": len(self.completed_traces),
            "recent_traces": len(recent_traces),
            "ttft_metrics": {
                "p50": percentile(ttft_values, 50),
                "p95": percentile(ttft_values, 95),
                "p99": percentile(ttft_values, 99),
                "count": len(ttft_values)
            },
            "caption_latency_metrics": {
                "p50": percentile(caption_latencies, 50),
                "p95": percentile(caption_latencies, 95),
                "p99": percentile(caption_latencies, 99),
                "count": len(caption_latencies)
            },
            "total_latency_metrics": {
                "p50": percentile(total_latencies, 50),
                "p95": percentile(total_latencies, 95),
                "p99": percentile(total_latencies, 99),
                "count": len(total_latencies)
            },
            "slo_compliance": {
                "ttft_target_ms": 450,
                "ttft_violations": len([v for v in ttft_values if v > 450]),
                "ttft_compliance_rate": 1 - (len([v for v in ttft_values if v > 450]) / len(ttft_values)) if ttft_values else 0,
                "caption_target_ms": 250,
                "caption_violations": len([v for v in caption_latencies if v > 250]),
                "caption_compliance_rate": 1 - (len([v for v in caption_latencies if v > 250]) / len(caption_latencies)) if caption_latencies else 0
            }
        }
    
    def export_traces_json(self, limit: int = 100) -> str:
        """Export recent traces as JSON for external analysis"""
        recent_traces = self.completed_traces[-limit:]
        traces_data = [asdict(trace) for trace in recent_traces]
        return json.dumps(traces_data, indent=2)
    
    def clear_traces(self):
        """Clear all traces (for testing/cleanup)"""
        self.active_traces.clear()
        self.completed_traces.clear()
        logger.info("Cleared all traces")

# Global tracer instance
_global_tracer: Optional[TranslationTracer] = None

def get_tracer() -> TranslationTracer:
    """Get the global tracer instance"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = TranslationTracer()
    return _global_tracer

# Convenience functions
def start_trace(trace_id: str = None, metadata: Dict[str, Any] = None) -> str:
    """Start a new trace"""
    return get_tracer().start_trace(trace_id, metadata)

def add_span(trace_id: str, operation: str, start_time: float, duration_ms: float, 
             metadata: Dict[str, Any] = None) -> str:
    """Add a span to a trace"""
    return get_tracer().add_span(trace_id, operation, start_time, duration_ms, metadata)

def complete_trace(trace_id: str, metadata: Dict[str, Any] = None) -> Optional[TraceContext]:
    """Complete a trace"""
    return get_tracer().complete_trace(trace_id, metadata)

def get_metrics() -> Dict[str, Any]:
    """Get metrics summary"""
    return get_tracer().get_metrics_summary()

class TracingContext:
    """Context manager for automatic trace completion"""
    
    def __init__(self, trace_id: str = None, metadata: Dict[str, Any] = None):
        self.trace_id = trace_id
        self.metadata = metadata or {}
        self.tracer = get_tracer()
        
    def __enter__(self):
        self.trace_id = self.tracer.start_trace(self.trace_id, self.metadata)
        return self.trace_id
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.tracer.add_error(self.trace_id, str(exc_val))
        self.tracer.complete_trace(self.trace_id)