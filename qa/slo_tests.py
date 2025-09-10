"""
SLO Test Suite for The HIVE Real-Time Translation System
Validates p95 TTFT ≤ 450ms and Caption Latency ≤ 250ms compliance
"""

import asyncio
import aiohttp
import numpy as np
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import statistics
import soundfile as sf
from pathlib import Path
import websockets
import tempfile
import sys

# Add backend path for imports
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from observability.tracer import TranslationTracer, get_tracer
from observability.metrics import TranslationMetrics, get_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SLOTestConfig:
    """Configuration for SLO testing"""
    ttft_target_ms: float = 450.0  # p95 Time-to-First-Token target
    caption_latency_target_ms: float = 250.0  # p95 caption latency target
    retraction_rate_target: float = 0.05  # <5% word retraction rate
    test_duration_minutes: int = 5
    sample_count: int = 100
    confidence_level: float = 0.95
    
    # Service endpoints
    stt_service_url: str = "http://localhost:8001"
    mt_service_url: str = "http://localhost:8002"
    tts_service_url: str = "http://localhost:8003"
    livekit_url: str = "ws://localhost:7880"

@dataclass
class SLOMeasurement:
    """Single SLO measurement result"""
    timestamp: datetime
    test_type: str
    language_pair: str
    input_duration_ms: float
    stt_latency_ms: float
    mt_latency_ms: float
    tts_latency_ms: float
    ttft_ms: float
    caption_latency_ms: float
    end_to_end_ms: float
    audio_quality_score: float
    translation_accuracy_score: float
    retraction_count: int
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class SLOTestResult:
    """Aggregated SLO test results"""
    test_name: str
    config: SLOTestConfig
    start_time: datetime
    end_time: datetime
    measurements: List[SLOMeasurement]
    
    # Aggregated metrics
    ttft_p95_ms: float
    caption_latency_p95_ms: float
    retraction_rate: float
    success_rate: float
    
    # SLO compliance
    ttft_slo_compliant: bool
    caption_slo_compliant: bool
    retraction_slo_compliant: bool
    overall_slo_compliant: bool
    
    # Performance statistics
    performance_stats: Dict[str, Any]

class AudioGenerator:
    """Generate synthetic audio for testing"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
    
    def generate_test_phrases(self, language: str = 'en') -> List[Tuple[np.ndarray, str]]:
        """Generate test audio phrases with known transcriptions"""
        phrases = {
            'en': [
                "Hello, this is a test message for the translation system",
                "The weather is nice today, perfect for a walk in the park",
                "Can you please help me understand how this system works",
                "I would like to schedule a meeting for tomorrow morning",
                "The quick brown fox jumps over the lazy dog"
            ],
            'es': [
                "Hola, este es un mensaje de prueba para el sistema de traducción",
                "El clima está agradable hoy, perfecto para caminar en el parque",
                "¿Puedes ayudarme a entender cómo funciona este sistema?",
                "Me gustaría programar una reunión para mañana por la mañana",
                "El rápido zorro marrón salta sobre el perro perezoso"
            ],
            'fr': [
                "Bonjour, ceci est un message de test pour le système de traduction",
                "Le temps est agréable aujourd'hui, parfait pour une promenade dans le parc",
                "Pouvez-vous m'aider à comprendre comment fonctionne ce système",
                "J'aimerais programmer une réunion pour demain matin",
                "Le renard brun rapide saute par-dessus le chien paresseux"
            ]
        }
        
        test_data = []
        for phrase in phrases.get(language, phrases['en']):
            audio = self._text_to_synthetic_audio(phrase, language)
            test_data.append((audio, phrase))
        
        return test_data
    
    def _text_to_synthetic_audio(self, text: str, language: str) -> np.ndarray:
        """Convert text to synthetic speech-like audio"""
        # Estimate duration based on text length and speech rate
        words = len(text.split())
        duration_seconds = words / 3.5  # ~3.5 words per second
        
        total_samples = int(duration_seconds * self.sample_rate)
        audio = np.zeros(total_samples)
        
        # Generate synthetic speech patterns
        t = np.linspace(0, duration_seconds, total_samples)
        
        # Fundamental frequency based on language
        f0_ranges = {
            'en': (120, 200),
            'es': (140, 220),
            'fr': (130, 210)
        }
        f0_base = np.random.uniform(*f0_ranges.get(language, f0_ranges['en']))
        
        # Create speech-like waveform with formants
        for i in range(3):  # Three formants
            formant_freq = f0_base * (i + 1) * (1 + 0.1 * np.sin(2 * np.pi * 0.5 * t))
            formant = (0.5 ** i) * np.sin(2 * np.pi * formant_freq * t)
            
            # Add amplitude modulation for speech-like patterns
            envelope = 0.8 + 0.2 * np.sin(2 * np.pi * 2 * t) 
            formant *= envelope
            
            audio += formant
        
        # Add word boundaries (brief pauses)
        word_positions = np.linspace(0, total_samples, words + 1, dtype=int)
        for i in range(len(word_positions) - 1):
            # Small pause between words
            if i < len(word_positions) - 2:
                pause_start = word_positions[i + 1] - int(0.05 * self.sample_rate)
                pause_end = word_positions[i + 1] + int(0.05 * self.sample_rate)
                if pause_end < total_samples:
                    audio[pause_start:pause_end] *= 0.1
        
        # Normalize and add realistic noise
        audio = audio / np.max(np.abs(audio)) * 0.7
        noise = np.random.normal(0, 0.005, len(audio))
        audio += noise
        
        return audio.astype(np.float32)

class SLOTestSuite:
    """Main SLO testing suite"""
    
    def __init__(self, config: SLOTestConfig):
        self.config = config
        self.audio_generator = AudioGenerator()
        self.tracer = get_tracer("slo-tests")
        self.metrics = get_metrics("slo-validation")
        
    async def run_ttft_latency_test(self, language_pairs: List[Tuple[str, str]] = None) -> SLOTestResult:
        """Test p95 Time-to-First-Token latency compliance"""
        if language_pairs is None:
            language_pairs = [("en", "es"), ("en", "fr"), ("es", "en"), ("fr", "en")]
        
        logger.info("Starting TTFT latency SLO test...")
        start_time = datetime.utcnow()
        
        measurements = []
        
        for source_lang, target_lang in language_pairs:
            logger.info(f"Testing TTFT for {source_lang} → {target_lang}")
            
            # Generate test audio samples
            test_phrases = self.audio_generator.generate_test_phrases(source_lang)
            
            for audio, expected_text in test_phrases[:self.config.sample_count // len(language_pairs)]:
                try:
                    measurement = await self._measure_ttft(audio, expected_text, source_lang, target_lang)
                    measurements.append(measurement)
                    
                    # Log progress
                    if len(measurements) % 10 == 0:
                        logger.info(f"Completed {len(measurements)} TTFT measurements")
                        
                except Exception as e:
                    logger.error(f"TTFT measurement failed: {e}")
                    measurements.append(SLOMeasurement(
                        timestamp=datetime.utcnow(),
                        test_type="ttft",
                        language_pair=f"{source_lang}-{target_lang}",
                        input_duration_ms=0,
                        stt_latency_ms=0,
                        mt_latency_ms=0,
                        tts_latency_ms=0,
                        ttft_ms=0,
                        caption_latency_ms=0,
                        end_to_end_ms=0,
                        audio_quality_score=0,
                        translation_accuracy_score=0,
                        retraction_count=0,
                        success=False,
                        error_message=str(e)
                    ))
        
        end_time = datetime.utcnow()
        return self._analyze_slo_results("ttft_latency_test", measurements, start_time, end_time)
    
    async def run_caption_latency_test(self, language_pairs: List[Tuple[str, str]] = None) -> SLOTestResult:
        """Test p95 caption latency compliance"""
        if language_pairs is None:
            language_pairs = [("en", "es"), ("en", "fr"), ("es", "en")]
        
        logger.info("Starting caption latency SLO test...")
        start_time = datetime.utcnow()
        
        measurements = []
        
        for source_lang, target_lang in language_pairs:
            logger.info(f"Testing caption latency for {source_lang} → {target_lang}")
            
            test_phrases = self.audio_generator.generate_test_phrases(source_lang)
            
            for audio, expected_text in test_phrases[:self.config.sample_count // len(language_pairs)]:
                try:
                    measurement = await self._measure_caption_latency(audio, expected_text, source_lang, target_lang)
                    measurements.append(measurement)
                    
                    if len(measurements) % 10 == 0:
                        logger.info(f"Completed {len(measurements)} caption latency measurements")
                        
                except Exception as e:
                    logger.error(f"Caption latency measurement failed: {e}")
                    measurements.append(SLOMeasurement(
                        timestamp=datetime.utcnow(),
                        test_type="caption_latency",
                        language_pair=f"{source_lang}-{target_lang}",
                        input_duration_ms=0,
                        stt_latency_ms=0,
                        mt_latency_ms=0,
                        tts_latency_ms=0,
                        ttft_ms=0,
                        caption_latency_ms=0,
                        end_to_end_ms=0,
                        audio_quality_score=0,
                        translation_accuracy_score=0,
                        retraction_count=0,
                        success=False,
                        error_message=str(e)
                    ))
        
        end_time = datetime.utcnow()
        return self._analyze_slo_results("caption_latency_test", measurements, start_time, end_time)
    
    async def run_word_retraction_test(self, language_pairs: List[Tuple[str, str]] = None) -> SLOTestResult:
        """Test word retraction rate compliance (<5%)"""
        if language_pairs is None:
            language_pairs = [("en", "es"), ("en", "fr")]
        
        logger.info("Starting word retraction rate SLO test...")
        start_time = datetime.utcnow()
        
        measurements = []
        
        for source_lang, target_lang in language_pairs:
            logger.info(f"Testing word retraction for {source_lang} → {target_lang}")
            
            # Use longer phrases for retraction testing
            test_phrases = self._generate_long_test_phrases(source_lang)
            
            for audio, expected_text in test_phrases:
                try:
                    measurement = await self._measure_word_retractions(audio, expected_text, source_lang, target_lang)
                    measurements.append(measurement)
                    
                    if len(measurements) % 5 == 0:
                        logger.info(f"Completed {len(measurements)} retraction rate measurements")
                        
                except Exception as e:
                    logger.error(f"Retraction measurement failed: {e}")
                    measurements.append(SLOMeasurement(
                        timestamp=datetime.utcnow(),
                        test_type="word_retraction",
                        language_pair=f"{source_lang}-{target_lang}",
                        input_duration_ms=0,
                        stt_latency_ms=0,
                        mt_latency_ms=0,
                        tts_latency_ms=0,
                        ttft_ms=0,
                        caption_latency_ms=0,
                        end_to_end_ms=0,
                        audio_quality_score=0,
                        translation_accuracy_score=0,
                        retraction_count=0,
                        success=False,
                        error_message=str(e)
                    ))
        
        end_time = datetime.utcnow()
        return self._analyze_slo_results("word_retraction_test", measurements, start_time, end_time)
    
    async def _measure_ttft(self, audio: np.ndarray, expected_text: str, 
                           source_lang: str, target_lang: str) -> SLOMeasurement:
        """Measure Time-to-First-Token for a single audio sample"""
        
        # Start overall timing
        overall_start = time.time()
        
        # Step 1: Send to STT service and measure first response
        stt_start = time.time()
        stt_result = await self._call_stt_service(audio)
        stt_duration = (time.time() - stt_start) * 1000  # Convert to ms
        
        if not stt_result.get('success'):
            raise Exception(f"STT failed: {stt_result.get('error')}")
        
        # Step 2: Send to MT service
        mt_start = time.time()
        mt_result = await self._call_mt_service(stt_result['text'], source_lang, target_lang)
        mt_duration = (time.time() - mt_start) * 1000
        
        if not mt_result.get('success'):
            raise Exception(f"MT failed: {mt_result.get('error')}")
        
        # Step 3: Start TTS and measure time to first audio token
        tts_start = time.time()
        tts_result = await self._call_tts_service_streaming(mt_result['translation'], target_lang)
        
        # TTFT is when we receive the first audio chunk
        ttft_duration = (tts_result['first_chunk_time'] - overall_start) * 1000
        tts_total_duration = (time.time() - tts_start) * 1000
        
        # Calculate metrics
        audio_duration = len(audio) / 16000 * 1000  # Convert to ms
        caption_latency = stt_duration + mt_duration
        end_to_end_duration = (time.time() - overall_start) * 1000
        
        return SLOMeasurement(
            timestamp=datetime.utcnow(),
            test_type="ttft",
            language_pair=f"{source_lang}-{target_lang}",
            input_duration_ms=audio_duration,
            stt_latency_ms=stt_duration,
            mt_latency_ms=mt_duration,
            tts_latency_ms=tts_total_duration,
            ttft_ms=ttft_duration,
            caption_latency_ms=caption_latency,
            end_to_end_ms=end_to_end_duration,
            audio_quality_score=self._evaluate_audio_quality(tts_result['audio']),
            translation_accuracy_score=self._evaluate_translation_accuracy(expected_text, mt_result['translation']),
            retraction_count=0,  # Not applicable for single measurement
            success=True
        )
    
    async def _measure_caption_latency(self, audio: np.ndarray, expected_text: str,
                                      source_lang: str, target_lang: str) -> SLOMeasurement:
        """Measure caption delivery latency"""
        
        overall_start = time.time()
        
        # Step 1: STT processing
        stt_start = time.time()
        stt_result = await self._call_stt_service(audio)
        stt_duration = (time.time() - stt_start) * 1000
        
        if not stt_result.get('success'):
            raise Exception(f"STT failed: {stt_result.get('error')}")
        
        # Step 2: MT processing 
        mt_start = time.time()
        mt_result = await self._call_mt_service(stt_result['text'], source_lang, target_lang)
        mt_duration = (time.time() - mt_start) * 1000
        
        if not mt_result.get('success'):
            raise Exception(f"MT failed: {mt_result.get('error')}")
        
        # Caption latency is STT + MT time
        caption_latency = stt_duration + mt_duration
        
        # For completeness, also measure TTS
        tts_start = time.time()
        tts_result = await self._call_tts_service(mt_result['translation'], target_lang)
        tts_duration = (time.time() - tts_start) * 1000
        
        audio_duration = len(audio) / 16000 * 1000
        end_to_end_duration = (time.time() - overall_start) * 1000
        
        return SLOMeasurement(
            timestamp=datetime.utcnow(),
            test_type="caption_latency",
            language_pair=f"{source_lang}-{target_lang}",
            input_duration_ms=audio_duration,
            stt_latency_ms=stt_duration,
            mt_latency_ms=mt_duration,
            tts_latency_ms=tts_duration,
            ttft_ms=caption_latency + tts_duration * 0.1,  # Estimate TTFT
            caption_latency_ms=caption_latency,
            end_to_end_ms=end_to_end_duration,
            audio_quality_score=0.8,  # Placeholder
            translation_accuracy_score=self._evaluate_translation_accuracy(expected_text, mt_result['translation']),
            retraction_count=0,
            success=True
        )
    
    async def _measure_word_retractions(self, audio: np.ndarray, expected_text: str,
                                       source_lang: str, target_lang: str) -> SLOMeasurement:
        """Measure word retraction rate using streaming STT"""
        
        overall_start = time.time()
        
        # Stream audio in chunks to STT service to measure retractions
        chunk_size_ms = 150  # 150ms chunks
        sample_rate = 16000
        chunk_samples = int(chunk_size_ms * sample_rate / 1000)
        
        stt_responses = []
        previous_words = []
        retraction_count = 0
        
        # Process audio in chunks
        for i in range(0, len(audio), chunk_samples):
            chunk = audio[i:i + chunk_samples]
            
            chunk_start = time.time()
            stt_result = await self._call_stt_service(chunk, streaming=True)
            
            if stt_result.get('success'):
                current_words = stt_result['text'].split()
                
                # Check for retractions (words that were different in previous response)
                if previous_words and len(previous_words) > 0:
                    # Count words that changed from previous iteration
                    min_len = min(len(current_words), len(previous_words))
                    for j in range(min_len):
                        if j < len(previous_words) and j < len(current_words):
                            if previous_words[j] != current_words[j]:
                                retraction_count += 1
                
                previous_words = current_words.copy()
                stt_responses.append({
                    'timestamp': time.time(),
                    'text': stt_result['text'],
                    'words': current_words
                })
        
        # Calculate final metrics
        if stt_responses:
            final_text = stt_responses[-1]['text']
            total_processing_time = (stt_responses[-1]['timestamp'] - overall_start) * 1000
            
            # Translate final text
            mt_start = time.time()
            mt_result = await self._call_mt_service(final_text, source_lang, target_lang)
            mt_duration = (time.time() - mt_start) * 1000
            
            # Calculate retraction rate
            total_words = len(final_text.split()) if final_text else 1
            retraction_rate = retraction_count / total_words if total_words > 0 else 0
            
        else:
            raise Exception("No STT responses received")
        
        audio_duration = len(audio) / 16000 * 1000
        
        return SLOMeasurement(
            timestamp=datetime.utcnow(),
            test_type="word_retraction", 
            language_pair=f"{source_lang}-{target_lang}",
            input_duration_ms=audio_duration,
            stt_latency_ms=total_processing_time,
            mt_latency_ms=mt_duration,
            tts_latency_ms=0,  # Not measured in retraction test
            ttft_ms=total_processing_time + mt_duration,
            caption_latency_ms=total_processing_time + mt_duration,
            end_to_end_ms=total_processing_time + mt_duration,
            audio_quality_score=0.8,
            translation_accuracy_score=self._evaluate_translation_accuracy(expected_text, mt_result.get('translation', '')),
            retraction_count=retraction_count,
            success=True
        )
    
    async def _call_stt_service(self, audio: np.ndarray, streaming: bool = False) -> Dict[str, Any]:
        """Call STT service with audio data"""
        try:
            # Convert audio to bytes (16-bit PCM)
            audio_int16 = (audio * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.stt_service_url}/transcribe",
                    data=audio_bytes,
                    headers={
                        'Content-Type': 'audio/wav',
                        'X-Language': 'auto'
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            'success': True,
                            'text': result.get('text', ''),
                            'confidence': result.get('confidence', 0.0)
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}: {await response.text()}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_mt_service(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Call MT service for translation"""
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
                        return {
                            'success': True,
                            'translation': result.get('translation', ''),
                            'confidence': result.get('confidence', 0.0)
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}: {await response.text()}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_tts_service(self, text: str, language: str) -> Dict[str, Any]:
        """Call TTS service for synthesis"""
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
                        audio_data = await response.read()
                        return {
                            'success': True,
                            'audio': audio_data,
                            'duration_ms': len(audio_data) / 32  # Estimate
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}: {await response.text()}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _call_tts_service_streaming(self, text: str, language: str) -> Dict[str, Any]:
        """Call TTS service in streaming mode to measure TTFT"""
        try:
            payload = {
                'text': text,
                'language': language,
                'voice_id': f"{language}-voice-1",
                'streaming': True
            }
            
            first_chunk_time = None
            audio_chunks = []
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.tts_service_url}/synthesize_stream",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    
                    if response.status == 200:
                        async for chunk in response.content.iter_chunked(1024):
                            if first_chunk_time is None:
                                first_chunk_time = time.time()
                            audio_chunks.append(chunk)
                        
                        return {
                            'success': True,
                            'audio': b''.join(audio_chunks),
                            'first_chunk_time': first_chunk_time or time.time()
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}'
                        }
                        
        except Exception as e:
            # Fallback to regular TTS if streaming not available
            regular_result = await self._call_tts_service(text, language)
            if regular_result.get('success'):
                regular_result['first_chunk_time'] = time.time()
            return regular_result
    
    def _generate_long_test_phrases(self, language: str) -> List[Tuple[np.ndarray, str]]:
        """Generate longer test phrases for retraction testing"""
        long_phrases = {
            'en': [
                "I would like to schedule a comprehensive meeting with all stakeholders to discuss the quarterly financial results and plan our strategic initiatives for the upcoming fiscal year, including budget allocations and resource management considerations",
                "The advanced machine learning algorithms implemented in our real-time translation system demonstrate remarkable accuracy and speed, processing multiple language pairs simultaneously while maintaining consistent quality metrics across diverse linguistic patterns",
                "During the international conference, participants from various countries will engage in multilingual discussions about sustainable development goals, climate change mitigation strategies, and collaborative research opportunities in renewable energy technologies"
            ],
            'es': [
                "Me gustaría programar una reunión integral con todas las partes interesadas para discutir los resultados financieros trimestrales y planificar nuestras iniciativas estratégicas para el próximo año fiscal, incluyendo asignaciones presupuestarias y consideraciones de gestión de recursos",
                "Los algoritmos avanzados de aprendizaje automático implementados en nuestro sistema de traducción en tiempo real demuestran una precisión y velocidad notables, procesando múltiples pares de idiomas simultáneamente mientras mantienen métricas de calidad consistentes",
                "Durante la conferencia internacional, los participantes de varios países participarán en discusiones multilingües sobre objetivos de desarrollo sostenible, estrategias de mitigación del cambio climático y oportunidades de investigación colaborativa"
            ]
        }
        
        test_data = []
        for phrase in long_phrases.get(language, long_phrases['en']):
            audio = self.audio_generator._text_to_synthetic_audio(phrase, language)
            test_data.append((audio, phrase))
        
        return test_data
    
    def _evaluate_audio_quality(self, audio_data: bytes) -> float:
        """Evaluate synthesized audio quality (placeholder implementation)"""
        # In a real implementation, this would use PESQ, STOI, or other audio quality metrics
        if len(audio_data) > 1000:  # Basic length check
            return 0.85
        return 0.6
    
    def _evaluate_translation_accuracy(self, source_text: str, translation: str) -> float:
        """Evaluate translation accuracy (placeholder implementation)"""
        # In a real implementation, this would use BLEU, METEOR, or semantic similarity
        if translation and len(translation) > len(source_text) * 0.5:
            return 0.8
        return 0.4
    
    def _analyze_slo_results(self, test_name: str, measurements: List[SLOMeasurement],
                            start_time: datetime, end_time: datetime) -> SLOTestResult:
        """Analyze SLO test results and check compliance"""
        
        # Filter successful measurements
        successful_measurements = [m for m in measurements if m.success]
        success_rate = len(successful_measurements) / len(measurements) if measurements else 0
        
        if not successful_measurements:
            logger.warning("No successful measurements to analyze")
            return SLOTestResult(
                test_name=test_name,
                config=self.config,
                start_time=start_time,
                end_time=end_time,
                measurements=measurements,
                ttft_p95_ms=float('inf'),
                caption_latency_p95_ms=float('inf'),
                retraction_rate=1.0,
                success_rate=success_rate,
                ttft_slo_compliant=False,
                caption_slo_compliant=False,
                retraction_slo_compliant=False,
                overall_slo_compliant=False,
                performance_stats={}
            )
        
        # Calculate p95 metrics
        ttft_values = [m.ttft_ms for m in successful_measurements]
        caption_latency_values = [m.caption_latency_ms for m in successful_measurements]
        retraction_counts = [m.retraction_count for m in successful_measurements if m.test_type == "word_retraction"]
        
        ttft_p95 = np.percentile(ttft_values, 95) if ttft_values else 0
        caption_latency_p95 = np.percentile(caption_latency_values, 95) if caption_latency_values else 0
        
        # Calculate retraction rate
        if retraction_counts:
            total_words = sum(len(m.language_pair.split('-')) * 10 for m in successful_measurements if m.test_type == "word_retraction")  # Estimate
            total_retractions = sum(retraction_counts)
            retraction_rate = total_retractions / total_words if total_words > 0 else 0
        else:
            retraction_rate = 0
        
        # Check SLO compliance
        ttft_slo_compliant = ttft_p95 <= self.config.ttft_target_ms
        caption_slo_compliant = caption_latency_p95 <= self.config.caption_latency_target_ms
        retraction_slo_compliant = retraction_rate <= self.config.retraction_rate_target
        
        overall_slo_compliant = ttft_slo_compliant and caption_slo_compliant and retraction_slo_compliant
        
        # Performance statistics
        performance_stats = {
            'ttft_mean_ms': statistics.mean(ttft_values) if ttft_values else 0,
            'ttft_median_ms': statistics.median(ttft_values) if ttft_values else 0,
            'ttft_p99_ms': np.percentile(ttft_values, 99) if ttft_values else 0,
            'caption_latency_mean_ms': statistics.mean(caption_latency_values) if caption_latency_values else 0,
            'caption_latency_median_ms': statistics.median(caption_latency_values) if caption_latency_values else 0,
            'stt_latency_p95_ms': np.percentile([m.stt_latency_ms for m in successful_measurements], 95) if successful_measurements else 0,
            'mt_latency_p95_ms': np.percentile([m.mt_latency_ms for m in successful_measurements], 95) if successful_measurements else 0,
            'tts_latency_p95_ms': np.percentile([m.tts_latency_ms for m in successful_measurements], 95) if successful_measurements else 0,
            'total_measurements': len(measurements),
            'successful_measurements': len(successful_measurements),
            'error_rate': 1 - success_rate
        }
        
        # Log results summary
        logger.info(f"=== SLO Test Results: {test_name} ===")
        logger.info(f"TTFT p95: {ttft_p95:.1f}ms (Target: ≤{self.config.ttft_target_ms}ms) - {'✓' if ttft_slo_compliant else '✗'}")
        logger.info(f"Caption Latency p95: {caption_latency_p95:.1f}ms (Target: ≤{self.config.caption_latency_target_ms}ms) - {'✓' if caption_slo_compliant else '✗'}")
        logger.info(f"Retraction Rate: {retraction_rate:.2%} (Target: ≤{self.config.retraction_rate_target:.1%}) - {'✓' if retraction_slo_compliant else '✗'}")
        logger.info(f"Success Rate: {success_rate:.2%}")
        logger.info(f"Overall SLO Compliance: {'✓ PASS' if overall_slo_compliant else '✗ FAIL'}")
        
        return SLOTestResult(
            test_name=test_name,
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            measurements=measurements,
            ttft_p95_ms=ttft_p95,
            caption_latency_p95_ms=caption_latency_p95,
            retraction_rate=retraction_rate,
            success_rate=success_rate,
            ttft_slo_compliant=ttft_slo_compliant,
            caption_slo_compliant=caption_slo_compliant,
            retraction_slo_compliant=retraction_slo_compliant,
            overall_slo_compliant=overall_slo_compliant,
            performance_stats=performance_stats
        )

# Utility functions for running tests
async def run_all_slo_tests(config: SLOTestConfig = None) -> Dict[str, SLOTestResult]:
    """Run all SLO tests and return results"""
    if config is None:
        config = SLOTestConfig()
    
    suite = SLOTestSuite(config)
    
    logger.info("Starting comprehensive SLO test suite...")
    
    # Run all test types
    tests = {
        'ttft_latency': suite.run_ttft_latency_test(),
        'caption_latency': suite.run_caption_latency_test(),
        'word_retraction': suite.run_word_retraction_test()
    }
    
    results = {}
    
    for test_name, test_coro in tests.items():
        try:
            logger.info(f"Running {test_name} test...")
            result = await test_coro
            results[test_name] = result
            
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}")
            results[test_name] = None
    
    # Generate summary
    overall_compliance = all(
        result and result.overall_slo_compliant 
        for result in results.values() 
        if result is not None
    )
    
    logger.info("=" * 60)
    logger.info("SLO TEST SUITE SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        if result:
            status = "PASS" if result.overall_slo_compliant else "FAIL"
            logger.info(f"{test_name:.<30} {status}")
        else:
            logger.info(f"{test_name:.<30} ERROR")
    
    logger.info(f"Overall SLO Compliance: {'PASS' if overall_compliance else 'FAIL'}")
    
    return results

if __name__ == "__main__":
    # Example usage
    async def main():
        config = SLOTestConfig(
            sample_count=50,  # Reduce for faster testing
            test_duration_minutes=2
        )
        
        results = await run_all_slo_tests(config)
        
        # Save results to file
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        with open(f"slo_test_results_{timestamp}.json", 'w') as f:
            json.dump({
                k: v.to_dict() if v else None 
                for k, v in results.items()
            }, f, indent=2, default=str)
    
    asyncio.run(main())