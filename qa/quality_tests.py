"""
Quality Assurance Tests for The HIVE Translation System
Translation accuracy, audio quality, and semantic validation framework
"""

import asyncio
import aiohttp
import numpy as np
import logging
import json
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import sys
import difflib
from collections import defaultdict
import soundfile as sf
import librosa
from scipy import signal
from scipy.stats import pearsonr

# Add backend path for imports  
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from observability.tracer import get_tracer
from observability.metrics import get_metrics

# Import audio generation
from .slo_tests import AudioGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QualityTestConfig:
    """Configuration for quality assurance testing"""
    # Service endpoints
    stt_service_url: str = "http://localhost:8001"
    mt_service_url: str = "http://localhost:8002" 
    tts_service_url: str = "http://localhost:8003"
    
    # Quality thresholds
    min_translation_accuracy_bleu: float = 0.5
    min_translation_accuracy_semantic: float = 0.7
    min_audio_quality_snr: float = 20.0  # dB
    min_audio_quality_pesq: float = 3.0
    max_word_error_rate: float = 0.15  # 15%
    min_voice_naturalness: float = 3.5  # 1-5 scale
    
    # Test languages
    test_languages: List[str] = None
    language_pairs: List[Tuple[str, str]] = None
    
    def __post_init__(self):
        if self.test_languages is None:
            self.test_languages = ["en", "es", "fr", "de", "ja", "zh"]
        if self.language_pairs is None:
            self.language_pairs = [
                ("en", "es"), ("en", "fr"), ("en", "de"), ("en", "ja"),
                ("es", "en"), ("fr", "en"), ("de", "en"), ("ja", "en")
            ]

@dataclass
class TranslationQualityResult:
    """Result from translation quality assessment"""
    source_text: str
    target_text: str
    reference_translation: str
    predicted_translation: str
    source_language: str
    target_language: str
    
    # Accuracy metrics
    bleu_score: float
    meteor_score: float
    semantic_similarity: float
    word_error_rate: float
    character_error_rate: float
    
    # Linguistic analysis
    fluency_score: float
    adequacy_score: float
    context_preservation: float
    
    # Quality assessment
    overall_quality: float
    quality_grade: str  # A, B, C, D, F
    
    timestamp: datetime

@dataclass 
class AudioQualityResult:
    """Result from audio quality assessment"""
    original_text: str
    synthesized_audio_path: str
    language: str
    voice_id: str
    
    # Technical quality metrics
    snr_db: float
    thd_percent: float
    frequency_response_score: float
    dynamic_range_db: float
    
    # Perceptual quality metrics
    pesq_score: float
    stoi_score: float
    naturalness_score: float
    intelligibility_score: float
    
    # Audio characteristics
    duration_seconds: float
    sample_rate: int
    bit_depth: int
    
    # Quality assessment
    overall_quality: float
    quality_grade: str
    
    timestamp: datetime

@dataclass
class QualityTestResult:
    """Complete quality test result"""
    test_name: str
    config: QualityTestConfig
    start_time: datetime
    end_time: datetime
    
    # Translation quality results
    translation_results: List[TranslationQualityResult]
    avg_translation_quality: float
    translation_compliance: bool
    
    # Audio quality results
    audio_results: List[AudioQualityResult]
    avg_audio_quality: float
    audio_compliance: bool
    
    # Overall assessment
    overall_quality_score: float
    quality_compliant: bool
    
    # Detailed analysis
    language_performance: Dict[str, float]
    voice_performance: Dict[str, float]
    error_analysis: Dict[str, List[str]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'translation_results': [asdict(r) for r in self.translation_results],
            'audio_results': [asdict(r) for r in self.audio_results]
        }

class TranslationQualityEvaluator:
    """Evaluate translation accuracy and quality"""
    
    def __init__(self, config: QualityTestConfig):
        self.config = config
        self.tracer = get_tracer("translation-quality-evaluator")
        
        # Reference translations for known test cases
        self.reference_translations = self._load_reference_translations()
    
    def _load_reference_translations(self) -> Dict[str, Dict[str, str]]:
        """Load reference translations for evaluation"""
        return {
            "en": {
                "es": {
                    "Hello, how are you today?": "Hola, ¿cómo estás hoy?",
                    "The weather is beautiful.": "El clima está hermoso.",
                    "I would like to order coffee.": "Me gustaría pedir café.",
                    "What time is the meeting?": "¿A qué hora es la reunión?",
                    "Thank you for your help.": "Gracias por tu ayuda.",
                    "This is a complex technical document about machine learning algorithms.": "Este es un documento técnico complejo sobre algoritmos de aprendizaje automático.",
                    "The quarterly financial results show significant improvement.": "Los resultados financieros trimestrales muestran una mejora significativa.",
                    "Please ensure all safety protocols are followed during the procedure.": "Asegúrese de que se sigan todos los protocolos de seguridad durante el procedimiento."
                },
                "fr": {
                    "Hello, how are you today?": "Bonjour, comment allez-vous aujourd'hui?",
                    "The weather is beautiful.": "Le temps est magnifique.",
                    "I would like to order coffee.": "Je voudrais commander du café.",
                    "What time is the meeting?": "À quelle heure est la réunion?",
                    "Thank you for your help.": "Merci pour votre aide.",
                    "This is a complex technical document about machine learning algorithms.": "Il s'agit d'un document technique complexe sur les algorithmes d'apprentissage automatique.",
                    "The quarterly financial results show significant improvement.": "Les résultats financiers trimestraux montrent une amélioration significative.",
                    "Please ensure all safety protocols are followed during the procedure.": "Veuillez vous assurer que tous les protocoles de sécurité sont suivis pendant la procédure."
                },
                "de": {
                    "Hello, how are you today?": "Hallo, wie geht es dir heute?",
                    "The weather is beautiful.": "Das Wetter ist schön.",
                    "I would like to order coffee.": "Ich möchte gerne Kaffee bestellen.",
                    "What time is the meeting?": "Um wie viel Uhr ist das Meeting?",
                    "Thank you for your help.": "Danke für deine Hilfe.",
                    "This is a complex technical document about machine learning algorithms.": "Dies ist ein komplexes technisches Dokument über Algorithmen des maschinellen Lernens.",
                    "The quarterly financial results show significant improvement.": "Die Quartalsergebnisse zeigen eine deutliche Verbesserung.",
                    "Please ensure all safety protocols are followed during the procedure.": "Bitte stellen Sie sicher, dass alle Sicherheitsprotokolle während des Verfahrens befolgt werden."
                }
            },
            # Add reverse translations
            "es": {
                "en": {
                    "Hola, ¿cómo estás hoy?": "Hello, how are you today?",
                    "El clima está hermoso.": "The weather is beautiful.",
                    "Me gustaría pedir café.": "I would like to order coffee.",
                    "¿A qué hora es la reunión?": "What time is the meeting?",
                    "Gracias por tu ayuda.": "Thank you for your help."
                }
            },
            "fr": {
                "en": {
                    "Bonjour, comment allez-vous aujourd'hui?": "Hello, how are you today?",
                    "Le temps est magnifique.": "The weather is beautiful.",
                    "Je voudrais commander du café.": "I would like to order coffee.",
                    "À quelle heure est la réunion?": "What time is the meeting?",
                    "Merci pour votre aide.": "Thank you for your help."
                }
            }
        }
    
    async def evaluate_translation_quality(self, source_lang: str, target_lang: str,
                                          test_cases: Optional[List[str]] = None) -> List[TranslationQualityResult]:
        """Evaluate translation quality for a language pair"""
        if test_cases is None:
            # Use reference test cases
            test_cases = list(
                self.reference_translations.get(source_lang, {}).get(target_lang, {}).keys()
            )
        
        if not test_cases:
            logger.warning(f"No test cases available for {source_lang} → {target_lang}")
            return []
        
        results = []
        
        for source_text in test_cases:
            try:
                # Get reference translation
                reference = self.reference_translations.get(source_lang, {}).get(target_lang, {}).get(source_text)
                
                if not reference:
                    logger.warning(f"No reference translation for: {source_text}")
                    continue
                
                # Get machine translation
                mt_result = await self._call_mt_service(source_text, source_lang, target_lang)
                
                if not mt_result.get('success'):
                    logger.error(f"MT service failed for: {source_text}")
                    continue
                
                predicted_translation = mt_result['translation']
                
                # Calculate quality metrics
                quality_result = self._calculate_translation_quality(
                    source_text, predicted_translation, reference, source_lang, target_lang
                )
                
                results.append(quality_result)
                
            except Exception as e:
                logger.error(f"Error evaluating translation for '{source_text}': {e}")
        
        return results
    
    def _calculate_translation_quality(self, source_text: str, predicted: str, 
                                     reference: str, source_lang: str, target_lang: str) -> TranslationQualityResult:
        """Calculate comprehensive translation quality metrics"""
        
        # BLEU score calculation
        bleu_score = self._calculate_bleu_score(predicted, reference)
        
        # METEOR score (simplified implementation)
        meteor_score = self._calculate_meteor_score(predicted, reference)
        
        # Semantic similarity
        semantic_similarity = self._calculate_semantic_similarity(predicted, reference)
        
        # Error rates
        word_error_rate = self._calculate_word_error_rate(predicted, reference)
        character_error_rate = self._calculate_character_error_rate(predicted, reference)
        
        # Linguistic analysis
        fluency_score = self._evaluate_fluency(predicted, target_lang)
        adequacy_score = self._evaluate_adequacy(predicted, reference)
        context_preservation = self._evaluate_context_preservation(source_text, predicted)
        
        # Overall quality calculation
        overall_quality = self._calculate_overall_quality(
            bleu_score, meteor_score, semantic_similarity, fluency_score, adequacy_score
        )
        
        # Quality grading
        quality_grade = self._assign_quality_grade(overall_quality)
        
        return TranslationQualityResult(
            source_text=source_text,
            target_text=predicted,
            reference_translation=reference,
            predicted_translation=predicted,
            source_language=source_lang,
            target_language=target_lang,
            bleu_score=bleu_score,
            meteor_score=meteor_score,
            semantic_similarity=semantic_similarity,
            word_error_rate=word_error_rate,
            character_error_rate=character_error_rate,
            fluency_score=fluency_score,
            adequacy_score=adequacy_score,
            context_preservation=context_preservation,
            overall_quality=overall_quality,
            quality_grade=quality_grade,
            timestamp=datetime.utcnow()
        )
    
    def _calculate_bleu_score(self, predicted: str, reference: str) -> float:
        """Calculate BLEU score (simplified implementation)"""
        try:
            pred_tokens = predicted.lower().split()
            ref_tokens = reference.lower().split()
            
            if not pred_tokens or not ref_tokens:
                return 0.0
            
            # 1-gram precision
            pred_1grams = set(pred_tokens)
            ref_1grams = set(ref_tokens)
            precision_1 = len(pred_1grams & ref_1grams) / len(pred_1grams) if pred_1grams else 0
            
            # 2-gram precision
            pred_2grams = set(zip(pred_tokens[:-1], pred_tokens[1:]))
            ref_2grams = set(zip(ref_tokens[:-1], ref_tokens[1:]))
            precision_2 = len(pred_2grams & ref_2grams) / len(pred_2grams) if pred_2grams else 0
            
            # Brevity penalty
            bp = min(1, len(pred_tokens) / len(ref_tokens)) if ref_tokens else 0
            
            # Simplified BLEU calculation
            if precision_1 > 0 and precision_2 > 0:
                bleu = bp * (precision_1 * precision_2) ** 0.5
            else:
                bleu = 0.0
            
            return min(1.0, bleu)
            
        except Exception as e:
            logger.error(f"Error calculating BLEU score: {e}")
            return 0.0
    
    def _calculate_meteor_score(self, predicted: str, reference: str) -> float:
        """Calculate METEOR score (simplified implementation)"""
        try:
            pred_tokens = predicted.lower().split()
            ref_tokens = reference.lower().split()
            
            if not pred_tokens or not ref_tokens:
                return 0.0
            
            # Exact matches
            matches = len(set(pred_tokens) & set(ref_tokens))
            
            # Precision and recall
            precision = matches / len(pred_tokens) if pred_tokens else 0
            recall = matches / len(ref_tokens) if ref_tokens else 0
            
            # F-mean
            if precision + recall > 0:
                f_mean = (precision * recall) / (0.9 * precision + 0.1 * recall)
            else:
                f_mean = 0
            
            return min(1.0, f_mean)
            
        except Exception as e:
            logger.error(f"Error calculating METEOR score: {e}")
            return 0.0
    
    def _calculate_semantic_similarity(self, predicted: str, reference: str) -> float:
        """Calculate semantic similarity (simplified implementation)"""
        try:
            # Word overlap similarity (simplified)
            pred_words = set(predicted.lower().split())
            ref_words = set(reference.lower().split())
            
            if not pred_words and not ref_words:
                return 1.0
            if not pred_words or not ref_words:
                return 0.0
            
            intersection = len(pred_words & ref_words)
            union = len(pred_words | ref_words)
            
            jaccard_similarity = intersection / union if union > 0 else 0
            
            # Length similarity
            length_ratio = min(len(predicted), len(reference)) / max(len(predicted), len(reference))
            
            # Combined semantic similarity
            semantic_sim = 0.7 * jaccard_similarity + 0.3 * length_ratio
            
            return min(1.0, semantic_sim)
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _calculate_word_error_rate(self, predicted: str, reference: str) -> float:
        """Calculate Word Error Rate (WER)"""
        try:
            pred_words = predicted.split()
            ref_words = reference.split()
            
            if not ref_words:
                return 1.0 if pred_words else 0.0
            
            # Calculate edit distance
            d = [[0] * (len(pred_words) + 1) for _ in range(len(ref_words) + 1)]
            
            for i in range(len(ref_words) + 1):
                d[i][0] = i
            for j in range(len(pred_words) + 1):
                d[0][j] = j
            
            for i in range(1, len(ref_words) + 1):
                for j in range(1, len(pred_words) + 1):
                    if ref_words[i-1] == pred_words[j-1]:
                        d[i][j] = d[i-1][j-1]
                    else:
                        d[i][j] = min(d[i-1][j], d[i][j-1], d[i-1][j-1]) + 1
            
            wer = d[len(ref_words)][len(pred_words)] / len(ref_words)
            return min(1.0, wer)
            
        except Exception as e:
            logger.error(f"Error calculating WER: {e}")
            return 1.0
    
    def _calculate_character_error_rate(self, predicted: str, reference: str) -> float:
        """Calculate Character Error Rate (CER)"""
        try:
            if not reference:
                return 1.0 if predicted else 0.0
            
            # Use difflib to calculate character-level differences
            matcher = difflib.SequenceMatcher(None, reference, predicted)
            char_errors = sum(max(len(reference[i:i+n]), len(predicted[j:j+m])) 
                            for tag, i, i_end, j, j_end in matcher.get_opcodes() 
                            if tag != 'equal'
                            for n, m in [(i_end-i, j_end-j)])
            
            cer = char_errors / len(reference) if reference else 0
            return min(1.0, cer)
            
        except Exception as e:
            logger.error(f"Error calculating CER: {e}")
            return 1.0
    
    def _evaluate_fluency(self, text: str, language: str) -> float:
        """Evaluate translation fluency (simplified heuristic)"""
        try:
            if not text.strip():
                return 0.0
            
            score = 3.0  # Start with neutral score
            
            # Check for proper sentence structure
            sentences = re.split(r'[.!?]+', text.strip())
            if sentences:
                avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / len([s for s in sentences if s.strip()])
                
                # Prefer moderate sentence lengths
                if 5 <= avg_sentence_length <= 25:
                    score += 0.5
                elif avg_sentence_length < 3 or avg_sentence_length > 40:
                    score -= 0.5
            
            # Check for punctuation
            if re.search(r'[.!?]', text):
                score += 0.3
            
            # Check for capitalization
            if text[0].isupper() if text else False:
                score += 0.2
            
            # Language-specific checks
            if language == "es":
                # Spanish-specific patterns
                if re.search(r'[¿¡]', text):
                    score += 0.3
            elif language == "fr":
                # French-specific patterns  
                if re.search(r'[àâäéèêëîïôöùûüÿç]', text.lower()):
                    score += 0.2
            elif language == "de":
                # German-specific patterns
                if re.search(r'[äöüß]', text.lower()):
                    score += 0.2
            
            return min(5.0, max(1.0, score))
            
        except Exception as e:
            logger.error(f"Error evaluating fluency: {e}")
            return 3.0
    
    def _evaluate_adequacy(self, predicted: str, reference: str) -> float:
        """Evaluate translation adequacy"""
        try:
            # Based on content preservation
            pred_content_words = set(re.findall(r'\b\w+\b', predicted.lower()))
            ref_content_words = set(re.findall(r'\b\w+\b', reference.lower()))
            
            if not ref_content_words:
                return 3.0
            
            content_overlap = len(pred_content_words & ref_content_words) / len(ref_content_words)
            
            # Convert to 1-5 scale
            adequacy_score = 1 + (content_overlap * 4)
            
            return min(5.0, adequacy_score)
            
        except Exception as e:
            logger.error(f"Error evaluating adequacy: {e}")
            return 3.0
    
    def _evaluate_context_preservation(self, source: str, translation: str) -> float:
        """Evaluate context preservation (simplified)"""
        try:
            # Check if key entities and concepts are preserved
            source_entities = re.findall(r'\b[A-Z][a-z]+\b', source)
            trans_entities = re.findall(r'\b[A-Z][a-z]+\b', translation)
            
            if source_entities:
                entity_preservation = len(set(source_entities) & set(trans_entities)) / len(set(source_entities))
            else:
                entity_preservation = 1.0
            
            # Check length ratio (context completeness)
            length_ratio = min(len(translation), len(source)) / max(len(translation), len(source)) if source and translation else 0
            
            context_score = 0.6 * entity_preservation + 0.4 * length_ratio
            
            return min(1.0, context_score)
            
        except Exception as e:
            logger.error(f"Error evaluating context preservation: {e}")
            return 0.5
    
    def _calculate_overall_quality(self, bleu: float, meteor: float, semantic: float,
                                 fluency: float, adequacy: float) -> float:
        """Calculate overall translation quality score"""
        try:
            # Normalize scores to 0-1 range
            normalized_fluency = (fluency - 1) / 4  # 1-5 scale to 0-1
            normalized_adequacy = (adequacy - 1) / 4  # 1-5 scale to 0-1
            
            # Weighted combination
            overall = (
                0.25 * bleu +
                0.20 * meteor + 
                0.20 * semantic +
                0.20 * normalized_fluency +
                0.15 * normalized_adequacy
            )
            
            return min(1.0, overall)
            
        except Exception as e:
            logger.error(f"Error calculating overall quality: {e}")
            return 0.0
    
    def _assign_quality_grade(self, score: float) -> str:
        """Assign letter grade based on quality score"""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
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
                            'translation': result.get('translation', '')
                        }
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

class AudioQualityEvaluator:
    """Evaluate synthesized audio quality"""
    
    def __init__(self, config: QualityTestConfig):
        self.config = config
        self.tracer = get_tracer("audio-quality-evaluator")
        self.audio_generator = AudioGenerator()
    
    async def evaluate_audio_quality(self, test_phrases: List[str], 
                                   language: str, voice_id: str = None) -> List[AudioQualityResult]:
        """Evaluate audio quality for given test phrases"""
        if voice_id is None:
            voice_id = f"{language}-voice-1"
        
        results = []
        
        for phrase in test_phrases:
            try:
                # Synthesize audio
                tts_result = await self._call_tts_service(phrase, language, voice_id)
                
                if not tts_result.get('success'):
                    logger.error(f"TTS failed for phrase: {phrase}")
                    continue
                
                audio_data = tts_result.get('audio_data')
                if not audio_data:
                    logger.error(f"No audio data returned for: {phrase}")
                    continue
                
                # Save audio to temporary file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(audio_data)
                    audio_path = temp_file.name
                
                # Evaluate audio quality
                quality_result = self._evaluate_audio_file(phrase, audio_path, language, voice_id)
                results.append(quality_result)
                
                # Clean up temporary file
                Path(audio_path).unlink(missing_ok=True)
                
            except Exception as e:
                logger.error(f"Error evaluating audio for '{phrase}': {e}")
        
        return results
    
    def _evaluate_audio_file(self, text: str, audio_path: str, 
                           language: str, voice_id: str) -> AudioQualityResult:
        """Evaluate quality of an audio file"""
        try:
            # Load audio
            audio, sample_rate = librosa.load(audio_path, sr=None)
            
            # Technical quality metrics
            snr_db = self._calculate_snr(audio)
            thd_percent = self._calculate_thd(audio, sample_rate)
            freq_response_score = self._evaluate_frequency_response(audio, sample_rate)
            dynamic_range = self._calculate_dynamic_range(audio)
            
            # Perceptual quality metrics (simplified implementations)
            pesq_score = self._estimate_pesq(audio, sample_rate)
            stoi_score = self._estimate_stoi(audio, sample_rate)
            naturalness_score = self._evaluate_naturalness(audio, sample_rate, language)
            intelligibility_score = self._evaluate_intelligibility(audio, sample_rate, text)
            
            # Audio characteristics
            duration_seconds = len(audio) / sample_rate
            bit_depth = 16  # Assume 16-bit
            
            # Overall quality calculation
            overall_quality = self._calculate_overall_audio_quality(
                snr_db, pesq_score, stoi_score, naturalness_score, intelligibility_score
            )
            
            quality_grade = self._assign_audio_quality_grade(overall_quality)
            
            return AudioQualityResult(
                original_text=text,
                synthesized_audio_path=audio_path,
                language=language,
                voice_id=voice_id,
                snr_db=snr_db,
                thd_percent=thd_percent,
                frequency_response_score=freq_response_score,
                dynamic_range_db=dynamic_range,
                pesq_score=pesq_score,
                stoi_score=stoi_score,
                naturalness_score=naturalness_score,
                intelligibility_score=intelligibility_score,
                duration_seconds=duration_seconds,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                overall_quality=overall_quality,
                quality_grade=quality_grade,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error evaluating audio file {audio_path}: {e}")
            # Return default result on error
            return AudioQualityResult(
                original_text=text,
                synthesized_audio_path=audio_path,
                language=language,
                voice_id=voice_id,
                snr_db=0.0,
                thd_percent=100.0,
                frequency_response_score=0.0,
                dynamic_range_db=0.0,
                pesq_score=1.0,
                stoi_score=0.0,
                naturalness_score=1.0,
                intelligibility_score=0.0,
                duration_seconds=0.0,
                sample_rate=16000,
                bit_depth=16,
                overall_quality=0.0,
                quality_grade="F",
                timestamp=datetime.utcnow()
            )
    
    def _calculate_snr(self, audio: np.ndarray) -> float:
        """Calculate Signal-to-Noise Ratio"""
        try:
            # Simple SNR calculation
            signal_power = np.mean(audio ** 2)
            
            # Estimate noise (assume quiet segments are noise)
            sorted_audio = np.sort(np.abs(audio))
            noise_threshold = sorted_audio[int(len(sorted_audio) * 0.1)]  # Bottom 10%
            noise_samples = audio[np.abs(audio) <= noise_threshold]
            noise_power = np.mean(noise_samples ** 2) if len(noise_samples) > 0 else 1e-10
            
            snr = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else 40
            return max(0, min(60, snr))  # Clamp between 0-60 dB
            
        except Exception as e:
            logger.error(f"Error calculating SNR: {e}")
            return 20.0
    
    def _calculate_thd(self, audio: np.ndarray, sample_rate: int) -> float:
        """Calculate Total Harmonic Distortion (simplified)"""
        try:
            # FFT analysis
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)
            
            # Find fundamental frequency (simplified)
            magnitude = np.abs(fft)
            fundamental_idx = np.argmax(magnitude[1:]) + 1  # Skip DC
            fundamental_freq = freqs[fundamental_idx]
            
            if fundamental_freq == 0:
                return 10.0  # Default THD if no fundamental found
            
            # Find harmonics
            harmonics_power = 0
            fundamental_power = magnitude[fundamental_idx] ** 2
            
            for harmonic in range(2, 6):  # 2nd to 5th harmonics
                harmonic_freq = fundamental_freq * harmonic
                harmonic_idx = np.argmin(np.abs(freqs - harmonic_freq))
                if harmonic_idx < len(magnitude):
                    harmonics_power += magnitude[harmonic_idx] ** 2
            
            thd = np.sqrt(harmonics_power / fundamental_power) * 100 if fundamental_power > 0 else 10
            return min(100, max(0, thd))
            
        except Exception as e:
            logger.error(f"Error calculating THD: {e}")
            return 5.0
    
    def _evaluate_frequency_response(self, audio: np.ndarray, sample_rate: int) -> float:
        """Evaluate frequency response quality"""
        try:
            # Calculate power spectral density
            freqs, psd = signal.welch(audio, sample_rate, nperseg=1024)
            
            # Evaluate response in key frequency bands
            # Speech frequency range: 80Hz - 8kHz
            speech_band_mask = (freqs >= 80) & (freqs <= 8000)
            if not np.any(speech_band_mask):
                return 0.5
            
            speech_psd = psd[speech_band_mask]
            speech_freqs = freqs[speech_band_mask]
            
            # Check for reasonable distribution across speech frequencies
            low_freq_power = np.mean(speech_psd[speech_freqs <= 500])   # 80-500Hz
            mid_freq_power = np.mean(speech_psd[(speech_freqs > 500) & (speech_freqs <= 2000)])  # 500-2000Hz
            high_freq_power = np.mean(speech_psd[speech_freqs > 2000])  # 2000-8000Hz
            
            total_power = low_freq_power + mid_freq_power + high_freq_power
            
            if total_power == 0:
                return 0.5
            
            # Good speech should have balanced frequency distribution
            low_ratio = low_freq_power / total_power
            mid_ratio = mid_freq_power / total_power
            high_ratio = high_freq_power / total_power
            
            # Ideal ratios for speech (rough estimates)
            ideal_low = 0.3
            ideal_mid = 0.5
            ideal_high = 0.2
            
            # Calculate deviation from ideal
            deviation = (
                abs(low_ratio - ideal_low) + 
                abs(mid_ratio - ideal_mid) + 
                abs(high_ratio - ideal_high)
            )
            
            # Convert to score (lower deviation = higher score)
            score = max(0, 1 - deviation)
            return score
            
        except Exception as e:
            logger.error(f"Error evaluating frequency response: {e}")
            return 0.7
    
    def _calculate_dynamic_range(self, audio: np.ndarray) -> float:
        """Calculate dynamic range in dB"""
        try:
            if len(audio) == 0:
                return 0.0
            
            max_amplitude = np.max(np.abs(audio))
            # Use 99th percentile as noise floor to avoid outliers
            noise_floor = np.percentile(np.abs(audio), 1) 
            
            if noise_floor > 0:
                dynamic_range = 20 * np.log10(max_amplitude / noise_floor)
            else:
                dynamic_range = 60  # Default for silence
            
            return max(0, min(120, dynamic_range))  # Clamp to reasonable range
            
        except Exception as e:
            logger.error(f"Error calculating dynamic range: {e}")
            return 40.0
    
    def _estimate_pesq(self, audio: np.ndarray, sample_rate: int) -> float:
        """Estimate PESQ score (simplified heuristic)"""
        try:
            # This is a simplified heuristic since real PESQ requires reference signal
            # Real implementation would use pypesq library
            
            # Check basic quality indicators
            score = 2.5  # Start with neutral PESQ score
            
            # SNR contribution
            snr = self._calculate_snr(audio)
            if snr > 20:
                score += 0.8
            elif snr > 15:
                score += 0.5
            elif snr < 10:
                score -= 0.5
            
            # Dynamic range contribution
            dynamic_range = self._calculate_dynamic_range(audio)
            if dynamic_range > 30:
                score += 0.4
            elif dynamic_range < 20:
                score -= 0.3
            
            # Frequency response contribution
            freq_score = self._evaluate_frequency_response(audio, sample_rate)
            score += freq_score * 0.8
            
            return max(1.0, min(4.5, score))
            
        except Exception as e:
            logger.error(f"Error estimating PESQ: {e}")
            return 3.0
    
    def _estimate_stoi(self, audio: np.ndarray, sample_rate: int) -> float:
        """Estimate STOI (Short-Time Objective Intelligibility) score"""
        try:
            # Simplified STOI estimation based on spectral characteristics
            
            # Calculate spectrogram
            f, t, Sxx = signal.spectrogram(audio, sample_rate, nperseg=256, noverlap=128)
            
            # Focus on speech frequency range (100Hz - 4kHz)
            speech_mask = (f >= 100) & (f <= 4000)
            if not np.any(speech_mask):
                return 0.5
            
            speech_spec = Sxx[speech_mask, :]
            
            # Measure spectral consistency over time
            if speech_spec.shape[1] > 1:
                # Calculate correlation between adjacent time frames
                correlations = []
                for i in range(speech_spec.shape[1] - 1):
                    corr, _ = pearsonr(speech_spec[:, i], speech_spec[:, i + 1])
                    if not np.isnan(corr):
                        correlations.append(abs(corr))
                
                if correlations:
                    avg_correlation = np.mean(correlations)
                    stoi_score = min(1.0, avg_correlation * 1.2)  # Scale and clamp
                else:
                    stoi_score = 0.5
            else:
                stoi_score = 0.5
            
            return stoi_score
            
        except Exception as e:
            logger.error(f"Error estimating STOI: {e}")
            return 0.7
    
    def _evaluate_naturalness(self, audio: np.ndarray, sample_rate: int, language: str) -> float:
        """Evaluate naturalness of synthesized speech"""
        try:
            # Simplified naturalness evaluation based on prosodic features
            score = 3.0  # Neutral score
            
            # Check for pitch variation (natural speech has pitch contours)
            # Use autocorrelation to estimate pitch
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[autocorr.size // 2:]
            
            # Find pitch periods
            if len(autocorr) > 100:
                # Look for periodicity in reasonable pitch range (80-400 Hz)
                min_period = int(sample_rate / 400)  # 400 Hz
                max_period = int(sample_rate / 80)   # 80 Hz
                
                if max_period < len(autocorr):
                    pitch_autocorr = autocorr[min_period:max_period]
                    if len(pitch_autocorr) > 0:
                        pitch_strength = np.max(pitch_autocorr) / autocorr[0] if autocorr[0] > 0 else 0
                        
                        # Good pitch strength indicates naturalness
                        if pitch_strength > 0.3:
                            score += 0.5
                        elif pitch_strength < 0.1:
                            score -= 0.5
            
            # Check for amplitude variation (natural speech has rhythm)
            if len(audio) > sample_rate:  # At least 1 second
                # Calculate RMS in 100ms windows
                window_size = int(0.1 * sample_rate)
                rms_values = []
                for i in range(0, len(audio) - window_size, window_size // 2):
                    window = audio[i:i + window_size]
                    rms = np.sqrt(np.mean(window ** 2))
                    rms_values.append(rms)
                
                if len(rms_values) > 2:
                    rms_variation = np.std(rms_values) / np.mean(rms_values) if np.mean(rms_values) > 0 else 0
                    
                    # Moderate variation is natural
                    if 0.2 <= rms_variation <= 0.8:
                        score += 0.4
                    elif rms_variation < 0.1:
                        score -= 0.3  # Too flat
                    elif rms_variation > 1.0:
                        score -= 0.2  # Too variable
            
            return max(1.0, min(5.0, score))
            
        except Exception as e:
            logger.error(f"Error evaluating naturalness: {e}")
            return 3.0
    
    def _evaluate_intelligibility(self, audio: np.ndarray, sample_rate: int, text: str) -> float:
        """Evaluate speech intelligibility"""
        try:
            # Simplified intelligibility assessment
            score = 3.0  # Neutral score
            
            # Check if audio duration matches text length expectation
            expected_duration = len(text.split()) / 3.5  # ~3.5 words per second
            actual_duration = len(audio) / sample_rate
            
            if actual_duration > 0:
                duration_ratio = expected_duration / actual_duration
                
                # Good ratio indicates proper pacing
                if 0.8 <= duration_ratio <= 1.2:
                    score += 0.5
                elif duration_ratio < 0.5 or duration_ratio > 2.0:
                    score -= 0.5
            
            # Check for pauses (silence periods)
            silence_threshold = np.percentile(np.abs(audio), 10)
            silence_mask = np.abs(audio) <= silence_threshold
            
            if len(audio) > 0:
                silence_ratio = np.sum(silence_mask) / len(audio)
                
                # Moderate silence is good for intelligibility
                if 0.1 <= silence_ratio <= 0.3:
                    score += 0.3
                elif silence_ratio > 0.5:
                    score -= 0.4  # Too much silence
                elif silence_ratio < 0.05:
                    score -= 0.2  # Too little pause
            
            # Check frequency content in consonant range (2-8 kHz)
            freqs, psd = signal.welch(audio, sample_rate, nperseg=1024)
            consonant_mask = (freqs >= 2000) & (freqs <= 8000)
            
            if np.any(consonant_mask):
                consonant_power = np.mean(psd[consonant_mask])
                total_power = np.mean(psd)
                
                consonant_ratio = consonant_power / total_power if total_power > 0 else 0
                
                # Sufficient high-frequency content for consonants
                if consonant_ratio > 0.15:
                    score += 0.4
                elif consonant_ratio < 0.05:
                    score -= 0.3
            
            return max(1.0, min(5.0, score))
            
        except Exception as e:
            logger.error(f"Error evaluating intelligibility: {e}")
            return 3.0
    
    def _calculate_overall_audio_quality(self, snr: float, pesq: float, stoi: float, 
                                       naturalness: float, intelligibility: float) -> float:
        """Calculate overall audio quality score"""
        try:
            # Normalize scores to 0-1 range
            normalized_snr = min(1.0, snr / 40)  # SNR up to 40 dB = 1.0
            normalized_pesq = (pesq - 1) / 3.5   # PESQ 1-4.5 to 0-1
            normalized_naturalness = (naturalness - 1) / 4  # 1-5 to 0-1
            normalized_intelligibility = (intelligibility - 1) / 4  # 1-5 to 0-1
            
            # Weighted combination
            overall = (
                0.20 * normalized_snr +
                0.30 * normalized_pesq +
                0.25 * stoi +
                0.15 * normalized_naturalness +
                0.10 * normalized_intelligibility
            )
            
            return min(1.0, max(0.0, overall))
            
        except Exception as e:
            logger.error(f"Error calculating overall audio quality: {e}")
            return 0.5
    
    def _assign_audio_quality_grade(self, score: float) -> str:
        """Assign letter grade for audio quality"""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    async def _call_tts_service(self, text: str, language: str, voice_id: str) -> Dict[str, Any]:
        """Call TTS service for synthesis"""
        try:
            payload = {
                'text': text,
                'language': language,
                'voice_id': voice_id
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
                            'audio_data': audio_data
                        }
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

class QualityTestSuite:
    """Main quality assurance test suite"""
    
    def __init__(self, config: QualityTestConfig = None):
        self.config = config or QualityTestConfig()
        self.translation_evaluator = TranslationQualityEvaluator(self.config)
        self.audio_evaluator = AudioQualityEvaluator(self.config)
        self.tracer = get_tracer("quality-test-suite")
    
    async def run_comprehensive_quality_tests(self) -> QualityTestResult:
        """Run comprehensive quality tests"""
        test_name = "comprehensive_quality_assessment"
        start_time = datetime.utcnow()
        
        logger.info("Starting comprehensive quality assessment...")
        
        translation_results = []
        audio_results = []
        
        # Test translation quality for each language pair
        for source_lang, target_lang in self.config.language_pairs:
            logger.info(f"Testing translation quality: {source_lang} → {target_lang}")
            
            try:
                lang_translation_results = await self.translation_evaluator.evaluate_translation_quality(
                    source_lang, target_lang
                )
                translation_results.extend(lang_translation_results)
                
            except Exception as e:
                logger.error(f"Translation quality test failed for {source_lang} → {target_lang}: {e}")
        
        # Test audio quality for each language
        test_phrases = [
            "Hello, this is a test of the audio quality.",
            "The quick brown fox jumps over the lazy dog.",
            "Please speak clearly and naturally for the best results."
        ]
        
        for language in self.config.test_languages[:3]:  # Limit to first 3 languages
            logger.info(f"Testing audio quality for language: {language}")
            
            try:
                lang_audio_results = await self.audio_evaluator.evaluate_audio_quality(
                    test_phrases, language
                )
                audio_results.extend(lang_audio_results)
                
            except Exception as e:
                logger.error(f"Audio quality test failed for {language}: {e}")
        
        end_time = datetime.utcnow()
        
        # Analyze results
        return self._analyze_quality_results(
            test_name, start_time, end_time, translation_results, audio_results
        )
    
    def _analyze_quality_results(self, test_name: str, start_time: datetime, end_time: datetime,
                               translation_results: List[TranslationQualityResult],
                               audio_results: List[AudioQualityResult]) -> QualityTestResult:
        """Analyze quality test results"""
        
        # Translation quality analysis
        if translation_results:
            avg_translation_quality = sum(r.overall_quality for r in translation_results) / len(translation_results)
            translation_compliance = avg_translation_quality >= self.config.min_translation_accuracy_semantic
        else:
            avg_translation_quality = 0.0
            translation_compliance = False
        
        # Audio quality analysis
        if audio_results:
            avg_audio_quality = sum(r.overall_quality for r in audio_results) / len(audio_results)
            audio_compliance = avg_audio_quality >= 0.7  # 70% threshold
        else:
            avg_audio_quality = 0.0
            audio_compliance = False
        
        # Overall quality assessment
        overall_quality_score = (avg_translation_quality + avg_audio_quality) / 2
        quality_compliant = translation_compliance and audio_compliance
        
        # Language performance analysis
        language_performance = {}
        for lang_pair in self.config.language_pairs:
            lang_key = f"{lang_pair[0]}-{lang_pair[1]}"
            lang_results = [r for r in translation_results 
                          if r.source_language == lang_pair[0] and r.target_language == lang_pair[1]]
            if lang_results:
                language_performance[lang_key] = sum(r.overall_quality for r in lang_results) / len(lang_results)
        
        # Voice performance analysis
        voice_performance = {}
        for result in audio_results:
            if result.voice_id not in voice_performance:
                voice_performance[result.voice_id] = []
            voice_performance[result.voice_id].append(result.overall_quality)
        
        # Average voice performances
        for voice_id in voice_performance:
            voice_performance[voice_id] = sum(voice_performance[voice_id]) / len(voice_performance[voice_id])
        
        # Error analysis
        error_analysis = {
            "translation_errors": [],
            "audio_errors": []
        }
        
        # Find low-quality translations
        for result in translation_results:
            if result.overall_quality < 0.6:
                error_analysis["translation_errors"].append(
                    f"Low quality translation ({result.quality_grade}): "
                    f"{result.source_language}→{result.target_language} - '{result.source_text}'"
                )
        
        # Find low-quality audio
        for result in audio_results:
            if result.overall_quality < 0.6:
                error_analysis["audio_errors"].append(
                    f"Low quality audio ({result.quality_grade}): "
                    f"{result.language} - '{result.original_text[:50]}...'"
                )
        
        # Log summary
        self._log_quality_summary(
            avg_translation_quality, translation_compliance,
            avg_audio_quality, audio_compliance,
            overall_quality_score, quality_compliant
        )
        
        return QualityTestResult(
            test_name=test_name,
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            translation_results=translation_results,
            avg_translation_quality=avg_translation_quality,
            translation_compliance=translation_compliance,
            audio_results=audio_results,
            avg_audio_quality=avg_audio_quality,
            audio_compliance=audio_compliance,
            overall_quality_score=overall_quality_score,
            quality_compliant=quality_compliant,
            language_performance=language_performance,
            voice_performance=voice_performance,
            error_analysis=error_analysis
        )
    
    def _log_quality_summary(self, avg_translation: float, translation_compliant: bool,
                           avg_audio: float, audio_compliant: bool,
                           overall: float, overall_compliant: bool):
        """Log quality test summary"""
        logger.info("=" * 70)
        logger.info("QUALITY ASSESSMENT SUMMARY")
        logger.info("=" * 70)
        
        logger.info(f"Translation Quality: {avg_translation:.3f} - {'✓ PASS' if translation_compliant else '✗ FAIL'}")
        logger.info(f"Audio Quality: {avg_audio:.3f} - {'✓ PASS' if audio_compliant else '✗ FAIL'}")
        logger.info(f"Overall Quality: {overall:.3f} - {'✓ PASS' if overall_compliant else '✗ FAIL'}")
        
        # Grade interpretation
        if overall >= 0.9:
            assessment = "EXCELLENT - Production ready quality"
        elif overall >= 0.8:
            assessment = "GOOD - Acceptable quality with minor issues"
        elif overall >= 0.7:
            assessment = "FAIR - Quality issues that may affect user experience"
        elif overall >= 0.6:
            assessment = "POOR - Significant quality problems"
        else:
            assessment = "CRITICAL - Unacceptable quality, major issues"
        
        logger.info(f"Quality Assessment: {assessment}")

# Utility functions
async def run_translation_quality_test(language_pairs: List[Tuple[str, str]] = None) -> QualityTestResult:
    """Run translation quality test only"""
    config = QualityTestConfig()
    if language_pairs:
        config.language_pairs = language_pairs
    
    suite = QualityTestSuite(config)
    
    # Run only translation tests
    start_time = datetime.utcnow()
    translation_results = []
    
    for source_lang, target_lang in config.language_pairs:
        try:
            results = await suite.translation_evaluator.evaluate_translation_quality(source_lang, target_lang)
            translation_results.extend(results)
        except Exception as e:
            logger.error(f"Translation test failed for {source_lang}→{target_lang}: {e}")
    
    end_time = datetime.utcnow()
    
    return suite._analyze_quality_results(
        "translation_quality_only", start_time, end_time, translation_results, []
    )

async def run_audio_quality_test(languages: List[str] = None) -> QualityTestResult:
    """Run audio quality test only"""
    config = QualityTestConfig()
    if languages:
        config.test_languages = languages
    
    suite = QualityTestSuite(config)
    
    # Run only audio tests
    start_time = datetime.utcnow()
    audio_results = []
    
    test_phrases = [
        "This is a test of the audio synthesis quality.",
        "Natural speech should sound clear and intelligible."
    ]
    
    for language in config.test_languages:
        try:
            results = await suite.audio_evaluator.evaluate_audio_quality(test_phrases, language)
            audio_results.extend(results)
        except Exception as e:
            logger.error(f"Audio test failed for {language}: {e}")
    
    end_time = datetime.utcnow()
    
    return suite._analyze_quality_results(
        "audio_quality_only", start_time, end_time, [], audio_results
    )

if __name__ == "__main__":
    # Example usage
    async def main():
        logger.info("Starting quality assurance tests...")
        
        # Run comprehensive quality tests
        config = QualityTestConfig()
        suite = QualityTestSuite(config)
        
        result = await suite.run_comprehensive_quality_tests()
        
        # Save results
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = f"quality_test_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        
        logger.info(f"Quality test results saved to {output_file}")
    
    asyncio.run(main())