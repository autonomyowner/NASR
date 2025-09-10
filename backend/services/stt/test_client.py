"""
STT WebSocket Test Client
Test client for streaming STT service with synthetic audio and real file testing
"""

import asyncio
import json
import logging
import time
import wave
import numpy as np
from typing import Optional, List, AsyncGenerator
from pathlib import Path
import argparse

import websockets
import pyaudio
import soundfile as sf
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class STTTestClient:
    """WebSocket client for testing STT service"""
    
    def __init__(self, server_url: str = "ws://localhost:8001/ws/stt"):
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.session_metrics = {
            "total_messages": 0,
            "confirmed_segments": 0,
            "avg_processing_time": 0.0,
            "start_time": None,
            "latencies": []
        }
        
    async def connect(self):
        """Connect to STT service"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            self.session_metrics["start_time"] = time.time()
            logger.info(f"Connected to STT service: {self.server_url}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from STT service"""
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from STT service")
    
    async def send_audio_chunk(self, audio_data: bytes):
        """Send audio chunk to STT service"""
        if not self.is_connected or not self.websocket:
            raise ConnectionError("Not connected to STT service")
        
        try:
            await self.websocket.send(audio_data)
        except (ConnectionClosedError, ConnectionClosedOK) as e:
            logger.error(f"Connection closed while sending: {e}")
            self.is_connected = False
            raise
    
    async def receive_response(self) -> Optional[dict]:
        """Receive response from STT service"""
        if not self.is_connected or not self.websocket:
            return None
        
        try:
            message = await self.websocket.recv()
            response = json.loads(message)
            
            # Update metrics
            self.session_metrics["total_messages"] += 1
            if response.get("type") == "confirmed":
                self.session_metrics["confirmed_segments"] += len(response.get("segments", []))
            
            processing_time = response.get("processing_time_ms", 0)
            self.session_metrics["latencies"].append(processing_time)
            
            return response
            
        except (ConnectionClosedError, ConnectionClosedOK):
            logger.info("Connection closed")
            self.is_connected = False
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode response: {e}")
            return None
    
    async def test_with_audio_file(self, audio_file: str, chunk_size: int = 4000):
        """Test STT service with audio file"""
        logger.info(f"Testing with audio file: {audio_file}")
        
        try:
            # Load audio file
            audio_data, sample_rate = sf.read(audio_file)
            
            # Convert to 16kHz mono if needed
            if sample_rate != 16000:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                sample_rate = 16000
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # Convert to int16 format
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            logger.info(f"Audio loaded: {len(audio_data)/sample_rate:.2f}s, {sample_rate}Hz")
            
            # Connect to service
            await self.connect()
            
            # Create tasks for sending and receiving
            send_task = asyncio.create_task(
                self._send_audio_chunks(audio_bytes, chunk_size)
            )
            receive_task = asyncio.create_task(
                self._receive_responses()
            )
            
            # Wait for sending to complete
            await send_task
            
            # Wait a bit more for final responses
            await asyncio.sleep(2.0)
            
            # Cancel receiving task
            receive_task.cancel()
            
            # Disconnect
            await self.disconnect()
            
            # Print results
            self._print_session_metrics()
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            if self.is_connected:
                await self.disconnect()
    
    async def _send_audio_chunks(self, audio_bytes: bytes, chunk_size: int):
        """Send audio in chunks"""
        total_chunks = len(audio_bytes) // chunk_size
        logger.info(f"Sending {total_chunks} audio chunks ({chunk_size} bytes each)")
        
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            
            if len(chunk) > 0:
                await self.send_audio_chunk(chunk)
                
                # Simulate real-time audio streaming (250ms chunks)
                await asyncio.sleep(0.25)
                
                if (i // chunk_size) % 10 == 0:
                    logger.info(f"Sent chunk {i // chunk_size + 1}/{total_chunks}")
        
        logger.info("Finished sending audio chunks")
    
    async def _receive_responses(self):
        """Continuously receive and log responses"""
        try:
            while self.is_connected:
                response = await self.receive_response()
                if response:
                    self._log_response(response)
                else:
                    break
        except asyncio.CancelledError:
            logger.info("Response receiving cancelled")
    
    def _log_response(self, response: dict):
        """Log STT response"""
        response_type = response.get("type", "unknown")
        segments = response.get("segments", [])
        processing_time = response.get("processing_time_ms", 0)
        
        if segments:
            text = " ".join(seg["text"] for seg in segments)
            confidence = np.mean([seg["confidence"] for seg in segments])
            
            logger.info(
                f"[{response_type.upper()}] '{text}' "
                f"(conf: {confidence:.2f}, time: {processing_time:.1f}ms)"
            )
    
    def _print_session_metrics(self):
        """Print session performance metrics"""
        duration = time.time() - self.session_metrics["start_time"]
        latencies = self.session_metrics["latencies"]
        
        print("\n" + "="*60)
        print("STT SESSION METRICS")
        print("="*60)
        print(f"Duration: {duration:.2f}s")
        print(f"Total messages: {self.session_metrics['total_messages']}")
        print(f"Confirmed segments: {self.session_metrics['confirmed_segments']}")
        
        if latencies:
            print(f"Processing time - Avg: {np.mean(latencies):.1f}ms")
            print(f"Processing time - P95: {np.percentile(latencies, 95):.1f}ms")
            print(f"Processing time - Max: {np.max(latencies):.1f}ms")
        
        print("="*60)
    
    async def test_with_microphone(self, duration_seconds: int = 30):
        """Test STT service with live microphone input"""
        logger.info(f"Testing with microphone for {duration_seconds}s")
        
        # Audio parameters
        CHUNK = 4000  # 250ms at 16kHz
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        p = pyaudio.PyAudio()
        
        try:
            # Open microphone stream
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            # Connect to STT service
            await self.connect()
            
            logger.info("Recording... Speak into microphone")
            
            # Create receiving task
            receive_task = asyncio.create_task(self._receive_responses())
            
            # Record and send audio
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time and self.is_connected:
                data = stream.read(CHUNK, exception_on_overflow=False)
                await self.send_audio_chunk(data)
                
                # Small delay to prevent overwhelming the server
                await asyncio.sleep(0.01)
            
            logger.info("Recording finished")
            
            # Wait for final responses
            await asyncio.sleep(2.0)
            
            # Cleanup
            receive_task.cancel()
            stream.stop_stream()
            stream.close()
            
            await self.disconnect()
            self._print_session_metrics()
            
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
        finally:
            p.terminate()
    
    def generate_test_audio(self, duration: float = 5.0, sample_rate: int = 16000) -> bytes:
        """Generate synthetic test audio (sine wave sweep)"""
        t = np.linspace(0, duration, int(duration * sample_rate), False)
        
        # Frequency sweep from 200Hz to 2000Hz
        frequency = 200 + (1800 * t / duration)
        audio = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # Add some speech-like modulation
        modulation = np.sin(2 * np.pi * 10 * t) * 0.1 + 1.0
        audio = audio * modulation
        
        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()
    
    async def test_synthetic_audio(self, duration: float = 10.0):
        """Test STT service with synthetic audio"""
        logger.info(f"Testing with synthetic audio ({duration}s)")
        
        # Generate test audio
        audio_bytes = self.generate_test_audio(duration)
        
        await self.connect()
        
        # Send and receive
        send_task = asyncio.create_task(
            self._send_audio_chunks(audio_bytes, 4000)
        )
        receive_task = asyncio.create_task(
            self._receive_responses()
        )
        
        await send_task
        await asyncio.sleep(2.0)
        receive_task.cancel()
        
        await self.disconnect()
        self._print_session_metrics()


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="STT Service Test Client")
    parser.add_argument("--url", default="ws://localhost:8001/ws/stt", help="STT service URL")
    parser.add_argument("--mode", choices=["file", "mic", "synthetic"], default="synthetic",
                      help="Test mode")
    parser.add_argument("--file", help="Audio file path (for file mode)")
    parser.add_argument("--duration", type=int, default=10, help="Duration in seconds")
    
    args = parser.parse_args()
    
    client = STTTestClient(args.url)
    
    try:
        if args.mode == "file":
            if not args.file:
                logger.error("File path required for file mode")
                return
            await client.test_with_audio_file(args.file)
        elif args.mode == "mic":
            await client.test_with_microphone(args.duration)
        else:  # synthetic
            await client.test_synthetic_audio(args.duration)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())