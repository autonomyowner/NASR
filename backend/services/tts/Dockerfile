# The HIVE TTS Service Container
# GPU-optimized container for streaming text-to-speech synthesis

FROM nvidia/cuda:12.1-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    libasound-dev \
    portaudio19-dev \
    espeak \
    espeak-data \
    libespeak-dev \
    festival \
    flite \
    sox \
    libffi-dev \
    libssl-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir -r requirements.txt

# Download and cache TTS models
RUN python3 -c "
import torch
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
print('Downloading SpeechT5 models...')
SpeechT5Processor.from_pretrained('microsoft/speecht5_tts')
SpeechT5ForTextToSpeech.from_pretrained('microsoft/speecht5_tts') 
SpeechT5HifiGan.from_pretrained('microsoft/speecht5_hifigan')
print('Models downloaded successfully')
"

# Install XTTS models (if available)
RUN python3 -c "
try:
    from TTS.api import TTS
    print('Downloading XTTS models...')
    tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=False)
    print('XTTS models downloaded successfully')
except Exception as e:
    print(f'XTTS download failed: {e}')
"

# Create directories for models and voices
RUN mkdir -p /app/models /app/voices /app/cache

# Copy application code
COPY . .

# Set proper permissions
RUN chmod +x /app/app.py

# Create non-root user for security
RUN groupadd -r tts && useradd -r -g tts tts
RUN chown -R tts:tts /app
USER tts

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Command to run the application
CMD ["python3", "app.py"]