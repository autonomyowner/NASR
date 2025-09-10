# The HIVE Translation System - Complete API Documentation

## 📋 Overview

This document provides comprehensive API documentation for all services in The HIVE real-time translation system. Each service exposes both HTTP REST APIs and WebSocket interfaces optimized for sub-500ms end-to-end latency.

## 🏗️ System Architecture

```
API Request Flow
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Auth Service   │    │   LiveKit SFU   │
│   React App     │───▶│   JWT Tokens     │───▶│   Room Access   │
│   Port: 5173    │    │   Port: 8004     │    │   Port: 7880    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   STT Service   │    │   MT Service     │    │   TTS Service   │
│   WebSocket     │    │   HTTP/WS        │    │   HTTP/WS       │
│   Port: 8001    │    │   Port: 8002     │    │   Port: 8003    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🛡️ Authentication & Authorization

### Auth Service API

**Base URL**: `http://localhost:8004` (development) | `https://api.yourdomain.com/auth` (production)

#### Generate Room Token
Create JWT token for LiveKit room access.

```http
POST /auth/token/room
Content-Type: application/json
Authorization: Bearer {API_KEY}

{
  "room_name": "conference-123",
  "participant_name": "user@example.com",
  "role": "speaker",                    // speaker, listener, moderator
  "metadata": {
    "user_id": "12345",
    "preferred_language": "en"
  },
  "ttl_hours": 2,                       // Token validity
  "allowed_languages": ["es", "fr", "de"]
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-01-01T12:00:00Z",
  "room_url": "wss://sfu.yourdomain.com",
  "participant_identity": "user@example.com",
  "permissions": {
    "can_publish": true,
    "can_subscribe": true,
    "can_translate": false
  }
}
```

#### Generate Translator Worker Token
Create token for translator worker participation.

```http
POST /auth/token/translator
Content-Type: application/json
Authorization: Bearer {API_KEY}

{
  "room_name": "conference-123",
  "worker_id": "translator-worker-001",
  "target_languages": ["es", "fr", "de"],
  "ttl_hours": 8
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-01-01T20:00:00Z",
  "worker_identity": "translator-worker-001",
  "permissions": {
    "can_publish": true,
    "can_subscribe": true,
    "can_translate": true,
    "can_record": false
  }
}
```

#### Generate TURN Credentials
Create credentials for CoTURN server access.

```http
POST /auth/credentials/turn
Content-Type: application/json
Authorization: Bearer {API_KEY}

{
  "room_name": "conference-123",
  "participant_name": "user@example.com",
  "ttl_seconds": 3600
}
```

**Response:**
```json
{
  "username": "1704110400:user@example.com",
  "credential": "generated_hmac_credential",
  "ttl": 3600,
  "uris": [
    "stun:turn.yourdomain.com:3478",
    "turn:turn.yourdomain.com:3478?transport=udp",
    "turns:turn.yourdomain.com:5349?transport=tcp"
  ]
}
```

#### Health Check
```http
GET /auth/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "dependencies": {
    "livekit": "healthy",
    "redis": "healthy",
    "coturn": "healthy"
  },
  "metrics": {
    "tokens_issued_24h": 1234,
    "active_sessions": 45
  }
}
```

---

## 🎤 Speech-to-Text (STT) Service API

**Base URL**: `http://localhost:8001` (development) | `https://stt.yourdomain.com` (production)

### Real-time WebSocket Streaming

#### WebSocket Endpoint
```
ws://localhost:8001/ws/stt
```

**Connection Parameters:**
```javascript
const params = {
  model_size: "base",           // tiny.en, base.en, small.en, medium.en
  language: "auto",             // auto-detect or specific language code
  enable_vad: true,             // Voice Activity Detection
  enable_timestamps: true,      // Word-level timestamps
  agreement_threshold: 2,       // LocalAgreement-2 threshold
  stability_window: 3,          // Stability analysis window
  chunk_duration_ms: 250        // Audio chunk processing size
}
```

**Audio Input Format:**
- **Sample Rate**: 16kHz
- **Channels**: Mono (1 channel)
- **Encoding**: 16-bit PCM
- **Chunk Size**: 250ms recommended (4000 bytes)

**Example WebSocket Client:**
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/stt');

ws.onopen = () => {
  console.log('STT WebSocket connected');
  // Send configuration
  ws.send(JSON.stringify({
    type: 'config',
    model_size: 'base.en',
    language: 'en',
    enable_vad: true
  }));
};

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  if (result.type === 'transcription') {
    console.log('Transcription:', result.text);
    console.log('Confidence:', result.confidence);
    console.log('Processing time:', result.processing_time_ms + 'ms');
  }
};

// Send audio chunks
function sendAudioChunk(audioBuffer) {
  ws.send(audioBuffer);  // Raw PCM bytes
}
```

**WebSocket Response Format:**
```json
{
  "type": "transcription",
  "text": "Hello, how are you today?",
  "confidence": 0.89,
  "language": "en",
  "is_partial": false,
  "words": [
    {
      "word": "Hello",
      "start": 0.0,
      "end": 0.4,
      "confidence": 0.95
    },
    {
      "word": "how",
      "start": 0.6,
      "end": 0.8,
      "confidence": 0.87
    }
  ],
  "processing_time_ms": 142.3,
  "model_version": "base.en",
  "chunk_id": "chunk_001",
  "timestamp": "2024-01-01T12:00:00.123Z"
}
```

### HTTP REST API

#### Batch Transcription
Process pre-recorded audio files.

```http
POST /transcribe
Content-Type: multipart/form-data

{
  "audio": <audio_file>,          // WAV, MP3, or FLAC file
  "model_size": "base.en",        // Optional
  "language": "auto",             // Optional
  "enable_timestamps": true,       // Optional
  "enable_vad": true              // Optional
}
```

**Response:**
```json
{
  "text": "Complete transcription of the audio file.",
  "confidence": 0.92,
  "language": "en", 
  "duration_seconds": 45.2,
  "processing_time_ms": 2341.7,
  "words": [
    {
      "word": "Complete",
      "start": 0.0,
      "end": 0.6,
      "confidence": 0.98
    }
  ],
  "metadata": {
    "model_version": "base.en",
    "sample_rate": 16000,
    "channels": 1
  }
}
```

#### Get Supported Languages
```http
GET /languages
```

**Response:**
```json
{
  "languages": [
    {
      "code": "en",
      "name": "English",
      "models": ["tiny.en", "base.en", "small.en"]
    },
    {
      "code": "es", 
      "name": "Spanish",
      "models": ["tiny", "base", "small"]
    }
  ],
  "default_model": "base.en"
}
```

#### Performance Metrics
```http
GET /performance
```

**Response:**
```json
{
  "processing_time_ms": {
    "p50": 134.5,
    "p95": 187.2,
    "p99": 243.1
  },
  "word_retraction_rate": 0.034,
  "confirmation_rate": 0.89,
  "active_sessions": 12,
  "chunks_processed_per_second": 45.2,
  "model_stats": {
    "base.en": {
      "accuracy": 0.94,
      "avg_confidence": 0.87
    }
  },
  "system_resources": {
    "gpu_utilization": 0.67,
    "memory_usage_mb": 2048,
    "cpu_usage": 0.45
  }
}
```

#### Service Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.2.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "models_loaded": ["base.en", "tiny.en"],
  "gpu_available": true,
  "dependencies": {
    "faster_whisper": "0.9.0",
    "torch": "2.1.0",
    "cuda_version": "11.8"
  },
  "uptime_seconds": 86400,
  "last_model_update": "2024-01-01T00:00:00Z"
}
```

---

## 🌐 Machine Translation (MT) Service API

**Base URL**: `http://localhost:8002` (development) | `https://mt.yourdomain.com` (production)

### Real-time WebSocket Streaming

#### WebSocket Endpoint
```
ws://localhost:8002/ws/translate
```

**Example WebSocket Client:**
```javascript
const ws = new WebSocket('ws://localhost:8002/ws/translate');

ws.onopen = () => {
  console.log('MT WebSocket connected');
};

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  console.log('Translation:', result.text);
  console.log('Confidence:', result.confidence);
  console.log('Processing time:', result.processing_time_ms + 'ms');
};

// Send translation request
const translationRequest = {
  text: "Hello, how are you today?",
  source_language: "en",
  target_language: "es",
  is_partial: false,
  sequence_id: "utterance_123",
  context: "Previous conversation context..."
};

ws.send(JSON.stringify(translationRequest));
```

**Request Format:**
```json
{
  "text": "Hello, how are you today?",
  "source_language": "en",
  "target_language": "es",
  "is_partial": false,
  "sequence_id": "utterance_123",
  "context": "Previous conversation context...",
  "enable_context": true,
  "max_alternatives": 3
}
```

**WebSocket Response Format:**
```json
{
  "text": "Hola, ¿cómo estás hoy?",
  "confidence": 0.92,
  "source_language": "en",
  "target_language": "es",
  "processing_time_ms": 45.2,
  "model_used": "marian-en-es-optimized",
  "context_used": true,
  "is_partial": false,
  "sequence_id": "utterance_123",
  "alternatives": [
    "Hola, ¿cómo te encuentras hoy?",
    "Hola, ¿qué tal estás hoy?"
  ],
  "quality_metrics": {
    "length_ratio": 1.1,
    "repetition_score": 0.05,
    "semantic_similarity": 0.89
  },
  "timestamp": "2024-01-01T12:00:00.123Z"
}
```

### HTTP REST API

#### Single Translation
```http
POST /translate
Content-Type: application/json

{
  "text": "Hello, how are you today?",
  "source_language": "en",
  "target_language": "es",
  "context": "Previous conversation...",
  "enable_context": true,
  "max_alternatives": 2
}
```

**Response:**
```json
{
  "text": "Hola, ¿cómo estás hoy?",
  "confidence": 0.92,
  "source_language": "en",
  "target_language": "es", 
  "processing_time_ms": 45.2,
  "model_used": "marian-en-es-optimized",
  "context_used": true,
  "alternatives": [
    "Hola, ¿cómo te encuentras hoy?"
  ],
  "quality_metrics": {
    "bleu_score": 0.89,
    "confidence_distribution": {
      "high": 0.7,
      "medium": 0.25,
      "low": 0.05
    }
  }
}
```

#### Batch Translation
```http
POST /translate/batch
Content-Type: application/json

{
  "texts": [
    "Hello world",
    "How are you?",
    "Good morning"
  ],
  "source_language": "en",
  "target_language": "es",
  "context": "Greeting conversation",
  "preserve_order": true
}
```

**Response:**
```json
{
  "translations": [
    {
      "text": "Hola mundo",
      "confidence": 0.95,
      "processing_time_ms": 23.1
    },
    {
      "text": "¿Cómo estás?", 
      "confidence": 0.91,
      "processing_time_ms": 28.4
    },
    {
      "text": "Buenos días",
      "confidence": 0.97,
      "processing_time_ms": 21.8
    }
  ],
  "total_processing_time_ms": 73.3,
  "batch_size": 3,
  "model_used": "marian-en-es-optimized"
}
```

#### Language Detection
```http
POST /detect
Content-Type: application/json

{
  "text": "Bonjour, comment allez-vous?"
}
```

**Response:**
```json
{
  "detected_language": "fr",
  "confidence": 0.98,
  "alternatives": [
    {
      "language": "fr",
      "confidence": 0.98
    },
    {
      "language": "it",
      "confidence": 0.02
    }
  ],
  "processing_time_ms": 12.3
}
```

#### Supported Language Pairs
```http
GET /languages
```

**Response:**
```json
{
  "language_pairs": [
    {
      "source": "en",
      "target": "es", 
      "model": "marian-en-es-optimized",
      "bleu_score": 34.2,
      "avg_latency_ms": 32
    },
    {
      "source": "en",
      "target": "fr",
      "model": "marian-en-fr-optimized", 
      "bleu_score": 31.8,
      "avg_latency_ms": 28
    }
  ],
  "total_pairs": 16,
  "supported_languages": ["en", "es", "fr", "de", "it", "pt", "nl", "ru"]
}
```

#### Performance Metrics
```http
GET /performance
```

**Response:**
```json
{
  "translation_time_ms": {
    "p50": 28.5,
    "p95": 67.2,
    "p99": 89.1
  },
  "confidence_distribution": {
    "high_confidence": 0.78,
    "medium_confidence": 0.18,
    "low_confidence": 0.04
  },
  "throughput": {
    "requests_per_second": 45.2,
    "tokens_per_second": 890.5
  },
  "active_sessions": 8,
  "cache_hit_rate": 0.23,
  "language_pair_usage": {
    "en-es": 0.45,
    "en-fr": 0.23,
    "en-de": 0.18,
    "other": 0.14
  },
  "system_resources": {
    "gpu_utilization": 0.52,
    "memory_usage_mb": 3072,
    "cpu_usage": 0.38
  }
}
```

---

## 🎵 Text-to-Speech (TTS) Service API

**Base URL**: `http://localhost:8003` (development) | `https://tts.yourdomain.com` (production)

### Real-time WebSocket Streaming

#### WebSocket Endpoint
```
ws://localhost:8003/ws/synthesize
```

**Example WebSocket Client:**
```javascript
const ws = new WebSocket('ws://localhost:8003/ws/synthesize');

ws.onopen = () => {
  console.log('TTS WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'audio_chunk') {
    // Handle streaming audio chunk
    const audioBytes = base64ToBytes(data.audio_chunk);
    // Feed to audio output or LiveKit track
  } else if (data.type === 'synthesis_complete') {
    console.log('Synthesis completed in', data.processing_time_ms + 'ms');
  }
};

// Send synthesis request
const synthRequest = {
  text: "Hola, ¿cómo estás hoy?",
  voice_id: "es-female-premium",
  language: "es",
  engine: "xtts",
  stream: true,
  audio_format: "wav",
  sample_rate: 16000
};

ws.send(JSON.stringify(synthRequest));
```

**Request Format:**
```json
{
  "text": "Hola, ¿cómo estás hoy?",
  "voice_id": "es-female-premium", 
  "language": "es",
  "engine": "xtts",
  "stream": true,
  "audio_format": "wav",
  "sample_rate": 16000,
  "speaking_rate": 1.0,
  "pitch": 0.0,
  "volume_gain_db": 0.0
}
```

**WebSocket Response - Audio Chunk:**
```json
{
  "type": "audio_chunk",
  "audio_chunk": "UklGRlYAAABXQVZFZm10IBAA...",  // Base64 encoded audio
  "chunk_index": 0,
  "chunk_size_bytes": 1024,
  "sample_rate": 16000,
  "is_final": false,
  "timestamp": "2024-01-01T12:00:00.123Z"
}
```

**WebSocket Response - Completion:**
```json
{
  "type": "synthesis_complete",
  "text_length": 24,
  "audio_duration_ms": 2150.0,
  "processing_time_ms": 234.7,
  "ttft_ms": 187.2,
  "voice_id": "es-female-premium",
  "engine": "xtts",
  "total_chunks": 5,
  "quality_score": 4.2
}
```

### HTTP REST API

#### Single Synthesis
```http
POST /synthesize
Content-Type: application/json

{
  "text": "Hello, welcome to The HIVE translation system!",
  "voice_id": "en-us-female-premium",
  "language": "en",
  "engine": "xtts",
  "audio_format": "wav",
  "sample_rate": 16000,
  "speaking_rate": 1.0,
  "pitch": 0.0,
  "volume_gain_db": 0.0
}
```

**Response:**
```json
{
  "audio_data": "UklGRlYAAABXQVZFZm10IBAA...",  // Base64 encoded audio
  "text_length": 47,
  "audio_duration_ms": 3250.0,
  "processing_time_ms": 287.4,
  "ttft_ms": 198.7,
  "voice_id": "en-us-female-premium",
  "engine": "xtts",
  "sample_rate": 16000,
  "channels": 1,
  "quality_score": 4.3,
  "metadata": {
    "text_normalized": "Hello, welcome to The HIVE translation system!",
    "phonemes": "həˈloʊ, ˈwɛlkəm tu ðə haɪv trænzˈleɪʃən ˈsɪstəm!",
    "prosody_applied": true
  }
}
```

#### Voice Cloning
```http
POST /voices/clone
Content-Type: multipart/form-data

{
  "reference_audio": <audio_file>,     // 3-10 seconds of reference speech
  "voice_name": "custom-voice-001",
  "language": "en",
  "description": "Professional male voice"
}
```

**Response:**
```json
{
  "voice_id": "custom-voice-001",
  "status": "processing",
  "estimated_completion_seconds": 120,
  "quality_preview_url": "/voices/custom-voice-001/preview",
  "clone_job_id": "job_12345"
}
```

#### Check Voice Clone Status
```http
GET /voices/clone/{job_id}
```

**Response:**
```json
{
  "job_id": "job_12345", 
  "status": "completed",
  "voice_id": "custom-voice-001",
  "quality_score": 4.1,
  "processing_time_seconds": 98.3,
  "preview_audio": "UklGRlYAAABXQVZFZm10IBAA...",
  "created_at": "2024-01-01T12:00:00Z",
  "metadata": {
    "reference_duration_seconds": 7.2,
    "training_iterations": 500,
    "similarity_score": 0.89
  }
}
```

#### Available Voices
```http
GET /voices
GET /voices?language=es&gender=female&quality=premium
```

**Response:**
```json
{
  "voices": [
    {
      "voice_id": "es-female-premium",
      "name": "Sofia Premium",
      "language": "es",
      "gender": "female", 
      "age": "adult",
      "style": "conversational",
      "quality_tier": "premium",
      "supported_engines": ["xtts", "speecht5"],
      "sample_url": "/voices/es-female-premium/sample",
      "accent": "mexican",
      "description": "Warm, professional female voice"
    },
    {
      "voice_id": "en-us-male-fast",
      "name": "David Fast", 
      "language": "en-US",
      "gender": "male",
      "age": "adult",
      "style": "neutral",
      "quality_tier": "standard",
      "supported_engines": ["piper", "speecht5"],
      "sample_url": "/voices/en-us-male-fast/sample",
      "accent": "general_american",
      "description": "Clear, fast synthesis voice"
    }
  ],
  "total_voices": 47,
  "engines": {
    "xtts": {
      "quality": "premium",
      "ttft_ms": 200,
      "supports_cloning": true
    },
    "piper": {
      "quality": "standard", 
      "ttft_ms": 100,
      "supports_cloning": false
    }
  }
}
```

#### Performance Metrics
```http
GET /performance
```

**Response:**
```json
{
  "synthesis_time_ms": {
    "p50": 198.5,
    "p95": 387.2,
    "p99": 567.8
  },
  "ttft_ms": {
    "p50": 143.2,
    "p95": 234.7,
    "p99": 298.1
  },
  "audio_quality_scores": {
    "mean": 4.2,
    "by_engine": {
      "xtts": 4.4,
      "piper": 3.9,
      "speecht5": 4.1
    }
  },
  "throughput": {
    "requests_per_second": 28.5,
    "characters_per_second": 450.2
  },
  "active_sessions": 15,
  "voice_usage": {
    "es-female-premium": 0.32,
    "en-us-male-1": 0.28,
    "fr-female-1": 0.15,
    "other": 0.25
  },
  "engine_performance": {
    "xtts": {
      "avg_ttft_ms": 201.3,
      "quality_score": 4.4,
      "active_sessions": 8
    },
    "piper": {
      "avg_ttft_ms": 98.7,
      "quality_score": 3.9, 
      "active_sessions": 5
    }
  },
  "system_resources": {
    "gpu_utilization": 0.71,
    "memory_usage_mb": 4096,
    "cpu_usage": 0.55
  }
}
```

### **File**: `backend/services/stt_client.py`

```python
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import asyncio
import numpy as np
import aiohttp

@dataclass
class STTResult:
    """Speech-to-text result with metadata"""
    text: str
    confidence: float
    detected_language: str
    word_timestamps: List[Dict[str, Any]]
    processing_time_ms: float
    model_version: str

@dataclass  
class STTConfig:
    """Configuration for STT service"""
    model_size: str = "base"  # whisper model: tiny, base, small, medium, large
    language: str = "auto"    # auto-detect or specific language code
    enable_vad: bool = True   # Voice Activity Detection
    enable_timestamps: bool = True
    temperature: float = 0.0  # Sampling temperature for Whisper
    compression_ratio_threshold: float = 2.4
    logprob_threshold: float = -1.0
    no_speech_threshold: float = 0.6

class STTClient:
    """Async client for Speech-to-Text service"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8001",
                 config: Optional[STTConfig] = None,
                 max_concurrent: int = 4,
                 timeout: float = 5.0):
        self.base_url = base_url
        self.config = config or STTConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def transcribe(self,
                        audio_data: np.ndarray,
                        sample_rate: int = 16000,
                        language: Optional[str] = None) -> STTResult:
        """
        Transcribe audio data to text
        
        Target SLO: <200ms for 250ms audio chunks
        """
        async with self.semaphore:
            # Implementation handles:
            # 1. Audio preprocessing (resampling, normalization)
            # 2. VAD for silence detection
            # 3. Whisper inference with LocalAgreement-2 stabilization
            # 4. Confidence scoring and language detection
            pass
            
    async def transcribe_streaming(self,
                                 audio_stream: asyncio.Queue,
                                 chunk_duration_ms: int = 250) -> asyncio.AsyncGenerator[STTResult, None]:
        """
        Stream transcription with real-time processing
        
        Yields partial results with LocalAgreement-2 stabilization
        """
        # Implementation handles:
        # 1. Streaming audio buffer management  
        # 2. Incremental transcription with context
        # 3. Text stabilization using LocalAgreement-2
        # 4. Real-time result streaming
        pass
        
    async def health_check(self) -> bool:
        """Check if STT service is healthy"""
        pass

    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        pass
        
    async def warm_up_model(self, model_size: str = "base") -> bool:
        """Pre-load model for faster first inference"""
        pass
```

### **Key Features**:
- **VAD Integration**: Reduces processing of silence
- **LocalAgreement-2**: Text stabilization for streaming
- **Model Warm-up**: Pre-loading for consistent latency
- **Concurrent Processing**: Semaphore-controlled parallelism

---

## 🌐 MT Client SDK Specification  

### **File**: `backend/services/mt_client.py`

```python
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import asyncio
import aiohttp

@dataclass
class TranslationResult:
    """Machine translation result with metadata"""
    text: str
    confidence: float
    source_language: str
    target_language: str
    processing_time_ms: float
    model_name: str
    context_used: bool
    alternatives: List[str]

@dataclass
class MTConfig:
    """Configuration for MT service"""
    primary_model: str = "opus-mt"  # Primary translation model
    fallback_model: str = "google-translate"  # Fallback for failures
    context_window: int = 512  # Context length in tokens
    enable_context: bool = True
    confidence_threshold: float = 0.7
    max_alternatives: int = 3
    cache_translations: bool = True

class MTClient:
    """Async client for Machine Translation service"""
    
    def __init__(self,
                 base_url: str = "http://localhost:8002", 
                 config: Optional[MTConfig] = None,
                 max_concurrent: int = 8,
                 timeout: float = 2.0):
        self.base_url = base_url
        self.config = config or MTConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.translation_cache: Dict[str, TranslationResult] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def translate(self,
                       text: str,
                       source_language: str,
                       target_language: str,
                       context: Optional[str] = None) -> TranslationResult:
        """
        Translate text with optional context
        
        Target SLO: <100ms with context awareness
        """
        async with self.semaphore:
            # Implementation handles:
            # 1. Cache lookup for repeated translations
            # 2. Context-aware translation with conversation history
            # 3. Primary model with fallback on failure
            # 4. Quality scoring and alternative generation
            pass
            
    async def translate_batch(self,
                             texts: List[str],
                             source_language: str,
                             target_language: str,
                             context: Optional[str] = None) -> List[TranslationResult]:
        """
        Batch translate multiple texts efficiently
        """
        # Implementation handles:
        # 1. Batch API optimization for throughput
        # 2. Parallel processing with shared context
        # 3. Result ordering and error handling
        pass
        
    async def get_supported_languages(self) -> Dict[str, List[str]]:
        """Get supported language pairs"""
        pass
        
    async def detect_language(self, text: str) -> Dict[str, float]:
        """Detect source language with confidence scores"""
        pass
        
    async def health_check(self) -> bool:
        """Check if MT service is healthy"""
        pass
        
    async def warm_up_models(self, language_pairs: List[tuple]) -> bool:
        """Pre-load models for specified language pairs"""
        pass
        
    def clear_cache(self):
        """Clear translation cache"""
        self.translation_cache.clear()
```

### **Key Features**:
- **Context Awareness**: Rolling conversation context
- **Caching**: Intelligent caching for repeated phrases  
- **Fallback Models**: Graceful degradation on failures
- **Batch Processing**: Optimized for multiple translations

---

## 🎵 TTS Client SDK Specification

### **File**: `backend/services/tts_client.py`

```python
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
import asyncio
import numpy as np
import aiohttp

@dataclass  
class TTSResult:
    """Text-to-speech result with metadata"""
    audio_data: np.ndarray
    sample_rate: int
    duration_ms: float
    processing_time_ms: float
    voice_id: str
    language: str
    text_length: int

@dataclass
class VoicePreset:
    """Voice configuration preset"""
    voice_id: str
    name: str
    language: str
    gender: str
    age: str
    style: str
    sample_url: str

@dataclass
class TTSConfig:
    """Configuration for TTS service"""
    default_voice: str = "neural-voice-1"
    sample_rate: int = 16000  # Match LiveKit audio requirements
    audio_format: str = "wav"
    speaking_rate: float = 1.0
    pitch: float = 0.0  # Semitones adjustment
    volume_gain_db: float = 0.0
    enable_streaming: bool = True
    chunk_size: int = 1024  # Audio chunk size for streaming

class TTSClient:
    """Async client for Text-to-Speech service"""
    
    def __init__(self,
                 base_url: str = "http://localhost:8003",
                 config: Optional[TTSConfig] = None, 
                 max_concurrent: int = 6,
                 timeout: float = 3.0):
        self.base_url = base_url  
        self.config = config or TTSConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.voice_cache: Dict[str, VoicePreset] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def synthesize(self,
                        text: str,
                        voice_id: str,
                        language: str) -> TTSResult:
        """
        Synthesize text to speech
        
        Target SLO: <150ms with voice consistency
        """
        async with self.semaphore:
            # Implementation handles:
            # 1. Text preprocessing (SSML, normalization)
            # 2. Voice model selection and caching
            # 3. Neural voice synthesis 
            # 4. Audio post-processing (format, sample rate)
            pass
            
    async def synthesize_streaming(self,
                                  text: str, 
                                  voice_id: str,
                                  language: str) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesis for real-time playback
        
        Yields audio chunks as soon as they're generated
        """
        # Implementation handles:
        # 1. Streaming synthesis with early audio frames
        # 2. Real-time audio chunk delivery
        # 3. Buffer management for smooth playback
        pass
        
    async def get_available_voices(self, 
                                  language: Optional[str] = None) -> List[VoicePreset]:
        """Get available voices, optionally filtered by language"""
        pass
        
    async def clone_voice(self,
                         reference_audio: np.ndarray,
                         voice_name: str) -> str:
        """
        Clone voice from reference audio (if supported)
        
        Returns voice_id for cloned voice
        """
        pass
        
    async def health_check(self) -> bool:
        """Check if TTS service is healthy"""
        pass
        
    async def warm_up_voice(self, voice_id: str) -> bool:
        """Pre-load voice model for faster synthesis"""
        pass
        
    async def estimate_duration(self, text: str, voice_id: str) -> float:
        """Estimate audio duration without synthesis"""
        pass
```

### **Key Features**:
- **Streaming Synthesis**: Real-time audio generation
- **Voice Consistency**: Persistent voice characteristics
- **Format Optimization**: LiveKit-compatible audio output
- **Voice Cloning**: Custom voice generation (optional)

---

## 🔍 Observability Integration

### **Tracing Integration**: `backend/observability/tracer.py`

```python
from typing import Dict, Any, Optional
import time
import logging
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter  
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

class TranslationTracer:
    """Distributed tracing for translation pipeline"""
    
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
        self.active_traces: Dict[str, Any] = {}
        
    def start_trace(self, trace_id: str, context: Dict[str, Any]):
        """Start new trace for translation request"""
        span = self.tracer.start_span(f"translation_pipeline_{trace_id}")
        span.set_attributes(context)
        self.active_traces[trace_id] = span
        
    def add_span(self, trace_id: str, operation: str, 
                start_time: float, duration_ms: float,
                attributes: Dict[str, Any]):
        """Add span for specific operation"""
        if trace_id in self.active_traces:
            with self.tracer.start_span(operation) as span:
                span.set_attributes(attributes)
                span.set_attribute("duration_ms", duration_ms)
                span.set_attribute("start_time", start_time)
                
    def complete_trace(self, trace_id: str, final_attributes: Dict[str, Any]):
        """Complete trace with final metrics"""
        if trace_id in self.active_traces:
            span = self.active_traces[trace_id]
            span.set_attributes(final_attributes)
            span.end()
            del self.active_traces[trace_id]
            
    def add_error(self, trace_id: str, error: str):
        """Add error to trace"""
        if trace_id in self.active_traces:
            span = self.active_traces[trace_id]
            span.set_status(trace.Status(trace.StatusCode.ERROR, error))
```

---

## 📊 Performance Requirements

### **SLO Targets Per Service**:

| Service | Target Latency | Max Concurrent | Throughput |
|---------|---------------|----------------|------------|
| STT     | <200ms        | 4 connections  | 20 req/sec |
| MT      | <100ms        | 8 connections  | 50 req/sec |
| TTS     | <150ms        | 6 connections  | 30 req/sec |

### **Error Handling**:
- **Retry Logic**: Exponential backoff with jitter
- **Circuit Breaker**: Automatic service degradation
- **Fallback**: Graceful service degradation
- **Health Checks**: Continuous service monitoring

### **Connection Management**:
- **Connection Pooling**: Persistent HTTP connections
- **Keep-Alive**: Long-lived connections for performance
- **Timeout Handling**: Progressive timeout strategies
- **Resource Cleanup**: Proper session management

---

## 🔧 Implementation Priority

### **Phase 1**: Core Client Implementation (Days 1-2)
1. Basic async HTTP clients with connection pooling
2. Request/response data structures  
3. Error handling and retry logic
4. Health check endpoints

### **Phase 2**: Advanced Features (Days 3-4)
1. Streaming interfaces for real-time processing
2. Caching and optimization features
3. Observability integration (tracing, metrics)
4. Load balancing and failover

### **Phase 3**: Integration & Testing (Days 5-6)
1. Integration with translator worker
2. Performance optimization and SLO validation
3. Comprehensive test suite
4. Documentation and examples

This specification provides the foundation for implementing high-performance, production-ready service clients that meet the ambitious SLO targets while maintaining system reliability and observability.