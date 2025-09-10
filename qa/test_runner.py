"""
The HIVE QA Test Runner
Comprehensive test orchestrator for production readiness validation
"""

import asyncio
import argparse
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import all test modules
from .slo_tests import run_all_slo_tests, SLOTestConfig
from .network_impairment import run_comprehensive_resilience_test, run_quick_resilience_test
from .integration_tests import run_full_integration_test, run_quick_integration_test
from .load_tests import run_comprehensive_load_tests, LoadTestConfig
from .quality_tests import run_translation_quality_test, run_audio_quality_test
from .deployment_gates import run_deployment_validation, run_quick_deployment_check

class TestSuite:
    """Test suite configuration"""
    
    def __init__(self, name: str, description: str, test_func, required: bool = True, 
                 timeout_minutes: int = 30):
        self.name = name
        self.description = description
        self.test_func = test_func
        self.required = required
        self.timeout_minutes = timeout_minutes

class QATestRunner:
    """Main QA test orchestrator"""
    
    def __init__(self):
        self.test_suites = self._define_test_suites()
        
    def _define_test_suites(self) -> List[TestSuite]:
        """Define all available test suites"""
        return [
            TestSuite(
                name="slo_validation",
                description="SLO Compliance Tests (TTFT, Caption Latency, Word Retractions)",
                test_func=self._run_slo_tests,
                required=True,
                timeout_minutes=15
            ),
            TestSuite(
                name="network_resilience",
                description="Network Impairment and Resilience Testing",
                test_func=self._run_network_tests,
                required=True,
                timeout_minutes=20
            ),
            TestSuite(
                name="integration_tests",
                description="End-to-End Pipeline Integration Tests",
                test_func=self._run_integration_tests,
                required=True,
                timeout_minutes=15
            ),
            TestSuite(
                name="load_tests",
                description="Load Testing and Performance Validation",
                test_func=self._run_load_tests,
                required=True,
                timeout_minutes=30
            ),
            TestSuite(
                name="quality_tests",
                description="Translation and Audio Quality Assessment",
                test_func=self._run_quality_tests,
                required=True,
                timeout_minutes=20
            ),
            TestSuite(
                name="deployment_gates",
                description="Production Deployment Readiness Gates",
                test_func=self._run_deployment_gates,
                required=True,
                timeout_minutes=25
            )
        ]
    
    async def run_all_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run all test suites"""
        logger.info("=" * 80)
        logger.info("THE HIVE QA TEST RUNNER - COMPREHENSIVE VALIDATION")
        logger.info("=" * 80)
        
        start_time = datetime.utcnow()
        test_results = {}
        
        # Select test suites based on mode
        if quick_mode:
            logger.info("Running in QUICK MODE - reduced test coverage for faster execution")
            selected_suites = [s for s in self.test_suites if s.name in [
                "slo_validation", "integration_tests", "deployment_gates"
            ]]
        else:
            logger.info("Running COMPREHENSIVE TEST SUITE - full production validation")
            selected_suites = self.test_suites
        
        logger.info(f"Test suites to execute: {len(selected_suites)}")
        for suite in selected_suites:
            logger.info(f"  • {suite.name}: {suite.description}")
        
        # Run test suites
        for i, suite in enumerate(selected_suites, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"TEST SUITE {i}/{len(selected_suites)}: {suite.name.upper()}")
            logger.info(f"Description: {suite.description}")
            logger.info(f"{'='*80}")
            
            suite_start = time.time()
            
            try:
                # Run test with timeout
                result = await asyncio.wait_for(
                    suite.test_func(quick_mode),
                    timeout=suite.timeout_minutes * 60
                )
                
                suite_duration = time.time() - suite_start
                
                test_results[suite.name] = {
                    "status": "completed",
                    "result": result,
                    "duration_seconds": suite_duration,
                    "success": self._evaluate_suite_success(result)
                }
                
                success_indicator = "✓ PASSED" if test_results[suite.name]["success"] else "✗ FAILED"
                logger.info(f"\n{suite.name} completed in {suite_duration:.1f}s - {success_indicator}")
                
            except asyncio.TimeoutError:
                logger.error(f"Test suite {suite.name} timed out after {suite.timeout_minutes} minutes")
                test_results[suite.name] = {
                    "status": "timeout",
                    "result": None,
                    "duration_seconds": suite.timeout_minutes * 60,
                    "success": False
                }
                
            except Exception as e:
                logger.error(f"Test suite {suite.name} failed with error: {e}")
                test_results[suite.name] = {
                    "status": "error",
                    "result": None,
                    "duration_seconds": time.time() - suite_start,
                    "success": False,
                    "error": str(e)
                }
            
            # Brief pause between test suites for system recovery
            if i < len(selected_suites):
                logger.info("Allowing system recovery time...")
                await asyncio.sleep(10)
        
        end_time = datetime.utcnow()
        
        # Generate summary report
        summary = self._generate_summary_report(test_results, start_time, end_time, quick_mode)
        
        # Log final summary
        self._log_final_summary(summary)
        
        return {
            "summary": summary,
            "detailed_results": test_results
        }
    
    async def run_specific_tests(self, test_names: List[str], quick_mode: bool = False) -> Dict[str, Any]:
        """Run specific test suites"""
        logger.info(f"Running specific test suites: {', '.join(test_names)}")
        
        # Filter test suites
        selected_suites = [s for s in self.test_suites if s.name in test_names]
        
        if not selected_suites:
            raise ValueError(f"No valid test suites found. Available: {[s.name for s in self.test_suites]}")
        
        # Temporarily replace all suites with selected ones
        original_suites = self.test_suites
        self.test_suites = selected_suites
        
        try:
            return await self.run_all_tests(quick_mode)
        finally:
            self.test_suites = original_suites
    
    async def _run_slo_tests(self, quick_mode: bool = False) -> Any:
        """Run SLO validation tests"""
        config = SLOTestConfig()
        if quick_mode:
            config.sample_count = 30
            config.test_duration_minutes = 1
        
        return await run_all_slo_tests(config)
    
    async def _run_network_tests(self, quick_mode: bool = False) -> Any:
        """Run network resilience tests"""
        if quick_mode:
            return await run_quick_resilience_test()
        else:
            return await run_comprehensive_resilience_test()
    
    async def _run_integration_tests(self, quick_mode: bool = False) -> Any:
        """Run integration tests"""
        if quick_mode:
            return await run_quick_integration_test()
        else:
            return await run_full_integration_test()
    
    async def _run_load_tests(self, quick_mode: bool = False) -> Any:
        """Run load tests"""
        config = LoadTestConfig()
        if quick_mode:
            config.max_concurrent_sessions = 4
            config.ramp_up_duration_seconds = 15
            config.sustained_load_duration_seconds = 30
            config.session_duration_seconds = 60
        
        return await run_comprehensive_load_tests(config)
    
    async def _run_quality_tests(self, quick_mode: bool = False) -> Any:
        """Run quality assessment tests"""
        # Run both translation and audio quality tests
        translation_result = await run_translation_quality_test([("en", "es"), ("es", "en")])
        audio_result = await run_audio_quality_test(["en", "es"])
        
        return {
            "translation_quality": translation_result,
            "audio_quality": audio_result
        }
    
    async def _run_deployment_gates(self, quick_mode: bool = False) -> Any:
        """Run deployment gates validation"""
        if quick_mode:
            return await run_quick_deployment_check()
        else:
            return await run_deployment_validation()
    
    def _evaluate_suite_success(self, result: Any) -> bool:
        """Evaluate if a test suite was successful"""
        if result is None:
            return False
        
        # Handle different result types
        if isinstance(result, bool):
            return result
        
        if isinstance(result, dict):
            # Check for common success indicators
            if "deployment_approved" in result:
                return result["deployment_approved"]
            
            if "overall_slo_compliant" in result:
                return result["overall_slo_compliant"]
            
            if "overall_compliant" in result:
                return result["overall_compliant"]
            
            if "quality_compliant" in result:
                return result["quality_compliant"]
            
            # For complex results, check if all sub-results are successful
            if all(isinstance(v, dict) and self._evaluate_suite_success(v) for v in result.values()):
                return True
            
            # Check for any pass indicators
            success_indicators = ["passed", "success", "compliant", "approved"]
            for key, value in result.items():
                if any(indicator in key.lower() for indicator in success_indicators):
                    if isinstance(value, bool):
                        return value
                    elif isinstance(value, (int, float)):
                        return value > 0.8  # 80% threshold
        
        # Default: assume success if we got a result
        return True
    
    def _generate_summary_report(self, test_results: Dict[str, Any], 
                                start_time: datetime, end_time: datetime,
                                quick_mode: bool) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        total_duration = (end_time - start_time).total_seconds()
        
        # Count results
        total_suites = len(test_results)
        completed_suites = sum(1 for r in test_results.values() if r["status"] == "completed")
        successful_suites = sum(1 for r in test_results.values() if r["success"])
        failed_suites = sum(1 for r in test_results.values() if not r["success"])
        timeout_suites = sum(1 for r in test_results.values() if r["status"] == "timeout")
        error_suites = sum(1 for r in test_results.values() if r["status"] == "error")
        
        # Calculate success rate
        success_rate = successful_suites / total_suites if total_suites > 0 else 0
        
        # Determine overall status
        if success_rate >= 0.9:
            overall_status = "EXCELLENT"
            production_ready = True
        elif success_rate >= 0.8:
            overall_status = "GOOD"
            production_ready = True
        elif success_rate >= 0.7:
            overall_status = "FAIR"
            production_ready = False
        else:
            overall_status = "POOR"
            production_ready = False
        
        # Check for critical failures
        critical_suites = ["slo_validation", "deployment_gates"]
        critical_failures = [name for name in critical_suites 
                           if name in test_results and not test_results[name]["success"]]
        
        if critical_failures:
            production_ready = False
        
        return {
            "test_run_info": {
                "mode": "quick" if quick_mode else "comprehensive",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": total_duration,
                "duration_formatted": self._format_duration(total_duration)
            },
            "results_summary": {
                "total_suites": total_suites,
                "completed": completed_suites,
                "successful": successful_suites,
                "failed": failed_suites,
                "timeout": timeout_suites,
                "error": error_suites,
                "success_rate": success_rate
            },
            "quality_assessment": {
                "overall_status": overall_status,
                "production_ready": production_ready,
                "critical_failures": critical_failures
            },
            "suite_details": {
                name: {
                    "success": result["success"],
                    "status": result["status"],
                    "duration": self._format_duration(result["duration_seconds"])
                }
                for name, result in test_results.items()
            }
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def _log_final_summary(self, summary: Dict[str, Any]):
        """Log comprehensive final summary"""
        logger.info("\n" + "=" * 80)
        logger.info("THE HIVE QA VALIDATION - FINAL REPORT")
        logger.info("=" * 80)
        
        test_info = summary["test_run_info"]
        results = summary["results_summary"]
        quality = summary["quality_assessment"]
        
        logger.info(f"Test Mode: {test_info['mode'].upper()}")
        logger.info(f"Duration: {test_info['duration_formatted']}")
        logger.info(f"Completed: {test_info['end_time']}")
        
        logger.info(f"\nTest Suite Results:")
        logger.info(f"  Total Suites: {results['total_suites']}")
        logger.info(f"  ✓ Successful: {results['successful']}")
        logger.info(f"  ✗ Failed: {results['failed']}")
        logger.info(f"  ⏱ Timeout: {results['timeout']}")
        logger.info(f"  ❌ Error: {results['error']}")
        logger.info(f"  Success Rate: {results['success_rate']:.1%}")
        
        logger.info(f"\nDetailed Results:")
        for suite_name, details in summary["suite_details"].items():
            status_symbol = "✓" if details["success"] else "✗"
            logger.info(f"  {status_symbol} {suite_name}: {details['status'].upper()} ({details['duration']})")
        
        logger.info(f"\nQuality Assessment:")
        logger.info(f"  Overall Status: {quality['overall_status']}")
        logger.info(f"  Production Ready: {'YES' if quality['production_ready'] else 'NO'}")
        
        if quality['critical_failures']:
            logger.error(f"\n🚨 CRITICAL FAILURES:")
            for failure in quality['critical_failures']:
                logger.error(f"  • {failure}")
        
        # Final deployment decision
        if quality['production_ready']:
            logger.info(f"\n🟢 DEPLOYMENT DECISION: APPROVED")
            logger.info("The HIVE translation system is ready for production deployment.")
        else:
            logger.error(f"\n🔴 DEPLOYMENT DECISION: REJECTED")
            logger.error("The HIVE translation system requires fixes before production deployment.")
        
        logger.info("=" * 80)

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="The HIVE QA Test Runner")
    parser.add_argument(
        "--mode",
        choices=["quick", "comprehensive"],
        default="comprehensive",
        help="Test execution mode (default: comprehensive)"
    )
    parser.add_argument(
        "--tests",
        nargs="*",
        help="Specific test suites to run (space-separated)",
        choices=[
            "slo_validation",
            "network_resilience", 
            "integration_tests",
            "load_tests",
            "quality_tests",
            "deployment_gates"
        ]
    )
    parser.add_argument(
        "--output",
        help="Output file for test results (JSON format)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create test runner
    runner = QATestRunner()
    
    try:
        # Run tests
        if args.tests:
            results = await runner.run_specific_tests(args.tests, args.mode == "quick")
        else:
            results = await runner.run_all_tests(args.mode == "quick")
        
        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Test results saved to: {args.output}")
        
        # Determine exit code
        production_ready = results["summary"]["quality_assessment"]["production_ready"]
        exit_code = 0 if production_ready else 1
        
        return exit_code
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)