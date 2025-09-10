# The HIVE Translator Worker

This directory contains the LiveKit translator participant that coordinates real-time audio translation using The HIVE's STT→MT→TTS pipeline.

## Architecture Overview

```
Audio Input → STT Service (150-300ms chunks) → LocalAgreement-2 → 
MT Service (rolling context) → TTS Service (streaming) → Audio Output + Captions
```

## Key Components

### Core Files
- `translator_worker.py` - Main LiveKit participant implementation
- `run_translator.py` - Standalone execution script  
- `config.py` - Configuration management
- `test_integration.py` - Integration testing script

### Service Clients
- `services/stt_client.py` - WebSocket client for STT service
- `services/mt_client.py` - WebSocket client for MT service
- `services/tts_client.py` - WebSocket client for TTS service

### Observability
- `observability/tracer.py` - Distributed tracing integration

## Quick Start

### 1. Start Backend Services

```bash
# Start all services with docker-compose
cd ../infra
docker-compose up -d

# Or start services individually for development
docker-compose up -d livekit redis coturn
cd ../services/stt && python app.py &
cd ../services/mt && python app.py &
cd ../services/tts && python app.py &
```

### 2. Configure Environment

```bash
# Copy example environment file
cp ../infra/.env.example ../infra/.env

# Edit configuration (set URLs, keys, etc.)
nano ../infra/.env
```

### 3. Test Integration

```bash
# Run integration tests
python test_integration.py
```

### 4. Run Translator Worker

```bash
# Run with LiveKit room credentials
python run_translator.py \
    --url ws://localhost:7880 \
    --token <YOUR_LIVEKIT_TOKEN> \
    --room translation-room-123 \
    --log-level INFO
```

## Configuration

### Environment Variables

Required variables (set in `../infra/.env`):
```bash
# Service URLs
STT_SERVICE_URL=ws://localhost:8001/ws/stt
MT_SERVICE_URL=ws://localhost:8002/ws/translate
TTS_SERVICE_URL=ws://localhost:8003/ws/synthesize

# LiveKit Configuration  
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_SECRET=secret

# Security
JWT_SECRET=your-super-secure-jwt-secret-key-at-least-32-chars
```

### Translation Configuration

```bash
# Target languages (comma-separated)
TARGET_LANGUAGES=es,fr,de,it,pt

# Performance settings
CHUNK_DURATION_MS=250
CONTEXT_LENGTH=512
STT_TIMEOUT_MS=5000
MT_TIMEOUT_MS=2000
TTS_TIMEOUT_MS=5000

# SLO targets
TTFT_TARGET_MS=450
CAPTION_LATENCY_TARGET_MS=250
MAX_RETRACTION_RATE=0.05
```

## How It Works

### 1. Room Connection
- Translator worker connects to LiveKit room as a participant
- Subscribes to all audio tracks from other participants
- Creates event handlers for participant join/leave

### 2. Audio Processing Pipeline
```python
# For each audio chunk from participants:
1. Buffer audio (150-300ms chunks with VAD)
2. Send to STT service via WebSocket
3. Apply LocalAgreement-2 stabilization  
4. Update rolling context buffer
5. Translate to all target languages (parallel)
6. Synthesize speech for each language
7. Publish translated audio tracks + captions
```

### 3. Track Publishing
- Creates separate audio track per target language
- Publishes real-time translated audio streams
- Sends captions via LiveKit data channels
- Handles track lifecycle management

### 4. Error Handling
- Service reconnection with exponential backoff
- Graceful degradation when services unavailable
- Request timeout and retry mechanisms
- Comprehensive logging and telemetry

## Performance Optimization

### Latency Targets
- **STT**: ≤200ms (with LocalAgreement-2 stabilization)
- **MT**: 20-80ms (incremental translation with context)
- **TTS**: ≤250ms (streaming synthesis with early frames)
- **Total**: ≤450ms Time-to-First-Token (TTFT)

### Concurrent Processing
- Parallel translation for multiple target languages
- Asynchronous service communication 
- Non-blocking audio track publishing
- Connection pooling and keep-alive

### Memory Management
- Rolling context buffers (512 tokens max)
- Audio chunk streaming (no accumulation)
- Automatic cleanup on participant disconnect
- Garbage collection optimization

## Monitoring and Debugging

### Logs
```bash
# View real-time logs
tail -f translator_worker.log

# Debug mode
python run_translator.py --log-level DEBUG ...
```

### Metrics
- Prometheus metrics: http://localhost:9090
- Grafana dashboards: http://localhost:3001 (admin/hive2024)
- Jaeger tracing: http://localhost:16686

### Health Checks
```bash
# Test individual services
curl http://localhost:8001/health
curl http://localhost:8002/health  
curl http://localhost:8003/health

# Test full pipeline
python test_integration.py
```

## Production Deployment

### Docker Deployment
```bash
# Build translator worker image
docker build -t hive-translator .

# Run with docker-compose
docker-compose -f ../infra/docker-compose.yml up -d
```

### Kubernetes
```yaml
# Use translator-deployment.yaml
kubectl apply -f ../infra/translator-deployment.yaml
```

### Scaling Considerations
- Run multiple translator workers per room (load balancing)
- Use Redis for session state sharing
- Monitor CPU/GPU utilization for ML services
- Configure auto-scaling based on concurrent sessions

## Troubleshooting

### Common Issues

1. **Services not connecting**
   - Check if backend services are running: `docker-compose ps`
   - Verify WebSocket URLs in configuration
   - Check firewall/network connectivity

2. **High latency**  
   - Monitor per-service latency in Grafana
   - Check GPU utilization for STT/TTS services
   - Verify chunk duration settings (250ms recommended)

3. **Audio quality issues**
   - Check sample rate conversion (16kHz mono)
   - Verify audio codec compatibility
   - Monitor audio buffer underruns

4. **Memory leaks**
   - Monitor context buffer sizes
   - Check for orphaned WebSocket connections
   - Verify track cleanup on disconnect

### Debug Commands
```bash
# Check service connectivity
netstat -an | grep :800[1-3]

# Monitor resource usage
docker stats

# View service logs
docker-compose logs -f stt-service
docker-compose logs -f mt-service
docker-compose logs -f tts-service
```

## Development

### Running Tests
```bash
# Integration tests
python test_integration.py

# Unit tests (if available)
python -m pytest tests/

# Load testing
python benchmark_translator.py --concurrent 10
```

### Code Quality
```bash
# Linting
pylint translator_worker.py
black translator_worker.py

# Type checking
mypy translator_worker.py
```

## API Reference

### TranslatorWorker Class
```python
class TranslatorWorker:
    def __init__(self, config: TranslationConfig)
    async def connect_to_room(self, url: str, token: str, room_name: str)
    async def process_participant_audio(self, participant, track)
    async def publish_translation(self, result: TranslationResult)
```

### Configuration Classes
```python
@dataclass
class TranslationConfig:
    stt_model: str = "base"
    chunk_duration_ms: int = 250
    context_length: int = 512
    target_languages: List[str] = ["es", "fr", "de", "it", "pt"]
    voice_presets: Dict[str, str] = {...}
```

## Support

For issues and questions:
1. Check logs and metrics first
2. Run integration tests to isolate issues
3. Consult troubleshooting section
4. Review service-specific documentation in `../services/`