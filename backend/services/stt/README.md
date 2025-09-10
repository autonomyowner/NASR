# STT Service - Streaming Speech-to-Text

A production-ready streaming Speech-to-Text service with LocalAgreement-2 stabilization for The HIVE real-time translation pipeline.

## Features

- **Real-time Streaming**: WebSocket-based streaming with ≤200ms processing latency
- **LocalAgreement-2 Algorithm**: Word stability filtering to minimize retractions (<5%)
- **Voice Activity Detection**: Smart audio processing with silero-vad and WebRTC VAD
- **GPU Optimization**: faster-whisper with CUDA/FP16 precision
- **Audio Chunking**: 150-300ms chunks with overlap for optimal latency/accuracy
- **Performance Monitoring**: Comprehensive metrics and health endpoints
- **Multiple Models**: Support for tiny.en, base.en, small.en models

## Quick Start

### Using Docker (Recommended)

```bash
# Build and run STT service
cd backend/services/stt
docker build -t hive-stt .
docker run -p 8001:8001 hive-stt
```

### Using Docker Compose (Full Stack)

```bash
# Start complete translation pipeline
cd backend/infra
docker-compose up -d stt-service

# Check service health
curl http://localhost:8001/health
```

### Local Development

```bash
# Install dependencies
cd backend/services/stt
pip install -r requirements.txt

# Run service
python app.py
```

## API Endpoints

### WebSocket Streaming

**Endpoint**: `ws://localhost:8001/ws/stt`

Send raw 16-bit PCM audio data (16kHz mono) and receive real-time transcription:

```python
import websockets
import asyncio

async def test_stt():
    uri = "ws://localhost:8001/ws/stt"
    
    async with websockets.connect(uri) as websocket:
        # Send audio chunks
        await websocket.send(audio_chunk_bytes)
        
        # Receive transcription
        response = await websocket.recv()
        print(response)  # JSON with segments and metadata
```

### HTTP Endpoints

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Models**: `GET /models`
- **Performance**: `GET /performance`
- **Batch Transcription**: `POST /transcribe`

## Configuration

### Environment Variables

```bash
MODEL_SIZE=base.en           # tiny.en, base.en, small.en
DEVICE=cuda                  # cuda, cpu, auto
CHUNK_DURATION_MS=250        # Audio chunk size
AGREEMENT_THRESHOLD=2        # LocalAgreement-2 threshold
STABILITY_WINDOW=3           # Stability analysis window
```

### STTConfig Class

```python
class STTConfig:
    MODEL_SIZE = "base.en"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    COMPUTE_TYPE = "float16" if torch.cuda.is_available() else "int8"
    
    # Audio processing
    SAMPLE_RATE = 16000
    CHUNK_DURATION_MS = 250
    OVERLAP_MS = 50
    
    # LocalAgreement-2
    AGREEMENT_THRESHOLD = 2
    STABILITY_WINDOW = 3
    CONFIDENCE_THRESHOLD = 0.7
```

## Testing

### WebSocket Test Client

```bash
# Test with synthetic audio
python test_client.py --mode synthetic --duration 10

# Test with microphone (requires pyaudio)
python test_client.py --mode mic --duration 30

# Test with audio file
python test_client.py --mode file --file test.wav
```

### Performance Benchmarks

```bash
# Run full benchmark suite
python benchmark.py --test all

# Specific tests
python benchmark.py --test latency
python benchmark.py --test accuracy
python benchmark.py --test throughput
```

## Architecture

### Core Components

```
STT Service Architecture
├── FastAPI Application (app.py)
│   ├── WebSocket endpoint (/ws/stt)
│   ├── Health & metrics endpoints
│   └── Batch processing endpoint
│
├── STTSession (per WebSocket connection)
│   ├── AudioProcessor (VAD + chunking)
│   ├── LocalAgreement2 (word stabilization)
│   └── Performance monitoring
│
├── Audio Processing Pipeline
│   ├── VADProcessor (silero-vad/webrtc-vad)
│   ├── AudioChunker (250ms + 50ms overlap)
│   └── Audio normalization
│
├── LocalAgreement-2 Algorithm
│   ├── Word candidate tracking
│   ├── Stability analysis
│   └── Confirmation logic
│
└── Performance Monitoring
    ├── Latency tracking
    ├── Quality metrics
    └── System resource monitoring
```

### Data Flow

```
16kHz PCM Audio → VAD → Chunking → faster-whisper → LocalAgreement-2 → JSON Response
     ↓              ↓        ↓            ↓              ↓
  Raw bytes    Speech detect  250ms    Word-level    Stable words
               (skip silence) chunks   timestamps    + confidence
```

## LocalAgreement-2 Algorithm

The LocalAgreement-2 algorithm minimizes word retractions by requiring agreement across multiple transcription hypotheses:

```python
class LocalAgreement2:
    def __init__(self, agreement_threshold=2, stability_window=3):
        self.threshold = agreement_threshold  # Min agreement count
        self.window = stability_window        # Recent transcriptions
    
    def process_transcription(self, words, confidences, timestamps):
        # Track word candidates across transcriptions
        # Confirm words that appear consistently >= threshold times
        # Return (interim_words, confirmed_words, has_new_confirmations)
```

### Key Features

- **Position-aware matching**: Words must appear at similar positions
- **Confidence filtering**: Only high-confidence words considered
- **Temporal alignment**: Uses timestamps for better matching
- **Memory management**: Automatic cleanup of old confirmations

## Performance Targets

### Latency Requirements

- **Processing Time**: ≤200ms per 250ms chunk
- **Total Latency**: ≤500ms end-to-end (including network)
- **Time-to-First-Token**: ≤450ms for initial word

### Quality Metrics

- **Word Retraction Rate**: <5% (target <2%)
- **Confirmation Rate**: >80% words confirmed within 1 second
- **Confidence Accuracy**: Mean confidence correlates with WER

### System Performance

- **Throughput**: 4+ concurrent sessions on single GPU
- **Memory Usage**: <2GB VRAM for base.en model
- **CPU Usage**: <50% on multi-core systems

## Monitoring

### Health Endpoints

```bash
# Service health
curl http://localhost:8001/health

# Performance metrics
curl http://localhost:8001/performance

# Prometheus metrics
curl http://localhost:8001/metrics
```

### Key Metrics

- `stt_processing_time_ms_p95`: 95th percentile processing time
- `stt_word_retraction_rate`: Word retraction percentage
- `stt_confirmation_rate`: Confirmation efficiency
- `stt_active_sessions`: Current WebSocket sessions
- `stt_chunks_per_second`: Processing throughput

### Grafana Dashboards

Access at http://localhost:3001 with admin/hive2024:

- **STT Performance**: Latency trends and distribution
- **Quality Metrics**: Accuracy and stability tracking  
- **System Resources**: GPU/CPU/Memory utilization
- **Error Tracking**: Failure rates and error analysis

## Production Deployment

### Docker with GPU Support

```yaml
# docker-compose.yml
stt-service:
  build: ../services/stt/
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stt-service
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: stt
        image: hive-stt:latest
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            memory: "2Gi"
            cpu: "1"
```

### Load Balancing

The STT service is stateless and can be horizontally scaled. Each WebSocket connection is handled by a single instance, but multiple instances can run behind a load balancer.

## Development

### Adding New Models

```python
# Update STTConfig
class STTConfig:
    MODEL_SIZE = "large-v2"  # New model
    
# Model will be automatically downloaded on first run
```

### Custom VAD Integration

```python
class CustomVAD:
    def detect_speech(self, audio: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        # Custom VAD logic
        return has_speech, confidence

# Integrate in AudioProcessor
audio_processor = AudioProcessor(vad_method="custom")
```

### Performance Optimization

1. **Model Selection**: Use smallest model that meets accuracy requirements
2. **Batch Processing**: Process multiple chunks together when possible
3. **Memory Management**: Regular cleanup of old session data
4. **GPU Utilization**: Monitor GPU usage and adjust concurrency

## Troubleshooting

### Common Issues

**High Latency**
- Check GPU availability: `nvidia-smi`
- Verify model loading: Check startup logs
- Monitor queue sizes: `/performance` endpoint

**Poor Accuracy**
- Ensure 16kHz mono audio input
- Check VAD sensitivity settings
- Verify LocalAgreement-2 configuration

**Memory Issues**
- Reduce concurrent sessions
- Enable session cleanup in config
- Monitor with `/metrics` endpoint

**WebSocket Disconnections**
- Check network stability
- Verify audio chunk format
- Monitor error logs

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python app.py

# Or in Docker
docker run -e LOG_LEVEL=DEBUG -p 8001:8001 hive-stt
```

## License

This STT service is part of The HIVE translation pipeline. See project root for license information.

## Support

For issues and questions:
- Check health endpoints for service status
- Review benchmark results for performance analysis
- Monitor Grafana dashboards for system health
- Examine logs for error details