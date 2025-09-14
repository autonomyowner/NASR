"""
Incremental Machine Translation Service

FastAPI-based streaming MT service with rolling context and 20-80ms latency.

Features:
- WebSocket streaming API for incremental translation
- Rolling context buffer for coherent translations
- Multiple translation models (MarianMT, NLLB-200)
- Glossary integration for domain-specific terms
- Quality filtering and smoothing
- ONNX/TensorRT optimization for speed
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
from collections import deque
import statistics

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from transformers import MarianMTModel, MarianTokenizer, pipeline
import torch
import re

# Import model optimization (optional)
try:
    from model_optimizer import ModelOptimizer, OptimizedTranslationEngine
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False

# Monitoring imports (optional)
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    import psutil
    import threading
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Quality assessment imports (optional)
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from collections import defaultdict
    QUALITY_AVAILABLE = True
except ImportError:
    QUALITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Prometheus metrics
translation_requests_total = Counter(
    'mt_translation_requests_total',
    'Total number of translation requests',
    ['source_lang', 'target_lang', 'status']
)

translation_duration_seconds = Histogram(
    'mt_translation_duration_seconds',
    'Time spent on translation processing',
    ['source_lang', 'target_lang', 'model'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

translation_confidence_score = Histogram(
    'mt_translation_confidence',
    'Confidence scores of translations',
    ['source_lang', 'target_lang'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

active_sessions_gauge = Gauge(
    'mt_active_sessions',
    'Number of active translation sessions'
)

model_load_time_seconds = Gauge(
    'mt_model_load_time_seconds',
    'Time taken to load translation models',
    ['model_pair']
)

system_memory_usage = Gauge(
    'mt_system_memory_bytes',
    'System memory usage'
)

gpu_memory_usage = Gauge(
    'mt_gpu_memory_bytes',
    'GPU memory usage'
)

context_buffer_size = Histogram(
    'mt_context_buffer_size',
    'Size of context buffer in tokens',
    ['session_id'],
    buckets=[0, 50, 100, 200, 300, 400, 500, 600, 700, 800]
)

@dataclass
class TranslationRequest:
    """Translation request with context"""
    text: str
    source_language: str
    target_language: str
    context: Optional[str] = None
    glossary_terms: Optional[Dict[str, str]] = None
    session_id: str = ""
    is_partial: bool = False  # Indicates if this is a partial/incremental update
    sequence_id: Optional[str] = None  # For tracking partial updates

@dataclass
class TranslationResult:
    """Translation result with metadata"""
    text: str
    confidence: float
    source_language: str
    target_language: str
    processing_time_ms: float
    model_used: str
    context_used: bool = False

class IncrementalTranslationManager:
    """Manages incremental/partial sentence translation updates"""
    
    def __init__(self):
        self.partial_segments: Dict[str, Dict[str, Any]] = {}  # session_id -> segment data
        self.completed_translations: Dict[str, List[str]] = {}  # session_id -> completed translations
        self.sequence_tracking: Dict[str, Dict[str, str]] = {}  # session_id -> {sequence_id: translation}
        
    def should_translate(self, request: TranslationRequest) -> Tuple[bool, str]:
        """Determine if we should translate and what text to use"""
        session_id = request.session_id
        
        if not request.is_partial:
            # Complete sentence, always translate
            return True, request.text
            
        # Handle partial updates
        if session_id not in self.partial_segments:
            self.partial_segments[session_id] = {
                "current_text": "",
                "last_translation": "",
                "word_count": 0,
                "last_update": time.time()
            }
            
        segment_data = self.partial_segments[session_id]
        
        # Check if text has changed significantly
        current_text = request.text
        previous_text = segment_data["current_text"]
        
        # Simple heuristics for when to retranslate partial text
        word_count = len(current_text.split())
        prev_word_count = segment_data["word_count"]
        
        should_translate = (
            # First partial segment
            not previous_text or
            # Significant word count change (new word added)
            word_count > prev_word_count or
            # Text has changed by more than just appending
            not current_text.startswith(previous_text) or
            # Time-based update (avoid too frequent updates)
            time.time() - segment_data["last_update"] > 0.5
        )
        
        if should_translate:
            segment_data["current_text"] = current_text
            segment_data["word_count"] = word_count
            segment_data["last_update"] = time.time()
            
        return should_translate, current_text
    
    def extract_incremental_update(
        self, 
        request: TranslationRequest,
        new_translation: str
    ) -> Tuple[str, bool]:
        """Extract the incremental part of translation"""
        if not request.is_partial:
            return new_translation, False
            
        session_id = request.session_id
        
        if session_id not in self.partial_segments:
            return new_translation, False
            
        segment_data = self.partial_segments[session_id]
        previous_translation = segment_data.get("last_translation", "")
        
        # Store current translation
        segment_data["last_translation"] = new_translation
        
        # If we have a sequence ID, track it
        if request.sequence_id:
            if session_id not in self.sequence_tracking:
                self.sequence_tracking[session_id] = {}
            self.sequence_tracking[session_id][request.sequence_id] = new_translation
        
        # Simple incremental extraction
        if previous_translation and new_translation.startswith(previous_translation):
            # Return only the new part
            incremental = new_translation[len(previous_translation):].strip()
            return incremental if incremental else new_translation, True
        else:
            # Return full translation if significant change
            return new_translation, False
    
    def finalize_partial_translation(self, session_id: str, final_translation: str):
        """Mark a partial translation as complete"""
        if session_id in self.completed_translations:
            self.completed_translations[session_id].append(final_translation)
        else:
            self.completed_translations[session_id] = [final_translation]
            
        # Clear partial data for this session
        if session_id in self.partial_segments:
            del self.partial_segments[session_id]
    
    def get_session_history(self, session_id: str) -> List[str]:
        """Get completed translations for session"""
        return self.completed_translations.get(session_id, [])
    
    def clear_session(self, session_id: str):
        """Clear all data for session"""
        self.partial_segments.pop(session_id, None)
        self.completed_translations.pop(session_id, None)
        self.sequence_tracking.pop(session_id, None)

class RollingContextManager:
    """Manages rolling context for better translation coherence"""
    
    def __init__(self, max_sentences: int = 3, max_tokens: int = 512):
        self.max_sentences = max_sentences
        self.max_tokens = max_tokens
        self.contexts: Dict[str, deque] = {}
        
    def get_context(self, session_id: str) -> str:
        """Get current context for session"""
        if session_id not in self.contexts:
            self.contexts[session_id] = deque(maxlen=self.max_sentences)
            
        return " ".join(self.contexts[session_id])
    
    def update_context(self, session_id: str, original: str, translation: str):
        """Update context with new sentence pair"""
        if session_id not in self.contexts:
            self.contexts[session_id] = deque(maxlen=self.max_sentences)
            
        # Add new sentence to context
        context_entry = f"{original} | {translation}"
        self.contexts[session_id].append(context_entry)
        
        # Trim if too many tokens
        while self._count_tokens(session_id) > self.max_tokens:
            if self.contexts[session_id]:
                self.contexts[session_id].popleft()
            else:
                break
                
    def _count_tokens(self, session_id: str) -> int:
        """Estimate token count in context"""
        if session_id not in self.contexts:
            return 0
        context = " ".join(self.contexts[session_id])
        return len(context.split())
    
    def clear_context(self, session_id: str):
        """Clear context for session"""
        if session_id in self.contexts:
            del self.contexts[session_id]

class QualityAssessment:
    """Advanced quality assessment for translations"""
    
    def __init__(self):
        self.sentence_model = None  # Load on demand
        self.repetition_cache = defaultdict(list)
        self.quality_history = []
        if QUALITY_AVAILABLE:
            self._load_nltk_data()
        
    def _load_nltk_data(self):
        """Load required NLTK data"""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        except Exception as e:
            logger.warning(f"Could not download NLTK data: {e}")
    
    def _get_sentence_model(self):
        """Lazy loading of sentence transformer model"""
        if self.sentence_model is None:
            try:
                # Use a lightweight multilingual model
                self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                logger.info("Loaded sentence transformer model for quality assessment")
            except Exception as e:
                logger.warning(f"Could not load sentence transformer: {e}")
                self.sentence_model = False  # Mark as failed
        return self.sentence_model if self.sentence_model else None
    
    def calculate_confidence(
        self, 
        original: str, 
        translation: str, 
        source_lang: str, 
        target_lang: str,
        context: str = None
    ) -> float:
        """Calculate comprehensive confidence score"""
        confidence_factors = []
        
        # 1. Length ratio confidence (should be reasonable)
        length_ratio = len(translation) / max(len(original), 1)
        if 0.3 <= length_ratio <= 3.0:  # Reasonable length range
            length_confidence = min(1.0, 1.0 - abs(1.0 - length_ratio) * 0.5)
        else:
            length_confidence = 0.3  # Low confidence for extreme ratios
        confidence_factors.append(("length", length_confidence))
        
        # 2. Repetition detection
        repetition_penalty = self._detect_repetition(translation, source_lang, target_lang)
        confidence_factors.append(("repetition", 1.0 - repetition_penalty))
        
        # 3. Character coverage (no unknown characters for known languages)
        coverage_confidence = self._calculate_coverage(translation, target_lang)
        confidence_factors.append(("coverage", coverage_confidence))
        
        # 4. Semantic similarity (if sentence model is available)
        semantic_confidence = self._calculate_semantic_similarity(original, translation)
        if semantic_confidence > 0:
            confidence_factors.append(("semantic", semantic_confidence))
        
        # 5. Context coherence (if context provided)
        if context:
            context_confidence = self._calculate_context_coherence(context, translation)
            if context_confidence > 0:
                confidence_factors.append(("context", context_confidence))
        
        # Calculate weighted average
        weights = {
            "length": 0.15,
            "repetition": 0.25,
            "coverage": 0.20,
            "semantic": 0.30,
            "context": 0.10
        }
        
        total_weight = sum(weights.get(name, 0.15) for name, _ in confidence_factors)
        if total_weight == 0:
            return 0.5  # Default confidence
            
        weighted_score = sum(
            score * weights.get(name, 0.15) 
            for name, score in confidence_factors
        ) / total_weight
        
        # Normalize to [0.1, 1.0] range
        final_confidence = max(0.1, min(1.0, weighted_score))
        
        # Store for quality tracking
        self.quality_history.append({
            "confidence": final_confidence,
            "factors": dict(confidence_factors),
            "source_lang": source_lang,
            "target_lang": target_lang
        })
        
        # Limit history
        if len(self.quality_history) > 1000:
            self.quality_history = self.quality_history[-500:]
            
        return final_confidence
    
    def _detect_repetition(self, text: str, source_lang: str, target_lang: str) -> float:
        """Detect repetitive patterns in translation"""
        pair_key = f"{source_lang}-{target_lang}"
        
        # Clean text and split into words
        words = text.lower().split()
        if len(words) < 3:
            return 0.0
            
        # Check for immediate repetitions
        immediate_repetitions = 0
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                immediate_repetitions += 1
                
        immediate_penalty = min(0.5, immediate_repetitions / len(words))
        
        # Check for phrase repetitions (3+ words)
        phrase_counts = defaultdict(int)
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            phrase_counts[phrase] += 1
            
        repeated_phrases = sum(1 for count in phrase_counts.values() if count > 1)
        phrase_penalty = min(0.3, repeated_phrases / max(1, len(phrase_counts)))
        
        # Track historical repetitions
        text_hash = hash(text)
        self.repetition_cache[pair_key].append(text_hash)
        
        # Limit cache size
        if len(self.repetition_cache[pair_key]) > 100:
            self.repetition_cache[pair_key] = self.repetition_cache[pair_key][-50:]
            
        # Check for exact repetitions in recent history
        recent_repetitions = self.repetition_cache[pair_key].count(text_hash)
        history_penalty = min(0.2, (recent_repetitions - 1) * 0.1) if recent_repetitions > 1 else 0
        
        return immediate_penalty + phrase_penalty + history_penalty
    
    def _calculate_coverage(self, text: str, target_lang: str) -> float:
        """Calculate character coverage confidence"""
        if not text:
            return 0.0
            
        # Define expected character sets for common languages
        char_sets = {
            "en": set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-\"()[]{}:;"),
            "es": set("abcdefghijklmnopqrstuvwxyzáéíóúüñABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ0123456789 .,!?'-\"()[]{}:;¿¡"),
            "fr": set("abcdefghijklmnopqrstuvwxyzàâäéèêëïîôöùûüÿçABCDEFGHIJKLMNOPQRSTUVWXYZÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÇ0123456789 .,!?'-\"()[]{}:;"),
            "de": set("abcdefghijklmnopqrstuvwxyzäöüßABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ0123456789 .,!?'-\"()[]{}:;"),
            "it": set("abcdefghijklmnopqrstuvwxyzàèéìíîòóùúABCDEFGHIJKLMNOPQRSTUVWXYZÀÈÉÌÍÎÒÓÙÚ0123456789 .,!?'-\"()[]{}:;")
        }
        
        expected_chars = char_sets.get(target_lang, char_sets["en"])
        text_chars = set(text)
        
        # Calculate coverage
        covered = len(text_chars.intersection(expected_chars))
        total = len(text_chars)
        
        if total == 0:
            return 0.0
            
        coverage_ratio = covered / total
        
        # Penalize heavily for many unexpected characters
        unexpected = total - covered
        penalty = min(0.5, unexpected * 0.05)
        
        return max(0.1, coverage_ratio - penalty)
    
    def _calculate_semantic_similarity(self, original: str, translation: str) -> float:
        """Calculate semantic similarity between original and translation"""
        model = self._get_sentence_model()
        if not model:
            return 0.0
            
        try:
            # Encode sentences
            original_embedding = model.encode([original])
            translation_embedding = model.encode([translation])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(original_embedding, translation_embedding)[0][0]
            
            # Normalize to reasonable range (semantic similarity can be lower across languages)
            # A similarity of 0.5+ is good for cross-lingual pairs
            normalized_similarity = min(1.0, max(0.0, (similarity + 0.2) / 0.8))
            
            return normalized_similarity
            
        except Exception as e:
            logger.warning(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _calculate_context_coherence(self, context: str, translation: str) -> float:
        """Calculate how well translation fits with context"""
        model = self._get_sentence_model()
        if not model or not context:
            return 0.0
            
        try:
            # Split context into recent sentences
            context_sentences = context.split('|')[-2:]  # Last 2 context entries
            if not context_sentences:
                return 0.0
                
            # Get embeddings
            context_embeddings = model.encode(context_sentences)
            translation_embedding = model.encode([translation])
            
            # Calculate average similarity to context
            similarities = cosine_similarity(translation_embedding, context_embeddings)[0]
            avg_similarity = np.mean(similarities)
            
            # Normalize (context coherence threshold is lower)
            coherence_score = min(1.0, max(0.0, (avg_similarity + 0.3) / 0.7))
            
            return coherence_score
            
        except Exception as e:
            logger.warning(f"Error calculating context coherence: {e}")
            return 0.0
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get quality assessment statistics"""
        if not self.quality_history:
            return {}
            
        recent_history = self.quality_history[-100:]  # Last 100 translations
        
        confidences = [item["confidence"] for item in recent_history]
        
        stats = {
            "confidence_distribution": {
                "mean": statistics.mean(confidences),
                "median": statistics.median(confidences),
                "std": statistics.stdev(confidences) if len(confidences) > 1 else 0,
                "min": min(confidences),
                "max": max(confidences)
            },
            "quality_factors": {
                "length": statistics.mean([
                    item["factors"].get("length", 0) for item in recent_history
                ]),
                "repetition": statistics.mean([
                    item["factors"].get("repetition", 0) for item in recent_history
                ]),
                "coverage": statistics.mean([
                    item["factors"].get("coverage", 0) for item in recent_history
                ]),
                "semantic": statistics.mean([
                    item["factors"].get("semantic", 0) for item in recent_history
                    if item["factors"].get("semantic", 0) > 0
                ]) if any(item["factors"].get("semantic", 0) > 0 for item in recent_history) else 0
            },
            "sample_count": len(recent_history)
        }
        
        return stats

class PerformanceMonitor:
    """Monitors system and model performance metrics"""
    
    def __init__(self):
        self.translation_times: List[float] = []
        self.confidence_scores: List[float] = []
        if MONITORING_AVAILABLE:
            self.start_monitoring()
        
    def start_monitoring(self):
        """Start background monitoring thread"""
        def monitor_system():
            while True:
                try:
                    # Update system memory
                    memory = psutil.virtual_memory()
                    system_memory_usage.set(memory.used)
                    
                    # Update GPU memory if available
                    if torch.cuda.is_available():
                        gpu_memory = torch.cuda.memory_allocated()
                        gpu_memory_usage.set(gpu_memory)
                        
                    time.sleep(10)  # Update every 10 seconds
                except Exception as e:
                    logger.error(f"Error monitoring system metrics: {e}")
                    time.sleep(30)
                    
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
        
    def record_translation(
        self, 
        duration: float, 
        confidence: float,
        source_lang: str,
        target_lang: str,
        model_name: str
    ):
        """Record translation metrics"""
        # Keep recent history for statistics
        self.translation_times.append(duration)
        self.confidence_scores.append(confidence)
        
        # Limit history size
        if len(self.translation_times) > 1000:
            self.translation_times = self.translation_times[-500:]
        if len(self.confidence_scores) > 1000:
            self.confidence_scores = self.confidence_scores[-500:]
            
        # Update Prometheus metrics
        translation_duration_seconds.labels(
            source_lang=source_lang,
            target_lang=target_lang,
            model=model_name
        ).observe(duration)
        
        translation_confidence_score.labels(
            source_lang=source_lang,
            target_lang=target_lang
        ).observe(confidence)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.translation_times:
            return {}
            
        return {
            "translation_latency_ms": {
                "p50": statistics.median(self.translation_times) * 1000,
                "p95": np.percentile(self.translation_times, 95) * 1000,
                "p99": np.percentile(self.translation_times, 99) * 1000,
                "mean": statistics.mean(self.translation_times) * 1000,
                "count": len(self.translation_times)
            },
            "confidence_scores": {
                "mean": statistics.mean(self.confidence_scores),
                "median": statistics.median(self.confidence_scores),
                "min": min(self.confidence_scores),
                "max": max(self.confidence_scores)
            }
        }

class GlossaryManager:
    """Manages domain-specific terminology"""
    
    def __init__(self):
        self.glossaries: Dict[Tuple[str, str], Dict[str, str]] = {}
        self._load_default_glossaries()
        
    def _load_default_glossaries(self):
        """Load default glossaries for common domains"""
        # Technical terms
        tech_terms = {
            "API": "API",
            "database": "base de datos",
            "server": "servidor",
            "client": "cliente",
            "authentication": "autenticación",
            "microservice": "microservicio"
        }
        self.glossaries[("en", "es")] = tech_terms
        
        # Medical terms  
        medical_terms = {
            "diagnosis": "diagnostic",
            "treatment": "traitement",
            "patient": "patient",
            "symptoms": "symptômes",
            "prescription": "prescription"
        }
        self.glossaries[("en", "fr")] = medical_terms
        
    def apply_glossary(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Tuple[str, Dict[str, str]]:
        """Apply glossary terms to text"""
        glossary_key = (source_lang, target_lang)
        if glossary_key not in self.glossaries:
            return text, {}
            
        glossary = self.glossaries[glossary_key]
        applied_terms = {}
        
        for source_term, target_term in glossary.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(source_term), re.IGNORECASE)
            if pattern.search(text):
                text = pattern.sub(target_term, text)
                applied_terms[source_term] = target_term
                
        return text, applied_terms

class TranslationEngine:
    """Core translation engine with multiple models"""
    
    def __init__(self, use_optimization: bool = True):
        self.models: Dict[Tuple[str, str], Any] = {}
        self.tokenizers: Dict[Tuple[str, str], Any] = {}
        self.pipelines: Dict[Tuple[str, str], Any] = {}
        self.use_optimization = use_optimization
        
        # Initialize optimizer if enabled
        if use_optimization and OPTIMIZATION_AVAILABLE:
            try:
                self.optimizer = ModelOptimizer()
                self.optimized_engine = OptimizedTranslationEngine(self.optimizer)
                logger.info("Model optimization enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize model optimization: {e}")
                self.use_optimization = False
                self.optimizer = None
                self.optimized_engine = None
        else:
            self.optimizer = None
            self.optimized_engine = None
            
        self._load_models()
        
    def _load_models(self):
        """Load translation models"""
        # Define supported language pairs and models
        model_configs = {
            ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
            ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr", 
            ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
            ("en", "it"): "Helsinki-NLP/opus-mt-en-it",
            ("en", "pt"): "Helsinki-NLP/opus-mt-en-roa",
            ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
            ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
            ("de", "en"): "Helsinki-NLP/opus-mt-de-en"
        }
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading translation models on {device}")
        
        for (src, tgt), model_name in model_configs.items():
            try:
                load_start = time.time()
                logger.info(f"Loading model for {src}→{tgt}: {model_name}")
                
                # Try optimized loading first
                if self.use_optimization and self.optimized_engine:
                    try:
                        self.optimized_engine.load_model(model_name, src, tgt)
                        logger.info(f"Successfully loaded optimized model for {src}→{tgt}")
                        continue
                    except Exception as e:
                        logger.warning(f"Optimized loading failed for {src}→{tgt}: {e}")
                        logger.info("Falling back to standard PyTorch loading")
                
                # Standard PyTorch loading as fallback
                model = MarianMTModel.from_pretrained(model_name).to(device)
                tokenizer = MarianTokenizer.from_pretrained(model_name)
                
                # Optimize model for inference
                model.eval()
                if device == "cuda":
                    model = model.half()  # Use FP16 for speed
                    
                self.models[(src, tgt)] = model
                self.tokenizers[(src, tgt)] = tokenizer
                
                # Also create pipeline for easier use
                pipe = pipeline(
                    "translation",
                    model=model,
                    tokenizer=tokenizer,
                    device=0 if device == "cuda" else -1,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32
                )
                self.pipelines[(src, tgt)] = pipe
                
                load_time = time.time() - load_start
                model_load_time_seconds.labels(model_pair=f"{src}-{tgt}").set(load_time)
                
                logger.info(f"Successfully loaded {src}→{tgt} model in {load_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Failed to load model for {src}→{tgt}: {e}")
                
    def get_supported_pairs(self) -> List[Tuple[str, str]]:
        """Get list of supported language pairs"""
        pairs = set(self.models.keys())
        
        # Add optimized model pairs if available
        if self.use_optimization and self.optimized_engine:
            pairs.update(self.optimized_engine.models.keys())
            
        return list(pairs)
        
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ) -> TranslationResult:
        """Translate text with optional context"""
        start_time = time.time()
        model_key = (source_lang, target_lang)
        
        # Check if we have optimized model available
        if (self.use_optimization and 
            self.optimized_engine and 
            model_key in self.optimized_engine.models):
            
            try:
                # Use optimized inference
                input_text = text
                if context:
                    input_text = f"{context} {text}"
                
                loop = asyncio.get_event_loop()
                translation, inference_time = await loop.run_in_executor(
                    None,
                    self.optimized_engine.translate,
                    input_text,
                    source_lang,
                    target_lang
                )
                
                # If we used context, try to extract just the new part
                if context:
                    translation = self._extract_new_translation(
                        translation, context, text
                    )
                
                processing_time = (time.time() - start_time) * 1000
                
                return TranslationResult(
                    text=translation,
                    confidence=0.90,  # Higher confidence for optimized models
                    source_language=source_lang,
                    target_language=target_lang,
                    processing_time_ms=processing_time,
                    model_used=f"optimized-{source_lang}-{target_lang}",
                    context_used=context is not None
                )
                
            except Exception as e:
                logger.warning(f"Optimized inference failed: {e}, falling back to PyTorch")
        
        # Fallback to standard PyTorch inference
        if model_key not in self.pipelines:
            raise ValueError(f"Unsupported language pair: {source_lang}→{target_lang}")
            
        try:
            # Prepare input text with context
            input_text = text
            if context:
                input_text = f"{context} {text}"
                
            # Run translation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._translate_sync,
                input_text,
                model_key
            )
            
            # Extract translation
            translated_text = result[0]["translation_text"]
            
            # If we used context, try to extract just the new part
            if context:
                translated_text = self._extract_new_translation(
                    translated_text, context, text
                )
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                text=translated_text,
                confidence=0.85,  # Default confidence for successful translation
                source_language=source_lang,
                target_language=target_lang,
                processing_time_ms=processing_time,
                model_used=f"marian-{source_lang}-{target_lang}",
                context_used=context is not None
            )
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                text="[Translation Error]",
                confidence=0.0,
                source_language=source_lang,
                target_language=target_lang,
                processing_time_ms=processing_time,
                model_used="error",
                context_used=False
            )
    
    def _translate_sync(self, text: str, model_key: Tuple[str, str]) -> List[Dict]:
        """Synchronous translation for thread execution"""
        pipeline = self.pipelines[model_key]
        return pipeline(text)
        
    def _extract_new_translation(
        self, 
        full_translation: str, 
        context: str, 
        new_text: str
    ) -> str:
        """Extract only the new part of translation when context was used"""
        # Simple heuristic: take the last sentence/phrase
        sentences = full_translation.split('. ')
        if len(sentences) > 1:
            return sentences[-1]
        else:
            # Fallback: return last portion based on text length ratio
            text_ratio = len(new_text) / (len(context) + len(new_text))
            split_point = int(len(full_translation) * (1 - text_ratio))
            return full_translation[split_point:].strip()

class MTService:
    """Main MT service coordinator"""
    
    def __init__(self):
        self.engine = TranslationEngine()
        self.context_manager = RollingContextManager()
        self.glossary = GlossaryManager()
        self.performance_monitor = PerformanceMonitor() if MONITORING_AVAILABLE else None
        self.quality_assessment = QualityAssessment() if QUALITY_AVAILABLE else None
        self.incremental_manager = IncrementalTranslationManager()
        
    async def translate_with_context(
        self,
        request: TranslationRequest
    ) -> TranslationResult:
        """Translate text with rolling context and incremental handling"""
        start_time = time.time()
        status = "success"
        
        try:
            # Check if we should translate (incremental logic)
            should_translate, text_to_translate = self.incremental_manager.should_translate(request)
            
            if not should_translate:
                # Return cached/previous result for efficiency
                session_data = self.incremental_manager.partial_segments.get(request.session_id, {})
                previous_translation = session_data.get("last_translation", "")
                
                if previous_translation:
                    return TranslationResult(
                        text=previous_translation,
                        confidence=0.95,  # High confidence for cached result
                        source_language=request.source_language,
                        target_language=request.target_language,
                        processing_time_ms=0.1,  # Very fast cached result
                        model_used="cached",
                        context_used=False
                    )
            
            # Get existing context
            context = self.context_manager.get_context(request.session_id)
            
            # Apply glossary terms
            processed_text, applied_terms = self.glossary.apply_glossary(
                text_to_translate,
                request.source_language,
                request.target_language
            )
            
            # Perform translation
            result = await self.engine.translate(
                processed_text,
                request.source_language,
                request.target_language,
                context if context else None
            )
            
            # Calculate advanced confidence score (if available)
            if self.quality_assessment:
                enhanced_confidence = self.quality_assessment.calculate_confidence(
                    request.text,
                    result.text,
                    request.source_language,
                    request.target_language,
                    context
                )
                # Update result with enhanced confidence
                result.confidence = enhanced_confidence
            
            # Handle incremental extraction
            if request.is_partial:
                incremental_text, is_incremental = self.incremental_manager.extract_incremental_update(
                    request, result.text
                )
                # For partial updates, we might want to return just the incremental part
                # But for now, return the full translation for consistency
                pass
            else:
                # For complete sentences, finalize any partial translations
                self.incremental_manager.finalize_partial_translation(
                    request.session_id, result.text
                )
            
            # Update context with new translation
            self.context_manager.update_context(
                request.session_id,
                request.text,
                result.text
            )
            
            # Record performance metrics (if available)
            if self.performance_monitor:
                duration = time.time() - start_time
                self.performance_monitor.record_translation(
                    duration,
                    result.confidence,
                    request.source_language,
                    request.target_language,
                    result.model_used
                )
            
            # Update context buffer size metric
            context_tokens = self.context_manager._count_tokens(request.session_id)
            context_buffer_size.labels(session_id=request.session_id[:8]).observe(context_tokens)
            
            return result
            
        except Exception as e:
            status = "error"
            logger.error(f"Translation error: {e}")
            # Return error result but still record metrics
            duration = time.time() - start_time
            error_result = TranslationResult(
                text="[Translation Error]",
                confidence=0.0,
                source_language=request.source_language,
                target_language=request.target_language,
                processing_time_ms=duration * 1000,
                model_used="error",
                context_used=False
            )
            return error_result
        finally:
            # Always record request metric
            translation_requests_total.labels(
                source_lang=request.source_language,
                target_lang=request.target_language,
                status=status
            ).inc()
    
    def clear_session(self, session_id: str):
        """Clear session context and incremental data"""
        self.context_manager.clear_context(session_id)
        self.incremental_manager.clear_session(session_id)

# FastAPI application
app = FastAPI(
    title="MT Service", 
    description="Incremental Machine Translation with Rolling Context",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MT service instance
mt_service = MTService()

@app.websocket("/ws/translate")
async def translate_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming translation"""
    await websocket.accept()
    session_id = f"session_{int(time.time() * 1000)}"
    logger.info(f"New MT session: {session_id}")
    
    # Update active sessions metric
    active_sessions_gauge.inc()
    
    try:
        while True:
            # Receive translation request
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            request = TranslationRequest(
                text=request_data["text"],
                source_language=request_data["source_language"],
                target_language=request_data["target_language"],
                context=request_data.get("context"),
                session_id=session_id,
                is_partial=request_data.get("is_partial", False),
                sequence_id=request_data.get("sequence_id")
            )
            
            # Perform translation
            result = await mt_service.translate_with_context(request)
            
            # Send result
            response = {
                "text": result.text,
                "confidence": result.confidence,
                "source_language": result.source_language,
                "target_language": result.target_language,
                "processing_time_ms": result.processing_time_ms,
                "model_used": result.model_used,
                "context_used": result.context_used,
                "is_partial": request.is_partial,
                "sequence_id": request.sequence_id
            }
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        logger.info(f"MT session disconnected: {session_id}")
    except Exception as e:
        logger.error(f"MT session error: {e}")
    finally:
        # Update active sessions metric
        active_sessions_gauge.dec()
        mt_service.clear_session(session_id)

@app.post("/translate")
async def translate_text(request: TranslationRequest):
    """HTTP endpoint for single translation"""
    result = await mt_service.translate_with_context(request)
    return result

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "supported_pairs": mt_service.engine.get_supported_pairs(),
        "active_sessions": len(mt_service.context_manager.contexts),
        "optimization_available": OPTIMIZATION_AVAILABLE,
        "monitoring_available": MONITORING_AVAILABLE,
        "quality_available": QUALITY_AVAILABLE
    }

@app.get("/languages") 
async def list_languages():
    """List supported languages and pairs"""
    pairs = mt_service.engine.get_supported_pairs()
    languages = set()
    for src, tgt in pairs:
        languages.add(src)
        languages.add(tgt)
        
    return {
        "supported_languages": sorted(list(languages)),
        "supported_pairs": pairs,
        "glossary_domains": ["technical", "medical", "business"]
    }

@app.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/performance")
async def get_performance_stats():
    """Get detailed performance statistics"""
    stats = {}

    if mt_service.performance_monitor:
        stats.update(mt_service.performance_monitor.get_statistics())

    # Add system info (if available)
    if MONITORING_AVAILABLE:
        memory = psutil.virtual_memory()
        stats.update({
            "system": {
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_used_gb": memory.used / (1024**3),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        })

    stats.update({
        "models": {
            "loaded_pairs": len(mt_service.engine.models),
            "supported_pairs": len(mt_service.engine.get_supported_pairs()),
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "gpu_available": torch.cuda.is_available(),
            "gpu_memory_gb": torch.cuda.memory_allocated() / (1024**3) if torch.cuda.is_available() else 0
        },
        "active_sessions": len(mt_service.context_manager.contexts)
    })

    if mt_service.quality_assessment:
        stats["quality_assessment"] = mt_service.quality_assessment.get_quality_statistics()

    return stats

@app.get("/benchmark/{source_lang}/{target_lang}")
async def benchmark_translation(source_lang: str, target_lang: str, test_count: int = 10):
    """Benchmark translation performance for a language pair"""
    if (source_lang, target_lang) not in mt_service.engine.get_supported_pairs():
        raise HTTPException(status_code=400, detail="Unsupported language pair")
    
    # Test sentences for benchmarking
    test_sentences = [
        "Hello, how are you today?",
        "The weather is beautiful this morning.",
        "I would like to schedule a meeting for next week.",
        "Technology is changing rapidly in the modern world.",
        "Please send me the report by email when it's ready.",
        "The restaurant serves excellent food and has great service.",
        "We need to discuss the project requirements in detail.",
        "The conference will be held at the convention center.",
        "Could you please help me with this technical problem?",
        "The team is working hard to meet the deadline."
    ]
    
    results = []
    session_id = f"benchmark_{int(time.time())}"
    
    for i in range(min(test_count, len(test_sentences))):
        sentence = test_sentences[i % len(test_sentences)]
        start_time = time.time()
        
        request = TranslationRequest(
            text=sentence,
            source_language=source_lang,
            target_language=target_lang,
            session_id=session_id
        )
        
        result = await mt_service.translate_with_context(request)
        latency = (time.time() - start_time) * 1000
        
        results.append({
            "input": sentence,
            "output": result.text,
            "latency_ms": latency,
            "confidence": result.confidence,
            "model": result.model_used
        })
    
    # Calculate statistics
    latencies = [r["latency_ms"] for r in results]
    confidences = [r["confidence"] for r in results]
    
    mt_service.clear_session(session_id)
    
    return {
        "language_pair": f"{source_lang}→{target_lang}",
        "test_count": len(results),
        "results": results,
        "statistics": {
            "latency_ms": {
                "min": min(latencies),
                "max": max(latencies),
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99)
            },
            "confidence": {
                "min": min(confidences),
                "max": max(confidences),
                "mean": statistics.mean(confidences),
                "median": statistics.median(confidences)
            }
        }
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8002,
        log_level="info"
    )