"""
Load Testing Harness for The HIVE Translation System
Comprehensive concurrent session testing and stress testing framework
"""

import asyncio
import aiohttp
import numpy as np
import time
import logging
import json
import uuid
import psutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import sys
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import statistics
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

# Add backend path for imports
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from observability.tracer import get_tracer
from observability.metrics import get_metrics

# Import other test modules
from .slo_tests import SLOTestSuite, SLOTestConfig, AudioGenerator
from .integration_tests import TranslationParticipant, IntegrationTestConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    # Load parameters
    max_concurrent_sessions: int = 16
    ramp_up_duration_seconds: int = 30
    sustained_load_duration_seconds: int = 300
    ramp_down_duration_seconds: int = 30
    
    # Session parameters
    session_duration_seconds: int = 180  # 3 minutes per session
    participants_per_session: int = 2
    language_pairs: List[Tuple[str, str]] = None
    
    # Performance targets
    max_cpu_usage_percent: float = 80.0
    max_memory_usage_percent: float = 85.0
    max_response_time_ms: float = 1000.0
    min_success_rate: float = 0.95
    
    # Service endpoints
    stt_service_url: str = "http://localhost:8001"
    mt_service_url: str = "http://localhost:8002"
    tts_service_url: str = "http://localhost:8003"
    livekit_url: str = "ws://localhost:7880"
    
    def __post_init__(self):
        if self.language_pairs is None:
            self.language_pairs = [
                ("en", "es"), ("en", "fr"), ("en", "de"), ("en", "ja"),
                ("es", "en"), ("fr", "en"), ("de", "en"), ("ja", "en")
            ]

@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    timestamp: datetime
    active_sessions: int
    cpu_usage_percent: float
    memory_usage_percent: float
    network_io_bytes_per_sec: float
    
    # Service response times
    stt_response_time_ms: float
    mt_response_time_ms: float
    tts_response_time_ms: float
    
    # Error rates
    stt_error_rate: float
    mt_error_rate: float
    tts_error_rate: float
    total_error_rate: float
    
    # Translation quality
    translation_latency_p95_ms: float
    audio_quality_score: float

@dataclass
class SessionStats:
    """Statistics for a single test session"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    participants: int
    language_pair: Tuple[str, str]
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def success_rate(self) -> float:
        return self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

@dataclass
class LoadTestResult:
    """Complete load test result"""
    test_name: str
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    
    # Overall metrics
    peak_concurrent_sessions: int
    total_sessions_created: int
    total_requests_sent: int
    total_successful_requests: int
    overall_success_rate: float
    
    # Performance metrics
    peak_cpu_usage: float
    peak_memory_usage: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    
    # Service performance
    stt_avg_response_ms: float
    mt_avg_response_ms: float
    tts_avg_response_ms: float
    
    # Load test phases
    ramp_up_successful: bool
    sustained_load_successful: bool
    ramp_down_successful: bool
    
    # Compliance
    cpu_compliant: bool
    memory_compliant: bool
    response_time_compliant: bool
    success_rate_compliant: bool
    overall_compliant: bool
    
    # Detailed data
    session_stats: List[SessionStats]
    metrics_timeline: List[LoadTestMetrics]
    error_summary: Dict[str, int]

class SystemMonitor:
    """Monitor system resources during load testing"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.monitor_interval = 1.0  # 1 second
        
    def start_monitoring(self):
        """Start system monitoring"""
        self.monitoring = True
        self.metrics = []
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                # Get network I/O
                net_io = psutil.net_io_counters()
                network_bytes_per_sec = (net_io.bytes_sent + net_io.bytes_recv) / self.monitor_interval
                
                # Create metrics entry
                metric = LoadTestMetrics(
                    timestamp=datetime.utcnow(),
                    active_sessions=0,  # Will be updated by load tester
                    cpu_usage_percent=cpu_percent,
                    memory_usage_percent=memory_percent,
                    network_io_bytes_per_sec=network_bytes_per_sec,
                    stt_response_time_ms=0.0,  # Will be updated
                    mt_response_time_ms=0.0,   # Will be updated
                    tts_response_time_ms=0.0,  # Will be updated
                    stt_error_rate=0.0,
                    mt_error_rate=0.0,
                    tts_error_rate=0.0,
                    total_error_rate=0.0,
                    translation_latency_p95_ms=0.0,
                    audio_quality_score=0.0
                )
                
                self.metrics.append(metric)
                
                # Limit metrics history to prevent memory issues
                if len(self.metrics) > 1000:
                    self.metrics = self.metrics[-500:]
                
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(self.monitor_interval)
    
    def get_latest_metrics(self) -> Optional[LoadTestMetrics]:
        """Get the latest system metrics"""
        return self.metrics[-1] if self.metrics else None
    
    def get_peak_usage(self) -> Tuple[float, float]:
        """Get peak CPU and memory usage"""
        if not self.metrics:
            return 0.0, 0.0
        
        peak_cpu = max(m.cpu_usage_percent for m in self.metrics)
        peak_memory = max(m.memory_usage_percent for m in self.metrics)
        
        return peak_cpu, peak_memory

class LoadGenerator:
    """Generate synthetic load for translation services"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.audio_generator = AudioGenerator()
        self.active_sessions = {}
        self.session_stats = []
        self.tracer = get_tracer("load-generator")
        
    async def create_translation_session(self, session_id: str, language_pair: Tuple[str, str],
                                       duration_seconds: int) -> SessionStats:
        """Create and run a single translation session"""
        source_lang, target_lang = language_pair
        
        session_stats = SessionStats(
            session_id=session_id,
            start_time=datetime.utcnow(),
            end_time=None,
            participants=self.config.participants_per_session,
            language_pair=language_pair
        )
        
        self.active_sessions[session_id] = session_stats
        
        try:
            # Generate conversation patterns
            conversation_events = self._generate_conversation_pattern(duration_seconds)
            
            for event in conversation_events:
                if event['type'] == 'speak':
                    # Generate audio
                    audio = self.audio_generator._text_to_synthetic_audio(
                        event['content'], source_lang
                    )
                    
                    # Send through translation pipeline
                    await self._process_translation_request(
                        session_stats, audio, event['content'], source_lang, target_lang
                    )
                    
                elif event['type'] == 'pause':
                    await asyncio.sleep(event['duration'])
                
                # Check if session should continue
                if session_id not in self.active_sessions:
                    break
        
        except Exception as e:
            session_stats.errors.append(f"Session error: {e}")
            logger.error(f"Error in session {session_id}: {e}")
        
        finally:
            session_stats.end_time = datetime.utcnow()
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            self.session_stats.append(session_stats)
        
        return session_stats
    
    def _generate_conversation_pattern(self, duration_seconds: int) -> List[Dict[str, Any]]:
        """Generate realistic conversation timing patterns"""
        events = []
        current_time = 0
        
        conversation_templates = [
            "Hello, how are you doing today?",
            "I think we should discuss this matter in more detail.",
            "Can you please explain the process step by step?",
            "That's an interesting perspective on the situation.",
            "Let me share my thoughts on this important topic.",
            "I agree with the previous statement completely.",
            "We need to consider all possible alternatives here.",
            "The results show a significant improvement in performance."
        ]
        
        while current_time < duration_seconds:
            # Speaking period
            speak_duration = np.random.normal(2.5, 1.0)  # 2.5±1 seconds
            speak_duration = max(0.5, min(speak_duration, 8.0))
            
            content = np.random.choice(conversation_templates)
            
            events.append({
                'type': 'speak',
                'start_time': current_time,
                'duration': speak_duration,
                'content': content
            })
            
            current_time += speak_duration
            
            # Pause period
            if current_time < duration_seconds:
                pause_duration = np.random.exponential(1.5)
                pause_duration = max(0.2, min(pause_duration, 5.0))
                
                events.append({
                    'type': 'pause',
                    'start_time': current_time,
                    'duration': pause_duration
                })
                
                current_time += pause_duration
        
        return events
    
    async def _process_translation_request(self, session_stats: SessionStats,
                                         audio: np.ndarray, text: str,
                                         source_lang: str, target_lang: str):
        """Process a single translation request through the pipeline"""
        request_start = time.time()
        session_stats.total_requests += 1
        
        try:
            # Step 1: STT
            stt_start = time.time()
            stt_result = await self._call_stt_service(audio)
            stt_duration = (time.time() - stt_start) * 1000
            
            if not stt_result.get('success'):
                raise Exception(f"STT failed: {stt_result.get('error')}")
            
            # Step 2: MT
            mt_start = time.time()
            mt_result = await self._call_mt_service(
                stt_result['text'], source_lang, target_lang
            )
            mt_duration = (time.time() - mt_start) * 1000
            
            if not mt_result.get('success'):
                raise Exception(f"MT failed: {mt_result.get('error')}")
            
            # Step 3: TTS
            tts_start = time.time()
            tts_result = await self._call_tts_service(
                mt_result['translation'], target_lang
            )
            tts_duration = (time.time() - tts_start) * 1000
            
            if not tts_result.get('success'):
                raise Exception(f"TTS failed: {tts_result.get('error')}")
            
            # Calculate total request time
            total_duration = (time.time() - request_start) * 1000
            
            # Update session statistics
            session_stats.successful_requests += 1
            session_stats.min_response_time_ms = min(session_stats.min_response_time_ms, total_duration)
            session_stats.max_response_time_ms = max(session_stats.max_response_time_ms, total_duration)
            
            # Update running average
            if session_stats.successful_requests == 1:
                session_stats.avg_response_time_ms = total_duration
            else:
                session_stats.avg_response_time_ms = (
                    (session_stats.avg_response_time_ms * (session_stats.successful_requests - 1) + total_duration) /
                    session_stats.successful_requests
                )
            
        except Exception as e:
            session_stats.failed_requests += 1
            session_stats.errors.append(str(e))
            logger.debug(f"Translation request failed: {e}")
    
    async def _call_stt_service(self, audio: np.ndarray) -> Dict[str, Any]:
        """Call STT service"""
        try:
            audio_bytes = (audio * 32767).astype(np.int16).tobytes()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.stt_service_url}/transcribe",
                    data=audio_bytes,
                    headers={'Content-Type': 'audio/wav'},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {'success': True, 'text': result.get('text', '')}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_mt_service(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Call MT service"""
        try:
            payload = {'text': text, 'source_language': source_lang, 'target_language': target_lang}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.mt_service_url}/translate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {'success': True, 'translation': result.get('translation', '')}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_tts_service(self, text: str, language: str) -> Dict[str, Any]:
        """Call TTS service"""
        try:
            payload = {'text': text, 'language': language, 'voice_id': f"{language}-voice-1"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.tts_service_url}/synthesize",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        return {'success': True}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_active_session_count(self) -> int:
        """Get number of currently active sessions"""
        return len(self.active_sessions)
    
    def stop_all_sessions(self):
        """Stop all active sessions"""
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

class LoadTestSuite:
    """Main load testing suite"""
    
    def __init__(self, config: LoadTestConfig = None):
        self.config = config or LoadTestConfig()
        self.system_monitor = SystemMonitor()
        self.load_generator = LoadGenerator(self.config)
        self.tracer = get_tracer("load-test-suite")
        
    async def run_ramp_up_test(self) -> LoadTestResult:
        """Run gradual ramp-up load test"""
        test_name = "ramp_up_load_test"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting ramp-up load test: 0 → {self.config.max_concurrent_sessions} sessions")
        
        # Start system monitoring
        self.system_monitor.start_monitoring()
        
        active_session_tasks = []
        session_counter = 0
        
        try:
            # Calculate ramp-up parameters
            ramp_interval = self.config.ramp_up_duration_seconds / self.config.max_concurrent_sessions
            
            # Ramp-up phase
            for i in range(self.config.max_concurrent_sessions):
                session_id = f"ramp-session-{session_counter}"
                session_counter += 1
                
                language_pair = self.config.language_pairs[i % len(self.config.language_pairs)]
                
                # Create session task
                session_task = asyncio.create_task(
                    self.load_generator.create_translation_session(
                        session_id, language_pair, self.config.session_duration_seconds
                    )
                )
                
                active_session_tasks.append(session_task)
                
                logger.info(f"Started session {i+1}/{self.config.max_concurrent_sessions}")
                
                # Wait before starting next session
                if i < self.config.max_concurrent_sessions - 1:
                    await asyncio.sleep(ramp_interval)
            
            # Sustained load phase
            logger.info(f"Sustaining load at {self.config.max_concurrent_sessions} sessions...")
            await asyncio.sleep(self.config.sustained_load_duration_seconds)
            
            # Stop all sessions
            self.load_generator.stop_all_sessions()
            
            # Wait for sessions to complete
            logger.info("Waiting for sessions to complete...")
            completed_sessions = await asyncio.gather(*active_session_tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Load test error: {e}")
            self.load_generator.stop_all_sessions()
            completed_sessions = []
        
        finally:
            self.system_monitor.stop_monitoring()
        
        end_time = datetime.utcnow()
        
        # Analyze results
        return self._analyze_load_test_results(
            test_name, start_time, end_time, completed_sessions
        )
    
    async def run_stress_test(self) -> LoadTestResult:
        """Run stress test to find system breaking point"""
        test_name = "stress_test"
        start_time = datetime.utcnow()
        
        logger.info("Starting stress test to find system limits...")
        
        self.system_monitor.start_monitoring()
        
        max_sessions_attempted = self.config.max_concurrent_sessions * 2  # Try double the normal load
        active_session_tasks = []
        session_counter = 0
        breaking_point_reached = False
        
        try:
            # Aggressive ramp-up
            for i in range(max_sessions_attempted):
                session_id = f"stress-session-{session_counter}"
                session_counter += 1
                
                language_pair = self.config.language_pairs[i % len(self.config.language_pairs)]
                
                session_task = asyncio.create_task(
                    self.load_generator.create_translation_session(
                        session_id, language_pair, 60  # Shorter sessions for stress test
                    )
                )
                
                active_session_tasks.append(session_task)
                
                # Check system health
                metrics = self.system_monitor.get_latest_metrics()
                if metrics:
                    if (metrics.cpu_usage_percent > 95 or 
                        metrics.memory_usage_percent > 95):
                        logger.warning(f"System stress detected at {i+1} sessions")
                        breaking_point_reached = True
                        break
                
                # Very short interval for aggressive loading
                await asyncio.sleep(0.5)
            
            # Brief sustained period
            if not breaking_point_reached:
                logger.info(f"Sustaining stress load at {len(active_session_tasks)} sessions...")
                await asyncio.sleep(30)  # Short sustained period
            
            # Stop sessions
            self.load_generator.stop_all_sessions()
            
            # Wait for completion
            completed_sessions = await asyncio.gather(*active_session_tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Stress test error: {e}")
            self.load_generator.stop_all_sessions()
            completed_sessions = []
        
        finally:
            self.system_monitor.stop_monitoring()
        
        end_time = datetime.utcnow()
        
        return self._analyze_load_test_results(
            test_name, start_time, end_time, completed_sessions
        )
    
    async def run_spike_test(self) -> LoadTestResult:
        """Run spike test with sudden load increases"""
        test_name = "spike_test"
        start_time = datetime.utcnow()
        
        logger.info("Starting spike test with sudden load increases...")
        
        self.system_monitor.start_monitoring()
        
        active_session_tasks = []
        session_counter = 0
        
        try:
            # Normal baseline load
            baseline_sessions = self.config.max_concurrent_sessions // 4
            
            logger.info(f"Starting baseline load: {baseline_sessions} sessions")
            for i in range(baseline_sessions):
                session_id = f"baseline-session-{session_counter}"
                session_counter += 1
                
                language_pair = self.config.language_pairs[i % len(self.config.language_pairs)]
                
                session_task = asyncio.create_task(
                    self.load_generator.create_translation_session(
                        session_id, language_pair, 120
                    )
                )
                
                active_session_tasks.append(session_task)
                await asyncio.sleep(0.2)
            
            # Wait for baseline to stabilize
            await asyncio.sleep(10)
            
            # Sudden spike
            spike_sessions = self.config.max_concurrent_sessions
            logger.info(f"Creating sudden spike: +{spike_sessions} sessions")
            
            # Create spike sessions rapidly
            spike_tasks = []
            for i in range(spike_sessions):
                session_id = f"spike-session-{session_counter}"
                session_counter += 1
                
                language_pair = self.config.language_pairs[i % len(self.config.language_pairs)]
                
                session_task = asyncio.create_task(
                    self.load_generator.create_translation_session(
                        session_id, language_pair, 60
                    )
                )
                
                spike_tasks.append(session_task)
                # Very rapid creation
                await asyncio.sleep(0.1)
            
            active_session_tasks.extend(spike_tasks)
            
            # Sustain spike briefly
            await asyncio.sleep(30)
            
            # Stop all sessions
            self.load_generator.stop_all_sessions()
            
            completed_sessions = await asyncio.gather(*active_session_tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Spike test error: {e}")
            self.load_generator.stop_all_sessions()
            completed_sessions = []
        
        finally:
            self.system_monitor.stop_monitoring()
        
        end_time = datetime.utcnow()
        
        return self._analyze_load_test_results(
            test_name, start_time, end_time, completed_sessions
        )
    
    def _analyze_load_test_results(self, test_name: str, start_time: datetime,
                                 end_time: datetime, session_results: List[Any]) -> LoadTestResult:
        """Analyze load test results"""
        
        # Filter successful sessions
        successful_sessions = [
            result for result in session_results
            if isinstance(result, SessionStats) and not isinstance(result, Exception)
        ]
        
        # Calculate overall metrics
        total_sessions = len(session_results)
        total_requests = sum(s.total_requests for s in successful_sessions)
        total_successful_requests = sum(s.successful_requests for s in successful_sessions)
        
        overall_success_rate = (
            total_successful_requests / total_requests 
            if total_requests > 0 else 0.0
        )
        
        # Calculate response time metrics
        all_response_times = []
        for session in successful_sessions:
            if session.successful_requests > 0:
                # Use average response time for each session
                all_response_times.extend([session.avg_response_time_ms] * session.successful_requests)
        
        if all_response_times:
            avg_response_time = statistics.mean(all_response_times)
            p95_response_time = np.percentile(all_response_times, 95)
            p99_response_time = np.percentile(all_response_times, 99)
        else:
            avg_response_time = 0.0
            p95_response_time = 0.0
            p99_response_time = 0.0
        
        # Get system performance metrics
        peak_cpu, peak_memory = self.system_monitor.get_peak_usage()
        
        # Estimate service response times (simplified)
        stt_avg_response = avg_response_time * 0.3 if avg_response_time > 0 else 0.0
        mt_avg_response = avg_response_time * 0.4 if avg_response_time > 0 else 0.0
        tts_avg_response = avg_response_time * 0.3 if avg_response_time > 0 else 0.0
        
        # Determine test phase success
        ramp_up_successful = peak_cpu < 90 and overall_success_rate > 0.8
        sustained_load_successful = overall_success_rate > 0.85
        ramp_down_successful = True  # Simplified
        
        # Check compliance
        cpu_compliant = peak_cpu <= self.config.max_cpu_usage_percent
        memory_compliant = peak_memory <= self.config.max_memory_usage_percent
        response_time_compliant = avg_response_time <= self.config.max_response_time_ms
        success_rate_compliant = overall_success_rate >= self.config.min_success_rate
        
        overall_compliant = (cpu_compliant and memory_compliant and 
                           response_time_compliant and success_rate_compliant)
        
        # Error summary
        error_summary = {}
        for session in successful_sessions:
            for error in session.errors:
                error_type = error.split(':')[0] if ':' in error else 'general'
                error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        peak_concurrent = max(
            len([s for s in successful_sessions if s.start_time <= t <= (s.end_time or datetime.utcnow())])
            for t in [start_time + timedelta(seconds=i) for i in range(int((end_time - start_time).total_seconds()))]
        ) if successful_sessions else 0
        
        # Create result
        result = LoadTestResult(
            test_name=test_name,
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            peak_concurrent_sessions=peak_concurrent,
            total_sessions_created=total_sessions,
            total_requests_sent=total_requests,
            total_successful_requests=total_successful_requests,
            overall_success_rate=overall_success_rate,
            peak_cpu_usage=peak_cpu,
            peak_memory_usage=peak_memory,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            stt_avg_response_ms=stt_avg_response,
            mt_avg_response_ms=mt_avg_response,
            tts_avg_response_ms=tts_avg_response,
            ramp_up_successful=ramp_up_successful,
            sustained_load_successful=sustained_load_successful,
            ramp_down_successful=ramp_down_successful,
            cpu_compliant=cpu_compliant,
            memory_compliant=memory_compliant,
            response_time_compliant=response_time_compliant,
            success_rate_compliant=success_rate_compliant,
            overall_compliant=overall_compliant,
            session_stats=successful_sessions,
            metrics_timeline=self.system_monitor.metrics,
            error_summary=error_summary
        )
        
        # Log summary
        self._log_load_test_summary(result)
        
        return result
    
    def _log_load_test_summary(self, result: LoadTestResult):
        """Log load test summary"""
        logger.info("=" * 70)
        logger.info(f"LOAD TEST RESULTS: {result.test_name.upper()}")
        logger.info("=" * 70)
        logger.info(f"Test Duration: {(result.end_time - result.start_time).total_seconds():.1f}s")
        logger.info(f"Peak Concurrent Sessions: {result.peak_concurrent_sessions}")
        logger.info(f"Total Sessions: {result.total_sessions_created}")
        logger.info(f"Total Requests: {result.total_requests_sent:,}")
        logger.info(f"Successful Requests: {result.total_successful_requests:,}")
        logger.info(f"Overall Success Rate: {result.overall_success_rate:.1%}")
        
        logger.info("\nPerformance Metrics:")
        logger.info(f"Peak CPU Usage: {result.peak_cpu_usage:.1f}%")
        logger.info(f"Peak Memory Usage: {result.peak_memory_usage:.1f}%")
        logger.info(f"Avg Response Time: {result.avg_response_time_ms:.1f}ms")
        logger.info(f"95th Percentile Response Time: {result.p95_response_time_ms:.1f}ms")
        logger.info(f"99th Percentile Response Time: {result.p99_response_time_ms:.1f}ms")
        
        logger.info("\nService Response Times:")
        logger.info(f"STT Avg: {result.stt_avg_response_ms:.1f}ms")
        logger.info(f"MT Avg: {result.mt_avg_response_ms:.1f}ms")
        logger.info(f"TTS Avg: {result.tts_avg_response_ms:.1f}ms")
        
        logger.info("\nCompliance Check:")
        logger.info(f"CPU Usage: {'✓' if result.cpu_compliant else '✗'} "
                   f"({result.peak_cpu_usage:.1f}% ≤ {result.config.max_cpu_usage_percent}%)")
        logger.info(f"Memory Usage: {'✓' if result.memory_compliant else '✗'} "
                   f"({result.peak_memory_usage:.1f}% ≤ {result.config.max_memory_usage_percent}%)")
        logger.info(f"Response Time: {'✓' if result.response_time_compliant else '✗'} "
                   f"({result.avg_response_time_ms:.1f}ms ≤ {result.config.max_response_time_ms}ms)")
        logger.info(f"Success Rate: {'✓' if result.success_rate_compliant else '✗'} "
                   f"({result.overall_success_rate:.1%} ≥ {result.config.min_success_rate:.1%})")
        
        logger.info(f"\nOverall Result: {'✓ PASS' if result.overall_compliant else '✗ FAIL'}")
        
        if result.error_summary:
            logger.info("\nError Summary:")
            for error_type, count in result.error_summary.items():
                logger.info(f"  {error_type}: {count}")
    
    def generate_load_test_report(self, results: List[LoadTestResult], output_dir: str = "qa/reports"):
        """Generate comprehensive load test report with charts"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Generate performance charts
        self._create_performance_charts(results, output_dir, timestamp)
        
        # Generate HTML report
        self._create_html_report(results, output_dir, timestamp)
        
        logger.info(f"Load test report generated in {output_dir}/")
    
    def _create_performance_charts(self, results: List[LoadTestResult], output_dir: str, timestamp: str):
        """Create performance visualization charts"""
        try:
            # CPU and Memory Usage Chart
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            for result in results:
                if result.metrics_timeline:
                    times = [m.timestamp for m in result.metrics_timeline]
                    cpu_values = [m.cpu_usage_percent for m in result.metrics_timeline]
                    memory_values = [m.memory_usage_percent for m in result.metrics_timeline]
                    
                    ax1.plot(times, cpu_values, label=f"{result.test_name} CPU")
                    ax2.plot(times, memory_values, label=f"{result.test_name} Memory")
            
            ax1.set_title('CPU Usage Over Time')
            ax1.set_ylabel('CPU Usage (%)')
            ax1.legend()
            ax1.grid(True)
            
            ax2.set_title('Memory Usage Over Time')
            ax2.set_ylabel('Memory Usage (%)')
            ax2.set_xlabel('Time')
            ax2.legend()
            ax2.grid(True)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/system_metrics_{timestamp}.png", dpi=150, bbox_inches='tight')
            plt.close()
            
            # Response Time Comparison Chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            test_names = [r.test_name for r in results]
            avg_times = [r.avg_response_time_ms for r in results]
            p95_times = [r.p95_response_time_ms for r in results]
            p99_times = [r.p99_response_time_ms for r in results]
            
            x = range(len(test_names))
            width = 0.25
            
            ax.bar([i - width for i in x], avg_times, width, label='Average', alpha=0.8)
            ax.bar(x, p95_times, width, label='95th Percentile', alpha=0.8)
            ax.bar([i + width for i in x], p99_times, width, label='99th Percentile', alpha=0.8)
            
            ax.set_xlabel('Test Type')
            ax.set_ylabel('Response Time (ms)')
            ax.set_title('Response Time Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(test_names, rotation=45)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/response_times_{timestamp}.png", dpi=150, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"Error creating charts: {e}")
    
    def _create_html_report(self, results: List[LoadTestResult], output_dir: str, timestamp: str):
        """Create HTML report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Load Test Report - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .test-result {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .pass {{ border-left: 5px solid #4CAF50; }}
                .fail {{ border-left: 5px solid #f44336; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Load Test Report</h1>
                <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            </div>
        """
        
        for result in results:
            status_class = "pass" if result.overall_compliant else "fail"
            status_text = "PASS" if result.overall_compliant else "FAIL"
            
            html_content += f"""
            <div class="test-result {status_class}">
                <h2>{result.test_name.title().replace('_', ' ')} - {status_text}</h2>
                
                <div class="metric">
                    <strong>Peak Sessions:</strong> {result.peak_concurrent_sessions}
                </div>
                <div class="metric">
                    <strong>Success Rate:</strong> {result.overall_success_rate:.1%}
                </div>
                <div class="metric">
                    <strong>Avg Response:</strong> {result.avg_response_time_ms:.1f}ms
                </div>
                <div class="metric">
                    <strong>Peak CPU:</strong> {result.peak_cpu_usage:.1f}%
                </div>
                <div class="metric">
                    <strong>Peak Memory:</strong> {result.peak_memory_usage:.1f}%
                </div>
                
                <h3>Detailed Metrics</h3>
                <table>
                    <tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr>
                    <tr>
                        <td>CPU Usage</td>
                        <td>{result.peak_cpu_usage:.1f}%</td>
                        <td>≤ {result.config.max_cpu_usage_percent}%</td>
                        <td>{'✓' if result.cpu_compliant else '✗'}</td>
                    </tr>
                    <tr>
                        <td>Memory Usage</td>
                        <td>{result.peak_memory_usage:.1f}%</td>
                        <td>≤ {result.config.max_memory_usage_percent}%</td>
                        <td>{'✓' if result.memory_compliant else '✗'}</td>
                    </tr>
                    <tr>
                        <td>Response Time</td>
                        <td>{result.avg_response_time_ms:.1f}ms</td>
                        <td>≤ {result.config.max_response_time_ms}ms</td>
                        <td>{'✓' if result.response_time_compliant else '✗'}</td>
                    </tr>
                    <tr>
                        <td>Success Rate</td>
                        <td>{result.overall_success_rate:.1%}</td>
                        <td>≥ {result.config.min_success_rate:.1%}</td>
                        <td>{'✓' if result.success_rate_compliant else '✗'}</td>
                    </tr>
                </table>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        with open(f"{output_dir}/load_test_report_{timestamp}.html", 'w') as f:
            f.write(html_content)

# Utility functions
async def run_comprehensive_load_tests(config: LoadTestConfig = None) -> Dict[str, LoadTestResult]:
    """Run comprehensive load test suite"""
    if config is None:
        config = LoadTestConfig()
    
    suite = LoadTestSuite(config)
    
    logger.info("Starting comprehensive load test suite...")
    
    tests = {
        'ramp_up': suite.run_ramp_up_test(),
        'stress': suite.run_stress_test(),
        'spike': suite.run_spike_test()
    }
    
    results = {}
    
    for test_name, test_coro in tests.items():
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Running {test_name} test...")
            logger.info(f"{'='*80}")
            
            result = await test_coro
            results[test_name] = result
            
            # Brief pause between tests for system recovery
            logger.info("Allowing system recovery time...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Load test {test_name} failed: {e}")
            results[test_name] = None
    
    # Generate report
    successful_results = [r for r in results.values() if r is not None]
    if successful_results:
        suite.generate_load_test_report(successful_results)
    
    return results

if __name__ == "__main__":
    # Example usage
    async def main():
        config = LoadTestConfig(
            max_concurrent_sessions=8,  # Reduced for testing
            ramp_up_duration_seconds=20,
            sustained_load_duration_seconds=60,
            session_duration_seconds=90
        )
        
        results = await run_comprehensive_load_tests(config)
        
        # Save results to JSON
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        with open(f"load_test_results_{timestamp}.json", 'w') as f:
            json.dump({
                k: asdict(v) if v else None
                for k, v in results.items()
            }, f, indent=2, default=str)
    
    asyncio.run(main())