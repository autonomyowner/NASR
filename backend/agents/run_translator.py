#!/usr/bin/env python3
"""
LiveKit Translator Worker Runner

Standalone script to run the translator worker with configuration management
and monitoring integration.
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from translator_worker import TranslatorWorker, TranslationConfig
from livekit import rtc

def setup_logging(level: str = "INFO"):
    """Configure logging for the application"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('translator_worker.log')
        ]
    )

def load_config() -> TranslationConfig:
    """Load configuration from environment variables"""
    return TranslationConfig(
        stt_model=os.getenv("STT_MODEL", "base"),
        chunk_duration_ms=int(os.getenv("CHUNK_DURATION_MS", "250")),
        context_length=int(os.getenv("CONTEXT_LENGTH", "512")),
        target_languages=os.getenv("TARGET_LANGUAGES", "es,fr,de,it,pt").split(","),
        voice_presets={
            "es": os.getenv("VOICE_ES", "es-female-1"),
            "fr": os.getenv("VOICE_FR", "fr-male-1"),
            "de": os.getenv("VOICE_DE", "de-female-1"),
            "it": os.getenv("VOICE_IT", "it-male-1"),
            "pt": os.getenv("VOICE_PT", "pt-female-1")
        }
    )

async def main():
    parser = argparse.ArgumentParser(description="Run LiveKit Translator Worker")
    parser.add_argument("--url", required=True, help="LiveKit server URL")
    parser.add_argument("--token", required=True, help="LiveKit access token")
    parser.add_argument("--room", required=True, help="Room name to join")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = load_config()
    logger.info(f"Loaded configuration: {config}")
    
    # Create and start translator worker
    worker = TranslatorWorker(config)
    
    try:
        logger.info(f"Connecting to room: {args.room} at {args.url}")
        await worker.connect_to_room(args.url, args.token, args.room)
        
        logger.info("Translator worker started successfully")
        logger.info("Waiting for participants and audio tracks...")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error running translator worker: {e}")
        raise
    finally:
        # Cleanup
        if worker.room:
            await worker.room.disconnect()
        logger.info("Translator worker stopped")

if __name__ == "__main__":
    # Load environment variables from .env file if it exists
    env_path = Path(__file__).parent.parent / "infra" / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    # Check required environment variables
    required_env_vars = [
        "STT_SERVICE_URL",
        "MT_SERVICE_URL", 
        "TTS_SERVICE_URL",
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_SECRET"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Error: Missing required environment variables: {missing_vars}")
        print(f"Please copy {env_path.parent}/.env.example to {env_path} and configure")
        sys.exit(1)
    
    asyncio.run(main())