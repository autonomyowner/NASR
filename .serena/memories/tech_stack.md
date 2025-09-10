# Tech Stack Details

## Frontend
- **React**: 19.1.0 with functional components and hooks
- **TypeScript**: ~5.8.3 with strict mode enabled
- **Build Tool**: Vite 7.0.4 for fast development and builds
- **Styling**: TailwindCSS 3.4.17 with PostCSS
- **Routing**: React Router DOM 7.7.1
- **WebRTC**: Custom hooks for advanced audio processing
- **Real-time Communication**: Socket.IO client for WebSocket connections

## Backend Services
- **Python**: FastAPI for async WebSocket services
- **LiveKit**: SFU (Selective Forwarding Unit) v1.4.3
- **Redis**: 7-alpine for caching and session state
- **CoTURN**: 4.6.2 for NAT traversal
- **Translation Services**:
  - STT: faster-whisper with LocalAgreement-2 algorithm
  - MT: MarianMT with rolling context translation
  - TTS: XTTS with streaming synthesis

## Observability Stack
- **Prometheus**: v2.45.0 for metrics collection
- **Grafana**: 10.0.0 for visualization dashboards
- **Jaeger**: 1.47.0 for distributed tracing
- **Nginx**: 1.25-alpine for reverse proxy and load balancing

## Infrastructure
- **Docker Compose**: Complete service orchestration
- **Network**: Custom bridge network (172.20.0.0/16) for co-location optimization
- **Volumes**: Persistent storage for models, data, and configurations