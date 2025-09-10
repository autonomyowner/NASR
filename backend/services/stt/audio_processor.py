"""
Audio Processing Pipeline
VAD, chunking, and audio preprocessing for streaming STT
"""

import time
import io
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass
import numpy as np
import torch
import torchaudio
from collections import deque

logger = logging.getLogger(__name__)

try:
    import silero_vad
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False
    logger.warning("silero-vad not available, using simple energy-based VAD")

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    logger.warning("webrtcvad not available")


@dataclass
class AudioChunk:
    """Audio chunk with speech detection metadata"""
    audio_data: np.ndarray
    sample_rate: int
    timestamp: float
    chunk_id: str
    has_speech: bool
    speech_confidence: float
    duration_ms: float
    
    def to_bytes(self) -> bytes:
        """Convert to bytes for transmission"""
        return (self.audio_data * 32767).astype(np.int16).tobytes()
    
    @classmethod
    def from_bytes(cls, data: bytes, sample_rate: int = 16000, chunk_id: str = None) -> 'AudioChunk':
        """Create from raw bytes"""
        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
        
        return cls(
            audio_data=audio_array,
            sample_rate=sample_rate,
            timestamp=time.time(),
            chunk_id=chunk_id or f"chunk_{int(time.time() * 1000)}",
            has_speech=True,  # Will be determined by VAD
            speech_confidence=0.0,
            duration_ms=len(audio_array) / sample_rate * 1000
        )


class VADProcessor:
    """Voice Activity Detection processor"""
    
    def __init__(
        self,
        method: str = "silero",  # "silero", "webrtc", "energy"
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100
    ):
        self.method = method
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration_ms / 1000.0
        self.min_silence_duration = min_silence_duration_ms / 1000.0
        
        # Initialize VAD model
        self.vad_model = None
        self.webrtc_vad = None
        
        if method == "silero" and SILERO_AVAILABLE:
            self._init_silero()
        elif method == "webrtc" and WEBRTCVAD_AVAILABLE:
            self._init_webrtc()
        else:
            logger.warning(f"VAD method '{method}' not available, falling back to energy-based")
            self.method = "energy"
    
    def _init_silero(self):
        """Initialize Silero VAD"""
        try:
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self.vad_model = model
            self.get_speech_timestamps, self.save_audio, self.read_audio, self.VADIterator, self.collect_chunks = utils
            logger.info("Silero VAD initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Silero VAD: {e}")
            self.method = "energy"
    
    def _init_webrtc(self):
        """Initialize WebRTC VAD"""
        try:
            # Aggressiveness: 0-3 (higher = more aggressive)
            self.webrtc_vad = webrtcvad.Vad(2)  
            logger.info("WebRTC VAD initialized")
        except Exception as e:
            logger.error(f"Failed to initialize WebRTC VAD: {e}")
            self.method = "energy"
    
    def detect_speech(self, audio: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """
        Detect speech in audio chunk.
        
        Returns:
            (has_speech, confidence_score)
        """
        if len(audio) == 0:
            return False, 0.0
            
        if self.method == "silero":
            return self._detect_silero(audio, sample_rate)
        elif self.method == "webrtc":
            return self._detect_webrtc(audio, sample_rate)
        else:
            return self._detect_energy(audio, sample_rate)
    
    def _detect_silero(self, audio: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """Silero VAD detection"""
        try:
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                audio_tensor = torch.from_numpy(audio).unsqueeze(0)
                audio = resampler(audio_tensor).squeeze().numpy()
                sample_rate = 16000
            
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio)
            
            # Get speech probability
            speech_prob = self.vad_model(audio_tensor, 16000).item()
            has_speech = speech_prob > self.threshold
            
            return has_speech, speech_prob
            
        except Exception as e:
            logger.error(f"Silero VAD error: {e}")
            return self._detect_energy(audio, sample_rate)
    
    def _detect_webrtc(self, audio: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """WebRTC VAD detection"""
        try:
            # Resample to supported rate if needed (8k, 16k, 32k, 48k)
            supported_rates = [8000, 16000, 32000, 48000]
            target_rate = min(supported_rates, key=lambda x: abs(x - sample_rate))
            
            if sample_rate != target_rate:
                resampler = torchaudio.transforms.Resample(sample_rate, target_rate)
                audio_tensor = torch.from_numpy(audio).unsqueeze(0)
                audio = resampler(audio_tensor).squeeze().numpy()
                sample_rate = target_rate
            
            # Convert to 16-bit PCM
            pcm_data = (audio * 32767).astype(np.int16).tobytes()
            
            # WebRTC VAD requires specific frame sizes
            frame_duration = 30  # 30ms frames
            frame_size = int(sample_rate * frame_duration / 1000)
            
            # Process frames
            speech_frames = 0
            total_frames = 0
            
            for i in range(0, len(pcm_data), frame_size * 2):  # *2 for 16-bit
                frame = pcm_data[i:i + frame_size * 2]
                if len(frame) == frame_size * 2:
                    total_frames += 1
                    if self.webrtc_vad.is_speech(frame, sample_rate):
                        speech_frames += 1
            
            if total_frames == 0:
                return False, 0.0
                
            speech_ratio = speech_frames / total_frames
            has_speech = speech_ratio > self.threshold
            
            return has_speech, speech_ratio
            
        except Exception as e:
            logger.error(f"WebRTC VAD error: {e}")
            return self._detect_energy(audio, sample_rate)
    
    def _detect_energy(self, audio: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """Simple energy-based VAD"""
        try:
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio ** 2))
            
            # Normalize to 0-1 range (rough approximation)
            normalized_energy = min(1.0, energy * 10)
            
            has_speech = normalized_energy > self.threshold
            
            return has_speech, normalized_energy
            
        except Exception as e:
            logger.error(f"Energy VAD error: {e}")
            return False, 0.0


class AudioChunker:
    """Handles audio chunking with overlap for streaming processing"""
    
    def __init__(
        self,
        chunk_duration_ms: int = 250,
        overlap_ms: int = 50,
        sample_rate: int = 16000,
        max_silence_chunks: int = 20
    ):
        self.chunk_duration = chunk_duration_ms / 1000.0
        self.overlap_duration = overlap_ms / 1000.0
        self.sample_rate = sample_rate
        self.max_silence_chunks = max_silence_chunks
        
        # Buffer for accumulating audio
        self.buffer = deque()
        self.buffer_size = 0
        self.chunk_counter = 0
        self.silence_counter = 0
        
        # Calculate sizes in samples
        self.chunk_samples = int(self.chunk_duration * sample_rate)
        self.overlap_samples = int(self.overlap_duration * sample_rate)
        self.step_samples = self.chunk_samples - self.overlap_samples
        
        logger.info(f"AudioChunker: {chunk_duration_ms}ms chunks, {overlap_ms}ms overlap")
    
    def add_audio(self, audio_data: np.ndarray) -> List[AudioChunk]:
        """Add audio data and return any complete chunks"""
        self.buffer.extend(audio_data)
        self.buffer_size += len(audio_data)
        
        chunks = []
        
        # Extract chunks while we have enough data
        while self.buffer_size >= self.chunk_samples:
            # Extract chunk
            chunk_data = np.array(list(self.buffer)[:self.chunk_samples])
            
            # Create chunk
            chunk = AudioChunk(
                audio_data=chunk_data,
                sample_rate=self.sample_rate,
                timestamp=time.time(),
                chunk_id=f"chunk_{self.chunk_counter}",
                has_speech=False,  # Will be determined by VAD
                speech_confidence=0.0,
                duration_ms=len(chunk_data) / self.sample_rate * 1000
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
            # Remove processed samples (maintaining overlap)
            for _ in range(self.step_samples):
                if self.buffer:
                    self.buffer.popleft()
                    self.buffer_size -= 1
        
        return chunks
    
    def flush_remaining(self) -> List[AudioChunk]:
        """Flush any remaining audio as final chunks"""
        chunks = []
        
        if self.buffer_size > 0:
            # Create final chunk with remaining data
            remaining_data = np.array(list(self.buffer))
            
            chunk = AudioChunk(
                audio_data=remaining_data,
                sample_rate=self.sample_rate,
                timestamp=time.time(),
                chunk_id=f"final_chunk_{self.chunk_counter}",
                has_speech=False,
                speech_confidence=0.0,
                duration_ms=len(remaining_data) / self.sample_rate * 1000
            )
            
            chunks.append(chunk)
            self.buffer.clear()
            self.buffer_size = 0
        
        return chunks
    
    def reset(self):
        """Reset chunker state"""
        self.buffer.clear()
        self.buffer_size = 0
        self.chunk_counter = 0
        self.silence_counter = 0


class AudioProcessor:
    """Complete audio processing pipeline"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration_ms: int = 250,
        overlap_ms: int = 50,
        vad_method: str = "silero",
        vad_threshold: float = 0.5,
        normalize_audio: bool = True
    ):
        self.sample_rate = sample_rate
        self.normalize_audio = normalize_audio
        
        # Initialize components
        self.vad = VADProcessor(
            method=vad_method,
            threshold=vad_threshold,
            min_speech_duration_ms=100,
            min_silence_duration_ms=200
        )
        
        self.chunker = AudioChunker(
            chunk_duration_ms=chunk_duration_ms,
            overlap_ms=overlap_ms,
            sample_rate=sample_rate
        )
        
        logger.info(f"AudioProcessor initialized: {sample_rate}Hz, {chunk_duration_ms}ms chunks")
    
    def add_audio_data(self, audio_bytes: bytes) -> List[AudioChunk]:
        """
        Process raw audio bytes and return speech chunks.
        
        Args:
            audio_bytes: Raw 16-bit PCM audio data
            
        Returns:
            List of processed audio chunks with speech detection
        """
        try:
            # Convert bytes to float array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
            
            # Normalize if requested
            if self.normalize_audio and len(audio_array) > 0:
                audio_array = self._normalize_audio(audio_array)
            
            # Create chunks
            raw_chunks = self.chunker.add_audio(audio_array)
            
            # Apply VAD to each chunk
            processed_chunks = []
            for chunk in raw_chunks:
                has_speech, confidence = self.vad.detect_speech(chunk.audio_data, chunk.sample_rate)
                
                # Update chunk with VAD results
                chunk.has_speech = has_speech
                chunk.speech_confidence = confidence
                
                processed_chunks.append(chunk)
            
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            return []
    
    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio to prevent clipping and improve SNR"""
        if len(audio) == 0:
            return audio
            
        # RMS normalization
        rms = np.sqrt(np.mean(audio ** 2))
        if rms > 0:
            # Target RMS of 0.1 (prevents over-normalization)
            target_rms = 0.1
            audio = audio * (target_rms / rms)
            
        # Clip to prevent overflow
        audio = np.clip(audio, -1.0, 1.0)
        
        return audio
    
    def finalize_session(self) -> List[AudioChunk]:
        """Flush any remaining audio and apply VAD"""
        final_chunks = self.chunker.flush_remaining()
        
        processed_chunks = []
        for chunk in final_chunks:
            has_speech, confidence = self.vad.detect_speech(chunk.audio_data, chunk.sample_rate)
            chunk.has_speech = has_speech
            chunk.speech_confidence = confidence
            processed_chunks.append(chunk)
        
        return processed_chunks
    
    def reset(self):
        """Reset processor state"""
        self.chunker.reset()
        logger.info("AudioProcessor state reset")
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        return {
            "sample_rate": self.sample_rate,
            "vad_method": self.vad.method,
            "chunk_duration_ms": self.chunker.chunk_duration * 1000,
            "overlap_ms": self.chunker.overlap_duration * 1000,
            "processed_chunks": self.chunker.chunk_counter,
            "buffer_size": self.chunker.buffer_size
        }