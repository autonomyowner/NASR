"""
The HIVE Observability Infrastructure

This package provides comprehensive monitoring, tracing, and alerting for
The HIVE real-time translation system.

Key Components:
- Distributed Tracing: End-to-end request tracing across STT→MT→TTS pipeline
- Metrics Collection: Prometheus metrics for SLO monitoring and performance analytics
- Health Monitoring: Service health checks and dependency monitoring
- Synthetic Load Testing: Automated testing with realistic conversation patterns
- Alerting: SLO violation detection and automated notifications

SLO Targets:
- Time-to-First-Token (TTFT): p95 ≤ 450ms
- Caption Latency: p95 ≤ 250ms
- Word Retraction Rate: <5%
- End-to-End Latency: <500ms target
"""

from .tracer import TranslationTracer, get_tracer, trace_translation_pipeline
from .metrics import TranslationMetrics, get_metrics, metrics_middleware
from .health_monitor import SystemHealthMonitor, HealthStatus, ServiceHealth
from .synthetic_load_runner import SyntheticLoadRunner, LoadTestConfig, run_synthetic_load_test

__version__ = "1.0.0"
__author__ = "The HIVE Translation Team"

__all__ = [
    "TranslationTracer",
    "get_tracer", 
    "trace_translation_pipeline",
    "TranslationMetrics",
    "get_metrics",
    "metrics_middleware",
    "SystemHealthMonitor",
    "HealthStatus",
    "ServiceHealth", 
    "SyntheticLoadRunner",
    "LoadTestConfig",
    "run_synthetic_load_test"
]