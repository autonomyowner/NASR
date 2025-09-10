# Essential Development Commands

## Frontend Development
```bash
npm run dev                 # Start main React app (port 5173)
npm run dev:signaling      # Start WebSocket signaling server (port 3001) 
npm run dev:both          # Start both servers concurrently
npm run build             # Production build
npm run lint              # Code quality check with ESLint
npm run preview           # Preview production build
```

## Backend Translation Services
```bash
# Start all services with Docker Compose
cd backend/infra
docker-compose up -d

# Start individual services for development
docker-compose up -d livekit redis coturn    # Core infrastructure only
cd ../services/stt && python app.py &        # STT service locally
cd ../services/mt && python app.py &         # MT service locally  
cd ../services/tts && python app.py &        # TTS service locally
```

## Development Workflow Commands
```bash
# Full stack startup
cd backend/infra && docker-compose up -d && cd ../.. && npm run dev

# Check service health
curl http://localhost:8001/health    # STT service
curl http://localhost:8002/health    # MT service
curl http://localhost:8003/health    # TTS service

# Monitor services
docker-compose logs -f SERVICE_NAME  # View specific service logs
docker-compose ps                    # Check service status
```

## Observability and Monitoring
```bash
# Access monitoring interfaces
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/hive2024)
# Jaeger: http://localhost:16686
# LiveKit: http://localhost:7880
```

## Testing Translation Pipeline
1. Navigate to `http://localhost:5173/call`
2. Create room with target language selection
3. Speak to test STT→MT→TTS pipeline
4. Monitor metrics in Grafana dashboards