"""
The HIVE Quality Assurance Testing Framework

Comprehensive testing infrastructure for The HIVE real-time translation system.
Validates SLO compliance, performance, quality, and production readiness.

Key Components:
- SLO Validation Tests: TTFT ≤ 450ms, caption latency ≤ 250ms, word retractions <5%
- Network Resilience Tests: Packet loss, jitter, bandwidth constraints, failure recovery
- Integration Tests: End-to-end STT→MT→TTS→LiveKit pipeline validation
- Load Tests: Concurrent sessions, stress testing, CPU/memory limits validation
- Quality Tests: Translation accuracy (BLEU/semantic), audio quality (SNR/PESQ)
- Deployment Gates: Automated production readiness with go/no-go decision

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    QA Test Framework                             │
├─────────────────────────────────────────────────────────────────┤
│ test_runner.py      │ Main orchestrator & CLI interface         │
│ slo_tests.py        │ SLO compliance validation                  │
│ network_impairment.py│ Network resilience testing               │
│ integration_tests.py │ End-to-end pipeline testing               │
│ load_tests.py       │ Performance & stress testing               │
│ quality_tests.py    │ Translation & audio quality               │
│ deployment_gates.py │ Production readiness gates                │
│ config.py           │ Centralized configuration                 │
└─────────────────────────────────────────────────────────────────┘

Usage Examples:

    # Quick validation (2-5 minutes)
    from qa import QATestRunner
    runner = QATestRunner()
    results = await runner.run_all_tests(quick_mode=True)
    
    # Comprehensive validation (20-30 minutes)  
    results = await runner.run_all_tests(quick_mode=False)
    
    # Specific test suites
    results = await runner.run_specific_tests(['slo_validation', 'deployment_gates'])
    
    # Individual test modules
    from qa import run_all_slo_tests, run_deployment_validation
    slo_results = await run_all_slo_tests()
    deploy_report = await run_deployment_validation()
    
    # Command line usage
    python -m qa.test_runner --mode comprehensive --output results.json
    ./qa/run_tests.sh -m quick -t slo_validation,deployment_gates

Service Level Objectives (SLOs):
- Time-to-First-Token (TTFT) p95: ≤ 450ms
- Caption Latency p95: ≤ 250ms  
- Word Retraction Rate: <5%
- Overall Success Rate: ≥95%
- CPU Usage: ≤80%, Memory: ≤85%

Production Deployment Gates:
✓ SLO Compliance: All targets met
✓ Network Resilience: Handles 1-5% packet loss
✓ Integration: End-to-end pipeline functional
✓ Load Testing: Supports target concurrent sessions
✓ Quality: Translation & audio quality thresholds
✓ Infrastructure: All services healthy
✓ Security: No critical vulnerabilities

Quick Start:
    cd qa/
    python test_runner.py --mode quick        # Fast validation
    python test_runner.py --mode comprehensive # Full validation
    ./run_tests.sh -m quick -v                # Bash script with verbose output
"""

from .test_runner import QATestRunner
from .config import QAConfig, get_qa_config, create_default_config_file

# Test modules
from .slo_tests import run_all_slo_tests, SLOTestConfig
from .network_impairment import run_comprehensive_resilience_test, run_quick_resilience_test
from .integration_tests import run_full_integration_test, run_quick_integration_test
from .load_tests import run_comprehensive_load_tests, LoadTestConfig
from .quality_tests import run_translation_quality_test, run_audio_quality_test, QualityTestConfig
from .deployment_gates import run_deployment_validation, run_quick_deployment_check

__version__ = "1.0.0"
__author__ = "The HIVE QA Team"
__description__ = "Comprehensive QA framework for The HIVE real-time translation system"

# Service Level Objectives
SLO_TARGETS = {
    "TTFT_P95_MS": 450.0,
    "CAPTION_LATENCY_P95_MS": 250.0,
    "RETRACTION_RATE_MAX": 0.05,
    "SUCCESS_RATE_MIN": 0.95,
    "CPU_USAGE_MAX": 0.80,
    "MEMORY_USAGE_MAX": 0.85
}

__all__ = [
    # Main components
    'QATestRunner',
    'QAConfig', 'get_qa_config', 'create_default_config_file',
    'SLO_TARGETS',
    
    # Test functions
    'run_all_slo_tests', 'SLOTestConfig',
    'run_comprehensive_resilience_test', 'run_quick_resilience_test',
    'run_full_integration_test', 'run_quick_integration_test', 
    'run_comprehensive_load_tests', 'LoadTestConfig',
    'run_translation_quality_test', 'run_audio_quality_test', 'QualityTestConfig',
    'run_deployment_validation', 'run_quick_deployment_check'
]