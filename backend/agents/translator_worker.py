"""
LiveKit Translator Worker - Real-time Audio Translation Agent

This worker subscribes to audio tracks in a LiveKit room, processes them through
STT→MT→TTS pipeline, and publishes translated audio tracks back to the room.

Key Features:
- Real-time audio processing with 150-300ms chunks
- Streaming STT with LocalAgreement-2 stabilization  
- Incremental MT with rolling context
- Streaming TTS with early frame publishing
- Per-language audio track publishing
- Real-time caption data channels
- Comprehensive telemetry and monitoring
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import numpy as np

from livekit import api, rtc
from livekit.agents import JobContext, WorkerOptions, cli

# Service clients
from services.stt_client import STTClient
from services.mt_client import MTClient  
from services.tts_client import TTSClient
from observability.tracer import TranslationTracer

logger = logging.getLogger(__name__)

@dataclass
class TranslationConfig:
    """Configuration for translation pipeline"""
    stt_model: str = "base"  # whisper model size
    chunk_duration_ms: int = 250  # audio chunk size
    context_length: int = 512  # MT context buffer
    target_languages: List[str] = None
    voice_presets: Dict[str, str] = None
    
    def __post_init__(self):
        if self.target_languages is None:
            self.target_languages = ["es", "fr", "de", "it", "pt"]
        if self.voice_presets is None:
            self.voice_presets = {
                "es": "es-female-1",
                "fr": "fr-male-1", 
                "de": "de-female-1",
                "it": "it-male-1",
                "pt": "pt-female-1"
            }

@dataclass  
class AudioChunk:
    """Audio chunk with metadata for processing"""
    audio_data: np.ndarray
    timestamp: float
    speaker_id: str
    chunk_id: str
    sample_rate: int = 16000

@dataclass
class TranslationResult:
    """Complete translation result with timing"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    audio_data: Optional[np.ndarray]
    confidence: float
    latency_ms: float
    chunk_id: str

class TranslatorWorker:
    """Main translator worker that handles the full pipeline"""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.room: Optional[rtc.Room] = None
        self.participants: Dict[str, rtc.RemoteParticipant] = {}
        self.audio_buffers: Dict[str, List[AudioChunk]] = {}
        
        # Service clients  
        self.stt_client = STTClient()
        self.mt_client = MTClient()
        self.tts_client = TTSClient()
        
        # Connection status
        self.services_connected = False
        
        # Telemetry
        self.tracer = TranslationTracer()
        
        # Processing state
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.context_buffers: Dict[str, List[str]] = {}
        self.published_tracks: Dict[str, rtc.LocalAudioTrack] = {}  # Track per language
        
    async def connect_services(self):
        """Connect to all backend services"""
        try:
            await asyncio.gather(
                self.stt_client.connect(),
                self.mt_client.connect(),
                self.tts_client.connect()
            )
            self.services_connected = True
            logger.info("Connected to all backend services")
        except Exception as e:
            logger.error(f"Failed to connect to services: {e}")
            self.services_connected = False
            raise
    
    async def connect_to_room(self, url: str, token: str, room_name: str):
        """Connect to LiveKit room and set up event handlers"""
        # Connect to backend services first
        if not self.services_connected:
            await self.connect_services()
            
        self.room = rtc.Room()
        
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant connected: {participant.identity}")
            self.participants[participant.identity] = participant
            
            # Subscribe to audio tracks
            participant.on("track_subscribed", self.on_track_subscribed)
            
        @self.room.on("participant_disconnected") 
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant disconnected: {participant.identity}")
            if participant.identity in self.participants:
                del self.participants[participant.identity]
            if participant.identity in self.processing_tasks:
                self.processing_tasks[participant.identity].cancel()
                del self.processing_tasks[participant.identity]
                
        await self.room.connect(url, token)
        logger.info(f"Connected to room: {room_name}")
        
    def on_track_subscribed(
        self,
        track: rtc.Track,
        publication: rtc.TrackPublication, 
        participant: rtc.RemoteParticipant
    ):
        """Handle new audio track subscription"""
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Subscribed to audio track from {participant.identity}")
            
            # Start processing task for this participant
            task = asyncio.create_task(
                self.process_participant_audio(participant, track)
            )
            self.processing_tasks[participant.identity] = task
            
    async def process_participant_audio(self, participant: rtc.RemoteParticipant, track: rtc.AudioTrack):
        """Main audio processing pipeline for a participant"""
        participant_id = participant.identity
        self.audio_buffers[participant_id] = []
        self.context_buffers[participant_id] = []
        
        # Create audio stream
        audio_stream = rtc.AudioStream(track)
        
        async for audio_frame_event in audio_stream:
            try:
                # Extract audio data
                frame = audio_frame_event.frame
                audio_data = np.frombuffer(frame.data, dtype=np.int16)
                
                # Create audio chunk
                chunk = AudioChunk(
                    audio_data=audio_data,
                    timestamp=time.time(),
                    speaker_id=participant_id,
                    chunk_id=f"{participant_id}_{int(time.time() * 1000)}",
                    sample_rate=frame.sample_rate
                )
                
                # Buffer audio chunks
                self.audio_buffers[participant_id].append(chunk)
                
                # Process when we have enough audio
                if self.should_process_buffer(participant_id):
                    await self.process_audio_buffer(participant_id)
                    
            except Exception as e:
                logger.error(f"Error processing audio from {participant_id}: {e}")
                
    def should_process_buffer(self, participant_id: str) -> bool:
        """Check if audio buffer is ready for processing"""
        buffer = self.audio_buffers[participant_id]
        if not buffer:
            return False
            
        # Check if we have enough audio duration
        total_duration = sum(len(chunk.audio_data) / chunk.sample_rate for chunk in buffer)
        return total_duration >= self.config.chunk_duration_ms / 1000
        
    async def process_audio_buffer(self, participant_id: str):
        """Process accumulated audio buffer through translation pipeline"""
        start_time = time.time()
        trace_id = f"translation_{participant_id}_{int(start_time * 1000)}"
        
        try:
            # Get and clear buffer
            buffer = self.audio_buffers[participant_id]
            self.audio_buffers[participant_id] = []
            
            if not buffer:
                return
                
            # Concatenate audio chunks
            combined_audio = np.concatenate([chunk.audio_data for chunk in buffer])
            
            # Start tracing
            self.tracer.start_trace(trace_id, {
                "participant_id": participant_id,
                "audio_duration_ms": len(combined_audio) / 16000 * 1000,
                "chunk_count": len(buffer)
            })
            
            # Step 1: Speech-to-Text
            stt_start = time.time()
            try:
                stt_result = await self.stt_client.transcribe(
                    audio_data=combined_audio,
                    sample_rate=16000,
                    language="auto"
                )
                stt_duration = (time.time() - stt_start) * 1000
            except Exception as e:
                logger.error(f"STT error: {e}")
                return  # Skip this chunk if STT fails
            
            self.tracer.add_span(trace_id, "stt_processing", stt_start, stt_duration, {
                "model": self.config.stt_model,
                "text_length": len(stt_result.text),
                "confidence": stt_result.confidence
            })
            
            if not stt_result.text.strip():
                return  # No speech detected
                
            # Step 2: Update context buffer
            self.update_context_buffer(participant_id, stt_result.text)
            context = " ".join(self.context_buffers[participant_id])
            
            # Step 3: Machine Translation for each target language  
            translation_tasks = []
            for target_lang in self.config.target_languages:
                if target_lang != stt_result.detected_language:
                    task = asyncio.create_task(self.translate_text(
                        trace_id=trace_id,
                        text=stt_result.text,
                        context=context,
                        source_lang=stt_result.detected_language,
                        target_lang=target_lang,
                        participant_id=participant_id
                    ))
                    translation_tasks.append(task)
                    
            # Process all translations concurrently
            if translation_tasks:
                translation_results = await asyncio.gather(*translation_tasks, return_exceptions=True)
                
                # Handle successful translations
                for result in translation_results:
                    if isinstance(result, TranslationResult):
                        await self.publish_translation(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Translation failed: {result}")
                        
        except Exception as e:
            logger.error(f"Error in translation pipeline: {e}")
            self.tracer.add_error(trace_id, str(e))
        finally:
            total_duration = (time.time() - start_time) * 1000
            self.tracer.complete_trace(trace_id, {"total_latency_ms": total_duration})
            
    def update_context_buffer(self, participant_id: str, text: str):
        """Update rolling context buffer for better translations"""
        buffer = self.context_buffers[participant_id]
        buffer.append(text)
        
        # Keep only recent context (last 3 sentences or 512 tokens)
        while len(buffer) > 3 or sum(len(s.split()) for s in buffer) > self.config.context_length:
            buffer.pop(0)
            
    async def translate_text(
        self, 
        trace_id: str,
        text: str,
        context: str,
        source_lang: str,
        target_lang: str,
        participant_id: str
    ) -> TranslationResult:
        """Translate text and synthesize audio"""
        
        # Step 1: Machine Translation
        mt_start = time.time()
        try:
            translation = await self.mt_client.translate(
                text=text,
                source_language=source_lang,
                target_language=target_lang,
                context=context
            )
            mt_duration = (time.time() - mt_start) * 1000
        except Exception as e:
            logger.error(f"MT error: {e}")
            raise
        
        self.tracer.add_span(trace_id, "mt_processing", mt_start, mt_duration, {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "input_length": len(text),
            "output_length": len(translation.text)
        })
        
        # Step 2: Text-to-Speech
        tts_start = time.time()
        voice_id = self.config.voice_presets.get(target_lang, f"{target_lang}-default")
        try:
            audio_result = await self.tts_client.synthesize(
                text=translation.text,
                voice_id=voice_id,
                language=target_lang
            )
            tts_duration = (time.time() - tts_start) * 1000
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise
        
        self.tracer.add_span(trace_id, "tts_processing", tts_start, tts_duration, {
            "voice_id": voice_id,
            "text_length": len(translation.text),
            "audio_duration_ms": len(audio_result.audio_data) / 16000 * 1000
        })
        
        total_latency = mt_duration + tts_duration
        
        return TranslationResult(
            original_text=text,
            translated_text=translation.text,
            source_language=source_lang,
            target_language=target_lang,
            audio_data=audio_result.audio_data,
            confidence=translation.confidence,
            latency_ms=total_latency,
            chunk_id=f"{trace_id}_{target_lang}"
        )
        
    async def publish_translation(self, result: TranslationResult):
        """Publish translated audio track and captions to room"""
        if not self.room:
            return
            
        try:
            # Get or create audio track for this language
            track_key = f"translated_{result.target_language}"
            
            if track_key not in self.published_tracks:
                # Create new audio source and track
                audio_source = rtc.AudioSource(16000, 1)  # 16kHz mono
                track = rtc.LocalAudioTrack.create_audio_track(
                    name=track_key,
                    source=audio_source
                )
                
                # Publish the track
                options = rtc.TrackPublishOptions(
                    name=track_key,
                    source=rtc.TrackSource.SOURCE_MICROPHONE
                )
                await self.room.local_participant.publish_track(track, options)
                self.published_tracks[track_key] = track
                
                logger.info(f"Published new audio track: {track_key}")
            
            # Send audio frames to the existing track
            if result.audio_data is not None and len(result.audio_data) > 0:
                track = self.published_tracks[track_key]
                audio_source = track.source
                
                # Convert float32 audio data to int16 for LiveKit
                if result.audio_data.dtype == np.float32:
                    audio_int16 = (result.audio_data * 32767).astype(np.int16)
                else:
                    audio_int16 = result.audio_data.astype(np.int16)
                
                # Create and send audio frame
                frame = rtc.AudioFrame.create(
                    data=audio_int16.tobytes(),
                    sample_rate=16000,
                    num_channels=1,
                    samples_per_channel=len(audio_int16)
                )
                await audio_source.capture_frame(frame)
                
            # Send captions via data channel
            caption_data = {
                "type": "translation",
                "original_text": result.original_text,
                "translated_text": result.translated_text,
                "source_language": result.source_language,
                "target_language": result.target_language,
                "confidence": result.confidence,
                "latency_ms": result.latency_ms,
                "timestamp": datetime.now().isoformat(),
                "chunk_id": result.chunk_id
            }
            
            await self.room.local_participant.publish_data(
                json.dumps(caption_data).encode('utf-8'),
                topic="captions"
            )
            
            logger.info(f"Published translation: {result.source_language}→{result.target_language}, latency: {result.latency_ms:.1f}ms")
            
        except Exception as e:
            logger.error(f"Error publishing translation: {e}")

async def entrypoint(ctx: JobContext):
    """Main entry point for LiveKit agent"""
    config = TranslationConfig()
    worker = TranslatorWorker(config)
    
    # Connect to room
    await worker.connect_to_room(
        url=ctx.room.url,
        token=ctx.room.token, 
        room_name=ctx.room.name
    )
    
    logger.info("Translator worker started successfully")
    
    # Keep worker running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run LiveKit agent
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))