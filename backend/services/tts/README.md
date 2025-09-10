# The HIVE TTS Service

High-performance streaming Text-to-Speech service with multi-engine support and sub-250ms time-to-first-audio.

## 🎯 Performance Goals

- **TTFT (Time-to-First-Token)**: ≤ 250ms
- **Streaming Latency**: <100ms between chunks  
- **Quality**: Natural-sounding speech for 10+ languages
- **Throughput**: 100+ concurrent synthesis sessions
- **Availability**: 99.5% uptime with graceful degradation

## 🚀 Quick Start

### Development Setup

```bash
# Install dependencies
cd backend/services/tts
pip install -r requirements.txt

# Start service
python app.py

# Service will be available at http://localhost:8003
```

### Docker Deployment

```bash
# Build and run via docker-compose
cd backend/infra
docker-compose up -d tts-service

# Check logs
docker-compose logs -f tts-service
```

## 🎛️ Engine Support

### 1. XTTS (Premium Quality)
- **Use Case**: High-quality multilingual synthesis
- **TTFT**: ~200-400ms
- **Features**: Voice cloning, emotional expression
- **Languages**: 16+ languages with native-like quality

### 2. Piper (Fast & Lightweight)
- **Use Case**: Low-latency real-time synthesis
- **TTFT**: ~100-200ms 
- **Features**: CPU-optimized, streaming-first
- **Languages**: 50+ voices across major languages

### 3. SpeechT5 (Balanced)
- **Use Case**: Good balance of speed and quality
- **TTFT**: ~150-250ms
- **Features**: HuggingFace integration, customizable
- **Languages**: English with speaker adaptation

### 4. Edge TTS (Cloud Fallback)
- **Use Case**: Fallback when local engines fail
- **TTFT**: ~300-500ms (network dependent)
- **Features**: Microsoft Neural voices
- **Languages**: 100+ voices, all major languages

### 5. Kokoro (Ultra-Low Latency)
- **Use Case**: Real-time conversation synthesis
- **TTFT**: <100ms (target)
- **Features**: Streaming-optimized architecture
- **Languages**: Japanese optimized, extensible

## 🗣️ Voice Library

### Premium Voices (Clone Capable)
```
English:  Sarah, David (General American)
Spanish:  Sofía (Mexican), Carlos (Castilian)  
French:   Léa (Parisian), Antoine (Québécois)
German:   Anna (Standard), Hans (Austrian)
Italian:  Giulia (Standard), Marco (Roman)
Portuguese: Ana (Brazilian), João (European)
Japanese: Yuki (Tokyo), Hiroshi (Osaka)
```

### Quality Tiers
- **Fast**: <150ms TTFT, basic quality
- **Standard**: <250ms TTFT, conversational quality
- **Premium**: <400ms TTFT, broadcast quality

## 🔧 API Usage

### WebSocket Streaming (Recommended)

```python
import websockets
import json

async def synthesize_streaming():
    uri = "ws://localhost:8003/ws/synthesize"
    
    async with websockets.connect(uri) as websocket:
        request = {
            "text": "Hello, this is a streaming synthesis test!",
            "voice_id": "en-us-female-premium",
            "language": "en", 
            "engine": "xtts",
            "stream": true
        }
        
        await websocket.send(json.dumps(request))
        
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get("audio_chunk"):
                # Process audio chunk
                audio_bytes = base64.b64decode(data["audio_chunk"])
                # Feed to audio output or LiveKit track
            
            if data.get("is_final"):
                break
```

### HTTP Batch Synthesis

```python
import requests

response = requests.post("http://localhost:8003/synthesize", json={
    "text": "Hello world!",
    "voice_id": "en-us-female-premium", 
    "language": "en",
    "engine": "xtts"
})

audio_data = response.json()["audio_data"]
```

### Voice Discovery

```python
# List all voices
voices = requests.get("http://localhost:8003/voices").json()

# Get voices for specific language
fr_voices = requests.get("http://localhost:8003/voices/fr").json()
```

## 📊 Monitoring & Metrics

### Health Check
```bash
curl http://localhost:8003/health
```

### Prometheus Metrics
```bash
curl http://localhost:8003/metrics
```

### Key Metrics
- `tts_synthesis_requests_total`: Request counter by engine/language
- `tts_ttft_duration_seconds`: Time-to-first-token latency
- `tts_synthesis_duration_seconds`: Total synthesis time
- `tts_active_sessions`: Concurrent synthesis sessions
- `tts_audio_quality_score`: Audio quality scores (MOS)

### Performance Benchmarking

```bash
# Run comprehensive benchmark
python test_tts.py --all --iterations 20 --connections 50

# TTFT benchmark only  
python test_tts.py --benchmark --iterations 100

# Stress test
python test_tts.py --stress --connections 100
```

## 🔧 Configuration

### Engine Selection Logic
```yaml
# config.yaml
engines:
  selection_strategy: "auto"  # auto, manual, quality_first, speed_first
  
  auto_selection:
    ttft_threshold_ms: 250
    quality_threshold: 3.0
    fallback_chain: ["piper", "speecht5", "edge-tts"]
```

### Voice Cloning
```python
# Clone voice from 3-10 seconds of reference audio
async def clone_and_synthesize():
    reference_audio = load_audio("reference.wav")
    
    request = {
        "text": "This will sound like the reference voice!",
        "voice_clone_reference": base64.b64encode(reference_audio),
        "voice_id": "en-us-female-premium",
        "language": "en",
        "engine": "xtts"  # Only XTTS supports cloning
    }
```

## 🧪 Testing

### Unit Tests
```bash
pytest tests/ -v
```

### Integration Tests
```bash
python test_tts.py --all
```

### Performance Tests
```bash
# Latency benchmark
python test_tts.py --benchmark --iterations 100

# Concurrent connections
python test_tts.py --stress --connections 200

# Audio quality validation
python test_tts.py --quality
```

## 🛠️ Development

### Adding New Engines

1. Implement engine interface:
```python
class CustomTTSEngine:
    async def synthesize(self, text: str, voice_id: str, language: str) -> AsyncGenerator[np.ndarray, None]:
        # Your implementation here
        pass
```

2. Register in service:
```python
tts_service.engines[TTSEngine.CUSTOM] = CustomTTSEngine()
```

### Adding New Voices

```python
voice_config = VoiceConfig(
    voice_id="custom-voice-id",
    name="Custom Voice",
    language="en",
    gender="female",
    supported_engines=[TTSEngine.XTTS],
    quality_tier="premium"
)

tts_service.voice_manager.voices[voice_config.voice_id] = voice_config
```

## 🚀 Production Deployment

### Resource Requirements

**Minimum (CPU-only):**
- 4 CPU cores
- 8GB RAM  
- 50GB storage

**Recommended (GPU):**
- 8 CPU cores
- 16GB RAM
- 1x GPU (8GB+ VRAM)
- 100GB NVMe storage

### Scaling Configuration

```yaml
# docker-compose.yml
tts-service:
  deploy:
    replicas: 3
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Monitoring Setup

1. **Prometheus**: Metrics collection
2. **Grafana**: Performance dashboards  
3. **Jaeger**: Distributed tracing
4. **AlertManager**: SLA violation alerts

## 🔍 Troubleshooting

### Common Issues

**High TTFT Latency:**
```bash
# Check GPU utilization
nvidia-smi

# Switch to faster engine
curl -X POST http://localhost:8003/synthesize -d '{"engine": "piper"}'

# Reduce text length
curl -X POST http://localhost:8003/synthesize -d '{"text": "Short text"}'
```

**Memory Issues:**
```bash
# Check memory usage
curl http://localhost:8003/health | jq '.memory_usage'

# Force garbage collection
curl -X POST http://localhost:8003/gc
```

**Audio Quality Problems:**
```bash
# Test audio enhancement
curl http://localhost:8003/synthesize?enhance_audio=true

# Check quality scores
curl http://localhost:8003/metrics | grep quality_score
```

### Performance Tuning

1. **GPU Optimization:**
   - Enable mixed precision (FP16)
   - Increase GPU memory allocation
   - Use tensor parallelism for large models

2. **CPU Optimization:**  
   - Increase worker processes
   - Enable NUMA optimization
   - Use optimized BLAS libraries

3. **Memory Management:**
   - Configure model caching strategy
   - Adjust voice embedding cache size
   - Enable audio chunk streaming

## 📈 Roadmap

### v2.1 (Q4 2024)
- [ ] Real-time voice conversion
- [ ] Emotional expression controls
- [ ] Advanced prosody modeling
- [ ] Multi-speaker synthesis

### v2.2 (Q1 2025)
- [ ] Streaming voice cloning (<1s reference)
- [ ] Cross-lingual voice transfer  
- [ ] Real-time accent adaptation
- [ ] Neural codec integration

### v3.0 (Q2 2025)
- [ ] End-to-end streaming pipeline
- [ ] Sub-100ms TTFT for all engines
- [ ] Conversational synthesis modes
- [ ] Advanced quality metrics (PESQ, STOI)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`python test_tts.py --all`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## 📄 License

This project is part of The HIVE translation pipeline. All rights reserved.

---

**The HIVE TTS Service** - Breaking language barriers with natural, real-time speech synthesis.