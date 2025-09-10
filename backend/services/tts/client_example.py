"""
TTS Service Client Example
Demonstrates how to integrate with The HIVE TTS service from other components

Usage examples:
- Translation pipeline integration
- WebSocket streaming client
- HTTP batch synthesis
- Voice cloning workflow
"""

import asyncio
import websockets
import requests
import json
import base64
import numpy as np
import wave
import io
from typing import Optional, AsyncGenerator, List, Dict
import aiohttp
import time

class TTSClient:
    """Client for The HIVE TTS Service"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws") + "/ws/synthesize"
        
    async def get_available_voices(self, language: Optional[str] = None) -> Dict:
        """Get available voices"""
        url = f"{self.base_url}/voices"
        if language:
            url += f"/{language}"
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
    
    async def synthesize_streaming(
        self,
        text: str,
        voice_id: str = "en-us-female-premium",
        language: str = "en",
        engine: str = "xtts"
    ) -> AsyncGenerator[Dict, None]:
        """Stream TTS synthesis"""
        
        async with websockets.connect(self.ws_url) as websocket:
            request = {
                "text": text,
                "voice_id": voice_id,
                "language": language,
                "engine": engine,
                "stream": True
            }
            
            await websocket.send(json.dumps(request))
            
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                yield data
                
                if data.get("is_final"):
                    break
    
    async def synthesize_to_file(
        self,
        text: str,
        output_file: str,
        voice_id: str = "en-us-female-premium",
        language: str = "en",
        engine: str = "xtts"
    ) -> Dict:
        """Synthesize text to audio file"""
        
        audio_chunks = []
        metadata = {}
        
        async for chunk_data in self.synthesize_streaming(text, voice_id, language, engine):
            if chunk_data.get("audio_chunk"):
                # Decode base64 audio
                audio_bytes = base64.b64decode(chunk_data["audio_chunk"])
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_chunks.append(audio_data)
            
            if chunk_data.get("is_final"):
                metadata = chunk_data.get("metadata", {})
                break
        
        # Save to WAV file
        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
            
            with wave.open(output_file, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(full_audio.tobytes())
            
            return {
                "file": output_file,
                "duration_seconds": len(full_audio) / 16000,
                "samples": len(full_audio),
                "metadata": metadata
            }
        else:
            raise ValueError("No audio data received")
    
    async def clone_voice_and_synthesize(
        self,
        text: str,
        reference_audio_file: str,
        output_file: str,
        base_voice_id: str = "en-us-female-premium",
        language: str = "en"
    ) -> Dict:
        """Clone voice from reference and synthesize text"""
        
        # Note: This is a simplified example
        # In production, voice cloning would be a separate endpoint
        
        async for chunk_data in self.synthesize_streaming(
            text, 
            base_voice_id, 
            language, 
            "xtts"  # XTTS supports voice cloning
        ):
            if chunk_data.get("is_final"):
                break
        
        return await self.synthesize_to_file(text, output_file, base_voice_id, language, "xtts")

class TranslationPipelineIntegration:
    """Example integration with translation pipeline"""
    
    def __init__(self, tts_client: TTSClient):
        self.tts_client = tts_client
        
    async def translate_and_synthesize(
        self,
        translated_text: str,
        target_language: str,
        session_id: str
    ) -> AsyncGenerator[bytes, None]:
        """Convert translated text to audio stream"""
        
        # Get best voice for target language
        voices = await self.tts_client.get_available_voices(target_language)
        if not voices.get("voices"):
            raise ValueError(f"No voices available for language: {target_language}")
        
        # Select premium voice if available
        best_voice = None
        for voice in voices["voices"]:
            if voice.get("quality_tier") == "premium":
                best_voice = voice["voice_id"]
                break
        
        if not best_voice:
            best_voice = voices["voices"][0]["voice_id"]
        
        # Stream synthesis
        async for chunk_data in self.tts_client.synthesize_streaming(
            translated_text,
            best_voice,
            target_language,
            "xtts"  # Use highest quality for translation
        ):
            if chunk_data.get("audio_chunk"):
                # Return raw audio bytes for LiveKit
                audio_bytes = base64.b64decode(chunk_data["audio_chunk"])
                yield audio_bytes

class LiveKitTTSBridge:
    """Bridge between TTS service and LiveKit"""
    
    def __init__(self, tts_client: TTSClient):
        self.tts_client = tts_client
        
    async def publish_audio_track(
        self,
        room_name: str,
        participant_id: str,
        text: str,
        language: str
    ):
        """Publish TTS audio to LiveKit track"""
        
        # This would integrate with LiveKit SDK
        # Simplified example showing the concept
        
        audio_buffer = io.BytesIO()
        
        async for chunk_data in self.tts_client.synthesize_streaming(text, language=language):
            if chunk_data.get("audio_chunk"):
                audio_bytes = base64.b64decode(chunk_data["audio_chunk"])
                audio_buffer.write(audio_bytes)
                
                # In real implementation, would publish chunk to LiveKit immediately
                # livekit_track.publish_audio_frame(audio_bytes)
        
        return audio_buffer.getvalue()

# Example usage functions

async def example_basic_synthesis():
    """Basic TTS synthesis example"""
    print("=== Basic TTS Synthesis ===")
    
    client = TTSClient()
    
    # Simple synthesis to file
    result = await client.synthesize_to_file(
        text="Hello! This is a test of the TTS service.",
        output_file="test_basic.wav",
        voice_id="en-us-female-premium",
        language="en",
        engine="xtts"
    )
    
    print(f"Generated: {result['file']}")
    print(f"Duration: {result['duration_seconds']:.2f}s")

async def example_streaming_synthesis():
    """Streaming TTS with real-time processing"""
    print("\n=== Streaming TTS Synthesis ===")
    
    client = TTSClient()
    
    text = "This is a longer text that will be synthesized in real-time chunks for low-latency applications."
    
    start_time = time.time()
    ttft = None
    chunks_received = 0
    
    async for chunk_data in client.synthesize_streaming(
        text=text,
        voice_id="en-us-female-premium",
        language="en",
        engine="piper"  # Fast engine for streaming
    ):
        if chunk_data.get("ttft_ms") and ttft is None:
            ttft = chunk_data["ttft_ms"]
            print(f"Time to First Token: {ttft:.1f}ms")
        
        if chunk_data.get("audio_chunk"):
            chunks_received += 1
            print(f"Received chunk {chunks_received} - Quality: {chunk_data.get('quality_score', 0):.2f}")
        
        if chunk_data.get("is_final"):
            total_time = time.time() - start_time
            print(f"Total synthesis time: {total_time*1000:.1f}ms")
            break

async def example_multilingual_synthesis():
    """Multi-language TTS synthesis"""
    print("\n=== Multi-language TTS ===")
    
    client = TTSClient()
    
    test_cases = [
        ("Hello, how are you today?", "en", "en-us-female-premium"),
        ("Bonjour, comment allez-vous?", "fr", "fr-fr-female-premium"), 
        ("¡Hola! ¿Cómo está usted?", "es", "es-mx-female-premium"),
        ("Guten Tag! Wie geht es Ihnen?", "de", "de-de-female-premium"),
    ]
    
    for text, lang, voice_id in test_cases:
        print(f"Synthesizing {lang}: {text}")
        
        result = await client.synthesize_to_file(
            text=text,
            output_file=f"test_{lang}.wav",
            voice_id=voice_id,
            language=lang,
            engine="xtts"
        )
        
        print(f"  Generated: {result['file']} ({result['duration_seconds']:.2f}s)")

async def example_performance_comparison():
    """Compare engine performance"""
    print("\n=== Engine Performance Comparison ===")
    
    client = TTSClient()
    test_text = "The quick brown fox jumps over the lazy dog."
    engines = ["piper", "speecht5", "xtts"]
    
    results = {}
    
    for engine in engines:
        print(f"\nTesting {engine.upper()} engine...")
        
        start_time = time.time()
        ttft = None
        chunks = 0
        
        try:
            async for chunk_data in client.synthesize_streaming(
                text=test_text,
                voice_id="en-us-female-premium",
                language="en",
                engine=engine
            ):
                if chunk_data.get("ttft_ms") and ttft is None:
                    ttft = chunk_data["ttft_ms"]
                
                if chunk_data.get("audio_chunk"):
                    chunks += 1
                
                if chunk_data.get("is_final"):
                    total_time = time.time() - start_time
                    results[engine] = {
                        "ttft_ms": ttft,
                        "total_time_ms": total_time * 1000,
                        "chunks": chunks
                    }
                    break
            
            print(f"  TTFT: {ttft:.1f}ms")
            print(f"  Total: {total_time*1000:.1f}ms") 
            print(f"  Chunks: {chunks}")
            
        except Exception as e:
            print(f"  Error: {e}")
            results[engine] = {"error": str(e)}
    
    # Find best performing engine
    valid_results = {k: v for k, v in results.items() if "error" not in v}
    if valid_results:
        best_ttft = min(valid_results.items(), key=lambda x: x[1]["ttft_ms"])
        print(f"\nBest TTFT: {best_ttft[0]} ({best_ttft[1]['ttft_ms']:.1f}ms)")

async def example_voice_listing():
    """List available voices"""
    print("\n=== Available Voices ===")
    
    client = TTSClient()
    
    # Get all voices
    all_voices = await client.get_available_voices()
    print(f"Total voices: {all_voices.get('total_voices')}")
    print(f"Languages: {', '.join(all_voices.get('languages', []))}")
    
    # Get English voices
    en_voices = await client.get_available_voices("en")
    print(f"\nEnglish voices: {len(en_voices.get('voices', []))}")
    
    for voice in en_voices.get("voices", [])[:3]:  # Show first 3
        print(f"  {voice['voice_id']}: {voice['name']} ({voice['gender']}, {voice['quality_tier']})")

async def main():
    """Run all examples"""
    
    # Check service health first
    try:
        response = requests.get("http://localhost:8003/health", timeout=5)
        health = response.json()
        print(f"TTS Service Status: {health.get('status')}")
        
        if health.get('status') != 'healthy':
            print("Service not healthy. Please start the TTS service first.")
            return
            
    except Exception as e:
        print(f"Cannot connect to TTS service: {e}")
        print("Please start the TTS service first: python app.py")
        return
    
    # Run examples
    await example_voice_listing()
    await example_basic_synthesis()
    await example_streaming_synthesis() 
    await example_multilingual_synthesis()
    await example_performance_comparison()
    
    print("\n=== All Examples Completed ===")
    print("Check the generated .wav files to hear the results!")

if __name__ == "__main__":
    asyncio.run(main())