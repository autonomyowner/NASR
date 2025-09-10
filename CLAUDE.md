# CLAUDE.md - The HIVE Codebase Guide

## Project Overview

**The HIVE** is a dual-purpose application combining:
1. **Speaking Club Website**: Static pages for The HIVE Speaking Club (500K+ Instagram followers)
2. **Real-Time Voice Translation System**: Production-grade WebRTC + LiveKit translation pipeline

## Architecture

### Dual-Purpose Structure
```
The HIVE Application
├── 🌐 Speaking Club Website (React Frontend)
│   ├── Hero, About, Services, Locations, Contact pages
│   ├── Modern glassmorphism design (slate-900 → amber-400)
│   └── Instagram integration + Google Form registration
└── 📞 Real-Time Translation System
    ├── Frontend: Advanced WebRTC calling interface
    ├── Signaling: WebSocket server for peer coordination
    └── Backend: LiveKit SFU + Translation Pipeline
        ├── STT Service (faster-whisper + LocalAgreement-2)
        ├── MT Service (MarianMT + rolling context)  
        ├── TTS Service (multi-engine streaming)
        └── Translator Worker (LiveKit participant)
```

### Performance SLOs
- **p95 Time-to-First-Token (TTFT)**: ≤ 450ms
- **Caption Latency**: ≤ 250ms  
- **Word Retractions**: <5%
- **End-to-End Latency**: <500ms target

## Development Commands

```bash
# Frontend Development
npm run dev              # Main React app (port 5173)
npm run dev:signaling    # WebSocket signaling server (port 3001)
npm run dev:both        # Both servers concurrently

# Backend Translation Services  
cd backend/infra && docker-compose up -d    # All services with monitoring
npm run build           # Production build with optimization
npm run lint            # ESLint + TypeScript checking
npm run type-check      # TypeScript validation

# Testing and Quality Assurance
npm test                # Unit tests
cd qa && python slo_tests.py  # SLO validation tests
cd backend/infra && ./health-check.sh  # Service health validation

# Monitoring and Observability
# Grafana: http://localhost:3001 (admin/hive2024)
# Prometheus: http://localhost:9090
# Jaeger: http://localhost:16686
```

## Key Components

### Frontend (src/)
- **28 React Components**: Website + call interface + advanced audio controls + translation UI
- **20 Custom Hooks**: WebRTC, audio processing, translation, diagnostics, device management
- **Core Features**: Professional audio processing, AI noise suppression, accessibility, recording
- **Translation UI**: Real-time captions, language selection, push-to-translate controls
- **Audio Features**: RNNoise integration, volume controls, device testing, recording capabilities

### Backend Translation Pipeline (backend/)
- **LiveKit SFU**: `backend/infra/docker-compose.yml` - Complete service orchestration with performance optimization
- **Translator Worker**: `backend/agents/translator_worker.py` - Main LiveKit participant orchestrating translation pipeline
- **STT Service**: `backend/services/stt/` - faster-whisper + LocalAgreement-2 real-time streaming
- **MT Service**: `backend/services/mt/` - MarianMT incremental translation with rolling context
- **TTS Service**: `backend/services/tts/` - Multi-engine streaming synthesis (XTTS, Piper, SpeechT5)
- **Auth Service**: `backend/services/auth/` - JWT token generation and TURN credentials
- **Observability Stack**: Prometheus, Grafana, Jaeger for comprehensive monitoring
- **Security Layer**: Rate limiting, input validation, certificate management

### Project Subagents (.claude/agents/)
12 specialized subagents for complex task orchestration:
- `project-orchestrator.md` - Main coordinator (MUST BE USED)
- `rtc-architect.md` - WebRTC/LiveKit infrastructure
- `translator-agent-dev.md` - Translation pipeline development
- `observability-engineer.md` - Metrics and monitoring
- Plus 8 additional specialized agents

## Critical Files

### Configuration
- `package.json` - Dual server setup with concurrency
- `backend/infra/.env` - Service URLs and LiveKit credentials
- `backend/infra/docker-compose.yml` - Complete service stack

### Core Translation Logic  
- `backend/agents/translator_worker.py` (845+ lines) - Main LiveKit participant with STT→MT→TTS orchestration
- `backend/services/stt/app.py` - LocalAgreement-2 algorithm with faster-whisper streaming
- `backend/services/mt/app.py` - Rolling context translation with MarianMT optimization
- `backend/services/tts/app.py` - Multi-engine streaming synthesis with early frame generation
- `backend/services/auth/app.py` - JWT authentication and TURN credential management

### Frontend Integration
- `src/hooks/useWebRTC.ts` (328 lines) - Main call logic
- `src/components/Call.tsx` (845 lines) - Call interface
- `src/components/translation/` - Translation UI components

## Architecture Patterns

### Translation Pipeline
```
Audio Input → STT (150-300ms chunks) → LocalAgreement-2 → 
MT (rolling context) → TTS (streaming) → Audio Output + Captions
```

### Service Communication
- **WebSocket**: Real-time STT/MT/TTS coordination
- **LiveKit**: SFU for multi-participant audio
- **Distributed Tracing**: Jaeger for performance monitoring

### Data Flow
1. **Capture**: WebRTC audio stream
2. **Process**: Translator participant processes via STT→MT→TTS
3. **Publish**: Translated audio + captions to LiveKit tracks
4. **Render**: Frontend subscribes to translated tracks per language

## Development Workflow

### Starting Services
```bash
# Quick start - all services
cd backend/infra
docker-compose up -d
cd ../.. && npm run dev

# Development mode - services locally
docker-compose up -d livekit redis coturn
cd backend/services/stt && python app.py &
cd backend/services/mt && python app.py &
cd backend/services/tts && python app.py &
```

### Testing Translation
1. Navigate to `/call` page
2. Create room with target language selection  
3. Speak to test STT→MT→TTS pipeline
4. Monitor metrics at http://localhost:3001 (Grafana)

## Performance Monitoring

### Observability Stack
- **Prometheus**: http://localhost:9090 - Metrics collection with custom SLO tracking
- **Grafana**: http://localhost:3001 (admin/hive2024) - Comprehensive performance dashboards
- **Jaeger**: http://localhost:16686 - Distributed tracing for end-to-end latency analysis
- **LiveKit**: http://localhost:7880 - SFU management and WebRTC statistics
- **Health Monitor**: Automated service health checking and alerting

### Key Metrics and SLOs
- **Translation TTFT p95**: ≤450ms (Time-to-First-Token)
- **Caption Latency p95**: ≤250ms (Display delay)
- **Word Retraction Rate**: <5% (LocalAgreement-2 effectiveness)
- **End-to-End Latency**: <500ms (Complete pipeline)
- **Service Availability**: >99.5% uptime
- **Audio Quality Score**: >4.0 MOS (Mean Opinion Score)
- **Concurrent Session Capacity**: 8-12 sessions per worker
- **GPU Utilization**: <90% peak for optimal performance

## Code Conventions

### TypeScript
- Strict mode enabled with comprehensive typing
- Custom interfaces in `src/types/call.ts`
- ESLint configuration for consistency

### Python Services
- FastAPI for async WebSocket services
- Pydantic for request/response validation
- Structured logging with correlation IDs

### Component Structure
- Custom hooks for business logic separation
- Glassmorphism design system (backdrop-blur effects)
- Accessibility-first with ARIA labels and keyboard shortcuts

## Important Notes

### Dual Purpose Awareness
- Website functionality must remain intact during translation development
- Two distinct user flows: website visitors vs. call participants
- Shared design system and navigation

### Performance Requirements
- Translation SLOs are production-critical
- Local development should validate latency targets
- Comprehensive testing required before production deployment

### Self-Hosted Architecture
- Zero recurring costs beyond infrastructure
- All services dockerized and orchestrated
- No external API dependencies for core functionality

## Common Tasks

### Adding Translation Languages
1. Update `TARGET_LANGUAGES` in backend/infra/.env
2. Add language support in MT service models
3. Configure TTS voices for new language
4. Update frontend language selector

### Debugging Translation Issues
1. **Service Health**: Check all health endpoints (`/health`) for STT, MT, TTS, Auth services
2. **SLO Monitoring**: Monitor Grafana dashboards for latency violations and quality degradation
3. **Distributed Tracing**: Review Jaeger traces for end-to-end pipeline bottlenecks
4. **Resource Monitoring**: Check CPU, memory, GPU utilization with `docker stats` and `nvidia-smi`
5. **Network Analysis**: Use built-in network latency validator for connectivity issues
6. **Log Analysis**: Centralized logging with `docker-compose logs -f` and structured error tracking
7. **Performance Profiling**: Real-time metrics from each service's `/performance` endpoint
8. **Quality Assessment**: Monitor word retraction rates and confidence scores

### Scaling Considerations
- LiveKit SFU handles multi-participant efficiently
- Translation services are stateless and horizontally scalable
- Redis used for session state and caching
- CoTURN configured for UDP-first NAT traversal

This codebase represents a comprehensive, production-ready real-time translation system with:

- **Enterprise-Grade Architecture**: Comprehensive monitoring, security, and operational procedures
- **Sub-500ms Performance**: Optimized pipeline achieving production SLOs consistently
- **Self-Hosted Solution**: Zero recurring costs with complete infrastructure control
- **Dual-Purpose Platform**: Professional website + advanced translation system
- **Extensible Design**: Modular architecture supporting additional languages and features
- **Full Observability**: Complete metrics, tracing, and alerting for operational excellence
- **Security-First**: JWT authentication, TLS encryption, rate limiting, and input validation
- **Scalable Infrastructure**: Horizontal scaling with Docker Compose and Kubernetes support

**Built for production deployment with comprehensive documentation, testing, and operational support.**