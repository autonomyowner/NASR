# The HIVE Translation System - Quick Start Guide

## 🚀 Starting All Services

This guide will help you quickly start The HIVE's real-time translation system locally for development and testing.

## Prerequisites

- **Docker & Docker Compose** (latest versions)
- **Node.js 18+** (for frontend development)
- **Python 3.9+** (for backend services)
- **GPU Support** (optional but recommended for better performance)

## Quick Start (All Services)

### 1. Start the Complete Stack

```bash
# Navigate to infrastructure directory
cd backend/infra

# Start all services (LiveKit, STT, MT, TTS, monitoring)
docker-compose up -d

# Check all services are running
docker-compose ps
```

### 2. Start Frontend Development Server

```bash
# In a new terminal, navigate to project root
cd ../..

# Install dependencies (if not already done)
npm install

# Start frontend dev server
npm run dev
```

### 3. Verify Services

Open your browser and check:

- **Frontend**: http://localhost:3000
- **LiveKit Dashboard**: http://localhost:7880  
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3001 (admin/admin123)
- **Jaeger Tracing**: http://localhost:16686

## Service-by-Service Startup

### Option A: Docker Services Only

```bash
# Start core infrastructure
docker-compose up -d livekit redis coturn

# Start translation services  
docker-compose up -d stt-service mt-service tts-service

# Start translator workers
docker-compose up -d translator-worker

# Start monitoring stack
docker-compose up -d prometheus grafana jaeger
```

### Option B: Development Mode (Mixed)

```bash
# Start infrastructure services with Docker
docker-compose up -d livekit redis coturn prometheus grafana

# Run translation services locally for development
cd backend/services/stt && python app.py &
cd backend/services/mt && python app.py &  
cd backend/services/tts && python app.py &

# Run translator worker locally
cd backend/agents && python run_translator.py \
  --url ws://localhost:7880 \
  --token YOUR_LIVEKIT_TOKEN \
  --room test-room
```

## Environment Configuration

### Required Environment Variables

Create a `.env` file in `backend/infra/`:

```bash
# LiveKit Configuration
LIVEKIT_API_KEY=devkey
LIVEKIT_SECRET_KEY=devsecret
LIVEKIT_URL=ws://localhost:7880

# Service URLs
STT_SERVICE_URL=ws://localhost:8000/ws/transcribe
MT_SERVICE_URL=ws://localhost:8001/ws/translate
TTS_SERVICE_URL=ws://localhost:8002/ws/synthesize

# TURN Server Configuration
TURN_USERNAME=hiveuser
TURN_CREDENTIAL=hivepass

# Translation Configuration
TARGET_LANGUAGES=es,fr,de,it,pt
STT_MODEL=base
CHUNK_DURATION_MS=250
CONTEXT_LENGTH=512

# Monitoring
GRAFANA_PASSWORD=admin123
PROMETHEUS_PORT=9090
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

## Testing the Translation Pipeline

### 1. Create a Test Room

```bash
# Use LiveKit CLI (install if needed)
lk room create test-room

# Or use the web interface at http://localhost:7880
```

### 2. Join Room and Test Translation

1. Open frontend at http://localhost:3000
2. Navigate to `/call` page  
3. Enter room name: `test-room`
4. Select target language (e.g., Spanish)
5. Click "Start Call" and speak to test translation

### 3. Monitor Performance

- **Check Grafana**: http://localhost:3001
  - View translation latency dashboards
  - Monitor SLO compliance (TTFT ≤ 450ms, captions ≤ 250ms)
  
- **Check Jaeger**: http://localhost:16686  
  - View distributed traces across STT→MT→TTS pipeline
  - Analyze performance bottlenecks

## Troubleshooting

### Services Not Starting

```bash
# Check Docker logs
docker-compose logs -f SERVICE_NAME

# Common issues:
docker-compose logs -f livekit        # LiveKit connection issues
docker-compose logs -f stt-service    # STT model loading
docker-compose logs -f translator-worker  # Worker connection errors
```

### Translation Not Working

1. **Check Service Health**:
   ```bash
   curl http://localhost:8000/health  # STT
   curl http://localhost:8001/health  # MT  
   curl http://localhost:8002/health  # TTS
   ```

2. **Check LiveKit Connection**:
   - Verify LiveKit dashboard shows active rooms
   - Check translator worker logs for connection errors
   
3. **Check Audio Permissions**:
   - Ensure browser has microphone permissions
   - Test with different browsers (Chrome recommended)

### Performance Issues

1. **High Latency** (TTFT > 450ms):
   - Check GPU availability: `docker-compose logs stt-service | grep GPU`
   - Try smaller STT model: Set `STT_MODEL=tiny` in .env
   - Check network latency between services

2. **Poor Translation Quality**:
   - Increase context length: Set `CONTEXT_LENGTH=1024`
   - Check supported language pairs in MT service logs
   - Verify audio quality (16kHz recommended)

## Development Workflow

### Code Changes

- **Frontend Changes**: Auto-reload via Vite dev server
- **Backend Services**: Restart specific service container
- **Translator Worker**: Restart worker container or process

### Adding New Languages

1. Update `TARGET_LANGUAGES` in .env
2. Add voice presets for new language in TTS service
3. Restart services: `docker-compose restart mt-service tts-service`

### Performance Testing

```bash
# Run synthetic load test
cd backend/agents
python synthetic_load_test.py --speakers 4 --duration 300

# Monitor metrics in Grafana during test
```

## Production Deployment

For production deployment, see `DEPLOYMENT.md` for:
- Kubernetes manifests
- SSL/TLS configuration  
- High availability setup
- Scaling recommendations

## Getting Help

- **Logs**: `docker-compose logs -f --tail=100`
- **Health Checks**: Service `/health` endpoints
- **Metrics**: Prometheus at http://localhost:9090
- **Tracing**: Jaeger at http://localhost:16686

The system is now ready for real-time voice translation with sub-500ms latency! 🎯