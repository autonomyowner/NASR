# The HIVE QA Testing Infrastructure

Comprehensive quality assurance testing framework for The HIVE real-time translation system, ensuring production readiness through automated SLO validation, performance testing, and deployment gates.

## Overview

This QA framework provides comprehensive testing capabilities to validate:
- **SLO Compliance**: p95 TTFT ≤ 450ms, Caption Latency ≤ 250ms, Word Retractions <5%
- **Network Resilience**: System performance under various network conditions
- **Integration Testing**: End-to-end pipeline validation (STT→MT→TTS→LiveKit)  
- **Load Testing**: Concurrent session handling and stress testing
- **Quality Assurance**: Translation accuracy and audio quality validation
- **Deployment Gates**: Automated production readiness validation

## Quick Start

### Prerequisites

1. **Services Running**: Ensure all backend services are running:
   ```bash
   cd backend/infra
   docker-compose up -d
   ```

2. **Python Dependencies**: Install required packages:
   ```bash
   pip install aiohttp numpy soundfile librosa scipy matplotlib psutil
   ```

### Basic Usage

Run comprehensive QA validation:
```bash
cd qa/
python test_runner.py --mode comprehensive
```

Run quick validation (faster, reduced coverage):
```bash
python test_runner.py --mode quick
```

Run specific test suites:
```bash
python test_runner.py --tests slo_validation deployment_gates
```

Save results to file:
```bash
python test_runner.py --output results.json
```

## Test Suites

### 1. SLO Validation (`slo_tests.py`)

Validates Service Level Objectives compliance:

```python
from qa.slo_tests import run_all_slo_tests, SLOTestConfig

# Run with custom config
config = SLOTestConfig(
    ttft_target_ms=450.0,
    caption_latency_target_ms=250.0,
    retraction_rate_target=0.05,
    sample_count=100
)

results = await run_all_slo_tests(config)
```

**Key Metrics**:
- Time-to-First-Token (TTFT) p95 latency
- Caption delivery latency p95  
- Word retraction rate
- Overall SLO compliance rate

### 2. Network Resilience (`network_impairment.py`)

Tests system resilience under various network conditions:

```python
from qa.network_impairment import run_comprehensive_resilience_test

# Test with packet loss, latency, jitter, bandwidth limits
results = await run_comprehensive_resilience_test()
```

**Test Conditions**:
- 1-5% packet loss simulation
- 50-200ms additional latency
- Network jitter (±25ms)
- Bandwidth constraints (256-512 Kbps)
- Combined impairment scenarios

### 3. Integration Testing (`integration_tests.py`)

End-to-end pipeline validation:

```python  
from qa.integration_tests import run_full_integration_test

# Test complete STT→MT→TTS→LiveKit pipeline
results = await run_full_integration_test()
```

**Test Scenarios**:
- Single participant sessions
- Multi-participant rooms (2-8 users)
- Language pair validation
- Real-time audio processing
- LiveKit room management

### 4. Load Testing (`load_tests.py`)

Performance validation under load:

```python
from qa.load_tests import run_comprehensive_load_tests, LoadTestConfig

config = LoadTestConfig(
    max_concurrent_sessions=16,
    sustained_load_duration_seconds=300,
    max_cpu_usage_percent=80.0
)

results = await run_comprehensive_load_tests(config)
```

**Test Types**:
- Ramp-up testing (gradual load increase)
- Stress testing (finding breaking point)
- Spike testing (sudden load increases)
- System resource monitoring

### 5. Quality Assessment (`quality_tests.py`)

Translation and audio quality validation:

```python
from qa.quality_tests import run_translation_quality_test, run_audio_quality_test

# Test translation accuracy
translation_results = await run_translation_quality_test([("en", "es"), ("fr", "en")])

# Test audio synthesis quality  
audio_results = await run_audio_quality_test(["en", "es", "fr"])
```

**Quality Metrics**:
- BLEU/METEOR scores for translation accuracy
- Semantic similarity assessment
- Audio quality (SNR, PESQ, naturalness)
- Voice intelligibility scoring

### 6. Deployment Gates (`deployment_gates.py`)

Automated production readiness validation:

```python
from qa.deployment_gates import run_deployment_validation

# Comprehensive production readiness check
report = await run_deployment_validation()
print(f"Deployment Approved: {report.deployment_approved}")
```

**Gate Categories**:
- **SLO Gates**: Performance targets compliance
- **Quality Gates**: Translation and audio quality thresholds
- **Performance Gates**: CPU, memory, response time limits
- **Infrastructure Gates**: Service health, connectivity
- **Security Gates**: Vulnerability scans, SSL certificates

## Configuration

### Environment Variables

```bash
# Service endpoints
export STT_SERVICE_URL="http://localhost:8001"
export MT_SERVICE_URL="http://localhost:8002" 
export TTS_SERVICE_URL="http://localhost:8003"
export LIVEKIT_URL="ws://localhost:7880"

# Test parameters
export QA_SAMPLE_COUNT=50
export QA_TEST_DURATION=300
export QA_MAX_CONCURRENT=8
```

### Configuration Files

Create `qa_config.json` for custom settings:

```json
{
  "slo_targets": {
    "ttft_p95_ms": 450,
    "caption_latency_p95_ms": 250,
    "retraction_rate_max": 0.05
  },
  "load_test": {
    "max_concurrent_sessions": 16,
    "test_duration_seconds": 300
  },
  "quality_thresholds": {
    "min_translation_accuracy": 0.7,
    "min_audio_quality": 0.7
  }
}
```

## CI/CD Integration

### GitHub Actions

```yaml
name: QA Validation
on: [push, pull_request]

jobs:
  qa-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup services
        run: |
          cd backend/infra
          docker-compose up -d
      - name: Run QA tests
        run: |
          cd qa/
          python test_runner.py --mode quick --output qa-results.json
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: qa-results
          path: qa/qa-results.json
```

### Pre-deployment Validation

```bash
#!/bin/bash
# pre-deploy.sh
cd qa/
python test_runner.py --mode comprehensive --output pre-deploy-results.json

# Check deployment approval
if [ $? -eq 0 ]; then
  echo "✅ QA validation passed - deployment approved"
  exit 0
else
  echo "❌ QA validation failed - deployment blocked"
  exit 1
fi
```

## Reports and Outputs

### Test Result Structure

```json
{
  "summary": {
    "test_run_info": {
      "mode": "comprehensive", 
      "duration_seconds": 1200.5,
      "start_time": "2024-01-15T10:30:00Z"
    },
    "results_summary": {
      "total_suites": 6,
      "successful": 5,
      "success_rate": 0.83
    },
    "quality_assessment": {
      "overall_status": "GOOD",
      "production_ready": true
    }
  },
  "detailed_results": {
    "slo_validation": {
      "status": "completed",
      "success": true,
      "result": { /* detailed SLO metrics */ }
    }
  }
}
```

### Generated Reports

The framework generates several report types:

1. **JSON Results**: Machine-readable test data
2. **HTML Reports**: Visual performance dashboards  
3. **Performance Charts**: CPU/memory usage graphs
4. **Deployment Report**: Production readiness summary

## Performance Monitoring

### Real-time Metrics

During test execution, the framework monitors:

- **System Resources**: CPU, memory, network I/O
- **Service Response Times**: STT, MT, TTS latencies
- **Translation Quality**: Accuracy scores over time
- **Error Rates**: Service failures and retries

### SLO Dashboards

Integration with Grafana dashboards for:
- Live SLO compliance tracking
- Performance trend analysis  
- Alert thresholds and notifications
- Historical comparison

## Troubleshooting

### Common Issues

**Services Not Responding**:
```bash
# Check service health
curl http://localhost:8001/health
curl http://localhost:8002/health  
curl http://localhost:8003/health

# Restart services
cd backend/infra
docker-compose restart
```

**Test Timeouts**:
- Reduce sample counts in quick mode
- Check system resources (CPU/memory)
- Verify network connectivity

**Quality Test Failures**:
- Ensure reference translations are loaded
- Check audio processing dependencies
- Verify language model availability

### Debug Mode

Enable verbose logging:
```bash
python test_runner.py --verbose --mode quick
```

Set logging level in code:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Architecture

### Test Framework Components

```
QA Framework
├── test_runner.py         # Main orchestrator
├── slo_tests.py          # SLO validation
├── network_impairment.py # Network resilience
├── integration_tests.py  # End-to-end testing
├── load_tests.py         # Performance testing
├── quality_tests.py      # Quality assessment
├── deployment_gates.py   # Production gates
└── reports/              # Generated reports
```

### Dependencies

- **aiohttp**: Async HTTP client for service calls
- **numpy/scipy**: Signal processing and statistics
- **soundfile/librosa**: Audio processing
- **matplotlib**: Performance visualization
- **psutil**: System resource monitoring

## Contributing

### Adding New Tests

1. Create test module in `qa/`
2. Implement async test functions
3. Add to `test_runner.py` test suites
4. Update documentation and examples

### Test Guidelines  

- Use async/await for all I/O operations
- Include comprehensive error handling
- Provide clear success/failure criteria
- Generate structured result objects
- Log progress and diagnostic information

### Code Standards

- Follow PEP 8 style guidelines
- Include type hints for function signatures  
- Add docstrings for all public functions
- Use descriptive variable and function names
- Implement proper exception handling

## Support

For questions or issues:
- Review test logs for error details
- Check service connectivity and health
- Verify configuration parameters
- Consult performance monitoring dashboards

The QA framework is designed to provide comprehensive production readiness validation for The HIVE translation system, ensuring reliable, high-quality real-time translation services.