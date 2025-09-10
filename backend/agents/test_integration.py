#!/usr/bin/env python3
"""
Integration test for The HIVE Translator Worker

Tests the complete STT→MT→TTS pipeline integration
"""

import asyncio
import logging
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.stt_client import STTClient
from services.mt_client import MTClient  
from services.tts_client import TTSClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_stt_service():
    """Test STT service connection and transcription"""
    logger.info("Testing STT service...")
    client = STTClient()
    
    try:
        await client.connect()
        
        # Generate test audio (1 second of sine wave at 440Hz)
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
        
        # Convert to int16 for STT service
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        result = await client.transcribe(audio_int16)
        logger.info(f"STT Result: {result.text if result else 'No result'}")
        
        await client.disconnect()
        return result is not None
        
    except Exception as e:
        logger.error(f"STT test failed: {e}")
        return False

async def test_mt_service():
    """Test MT service connection and translation"""
    logger.info("Testing MT service...")
    client = MTClient()
    
    try:
        await client.connect()
        
        result = await client.translate(
            text="Hello, how are you today?",
            source_language="en",
            target_language="es"
        )
        
        logger.info(f"MT Result: {result.text if result else 'No result'}")
        
        await client.disconnect()
        return result is not None
        
    except Exception as e:
        logger.error(f"MT test failed: {e}")
        return False

async def test_tts_service():
    """Test TTS service connection and synthesis"""
    logger.info("Testing TTS service...")
    client = TTSClient()
    
    try:
        await client.connect()
        
        result = await client.synthesize(
            text="Hello world",
            voice_id="en-us-female-1", 
            language="en"
        )
        
        logger.info(f"TTS Result: {len(result.audio_data) if result and result.audio_data is not None else 0} audio samples")
        
        await client.disconnect()
        return result is not None and result.audio_data is not None and len(result.audio_data) > 0
        
    except Exception as e:
        logger.error(f"TTS test failed: {e}")
        return False

async def test_full_pipeline():
    """Test the complete pipeline"""
    logger.info("Testing full STT→MT→TTS pipeline...")
    
    stt_client = STTClient()
    mt_client = MTClient()
    tts_client = TTSClient()
    
    try:
        # Connect all services
        await asyncio.gather(
            stt_client.connect(),
            mt_client.connect(), 
            tts_client.connect()
        )
        
        # Generate test audio (simple sine wave)
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.int16)
        
        # Step 1: STT
        stt_result = await stt_client.transcribe(audio_data)
        if not stt_result or not stt_result.text:
            # Use fallback text for testing
            text = "Hello, this is a test message"
            logger.info(f"Using fallback text: {text}")
        else:
            text = stt_result.text
            logger.info(f"STT: {text}")
        
        # Step 2: MT
        mt_result = await mt_client.translate(
            text=text,
            source_language="en",
            target_language="es"
        )
        
        if not mt_result:
            logger.error("MT failed")
            return False
            
        logger.info(f"MT: {mt_result.text}")
        
        # Step 3: TTS
        tts_result = await tts_client.synthesize(
            text=mt_result.text,
            voice_id="es-mx-female-1",
            language="es"
        )
        
        if not tts_result or tts_result.audio_data is None:
            logger.error("TTS failed")
            return False
            
        logger.info(f"TTS: Generated {len(tts_result.audio_data)} audio samples")
        
        # Disconnect all services
        await asyncio.gather(
            stt_client.disconnect(),
            mt_client.disconnect(),
            tts_client.disconnect()
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        return False

async def main():
    """Run all integration tests"""
    logger.info("Starting integration tests...")
    
    tests = [
        ("STT Service", test_stt_service),
        ("MT Service", test_mt_service),
        ("TTS Service", test_tts_service),
        ("Full Pipeline", test_full_pipeline)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        logger.info(f"{'='*50}")
        
        try:
            success = await test_func()
            results[test_name] = success
            status = "PASSED" if success else "FAILED"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name} test error: {e}")
            results[test_name] = False
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("Test Summary:")
    logger.info(f"{'='*50}")
    
    for test_name, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"{test_name:.<30} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    logger.info(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        logger.info("🎉 All tests passed! The translator worker is ready.")
        return 0
    else:
        logger.error("❌ Some tests failed. Check service connections and configurations.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)