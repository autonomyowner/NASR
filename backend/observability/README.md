# The HIVE Observability Infrastructure

Comprehensive monitoring, tracing, and alerting system for The HIVE real-time translation pipeline.

## Overview

This observability infrastructure provides complete visibility into the STT→MT→TTS translation pipeline with:

- **End-to-End Tracing**: Distributed tracing across all services with Jaeger
- **SLO Monitoring**: Real-time dashboards tracking critical performance metrics
- **Automated Alerting**: Proactive notifications for SLO violations and service issues
- **Synthetic Testing**: Continuous load testing with realistic conversation patterns
- **Health Monitoring**: Comprehensive service and dependency health checks

## Key SLO Targets

| Metric | Target | Current Status |
|--------|--------|----------------|
| Time-to-First-Token (TTFT) | p95 ≤ 450ms | 🟢 Monitoring Active |
| Caption Latency | p95 ≤ 250ms | 🟢 Monitoring Active |
| Word Retraction Rate | <5% | 🟢 Monitoring Active |
| End-to-End Latency | <500ms | 🟢 Monitoring Active |

## Quick Start

### 1. Start Observability Stack

```bash
cd backend/infra
docker-compose up -d prometheus grafana jaeger health-monitor
```

### 2. Access Monitoring Interfaces

- **Grafana Dashboards**: http://localhost:3001 (admin/hive2024)
- **Prometheus**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686
- **Health Monitor**: http://localhost:8080

### 3. Run Synthetic Load Tests

```bash
cd backend/observability
python synthetic_load_runner.py
```

## Architecture

### Service Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   STT Service   │    │   MT Service    │    │   TTS Service   │
│                 │    │                 │    │                 │
│ • Metrics       │    │ • Metrics       │    │ • Metrics       │ 
│ • Tracing       │────│ • Tracing       │────│ • Tracing       │
│ • Health Checks │    │ • Health Checks │    │ • Health Checks │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Observability   │
                    │                 │
                    │ • Prometheus    │
                    │ • Grafana       │
                    │ • Jaeger        │
                    │ • Health Monitor│
                    │ • Alertmanager  │
                    └─────────────────┘
```

### Distributed Tracing Schema

```json
{
  "trace_id": "uuid4",
  "spans": [
    {
      "span_id": "mic_capture",
      "timestamp": "2024-01-01T00:00:00.000Z",
      "duration_ms": 0,
      "metadata": {"sample_rate": 16000, "channels": 1}
    },
    {
      "span_id": "stt_first_token",
      "timestamp": "2024-01-01T00:00:00.150Z", 
      "duration_ms": 150,
      "metadata": {"model": "whisper-base", "confidence": 0.85}
    },
    {
      "span_id": "mt_translation",
      "timestamp": "2024-01-01T00:00:00.200Z",
      "duration_ms": 50,
      "metadata": {"src_lang": "en", "tgt_lang": "es", "tokens": 15}
    },
    {
      "span_id": "tts_synthesis",
      "timestamp": "2024-01-01T00:00:00.250Z",
      "duration_ms": 200,
      "metadata": {"voice_id": "es-female-1", "streaming": true}
    }
  ]
}
```

## Dashboards

### 1. SLO Monitoring Dashboard

Primary dashboard tracking translation SLOs:

- **TTFT Latency**: Real-time p95 latency with 450ms target line
- **Caption Latency**: p95 caption display latency with 250ms target
- **Word Retraction Rate**: Percentage of words retracted/corrected
- **Service Health**: Live status of all translation services
- **Active Sessions**: Current translation sessions and participant count

### 2. Service Performance Dashboard

Detailed service metrics:

- **STT Service**: Processing latency, throughput, model performance
- **MT Service**: Translation speed, confidence scores, language pair usage
- **TTS Service**: Synthesis time, voice usage, streaming performance
- **System Resources**: CPU, Memory, GPU utilization by service

### 3. User Experience Dashboard

User-facing metrics:

- **Session Analytics**: Duration, participant engagement, popular languages
- **Quality Metrics**: Translation accuracy, audio quality scores
- **Error Tracking**: Failed requests, retries, user-reported issues

## Alerting Rules

### Critical Alerts (PagerDuty)

- **TTFT SLO Breach**: p95 TTFT > 450ms for 2+ minutes
- **Service Down**: Any translation service unreachable for 1+ minute
- **High Error Rate**: Service error rate > 1% for 5+ minutes
- **End-to-End Latency**: p95 > 500ms for 3+ minutes

### Warning Alerts (Slack)

- **Caption Latency SLO**: p95 > 250ms for 5+ minutes
- **High Retraction Rate**: Word retractions > 5% for 10+ minutes
- **Resource Usage**: CPU/Memory/GPU > 80% for 10+ minutes
- **Poor Audio Quality**: Average quality score < 60% for 10+ minutes

## Synthetic Load Testing

### Test Scenarios

1. **Baseline Load**: 2 concurrent speakers, 5-minute sessions
2. **Peak Load**: 8 concurrent speakers, realistic conversation patterns
3. **Stress Test**: 16 concurrent speakers, 10-minute sessions
4. **Network Impairment**: Simulated packet loss and latency

### Running Load Tests

```bash
# Run single scenario
python -c "
from synthetic_load_runner import run_synthetic_load_test
import asyncio
result = asyncio.run(run_synthetic_load_test('peak_load'))
print(f'Success Rate: {result.success_rate:.2%}')
print(f'TTFT p95: {result.metrics[\"ttft_p95_ms\"]:.1f}ms')
"

# Run all scenarios
python synthetic_load_runner.py
```

### Load Test Results

Results are automatically exported to JSON with:
- Performance percentiles (p50, p95, p99)
- SLO compliance status
- Error analysis and failure modes
- Resource utilization during test

## Health Monitoring

### Health Check Endpoints

```bash
# Overall system health
curl http://localhost:8080/health/detailed

# Specific service health  
curl http://localhost:8080/health/service/stt-service

# Basic health check
curl http://localhost:8080/health
```

### Health Status Levels

- **HEALTHY**: All systems operational, SLOs met
- **DEGRADED**: Minor issues detected, SLOs at risk
- **UNHEALTHY**: Critical issues, SLO violations active
- **UNKNOWN**: Unable to determine status

## Integration Guide

### Adding Observability to New Services

1. **Install Dependencies**
   ```python
   from backend.observability import get_tracer, get_metrics, metrics_middleware
   ```

2. **Initialize Tracing and Metrics**
   ```python
   tracer = get_tracer("my-service")
   metrics = get_metrics("my-service")
   
   # Add middleware
   app.middleware("http")(metrics_middleware("my-service"))
   ```

3. **Instrument Key Operations**
   ```python
   @trace_translation_pipeline
   async def process_request(request):
       with tracer.trace_operation("processing", {"request_id": request.id}):
           # Your processing logic
           result = await process(request)
           
           # Record metrics
           metrics.record_processing_time(processing_duration)
           return result
   ```

4. **Add Health Checks**
   ```python
   @app.get("/health")
   async def health_check():
       return {"status": "healthy", "timestamp": datetime.utcnow()}
   ```

### Custom Metrics

```python
# Record custom business metrics
metrics.record_translation_confidence(0.85, "mt-service", "en-es")
metrics.record_word_processed("spanish")
metrics.record_word_retraction("spanish", "correction")
```

### Custom Tracing

```python
# Create custom trace spans
span_id = tracer.start_span("custom_operation", metadata={
    "user_id": user.id,
    "language": "spanish"
})

# ... perform operation ...

tracer.finish_span(span_id, "completed", {"result": "success"})
```

## Troubleshooting

### Common Issues

1. **Metrics Not Appearing in Grafana**
   - Check Prometheus scrape targets: http://localhost:9090/targets
   - Verify service `/metrics` endpoints are accessible
   - Check Grafana datasource configuration

2. **Traces Missing in Jaeger**
   - Verify Jaeger agent connectivity on port 6831
   - Check service instrumentation and trace initialization
   - Review OpenTelemetry configuration

3. **Alerts Not Firing**
   - Check Prometheus alert rules: http://localhost:9090/rules
   - Verify AlertManager configuration
   - Test alert expressions in Prometheus query interface

4. **Health Checks Failing**
   - Review service logs: `docker logs <service-name>`
   - Check network connectivity between services
   - Verify Redis connectivity and performance

### Performance Optimization

1. **Reduce Metric Cardinality**
   - Limit label values to prevent metric explosion
   - Use recording rules for expensive queries
   - Archive old metrics data regularly

2. **Optimize Tracing Overhead**
   - Configure appropriate sampling rates
   - Use async trace export
   - Limit span metadata size

3. **Dashboard Performance**
   - Use recording rules for complex queries
   - Set appropriate time ranges
   - Cache dashboard results when possible

## Maintenance

### Regular Tasks

- **Weekly**: Review dashboard performance and optimize slow queries
- **Monthly**: Archive old metrics data and traces
- **Quarterly**: Update SLO targets based on user feedback and system evolution

### Backup and Recovery

```bash
# Backup Prometheus data
docker exec hive-prometheus tar -czf /backup/prometheus-$(date +%Y%m%d).tar.gz /prometheus

# Backup Grafana dashboards
docker exec hive-grafana tar -czf /backup/grafana-$(date +%Y%m%d).tar.gz /var/lib/grafana
```

## Support and Contributing

- **Documentation**: https://wiki.thehive.com/observability
- **Runbooks**: https://wiki.thehive.com/runbooks
- **Slack**: #observability-alerts
- **On-call**: observability-team@thehive.com

For questions or contributions, please reach out to the observability team.