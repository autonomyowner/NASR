# Codebase Structure

## Root Directory
```
D:\NASR\thehive\
├── frontend/                 # React application
├── backend/                  # Translation services
├── signaling-server/         # WebSocket server
├── .claude/agents/          # 12 specialized subagents
└── configuration files
```

## Frontend Structure (src/)
- **24 React Components**: Website + call interface + advanced audio controls
- **17 Custom Hooks**: WebRTC, audio processing, translation, diagnostics
- **Key Directories**:
  - `src/components/` - UI components including Call.tsx (845 lines)
  - `src/hooks/` - Custom hooks including useWebRTC.ts (328 lines)  
  - `src/services/` - Frontend service integrations
  - `src/types/` - TypeScript type definitions

## Backend Structure (backend/)
- **Translation Pipeline**:
  - `backend/agents/translator_worker.py` (845 lines) - Main participant logic
  - `backend/services/stt/` - Speech-to-Text with faster-whisper
  - `backend/services/mt/` - Machine Translation with MarianMT
  - `backend/services/tts/` - Text-to-Speech with XTTS
  - `backend/services/auth/` - Authentication service

## Infrastructure (backend/infra/)
- **docker-compose.yml** - Complete service orchestration
- **Monitoring Stack**: Prometheus, Grafana, Jaeger configurations
- **Network Configuration**: CoTURN, Nginx, LiveKit setup
- **Environment Files**: .env templates for service configuration

## Critical Files
- `package.json` - Dual server setup with concurrency
- `src/hooks/useWebRTC.ts` - Main WebRTC call logic
- `src/components/Call.tsx` - Primary call interface
- `backend/infra/docker-compose.yml` - Service stack definition

## Project Subagents (.claude/agents/)
12 specialized agents for task orchestration:
- `project-orchestrator.md` - Main coordinator (MUST BE USED)
- `observability-engineer.md` - Metrics and monitoring  
- `rtc-architect.md` - WebRTC/LiveKit infrastructure
- Plus 9 additional specialized agents