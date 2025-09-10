"""
STT Service Client SDK

WebSocket client for connecting the LiveKit translator worker
to the streaming STT service.
"""

import asyncio
import json
import logging
import websockets
import numpy as np
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class STTResult:
    """STT transcription result"""
    text: str
    confidence: float
    detected_language: str
    is_final: bool
    timestamp: float
    processing_time_ms: float
    words: Optional[list] = None

class STTClient:
    """WebSocket client for STT service"""
    
    def __init__(self, service_url: str = "ws://localhost:8001/ws/stt"):
        self.service_url = service_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_counter = 0
        
    async def connect(self):
        """Connect to STT service"""
        try:
            self.websocket = await websockets.connect(self.service_url)
            self.is_connected = True
            logger.info(f"Connected to STT service at {self.service_url}")
            
            # Start listening for responses
            asyncio.create_task(self._listen_for_responses())
            
        except Exception as e:
            logger.error(f"Failed to connect to STT service: {e}")
            self.is_connected = False
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from STT service"""
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False
        self.websocket = None
        logger.info("Disconnected from STT service")
    
    async def transcribe(
        self, 
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: str = "auto"
    ) -> STTResult:
        """Send audio for transcription and wait for result"""
        if not self.is_connected or not self.websocket:
            await self.connect()
            if not self.is_connected:
                raise Exception("Failed to connect to STT service")
            
        try:
            # Convert numpy array to bytes
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_data.tobytes()
            
            # Create a future for this request
            request_id = str(self.request_counter)
            self.request_counter += 1
            future = asyncio.Future()
            self.pending_requests[request_id] = future
            
            # Send audio data as bytes (the service expects raw audio bytes)
            await self.websocket.send(audio_bytes)
            
            # Wait for response with timeout
            try:
                result = await asyncio.wait_for(future, timeout=10.0)
                return result
            except asyncio.TimeoutError:
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                raise Exception("STT transcription timed out")
            
        except Exception as e:
            logger.error(f"Error sending audio to STT service: {e}")
            raise
    
    async def _listen_for_responses(self):
        """Listen for STT service responses"""
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    data = json.loads(message)
                    result = STTResult(
                        text=data["text"],
                        confidence=data["confidence"],
                        detected_language=data.get("language", "en"),
                        is_final=data.get("is_final", True),
                        timestamp=data.get("timestamp", 0),
                        processing_time_ms=data.get("processing_time_ms", 0),
                        words=data.get("words")
                    )
                    
                    # Complete the first pending request
                    if self.pending_requests:
                        request_id = next(iter(self.pending_requests.keys()))
                        future = self.pending_requests.pop(request_id)
                        if not future.done():
                            future.set_result(result)
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("STT service connection closed")
            self.is_connected = False
            # Cancel all pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.set_exception(Exception("Connection closed"))
            self.pending_requests.clear()
        except Exception as e:
            logger.error(f"Error listening for STT responses: {e}")
            # Cancel all pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.set_exception(e)
            self.pending_requests.clear()

class BatchSTTClient:
    """Batch STT client for non-streaming requests"""
    
    def __init__(self, service_url: str = "http://stt-service:8000"):
        self.service_url = service_url
    
    async def transcribe_batch(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: str = "auto"
    ) -> STTResult:
        """Transcribe audio in batch mode"""
        # This would use HTTP requests for batch processing
        # Implementation would depend on the STT service HTTP API
        pass