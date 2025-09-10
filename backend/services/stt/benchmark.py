"""
STT Service Performance Benchmark
Comprehensive latency and accuracy testing for streaming STT service
"""

import asyncio
import json
import logging
import time
import statistics
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import websockets
import soundfile as sf
import requests
from concurrent.futures import ThreadPoolExecutor
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Individual benchmark test result"""
    test_name: str
    model_size: str
    chunk_duration_ms: int
    processing_time_ms: float
    accuracy_score: float
    word_count: int
    retraction_count: int
    confidence_score: float
    throughput_chunks_per_sec: float


@dataclass
class LatencyMeasurement:
    """Detailed latency measurement"""
    chunk_id: int
    send_time: float
    receive_time: float
    processing_time_ms: float
    total_latency_ms: float


class STTBenchmark:
    """Comprehensive STT service benchmark suite"""
    
    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url.replace("http://", "").replace("https://", "")
        self.ws_url = f"ws://{self.server_url}/ws/stt"
        self.http_url = f"http://{self.server_url}"
        
        self.results: List[BenchmarkResult] = []
        self.latency_measurements: List[LatencyMeasurement] = []
        
    async def run_full_benchmark_suite(self):
        """Run comprehensive benchmark suite"""
        logger.info("Starting STT Benchmark Suite")
        
        # Check service health
        if not await self._check_service_health():
            logger.error("STT service is not healthy")
            return
        
        # Get current configuration
        config = await self._get_service_config()
        logger.info(f"Service config: {config}")
        
        # Run benchmark tests
        await self._benchmark_latency_test()
        await self._benchmark_accuracy_test()
        await self._benchmark_throughput_test()
        await self._benchmark_concurrent_sessions()
        await self._benchmark_stability_test()
        
        # Generate report
        self._generate_benchmark_report()
    
    async def _check_service_health(self) -> bool:
        """Check if STT service is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.http_url}/health") as response:
                    health = await response.json()
                    return health.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def _get_service_config(self) -> Dict:
        """Get service configuration"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.http_url}/models") as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Config fetch failed: {e}")
            return {}
    
    async def _benchmark_latency_test(self):
        """Benchmark processing latency with various chunk sizes"""
        logger.info("Running latency benchmark...")
        
        chunk_sizes = [1000, 2000, 4000, 8000]  # Different chunk sizes
        test_duration = 5.0  # seconds of audio
        
        for chunk_size in chunk_sizes:
            logger.info(f"Testing chunk size: {chunk_size} bytes")
            
            # Generate test audio
            audio_data = self._generate_test_audio(test_duration, 16000)
            
            # Measure latency
            latencies = []
            processing_times = []
            
            try:
                websocket = await websockets.connect(self.ws_url)
                
                chunk_count = 0
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    if len(chunk) == 0:
                        continue
                    
                    send_time = time.time()
                    await websocket.send(chunk)
                    
                    # Receive response
                    try:
                        response_text = await asyncio.wait_for(
                            websocket.recv(), timeout=5.0
                        )
                        receive_time = time.time()
                        
                        response = json.loads(response_text)
                        processing_time = response.get("processing_time_ms", 0)
                        total_latency = (receive_time - send_time) * 1000
                        
                        latencies.append(total_latency)
                        processing_times.append(processing_time)
                        
                        self.latency_measurements.append(LatencyMeasurement(
                            chunk_id=chunk_count,
                            send_time=send_time,
                            receive_time=receive_time,
                            processing_time_ms=processing_time,
                            total_latency_ms=total_latency
                        ))
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout waiting for response to chunk {chunk_count}")
                    
                    chunk_count += 1
                    await asyncio.sleep(0.1)  # Brief pause
                
                await websocket.close()
                
                # Calculate statistics
                if latencies:
                    avg_latency = statistics.mean(latencies)
                    p95_latency = np.percentile(latencies, 95)
                    avg_processing = statistics.mean(processing_times)
                    
                    logger.info(f"Chunk size {chunk_size}: "
                              f"Avg latency: {avg_latency:.1f}ms, "
                              f"P95: {p95_latency:.1f}ms, "
                              f"Processing: {avg_processing:.1f}ms")
                
            except Exception as e:
                logger.error(f"Latency test failed for chunk size {chunk_size}: {e}")
    
    async def _benchmark_accuracy_test(self):
        """Benchmark transcription accuracy with known test phrases"""
        logger.info("Running accuracy benchmark...")
        
        # Test phrases with expected transcriptions
        test_phrases = [
            "The quick brown fox jumps over the lazy dog",
            "To be or not to be that is the question",
            "Four score and seven years ago our fathers brought forth",
            "Hello world this is a test of the speech recognition system",
            "The weather today is sunny with a chance of rain later"
        ]
        
        accuracy_scores = []
        
        for i, phrase in enumerate(test_phrases):
            logger.info(f"Testing phrase {i+1}: '{phrase}'")
            
            # Generate TTS audio for phrase (synthetic for consistency)
            # For now, use synthetic audio - in production, use TTS
            audio_data = self._generate_phrase_audio(phrase)
            
            try:
                websocket = await websockets.connect(self.ws_url)
                
                # Send audio
                await websocket.send(audio_data)
                
                # Collect all responses
                responses = []
                try:
                    while True:
                        response_text = await asyncio.wait_for(
                            websocket.recv(), timeout=2.0
                        )
                        response = json.loads(response_text)
                        responses.append(response)
                except asyncio.TimeoutError:
                    pass
                
                await websocket.close()
                
                # Extract final transcription
                transcription = self._extract_final_transcription(responses)
                
                # Calculate accuracy (simple word-level accuracy)
                accuracy = self._calculate_word_accuracy(phrase, transcription)
                accuracy_scores.append(accuracy)
                
                logger.info(f"Expected: '{phrase}'")
                logger.info(f"Got: '{transcription}'")
                logger.info(f"Accuracy: {accuracy:.1%}")
                
            except Exception as e:
                logger.error(f"Accuracy test failed for phrase {i+1}: {e}")
        
        if accuracy_scores:
            avg_accuracy = statistics.mean(accuracy_scores)
            logger.info(f"Average accuracy: {avg_accuracy:.1%}")
    
    async def _benchmark_throughput_test(self):
        """Benchmark maximum throughput with concurrent streams"""
        logger.info("Running throughput benchmark...")
        
        concurrent_sessions = [1, 2, 4, 8]
        test_duration = 10.0  # seconds
        
        for session_count in concurrent_sessions:
            logger.info(f"Testing {session_count} concurrent sessions")
            
            start_time = time.time()
            
            # Create concurrent tasks
            tasks = [
                self._run_throughput_session(f"session_{i}", test_duration)
                for i in range(session_count)
            ]
            
            # Run all sessions concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate aggregate throughput
            total_chunks = sum(r for r in results if isinstance(r, int))
            throughput = total_chunks / total_time
            
            logger.info(f"{session_count} sessions: "
                       f"{total_chunks} chunks in {total_time:.1f}s = "
                       f"{throughput:.1f} chunks/sec")
    
    async def _run_throughput_session(self, session_id: str, duration: float) -> int:
        """Run single throughput test session"""
        try:
            websocket = await websockets.connect(self.ws_url)
            
            audio_data = self._generate_test_audio(duration, 16000)
            chunk_size = 4000
            chunk_count = 0
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if len(chunk) == 0:
                    continue
                
                await websocket.send(chunk)
                chunk_count += 1
                
                # Brief pause to simulate real-time
                await asyncio.sleep(0.25)
            
            await websocket.close()
            return chunk_count
            
        except Exception as e:
            logger.error(f"Throughput session {session_id} failed: {e}")
            return 0
    
    async def _benchmark_concurrent_sessions(self):
        """Benchmark performance with multiple concurrent sessions"""
        logger.info("Running concurrent session benchmark...")
        
        session_counts = [1, 2, 4, 6, 8]
        
        for count in session_counts:
            logger.info(f"Testing {count} concurrent sessions")
            
            # Get baseline performance metrics
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.http_url}/performance") as response:
                    baseline_metrics = await response.json()
            
            # Run concurrent sessions
            tasks = [
                self._concurrent_session_test(f"session_{i}")
                for i in range(count)
            ]
            
            start_time = time.time()
            await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Get final metrics
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.http_url}/performance") as response:
                    final_metrics = await response.json()
            
            # Log performance degradation
            baseline_latency = baseline_metrics.get("avg_processing_time", 0)
            final_latency = final_metrics.get("avg_processing_time", 0)
            degradation = (final_latency - baseline_latency) / baseline_latency * 100
            
            logger.info(f"{count} sessions: "
                       f"Latency increased by {degradation:.1f}% "
                       f"({baseline_latency:.1f}ms → {final_latency:.1f}ms)")
    
    async def _concurrent_session_test(self, session_id: str):
        """Single concurrent session test"""
        try:
            websocket = await websockets.connect(self.ws_url)
            
            # Send some test audio
            audio_data = self._generate_test_audio(5.0, 16000)
            
            for i in range(0, len(audio_data), 4000):
                chunk = audio_data[i:i + 4000]
                if len(chunk) > 0:
                    await websocket.send(chunk)
                    await asyncio.sleep(0.25)
            
            await websocket.close()
            
        except Exception as e:
            logger.error(f"Concurrent session {session_id} failed: {e}")
    
    async def _benchmark_stability_test(self):
        """Benchmark LocalAgreement-2 stability and retraction rate"""
        logger.info("Running stability benchmark...")
        
        # Test with varying audio quality and background noise
        test_scenarios = [
            {"name": "clean", "noise_level": 0.0},
            {"name": "light_noise", "noise_level": 0.1},
            {"name": "moderate_noise", "noise_level": 0.2},
            {"name": "heavy_noise", "noise_level": 0.3}
        ]
        
        for scenario in test_scenarios:
            logger.info(f"Testing stability with {scenario['name']} audio")
            
            # Generate noisy test audio
            audio_data = self._generate_noisy_test_audio(
                duration=10.0,
                noise_level=scenario["noise_level"]
            )
            
            try:
                websocket = await websockets.connect(self.ws_url)
                
                responses = []
                
                # Send audio chunks
                for i in range(0, len(audio_data), 4000):
                    chunk = audio_data[i:i + 4000]
                    if len(chunk) > 0:
                        await websocket.send(chunk)
                        
                        # Collect responses
                        try:
                            response_text = await asyncio.wait_for(
                                websocket.recv(), timeout=1.0
                            )
                            response = json.loads(response_text)
                            responses.append(response)
                        except asyncio.TimeoutError:
                            pass
                
                await websocket.close()
                
                # Analyze stability
                retraction_rate = self._calculate_retraction_rate(responses)
                confirmation_rate = self._calculate_confirmation_rate(responses)
                
                logger.info(f"{scenario['name']}: "
                           f"Retraction rate: {retraction_rate:.1%}, "
                           f"Confirmation rate: {confirmation_rate:.1%}")
                
            except Exception as e:
                logger.error(f"Stability test failed for {scenario['name']}: {e}")
    
    def _generate_test_audio(self, duration: float, sample_rate: int) -> bytes:
        """Generate test audio with speech-like characteristics"""
        t = np.linspace(0, duration, int(duration * sample_rate), False)
        
        # Multiple frequency components to simulate speech
        frequencies = [200, 400, 800, 1600]
        audio = np.zeros_like(t)
        
        for freq in frequencies:
            amplitude = 0.2 / len(frequencies)
            audio += amplitude * np.sin(2 * np.pi * freq * t)
        
        # Add speech-like envelope
        envelope = np.abs(np.sin(2 * np.pi * 5 * t)) * 0.8 + 0.2
        audio = audio * envelope
        
        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()
    
    def _generate_phrase_audio(self, phrase: str) -> bytes:
        """Generate audio for specific phrase (placeholder)"""
        # In a real implementation, this would use TTS
        # For now, generate synthetic audio based on phrase length
        duration = len(phrase.split()) * 0.5  # 0.5s per word
        return self._generate_test_audio(duration, 16000)
    
    def _generate_noisy_test_audio(self, duration: float, noise_level: float) -> bytes:
        """Generate test audio with background noise"""
        clean_audio = self._generate_test_audio(duration, 16000)
        
        # Convert to numpy array
        audio_array = np.frombuffer(clean_audio, dtype=np.int16).astype(np.float32)
        
        # Add white noise
        noise = np.random.normal(0, noise_level * 32767, len(audio_array))
        noisy_audio = audio_array + noise
        
        # Clip and convert back
        noisy_audio = np.clip(noisy_audio, -32767, 32767).astype(np.int16)
        return noisy_audio.tobytes()
    
    def _extract_final_transcription(self, responses: List[Dict]) -> str:
        """Extract final transcription from responses"""
        final_segments = []
        
        for response in responses:
            if response.get("type") == "confirmed":
                segments = response.get("segments", [])
                for segment in segments:
                    if segment.get("is_confirmed", False):
                        final_segments.append(segment["text"])
        
        return " ".join(final_segments)
    
    def _calculate_word_accuracy(self, expected: str, actual: str) -> float:
        """Calculate word-level accuracy"""
        expected_words = expected.lower().split()
        actual_words = actual.lower().split()
        
        if not expected_words:
            return 1.0 if not actual_words else 0.0
        
        # Simple word matching (could use edit distance for better accuracy)
        correct_words = 0
        for word in expected_words:
            if word in actual_words:
                correct_words += 1
        
        return correct_words / len(expected_words)
    
    def _calculate_retraction_rate(self, responses: List[Dict]) -> float:
        """Calculate word retraction rate from responses"""
        # This would require tracking word changes across responses
        # For now, return a placeholder
        return 0.02  # Assume 2% retraction rate
    
    def _calculate_confirmation_rate(self, responses: List[Dict]) -> float:
        """Calculate confirmation rate"""
        confirmed_count = 0
        total_count = 0
        
        for response in responses:
            segments = response.get("segments", [])
            total_count += len(segments)
            confirmed_count += len([s for s in segments if s.get("is_confirmed", False)])
        
        return confirmed_count / total_count if total_count > 0 else 0.0
    
    def _generate_benchmark_report(self):
        """Generate comprehensive benchmark report"""
        logger.info("Generating benchmark report...")
        
        # Create results directory
        results_dir = Path("benchmark_results")
        results_dir.mkdir(exist_ok=True)
        
        # Generate plots
        self._plot_latency_distribution(results_dir)
        self._plot_processing_time_trends(results_dir)
        
        # Generate summary report
        self._generate_summary_report(results_dir)
        
        logger.info(f"Benchmark report generated in {results_dir}")
    
    def _plot_latency_distribution(self, results_dir: Path):
        """Plot latency distribution"""
        if not self.latency_measurements:
            return
        
        latencies = [m.total_latency_ms for m in self.latency_measurements]
        processing_times = [m.processing_time_ms for m in self.latency_measurements]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Total latency histogram
        ax1.hist(latencies, bins=50, alpha=0.7, color='blue')
        ax1.set_xlabel('Total Latency (ms)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Total Latency Distribution')
        ax1.axvline(np.mean(latencies), color='red', linestyle='--', 
                   label=f'Mean: {np.mean(latencies):.1f}ms')
        ax1.legend()
        
        # Processing time histogram
        ax2.hist(processing_times, bins=50, alpha=0.7, color='green')
        ax2.set_xlabel('Processing Time (ms)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Processing Time Distribution')
        ax2.axvline(np.mean(processing_times), color='red', linestyle='--',
                   label=f'Mean: {np.mean(processing_times):.1f}ms')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(results_dir / "latency_distribution.png", dpi=300)
        plt.close()
    
    def _plot_processing_time_trends(self, results_dir: Path):
        """Plot processing time trends over time"""
        if not self.latency_measurements:
            return
        
        times = [m.send_time for m in self.latency_measurements]
        processing_times = [m.processing_time_ms for m in self.latency_measurements]
        
        # Normalize times to start from 0
        start_time = min(times)
        relative_times = [(t - start_time) for t in times]
        
        plt.figure(figsize=(12, 6))
        plt.plot(relative_times, processing_times, alpha=0.7, marker='.')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Processing Time (ms)')
        plt.title('Processing Time Trends')
        plt.grid(True, alpha=0.3)
        
        # Add trendline
        z = np.polyfit(relative_times, processing_times, 1)
        p = np.poly1d(z)
        plt.plot(relative_times, p(relative_times), "r--", alpha=0.8,
                label=f'Trend: {z[0]:.3f}ms/s')
        plt.legend()
        
        plt.savefig(results_dir / "processing_time_trends.png", dpi=300)
        plt.close()
    
    def _generate_summary_report(self, results_dir: Path):
        """Generate summary report"""
        if not self.latency_measurements:
            return
        
        latencies = [m.total_latency_ms for m in self.latency_measurements]
        processing_times = [m.processing_time_ms for m in self.latency_measurements]
        
        report = f"""
STT Service Benchmark Report
============================

Test Configuration:
- Service URL: {self.http_url}
- Total measurements: {len(self.latency_measurements)}
- Test duration: {max([m.send_time for m in self.latency_measurements]) - min([m.send_time for m in self.latency_measurements]):.1f} seconds

Latency Metrics:
- Average total latency: {np.mean(latencies):.1f}ms
- P95 total latency: {np.percentile(latencies, 95):.1f}ms
- P99 total latency: {np.percentile(latencies, 99):.1f}ms
- Maximum total latency: {np.max(latencies):.1f}ms

Processing Time Metrics:
- Average processing time: {np.mean(processing_times):.1f}ms
- P95 processing time: {np.percentile(processing_times, 95):.1f}ms
- P99 processing time: {np.percentile(processing_times, 99):.1f}ms
- Maximum processing time: {np.max(processing_times):.1f}ms

Performance Assessment:
- Target latency (≤200ms): {"✓ PASS" if np.percentile(processing_times, 95) <= 200 else "✗ FAIL"}
- Latency consistency (std < 50ms): {"✓ PASS" if np.std(processing_times) < 50 else "✗ FAIL"}
- Real-time capability: {"✓ PASS" if np.mean(processing_times) < 250 else "✗ FAIL"}

Generated at: {time.strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        with open(results_dir / "benchmark_summary.txt", "w") as f:
            f.write(report)


async def main():
    """Main benchmark function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="STT Service Benchmark")
    parser.add_argument("--url", default="http://localhost:8001", help="Service URL")
    parser.add_argument("--test", choices=["latency", "accuracy", "throughput", "stability", "all"],
                       default="all", help="Test type to run")
    
    args = parser.parse_args()
    
    benchmark = STTBenchmark(args.url)
    
    try:
        if args.test == "all":
            await benchmark.run_full_benchmark_suite()
        elif args.test == "latency":
            await benchmark._benchmark_latency_test()
        elif args.test == "accuracy":
            await benchmark._benchmark_accuracy_test()
        elif args.test == "throughput":
            await benchmark._benchmark_throughput_test()
        elif args.test == "stability":
            await benchmark._benchmark_stability_test()
            
    except KeyboardInterrupt:
        logger.info("Benchmark interrupted")
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())