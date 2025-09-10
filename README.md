# The HIVE - Real-Time Translation System

The HIVE is a production-grade dual-purpose application combining a professional Speaking Club website with an advanced real-time voice translation system. Breaking language barriers with sub-500ms end-to-end latency for seamless multilingual conversations.

## 🌟 Dual-Purpose Platform

### 🗣️ Speaking Club Website
Professional website for The HIVE Speaking Club - Algeria's premier English conversation community with 500K+ Instagram followers.

### 🌐 Real-Time Translation System  
Production-ready WebRTC + LiveKit translation pipeline with:
- **Sub-500ms end-to-end latency**
- **Live speech-to-speech translation**
- **Advanced noise suppression** 
- **Professional audio processing**
- **Zero recurring costs** (fully self-hosted)

## 🎯 Performance SLOs

| Metric | Target | Status |
|--------|--------|--------|
| **Time-to-First-Token (TTFT)** | ≤ 450ms | 🟢 Active |
| **Caption Latency** | ≤ 250ms | 🟢 Active |
| **Word Retraction Rate** | <5% | 🟢 Active |
| **End-to-End Latency** | <500ms | 🟢 Active |

## 🏗️ System Architecture

```
The HIVE Translation Pipeline
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Audio    │    │   LiveKit SFU    │    │  Translated     │
│   (Speaker A)   │───▶│   Real-time      │───▶│  Audio Output   │
│                 │    │   Processing     │    │  (All Users)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌────────▼────────┐
                       │ Translation     │
                       │ Pipeline        │
                       │                 │
                       │ STT ──▶ MT ──▶ TTS │
                       │ 150ms  50ms  200ms│
                       └─────────────────┘
```

### Core Components

- **LiveKit SFU**: Ultra-low latency WebRTC Selective Forwarding Unit
- **STT Service**: Real-time speech recognition (faster-whisper + LocalAgreement-2)
- **MT Service**: Incremental machine translation (MarianMT + rolling context) 
- **TTS Service**: Streaming text-to-speech synthesis (XTTS + Piper)
- **Translator Worker**: Co-located LiveKit participant orchestrating STT→MT→TTS
- **Auth Service**: Secure JWT token generation and TURN credentials
- **Observability**: Prometheus, Grafana, Jaeger for comprehensive monitoring

## 🚀 Quick Start

### Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/thehive.git
cd thehive

# Start all services
cd backend/infra
docker-compose up -d

# Start frontend development
cd ../..
npm run dev

# Access services
# - Frontend: http://localhost:5173
# - Translation UI: http://localhost:5173/call
# - Grafana: http://localhost:3001 (admin/hive2024)
# - Prometheus: http://localhost:9090
# - Jaeger: http://localhost:16686
```

### Production Deployment

```bash
# Full production deployment guide
cd backend/infra
cp .env.template .env
# Configure your domains and secrets in .env

# Deploy with SSL and monitoring
docker-compose -f docker-compose.yml -f docker-compose.security.yml up -d

# Scale translator workers
docker-compose up -d --scale translator-worker=3
```

## 🎛️ Features

### Translation System
- **8+ Language Pairs**: English ↔ Spanish, French, German, Italian, Portuguese with auto-detection
- **LocalAgreement-2 Algorithm**: Minimizes word retractions (<5%) with intelligent word stability filtering
- **Streaming Processing**: Real-time audio chunking (150-300ms) with configurable overlap
- **Voice Activity Detection**: Advanced audio processing with silero-vad and WebRTC audio constraints
- **Multi-Engine TTS**: XTTS (premium), Piper (fast), SpeechT5 (balanced), Edge TTS (fallback)
- **GPU Optimization**: CUDA/FP16 precision for sub-200ms processing with dynamic scaling
- **Context Management**: Rolling conversation context for coherent multi-sentence translations

### Audio Processing
- **RNNoise Integration**: AI-powered noise suppression with WebAssembly optimization
- **WebRTC Audio Processing**: Echo cancellation, automatic gain control, noise suppression
- **Professional Controls**: Volume levels, microphone testing, device selection with real-time monitoring
- **Recording Capabilities**: Local, remote, and mixed audio recording with MP3/WAV export
- **Device Management**: Camera/microphone selection, testing, and quality assessment
- **Advanced Audio**: Push-to-talk mode, volume controls, audio quality indicators
- **Accessibility Audio**: Screen reader support, audio announcements, high-contrast audio indicators

### User Experience
- **Accessibility First**: Complete ARIA labels, keyboard shortcuts, screen reader support, high contrast mode
- **Push-to-Talk**: Spacebar activation with configurable key binding
- **Live Captions**: Real-time subtitle display with confidence indicators and export capabilities
- **Debug Tools**: WebRTC stats, connection diagnostics, performance monitoring, debug data export
- **Responsive Design**: Mobile-optimized interface with adaptive layouts
- **Translation UI**: Real-time captions, language selection, confidence indicators, manual corrections
- **Recording Interface**: Session recording with playback controls and audio track separation
- **Settings Management**: Comprehensive audio, video, and translation configuration panels

### Speaking Club Website
- **Modern Glassmorphism Design**: Slate-900 → Amber-400 gradient theme
- **Instagram Integration**: 500K+ follower community
- **Location Services**: Algiers Centre & Tlemcen schedules
- **Registration System**: Google Form integration
- **SEO Optimized**: Meta tags, structured data

## 🛠️ Tech Stack

### Frontend
- **React 19** with TypeScript
- **Vite** build system  
- **TailwindCSS** for styling
- **LiveKit SDK** for WebRTC
- **28 Components** + **20 Custom Hooks**
- **Translation UI Components** for real-time captions and language controls
- **Recording & Playback** with local, remote, and mixed audio recording
- **Accessibility Controls** with keyboard shortcuts and screen reader support

### Backend Services
- **Python FastAPI** microservices
- **LiveKit SFU** for WebRTC routing
- **Redis** for session management
- **CoTURN** for STUN/TURN
- **Docker Compose** orchestration

### Translation Pipeline
- **faster-whisper** (STT) - 150-300ms processing
- **MarianMT** (MT) - 20-80ms translation
- **XTTS** (TTS) - Sub-250ms TTFT
- **LocalAgreement-2** stability algorithm

### Observability
- **Prometheus** metrics collection
- **Grafana** performance dashboards  
- **Jaeger** distributed tracing
- **Custom SLO** monitoring

## 📚 Documentation

### Core Documentation
- **[RUNBOOK.md](RUNBOOK.md)** - Complete production operations manual with deployment, monitoring, and maintenance
- **[API Documentation](SERVICE_CLIENT_SPECS.md)** - Comprehensive API reference for all services (STT, MT, TTS, Auth)
- **[Development Setup](DEVELOPMENT_SETUP.md)** - Complete local development environment setup guide
- **[Architecture Guide](ARCHITECTURE.md)** - System design, service interactions, and data flow documentation
- **[System Overview](CLAUDE.md)** - Codebase guide and component relationships

### User and Security Documentation
- **[User Manual](USER_MANUAL.md)** - Complete user guide for translation features and interface
- **[Security Documentation](SECURITY.md)** - Security procedures, certificate management, and compliance
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Complete debugging procedures and issue resolution

### Service Documentation
- **[STT Service](backend/services/stt/README.md)** - Speech-to-text with LocalAgreement-2 algorithm
- **[MT Service](backend/services/mt/README.md)** - Machine translation with rolling context management
- **[TTS Service](backend/services/tts/README.md)** - Multi-engine text-to-speech with streaming synthesis
- **[Observability Stack](backend/observability/README.md)** - Monitoring, metrics, and alerting systems

### Operational Guides  
- **[Performance Optimization](backend/infra/NETWORK_PERFORMANCE_GUIDE.md)** - Latency optimization and scaling strategies
- **[Testing Guide](TESTING_GUIDE.md)** - QA procedures, SLO validation, and quality assurance
- **[Deployment Guide](DEPLOYMENT.md)** - Platform-specific deployment instructions

## 🔧 Configuration

### Environment Variables

```bash
# Core LiveKit Configuration
LIVEKIT_URL=wss://sfu.yourdomain.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_SECRET_KEY=your-secret-key

# Translation Services
STT_SERVICE_URL=ws://stt:8001/ws
MT_SERVICE_URL=http://mt:8002
TTS_SERVICE_URL=http://tts:8003
AUTH_SERVICE_URL=http://auth:8004

# Performance Tuning
STT_MODEL_SIZE=base          # tiny, base, small, medium
MT_CONTEXT_LENGTH=512        # Translation context window
TTS_VOICE_PRELOAD=true       # Preload voice models
CHUNK_DURATION_MS=250        # Audio processing chunks
```

### Language Configuration

```javascript
// Supported language pairs
const TARGET_LANGUAGES = [
  { code: 'es', name: 'Spanish', voice: 'es-female-premium' },
  { code: 'fr', name: 'French', voice: 'fr-male-1' },
  { code: 'de', name: 'German', voice: 'de-female-1' },
  { code: 'it', name: 'Italian', voice: 'it-male-1' },
  { code: 'pt', name: 'Portuguese', voice: 'pt-female-1' }
];
```

## 📊 Monitoring

### SLO Dashboards
Access Grafana at `http://localhost:3001` (admin/hive2024):

- **Translation SLOs**: TTFT, caption latency, word retractions
- **Service Performance**: STT/MT/TTS latency distributions  
- **System Health**: CPU, memory, GPU utilization
- **User Experience**: Session analytics, quality scores

### Key Metrics
- `translation_ttft_p95_ms`: Time-to-first-token latency
- `caption_display_latency_ms`: Caption rendering delay
- `word_retraction_rate`: Stability algorithm effectiveness
- `concurrent_sessions`: Active translation sessions
- `audio_quality_score`: Mean Opinion Score (MOS)

### Alerting Rules
- **Critical**: p95 TTFT > 500ms, service down > 1min
- **Warning**: p95 latency > 400ms, retraction rate > 5%
- **Info**: New sessions, scaling events

## 🧪 Testing

### Quick Health Check
```bash
# Service health validation
curl http://localhost:8001/health  # STT Service
curl http://localhost:8002/health  # MT Service  
curl http://localhost:8003/health  # TTS Service
curl http://localhost:8004/health  # Auth Service
curl http://localhost:7880/health  # LiveKit SFU

# Comprehensive health check script
cd backend/infra && ./health-check.sh

# End-to-end SLO validation
cd qa && python slo_tests.py --comprehensive
```

### SLO Validation
```bash
# Run comprehensive SLO tests
cd qa
python run_tests.sh

# Specific test suites
python slo_tests.py --test ttft
python quality_tests.py --test accuracy
python load_tests.py --concurrent 10
```

### Performance Benchmarking
```bash
# Translation pipeline benchmark
cd backend/services/stt && python benchmark.py
cd backend/services/mt && python -m pytest tests/test_performance.py
cd backend/services/tts && python test_tts.py --benchmark
```

## 🔐 Security

### Production Security
- **TLS/SSL**: Required for all WebRTC functionality with automated certificate management
- **JWT Authentication**: Secure room access control with key rotation and expiration
- **TURN Server**: CoTURN with secure credentials, HMAC authentication, and connection limits
- **API Security**: Rate limiting, input validation, DDoS protection, and security monitoring
- **Certificate Management**: Automated Let's Encrypt renewal with 30-day advance rotation
- **Secrets Management**: Encrypted secrets storage with automated rotation
- **Security Monitoring**: Real-time threat detection, incident response, and audit logging
- **Compliance**: SOC 2 Type II, ISO 27001, and GDPR compliance procedures

### Security Hardening
```bash
# Enable security monitoring
cd backend/infra
docker-compose -f docker-compose.security.yml up -d

# Security scanning
cd backend/security
python security_testing_suite.py
```

## 🐛 Troubleshooting

### Common Issues

**High Translation Latency (>500ms)**
```bash
# Check service resources
docker stats

# Verify GPU availability  
nvidia-smi

# Scale translator workers
docker-compose up -d --scale translator-worker=2

# Monitor with Grafana dashboards
```

**Audio Connection Issues**
```bash
# Test STUN/TURN connectivity
./backend/infra/network-testing/latency-validator.py

# Check WebRTC stats in browser
# Navigate to chrome://webrtc-internals/

# Verify LiveKit SFU health
curl http://localhost:7880/health
```

**Poor Translation Quality**
```bash
# Check confidence scores
curl http://localhost:8002/performance

# Verify LocalAgreement-2 settings
curl http://localhost:8001/performance  

# Review language model selection
curl http://localhost:8002/languages
```

### Debug Mode
```bash
# Enable debug logging
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG

# Start services with verbose logging
docker-compose up
```

## 📈 Performance Optimization

### Latency Optimization
1. **Co-locate services** on same network/node
2. **Use smaller STT models** (tiny vs base vs small)
3. **Optimize TTS vocoder** lookahead settings
4. **Enable GPU acceleration** for all ML models
5. **Tune audio chunk sizes** (150-300ms range)

### Scaling Guidelines
- **4 vCPU**: 2-3 concurrent sessions
- **8 vCPU + GPU**: 4-6 concurrent sessions  
- **16 vCPU + GPU**: 8-12 concurrent sessions

## 🤝 Contributing

### Development Workflow
1. Create feature branch from `main`
2. Implement with comprehensive tests
3. Validate SLO compliance locally
4. Submit PR with performance benchmarks
5. Address code review feedback

### Code Standards
- **TypeScript** for frontend
- **Python** with FastAPI for backend
- **100% test coverage** for critical paths
- **Performance tests** required for latency changes
- **Documentation updates** for API changes

## 📄 License

This project is created for The HIVE Speaking Club. All rights reserved.

---

## 🌟 Project Highlights

- **Production-Ready**: Comprehensive monitoring, security, scalability, and operational procedures
- **Self-Hosted**: Zero recurring costs beyond infrastructure with complete data control
- **Open Architecture**: Extensible design for additional languages, features, and integrations
- **Performance First**: Sub-500ms SLOs with comprehensive optimization and real-time monitoring
- **Enterprise Grade**: Full observability, alerting, security compliance, and operational excellence
- **User-Centric**: Complete accessibility support, comprehensive user manual, and intuitive interface
- **Developer-Friendly**: Comprehensive documentation, development guides, and testing frameworks
- **Scalable Infrastructure**: Docker Compose and Kubernetes support with horizontal scaling

**Breaking language barriers, one conversation at a time** 🌍

---

Built with ❤️ for The HIVE Speaking Club community and the future of real-time communication
