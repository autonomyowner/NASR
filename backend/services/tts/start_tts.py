#!/usr/bin/env python3
"""
TTS Service Startup Script
Production-ready startup with configuration validation and health checks
"""

import os
import sys
import time
import asyncio
import logging
import argparse
import yaml
from pathlib import Path
import torch
import psutil
import subprocess

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, tts_service
import uvicorn

logger = logging.getLogger(__name__)

class TTSServiceBootstrap:
    """Bootstrap and startup management for TTS service"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded configuration from {self.config_path}")
                    return config
            else:
                logger.warning(f"Config file {self.config_path} not found, using defaults")
                return self.default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.default_config()
    
    def default_config(self) -> dict:
        """Default configuration"""
        return {
            "service": {
                "host": "0.0.0.0",
                "port": 8003,
                "workers": 1
            },
            "performance": {
                "target_ttft_ms": 250
            }
        }
    
    def validate_system_requirements(self) -> bool:
        """Validate system requirements"""
        logger.info("Validating system requirements...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            logger.error("Python 3.8+ required")
            return False
        
        # Check available memory
        memory_gb = psutil.virtual_memory().total / (1024**3)
        if memory_gb < 4:
            logger.warning(f"Low memory: {memory_gb:.1f}GB (recommended: 8GB+)")
        else:
            logger.info(f"Memory: {memory_gb:.1f}GB")
        
        # Check GPU availability
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                logger.info(f"GPU {i}: {gpu_name} ({gpu_memory:.1f}GB)")
        else:
            logger.warning("No CUDA GPUs available, using CPU mode")
        
        # Check disk space
        disk_free = psutil.disk_usage('/').free / (1024**3)
        if disk_free < 10:
            logger.warning(f"Low disk space: {disk_free:.1f}GB")
        else:
            logger.info(f"Disk space: {disk_free:.1f}GB available")
        
        return True
    
    def setup_logging(self, level: str = "INFO"):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('tts_service.log')
            ]
        )
        
        # Reduce noise from some libraries
        logging.getLogger('transformers').setLevel(logging.WARNING)
        logging.getLogger('torch').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        logger.info(f"Logging configured at {level} level")
    
    async def warmup_models(self):
        """Warm up TTS models"""
        logger.info("Starting model warmup...")
        
        try:
            # Initialize the service
            await tts_service.initialize()
            
            # Warm up each engine with a test synthesis
            warmup_text = "System initialization test."
            
            for engine_name, engine in tts_service.engines.items():
                try:
                    logger.info(f"Warming up {engine_name.value} engine...")
                    
                    # Quick test synthesis
                    async for result in tts_service.synthesize_streaming({
                        "text": warmup_text,
                        "voice_id": "en-us-female-premium",
                        "language": "en",
                        "engine": engine_name,
                        "stream": True
                    }):
                        if result.is_final:
                            logger.info(f"✓ {engine_name.value} engine ready")
                            break
                            
                except Exception as e:
                    logger.warning(f"Failed to warm up {engine_name.value}: {e}")
            
            logger.info("Model warmup completed")
            
        except Exception as e:
            logger.error(f"Model warmup failed: {e}")
            raise
    
    def check_dependencies(self) -> bool:
        """Check required dependencies"""
        logger.info("Checking dependencies...")
        
        required_packages = [
            "fastapi",
            "uvicorn", 
            "torch",
            "transformers",
            "soundfile",
            "librosa",
            "websockets"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                logger.debug(f"✓ {package}")
            except ImportError:
                missing_packages.append(package)
                logger.error(f"✗ {package}")
        
        if missing_packages:
            logger.error(f"Missing required packages: {missing_packages}")
            logger.error("Install with: pip install -r requirements.txt")
            return False
        
        logger.info("All dependencies satisfied")
        return True
    
    async def health_check_loop(self, interval: int = 30):
        """Continuous health monitoring"""
        while True:
            try:
                # Check GPU memory if available
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_allocated() / (1024**3)
                    if gpu_memory > 6:  # >6GB usage warning
                        logger.warning(f"High GPU memory usage: {gpu_memory:.1f}GB")
                
                # Check system memory
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 85:
                    logger.warning(f"High memory usage: {memory_percent:.1f}%")
                
                # Check active sessions
                active_sessions = len(tts_service.active_sessions)
                if active_sessions > 50:
                    logger.warning(f"High session count: {active_sessions}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(interval)
    
    def start_service(self, dev_mode: bool = False):
        """Start the TTS service"""
        config = self.config.get("service", {})
        
        uvicorn_config = {
            "app": app,
            "host": config.get("host", "0.0.0.0"),
            "port": config.get("port", 8003),
            "log_level": "info",
            "access_log": True,
        }
        
        if dev_mode:
            uvicorn_config.update({
                "reload": True,
                "reload_dirs": ["."],
                "log_level": "debug"
            })
        else:
            uvicorn_config.update({
                "workers": config.get("workers", 1),
                "loop": "uvloop",
                "http": "httptools"
            })
        
        logger.info(f"Starting TTS service on {uvicorn_config['host']}:{uvicorn_config['port']}")
        uvicorn.run(**uvicorn_config)

async def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description="TTS Service Startup")
    parser.add_argument("--config", default="config.yaml", help="Configuration file")
    parser.add_argument("--dev", action="store_true", help="Development mode")
    parser.add_argument("--no-warmup", action="store_true", help="Skip model warmup")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--validate-only", action="store_true", help="Validate and exit")
    
    args = parser.parse_args()
    
    # Initialize bootstrap
    bootstrap = TTSServiceBootstrap(args.config)
    bootstrap.setup_logging(args.log_level)
    
    logger.info("Starting TTS Service Bootstrap")
    logger.info(f"Python {sys.version}")
    logger.info(f"PyTorch {torch.__version__}")
    
    # Validate system
    if not bootstrap.validate_system_requirements():
        logger.error("System requirements not met")
        sys.exit(1)
    
    # Check dependencies
    if not bootstrap.check_dependencies():
        logger.error("Dependency check failed")
        sys.exit(1)
    
    if args.validate_only:
        logger.info("Validation completed successfully")
        return
    
    # Model warmup
    if not args.no_warmup:
        try:
            await bootstrap.warmup_models()
        except Exception as e:
            logger.error(f"Warmup failed: {e}")
            if not args.dev:
                sys.exit(1)
    
    # Start health monitoring in background
    if not args.dev:
        asyncio.create_task(bootstrap.health_check_loop())
    
    # Start the service
    logger.info("TTS Service ready to start")
    bootstrap.start_service(args.dev)

if __name__ == "__main__":
    asyncio.run(main())