"""
Comprehensive Testing Suite for TTS Service
Performance benchmarks, stress tests, and quality validation

Usage:
    python test_tts.py --benchmark --stress --quality
"""

import asyncio
import json
import time
import websockets
import requests
import numpy as np
import argparse
import statistics
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import pandas as pd
from concurrent.futures import asyncio as aio
import aiofiles
import wave
import os

class TTSTestSuite:
    """Comprehensive TTS testing framework"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws") + "/ws/synthesize"
        self.results: Dict = {}
        
    async def test_health_check(self) -> bool:
        """Test service health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            health_data = response.json()
            print("=== Health Check ===")
            print(f"Status: {health_data.get('status')}")
            print(f"Available Voices: {health_data.get('available_voices')}")
            print(f"Engines: {health_data.get('engines')}")
            print(f"GPU Available: {health_data.get('gpu_available')}")
            return health_data.get('status') == 'healthy'
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    async def test_voice_listing(self) -> Dict:
        """Test voice listing endpoints"""
        try:
            response = requests.get(f"{self.base_url}/voices")
            voices_data = response.json()
            print("\n=== Voice Listing ===")
            print(f"Total Voices: {voices_data.get('total_voices')}")
            print(f"Languages: {voices_data.get('languages')}")
            
            # Test language-specific endpoint
            for lang in voices_data.get('languages', [])[:3]:  # Test first 3 languages
                lang_response = requests.get(f"{self.base_url}/voices/{lang}")
                lang_data = lang_response.json()
                print(f"{lang}: {len(lang_data.get('voices', []))} voices")
                
            return voices_data
        except Exception as e:
            print(f"Voice listing test failed: {e}")
            return {}
    
    async def benchmark_ttft(self, iterations: int = 10) -> Dict:
        """Benchmark Time-to-First-Token performance"""
        print("\n=== TTFT Benchmark ===")
        
        test_texts = [
            "Hello, world!",
            "This is a longer sentence to test synthesis latency.",
            "The quick brown fox jumps over the lazy dog. This sentence contains various phonemes for comprehensive testing.",
            "Real-time translation requires ultra-low latency text-to-speech synthesis for natural conversation flow."
        ]
        
        engines = ["xtts", "piper", "speecht5", "edge-tts", "kokoro"]
        results = {}
        
        for engine in engines:
            print(f"\nTesting {engine.upper()} engine...")
            engine_results = []
            
            for text in test_texts:
                ttfts = []
                
                for i in range(iterations):
                    try:
                        async with websockets.connect(self.ws_url) as websocket:
                            request = {
                                "text": text,
                                "voice_id": "en-us-female-premium",
                                "language": "en",
                                "engine": engine,
                                "stream": True
                            }
                            
                            start_time = time.time()
                            await websocket.send(json.dumps(request))
                            
                            # Wait for first audio chunk
                            response = await websocket.recv()
                            data = json.loads(response)
                            
                            if data.get("ttft_ms"):
                                ttfts.append(data["ttft_ms"])
                            
                            # Close connection
                            await websocket.close()
                            
                    except Exception as e:
                        print(f"TTFT test failed for {engine}: {e}")
                        continue
                
                if ttfts:
                    avg_ttft = statistics.mean(ttfts)
                    p95_ttft = np.percentile(ttfts, 95)
                    engine_results.append({
                        "text_length": len(text),
                        "avg_ttft_ms": avg_ttft,
                        "p95_ttft_ms": p95_ttft,
                        "samples": len(ttfts)
                    })
                    print(f"  Text length {len(text)}: {avg_ttft:.1f}ms avg, {p95_ttft:.1f}ms p95")
            
            results[engine] = engine_results
        
        self.results["ttft_benchmark"] = results
        return results
    
    async def stress_test_concurrent_connections(self, max_connections: int = 20) -> Dict:
        """Stress test with concurrent connections"""
        print(f"\n=== Stress Test ({max_connections} concurrent connections) ===")
        
        async def single_connection_test(connection_id: int) -> Tuple[int, float, bool]:
            """Test single connection"""
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    request = {
                        "text": f"Connection {connection_id} stress test message.",
                        "voice_id": "en-us-female-premium",
                        "language": "en",
                        "engine": "piper",  # Use fastest engine for stress test
                        "stream": True
                    }
                    
                    start_time = time.time()
                    await websocket.send(json.dumps(request))
                    
                    chunks_received = 0
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        chunks_received += 1
                        
                        if data.get("is_final"):
                            break
                    
                    total_time = time.time() - start_time
                    return connection_id, total_time, True
                    
            except Exception as e:
                print(f"Connection {connection_id} failed: {e}")
                return connection_id, 0, False
        
        # Run concurrent connections
        tasks = [single_connection_test(i) for i in range(max_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_connections = [r for r in results if isinstance(r, tuple) and r[2]]
        failed_connections = len(results) - len(successful_connections)
        
        if successful_connections:
            completion_times = [r[1] for r in successful_connections]
            avg_time = statistics.mean(completion_times)
            p95_time = np.percentile(completion_times, 95)
        else:
            avg_time = p95_time = 0
        
        stress_results = {
            "max_connections": max_connections,
            "successful": len(successful_connections),
            "failed": failed_connections,
            "success_rate": len(successful_connections) / max_connections * 100,
            "avg_completion_time": avg_time,
            "p95_completion_time": p95_time
        }
        
        print(f"Success Rate: {stress_results['success_rate']:.1f}%")
        print(f"Average Completion: {avg_time:.2f}s")
        print(f"P95 Completion: {p95_time:.2f}s")
        
        self.results["stress_test"] = stress_results
        return stress_results
    
    async def test_audio_quality(self, output_dir: str = "test_outputs") -> Dict:
        """Test audio quality metrics"""
        print(f"\n=== Audio Quality Test ===")
        
        os.makedirs(output_dir, exist_ok=True)
        
        test_cases = [
            {
                "text": "The quick brown fox jumps over the lazy dog.",
                "voice_id": "en-us-female-premium",
                "language": "en",
                "engine": "xtts"
            },
            {
                "text": "Bonjour, comment allez-vous aujourd'hui?",
                "voice_id": "fr-fr-female-premium",
                "language": "fr", 
                "engine": "xtts"
            },
            {
                "text": "¡Hola! ¿Cómo está usted hoy?",
                "voice_id": "es-mx-female-premium",
                "language": "es",
                "engine": "xtts"
            }
        ]
        
        quality_results = []
        
        for i, test_case in enumerate(test_cases):
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    await websocket.send(json.dumps(test_case))
                    
                    audio_chunks = []
                    quality_scores = []
                    
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if data.get("audio_chunk"):
                            # Decode audio chunk
                            import base64
                            audio_bytes = base64.b64decode(data["audio_chunk"])
                            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                            audio_chunks.append(audio_data)
                            
                            if data.get("quality_score"):
                                quality_scores.append(data["quality_score"])
                        
                        if data.get("is_final"):
                            break
                    
                    # Save audio file
                    if audio_chunks:
                        full_audio = np.concatenate(audio_chunks)
                        filename = f"{output_dir}/test_{i}_{test_case['language']}_{test_case['engine']}.wav"
                        
                        with wave.open(filename, 'wb') as wav_file:
                            wav_file.setnchannels(1)  # Mono
                            wav_file.setsampwidth(2)  # 16-bit
                            wav_file.setframerate(16000)  # 16kHz
                            wav_file.writeframes(full_audio.tobytes())
                        
                        avg_quality = statistics.mean(quality_scores) if quality_scores else 0
                        quality_results.append({
                            "text": test_case["text"],
                            "language": test_case["language"],
                            "engine": test_case["engine"],
                            "filename": filename,
                            "duration_seconds": len(full_audio) / 16000,
                            "avg_quality_score": avg_quality,
                            "audio_samples": len(full_audio)
                        })
                        
                        print(f"{test_case['language']}-{test_case['engine']}: Quality {avg_quality:.2f}/5.0")
            
            except Exception as e:
                print(f"Quality test failed for {test_case}: {e}")
        
        self.results["quality_test"] = quality_results
        return quality_results
    
    async def test_engine_comparison(self) -> Dict:
        """Compare performance across all engines"""
        print("\n=== Engine Comparison ===")
        
        test_text = "This is a standardized test sentence for engine comparison."
        engines = ["xtts", "piper", "speecht5", "edge-tts", "kokoro"]
        
        comparison_results = {}
        
        for engine in engines:
            print(f"Testing {engine.upper()}...")
            
            try:
                start_time = time.time()
                
                async with websockets.connect(self.ws_url) as websocket:
                    request = {
                        "text": test_text,
                        "voice_id": "en-us-female-premium",
                        "language": "en",
                        "engine": engine,
                        "stream": True
                    }
                    
                    await websocket.send(json.dumps(request))
                    
                    chunks = 0
                    ttft = None
                    total_quality = 0
                    
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if data.get("ttft_ms") and ttft is None:
                            ttft = data["ttft_ms"]
                        
                        if data.get("quality_score"):
                            total_quality += data["quality_score"]
                            chunks += 1
                        
                        if data.get("is_final"):
                            break
                
                total_time = time.time() - start_time
                avg_quality = total_quality / chunks if chunks > 0 else 0
                
                comparison_results[engine] = {
                    "ttft_ms": ttft,
                    "total_time_ms": total_time * 1000,
                    "avg_quality": avg_quality,
                    "chunks": chunks,
                    "status": "success"
                }
                
                print(f"  TTFT: {ttft:.1f}ms, Total: {total_time*1000:.1f}ms, Quality: {avg_quality:.2f}")
                
            except Exception as e:
                print(f"  Failed: {e}")
                comparison_results[engine] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        self.results["engine_comparison"] = comparison_results
        return comparison_results
    
    def generate_report(self, output_file: str = "tts_test_report.html") -> None:
        """Generate comprehensive test report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TTS Service Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .section {{ margin-bottom: 30px; }}
                .metric {{ background: #f5f5f5; padding: 10px; margin: 5px 0; border-radius: 5px; }}
                .success {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>TTS Service Test Report</h1>
            <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="section">
                <h2>Test Summary</h2>
                <div class="metric">Total Tests Run: {len(self.results)}</div>
            </div>
            
            {self._generate_ttft_section()}
            {self._generate_stress_section()}
            {self._generate_quality_section()}
            {self._generate_comparison_section()}
            
            <div class="section">
                <h2>Raw Results</h2>
                <pre>{json.dumps(self.results, indent=2)}</pre>
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"\nTest report generated: {output_file}")
    
    def _generate_ttft_section(self) -> str:
        """Generate TTFT benchmark section"""
        if "ttft_benchmark" not in self.results:
            return ""
        
        html = "<div class='section'><h2>TTFT Benchmark Results</h2>"
        
        for engine, results in self.results["ttft_benchmark"].items():
            if results:
                avg_ttfts = [r["avg_ttft_ms"] for r in results]
                overall_avg = statistics.mean(avg_ttfts)
                
                status_class = "success" if overall_avg <= 250 else "warning" if overall_avg <= 500 else "error"
                html += f"<div class='metric {status_class}'>"
                html += f"<strong>{engine.upper()}</strong>: {overall_avg:.1f}ms average TTFT"
                html += "</div>"
        
        html += "</div>"
        return html
    
    def _generate_stress_section(self) -> str:
        """Generate stress test section"""
        if "stress_test" not in self.results:
            return ""
        
        result = self.results["stress_test"]
        status_class = "success" if result["success_rate"] >= 90 else "warning" if result["success_rate"] >= 70 else "error"
        
        html = f"""
        <div class='section'>
            <h2>Stress Test Results</h2>
            <div class='metric {status_class}'>
                Success Rate: {result['success_rate']:.1f}% ({result['successful']}/{result['max_connections']})
            </div>
            <div class='metric'>
                Average Completion: {result['avg_completion_time']:.2f}s
            </div>
        </div>
        """
        return html
    
    def _generate_quality_section(self) -> str:
        """Generate quality test section"""
        if "quality_test" not in self.results:
            return ""
        
        html = "<div class='section'><h2>Audio Quality Results</h2><table>"
        html += "<tr><th>Language</th><th>Engine</th><th>Quality Score</th><th>Duration</th></tr>"
        
        for result in self.results["quality_test"]:
            quality = result["avg_quality_score"]
            status_class = "success" if quality >= 3.5 else "warning" if quality >= 2.5 else "error"
            html += f"<tr class='{status_class}'>"
            html += f"<td>{result['language']}</td>"
            html += f"<td>{result['engine']}</td>"
            html += f"<td>{quality:.2f}/5.0</td>"
            html += f"<td>{result['duration_seconds']:.1f}s</td>"
            html += "</tr>"
        
        html += "</table></div>"
        return html
    
    def _generate_comparison_section(self) -> str:
        """Generate engine comparison section"""
        if "engine_comparison" not in self.results:
            return ""
        
        html = "<div class='section'><h2>Engine Comparison</h2><table>"
        html += "<tr><th>Engine</th><th>TTFT</th><th>Total Time</th><th>Quality</th><th>Status</th></tr>"
        
        for engine, result in self.results["engine_comparison"].items():
            if result["status"] == "success":
                ttft_class = "success" if result["ttft_ms"] <= 250 else "warning"
                html += f"<tr><td>{engine.upper()}</td>"
                html += f"<td class='{ttft_class}'>{result['ttft_ms']:.1f}ms</td>"
                html += f"<td>{result['total_time_ms']:.1f}ms</td>"
                html += f"<td>{result['avg_quality']:.2f}</td>"
                html += f"<td class='success'>Success</td></tr>"
            else:
                html += f"<tr><td>{engine.upper()}</td><td colspan='4' class='error'>Failed</td></tr>"
        
        html += "</table></div>"
        return html

async def main():
    """Main testing function"""
    parser = argparse.ArgumentParser(description="TTS Service Test Suite")
    parser.add_argument("--url", default="http://localhost:8003", help="TTS service URL")
    parser.add_argument("--benchmark", action="store_true", help="Run TTFT benchmark")
    parser.add_argument("--stress", action="store_true", help="Run stress test")
    parser.add_argument("--quality", action="store_true", help="Run quality test")
    parser.add_argument("--comparison", action="store_true", help="Run engine comparison")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--iterations", type=int, default=10, help="Benchmark iterations")
    parser.add_argument("--connections", type=int, default=20, help="Stress test connections")
    parser.add_argument("--output", default="tts_test_report.html", help="Report output file")
    
    args = parser.parse_args()
    
    tester = TTSTestSuite(args.url)
    
    # Health check first
    if not await tester.test_health_check():
        print("Service health check failed. Aborting tests.")
        return
    
    # Voice listing test
    await tester.test_voice_listing()
    
    # Run selected tests
    if args.all or args.benchmark:
        await tester.benchmark_ttft(args.iterations)
    
    if args.all or args.stress:
        await tester.stress_test_concurrent_connections(args.connections)
    
    if args.all or args.quality:
        await tester.test_audio_quality()
    
    if args.all or args.comparison:
        await tester.test_engine_comparison()
    
    # Generate report
    tester.generate_report(args.output)
    
    print(f"\n=== Test Summary ===")
    print(f"Tests completed: {len(tester.results)}")
    print(f"Report saved: {args.output}")

if __name__ == "__main__":
    asyncio.run(main())