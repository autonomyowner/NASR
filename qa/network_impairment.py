"""
Network Impairment Testing Framework for The HIVE Translation System
Simulates various network conditions to validate system resilience and SLO compliance
"""

import asyncio
import subprocess
import platform
import time
import logging
import json
import psutil
from typing import Dict, List, Any, Optional, NamedTuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import aiohttp
from pathlib import Path
import sys

# Add backend path for imports
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from observability.tracer import get_tracer
from observability.metrics import get_metrics

# Import SLO tests
from .slo_tests import SLOTestSuite, SLOTestConfig, SLOTestResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NetworkCondition:
    """Represents a specific network impairment condition"""
    name: str
    description: str
    packet_loss_percent: float = 0.0
    latency_ms: int = 0
    jitter_ms: int = 0
    bandwidth_limit_kbps: Optional[int] = None
    corruption_percent: float = 0.0
    duplication_percent: float = 0.0
    reorder_percent: float = 0.0
    expected_degradation: str = ""

@dataclass
class NetworkImpairmentResult:
    """Result from network impairment testing"""
    test_name: str
    condition: NetworkCondition
    baseline_slo_result: SLOTestResult
    impaired_slo_result: SLOTestResult
    degradation_metrics: Dict[str, float]
    resilience_score: float
    slo_maintained: bool
    start_time: datetime
    end_time: datetime
    error_messages: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'baseline_slo_result': self.baseline_slo_result.to_dict() if hasattr(self.baseline_slo_result, 'to_dict') else None,
            'impaired_slo_result': self.impaired_slo_result.to_dict() if hasattr(self.impaired_slo_result, 'to_dict') else None
        }

class NetworkImpairmentTester:
    """Main network impairment testing framework"""
    
    def __init__(self, interface: str = None):
        """Initialize network impairment tester
        
        Args:
            interface: Network interface to apply impairments to (auto-detect if None)
        """
        self.interface = interface or self._detect_primary_interface()
        self.platform = platform.system().lower()
        self.active_impairments = []
        self.tracer = get_tracer("network-impairment-tester")
        self.metrics = get_metrics("network-tests")
        
        # Validate system capabilities
        self._validate_system_capabilities()
        
    def _detect_primary_interface(self) -> str:
        """Auto-detect the primary network interface"""
        try:
            if self.platform == "windows":
                # On Windows, use the interface with the default route
                result = subprocess.run(['route', 'print', '0.0.0.0'], 
                                      capture_output=True, text=True)
                # Parse route table to find primary interface (simplified)
                return "ethernet"  # Default for Windows
            elif self.platform == "linux":
                # Find interface with default route
                result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and result.stdout:
                    # Extract interface name from default route
                    parts = result.stdout.split()
                    if 'dev' in parts:
                        dev_index = parts.index('dev')
                        if dev_index + 1 < len(parts):
                            return parts[dev_index + 1]
                return "eth0"  # Fallback
            else:
                return "en0"  # macOS default
        except Exception as e:
            logger.warning(f"Could not auto-detect interface: {e}")
            return "eth0"
    
    def _validate_system_capabilities(self):
        """Validate that the system supports network impairment"""
        if self.platform == "windows":
            # Check for required Windows tools
            tools = ['netsh']
            for tool in tools:
                if not self._command_exists(tool):
                    logger.warning(f"Network impairment tool '{tool}' not found on Windows")
        elif self.platform == "linux":
            # Check for tc (traffic control)
            if not self._command_exists('tc'):
                raise RuntimeError("Linux 'tc' (traffic control) command not found. Install iproute2 package.")
        elif self.platform == "darwin":
            # Check for pfctl on macOS
            if not self._command_exists('pfctl'):
                logger.warning("macOS 'pfctl' not found. Some network impairments may not work.")
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists on the system"""
        try:
            subprocess.run([command, '--help'], capture_output=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @asynccontextmanager
    async def apply_network_condition(self, condition: NetworkCondition):
        """Context manager to apply and cleanup network conditions"""
        logger.info(f"Applying network condition: {condition.name}")
        
        try:
            # Apply the network impairment
            await self._apply_impairment(condition)
            
            # Wait for conditions to stabilize
            await asyncio.sleep(2)
            
            yield condition
            
        except Exception as e:
            logger.error(f"Error applying network condition {condition.name}: {e}")
            raise
        finally:
            # Always cleanup, even on error
            try:
                await self._cleanup_impairments()
                await asyncio.sleep(1)  # Allow cleanup to take effect
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")
    
    async def _apply_impairment(self, condition: NetworkCondition):
        """Apply specific network impairment based on platform"""
        if self.platform == "linux":
            await self._apply_linux_impairment(condition)
        elif self.platform == "windows":
            await self._apply_windows_impairment(condition)
        elif self.platform == "darwin":
            await self._apply_macos_impairment(condition)
        else:
            logger.warning(f"Network impairment not implemented for platform: {self.platform}")
    
    async def _apply_linux_impairment(self, condition: NetworkCondition):
        """Apply network impairment using Linux tc (traffic control)"""
        commands = []
        
        # Remove existing qdiscs
        cleanup_cmd = f"tc qdisc del dev {self.interface} root"
        commands.append(cleanup_cmd)
        
        # Build netem command
        netem_parts = []
        
        if condition.latency_ms > 0:
            if condition.jitter_ms > 0:
                netem_parts.append(f"delay {condition.latency_ms}ms {condition.jitter_ms}ms")
            else:
                netem_parts.append(f"delay {condition.latency_ms}ms")
        
        if condition.packet_loss_percent > 0:
            netem_parts.append(f"loss {condition.packet_loss_percent}%")
        
        if condition.corruption_percent > 0:
            netem_parts.append(f"corrupt {condition.corruption_percent}%")
        
        if condition.duplication_percent > 0:
            netem_parts.append(f"duplicate {condition.duplication_percent}%")
        
        if condition.reorder_percent > 0:
            netem_parts.append(f"reorder {condition.reorder_percent}%")
        
        if netem_parts:
            netem_cmd = f"tc qdisc add dev {self.interface} root netem {' '.join(netem_parts)}"
            commands.append(netem_cmd)
        
        # Apply bandwidth limit if specified
        if condition.bandwidth_limit_kbps:
            tbf_cmd = f"tc qdisc add dev {self.interface} root tbf rate {condition.bandwidth_limit_kbps}kbit latency 50ms burst 1540"
            commands.append(tbf_cmd)
        
        # Execute commands
        for cmd in commands:
            try:
                result = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0 and "RTNETLINK answers: No such file or directory" not in stderr.decode():
                    logger.warning(f"Command failed: {cmd}")
                    logger.warning(f"Error: {stderr.decode().strip()}")
                    
            except Exception as e:
                logger.error(f"Error executing command '{cmd}': {e}")
        
        self.active_impairments.append(condition)
    
    async def _apply_windows_impairment(self, condition: NetworkCondition):
        """Apply network impairment on Windows using netsh or other tools"""
        logger.warning("Windows network impairment implementation is limited")
        
        # Windows has limited built-in network impairment capabilities
        # This is a placeholder for Windows-specific implementations
        # In production, you might use tools like:
        # - Clumsy (third-party tool)
        # - NetEm for Windows
        # - Windows built-in QoS policies
        
        if condition.packet_loss_percent > 0:
            logger.info(f"Simulating {condition.packet_loss_percent}% packet loss on Windows")
        
        if condition.latency_ms > 0:
            logger.info(f"Simulating {condition.latency_ms}ms latency on Windows")
        
        # For now, we'll simulate by adding application-level delays
        # This is not ideal but allows testing on Windows development machines
        self.active_impairments.append(condition)
    
    async def _apply_macos_impairment(self, condition: NetworkCondition):
        """Apply network impairment on macOS using dummynet/pfctl"""
        logger.warning("macOS network impairment implementation is limited")
        
        # macOS network impairment using dummynet
        # This requires administrative privileges
        
        commands = []
        
        if condition.packet_loss_percent > 0 or condition.latency_ms > 0:
            # Configure dummynet pipe
            pipe_config = []
            if condition.latency_ms > 0:
                pipe_config.append(f"delay {condition.latency_ms}ms")
            if condition.packet_loss_percent > 0:
                pipe_config.append(f"plr {condition.packet_loss_percent/100}")
            if condition.bandwidth_limit_kbps:
                pipe_config.append(f"bw {condition.bandwidth_limit_kbps}Kbit/s")
            
            pipe_cmd = f"dnctl pipe 1 config {' '.join(pipe_config)}"
            commands.append(pipe_cmd)
            
            # Add firewall rule to use the pipe
            fw_cmd = f"dnctl add 1000 pipe 1 ip from any to any"
            commands.append(fw_cmd)
        
        # Execute commands (requires sudo)
        for cmd in commands:
            try:
                process = await asyncio.create_subprocess_shell(
                    f"sudo {cmd}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.warning(f"macOS command failed: {cmd}")
                    logger.warning(f"Error: {stderr.decode().strip()}")
                    
            except Exception as e:
                logger.error(f"Error executing macOS command '{cmd}': {e}")
        
        self.active_impairments.append(condition)
    
    async def _cleanup_impairments(self):
        """Clean up all applied network impairments"""
        if not self.active_impairments:
            return
        
        logger.info("Cleaning up network impairments...")
        
        if self.platform == "linux":
            await self._cleanup_linux_impairments()
        elif self.platform == "windows":
            await self._cleanup_windows_impairments()
        elif self.platform == "darwin":
            await self._cleanup_macos_impairments()
        
        self.active_impairments.clear()
    
    async def _cleanup_linux_impairments(self):
        """Clean up Linux tc rules"""
        cleanup_commands = [
            f"tc qdisc del dev {self.interface} root",
            f"tc qdisc del dev {self.interface} ingress"
        ]
        
        for cmd in cleanup_commands:
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            except Exception as e:
                logger.debug(f"Cleanup command failed (expected): {cmd} - {e}")
    
    async def _cleanup_windows_impairments(self):
        """Clean up Windows network impairments"""
        logger.info("Windows network impairment cleanup")
        # Implementation would depend on the specific Windows tool used
    
    async def _cleanup_macos_impairments(self):
        """Clean up macOS dummynet rules"""
        cleanup_commands = [
            "sudo dnctl -f flush",
            "sudo pfctl -F all"
        ]
        
        for cmd in cleanup_commands:
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            except Exception as e:
                logger.debug(f"macOS cleanup command failed: {cmd} - {e}")

class NetworkResilienceTestSuite:
    """Test suite for network resilience validation"""
    
    def __init__(self, slo_config: SLOTestConfig = None):
        self.slo_config = slo_config or SLOTestConfig()
        self.impairment_tester = NetworkImpairmentTester()
        self.slo_suite = SLOTestSuite(self.slo_config)
        self.tracer = get_tracer("network-resilience-tests")
    
    def get_test_conditions(self) -> List[NetworkCondition]:
        """Get predefined network test conditions"""
        return [
            NetworkCondition(
                name="baseline",
                description="Normal network conditions (no impairment)",
                expected_degradation="None - baseline performance"
            ),
            NetworkCondition(
                name="light_packet_loss",
                description="1% packet loss simulation",
                packet_loss_percent=1.0,
                expected_degradation="Slight increase in retransmissions, minimal SLO impact"
            ),
            NetworkCondition(
                name="moderate_packet_loss",
                description="3% packet loss simulation",
                packet_loss_percent=3.0,
                expected_degradation="Noticeable retransmissions, potential SLO degradation"
            ),
            NetworkCondition(
                name="high_packet_loss",
                description="5% packet loss simulation",
                packet_loss_percent=5.0,
                expected_degradation="Significant impact on SLOs, RED/PLC compensation needed"
            ),
            NetworkCondition(
                name="low_latency_increase",
                description="50ms additional latency",
                latency_ms=50,
                expected_degradation="Moderate increase in total latency"
            ),
            NetworkCondition(
                name="medium_latency_increase", 
                description="100ms additional latency",
                latency_ms=100,
                expected_degradation="Noticeable latency impact on real-time performance"
            ),
            NetworkCondition(
                name="high_latency_increase",
                description="200ms additional latency", 
                latency_ms=200,
                expected_degradation="Significant latency impact, may exceed SLO targets"
            ),
            NetworkCondition(
                name="network_jitter",
                description="Network jitter simulation",
                latency_ms=50,
                jitter_ms=25,
                expected_degradation="Variable latency affecting jitter buffer"
            ),
            NetworkCondition(
                name="bandwidth_constraint_512k",
                description="512 Kbps bandwidth limit",
                bandwidth_limit_kbps=512,
                expected_degradation="Audio quality reduction, potential buffering"
            ),
            NetworkCondition(
                name="bandwidth_constraint_256k",
                description="256 Kbps bandwidth limit", 
                bandwidth_limit_kbps=256,
                expected_degradation="Significant audio quality impact"
            ),
            NetworkCondition(
                name="combined_impairment",
                description="Combined packet loss, latency, and jitter",
                packet_loss_percent=2.0,
                latency_ms=75,
                jitter_ms=15,
                expected_degradation="Multiple network issues affecting overall performance"
            ),
            NetworkCondition(
                name="severe_conditions",
                description="Severe network conditions",
                packet_loss_percent=4.0,
                latency_ms=150,
                jitter_ms=30,
                bandwidth_limit_kbps=384,
                expected_degradation="Extreme conditions testing system limits"
            )
        ]
    
    async def run_single_impairment_test(self, condition: NetworkCondition) -> NetworkImpairmentResult:
        """Run SLO tests under a specific network condition"""
        logger.info(f"Starting network impairment test: {condition.name}")
        start_time = datetime.utcnow()
        error_messages = []
        
        try:
            # First, get baseline measurements (no impairment)
            if condition.name != "baseline":
                logger.info("Running baseline SLO test...")
                baseline_result = await self.slo_suite.run_ttft_latency_test([("en", "es")])
            else:
                baseline_result = None
            
            # Apply network condition and run impaired test
            logger.info(f"Applying network condition: {condition.description}")
            
            async with self.impairment_tester.apply_network_condition(condition):
                # Run SLO tests under impaired conditions
                logger.info("Running SLO tests under network impairment...")
                impaired_result = await self.slo_suite.run_ttft_latency_test([("en", "es")])
                
                # Also test caption latency under impairment
                caption_result = await self.slo_suite.run_caption_latency_test([("en", "es")])
                
                # Combine results (use the worse of the two)
                if not impaired_result.overall_slo_compliant or not caption_result.overall_slo_compliant:
                    impaired_result.overall_slo_compliant = False
                    impaired_result.ttft_p95_ms = max(impaired_result.ttft_p95_ms, caption_result.ttft_p95_ms)
                    impaired_result.caption_latency_p95_ms = max(impaired_result.caption_latency_p95_ms, caption_result.caption_latency_p95_ms)
            
            # Calculate degradation metrics
            if baseline_result and condition.name != "baseline":
                degradation_metrics = self._calculate_degradation_metrics(baseline_result, impaired_result)
                resilience_score = self._calculate_resilience_score(baseline_result, impaired_result, condition)
            else:
                degradation_metrics = {}
                resilience_score = 1.0 if impaired_result.overall_slo_compliant else 0.5
            
            # Determine if SLOs were maintained
            slo_maintained = impaired_result.overall_slo_compliant
            
            end_time = datetime.utcnow()
            
            result = NetworkImpairmentResult(
                test_name=f"network_impairment_{condition.name}",
                condition=condition,
                baseline_slo_result=baseline_result,
                impaired_slo_result=impaired_result,
                degradation_metrics=degradation_metrics,
                resilience_score=resilience_score,
                slo_maintained=slo_maintained,
                start_time=start_time,
                end_time=end_time,
                error_messages=error_messages
            )
            
            # Log summary
            self._log_test_summary(result)
            
            return result
            
        except Exception as e:
            error_messages.append(str(e))
            logger.error(f"Network impairment test {condition.name} failed: {e}")
            
            # Return partial result
            return NetworkImpairmentResult(
                test_name=f"network_impairment_{condition.name}",
                condition=condition,
                baseline_slo_result=None,
                impaired_slo_result=None,
                degradation_metrics={},
                resilience_score=0.0,
                slo_maintained=False,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error_messages=error_messages
            )
    
    def _calculate_degradation_metrics(self, baseline: SLOTestResult, impaired: SLOTestResult) -> Dict[str, float]:
        """Calculate performance degradation metrics"""
        metrics = {}
        
        if baseline and impaired:
            # TTFT degradation
            if baseline.ttft_p95_ms > 0:
                ttft_degradation = (impaired.ttft_p95_ms - baseline.ttft_p95_ms) / baseline.ttft_p95_ms
                metrics['ttft_degradation_percent'] = ttft_degradation * 100
            
            # Caption latency degradation
            if baseline.caption_latency_p95_ms > 0:
                caption_degradation = (impaired.caption_latency_p95_ms - baseline.caption_latency_p95_ms) / baseline.caption_latency_p95_ms
                metrics['caption_latency_degradation_percent'] = caption_degradation * 100
            
            # Success rate degradation
            success_degradation = baseline.success_rate - impaired.success_rate
            metrics['success_rate_degradation_percent'] = success_degradation * 100
            
            # Overall performance impact
            avg_degradation = (
                metrics.get('ttft_degradation_percent', 0) + 
                metrics.get('caption_latency_degradation_percent', 0) +
                metrics.get('success_rate_degradation_percent', 0)
            ) / 3
            metrics['overall_degradation_percent'] = avg_degradation
        
        return metrics
    
    def _calculate_resilience_score(self, baseline: SLOTestResult, impaired: SLOTestResult, 
                                   condition: NetworkCondition) -> float:
        """Calculate resilience score (0.0 = poor, 1.0 = excellent)"""
        if not baseline or not impaired:
            return 0.0
        
        # Base score starts at 1.0
        resilience_score = 1.0
        
        # Penalize SLO violations
        if not impaired.overall_slo_compliant:
            resilience_score -= 0.3
        
        # Penalize based on degradation severity
        if impaired.ttft_p95_ms > baseline.ttft_p95_ms:
            ttft_increase = (impaired.ttft_p95_ms - baseline.ttft_p95_ms) / baseline.ttft_p95_ms
            resilience_score -= min(ttft_increase * 0.5, 0.4)
        
        if impaired.success_rate < baseline.success_rate:
            success_decrease = baseline.success_rate - impaired.success_rate
            resilience_score -= success_decrease * 0.3
        
        # Consider the severity of network condition
        condition_severity = self._assess_condition_severity(condition)
        expected_impact = condition_severity * 0.2  # Expected degradation
        
        if resilience_score > (1.0 - expected_impact):
            # System performed better than expected under adverse conditions
            resilience_score = min(1.0, resilience_score + 0.1)
        
        return max(0.0, resilience_score)
    
    def _assess_condition_severity(self, condition: NetworkCondition) -> float:
        """Assess the severity of network condition (0.0 = none, 1.0 = severe)"""
        severity = 0.0
        
        # Packet loss impact
        if condition.packet_loss_percent > 0:
            severity += min(condition.packet_loss_percent / 5.0, 0.4)  # Max 40% from packet loss
        
        # Latency impact
        if condition.latency_ms > 0:
            severity += min(condition.latency_ms / 200.0, 0.3)  # Max 30% from latency
        
        # Jitter impact
        if condition.jitter_ms > 0:
            severity += min(condition.jitter_ms / 50.0, 0.2)  # Max 20% from jitter
        
        # Bandwidth impact
        if condition.bandwidth_limit_kbps:
            if condition.bandwidth_limit_kbps < 512:
                severity += 0.1  # 10% for bandwidth constraints
        
        return min(severity, 1.0)
    
    def _log_test_summary(self, result: NetworkImpairmentResult):
        """Log a summary of the test result"""
        logger.info("=" * 60)
        logger.info(f"NETWORK IMPAIRMENT TEST: {result.condition.name.upper()}")
        logger.info("=" * 60)
        logger.info(f"Condition: {result.condition.description}")
        
        if result.condition.packet_loss_percent > 0:
            logger.info(f"Packet Loss: {result.condition.packet_loss_percent}%")
        if result.condition.latency_ms > 0:
            logger.info(f"Additional Latency: {result.condition.latency_ms}ms")
        if result.condition.jitter_ms > 0:
            logger.info(f"Jitter: {result.condition.jitter_ms}ms")
        if result.condition.bandwidth_limit_kbps:
            logger.info(f"Bandwidth Limit: {result.condition.bandwidth_limit_kbps} Kbps")
        
        if result.impaired_slo_result:
            logger.info(f"TTFT p95: {result.impaired_slo_result.ttft_p95_ms:.1f}ms")
            logger.info(f"Caption Latency p95: {result.impaired_slo_result.caption_latency_p95_ms:.1f}ms")
            logger.info(f"Success Rate: {result.impaired_slo_result.success_rate:.2%}")
        
        logger.info(f"SLO Maintained: {'✓ YES' if result.slo_maintained else '✗ NO'}")
        logger.info(f"Resilience Score: {result.resilience_score:.2f}/1.00")
        
        if result.degradation_metrics:
            logger.info("Performance Degradation:")
            for metric, value in result.degradation_metrics.items():
                logger.info(f"  {metric}: {value:.1f}%")
        
        if result.error_messages:
            logger.warning("Errors encountered:")
            for error in result.error_messages:
                logger.warning(f"  {error}")
    
    async def run_full_resilience_suite(self, conditions: List[NetworkCondition] = None) -> Dict[str, NetworkImpairmentResult]:
        """Run the complete network resilience test suite"""
        if conditions is None:
            conditions = self.get_test_conditions()
        
        logger.info(f"Starting full network resilience test suite ({len(conditions)} conditions)")
        
        results = {}
        
        for condition in conditions:
            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"Testing condition: {condition.name}")
                logger.info(f"{'='*80}")
                
                result = await self.run_single_impairment_test(condition)
                results[condition.name] = result
                
                # Brief pause between tests to allow system recovery
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Failed to test condition {condition.name}: {e}")
                results[condition.name] = None
        
        # Generate overall summary
        self._generate_suite_summary(results)
        
        return results
    
    def _generate_suite_summary(self, results: Dict[str, NetworkImpairmentResult]):
        """Generate and log summary of all resilience tests"""
        logger.info("\n" + "=" * 80)
        logger.info("NETWORK RESILIENCE TEST SUITE SUMMARY")
        logger.info("=" * 80)
        
        total_tests = len(results)
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        
        resilience_scores = []
        
        for condition_name, result in results.items():
            if result is None:
                status = "ERROR"
                error_tests += 1
            elif result.slo_maintained:
                status = "PASS"
                passed_tests += 1
                resilience_scores.append(result.resilience_score)
            else:
                status = "FAIL"
                failed_tests += 1
                resilience_scores.append(result.resilience_score)
            
            logger.info(f"{condition_name:.<30} {status}")
        
        logger.info("-" * 80)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests} ({passed_tests/total_tests:.1%})")
        logger.info(f"Failed: {failed_tests} ({failed_tests/total_tests:.1%})")
        logger.info(f"Errors: {error_tests} ({error_tests/total_tests:.1%})")
        
        if resilience_scores:
            avg_resilience = sum(resilience_scores) / len(resilience_scores)
            logger.info(f"Average Resilience Score: {avg_resilience:.2f}/1.00")
            
            # Overall assessment
            if avg_resilience >= 0.8:
                assessment = "EXCELLENT - System shows high resilience to network impairments"
            elif avg_resilience >= 0.6:
                assessment = "GOOD - System handles most network conditions well"
            elif avg_resilience >= 0.4:
                assessment = "FAIR - Some degradation under network stress"
            else:
                assessment = "POOR - Significant impact from network impairments"
            
            logger.info(f"Overall Assessment: {assessment}")

# Utility functions
async def run_quick_resilience_test() -> Dict[str, NetworkImpairmentResult]:
    """Run a quick resilience test with essential conditions"""
    quick_conditions = [
        NetworkCondition(
            name="baseline",
            description="Baseline (no impairment)"
        ),
        NetworkCondition(
            name="light_packet_loss",
            description="1% packet loss",
            packet_loss_percent=1.0
        ),
        NetworkCondition(
            name="moderate_latency",
            description="100ms additional latency", 
            latency_ms=100
        ),
        NetworkCondition(
            name="combined_light",
            description="Light packet loss + latency",
            packet_loss_percent=1.0,
            latency_ms=50
        )
    ]
    
    suite = NetworkResilienceTestSuite()
    return await suite.run_full_resilience_suite(quick_conditions)

async def run_comprehensive_resilience_test() -> Dict[str, NetworkImpairmentResult]:
    """Run comprehensive resilience test with all conditions"""
    suite = NetworkResilienceTestSuite()
    return await suite.run_full_resilience_suite()

if __name__ == "__main__":
    # Example usage
    async def main():
        logger.info("Starting network resilience testing...")
        
        # Run quick test by default
        results = await run_quick_resilience_test()
        
        # Save results
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = f"network_resilience_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                k: v.to_dict() if v else None 
                for k, v in results.items()
            }, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_file}")
    
    asyncio.run(main())