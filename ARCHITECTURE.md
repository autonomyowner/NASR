# The HIVE Translation System - Architecture Documentation

## System Architecture Overview

The HIVE is a production-grade dual-purpose platform combining a professional speaking club website with an advanced real-time voice translation system. The architecture is designed for sub-500ms end-to-end translation latency while maintaining high availability and scalability.

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           The HIVE Translation System                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────────┐ │
│  │   Frontend      │    │   Load Balancer  │    │   Backend Services          │ │
│  │   React App     │───▶│   nginx/HAProxy  │───▶│   Translation Pipeline      │ │
│  │   Port: 5173    │    │   SSL/TLS Term   │    │   STT → MT → TTS            │ │
│  └─────────────────┘    └──────────────────┘    └─────────────────────────────┘ │
│           │                        │                          │                 │
│           ▼                        ▼                          ▼                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────────┐ │
│  │ WebRTC Signaling│    │   Auth Service   │    │   LiveKit SFU               │ │
│  │ WebSocket Server│    │   JWT + TURN     │    │   WebRTC Router             │ │
│  │   Port: 3001    │    │   Port: 8004     │    │   Port: 7880                │ │
│  └─────────────────┘    └──────────────────┘    └─────────────────────────────┘ │
│                                   │                          │                 │
│                                   ▼                          ▼                 │
│                        ┌──────────────────┐    ┌─────────────────────────────┐ │
│                        │   CoTURN Server  │    │   Translator Workers       │ │
│                        │   STUN/TURN      │    │   LiveKit Participants     │ │
│                        │   Port: 3478     │    │   STT→MT→TTS Pipeline      │ │
│                        └──────────────────┘    └─────────────────────────────┘ │
│                                                           │                     │
│                                                           ▼                     │
│                                                 ┌─────────────────────────────┐ │
│                                                 │   Observability Stack      │ │
│                                                 │   Prometheus + Grafana     │ │
│                                                 │   Jaeger + Health Monitor  │ │
│                                                 └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🌐 Frontend Architecture

### Component Hierarchy

```
App.tsx
├── Navbar.tsx                    # Navigation and theme switching
├── Home.tsx                      # Speaking club homepage
│   ├── Hero.tsx                  # Main hero section with stats
│   ├── About.tsx                 # Mission and vision
│   ├── Services.tsx              # Service offerings
│   ├── OfferForYou.tsx          # Value propositions
│   ├── Locations.tsx            # Physical locations
│   └── Contact.tsx               # Contact and registration
├── Call.tsx (845 lines)          # Main translation interface
│   ├── AudioSetupPanel.tsx       # Mic/camera setup
│   │   ├── DeviceSelector.tsx    # Device selection
│   │   ├── MicTest.tsx          # Microphone testing
│   │   └── AudioSettings.tsx     # Audio configuration
│   ├── WebRTCDebug.tsx          # Connection diagnostics
│   ├── RecordingControls.tsx     # Session recording
│   ├── AccessibilityControls.tsx # A11y features
│   ├── RNNoiseSettings.tsx       # Noise suppression
│   ├── TURNSettings.tsx          # Network configuration
│   └── translation/              # Translation-specific UI
│       ├── TranslationSettingsPanel.tsx
│       ├── TranslatedAudioSelector.tsx
│       ├── CaptionsView.tsx
│       └── PushToTranslateButton.tsx
└── Footer.tsx                    # Site footer
```

### Hook Architecture

```
Core Hooks (17 total)
├── WebRTC & Communication
│   ├── useWebRTC.ts (328 lines)     # Main WebRTC functionality
│   ├── usePeerConnection.ts         # Peer-to-peer connections
│   ├── useIncomingCall.ts          # Call handling
│   ├── useWebRTCStats.ts           # Connection statistics
│   └── useTURNConfig.ts            # TURN server management
├── Audio Processing
│   ├── useAudioSettings.ts         # Audio configuration
│   ├── useDeviceSelection.ts       # Camera/mic selection
│   ├── useVolumeControls.ts        # Volume management
│   ├── useRNNoise.ts               # AI noise suppression
│   ├── useMicTest.ts               # Microphone testing
│   └── useRecording.ts             # Session recording
├── Translation Features
│   ├── useTranslatedSpeech.ts      # Main translation hook
│   ├── useTranslationState.ts      # Translation state management
│   ├── useTranslationKeyboardShortcuts.ts # Keyboard controls
│   └── useSpeechRecognition.ts     # Speech recognition
├── User Experience
│   ├── useNotifications.ts         # System notifications
│   ├── useKeyboardShortcuts.ts     # Global shortcuts
│   ├── useCallHistory.ts          # Call history management
│   ├── useCallQuality.ts          # Quality assessment
│   └── useLanguagePreferences.ts   # Language settings
```

### State Management

**Context Providers:**
- `CallContext`: WebRTC call state and participant management
- `TranslationContext`: Translation settings and language preferences
- `AudioContext`: Audio device and processing state
- `NotificationContext`: System notifications and alerts

**Local State Strategy:**
- Component-specific state using `useState`
- Complex state logic in custom hooks
- Shared state through React Context
- Persistent preferences in localStorage

### Data Flow

```
User Interaction
       ↓
Component Event Handler
       ↓
Custom Hook (useWebRTC, useTranslation, etc.)
       ↓
Service Layer (signalingService, translationService)
       ↓ 
WebSocket/HTTP API Call
       ↓
Backend Services
       ↓
State Update (React Context)
       ↓
Component Re-render
       ↓
UI Update
```

## 🎙️ Backend Translation Pipeline

### Service Architecture

```
Translation Request Flow
┌─────────────────┐
│   Audio Input   │ 16kHz PCM, 250ms chunks
│   (WebRTC)      │
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Translator      │ LiveKit participant that:
│ Worker          │ 1. Subscribes to audio tracks
│ (Python)        │ 2. Processes through pipeline
│                 │ 3. Publishes translated tracks
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ STT Service     │ faster-whisper + LocalAgreement-2
│ (Port 8001)     │ • 150-200ms processing latency
│                 │ • Word-level timestamps
│                 │ • Confidence scoring
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ MT Service      │ MarianMT + rolling context
│ (Port 8002)     │ • 20-80ms translation latency
│                 │ • Context-aware translation
│                 │ • Quality assessment
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ TTS Service     │ XTTS + Piper + SpeechT5
│ (Port 8003)     │ • Sub-250ms TTFT
│                 │ • Streaming synthesis
│                 │ • Multi-engine support
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Translated      │ 16kHz PCM audio + captions
│ Audio Output    │ Published to LiveKit tracks
│ (WebRTC)        │
└─────────────────┘
```

### Core Services Deep Dive

#### STT Service (Speech-to-Text)

**Architecture:**
```python
STTService
├── WebSocket Handler (/ws/stt)
│   ├── AudioProcessor
│   │   ├── VADProcessor (Voice Activity Detection)
│   │   ├── AudioChunker (250ms chunks + 50ms overlap)
│   │   └── AudioNormalizer
│   └── LocalAgreement2 Algorithm
│       ├── WordCandidateTracker
│       ├── StabilityAnalyzer
│       └── ConfirmationLogic
├── HTTP API (/transcribe, /health, /performance)
├── Model Manager
│   ├── WhisperModel (tiny.en, base.en, small.en)
│   ├── ModelCache
│   └── GPUOptimizer
└── Metrics Collector
    ├── LatencyTracker
    ├── AccuracyMetrics
    └── ResourceMonitor
```

**LocalAgreement-2 Algorithm:**
```python
class LocalAgreement2:
    def __init__(self, agreement_threshold=2, stability_window=3):
        self.threshold = agreement_threshold  # Min agreement count
        self.window = stability_window        # Recent transcriptions
        self.word_candidates = {}            # Track word occurrences
        
    def process_transcription(self, words, confidences, timestamps):
        # 1. Track word candidates across transcriptions
        # 2. Confirm words appearing >= threshold times
        # 3. Return (interim_words, confirmed_words, new_confirmations)
        # 4. Minimize retractions through position-aware matching
```

**Key Features:**
- **Streaming Processing**: WebSocket-based real-time transcription
- **Word Stability**: LocalAgreement-2 reduces retractions <5%
- **GPU Optimization**: CUDA acceleration with FP16 precision
- **VAD Integration**: Smart silence detection with silero-vad
- **Model Flexibility**: Support for multiple Whisper model sizes

#### MT Service (Machine Translation)

**Architecture:**
```python
MTService
├── WebSocket Handler (/ws/translate)
├── HTTP API (/translate, /batch, /detect)
├── Translation Engine
│   ├── MarianMTModels (8+ language pairs)
│   ├── ContextManager (rolling 3-sentence buffer)
│   ├── QualityAssessor
│   │   ├── LengthRatioAnalyzer
│   │   ├── RepetitionDetector
│   │   ├── SemanticSimilarity
│   │   └── ContextCoherenceChecker
│   └── IncrementalProcessor
├── Model Optimizer
│   ├── ONNXConverter
│   ├── TensorRTOptimizer
│   └── BatchProcessor
└── Cache System
    ├── TranslationCache
    ├── ContextCache
    └── ModelCache
```

**Rolling Context Strategy:**
```python
class ContextManager:
    def __init__(self, max_sentences=3, max_tokens=512):
        self.context_buffer = collections.deque(maxlen=max_sentences)
        self.max_tokens = max_tokens
        
    def update_context(self, source_text, translated_text):
        # Maintain conversation context for coherent translations
        self.context_buffer.append({
            'source': source_text,
            'translation': translated_text,
            'timestamp': time.time()
        })
```

**Key Features:**
- **Context Awareness**: Rolling conversation context for coherence
- **Performance Optimization**: ONNX and TensorRT acceleration
- **Quality Assessment**: Multi-factor confidence scoring
- **Incremental Processing**: Handles partial sentences from STT
- **Language Detection**: Automatic source language identification

#### TTS Service (Text-to-Speech)

**Architecture:**
```python
TTSService
├── WebSocket Handler (/ws/synthesize)
├── HTTP API (/synthesize, /voices, /clone)
├── Engine Manager
│   ├── XTTS (Premium quality, 200ms TTFT)
│   ├── Piper (Fast synthesis, 100ms TTFT)
│   ├── SpeechT5 (Balanced quality/speed)
│   ├── EdgeTTS (Cloud fallback)
│   └── KokoroTTS (Ultra-low latency)
├── Voice Manager
│   ├── VoiceLibrary (47+ voices, 10+ languages)
│   ├── VoiceCloning (3-10s reference audio)
│   ├── VoicePreloader
│   └── QualityScorer
├── Streaming Synthesizer
│   ├── ChunkGenerator (1024-byte chunks)
│   ├── EarlyFramePublisher
│   └── AudioPostProcessor
└── Performance Monitor
    ├── TTFTTracker
    ├── QualityMetrics
    └── ThroughputMonitor
```

**Streaming Synthesis Flow:**
```python
async def streaming_synthesis(text: str, voice_id: str):
    # 1. Text preprocessing and normalization
    normalized_text = preprocess_text(text)
    
    # 2. Start synthesis with early frame generation
    synthesis_task = engine.synthesize_streaming(normalized_text, voice_id)
    
    # 3. Stream audio chunks as they become available
    async for audio_chunk in synthesis_task:
        yield {
            'type': 'audio_chunk',
            'data': base64.encode(audio_chunk),
            'timestamp': time.time()
        }
    
    # 4. Send completion notification
    yield {'type': 'synthesis_complete', 'total_duration': total_duration}
```

**Key Features:**
- **Multi-Engine Support**: 5 TTS engines for different use cases
- **Streaming Synthesis**: Real-time audio generation and delivery
- **Voice Cloning**: Custom voice creation from reference audio
- **Quality Tiers**: Fast, standard, and premium synthesis modes
- **Format Optimization**: LiveKit-compatible 16kHz mono audio

### LiveKit Integration

**Room Architecture:**
```
LiveKit Room: "conference-123"
├── Participants
│   ├── User A (Speaker)
│   │   ├── Audio Track (original speech)
│   │   └── Metadata: {preferred_language: "en"}
│   ├── User B (Listener) 
│   │   ├── Subscribes to: translated-spanish, translated-french
│   │   └── Metadata: {target_languages: ["es", "fr"]}
│   └── Translator Worker (System Participant)
│       ├── Subscribes to: all participant audio
│       ├── Publishes: translated audio tracks per language
│       │   ├── "translated-spanish" (es)
│       │   ├── "translated-french" (fr) 
│       │   └── "translated-german" (de)
│       └── Data Channel: real-time captions
└── Room Settings
    ├── Audio Codec: Opus (64kbps)
    ├── Target Latency: <100ms
    └── Adaptive Stream: enabled
```

**Translator Worker Logic:**
```python
class TranslatorWorker:
    async def on_track_subscribed(self, track: rtc.Track, publication: rtc.TrackPublication):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            # 1. Create audio processing pipeline for this track
            processor = AudioProcessor(participant_id=publication.participant.identity)
            
            # 2. Start real-time processing
            async for audio_chunk in track.audio_stream():
                # STT: Speech recognition
                transcription = await self.stt_client.transcribe(audio_chunk)
                
                # MT: Translation to all target languages
                for target_lang in self.config.target_languages:
                    translation = await self.mt_client.translate(
                        transcription.text, 
                        source_lang='auto',
                        target_lang=target_lang
                    )
                    
                    # TTS: Speech synthesis
                    audio_data = await self.tts_client.synthesize(
                        translation.text,
                        voice_id=self.config.voice_presets[target_lang],
                        language=target_lang
                    )
                    
                    # 3. Publish translated audio to room
                    await self.publish_audio(f"translated-{target_lang}", audio_data)
                    
                    # 4. Send captions via data channel
                    await self.send_caption(target_lang, translation.text)
```

## 🔧 Infrastructure Architecture

### Container Orchestration

```yaml
# docker-compose.yml structure
services:
  # Core Infrastructure
  redis:          # Session state and caching
  livekit:        # WebRTC SFU
  coturn:         # STUN/TURN server
  
  # Translation Services
  stt-service:    # Speech-to-text
  mt-service:     # Machine translation
  tts-service:    # Text-to-speech
  auth-service:   # JWT token generation
  
  # Translation Workers
  translator-worker:  # LiveKit participants (scalable)
  
  # Observability
  prometheus:     # Metrics collection
  grafana:        # Dashboard visualization
  jaeger:         # Distributed tracing
  health-monitor: # Service health checking
  
  # Security & Networking
  nginx:          # Load balancer and SSL termination
```

### Network Architecture

```
Internet
    │
    ▼
┌─────────────────┐
│ Load Balancer   │ nginx/HAProxy
│ SSL Termination │ • HTTPS → HTTP routing
│                 │ • WebSocket proxy
└─────┬───────────┘ • Rate limiting
      │
      ├─────────────────────────────────────────────────┐
      │                                                 │
      ▼                                                 ▼
┌─────────────────┐                            ┌─────────────────┐
│ Frontend        │                            │ API Gateway     │
│ Static Assets   │                            │ Authentication  │
│ React SPA       │                            │ Request Routing │
└─────────────────┘                            └─────┬───────────┘
                                                     │
                                    ┌────────────────┼────────────────┐
                                    │                │                │
                                    ▼                ▼                ▼
                            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                            │ STT Service │ │ MT Service  │ │ TTS Service │
                            │ WebSocket   │ │ HTTP/WS     │ │ HTTP/WS     │
                            └─────────────┘ └─────────────┘ └─────────────┘
                                    │                │                │
                                    └────────────────┼────────────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │ LiveKit SFU     │
                                            │ WebRTC Routing  │
                                            │ Media Processing│
                                            └─────────────────┘
```

### Data Flow Architecture

#### Real-time Translation Flow

```
1. Audio Capture (Browser)
   ├── MediaStream API
   ├── 16kHz, mono PCM
   └── 250ms chunks
         │
         ▼
2. WebRTC Transport (LiveKit)
   ├── Opus codec compression
   ├── Adaptive bitrate
   └── Network resilience
         │
         ▼
3. Translator Worker (LiveKit Participant)
   ├── Audio track subscription
   ├── Real-time processing
   └── Multi-language publishing
         │
         ▼
4. STT Processing
   ├── Voice Activity Detection
   ├── Whisper transcription
   ├── LocalAgreement-2 stabilization
   └── Word-level timestamps
         │
         ▼
5. MT Processing
   ├── Language detection
   ├── Context-aware translation
   ├── Quality assessment
   └── Confidence scoring
         │
         ▼
6. TTS Processing
   ├── Text normalization
   ├── Voice model selection
   ├── Streaming synthesis
   └── Audio post-processing
         │
         ▼
7. Media Distribution (LiveKit)
   ├── Per-language audio tracks
   ├── Real-time captions
   └── Participant subscription
         │
         ▼
8. Client Playback (Browser)
   ├── Audio context management
   ├── Synchronization
   └── User interface updates
```

#### Data Storage Architecture

```
┌─────────────────┐
│ Redis           │ Session state, caching
│ (In-Memory)     │ • WebRTC session data
│                 │ • Translation context
│                 │ • User preferences
│                 │ • Rate limiting counters
└─────────────────┘

┌─────────────────┐
│ PostgreSQL      │ Persistent data (optional)
│ (Optional)      │ • User accounts
│                 │ • Call history
│                 │ • Analytics data
│                 │ • TURN user management
└─────────────────┘

┌─────────────────┐
│ File System     │ Model storage
│ (/app/models)   │ • ML models (STT/MT/TTS)
│                 │ • Voice presets
│                 │ • Configuration files
│                 │ • SSL certificates
└─────────────────┘
```

## 📊 Observability Architecture

### Metrics Collection

```
Service Metrics Flow
┌─────────────────┐
│ Application     │ Custom metrics, business KPIs
│ Metrics         │ • Translation latency
│                 │ • Word accuracy rates
│                 │ • User engagement
└─────┬───────────┘
      │ /metrics endpoint (Prometheus format)
      ▼
┌─────────────────┐
│ Prometheus      │ Time-series database
│ (Port 9090)     │ • Metric aggregation
│                 │ • Alerting rules
│                 │ • Data retention
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Grafana         │ Visualization and dashboards
│ (Port 3001)     │ • SLO monitoring
│                 │ • Performance trends
│                 │ • Alert management
└─────────────────┘
```

### Distributed Tracing

```
Request Tracing Flow
User Request
     │
     ▼
┌─────────────────┐
│ Frontend        │ Trace ID generation
│ (Correlation)   │ Span: user_interaction
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ STT Service     │ Span: stt_processing
│                 │ • Audio preprocessing
│                 │ • Model inference
│                 │ • Post-processing
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ MT Service      │ Span: translation
│                 │ • Context retrieval
│                 │ • Model inference
│                 │ • Quality assessment
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ TTS Service     │ Span: synthesis
│                 │ • Text preprocessing
│                 │ • Audio generation
│                 │ • Streaming delivery
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Jaeger          │ Distributed tracing backend
│ (Port 16686)    │ • Trace aggregation
│                 │ • Performance analysis
│                 │ • Bottleneck identification
└─────────────────┘
```

### SLO Monitoring Framework

```python
# SLO Definition Example
SLO_TARGETS = {
    'translation_ttft': {
        'target_p95_ms': 450,
        'measurement_window': '5m',
        'alert_threshold': 500,
        'critical_threshold': 600
    },
    'caption_latency': {
        'target_p95_ms': 250,
        'measurement_window': '5m', 
        'alert_threshold': 300,
        'critical_threshold': 400
    },
    'word_retraction_rate': {
        'target_percentage': 5.0,
        'measurement_window': '10m',
        'alert_threshold': 8.0,
        'critical_threshold': 12.0
    }
}
```

## 🔐 Security Architecture

### Authentication and Authorization Flow

```
Authentication Flow
┌─────────────────┐
│ User Request    │ Room access attempt
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Frontend Auth   │ Token request with credentials
│                 │ • Room name
│                 │ • User identity
│                 │ • Requested permissions
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Auth Service    │ JWT token generation
│ (Port 8004)     │ • Identity verification
│                 │ • Permission assignment
│                 │ • Token signing (HMAC/RSA)
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ LiveKit SFU     │ Token validation
│                 │ • Signature verification
│                 │ • Permission checking
│                 │ • Room access control
└─────────────────┘
```

### Network Security

```
Security Layers
┌─────────────────┐
│ TLS/SSL Layer   │ HTTPS/WSS encryption
│                 │ • Certificate management
│                 │ • Perfect Forward Secrecy
│                 │ • HSTS headers
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Application     │ JWT tokens, API keys
│ Security        │ • Token expiration
│                 │ • Rate limiting
│                 │ • Input validation
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ WebRTC Security │ DTLS encryption
│                 │ • SRTP media encryption
│                 │ • ICE authentication
│                 │ • TURN credential rotation
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Network         │ Firewall rules
│ Security        │ • Port restrictions
│                 │ • DDoS protection
│                 │ • VPN access (optional)
└─────────────────┘
```

## 🎯 Performance Architecture

### Latency Optimization Strategy

```
Latency Budget Breakdown (Target: <500ms end-to-end)
┌─────────────────┐
│ Network (RTT)   │ 50ms  │ Client ←→ Server
└─────────────────┘
┌─────────────────┐
│ STT Processing  │ 150ms │ Audio → Text
└─────────────────┘
┌─────────────────┐
│ MT Processing   │ 50ms  │ Text → Translation
└─────────────────┘
┌─────────────────┐  
│ TTS Processing  │ 200ms │ Text → Audio
└─────────────────┘
┌─────────────────┐
│ Buffer/Overhead │ 50ms  │ Queuing, serialization
└─────────────────┘
═════════════════════
Total Budget: 500ms
```

### Scaling Strategy

```
Horizontal Scaling Architecture
┌─────────────────┐
│ Load Balancer   │ nginx with least_conn
│                 │ • Health check integration
│                 │ • Failover capabilities
└─────┬───────────┘
      │
      ├─────────────────────────────────────────┐
      │                                         │
      ▼                                         ▼
┌─────────────────┐                    ┌─────────────────┐
│ Service Pool A  │                    │ Service Pool B  │
│ ├── STT (3x)    │                    │ ├── STT (3x)    │
│ ├── MT (4x)     │                    │ ├── MT (4x)     │
│ ├── TTS (2x)    │                    │ ├── TTS (2x)    │
│ └── Auth (2x)   │                    │ └── Auth (2x)   │
└─────────────────┘                    └─────────────────┘
      │                                         │
      └─────────────────┬───────────────────────┘
                        │
                        ▼
                ┌─────────────────┐
                │ Shared State    │
                │ ├── Redis Cluster
                │ ├── LiveKit SFU
                │ └── CoTURN Server
                └─────────────────┘
```

### Caching Strategy

```python
# Multi-Layer Caching Architecture
class CachingStrategy:
    def __init__(self):
        # L1: In-memory process cache (fastest)
        self.memory_cache = LRUCache(maxsize=1000)
        
        # L2: Redis distributed cache (shared)
        self.redis_cache = RedisCache(ttl=3600)
        
        # L3: File system cache (persistent)
        self.file_cache = FileSystemCache(path="/tmp/cache")
    
    async def get_translation(self, text: str, lang_pair: str):
        # Check caches in order of speed
        cache_key = f"translation:{hash(text)}:{lang_pair}"
        
        # L1: Memory cache
        if result := self.memory_cache.get(cache_key):
            return result
            
        # L2: Redis cache  
        if result := await self.redis_cache.get(cache_key):
            self.memory_cache.set(cache_key, result)
            return result
            
        # L3: File cache
        if result := await self.file_cache.get(cache_key):
            await self.redis_cache.set(cache_key, result)
            self.memory_cache.set(cache_key, result)
            return result
            
        # Cache miss - compute and store in all layers
        result = await self.compute_translation(text, lang_pair)
        await self.store_in_all_caches(cache_key, result)
        return result
```

## 🚀 Deployment Architecture

### Production Deployment Topology

```
Multi-Region Deployment (Future)
┌─────────────────────────────────────────────────────────────────┐
│ Primary Region (us-east-1)                                      │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐ │
│ │ Web Tier        │ │ App Tier        │ │ Data Tier           │ │
│ │ • Load Balancer │ │ • Translation   │ │ • Redis Cluster     │ │
│ │ • CDN           │ │   Services      │ │ • PostgreSQL        │ │
│ │ • SSL Term      │ │ • LiveKit SFU   │ │ • File Storage      │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ Replication
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Secondary Region (eu-west-1) - Disaster Recovery               │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐ │
│ │ Web Tier        │ │ App Tier        │ │ Data Tier           │ │
│ │ • Load Balancer │ │ • Translation   │ │ • Redis Replica     │ │
│ │ • CDN           │ │   Services      │ │ • PostgreSQL Read   │ │
│ │ • SSL Term      │ │ • LiveKit SFU   │ │ • File Backup       │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Kubernetes Architecture (Optional)

```yaml
# k8s deployment structure
apiVersion: apps/v1
kind: Deployment
metadata:
  name: translation-services
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: stt-service
        resources:
          requests:
            nvidia.com/gpu: 1
            memory: "2Gi"
            cpu: "1"
          limits:
            nvidia.com/gpu: 1
            memory: "4Gi"
            cpu: "2"
      - name: mt-service
        resources:
          requests:
            memory: "1Gi" 
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
      - name: tts-service
        resources:
          requests:
            nvidia.com/gpu: 1
            memory: "3Gi"
            cpu: "1"
          limits:
            nvidia.com/gpu: 1  
            memory: "6Gi"
            cpu: "2"
```

## 🔄 CI/CD Architecture

### Deployment Pipeline

```
Development Workflow
┌─────────────────┐
│ Developer       │ Code changes, feature branches
│ Commits         │
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ GitHub Actions  │ Automated CI/CD pipeline
│ Pipeline        │ • Lint, test, build
│                 │ • Security scanning
│                 │ • Performance validation
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Staging         │ Full system testing
│ Environment     │ • SLO validation
│                 │ • Load testing  
│                 │ • Integration tests
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Production      │ Blue-green deployment
│ Deployment      │ • Zero-downtime updates
│                 │ • Automatic rollback
│                 │ • Health monitoring
└─────────────────┘
```

---

This architecture documentation provides a comprehensive view of The HIVE Translation System's design, from frontend components to backend services, infrastructure, and deployment strategies. The architecture is designed for production-scale operation with sub-500ms translation latency while maintaining high availability and scalability.

**Document Version**: 1.0  
**Last Updated**: $(date +%Y-%m-%d)  
**Next Review**: $(date -d "+3 months" +%Y-%m-%d)