"""
Synthetic Load Testing Framework for The HIVE Translation Pipeline
Implements automated load testing with realistic audio patterns and SLO validation
"""

import asyncio
import aiohttp
import numpy as np
import soundfile as sf
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import time
import json
import uuid
import logging
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
import websockets
import wave
import io

from .tracer import TranslationTracer, get_tracer
from .metrics import TranslationMetrics, get_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass 
class LoadTestConfig:
    """Configuration for synthetic load testing"""
    concurrent_speakers: int = 4
    session_duration_seconds: int = 300  # 5 minutes
    target_languages: List[str] = None
    audio_sample_rate: int = 16000
    chunk_duration_ms: int = 100
    test_scenarios: List[str] = None
    
    def __post_init__(self):
        if self.target_languages is None:
            self.target_languages = ['es', 'fr', 'de', 'ja']
        if self.test_scenarios is None:
            self.test_scenarios = ['baseline', 'peak_load', 'stress_test', 'network_impairment']

@dataclass
class LoadTestResult:
    """Results from a load test run"""
    test_id: str
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    metrics: Dict[str, Any]
    slo_violations: List[Dict[str, Any]]
    error_count: int
    success_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }

class SyntheticAudioGenerator:
    """Generates realistic synthetic audio for testing"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.speech_patterns = {
            'english': {
                'phonemes': ['ah', 'eh', 'ih', 'oh', 'oo', 'r', 'l', 'n', 'm', 's', 't', 'k'],
                'word_durations': (0.2, 0.8),  # seconds
                'pause_durations': (0.1, 0.5),
                'pitch_range': (80, 300),  # Hz
                'speech_rate': 3.5  # words per second
            },
            'spanish': {
                'phonemes': ['a', 'e', 'i', 'o', 'u', 'r', 'l', 'n', 'm', 's', 't', 'k'],
                'word_durations': (0.3, 0.9),
                'pause_durations': (0.15, 0.4),
                'pitch_range': (100, 350),
                'speech_rate': 4.0
            },
            'french': {
                'phonemes': ['a', 'e', 'i', 'o', 'u', 'r', 'l', 'n', 'm', 'j', 'v', 'z'],
                'word_durations': (0.25, 0.85),
                'pause_durations': (0.12, 0.45),
                'pitch_range': (90, 320),
                'speech_rate': 3.8
            }
        }
    
    def generate_speech_chunk(self, language: str = 'english', duration_seconds: float = 1.0) -> np.ndarray:
        """Generate a chunk of synthetic speech audio"""
        pattern = self.speech_patterns.get(language, self.speech_patterns['english'])
        
        total_samples = int(duration_seconds * self.sample_rate)
        audio = np.zeros(total_samples)
        
        current_pos = 0
        while current_pos < total_samples:
            # Generate a word
            word_duration = np.random.uniform(*pattern['word_durations'])
            word_samples = int(word_duration * self.sample_rate)
            
            if current_pos + word_samples > total_samples:
                word_samples = total_samples - current_pos
            
            # Generate phoneme sequence for this word
            pitch = np.random.uniform(*pattern['pitch_range'])
            
            # Create simple synthetic speech using formant synthesis
            t = np.linspace(0, word_duration, word_samples)
            
            # Fundamental frequency modulation
            f0 = pitch * (1 + 0.1 * np.sin(2 * np.pi * 2 * t))  # Slight intonation
            
            # Generate formants (simplified)
            formant1 = np.sin(2 * np.pi * f0 * t)  # F1
            formant2 = 0.5 * np.sin(2 * np.pi * f0 * 2.5 * t)  # F2
            formant3 = 0.3 * np.sin(2 * np.pi * f0 * 4 * t)  # F3
            
            # Combine formants
            word_audio = formant1 + formant2 + formant3
            
            # Apply envelope
            envelope = np.exp(-t / (word_duration * 0.3))  # Exponential decay
            word_audio *= envelope
            
            # Add to main audio
            audio[current_pos:current_pos + word_samples] = word_audio
            current_pos += word_samples
            
            # Add pause
            if current_pos < total_samples:
                pause_duration = np.random.uniform(*pattern['pause_durations'])
                pause_samples = min(int(pause_duration * self.sample_rate), total_samples - current_pos)
                current_pos += pause_samples
        
        # Normalize and add slight noise
        audio = audio / np.max(np.abs(audio)) * 0.8
        noise = np.random.normal(0, 0.01, len(audio))
        audio += noise
        
        return audio.astype(np.float32)
    
    def save_to_wav(self, audio: np.ndarray, filename: str):
        """Save audio array to WAV file"""
        sf.write(filename, audio, self.sample_rate)
    
    def audio_to_bytes(self, audio: np.ndarray) -> bytes:
        """Convert audio array to bytes for streaming"""
        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()

class SyntheticSpeaker:
    """Simulates a speaker in a translation session"""
    
    def __init__(self, speaker_id: str, source_language: str, target_language: str, 
                 session_duration: int, services_config: Dict[str, str]):
        self.speaker_id = speaker_id
        self.source_language = source_language
        self.target_language = target_language
        self.session_duration = session_duration
        self.services_config = services_config
        
        self.audio_generator = SyntheticAudioGenerator()
        self.tracer = get_tracer(f"synthetic-speaker-{speaker_id}")
        self.metrics = get_metrics("load-test")
        
        self.is_speaking = False
        self.session_start_time = None
        self.measurements = []
        
    async def start_translation_session(self) -> Dict[str, Any]:
        """Start a full translation session with realistic conversation"""
        self.session_start_time = datetime.utcnow()
        trace_id = self.tracer.create_trace("synthetic_translation_session", {
            "speaker_id": self.speaker_id,
            "source_language": self.source_language,
            "target_language": self.target_language
        })
        
        session_results = {
            "speaker_id": self.speaker_id,
            "trace_id": trace_id,
            "measurements": [],
            "errors": [],
            "start_time": self.session_start_time.isoformat()
        }
        
        # Generate conversation patterns
        conversation_events = self._generate_conversation_pattern()
        
        for event in conversation_events:
            try:
                if event['type'] == 'speak':
                    measurement = await self._simulate_speech_event(
                        event['duration'],
                        event['content_type']
                    )
                    session_results['measurements'].append(measurement)
                    
                elif event['type'] == 'pause':
                    await asyncio.sleep(event['duration'])
                    
            except Exception as e:
                error_info = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "event": event
                }
                session_results['errors'].append(error_info)
                logger.error(f"Error in speaker {self.speaker_id}: {e}")
        
        session_results['end_time'] = datetime.utcnow().isoformat()
        return session_results
    
    def _generate_conversation_pattern(self) -> List[Dict[str, Any]]:
        """Generate realistic conversation timing patterns"""
        events = []
        current_time = 0
        
        while current_time < self.session_duration:
            # Speaking period
            speak_duration = np.random.normal(3.0, 1.5)  # 3±1.5 seconds
            speak_duration = max(0.5, min(speak_duration, 10.0))  # Clamp to reasonable range
            
            content_types = ['question', 'statement', 'response', 'explanation']
            content_type = np.random.choice(content_types)
            
            events.append({
                'type': 'speak',
                'start_time': current_time,
                'duration': speak_duration,
                'content_type': content_type
            })
            
            current_time += speak_duration
            
            # Pause period
            if current_time < self.session_duration:
                pause_duration = np.random.exponential(2.0)  # Exponential distribution for pauses
                pause_duration = max(0.2, min(pause_duration, 8.0))  # Clamp
                
                events.append({
                    'type': 'pause',
                    'start_time': current_time,
                    'duration': pause_duration
                })
                
                current_time += pause_duration
        
        return events
    
    async def _simulate_speech_event(self, duration: float, content_type: str) -> Dict[str, Any]:
        """Simulate a single speech event through the translation pipeline"""
        measurement_start = time.time()
        
        with self.tracer.trace_operation("speech_event", {
            "duration": duration,
            "content_type": content_type,
            "language_pair": f"{self.source_language}-{self.target_language}"
        }) as span_id:
            
            # Generate synthetic audio
            audio = self.audio_generator.generate_speech_chunk(
                language=self.source_language,
                duration_seconds=duration
            )
            
            # Stream to STT service
            stt_start = time.time()
            stt_response = await self._send_to_stt(audio)
            stt_duration = time.time() - stt_start
            
            self.metrics.record_stt_processing(stt_duration, "whisper-base", f"{int(duration*1000)}ms")
            
            if not stt_response.get('success'):
                raise Exception(f"STT failed: {stt_response.get('error')}")
            
            # Send to MT service
            mt_start = time.time()
            mt_response = await self._send_to_mt(stt_response['transcript'])
            mt_duration = time.time() - mt_start
            
            self.metrics.record_mt_processing(
                mt_duration, 
                "marian", 
                f"{self.source_language}-{self.target_language}"
            )
            
            if not mt_response.get('success'):
                raise Exception(f"MT failed: {mt_response.get('error')}")
            
            # Send to TTS service
            tts_start = time.time()
            tts_response = await self._send_to_tts(mt_response['translation'])
            tts_duration = time.time() - tts_start
            
            self.metrics.record_tts_processing(tts_duration, "xtts", f"{self.target_language}-voice-1")
            
            if not tts_response.get('success'):
                raise Exception(f"TTS failed: {tts_response.get('error')}")
            
            # Calculate end-to-end metrics
            total_duration = time.time() - measurement_start
            ttft = stt_duration + mt_duration + (tts_duration * 0.1)  # Assume first audio after 10% of TTS
            
            # Record SLO metrics
            self.metrics.record_ttft(
                ttft, 
                f"{self.source_language}-{self.target_language}",
                "synthetic-v1"
            )
            
            self.metrics.record_caption_latency(
                stt_duration + mt_duration,
                f"{self.source_language}-{self.target_language}"
            )
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "span_id": span_id,
                "duration_seconds": duration,
                "content_type": content_type,
                "stt_duration_ms": stt_duration * 1000,
                "mt_duration_ms": mt_duration * 1000,
                "tts_duration_ms": tts_duration * 1000,
                "ttft_ms": ttft * 1000,
                "total_duration_ms": total_duration * 1000,
                "transcript": stt_response.get('transcript', ''),
                "translation": mt_response.get('translation', ''),
                "success": True
            }
    
    async def _send_to_stt(self, audio: np.ndarray) -> Dict[str, Any]:
        """Send audio to STT service"""
        try:
            audio_bytes = self.audio_generator.audio_to_bytes(audio)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.services_config['stt_url']}/transcribe",
                    data=audio_bytes,
                    headers={'Content-Type': 'audio/wav'}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {'success': True, 'transcript': result.get('text', '')}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _send_to_mt(self, text: str) -> Dict[str, Any]:
        """Send text to MT service"""
        try:
            payload = {
                'text': text,
                'source_language': self.source_language,
                'target_language': self.target_language
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.services_config['mt_url']}/translate",
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {'success': True, 'translation': result.get('translation', '')}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _send_to_tts(self, text: str) -> Dict[str, Any]:
        """Send text to TTS service"""
        try:
            payload = {
                'text': text,
                'language': self.target_language,
                'voice_id': f"{self.target_language}-voice-1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.services_config['tts_url']}/synthesize",
                    json=payload
                ) as response:
                    if response.status == 200:
                        return {'success': True, 'audio_generated': True}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

class SyntheticLoadRunner:
    """Main load testing orchestrator"""
    
    def __init__(self, config: LoadTestConfig, services_config: Dict[str, str]):
        self.config = config
        self.services_config = services_config
        self.tracer = get_tracer("synthetic-load-runner")
        self.metrics = get_metrics("load-test-runner")
        
    async def run_load_test(self, scenario: str = "baseline") -> LoadTestResult:
        """Execute a complete load test scenario"""
        test_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Starting load test {test_id} with scenario: {scenario}")
        
        # Create trace for entire load test
        trace_id = self.tracer.create_trace("synthetic_load_test", {
            "test_id": test_id,
            "scenario": scenario,
            "concurrent_speakers": self.config.concurrent_speakers,
            "session_duration": self.config.session_duration_seconds
        })
        
        try:
            # Configure scenario-specific parameters
            scenario_config = self._configure_scenario(scenario)
            
            # Create speakers
            speakers = self._create_synthetic_speakers(scenario_config)
            
            # Run concurrent sessions
            session_results = await self._run_concurrent_sessions(speakers)
            
            # Analyze results
            end_time = datetime.utcnow()
            result = self._analyze_results(
                test_id, start_time, end_time, session_results, scenario_config
            )
            
            logger.info(f"Load test {test_id} completed. Success rate: {result.success_rate:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"Load test {test_id} failed: {e}")
            raise
        finally:
            self.tracer.finish_span(trace_id, "completed")
    
    def _configure_scenario(self, scenario: str) -> Dict[str, Any]:
        """Configure test parameters for specific scenarios"""
        scenarios = {
            "baseline": {
                "concurrent_speakers": 2,
                "session_duration": 300,
                "language_pairs": [("en", "es"), ("en", "fr")]
            },
            "peak_load": {
                "concurrent_speakers": 8,
                "session_duration": 300,
                "language_pairs": [("en", "es"), ("en", "fr"), ("es", "en"), ("fr", "en")]
            },
            "stress_test": {
                "concurrent_speakers": 16,
                "session_duration": 600,
                "language_pairs": [("en", "es"), ("en", "fr"), ("en", "de"), ("en", "ja")]
            },
            "network_impairment": {
                "concurrent_speakers": 4,
                "session_duration": 300,
                "language_pairs": [("en", "es")],
                "network_delay_ms": 200,
                "packet_loss_rate": 0.02
            }
        }
        
        return scenarios.get(scenario, scenarios["baseline"])
    
    def _create_synthetic_speakers(self, scenario_config: Dict[str, Any]) -> List[SyntheticSpeaker]:
        """Create synthetic speaker instances"""
        speakers = []
        concurrent_count = scenario_config["concurrent_speakers"]
        language_pairs = scenario_config["language_pairs"]
        
        for i in range(concurrent_count):
            # Distribute language pairs among speakers
            source_lang, target_lang = language_pairs[i % len(language_pairs)]
            
            speaker = SyntheticSpeaker(
                speaker_id=f"speaker-{i}",
                source_language=source_lang,
                target_language=target_lang,
                session_duration=scenario_config["session_duration"],
                services_config=self.services_config
            )
            speakers.append(speaker)
        
        return speakers
    
    async def _run_concurrent_sessions(self, speakers: List[SyntheticSpeaker]) -> List[Dict[str, Any]]:
        """Run all speaker sessions concurrently"""
        logger.info(f"Starting {len(speakers)} concurrent translation sessions")
        
        tasks = [speaker.start_translation_session() for speaker in speakers]
        
        # Run with timeout to prevent hanging
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.session_duration_seconds + 60  # Extra timeout buffer
            )
            
            # Process results and handle exceptions
            session_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    session_results.append({
                        "speaker_id": f"speaker-{i}",
                        "error": str(result),
                        "success": False
                    })
                else:
                    session_results.append(result)
            
            return session_results
            
        except asyncio.TimeoutError:
            logger.error("Load test timed out")
            raise
    
    def _analyze_results(self, test_id: str, start_time: datetime, end_time: datetime,
                        session_results: List[Dict[str, Any]], scenario_config: Dict[str, Any]) -> LoadTestResult:
        """Analyze load test results and calculate SLO violations"""
        total_duration = (end_time - start_time).total_seconds()
        
        # Calculate success metrics
        successful_sessions = [r for r in session_results if r.get('success', True)]
        success_rate = len(successful_sessions) / len(session_results)
        
        # Collect all measurements
        all_measurements = []
        for session in successful_sessions:
            if 'measurements' in session:
                all_measurements.extend(session['measurements'])
        
        # Calculate performance metrics
        if all_measurements:
            ttft_values = [m['ttft_ms'] for m in all_measurements if 'ttft_ms' in m]
            caption_latencies = [m['stt_duration_ms'] + m['mt_duration_ms'] for m in all_measurements]
            
            ttft_p95 = np.percentile(ttft_values, 95) if ttft_values else 0
            caption_p95 = np.percentile(caption_latencies, 95) if caption_latencies else 0
        else:
            ttft_p95 = 0
            caption_p95 = 0
        
        # Check SLO violations
        slo_violations = []
        if ttft_p95 > 450:  # 450ms target
            slo_violations.append({
                "type": "TTFT_SLO_VIOLATION",
                "actual": ttft_p95,
                "target": 450,
                "severity": "critical"
            })
        
        if caption_p95 > 250:  # 250ms target
            slo_violations.append({
                "type": "CAPTION_LATENCY_SLO_VIOLATION", 
                "actual": caption_p95,
                "target": 250,
                "severity": "warning"
            })
        
        metrics = {
            "total_sessions": len(session_results),
            "successful_sessions": len(successful_sessions),
            "total_measurements": len(all_measurements),
            "ttft_p95_ms": ttft_p95,
            "caption_latency_p95_ms": caption_p95,
            "avg_session_duration_seconds": np.mean([
                len(s.get('measurements', [])) * 3.5 for s in successful_sessions  # Estimate
            ]) if successful_sessions else 0
        }
        
        error_count = sum(len(s.get('errors', [])) for s in session_results)
        
        return LoadTestResult(
            test_id=test_id,
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            total_duration_seconds=total_duration,
            metrics=metrics,
            slo_violations=slo_violations,
            error_count=error_count,
            success_rate=success_rate
        )

# Main execution functions
async def run_synthetic_load_test(scenario: str = "baseline") -> LoadTestResult:
    """Run a synthetic load test with specified scenario"""
    config = LoadTestConfig()
    
    services_config = {
        "stt_url": "http://localhost:8001",
        "mt_url": "http://localhost:8002", 
        "tts_url": "http://localhost:8003"
    }
    
    runner = SyntheticLoadRunner(config, services_config)
    return await runner.run_load_test(scenario)

def run_all_scenarios():
    """Run all predefined test scenarios"""
    scenarios = ["baseline", "peak_load", "stress_test", "network_impairment"]
    
    async def run_all():
        results = {}
        for scenario in scenarios:
            try:
                result = await run_synthetic_load_test(scenario)
                results[scenario] = result.to_dict()
                
                # Log summary
                print(f"\n=== {scenario.upper()} SCENARIO RESULTS ===")
                print(f"Success Rate: {result.success_rate:.2%}")
                print(f"TTFT p95: {result.metrics['ttft_p95_ms']:.1f}ms (Target: ≤450ms)")
                print(f"Caption Latency p95: {result.metrics['caption_latency_p95_ms']:.1f}ms (Target: ≤250ms)")
                print(f"SLO Violations: {len(result.slo_violations)}")
                
            except Exception as e:
                logger.error(f"Scenario {scenario} failed: {e}")
                results[scenario] = {"error": str(e)}
        
        return results
    
    return asyncio.run(run_all())

if __name__ == "__main__":
    # Example usage
    print("Starting synthetic load testing...")
    results = run_all_scenarios()
    
    # Save results to file
    with open(f"load_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)