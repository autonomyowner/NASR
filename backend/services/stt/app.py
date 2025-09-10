"""
STT Service with LocalAgreement-2 Stabilization
Real-time streaming Speech-to-Text service with word stability filtering
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Tuple, AsyncGenerator

import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
import numpy as np
from faster_whisper import WhisperModel

from .local_agreement import LocalAgreement2
from .audio_processor import AudioProcessor, AudioChunk
from .performance_monitor import PerformanceMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
whisper_model: Optional[WhisperModel] = None
performance_monitor = PerformanceMonitor()


class STTConfig:
    """STT Service Configuration"""
    MODEL_SIZE = "base.en"  # tiny.en, base.en, small.en
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    COMPUTE_TYPE = "float16" if torch.cuda.is_available() else "int8"
    
    # Audio processing
    SAMPLE_RATE = 16000
    CHUNK_DURATION_MS = 250  # 250ms chunks for optimal latency
    OVERLAP_MS = 50  # 50ms overlap
    VAD_AGGRESSIVENESS = 2  # 0-3, higher = more aggressive
    
    # LocalAgreement-2 parameters
    AGREEMENT_THRESHOLD = 2  # Minimum agreement count
    STABILITY_WINDOW = 3     # Window for stability analysis
    CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence for word acceptance


class TranscriptionSegment(BaseModel):
    """Single transcription segment"""
    id: str
    text: str
    start: float
    end: float
    confidence: float
    is_confirmed: bool = False


class STTResponse(BaseModel):
    """STT WebSocket response"""
    type: str  # "partial", "confirmed", "final"
    segments: List[TranscriptionSegment]
    processing_time_ms: float
    session_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global whisper_model
    
    logger.info(f"Loading Whisper model: {STTConfig.MODEL_SIZE} on {STTConfig.DEVICE}")
    
    try:
        whisper_model = WhisperModel(
            STTConfig.MODEL_SIZE,
            device=STTConfig.DEVICE,
            compute_type=STTConfig.COMPUTE_TYPE,
            num_workers=1,
            local_files_only=False
        )
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down STT service")


class STTSession:
    """Manages a single STT session with LocalAgreement-2"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.agreement_filter = LocalAgreement2(
            agreement_threshold=STTConfig.AGREEMENT_THRESHOLD,
            stability_window=STTConfig.STABILITY_WINDOW,
            confidence_threshold=STTConfig.CONFIDENCE_THRESHOLD
        )
        self.audio_processor = AudioProcessor(
            sample_rate=STTConfig.SAMPLE_RATE,
            chunk_duration_ms=STTConfig.CHUNK_DURATION_MS,
            overlap_ms=STTConfig.OVERLAP_MS,
            vad_threshold=0.5
        )
        self.segment_counter = 0
        self.active = True
        
        # Register with performance monitor
        performance_monitor.record_session_start(session_id)
        
    async def process_audio_chunk(self, audio_data: bytes) -> Optional[STTResponse]:
        """Process incoming audio chunk"""
        if not self.active or not whisper_model:
            return None
            
        start_time = time.time()
        
        try:
            # Process audio chunks
            chunks = self.audio_processor.add_audio_data(audio_data)
            if not chunks:
                return None
            
            # Process speech chunks only
            speech_chunks = [chunk for chunk in chunks if chunk.has_speech]
            if not speech_chunks:
                return None
            
            all_segments = []
            
            for chunk in speech_chunks:
                # Transcribe with Whisper
                segments, info = whisper_model.transcribe(
                    chunk.audio_data,
                    language="en",
                    word_timestamps=True,
                    condition_on_previous_text=False
                )
                
                # Extract words and confidences
                words = []
                confidences = []
                timestamps = []
                
                for segment in segments:
                    if hasattr(segment, 'words') and segment.words:
                        for word in segment.words:
                            words.append(word.word.strip())
                            confidences.append(getattr(word, 'probability', 0.8))
                            timestamps.append((word.start, word.end))
                    else:
                        # Fallback to segment-level
                        segment_words = segment.text.strip().split()
                        words.extend(segment_words)
                        confidences.extend([0.8] * len(segment_words))
                        # Estimate word timestamps
                        word_duration = (segment.end - segment.start) / len(segment_words) if segment_words else 0
                        for i, word in enumerate(segment_words):
                            word_start = segment.start + i * word_duration
                            word_end = word_start + word_duration
                            timestamps.append((word_start, word_end))
                
                if not words:
                    continue
                
                # Apply LocalAgreement-2 filtering
                interim_words, confirmed_words, has_new_confirmations = self.agreement_filter.process_transcription(
                    words, confidences, timestamps
                )
                
                # Create segments for confirmed words
                for i, word in enumerate(confirmed_words):
                    self.segment_counter += 1
                    seg = TranscriptionSegment(
                        id=f"{self.session_id}_{self.segment_counter}",
                        text=word,
                        start=timestamps[i][0] if i < len(timestamps) else time.time(),
                        end=timestamps[i][1] if i < len(timestamps) else time.time(),
                        confidence=confidences[i] if i < len(confidences) else 0.8,
                        is_confirmed=True
                    )
                    all_segments.append(seg)
                
                # Record performance metrics
                performance_monitor.record_word_confirmation(
                    len(words), len(confirmed_words), 0
                )
            
            processing_time = (time.time() - start_time) * 1000
            performance_monitor.record_processing_time(
                processing_time, 
                STTConfig.CHUNK_DURATION_MS,
                self.session_id,
                confidence=np.mean(confidences) if confidences else 0.0,
                has_speech=len(speech_chunks) > 0
            )
            
            if all_segments:
                response_type = "confirmed" if any(seg.is_confirmed for seg in all_segments) else "partial"
                
                return STTResponse(
                    type=response_type,
                    segments=all_segments,
                    processing_time_ms=processing_time,
                    session_id=self.session_id
                )
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            performance_monitor.record_error("processing", self.session_id)
            return None
        
        return None
    
    def finalize_session(self) -> Optional[STTResponse]:
        """Finalize session and return any remaining segments"""
        self.active = False
        
        # Get final words from LocalAgreement-2
        final_words = self.agreement_filter.finalize_session()
        
        if final_words:
            final_segments = []
            for word in final_words:
                self.segment_counter += 1
                seg = TranscriptionSegment(
                    id=f"{self.session_id}_{self.segment_counter}",
                    text=word.word,
                    start=word.start_time,
                    end=word.end_time,
                    confidence=word.confidence,
                    is_confirmed=True
                )
                final_segments.append(seg)
                
            return STTResponse(
                type="final",
                segments=final_segments,
                processing_time_ms=0.0,
                session_id=self.session_id
            )
        
        # Cleanup performance monitoring
        performance_monitor.record_session_end(self.session_id)
        
        return None


# Active sessions
active_sessions: Dict[str, STTSession] = {}

app = FastAPI(
    title="STT Service",
    description="Streaming Speech-to-Text with LocalAgreement-2 stabilization",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    model_loaded = whisper_model is not None
    gpu_available = torch.cuda.is_available()
    
    return {
        "status": "healthy" if model_loaded else "degraded",
        "model_loaded": model_loaded,
        "model_size": STTConfig.MODEL_SIZE,
        "device": STTConfig.DEVICE,
        "gpu_available": gpu_available,
        "active_sessions": len(active_sessions),
        "performance": performance_monitor.get_stats()
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint"""
    return performance_monitor.get_prometheus_metrics()


@app.get("/models")
async def list_models():
    """List available models"""
    return {
        "available_models": ["tiny.en", "base.en", "small.en", "medium.en", "large"],
        "current_model": STTConfig.MODEL_SIZE,
        "supported_languages": ["en"],
        "config": {
            "chunk_duration_ms": STTConfig.CHUNK_DURATION_MS,
            "overlap_ms": STTConfig.OVERLAP_MS,
            "agreement_threshold": STTConfig.AGREEMENT_THRESHOLD,
            "stability_window": STTConfig.STABILITY_WINDOW
        }
    }


@app.websocket("/ws/stt")
async def stt_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming STT"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())
    session = STTSession(session_id)
    active_sessions[session_id] = session
    
    logger.info(f"STT session started: {session_id}")
    
    try:
        while True:
            # Receive audio data
            data = await websocket.receive_bytes()
            
            # Process audio chunk
            response = await session.process_audio_chunk(data)
            
            # Send response if available
            if response:
                await websocket.send_text(response.json())
                
    except WebSocketDisconnect:
        logger.info(f"STT session disconnected: {session_id}")
    except Exception as e:
        logger.error(f"STT session error: {e}")
    finally:
        # Cleanup session
        if session_id in active_sessions:
            final_response = active_sessions[session_id].finalize_session()
            if final_response:
                try:
                    await websocket.send_text(final_response.json())
                except:
                    pass
            del active_sessions[session_id]
        
        logger.info(f"STT session cleaned up: {session_id}")


@app.post("/transcribe")
async def transcribe_audio(audio_file: bytes):
    """Batch transcription endpoint for testing"""
    if not whisper_model:
        raise HTTPException(status_code=503, detail="STT model not loaded")
    
    start_time = time.time()
    
    try:
        # Create temporary session for batch processing
        session = STTSession("batch_" + str(uuid.uuid4())[:8])
        
        # Process audio
        response = await session.process_audio_chunk(audio_file)
        
        # Finalize to get all segments
        final_response = session.finalize_session()
        
        if final_response:
            return final_response
        elif response:
            return response
        else:
            return STTResponse(
                type="empty",
                segments=[],
                processing_time_ms=(time.time() - start_time) * 1000,
                session_id=session.session_id
            )
            
    except Exception as e:
        logger.error(f"Batch transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.get("/performance")
async def get_performance():
    """Get detailed performance metrics"""
    return performance_monitor.get_current_metrics()


@app.get("/session/{session_id}/metrics")
async def get_session_metrics(session_id: str):
    """Get metrics for specific session"""
    metrics = performance_monitor.get_session_metrics(session_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return metrics


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )