"""
TTS Service Client SDK

WebSocket client for connecting the LiveKit translator worker
to the streaming TTS service.
"""

import asyncio
import json
import logging
import websockets
import base64
import numpy as np
from typing import Optional, Callable, Dict, Any, AsyncGenerator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TTSResult:
    """TTS synthesis result"""
    audio_data: np.ndarray
    sample_rate: int
    voice_id: str
    language: str
    processing_time_ms: float
    ttft_ms: Optional[float] = None  # Time to first frame
    is_final: bool = False

class TTSClient:
    """WebSocket client for TTS service"""
    
    def __init__(self, service_url: str = "ws://localhost:8003/ws/synthesize"):
        self.service_url = service_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.pending_requests: Dict[str, Dict] = {}
        self.request_counter = 0
        
    async def connect(self):
        """Connect to TTS service"""
        try:
            self.websocket = await websockets.connect(self.service_url)
            self.is_connected = True
            logger.info(f"Connected to TTS service at {self.service_url}")
            
            # Start listening for responses
            asyncio.create_task(self._listen_for_responses())
            
        except Exception as e:
            logger.error(f"Failed to connect to TTS service: {e}")
            self.is_connected = False
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from TTS service"""
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False
        self.websocket = None
        logger.info("Disconnected from TTS service")
    
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        stream: bool = False,
        speed: float = 1.0
    ) -> TTSResult:
        """Send text for speech synthesis and wait for result"""
        if not self.is_connected or not self.websocket:
            await self.connect()
            if not self.is_connected:
                raise Exception("Failed to connect to TTS service")
            
        try:
            # Create session_id for request tracking
            session_id = f"session_{self.request_counter}"
            self.request_counter += 1
            
            request = {
                "text": text,
                "voice_id": voice_id,
                "language": language,
                "stream": stream,
                "speed": speed,
                "session_id": session_id
            }
            
            # Create tracking for this request
            future = asyncio.Future()
            audio_chunks = []
            self.pending_requests[session_id] = {
                "future": future,
                "audio_chunks": audio_chunks,
                "metadata": None
            }
            
            await self.websocket.send(json.dumps(request))
            
            # Wait for response with timeout
            try:
                result = await asyncio.wait_for(future, timeout=15.0)
                return result
            except asyncio.TimeoutError:
                if session_id in self.pending_requests:
                    del self.pending_requests[session_id]
                raise Exception("TTS synthesis timed out")
            
        except Exception as e:
            logger.error(f"Error sending synthesis request: {e}")
            raise
    
    async def _listen_for_responses(self):
        """Listen for TTS service responses"""
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    data = json.loads(message)
                    session_id = data.get("session_id")
                    
                    if session_id and session_id in self.pending_requests:
                        request_data = self.pending_requests[session_id]
                        
                        # Handle audio chunk
                        if data.get("audio_chunk"):
                            audio_bytes = base64.b64decode(data["audio_chunk"])
                            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                            request_data["audio_chunks"].append(audio_data)
                        
                        # Store metadata on first chunk
                        if not request_data["metadata"]:
                            request_data["metadata"] = {
                                "voice_id": data.get("voice_id", "unknown"),
                                "language": data.get("language", "en"),
                                "sample_rate": data.get("sample_rate", 16000),
                                "processing_time_ms": data.get("processing_time_ms", 0)
                            }
                        
                        # Complete on final chunk
                        if data.get("is_final", False):
                            # Concatenate all audio chunks
                            if request_data["audio_chunks"]:
                                combined_audio = np.concatenate(request_data["audio_chunks"])
                            else:
                                combined_audio = np.array([], dtype=np.float32)
                                
                            result = TTSResult(
                                audio_data=combined_audio,
                                sample_rate=request_data["metadata"]["sample_rate"],
                                voice_id=request_data["metadata"]["voice_id"],
                                language=request_data["metadata"]["language"],
                                processing_time_ms=request_data["metadata"]["processing_time_ms"],
                                is_final=True
                            )
                            
                            future = request_data["future"]
                            if not future.done():
                                future.set_result(result)
                            del self.pending_requests[session_id]
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("TTS service connection closed")
            self.is_connected = False
            # Cancel all pending requests
            for request_data in self.pending_requests.values():
                future = request_data["future"]
                if not future.done():
                    future.set_exception(Exception("Connection closed"))
            self.pending_requests.clear()
        except Exception as e:
            logger.error(f"Error listening for TTS responses: {e}")
            # Cancel all pending requests
            for request_data in self.pending_requests.values():
                future = request_data["future"]
                if not future.done():
                    future.set_exception(e)
            self.pending_requests.clear()

class BatchTTSClient:
    """Batch TTS client for non-streaming requests"""
    
    def __init__(self, service_url: str = "http://tts-service:8002"):
        self.service_url = service_url
    
    async def synthesize_batch(
        self,
        text: str,
        voice_id: str,
        language: str,
        speed: float = 1.0
    ) -> TTSResult:
        """Synthesize speech in batch mode using HTTP API"""
        import aiohttp
        
        try:
            data = {
                "text": text,
                "voice_id": voice_id,
                "language": language,
                "stream": False,
                "speed": speed
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.service_url}/synthesize", json=data) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        
                        # Decode base64 audio data
                        audio_bytes = base64.b64decode(result_data["audio_data"])
                        audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                        
                        return TTSResult(
                            audio_data=audio_data,
                            sample_rate=result_data["sample_rate"],
                            voice_id=result_data["voice_id"],
                            language=result_data["language"],
                            processing_time_ms=0,  # Not provided in batch mode
                            is_final=True
                        )
                    else:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Batch synthesis error: {e}")
            raise

class StreamingTTSClient:
    """Streaming TTS client that yields audio chunks as they arrive"""
    
    def __init__(self, service_url: str = "ws://tts-service:8002/ws/synthesize"):
        self.service_url = service_url
    
    async def synthesize_stream(
        self,
        text: str,
        voice_id: str,
        language: str,
        speed: float = 1.0
    ) -> AsyncGenerator[TTSResult, None]:
        """Synthesize speech and yield chunks as they arrive"""
        websocket = None
        try:
            websocket = await websockets.connect(self.service_url)
            
            request = {
                "text": text,
                "voice_id": voice_id,
                "language": language,
                "stream": True,
                "speed": speed
            }
            
            await websocket.send(json.dumps(request))
            
            async for message in websocket:
                if isinstance(message, str):
                    data = json.loads(message)
                    
                    # Decode base64 audio data
                    audio_data = np.array([])
                    if data["audio_chunk"]:
                        audio_bytes = base64.b64decode(data["audio_chunk"])
                        audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                    
                    result = TTSResult(
                        audio_data=audio_data,
                        sample_rate=data["sample_rate"],
                        voice_id=data["voice_id"],
                        language=data["language"],
                        processing_time_ms=data["processing_time_ms"],
                        ttft_ms=data.get("ttft_ms"),
                        is_final=data["is_final"]
                    )
                    
                    yield result
                    
                    if data["is_final"]:
                        break
                        
        except Exception as e:
            logger.error(f"Streaming synthesis error: {e}")
            raise
        finally:
            if websocket:
                await websocket.close()