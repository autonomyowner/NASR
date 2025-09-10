# The HIVE Project Overview

## Purpose
The HIVE is a dual-purpose application that combines:
1. **Speaking Club Website**: Static pages for The HIVE Speaking Club (500K+ Instagram followers)
2. **Real-Time Voice Translation System**: Production-grade WebRTC + LiveKit translation pipeline

## Architecture
- **Frontend**: React + TypeScript with advanced WebRTC calling interface
- **Signaling**: WebSocket server for peer coordination
- **Backend**: LiveKit SFU + Translation Pipeline with STT, MT, and TTS services
- **Performance SLOs**: p95 TTFT ≤ 450ms, Caption Latency ≤ 250ms, Word Retractions <5%

## Key Features
- Real-time voice translation with end-to-end latency <500ms target
- Professional audio processing with AI noise suppression
- Accessibility-first design with ARIA labels and keyboard shortcuts
- Modern glassmorphism design (slate-900 → amber-400)
- Zero recurring costs beyond infrastructure (self-hosted)

## Tech Stack Overview
- **Frontend**: React 19, TypeScript, Vite, TailwindCSS
- **Backend**: Python FastAPI services, LiveKit SFU, Redis
- **Translation Pipeline**: faster-whisper (STT), MarianMT (MT), XTTS (TTS)
- **Observability**: Prometheus, Grafana, Jaeger
- **Infrastructure**: Docker Compose orchestration