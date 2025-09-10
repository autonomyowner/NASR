"""
STT Service Package
Real-time streaming Speech-to-Text with LocalAgreement-2 stabilization
"""

__version__ = "1.0.0"
__author__ = "The HIVE Translation Team"

from .app import app, STTConfig, STTSession
from .local_agreement import LocalAgreement2
from .audio_processor import AudioProcessor, AudioChunk
from .performance_monitor import PerformanceMonitor

__all__ = [
    "app",
    "STTConfig", 
    "STTSession",
    "LocalAgreement2",
    "AudioProcessor",
    "AudioChunk", 
    "PerformanceMonitor"
]