# The HIVE Translation System - Troubleshooting Guide

## Quick Reference

### Emergency Contacts
- **On-Call Engineer**: oncall@thehive.com | Slack: #oncall
- **Platform Team**: platform@thehive.com | Slack: #platform  
- **Translation Team**: ml-team@thehive.com | Slack: #translation

### Service Status Dashboard
- **Grafana**: https://monitoring.yourdomain.com:3001
- **Prometheus**: https://monitoring.yourdomain.com:9090
- **Service Health**: https://api.yourdomain.com/health

---

## 🚨 Critical Issues - Immediate Action Required

### 1. Translation SLO Breach (>500ms End-to-End)

**Symptoms:**
- Grafana alerts: "Translation TTFT SLO Breach"
- User reports of delayed translations
- p95 latency >500ms sustained for >2 minutes

**Immediate Actions:**

```bash
# 1. Check system resources
docker stats | grep -E "(stt|mt|tts|translator)"

# 2. Verify GPU availability
nvidia-smi

# 3. Check service health
curl -f http://localhost:8001/health  # STT
curl -f http://localhost:8002/health  # MT
curl -f http://localhost:8003/health  # TTS

# 4. Scale translator workers if resources allow
docker-compose up -d --scale translator-worker=4

# 5. Check queue depths
curl -s http://localhost:8001/performance | jq '.queue_depth'
curl -s http://localhost:8002/performance | jq '.queue_depth' 
curl -s http://localhost:8003/performance | jq '.queue_depth'
```

**Root Cause Analysis:**

```bash
# Latency breakdown analysis
curl -s http://localhost:8080/traces/recent | jq '
.traces[0:10] | map({
  total: .duration_ms,
  stt: (.spans[] | select(.name=="stt") | .duration_ms),
  mt: (.spans[] | select(.name=="mt") | .duration_ms),
  tts: (.spans[] | select(.name=="tts") | .duration_ms)
})
'

# Common bottlenecks:
# - STT >200ms: GPU overload, model too large
# - MT >100ms: Context buffer overflow, model switching
# - TTS >400ms: Voice loading delay, synthesis queue
```

**Mitigation Steps:**

```bash
# If STT is bottleneck (>200ms):
# Switch to faster model
curl -X POST http://localhost:8001/config \
  -d '{"model_size": "tiny.en"}'

# If MT is bottleneck (>100ms):  
# Reduce context length
curl -X POST http://localhost:8002/config \
  -d '{"context_length": 256}'

# If TTS is bottleneck (>400ms):
# Switch to faster engine
curl -X POST http://localhost:8003/config \
  -d '{"default_engine": "piper"}'
```

### 2. Complete Service Outage

**Symptoms:**
- All translation requests failing
- LiveKit rooms not accessible
- Health checks returning errors

**Immediate Actions:**

```bash
# 1. Check core services
docker-compose ps

# 2. Restart failed services
FAILED_SERVICES=$(docker-compose ps --services --filter "status=exited")
for service in $FAILED_SERVICES; do
    echo "Restarting $service..."
    docker-compose restart $service
    sleep 10
done

# 3. Verify LiveKit SFU
curl -f http://localhost:7880/health || {
    echo "LiveKit down - checking dependencies..."
    docker-compose restart redis
    sleep 15
    docker-compose restart livekit
}

# 4. Check TURN server
systemctl status coturn || {
    echo "CoTURN down - restarting..."
    systemctl restart coturn
}
```

**If issues persist:**

```bash
# Nuclear option - full stack restart (coordinate with users)
docker-compose down
sleep 30
docker-compose up -d

# Verify recovery
sleep 60
./health-check.sh
```

### 3. Audio Connection Failures

**Symptoms:**
- WebRTC connections failing  
- No audio in LiveKit rooms
- TURN server errors

**Immediate Actions:**

```bash
# 1. Test STUN/TURN connectivity
./backend/infra/network-testing/latency-validator.py

# 2. Check CoTURN server
docker-compose logs coturn | tail -50

# 3. Verify port accessibility
nmap -p 3478,5349,50000-50199 your-server-ip

# 4. Test WebRTC from browser
# Navigate to chrome://webrtc-internals/
# Look for connection failures or ICE gathering issues
```

**Common Fixes:**

```bash
# Update STUN/TURN configuration
docker-compose exec coturn cat /etc/turnserver.conf | grep -E "(realm|server-name)"

# Restart with fresh credentials
docker-compose restart coturn auth-service

# Check firewall rules
sudo ufw status | grep -E "(3478|5349|50000:50199)"
```

---

## ⚠️ Performance Issues - Response Within 15 Minutes

### High Latency (400-500ms)

**Investigation Steps:**

```bash
# 1. Latency breakdown
curl -s http://localhost:8080/metrics | grep -E "translation_.*_p95"

# 2. Resource utilization
htop
iostat -x 1 5
nvidia-smi -l 1

# 3. Network latency
ping -c 10 localhost  # Should be <1ms
ping -c 10 stt-service
ping -c 10 mt-service  
ping -c 10 tts-service
```

**Performance Optimization:**

```bash
# Enable performance mode
curl -X POST http://localhost:8001/config \
  -d '{"performance_mode": true, "chunk_duration_ms": 200}'

curl -X POST http://localhost:8002/config \
  -d '{"enable_batching": true, "batch_size": 4}'

curl -X POST http://localhost:8003/config \
  -d '{"streaming_mode": true, "chunk_size": 512}'

# Monitor improvements
watch 'curl -s http://localhost:8080/metrics | grep translation_ttft_p95'
```

### Memory Leaks

**Detection:**

```bash
# Monitor memory growth
docker stats --no-stream | grep -E "(stt|mt|tts)"

# Check for memory leaks over time
for i in {1..5}; do
    docker stats --no-stream | grep -E "(stt|mt|tts)"
    sleep 60
done
```

**Mitigation:**

```bash
# Force garbage collection
curl -X POST http://localhost:8001/gc
curl -X POST http://localhost:8002/gc
curl -X POST http://localhost:8003/gc

# If memory continues growing, restart service
docker-compose restart stt-service
```

### High CPU Usage

**Investigation:**

```bash
# Top CPU consumers
docker stats --no-stream | sort -k3 -nr

# Check for runaway processes
docker exec stt-service top -b -n1 | head -20
docker exec mt-service top -b -n1 | head -20
docker exec tts-service top -b -n1 | head -20
```

**Optimization:**

```bash
# Reduce concurrent processing
curl -X POST http://localhost:8001/config \
  -d '{"max_concurrent_sessions": 2}'

# Enable CPU optimizations
curl -X POST http://localhost:8002/config \
  -d '{"cpu_threads": 4, "enable_mkl": true}'
```

---

## 🔧 Service-Specific Issues

### STT Service Problems

#### Poor Transcription Accuracy

**Symptoms:**
- Low confidence scores (<0.7)
- Incorrect transcriptions
- Missing words or phrases

**Troubleshooting:**

```bash
# Check input audio quality
curl -s http://localhost:8001/performance | jq '.audio_quality_stats'

# Verify model selection
curl -s http://localhost:8001/config | jq '.model_size'

# Test with known good audio
curl -X POST http://localhost:8001/transcribe \
  -F "audio=@test-audio.wav" \
  -F "model_size=base.en"
```

**Solutions:**

```bash
# Switch to larger, more accurate model
curl -X POST http://localhost:8001/config \
  -d '{"model_size": "small.en"}'

# Adjust VAD sensitivity  
curl -X POST http://localhost:8001/config \
  -d '{"vad_threshold": 0.3}'

# Enable preprocessing
curl -X POST http://localhost:8001/config \
  -d '{"enable_preprocessing": true, "noise_reduction": true}'
```

#### High Word Retraction Rate (>5%)

**Symptoms:**
- Frequent text corrections
- LocalAgreement-2 instability
- Users reporting inconsistent captions

**Troubleshooting:**

```bash
# Check agreement algorithm settings
curl -s http://localhost:8001/performance | jq '.localagreement2_stats'

# Monitor word stability
curl -s http://localhost:8001/performance | jq '.word_retraction_rate'
```

**Solutions:**

```bash
# Increase stability window
curl -X POST http://localhost:8001/config \
  -d '{"stability_window": 5, "agreement_threshold": 3}'

# Reduce chunk overlap
curl -X POST http://localhost:8001/config \
  -d '{"chunk_overlap_ms": 25}'
```

### MT Service Problems

#### Translation Quality Issues

**Symptoms:**
- Nonsensical translations
- Context not preserved
- Wrong language detection

**Troubleshooting:**

```bash
# Check confidence distribution
curl -s http://localhost:8002/performance | jq '.confidence_distribution'

# Test specific language pair
curl -X POST http://localhost:8002/translate \
  -d '{"text": "Test sentence", "source_language": "en", "target_language": "es"}'

# Verify model loading
curl -s http://localhost:8002/models | jq '.loaded_models'
```

**Solutions:**

```bash
# Force model reload
curl -X POST http://localhost:8002/models/reload \
  -d '{"language_pair": "en-es"}'

# Increase context window
curl -X POST http://localhost:8002/config \
  -d '{"context_length": 1024}'

# Enable quality filters
curl -X POST http://localhost:8002/config \
  -d '{"min_confidence": 0.8, "enable_quality_filter": true}'
```

#### Slow Translation Speed (>100ms)

**Symptoms:**
- MT latency consistently high
- Queue backlog growing
- Users experiencing delays

**Troubleshooting:**

```bash
# Check processing time breakdown
curl -s http://localhost:8002/performance | jq '.processing_breakdown'

# Monitor queue status
curl -s http://localhost:8002/queue | jq '.depth'

# Check model optimization
curl -s http://localhost:8002/models | jq '.optimization_status'
```

**Solutions:**

```bash
# Enable model optimization
curl -X POST http://localhost:8002/optimize \
  -d '{"enable_onnx": true, "enable_tensorrt": true}'

# Increase batch processing
curl -X POST http://localhost:8002/config \
  -d '{"batch_size": 8, "batch_timeout_ms": 50}'

# Scale MT service
docker-compose up -d --scale mt-service=2
```

### TTS Service Problems

#### Slow Synthesis (>400ms TTFT)

**Symptoms:**
- Long delays before audio output
- TTFT consistently above target
- Audio choppy or delayed

**Troubleshooting:**

```bash
# Check synthesis time breakdown
curl -s http://localhost:8003/performance | jq '.ttft_breakdown'

# Monitor voice loading times
curl -s http://localhost:8003/voices | jq '.loading_times'

# Check engine performance
curl -s http://localhost:8003/engines | jq '.performance_stats'
```

**Solutions:**

```bash
# Preload commonly used voices
curl -X POST http://localhost:8003/voices/preload \
  -d '{"voice_ids": ["es-female-premium", "en-us-male-1"]}'

# Switch to faster engine for speed-critical use
curl -X POST http://localhost:8003/config \
  -d '{"default_engine": "piper", "quality_mode": "fast"}'

# Enable streaming synthesis
curl -X POST http://localhost:8003/config \
  -d '{"streaming_enabled": true, "chunk_size": 512}'
```

#### Poor Audio Quality

**Symptoms:**
- Robotic or distorted audio
- Low quality scores (<3.5)
- User complaints about audio

**Troubleshooting:**

```bash
# Check quality metrics
curl -s http://localhost:8003/performance | jq '.audio_quality_scores'

# Test different engines
for engine in xtts piper speecht5; do
    curl -X POST http://localhost:8003/synthesize \
        -d "{\"text\": \"Quality test\", \"engine\": \"$engine\"}" | \
        jq '.quality_score'
done
```

**Solutions:**

```bash
# Switch to higher quality engine
curl -X POST http://localhost:8003/config \
  -d '{"default_engine": "xtts", "quality_mode": "premium"}'

# Adjust synthesis parameters
curl -X POST http://localhost:8003/config \
  -d '{"speaking_rate": 0.95, "enable_enhancement": true}'

# Use premium voices
curl -X POST http://localhost:8003/config \
  -d '{"prefer_premium_voices": true}'
```

---

## 🌐 Network and Connectivity Issues

### WebRTC Connection Failures

**Symptoms:**
- ICE connection failures
- Audio not flowing between participants
- Intermittent disconnections

**Diagnosis:**

```bash
# Test STUN server
stun-client stun.yourdomain.com 3478

# Check TURN server logs
docker-compose logs coturn | grep -E "(allocation|relay)"

# Verify certificate validity
echo | openssl s_client -connect turn.yourdomain.com:5349 | \
  openssl x509 -noout -dates
```

**Solutions:**

```bash
# Update TURN server configuration
cat > /etc/turnserver.conf << 'EOF'
listening-port=3478
tls-listening-port=5349
external-ip=YOUR_PUBLIC_IP
realm=turn.yourdomain.com
server-name=turn.yourdomain.com
lt-cred-mech
user=turnuser:turnpass
cert=/etc/ssl/turn_cert.pem
pkey=/etc/ssl/turn_key.pem
EOF

systemctl restart coturn

# Test connectivity after changes
./backend/infra/network-testing/latency-validator.py
```

### High Packet Loss

**Symptoms:**
- Audio quality degradation
- Choppy or intermittent audio
- WebRTC statistics showing packet loss >1%

**Investigation:**

```bash
# Check network statistics
ss -tuln | grep -E "(3478|5349|7880)"

# Monitor packet loss
ping -c 100 -i 0.1 your-server-ip | \
  grep "packet loss"

# Check bandwidth utilization
iftop -t -s 10
```

**Mitigation:**

```bash
# Adjust audio codec settings
curl -X POST http://localhost:7880/rooms/your-room/participants/config \
  -d '{"audio_codec": "opus", "bitrate": 64000}'

# Enable adaptive bitrate
curl -X POST http://localhost:7880/config \
  -d '{"enable_adaptive_stream": true, "min_bitrate": 32000}'
```

### DNS Resolution Issues

**Symptoms:**
- Service discovery failures
- Intermittent connection timeouts
- Certificate validation errors

**Diagnosis:**

```bash
# Test DNS resolution
nslookup sfu.yourdomain.com
nslookup turn.yourdomain.com
nslookup api.yourdomain.com

# Check /etc/hosts file
grep -E "(sfu|turn|api)\.yourdomain\.com" /etc/hosts
```

**Solutions:**

```bash
# Add explicit DNS entries
echo "YOUR_SERVER_IP sfu.yourdomain.com turn.yourdomain.com api.yourdomain.com" >> /etc/hosts

# Verify resolution
for host in sfu.yourdomain.com turn.yourdomain.com api.yourdomain.com; do
    echo "Testing $host..."
    curl -I https://$host/health
done
```

---

## 🔐 Security Issues

### Certificate Expiration

**Symptoms:**
- HTTPS connection errors
- WebRTC DTLS failures
- Browser security warnings

**Check Certificate Status:**

```bash
# Check all certificates
for domain in sfu.yourdomain.com turn.yourdomain.com api.yourdomain.com; do
    echo "Checking $domain..."
    echo | openssl s_client -servername $domain -connect $domain:443 2>/dev/null | \
    openssl x509 -noout -dates
done
```

**Renew Certificates:**

```bash
# Automatic renewal
certbot renew --quiet

# Manual renewal if needed
certbot certonly --standalone -d sfu.yourdomain.com
certbot certonly --standalone -d turn.yourdomain.com  
certbot certonly --standalone -d api.yourdomain.com

# Update certificate locations
cp /etc/letsencrypt/live/*/fullchain.pem /etc/ssl/thehive/
cp /etc/letsencrypt/live/*/privkey.pem /etc/ssl/thehive/

# Restart services
docker-compose restart nginx coturn
```

### Authentication Failures

**Symptoms:**
- JWT token validation errors
- Room access denied
- TURN authentication failures

**Troubleshooting:**

```bash
# Test token generation
curl -X POST http://localhost:8004/auth/token/room \
  -H "Authorization: Bearer $AUTH_SERVICE_API_KEY" \
  -d '{"room_name": "test", "participant_name": "test-user"}'

# Verify TURN credentials
curl -X POST http://localhost:8004/auth/credentials/turn \
  -H "Authorization: Bearer $AUTH_SERVICE_API_KEY" \
  -d '{"room_name": "test", "participant_name": "test-user"}'
```

**Solutions:**

```bash
# Regenerate secret keys
export LIVEKIT_SECRET_KEY=$(openssl rand -hex 32)
export AUTH_SERVICE_API_KEY=$(openssl rand -hex 32)  
export TURN_SECRET_KEY=$(openssl rand -hex 32)

# Update configuration
sed -i "s/LIVEKIT_SECRET_KEY=.*/LIVEKIT_SECRET_KEY=$LIVEKIT_SECRET_KEY/" .env
sed -i "s/AUTH_SERVICE_API_KEY=.*/AUTH_SERVICE_API_KEY=$AUTH_SERVICE_API_KEY/" .env
sed -i "s/TURN_SECRET_KEY=.*/TURN_SECRET_KEY=$TURN_SECRET_KEY/" .env

# Restart services
docker-compose restart auth-service livekit coturn
```

---

## 🔍 Debugging Tools and Commands

### Log Analysis

```bash
# Centralized logging
docker-compose logs --tail=100 -f

# Service-specific logs
docker-compose logs --tail=100 stt-service | grep ERROR
docker-compose logs --tail=100 mt-service | grep WARN
docker-compose logs --tail=100 tts-service | grep INFO

# Filter by timestamp (last 1 hour)
docker-compose logs --since "1h" | grep ERROR
```

### Performance Analysis

```bash
# Real-time metrics
watch 'curl -s http://localhost:8080/metrics | grep -E "translation_.*_p95"'

# Resource monitoring
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# GPU monitoring
nvidia-smi -l 1
```

### Network Debugging

```bash
# Port connectivity
for port in 3478 5349 7880 8001 8002 8003 8004; do
    echo "Testing port $port..."
    nc -zv localhost $port
done

# Bandwidth testing
iperf3 -s -p 5001 &  # Start server
iperf3 -c localhost -p 5001 -t 10  # Test bandwidth
```

### Database and State

```bash
# Redis state
redis-cli info
redis-cli keys "*"

# LiveKit room status
curl -s http://localhost:7880/rooms | jq '.rooms[] | {name: .name, participants: .num_participants}'

# Service configurations
curl -s http://localhost:8001/config | jq .
curl -s http://localhost:8002/config | jq .
curl -s http://localhost:8003/config | jq .
```

---

## 📋 Health Check Scripts

### Automated Health Check

```bash
#!/bin/bash
# health-check.sh

FAILED=0

echo "=== The HIVE Translation System Health Check ==="
echo "Timestamp: $(date)"
echo

# Core services
for service in livekit:7880 stt:8001 mt:8002 tts:8003 auth:8004; do
    name=${service%:*}
    port=${service#*:}
    
    if curl -f -s http://localhost:$port/health >/dev/null 2>&1; then
        echo "✓ $name service is healthy"
    else
        echo "✗ $name service health check failed"
        FAILED=1
    fi
done

# Dependencies
if redis-cli ping >/dev/null 2>&1; then
    echo "✓ Redis is healthy"
else
    echo "✗ Redis health check failed"
    FAILED=1
fi

if nc -z localhost 3478; then
    echo "✓ CoTURN is healthy"
else
    echo "✗ CoTURN health check failed"
    FAILED=1
fi

# Performance checks
TTFT_P95=$(curl -s http://localhost:8080/metrics | grep 'translation_ttft_p95' | awk '{print $2}' | head -1)
if [ $(echo "$TTFT_P95 < 500" | bc) -eq 1 ]; then
    echo "✓ TTFT SLO met (${TTFT_P95}ms < 500ms)"
else
    echo "⚠ TTFT SLO at risk (${TTFT_P95}ms >= 500ms)"
fi

echo
if [ $FAILED -eq 0 ]; then
    echo "🎉 All systems healthy"
    exit 0
else
    echo "❌ Some systems require attention"
    exit 1
fi
```

### SLO Validation Script

```bash
#!/bin/bash
# slo-check.sh

echo "=== SLO Status Check ==="

# TTFT SLO (≤450ms)
TTFT=$(curl -s http://localhost:8080/metrics | grep 'translation_ttft_p95' | awk '{print $2}')
if [ $(echo "$TTFT <= 450" | bc) -eq 1 ]; then
    echo "✓ TTFT SLO: ${TTFT}ms (target: ≤450ms)"
else
    echo "✗ TTFT SLO BREACH: ${TTFT}ms (target: ≤450ms)"
fi

# Caption Latency SLO (≤250ms)  
CAPTION=$(curl -s http://localhost:8080/metrics | grep 'caption_latency_p95' | awk '{print $2}')
if [ $(echo "$CAPTION <= 250" | bc) -eq 1 ]; then
    echo "✓ Caption Latency SLO: ${CAPTION}ms (target: ≤250ms)"
else
    echo "✗ Caption Latency SLO BREACH: ${CAPTION}ms (target: ≤250ms)"
fi

# Word Retraction Rate SLO (<5%)
RETRACTION=$(curl -s http://localhost:8001/performance | jq -r '.word_retraction_rate')
if [ $(echo "$RETRACTION < 0.05" | bc) -eq 1 ]; then
    echo "✓ Word Retraction SLO: ${RETRACTION}% (target: <5%)"
else
    echo "✗ Word Retraction SLO BREACH: ${RETRACTION}% (target: <5%)"
fi
```

---

## 📞 Escalation Procedures

### Level 1 - On-Call Response (0-15 minutes)
- Critical SLO breaches
- Complete service outages
- Security incidents

**Actions:**
1. Execute immediate mitigation steps
2. Notify #oncall Slack channel
3. Update status page if available
4. Document actions taken

### Level 2 - Platform Team (15-60 minutes)
- Persistent performance issues
- Complex technical problems
- Infrastructure failures

**Actions:**
1. Engage platform engineering team
2. Start incident bridge if needed
3. Coordinate with stakeholders
4. Implement temporary workarounds

### Level 3 - Engineering Leadership (1+ hours)
- System design issues
- Major architectural changes needed
- Customer impact assessment

**Actions:**
1. Escalate to engineering management
2. Prepare detailed incident report
3. Plan post-incident review
4. Coordinate external communications

---

## 🆕 New Component Troubleshooting

### Recording System Issues

**Issue**: Recording not working or files corrupted

```bash
# Check browser recording support
# In browser console:
console.log('MediaRecorder supported:', typeof MediaRecorder !== 'undefined');
console.log('Supported types:', [
  'audio/webm;codecs=opus',
  'audio/mp4;codecs=mp4a.40.2',
  'audio/wav'
].filter(type => MediaRecorder.isTypeSupported(type)));

# Check recording permissions and storage
# Verify sufficient disk space for recordings
df -h /tmp
ls -la /tmp/recordings/
```

### Translation UI Component Issues

**Issue**: Captions not displaying or incorrect confidence indicators

```bash
# Check caption service connectivity
curl -s http://localhost:8001/captions/status

# Verify WebSocket connection for real-time captions
# In browser DevTools → Network → WS tab
# Look for captions WebSocket connection

# Check caption processing performance
curl -s http://localhost:8001/performance | jq '.caption_processing_time_ms'
```

### Accessibility Feature Issues

**Issue**: Screen reader not working or keyboard shortcuts not responding

```bash
# Check ARIA attribute implementation
# In browser DevTools → Accessibility tab
# Verify all interactive elements have proper labels

# Test keyboard navigation programmatically
# In browser console:
document.addEventListener('keydown', (e) => {
  console.log('Key pressed:', e.key, 'Target:', e.target.tagName);
});

# Check accessibility settings persistence
localStorage.getItem('accessibility-settings');
```

### WebAssembly (RNNoise) Issues

**Issue**: RNNoise not loading or poor performance

```bash
# Check WebAssembly support
# In browser console:
console.log('WebAssembly supported:', typeof WebAssembly !== 'undefined');

# Check RNNoise module loading
# Monitor Network tab for .wasm file downloads
# Check for CORS issues with WASM files

# Performance monitoring
# Enable in development with:
export ENABLE_RNNOISE_DEBUG=true
```

### Auth Service Token Issues

**Issue**: JWT tokens not generating or validation failing

```bash
# Test token generation
curl -X POST http://localhost:8004/auth/token/room \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_SERVICE_API_KEY" \
  -d '{
    "room_name": "test-room",
    "participant_name": "test-user",
    "role": "speaker"
  }'

# Verify JWT token structure
# Use jwt.io to decode token and check claims

# Check key rotation status
curl -s http://localhost:8004/admin/key-rotation-status
```

This troubleshooting guide should be updated regularly based on new issues encountered and solutions discovered. Keep it accessible to all team members and ensure procedures are tested during maintenance windows.

**Document Version**: 1.1  
**Last Updated**: 2024-01-01  
**Next Review**: 2024-02-01  
**Covers**: Complete system including new recording, accessibility, and WebAssembly components