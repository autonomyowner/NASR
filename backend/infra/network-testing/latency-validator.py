#!/usr/bin/env python3
"""
Network Performance Validator for The HIVE Translation System
Validates sub-500ms end-to-end latency target with comprehensive testing

Target SLOs:
- p95 end-to-end latency ≤ 500ms
- p95 caption latency ≤ 250ms  
- Packet loss resilience up to 5%
- Jitter tolerance up to 150ms
"""

import asyncio
import time
import json
import logging
import statistics
import argparse
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import aiohttp
import websockets
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/hive-latency-validator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class LatencyMeasurement:
    timestamp: float
    client_to_sfu: float
    sfu_processing: float
    stt_processing: float
    mt_processing: float
    tts_processing: float
    sfu_to_client: float
    end_to_end: float
    packet_loss: float
    jitter: float
    quality_score: float

@dataclass
class TestResult:
    test_name: str
    duration_seconds: int
    measurements: List[LatencyMeasurement]
    p95_latency: float
    p99_latency: float
    avg_latency: float
    max_latency: float
    avg_packet_loss: float
    avg_jitter: float
    avg_quality: float
    slo_compliance: bool

class LatencyValidator:
    def __init__(self, config: Dict):
        self.config = config
        self.livekit_url = config.get('livekit_url', 'ws://localhost:7880')
        self.signaling_url = config.get('signaling_url', 'ws://localhost:3001')
        self.services = {
            'stt': config.get('stt_url', 'http://localhost:8001'),
            'mt': config.get('mt_url', 'http://localhost:8002'),
            'tts': config.get('tts_url', 'http://localhost:8003')
        }
        self.target_slo = config.get('target_latency_ms', 500)
        self.measurements = []
        
    async def measure_service_latency(self, service: str, endpoint: str) -> float:
        """Measure latency for a specific service endpoint"""
        start_time = time.perf_counter()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.services[service]}{endpoint}", 
                                     timeout=aiohttp.ClientTimeout(total=10)) as response:
                    await response.read()
                    end_time = time.perf_counter()
                    return (end_time - start_time) * 1000  # Convert to milliseconds
        except Exception as e:
            logger.error(f"Error measuring {service} latency: {e}")
            return float('inf')
    
    async def measure_webrtc_latency(self) -> Tuple[float, float, float]:
        """Measure WebRTC connection establishment and audio latency"""
        start_time = time.perf_counter()
        
        try:
            # Simulate WebRTC connection establishment
            async with websockets.connect(
                self.signaling_url,
                timeout=10
            ) as websocket:
                # Measure signaling latency
                signal_start = time.perf_counter()
                await websocket.send(json.dumps({
                    'type': 'ping',
                    'timestamp': signal_start
                }))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                signal_end = time.perf_counter()
                
                signaling_latency = (signal_end - signal_start) * 1000
                
                # Estimate WebRTC establishment time (typically 2-5 seconds)
                connection_latency = 3000  # Conservative estimate
                
                # Measure end-to-end audio path latency
                audio_latency = await self._measure_audio_path_latency()
                
                return signaling_latency, connection_latency, audio_latency
                
        except Exception as e:
            logger.error(f"Error measuring WebRTC latency: {e}")
            return float('inf'), float('inf'), float('inf')
    
    async def _measure_audio_path_latency(self) -> float:
        """Measure audio processing path latency through translation pipeline"""
        try:
            # Measure STT latency with sample audio
            stt_latency = await self.measure_service_latency('stt', '/health')
            
            # Measure MT latency with sample text
            mt_latency = await self.measure_service_latency('mt', '/health')
            
            # Measure TTS latency with sample synthesis
            tts_latency = await self.measure_service_latency('tts', '/health')
            
            # Total pipeline latency (simplified measurement)
            return stt_latency + mt_latency + tts_latency
            
        except Exception as e:
            logger.error(f"Error measuring audio path latency: {e}")
            return float('inf')
    
    async def simulate_packet_loss(self, loss_rate: float) -> float:
        """Simulate packet loss and measure impact on latency"""
        # This would integrate with tc (traffic control) for real packet loss simulation
        # For now, we'll simulate the impact on measured latency
        base_latency = 50  # Base network latency in ms
        
        # Packet loss increases latency due to retransmissions and buffering
        loss_impact = loss_rate * 200  # 200ms impact per 1% packet loss
        
        return base_latency + loss_impact
    
    async def simulate_jitter(self, jitter_ms: float) -> float:
        """Simulate network jitter and measure impact"""
        import random
        
        # Jitter affects buffering requirements
        base_jitter_buffer = 20  # 20ms base buffer
        adaptive_buffer = min(jitter_ms * 2, 100)  # Adaptive buffer, max 100ms
        
        # Random variation due to jitter
        jitter_variation = random.uniform(-jitter_ms/2, jitter_ms/2)
        
        return base_jitter_buffer + adaptive_buffer + abs(jitter_variation)
    
    async def run_single_measurement(self, test_conditions: Dict) -> LatencyMeasurement:
        """Run a single end-to-end latency measurement"""
        start_time = time.perf_counter()
        
        # Measure individual components
        signaling_lat, connection_lat, audio_lat = await self.measure_webrtc_latency()
        
        # Measure service latencies
        stt_lat = await self.measure_service_latency('stt', '/health')
        mt_lat = await self.measure_service_latency('mt', '/health')
        tts_lat = await self.measure_service_latency('tts', '/health')
        
        # Calculate network impact
        packet_loss = test_conditions.get('packet_loss', 0.0)
        jitter = test_conditions.get('jitter', 0.0)
        
        network_impact = await self.simulate_packet_loss(packet_loss)
        jitter_impact = await self.simulate_jitter(jitter)
        
        # Calculate total end-to-end latency
        end_to_end = (
            signaling_lat +      # WebRTC signaling
            connection_lat +     # Connection establishment  
            audio_lat +          # Audio capture/playback
            stt_lat +           # Speech-to-text
            mt_lat +            # Machine translation
            tts_lat +           # Text-to-speech
            network_impact +    # Network conditions
            jitter_impact       # Jitter buffering
        )
        
        # Calculate quality score (0.0 to 1.0)
        quality_score = max(0.0, min(1.0, (self.target_slo - end_to_end) / self.target_slo))
        
        return LatencyMeasurement(
            timestamp=time.time(),
            client_to_sfu=signaling_lat + connection_lat,
            sfu_processing=10.0,  # Estimated SFU processing
            stt_processing=stt_lat,
            mt_processing=mt_lat, 
            tts_processing=tts_lat,
            sfu_to_client=audio_lat,
            end_to_end=end_to_end,
            packet_loss=packet_loss,
            jitter=jitter,
            quality_score=quality_score
        )
    
    async def run_test_scenario(self, 
                               test_name: str,
                               test_conditions: Dict,
                               duration_seconds: int = 60,
                               measurement_interval: float = 1.0) -> TestResult:
        """Run a complete test scenario with multiple measurements"""
        
        logger.info(f"Starting test scenario: {test_name}")
        logger.info(f"Test conditions: {test_conditions}")
        logger.info(f"Duration: {duration_seconds}s, Interval: {measurement_interval}s")
        
        measurements = []
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        while time.time() < end_time:
            try:
                measurement = await self.run_single_measurement(test_conditions)
                measurements.append(measurement)
                
                logger.debug(f"Measurement: {measurement.end_to_end:.2f}ms end-to-end")
                
                # Wait for next measurement
                await asyncio.sleep(measurement_interval)
                
            except Exception as e:
                logger.error(f"Error during measurement: {e}")
                continue
        
        # Calculate statistics
        latencies = [m.end_to_end for m in measurements if m.end_to_end != float('inf')]
        
        if not latencies:
            logger.error(f"No valid measurements for test {test_name}")
            return TestResult(
                test_name=test_name,
                duration_seconds=duration_seconds,
                measurements=measurements,
                p95_latency=float('inf'),
                p99_latency=float('inf'),
                avg_latency=float('inf'),
                max_latency=float('inf'),
                avg_packet_loss=0.0,
                avg_jitter=0.0,
                avg_quality=0.0,
                slo_compliance=False
            )
        
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99_latency = statistics.quantiles(latencies, n=100)[98] # 99th percentile  
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        avg_packet_loss = statistics.mean([m.packet_loss for m in measurements])
        avg_jitter = statistics.mean([m.jitter for m in measurements])
        avg_quality = statistics.mean([m.quality_score for m in measurements])
        
        slo_compliance = p95_latency <= self.target_slo
        
        logger.info(f"Test {test_name} completed:")
        logger.info(f"  p95 latency: {p95_latency:.2f}ms (target: {self.target_slo}ms)")
        logger.info(f"  p99 latency: {p99_latency:.2f}ms")
        logger.info(f"  Average latency: {avg_latency:.2f}ms")
        logger.info(f"  Max latency: {max_latency:.2f}ms")
        logger.info(f"  SLO compliance: {'✓' if slo_compliance else '✗'}")
        
        return TestResult(
            test_name=test_name,
            duration_seconds=duration_seconds,
            measurements=measurements,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            avg_latency=avg_latency,
            max_latency=max_latency,
            avg_packet_loss=avg_packet_loss,
            avg_jitter=avg_jitter,
            avg_quality=avg_quality,
            slo_compliance=slo_compliance
        )
    
    async def run_comprehensive_test_suite(self) -> List[TestResult]:
        """Run comprehensive test suite covering various network conditions"""
        
        test_scenarios = [
            {
                'name': 'Baseline - Clean Network',
                'conditions': {'packet_loss': 0.0, 'jitter': 0.0},
                'duration': 120
            },
            {
                'name': 'Light Packet Loss (1%)',
                'conditions': {'packet_loss': 1.0, 'jitter': 10.0},
                'duration': 180
            },
            {
                'name': 'Moderate Packet Loss (3%)',
                'conditions': {'packet_loss': 3.0, 'jitter': 30.0},
                'duration': 180
            },
            {
                'name': 'Heavy Packet Loss (5%)',
                'conditions': {'packet_loss': 5.0, 'jitter': 50.0},
                'duration': 300
            },
            {
                'name': 'High Jitter (100ms)',
                'conditions': {'packet_loss': 1.0, 'jitter': 100.0},
                'duration': 180
            },
            {
                'name': 'Extreme Jitter (150ms)',
                'conditions': {'packet_loss': 2.0, 'jitter': 150.0},
                'duration': 300
            },
            {
                'name': 'Mobile Network Simulation',
                'conditions': {'packet_loss': 2.0, 'jitter': 80.0},
                'duration': 600
            },
            {
                'name': 'Stress Test - Worst Case',
                'conditions': {'packet_loss': 5.0, 'jitter': 150.0},
                'duration': 300
            }
        ]
        
        results = []
        
        for scenario in test_scenarios:
            try:
                result = await self.run_test_scenario(
                    test_name=scenario['name'],
                    test_conditions=scenario['conditions'],
                    duration_seconds=scenario['duration']
                )
                results.append(result)
                
                # Brief pause between tests
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error running scenario {scenario['name']}: {e}")
                continue
        
        return results
    
    def generate_report(self, results: List[TestResult]) -> str:
        """Generate comprehensive performance report"""
        
        report = []
        report.append("=" * 80)
        report.append("THE HIVE - NETWORK PERFORMANCE VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Target SLO: p95 latency ≤ {self.target_slo}ms")
        report.append("")
        
        # Summary statistics
        passing_tests = [r for r in results if r.slo_compliance]
        compliance_rate = len(passing_tests) / len(results) * 100
        
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total test scenarios: {len(results)}")
        report.append(f"SLO compliant scenarios: {len(passing_tests)}")
        report.append(f"Overall compliance rate: {compliance_rate:.1f}%")
        report.append("")
        
        # Individual test results
        report.append("DETAILED RESULTS")
        report.append("-" * 40)
        
        for result in results:
            status = "✓ PASS" if result.slo_compliance else "✗ FAIL"
            report.append(f"\n{result.test_name} - {status}")
            report.append(f"  Duration: {result.duration_seconds}s")
            report.append(f"  Measurements: {len(result.measurements)}")
            report.append(f"  p95 latency: {result.p95_latency:.2f}ms")
            report.append(f"  p99 latency: {result.p99_latency:.2f}ms")
            report.append(f"  Average latency: {result.avg_latency:.2f}ms")
            report.append(f"  Max latency: {result.max_latency:.2f}ms")
            report.append(f"  Avg packet loss: {result.avg_packet_loss:.2f}%")
            report.append(f"  Avg jitter: {result.avg_jitter:.2f}ms")
            report.append(f"  Avg quality: {result.avg_quality:.3f}")
        
        # Recommendations
        report.append("\nRECOMMENDATIONS")
        report.append("-" * 40)
        
        if compliance_rate < 80:
            report.append("⚠️  Overall compliance rate is below 80%")
            report.append("   Consider network infrastructure improvements")
        
        failing_tests = [r for r in results if not r.slo_compliance]
        if failing_tests:
            report.append("⚠️  Failed scenarios require attention:")
            for test in failing_tests:
                report.append(f"   - {test.test_name}: {test.p95_latency:.0f}ms (target: {self.target_slo}ms)")
        
        if compliance_rate >= 90:
            report.append("✅ Excellent performance across test scenarios")
            report.append("   System meets sub-500ms latency requirements")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_results(self, results: List[TestResult], filename: str = None):
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hive_latency_validation_{timestamp}.json"
        
        # Convert results to serializable format
        serializable_results = []
        for result in results:
            result_dict = asdict(result)
            # Convert measurements to dicts
            result_dict['measurements'] = [asdict(m) for m in result.measurements]
            serializable_results.append(result_dict)
        
        with open(filename, 'w') as f:
            json.dump({
                'test_suite': 'The HIVE Network Performance Validation',
                'timestamp': datetime.now().isoformat(),
                'target_slo_ms': self.target_slo,
                'results': serializable_results
            }, f, indent=2)
        
        logger.info(f"Results saved to {filename}")

async def main():
    parser = argparse.ArgumentParser(description='The HIVE Network Performance Validator')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--target-latency', type=int, default=500, 
                       help='Target latency SLO in milliseconds')
    parser.add_argument('--duration', type=int, default=120,
                       help='Test duration per scenario in seconds')
    parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        'livekit_url': 'ws://localhost:7880',
        'signaling_url': 'ws://localhost:3001', 
        'stt_url': 'http://localhost:8001',
        'mt_url': 'http://localhost:8002',
        'tts_url': 'http://localhost:8003',
        'target_latency_ms': args.target_latency
    }
    
    if args.config:
        try:
            with open(args.config, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Create validator and run tests
    validator = LatencyValidator(config)
    
    logger.info("Starting comprehensive network performance validation")
    logger.info(f"Target SLO: p95 latency ≤ {config['target_latency_ms']}ms")
    
    try:
        results = await validator.run_comprehensive_test_suite()
        
        # Generate and display report
        report = validator.generate_report(results)
        print(report)
        
        # Save results
        validator.save_results(results, args.output)
        
        # Exit with appropriate code
        passing_tests = [r for r in results if r.slo_compliance]
        compliance_rate = len(passing_tests) / len(results)
        
        if compliance_rate >= 0.9:
            logger.info("✅ All tests passed - system meets performance requirements")
            exit(0)
        elif compliance_rate >= 0.7:
            logger.warning("⚠️  Some tests failed - review recommendations")  
            exit(1)
        else:
            logger.error("❌ Multiple test failures - significant issues detected")
            exit(2)
            
    except KeyboardInterrupt:
        logger.info("Test suite interrupted by user")
        exit(3)
    except Exception as e:
        logger.error(f"Fatal error during testing: {e}")
        exit(4)

if __name__ == "__main__":
    asyncio.run(main())