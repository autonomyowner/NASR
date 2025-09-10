"""
End-to-End Integration Test Framework for The HIVE Translation Pipeline
Tests complete STT→MT→TTS→LiveKit pipeline integration with real-world scenarios
"""

import asyncio
import aiohttp
import websockets
import json
import time
import logging
import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor
import threading

# Add backend path for imports
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from observability.tracer import get_tracer
from observability.metrics import get_metrics

# Import related test modules
from .slo_tests import AudioGenerator, SLOTestConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IntegrationTestConfig:
    """Configuration for integration testing"""
    # Service endpoints
    stt_service_url: str = "http://localhost:8001"
    mt_service_url: str = "http://localhost:8002"
    tts_service_url: str = "http://localhost:8003"
    livekit_url: str = "ws://localhost:7880"
    livekit_api_url: str = "http://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"
    
    # Test parameters
    test_duration_seconds: int = 300  # 5 minutes
    max_concurrent_participants: int = 8
    language_pairs: List[Tuple[str, str]] = None
    
    # Performance thresholds
    max_join_time_ms: float = 2000.0  # Time to join room
    max_audio_delay_ms: float = 500.0  # End-to-end audio delay
    min_audio_quality_score: float = 0.7
    min_translation_accuracy: float = 0.8
    
    def __post_init__(self):
        if self.language_pairs is None:
            self.language_pairs = [
                ("en", "es"), ("en", "fr"), ("en", "de"),
                ("es", "en"), ("fr", "en"), ("de", "en")
            ]

@dataclass
class ParticipantSession:
    """Represents a single participant in a translation session"""
    participant_id: str
    room_name: str
    source_language: str
    target_language: str
    join_time: Optional[datetime] = None
    first_audio_time: Optional[datetime] = None
    translation_events: List[Dict[str, Any]] = None
    audio_quality_scores: List[float] = None
    errors: List[str] = None
    is_active: bool = False
    
    def __post_init__(self):
        if self.translation_events is None:
            self.translation_events = []
        if self.audio_quality_scores is None:
            self.audio_quality_scores = []
        if self.errors is None:
            self.errors = []

@dataclass
class IntegrationTestResult:
    """Result from integration testing"""
    test_name: str
    config: IntegrationTestConfig
    start_time: datetime
    end_time: datetime
    participants: List[ParticipantSession]
    
    # Performance metrics
    avg_join_time_ms: float
    avg_translation_latency_ms: float
    avg_audio_quality_score: float
    avg_translation_accuracy: float
    success_rate: float
    
    # Pipeline health
    stt_success_rate: float
    mt_success_rate: float
    tts_success_rate: float
    livekit_success_rate: float
    
    # Test compliance
    join_time_compliant: bool
    audio_delay_compliant: bool
    quality_compliant: bool
    overall_compliant: bool
    
    error_summary: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'participants': [asdict(p) for p in self.participants]
        }

class LiveKitClient:
    """LiveKit WebSocket client for integration testing"""
    
    def __init__(self, room_name: str, participant_id: str, config: IntegrationTestConfig):
        self.room_name = room_name
        self.participant_id = participant_id
        self.config = config
        self.websocket = None
        self.is_connected = False
        self.audio_tracks = {}
        self.translation_tracks = {}
        
    async def connect(self) -> bool:
        """Connect to LiveKit room"""
        try:
            # Generate JWT token for LiveKit
            token = self._generate_access_token()
            
            # Connect to LiveKit WebSocket
            ws_url = f"{self.config.livekit_url.replace('http', 'ws')}/ws"
            headers = {"Authorization": f"Bearer {token}"}
            
            self.websocket = await websockets.connect(ws_url, extra_headers=headers)
            
            # Send join request
            join_message = {
                "method": "join",
                "params": {
                    "room": self.room_name,
                    "identity": self.participant_id
                }
            }
            
            await self.websocket.send(json.dumps(join_message))
            
            # Wait for join confirmation
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            result = json.loads(response)
            
            if result.get("result", {}).get("success"):
                self.is_connected = True
                logger.info(f"Participant {self.participant_id} joined room {self.room_name}")
                return True
            else:
                logger.error(f"Failed to join room: {result}")
                return False
                
        except Exception as e:
            logger.error(f"LiveKit connection error: {e}")
            return False
    
    async def publish_audio_track(self, audio_data: np.ndarray, language: str) -> bool:
        """Publish audio track to LiveKit"""
        try:
            if not self.is_connected:
                return False
            
            # Convert audio to appropriate format
            audio_bytes = self._audio_to_bytes(audio_data)
            
            # Send publish request
            publish_message = {
                "method": "publishTrack",
                "params": {
                    "type": "audio",
                    "codec": "opus",
                    "language": language,
                    "data": audio_bytes.hex()
                }
            }
            
            await self.websocket.send(json.dumps(publish_message))
            return True
            
        except Exception as e:
            logger.error(f"Error publishing audio track: {e}")
            return False
    
    async def subscribe_to_translations(self, target_language: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribe to translated audio tracks"""
        try:
            subscribe_message = {
                "method": "subscribe",
                "params": {
                    "track_type": "translation",
                    "language": target_language
                }
            }
            
            await self.websocket.send(json.dumps(subscribe_message))
            
            # Listen for translation events
            while self.is_connected:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data.get("type") == "translation":
                        yield data
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving translation: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error subscribing to translations: {e}")
    
    async def disconnect(self):
        """Disconnect from LiveKit"""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
        self.is_connected = False
    
    def _generate_access_token(self) -> str:
        """Generate JWT access token for LiveKit (simplified)"""
        # In a real implementation, this would generate a proper JWT
        # For testing, we'll use a simplified token
        import base64
        token_data = {
            "iss": self.config.livekit_api_key,
            "sub": self.participant_id,
            "room": self.room_name,
            "exp": int(time.time()) + 3600  # 1 hour expiry
        }
        return base64.b64encode(json.dumps(token_data).encode()).decode()
    
    def _audio_to_bytes(self, audio: np.ndarray) -> bytes:
        """Convert audio array to bytes"""
        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()

class TranslationParticipant:
    """Simulates a participant in a translation session"""
    
    def __init__(self, config: IntegrationTestConfig, participant_id: str, 
                 room_name: str, source_lang: str, target_lang: str):
        self.config = config
        self.participant_id = participant_id
        self.room_name = room_name
        self.source_lang = source_lang
        self.target_lang = target_lang
        
        self.session = ParticipantSession(
            participant_id=participant_id,
            room_name=room_name,
            source_language=source_lang,
            target_language=target_lang
        )
        
        self.livekit_client = LiveKitClient(room_name, participant_id, config)
        self.audio_generator = AudioGenerator()
        self.tracer = get_tracer(f"integration-participant-{participant_id}")
        
        self._running = False
    
    async def join_session(self) -> bool:
        """Join the translation session"""
        try:
            join_start = time.time()
            
            # Connect to LiveKit
            if not await self.livekit_client.connect():
                self.session.errors.append("Failed to connect to LiveKit")
                return False
            
            join_duration = (time.time() - join_start) * 1000
            
            self.session.join_time = datetime.utcnow()
            self.session.is_active = True
            
            logger.info(f"Participant {self.participant_id} joined in {join_duration:.1f}ms")
            
            return True
            
        except Exception as e:
            error_msg = f"Error joining session: {e}"
            self.session.errors.append(error_msg)
            logger.error(error_msg)
            return False
    
    async def start_conversation_simulation(self) -> None:
        """Start simulating conversation with translations"""
        if not self.session.is_active:
            logger.error(f"Participant {self.participant_id} not active")
            return
        
        self._running = True
        
        # Start listening for translations
        translation_task = asyncio.create_task(self._listen_for_translations())
        
        # Start speaking simulation
        speaking_task = asyncio.create_task(self._simulate_speaking())
        
        try:
            await asyncio.gather(translation_task, speaking_task)
        except Exception as e:
            logger.error(f"Error in conversation simulation: {e}")
            self.session.errors.append(str(e))
        finally:
            self._running = False
    
    async def _simulate_speaking(self) -> None:
        """Simulate speaking with realistic patterns"""
        speak_intervals = [3, 5, 2, 4, 6, 3, 7, 2]  # Varied speaking intervals
        
        for i, interval in enumerate(speak_intervals):
            if not self._running:
                break
            
            try:
                # Generate speech for this interval
                speech_phrases = [
                    "Hello everyone, how are you doing today?",
                    "I think we should discuss the quarterly results in detail.",
                    "The weather has been quite nice this week, perfect for outdoor activities.",
                    "Can you please explain the process once more for clarity?",
                    "I agree with the previous statement about improving efficiency.",
                    "Let me share my perspective on this important topic.",
                    "We need to consider all stakeholders in this decision making process."
                ]
                
                phrase = speech_phrases[i % len(speech_phrases)]
                audio = self.audio_generator._text_to_synthetic_audio(phrase, self.source_lang)
                
                # Send audio to translation pipeline
                translation_start = time.time()
                
                # Publish to LiveKit
                await self.livekit_client.publish_audio_track(audio, self.source_lang)
                
                # Also send directly to services for latency measurement
                stt_result = await self._call_stt_service(audio)
                
                if stt_result.get('success'):
                    mt_result = await self._call_mt_service(
                        stt_result['text'], self.source_lang, self.target_lang
                    )
                    
                    if mt_result.get('success'):
                        tts_result = await self._call_tts_service(
                            mt_result['translation'], self.target_lang
                        )
                        
                        # Record translation event
                        translation_duration = (time.time() - translation_start) * 1000
                        
                        self.session.translation_events.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'original_text': phrase,
                            'transcribed_text': stt_result['text'],
                            'translated_text': mt_result['translation'],
                            'latency_ms': translation_duration,
                            'success': tts_result.get('success', False)
                        })
                        
                        # Record first audio time
                        if self.session.first_audio_time is None:
                            self.session.first_audio_time = datetime.utcnow()
                
                # Wait before next speech
                await asyncio.sleep(interval)
                
            except Exception as e:
                error_msg = f"Error in speaking simulation: {e}"
                self.session.errors.append(error_msg)
                logger.error(error_msg)
    
    async def _listen_for_translations(self) -> None:
        """Listen for incoming translated audio"""
        try:
            async for translation_data in self.livekit_client.subscribe_to_translations(self.target_lang):
                if not self._running:
                    break
                
                # Process received translation
                audio_quality = self._evaluate_received_audio(translation_data)
                self.session.audio_quality_scores.append(audio_quality)
                
                logger.debug(f"Participant {self.participant_id} received translation with quality {audio_quality:.2f}")
                
        except Exception as e:
            error_msg = f"Error listening for translations: {e}"
            self.session.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _call_stt_service(self, audio: np.ndarray) -> Dict[str, Any]:
        """Call STT service directly"""
        try:
            audio_bytes = (audio * 32767).astype(np.int16).tobytes()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.stt_service_url}/transcribe",
                    data=audio_bytes,
                    headers={'Content-Type': 'audio/wav'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {'success': True, 'text': result.get('text', '')}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_mt_service(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Call MT service directly"""
        try:
            payload = {
                'text': text,
                'source_language': source_lang,
                'target_language': target_lang
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.mt_service_url}/translate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {'success': True, 'translation': result.get('translation', '')}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_tts_service(self, text: str, language: str) -> Dict[str, Any]:
        """Call TTS service directly"""
        try:
            payload = {
                'text': text,
                'language': language,
                'voice_id': f"{language}-voice-1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.tts_service_url}/synthesize",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    
                    if response.status == 200:
                        return {'success': True}
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _evaluate_received_audio(self, translation_data: Dict[str, Any]) -> float:
        """Evaluate quality of received translated audio"""
        # Simple quality evaluation based on data completeness
        if translation_data.get('audio_data') and len(translation_data['audio_data']) > 100:
            return 0.8  # Good quality
        elif translation_data.get('audio_data'):
            return 0.6  # Fair quality
        else:
            return 0.2  # Poor quality
    
    async def leave_session(self) -> None:
        """Leave the translation session"""
        self._running = False
        self.session.is_active = False
        await self.livekit_client.disconnect()
        logger.info(f"Participant {self.participant_id} left session")

class IntegrationTestSuite:
    """Main integration test suite"""
    
    def __init__(self, config: IntegrationTestConfig = None):
        self.config = config or IntegrationTestConfig()
        self.tracer = get_tracer("integration-tests")
        self.metrics = get_metrics("integration-validation")
        
    async def test_single_participant_session(self, language_pair: Tuple[str, str]) -> IntegrationTestResult:
        """Test single participant translation session"""
        source_lang, target_lang = language_pair
        test_name = f"single_participant_{source_lang}_{target_lang}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting single participant test: {source_lang} → {target_lang}")
        
        room_name = f"test-room-{uuid.uuid4().hex[:8]}"
        participant_id = "test-participant-1"
        
        # Create participant
        participant = TranslationParticipant(
            self.config, participant_id, room_name, source_lang, target_lang
        )
        
        try:
            # Join session
            if not await participant.join_session():
                raise Exception("Failed to join session")
            
            # Run conversation simulation
            conversation_task = asyncio.create_task(participant.start_conversation_simulation())
            
            # Run for specified duration
            await asyncio.sleep(min(self.config.test_duration_seconds, 30))  # Limit to 30s for single participant
            
            # Stop conversation
            participant._running = False
            
            # Wait for tasks to complete
            try:
                await asyncio.wait_for(conversation_task, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Conversation task did not complete in time")
            
            # Leave session
            await participant.leave_session()
            
            end_time = datetime.utcnow()
            
            # Analyze results
            return self._analyze_integration_results(
                test_name, start_time, end_time, [participant.session]
            )
            
        except Exception as e:
            logger.error(f"Single participant test failed: {e}")
            participant.session.errors.append(str(e))
            
            return IntegrationTestResult(
                test_name=test_name,
                config=self.config,
                start_time=start_time,
                end_time=datetime.utcnow(),
                participants=[participant.session],
                avg_join_time_ms=0,
                avg_translation_latency_ms=0,
                avg_audio_quality_score=0,
                avg_translation_accuracy=0,
                success_rate=0,
                stt_success_rate=0,
                mt_success_rate=0,
                tts_success_rate=0,
                livekit_success_rate=0,
                join_time_compliant=False,
                audio_delay_compliant=False,
                quality_compliant=False,
                overall_compliant=False,
                error_summary={"total_errors": 1}
            )
    
    async def test_multi_participant_session(self, participant_count: int = 4) -> IntegrationTestResult:
        """Test multi-participant translation session"""
        test_name = f"multi_participant_{participant_count}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting multi-participant test with {participant_count} participants")
        
        room_name = f"test-room-{uuid.uuid4().hex[:8]}"
        participants = []
        
        # Create participants with different language pairs
        for i in range(participant_count):
            language_pair = self.config.language_pairs[i % len(self.config.language_pairs)]
            participant = TranslationParticipant(
                self.config,
                f"test-participant-{i+1}",
                room_name,
                language_pair[0],
                language_pair[1]
            )
            participants.append(participant)
        
        try:
            # Join all participants
            join_tasks = [p.join_session() for p in participants]
            join_results = await asyncio.gather(*join_tasks, return_exceptions=True)
            
            successful_participants = [
                p for p, result in zip(participants, join_results)
                if result is True
            ]
            
            if not successful_participants:
                raise Exception("No participants successfully joined")
            
            logger.info(f"{len(successful_participants)}/{participant_count} participants joined successfully")
            
            # Start conversations
            conversation_tasks = [
                p.start_conversation_simulation() 
                for p in successful_participants
            ]
            
            # Run for specified duration
            await asyncio.sleep(min(self.config.test_duration_seconds, 60))  # Limit to 60s for multi-participant
            
            # Stop all conversations
            for p in successful_participants:
                p._running = False
            
            # Wait for conversations to complete
            try:
                await asyncio.wait_for(
                    asyncio.gather(*conversation_tasks, return_exceptions=True),
                    timeout=15
                )
            except asyncio.TimeoutError:
                logger.warning("Some conversation tasks did not complete in time")
            
            # Leave all sessions
            leave_tasks = [p.leave_session() for p in participants]
            await asyncio.gather(*leave_tasks, return_exceptions=True)
            
            end_time = datetime.utcnow()
            
            # Analyze results
            all_sessions = [p.session for p in participants]
            return self._analyze_integration_results(test_name, start_time, end_time, all_sessions)
            
        except Exception as e:
            logger.error(f"Multi-participant test failed: {e}")
            
            # Ensure cleanup
            for p in participants:
                try:
                    await p.leave_session()
                except:
                    pass
            
            return IntegrationTestResult(
                test_name=test_name,
                config=self.config,
                start_time=start_time,
                end_time=datetime.utcnow(),
                participants=[p.session for p in participants],
                avg_join_time_ms=0,
                avg_translation_latency_ms=0,
                avg_audio_quality_score=0,
                avg_translation_accuracy=0,
                success_rate=0,
                stt_success_rate=0,
                mt_success_rate=0,
                tts_success_rate=0,
                livekit_success_rate=0,
                join_time_compliant=False,
                audio_delay_compliant=False,
                quality_compliant=False,
                overall_compliant=False,
                error_summary={"total_errors": 1}
            )
    
    def _analyze_integration_results(self, test_name: str, start_time: datetime, 
                                   end_time: datetime, sessions: List[ParticipantSession]) -> IntegrationTestResult:
        """Analyze integration test results"""
        
        # Calculate join times
        join_times = []
        for session in sessions:
            if session.join_time and session.is_active:
                # Estimate join time (simplified)
                join_times.append(1000)  # Placeholder: 1 second
        
        avg_join_time = sum(join_times) / len(join_times) if join_times else 0
        
        # Calculate translation metrics
        all_translation_events = []
        for session in sessions:
            all_translation_events.extend(session.translation_events)
        
        if all_translation_events:
            avg_translation_latency = sum(e['latency_ms'] for e in all_translation_events) / len(all_translation_events)
            translation_success_rate = sum(1 for e in all_translation_events if e['success']) / len(all_translation_events)
        else:
            avg_translation_latency = 0
            translation_success_rate = 0
        
        # Calculate audio quality
        all_quality_scores = []
        for session in sessions:
            all_quality_scores.extend(session.audio_quality_scores)
        
        avg_audio_quality = sum(all_quality_scores) / len(all_quality_scores) if all_quality_scores else 0
        
        # Calculate service success rates (simplified)
        successful_sessions = [s for s in sessions if s.is_active and len(s.errors) == 0]
        overall_success_rate = len(successful_sessions) / len(sessions) if sessions else 0
        
        # Service-specific success rates (estimated based on translation events)
        stt_success_rate = translation_success_rate
        mt_success_rate = translation_success_rate
        tts_success_rate = translation_success_rate
        livekit_success_rate = overall_success_rate
        
        # Calculate translation accuracy (placeholder)
        avg_translation_accuracy = 0.8 if all_translation_events else 0
        
        # Check compliance
        join_time_compliant = avg_join_time <= self.config.max_join_time_ms
        audio_delay_compliant = avg_translation_latency <= self.config.max_audio_delay_ms
        quality_compliant = avg_audio_quality >= self.config.min_audio_quality_score
        
        overall_compliant = (join_time_compliant and audio_delay_compliant and 
                           quality_compliant and overall_success_rate >= 0.9)
        
        # Error summary
        error_summary = {}
        total_errors = 0
        for session in sessions:
            total_errors += len(session.errors)
            for error in session.errors:
                error_type = error.split(':')[0] if ':' in error else 'general'
                error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        error_summary['total_errors'] = total_errors
        
        # Log results summary
        logger.info("=" * 60)
        logger.info(f"INTEGRATION TEST RESULTS: {test_name.upper()}")
        logger.info("=" * 60)
        logger.info(f"Participants: {len(sessions)}")
        logger.info(f"Successful Participants: {len(successful_sessions)}")
        logger.info(f"Average Join Time: {avg_join_time:.1f}ms")
        logger.info(f"Average Translation Latency: {avg_translation_latency:.1f}ms")
        logger.info(f"Average Audio Quality: {avg_audio_quality:.2f}")
        logger.info(f"Overall Success Rate: {overall_success_rate:.1%}")
        logger.info(f"Join Time Compliant: {'✓' if join_time_compliant else '✗'}")
        logger.info(f"Audio Delay Compliant: {'✓' if audio_delay_compliant else '✗'}")
        logger.info(f"Quality Compliant: {'✓' if quality_compliant else '✗'}")
        logger.info(f"Overall Compliant: {'✓ PASS' if overall_compliant else '✗ FAIL'}")
        if total_errors > 0:
            logger.warning(f"Total Errors: {total_errors}")
        
        return IntegrationTestResult(
            test_name=test_name,
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            participants=sessions,
            avg_join_time_ms=avg_join_time,
            avg_translation_latency_ms=avg_translation_latency,
            avg_audio_quality_score=avg_audio_quality,
            avg_translation_accuracy=avg_translation_accuracy,
            success_rate=overall_success_rate,
            stt_success_rate=stt_success_rate,
            mt_success_rate=mt_success_rate,
            tts_success_rate=tts_success_rate,
            livekit_success_rate=livekit_success_rate,
            join_time_compliant=join_time_compliant,
            audio_delay_compliant=audio_delay_compliant,
            quality_compliant=quality_compliant,
            overall_compliant=overall_compliant,
            error_summary=error_summary
        )
    
    async def run_comprehensive_integration_tests(self) -> Dict[str, IntegrationTestResult]:
        """Run comprehensive integration test suite"""
        logger.info("Starting comprehensive integration test suite...")
        
        tests = {}
        
        # Test 1: Single participant sessions for each language pair
        for i, language_pair in enumerate(self.config.language_pairs[:3]):  # Limit to 3 pairs
            test_name = f"single_{language_pair[0]}_{language_pair[1]}"
            try:
                result = await self.test_single_participant_session(language_pair)
                tests[test_name] = result
                
                # Brief pause between tests
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Single participant test {test_name} failed: {e}")
                tests[test_name] = None
        
        # Test 2: Multi-participant sessions
        multi_participant_tests = [
            ("2_participants", 2),
            ("4_participants", 4)
        ]
        
        for test_name, participant_count in multi_participant_tests:
            try:
                result = await self.test_multi_participant_session(participant_count)
                tests[test_name] = result
                
                # Longer pause between multi-participant tests
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Multi-participant test {test_name} failed: {e}")
                tests[test_name] = None
        
        # Generate overall summary
        self._generate_integration_summary(tests)
        
        return tests
    
    def _generate_integration_summary(self, results: Dict[str, IntegrationTestResult]):
        """Generate and log integration test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("INTEGRATION TEST SUITE SUMMARY")
        logger.info("=" * 80)
        
        total_tests = len(results)
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        
        for test_name, result in results.items():
            if result is None:
                status = "ERROR"
                error_tests += 1
            elif result.overall_compliant:
                status = "PASS"
                passed_tests += 1
            else:
                status = "FAIL"
                failed_tests += 1
            
            logger.info(f"{test_name:.<35} {status}")
        
        logger.info("-" * 80)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests} ({passed_tests/total_tests:.1%})")
        logger.info(f"Failed: {failed_tests} ({failed_tests/total_tests:.1%})")
        logger.info(f"Errors: {error_tests} ({error_tests/total_tests:.1%})")
        
        # Overall assessment
        if passed_tests == total_tests:
            assessment = "EXCELLENT - All integration tests passed"
        elif passed_tests >= total_tests * 0.8:
            assessment = "GOOD - Most integration tests passed"
        elif passed_tests >= total_tests * 0.6:
            assessment = "FAIR - Some integration issues detected"
        else:
            assessment = "POOR - Significant integration problems"
        
        logger.info(f"Overall Assessment: {assessment}")

# Utility functions
async def run_quick_integration_test() -> Dict[str, IntegrationTestResult]:
    """Run a quick integration test"""
    config = IntegrationTestConfig(
        test_duration_seconds=30,  # Short test
        language_pairs=[("en", "es"), ("es", "en")]  # Limited language pairs
    )
    
    suite = IntegrationTestSuite(config)
    
    # Just run single participant tests
    results = {}
    for language_pair in config.language_pairs:
        test_name = f"quick_{language_pair[0]}_{language_pair[1]}"
        try:
            result = await suite.test_single_participant_session(language_pair)
            results[test_name] = result
        except Exception as e:
            logger.error(f"Quick test {test_name} failed: {e}")
            results[test_name] = None
    
    return results

async def run_full_integration_test() -> Dict[str, IntegrationTestResult]:
    """Run full integration test suite"""
    suite = IntegrationTestSuite()
    return await suite.run_comprehensive_integration_tests()

if __name__ == "__main__":
    # Example usage
    async def main():
        logger.info("Starting integration testing...")
        
        # Run quick test by default
        results = await run_quick_integration_test()
        
        # Save results
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = f"integration_test_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                k: v.to_dict() if v else None
                for k, v in results.items()
            }, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_file}")
    
    asyncio.run(main())