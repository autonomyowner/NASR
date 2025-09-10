"""
MT Service Client SDK

WebSocket client for connecting the LiveKit translator worker
to the streaming MT service.
"""

import asyncio
import json
import logging
import websockets
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MTResult:
    """MT translation result"""
    text: str
    confidence: float
    source_language: str
    target_language: str
    processing_time_ms: float
    model_used: str
    context_used: bool = False

class MTClient:
    """WebSocket client for MT service"""
    
    def __init__(self, service_url: str = "ws://localhost:8002/ws/translate"):
        self.service_url = service_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_counter = 0
        
    async def connect(self):
        """Connect to MT service"""
        try:
            self.websocket = await websockets.connect(self.service_url)
            self.is_connected = True
            logger.info(f"Connected to MT service at {self.service_url}")
            
            # Start listening for responses
            asyncio.create_task(self._listen_for_responses())
            
        except Exception as e:
            logger.error(f"Failed to connect to MT service: {e}")
            self.is_connected = False
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from MT service"""
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False
        self.websocket = None
        logger.info("Disconnected from MT service")
    
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> MTResult:
        """Send text for translation and wait for result"""
        if not self.is_connected or not self.websocket:
            await self.connect()
            if not self.is_connected:
                raise Exception("Failed to connect to MT service")
            
        try:
            # Create a session_id for request tracking
            session_id = f"session_{self.request_counter}"
            self.request_counter += 1
            
            request = {
                "text": text,
                "source_language": source_language, 
                "target_language": target_language,
                "context": context,
                "session_id": session_id
            }
            
            # Create a future for this request
            future = asyncio.Future()
            self.pending_requests[session_id] = future
            
            await self.websocket.send(json.dumps(request))
            
            # Wait for response with timeout
            try:
                result = await asyncio.wait_for(future, timeout=10.0)
                return result
            except asyncio.TimeoutError:
                if session_id in self.pending_requests:
                    del self.pending_requests[session_id]
                raise Exception("MT translation timed out")
            
        except Exception as e:
            logger.error(f"Error sending translation request: {e}")
            raise
    
    async def _listen_for_responses(self):
        """Listen for MT service responses"""
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    data = json.loads(message)
                    session_id = data.get("session_id")
                    
                    result = MTResult(
                        text=data["translation"],
                        confidence=data.get("confidence", 0.9),
                        source_language=data["source_language"],
                        target_language=data["target_language"],
                        processing_time_ms=data.get("processing_time_ms", 0),
                        model_used=data.get("model_used", "marian"),
                        context_used=data.get("context_used", False)
                    )
                    
                    # Complete the matching request
                    if session_id and session_id in self.pending_requests:
                        future = self.pending_requests.pop(session_id)
                        if not future.done():
                            future.set_result(result)
                    elif self.pending_requests:
                        # Fallback: complete the first pending request
                        request_id = next(iter(self.pending_requests.keys()))
                        future = self.pending_requests.pop(request_id)
                        if not future.done():
                            future.set_result(result)
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("MT service connection closed")
            self.is_connected = False
            # Cancel all pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.set_exception(Exception("Connection closed"))
            self.pending_requests.clear()
        except Exception as e:
            logger.error(f"Error listening for MT responses: {e}")
            # Cancel all pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.set_exception(e)
            self.pending_requests.clear()

class BatchMTClient:
    """Batch MT client for non-streaming requests"""
    
    def __init__(self, service_url: str = "http://mt-service:8002"):
        self.service_url = service_url
    
    async def translate_batch(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> MTResult:
        """Translate text in batch mode using HTTP API"""
        import aiohttp
        
        try:
            data = {
                "text": text,
                "source_language": source_language,
                "target_language": target_language,
                "context": context,
                "session_id": "batch_" + str(hash(text))[:8]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.service_url}/translate", json=data) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        return MTResult(
                            text=result_data["text"],
                            confidence=result_data["confidence"],
                            source_language=result_data["source_language"],
                            target_language=result_data["target_language"],
                            processing_time_ms=result_data["processing_time_ms"],
                            model_used=result_data["model_used"],
                            context_used=result_data.get("context_used", False)
                        )
                    else:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Batch translation error: {e}")
            raise