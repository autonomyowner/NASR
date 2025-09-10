# The HIVE Translation System - Operations Runbook

## System Overview

The HIVE Translation System is a production-grade real-time voice translation platform delivering sub-500ms end-to-end translation latency. This runbook provides comprehensive operational procedures for deployment, monitoring, and maintenance of the system.

### Architecture at a Glance

```
Production Architecture
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Load Balancer  │    │   LiveKit SFU    │    │  Translation     │
│   (nginx/HAProxy)│───▶│   WebRTC Router  │───▶│  Services        │
│   SSL Termination│    │   Port: 7880     │    │  STT/MT/TTS      │
└──────────────────┘    └──────────────────┘    └──────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   CoTURN Server  │    │   Auth Service   │    │  Observability   │
│   STUN/TURN      │    │   JWT Tokens     │    │  Monitoring      │
│   Port: 3478     │    │   Port: 8004     │    │  Grafana/Prom    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### SLO Definitions and Monitoring Dashboards

| SLO Metric | Target | Critical Threshold | Dashboard |
|------------|--------|-------------------|-----------|
| **Time-to-First-Token (TTFT)** | p95 ≤ 450ms | p95 > 500ms | Translation SLOs |
| **Caption Latency** | p95 ≤ 250ms | p95 > 300ms | User Experience |
| **Word Retraction Rate** | <5% | >8% | Quality Metrics |
| **End-to-End Latency** | <500ms | >600ms | Service Performance |
| **Service Availability** | >99.5% | <99% | System Health |

### Emergency Contact Information

| Role | Contact | Primary | Secondary |
|------|---------|---------|-----------|
| **On-Call Engineer** | oncall@thehive.com | +1-XXX-XXX-XXXX | Slack: #oncall |
| **Platform Lead** | platform@thehive.com | +1-XXX-XXX-XXXX | Slack: #platform |
| **Translation Team** | ml-team@thehive.com | +1-XXX-XXX-XXXX | Slack: #translation |
| **Infrastructure** | infra@thehive.com | +1-XXX-XXX-XXXX | Slack: #infrastructure |

## Service Health Monitoring

### Dashboard URLs and Key Metrics

**Primary Dashboards:**
- **Grafana**: https://monitoring.yourdomain.com:3001 (admin/secure_password)
- **Prometheus**: https://monitoring.yourdomain.com:9090
- **Jaeger Tracing**: https://monitoring.yourdomain.com:16686
- **LiveKit Dashboard**: https://sfu.yourdomain.com:7880

**Critical Metrics to Monitor:**

```bash
# Translation Pipeline Metrics
translation_ttft_p95_ms              # Time-to-first-token latency
caption_display_latency_p95_ms       # Caption rendering delay  
word_retraction_rate                 # LocalAgreement-2 stability
concurrent_translation_sessions      # Active sessions

# Service Health Metrics
service_up{job="stt-service"}        # STT service availability
service_up{job="mt-service"}         # MT service availability
service_up{job="tts-service"}        # TTS service availability
service_up{job="livekit"}            # LiveKit SFU availability

# System Resource Metrics
node_cpu_utilization                 # CPU usage across nodes
node_memory_utilization              # Memory usage across nodes
nvidia_gpu_utilization               # GPU usage for ML services
disk_space_usage                     # Storage utilization

# Network Performance Metrics
webrtc_connection_success_rate       # WebRTC connection success
packet_loss_rate                     # Network quality
jitter_ms                           # Network stability
bandwidth_utilization_mbps           # Network throughput
```

### Health Check Endpoints and Expected Responses

```bash
# Core Services Health Checks
curl -f https://api.yourdomain.com/health/livekit
# Expected: {"status": "healthy", "version": "1.4.3", "uptime": 86400}

curl -f https://api.yourdomain.com/health/stt
# Expected: {"status": "healthy", "model": "base.en", "gpu_available": true}

curl -f https://api.yourdomain.com/health/mt  
# Expected: {"status": "healthy", "languages": ["en-es", "en-fr"], "latency_p95_ms": 45}

curl -f https://api.yourdomain.com/health/tts
# Expected: {"status": "healthy", "engines": ["xtts", "piper"], "voices_loaded": 12}

curl -f https://api.yourdomain.com/health/auth
# Expected: {"status": "healthy", "jwt_service": "operational", "turn_available": true}

# Dependency Health Checks  
curl -f https://api.yourdomain.com/health/redis
# Expected: {"status": "healthy", "connected_clients": 3, "memory_usage": "45MB"}

curl -f https://api.yourdomain.com/health/coturn
# Expected: {"status": "healthy", "active_allocations": 15, "total_sent": "1.2GB"}
```

### Performance Baseline Expectations

**Translation Pipeline Performance:**
- STT Processing: 150-200ms per 250ms chunk
- MT Translation: 20-80ms per segment
- TTS Synthesis: 200-400ms TTFT
- End-to-End: <500ms total latency

**System Resource Baselines:**
- CPU Utilization: <60% average, <80% peak
- Memory Usage: <70% average, <85% peak
- GPU Utilization: <75% average, <90% peak
- Disk Usage: <80% capacity

## Common Operations

### Service Restart Procedures

**1. Rolling Restart of Translation Services**
```bash
# STT Service rolling restart
cd backend/infra
docker-compose restart stt-service
sleep 30
curl -f http://localhost:8001/health || echo "STT restart failed"

# MT Service rolling restart
docker-compose restart mt-service
sleep 15  
curl -f http://localhost:8002/health || echo "MT restart failed"

# TTS Service rolling restart
docker-compose restart tts-service
sleep 45  # TTS takes longer due to model loading
curl -f http://localhost:8003/health || echo "TTS restart failed"
```

**2. LiveKit SFU Restart (Coordinate with active sessions)**
```bash
# Check active rooms first
curl -s http://localhost:7880/rooms | jq '.rooms | length'

# If active sessions exist, coordinate with users
echo "WARNING: Active sessions detected. Coordinate with users before restart."

# Graceful restart
docker-compose restart livekit
sleep 20
curl -f http://localhost:7880/health || echo "LiveKit restart failed"
```

**3. Translator Worker Scaling**
```bash
# Scale up translator workers
docker-compose up -d --scale translator-worker=4

# Verify all workers are healthy
docker-compose ps translator-worker
docker-compose logs --tail=20 translator-worker

# Scale down (gradual)
docker-compose up -d --scale translator-worker=2
```

### Configuration Updates

**1. Environment Variable Updates**
```bash
# Update configuration
cd backend/infra
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Edit configuration
vim .env

# Apply changes (rolling update)
docker-compose up -d --force-recreate

# Verify changes applied
docker-compose exec stt-service env | grep MODEL_SIZE
```

**2. Language Model Updates**
```bash
# Update STT models
docker-compose exec stt-service python -c "
from faster_whisper import WhisperModel
model = WhisperModel('small.en', device='cuda')
print('Model loaded successfully')
"

# Update MT models  
docker-compose exec mt-service python -c "
from transformers import MarianMTModel
model = MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-en-es')
print('Translation model loaded')
"

# Update TTS voices
docker-compose exec tts-service python -c "
from TTS.api import TTS
tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2')
print('TTS model loaded')
"
```

### Scaling Operations

**1. Horizontal Scaling**
```bash
# Scale translation services
docker-compose up -d --scale stt-service=2 --scale mt-service=2 --scale tts-service=2

# Scale translator workers based on load
CONCURRENT_SESSIONS=$(curl -s http://localhost:7880/stats | jq '.total_rooms')
REQUIRED_WORKERS=$((CONCURRENT_SESSIONS / 3 + 1))
docker-compose up -d --scale translator-worker=${REQUIRED_WORKERS}

# Verify scaling
docker-compose ps | grep -E "(stt|mt|tts|translator)"
```

**2. Vertical Scaling Resource Limits**
```yaml
# Update docker-compose.yml with new resource limits
services:
  stt-service:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'  
          memory: 2G
          devices:
            - driver: nvidia
              count: 1
```

### Backup and Recovery Procedures

**1. Configuration and State Backup**
```bash
#!/bin/bash
# backup-system.sh
BACKUP_DIR="/backup/thehive/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Configuration backup
cp -r backend/infra/.env* "$BACKUP_DIR/"
cp -r backend/infra/docker-compose* "$BACKUP_DIR/"
cp -r /etc/ssl/thehive "$BACKUP_DIR/"

# Redis state backup
docker exec hive-redis redis-cli --rdb - > "$BACKUP_DIR/redis.rdb"

# LiveKit configuration
docker exec hive-livekit cat /etc/livekit/server.yaml > "$BACKUP_DIR/livekit-config.yaml"

# Database backup (if using PostgreSQL for CoTURN)
if [ "$DB_HOST" != "" ]; then
    pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_DIR/coturn.sql"
fi

# Create compressed archive
tar czf "/backup/thehive_$(date +%Y%m%d_%H%M%S).tar.gz" -C "/backup" "thehive"

echo "Backup completed: $BACKUP_DIR"
```

**2. Service State Recovery**
```bash
#!/bin/bash  
# restore-system.sh
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 /path/to/backup.tar.gz"
    exit 1
fi

# Extract backup
RESTORE_DIR="/tmp/restore_$(date +%s)"
mkdir -p "$RESTORE_DIR"
tar xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# Stop services
cd backend/infra
docker-compose down

# Restore configurations
cp "$RESTORE_DIR"/thehive/*/.env* .
cp "$RESTORE_DIR"/thehive/*/docker-compose* .

# Restore SSL certificates
sudo cp -r "$RESTORE_DIR"/thehive/*/ssl/* /etc/ssl/thehive/

# Restore Redis data
docker-compose up -d redis
sleep 10
docker exec -i hive-redis redis-cli --pipe < "$RESTORE_DIR/thehive/redis.rdb"

# Start all services
docker-compose up -d

# Verify recovery
./health-check.sh

echo "System recovery completed"
```

## Emergency Procedures

### Service Outage Response

**1. Critical Service Down (LiveKit SFU)**
```bash
# Immediate Response (< 2 minutes)
# Check service status
docker-compose ps livekit

# Check logs for errors
docker-compose logs --tail=50 livekit

# Attempt restart
docker-compose restart livekit
sleep 30

# Verify recovery
curl -f http://localhost:7880/health

# If restart fails, check dependencies
curl -f http://localhost:6379/ping  # Redis
systemctl status coturn            # CoTURN
```

**2. Translation Service Degradation**
```bash
# Check all translation services
for service in stt-service mt-service tts-service; do
    echo "Checking $service..."
    curl -f http://localhost:800{1,2,3}/health || echo "$service FAILED"
done

# Check GPU availability
nvidia-smi

# Check system resources
htop
iostat -x 1 5

# Scale up if resource constrained
docker-compose up -d --scale translator-worker=6

# Check for memory leaks
docker stats | grep -E "(stt|mt|tts)"
```

### Performance Degradation Investigation

**1. High Latency Investigation**
```bash
# Check SLO violations in Grafana
# Navigate to Translation SLOs dashboard

# Investigate network latency
./backend/infra/network-testing/latency-validator.py

# Check service-to-service latency
curl -s http://localhost:8001/performance | jq '.processing_time_ms'
curl -s http://localhost:8002/performance | jq '.translation_time_ms'  
curl -s http://localhost:8003/performance | jq '.synthesis_time_ms'

# Check queue depths
curl -s http://localhost:8001/metrics | grep queue_depth
curl -s http://localhost:8002/metrics | grep queue_depth
curl -s http://localhost:8003/metrics | grep queue_depth

# Investigate system bottlenecks
dstat -cdn --top-cpu --top-mem 5 6
```

**2. Translation Quality Issues**
```bash
# Check model health
docker-compose exec stt-service python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB')
"

# Check confidence scores
curl -s http://localhost:8002/performance | jq '.confidence_distribution'

# Check LocalAgreement-2 effectiveness  
curl -s http://localhost:8001/performance | jq '.word_retraction_rate'

# Review recent error patterns
docker-compose logs --tail=100 stt-service | grep ERROR
docker-compose logs --tail=100 mt-service | grep ERROR
docker-compose logs --tail=100 tts-service | grep ERROR
```

### Security Incident Response

**1. Suspicious Activity Detection**
```bash
# Check authentication failures
docker-compose logs auth-service | grep -i "authentication failed"

# Review TURN server access logs
docker-compose logs coturn | grep -i "unauthorized"

# Check for DDoS patterns
docker-compose logs nginx | awk '{print $1}' | sort | uniq -c | sort -nr | head -20

# Review WebRTC connection patterns
curl -s http://localhost:7880/stats | jq '.rooms[] | select(.num_participants > 10)'
```

**2. Certificate Expiration**
```bash  
# Check certificate validity
for domain in sfu.yourdomain.com turn.yourdomain.com api.yourdomain.com; do
    echo "Checking $domain..."
    echo | openssl s_client -servername $domain -connect $domain:443 2>/dev/null | \
    openssl x509 -noout -dates
done

# Renew certificates
certbot renew --quiet

# Restart services using certificates
docker-compose restart nginx coturn
```

### Data Recovery Procedures

**1. Redis Session Recovery**
```bash
# Check Redis connectivity
redis-cli -h localhost -p 6379 ping

# Backup current state before recovery
redis-cli -h localhost -p 6379 --rdb backup_$(date +%Y%m%d_%H%M%S).rdb

# Restore from backup if needed
redis-cli -h localhost -p 6379 FLUSHALL
cat backup_file.rdb | redis-cli -h localhost -p 6379 --pipe

# Verify session data
redis-cli -h localhost -p 6379 INFO keyspace
```

**2. Configuration Recovery**
```bash
# Restore from Git if configuration corrupted
git checkout HEAD -- backend/infra/.env
git checkout HEAD -- backend/infra/docker-compose.yml

# Restore from backup
cp /backup/latest/thehive/.env backend/infra/
cp /backup/latest/thehive/docker-compose.yml backend/infra/

# Validate configuration
docker-compose config
```

## Maintenance Windows

### Planned Maintenance Procedures

**1. Monthly System Updates**
```bash
#!/bin/bash
# monthly-maintenance.sh

echo "Starting monthly maintenance at $(date)"

# 1. System package updates
sudo apt update && sudo apt upgrade -y

# 2. Docker image updates
cd backend/infra
docker-compose pull

# 3. Certificate renewals
certbot renew --quiet

# 4. Log rotation and cleanup
docker system prune -f
find /var/log -name "*.log" -mtime +30 -delete

# 5. Backup creation
./backup-system.sh

# 6. Rolling service updates
docker-compose up -d --force-recreate

# 7. Health verification
sleep 60
./health-check.sh

echo "Monthly maintenance completed at $(date)"
```

**2. Model Updates and Optimization**
```bash
#!/bin/bash
# model-update.sh

# Download new models during maintenance window
cd backend/services/stt
python -c "
from faster_whisper import WhisperModel
models = ['tiny.en', 'base.en', 'small.en']
for model in models:
    print(f'Downloading {model}...')
    WhisperModel(model, device='cuda')
"

# Update TTS models
cd ../tts
python -c "
from TTS.api import TTS
tts_models = [
    'tts_models/multilingual/multi-dataset/xtts_v2',
    'tts_models/en/ljspeech/tacotron2-DDC'
]
for model in tts_models:
    print(f'Loading {model}...')
    TTS(model)
"

# Update MT models
cd ../mt
python model_optimizer.py --update-all

echo "Model updates completed"
```

### Rolling Update Strategies

**1. Blue-Green Deployment**
```bash
#!/bin/bash
# blue-green-deploy.sh

# Current (blue) environment running
CURRENT_ENV="blue"
NEW_ENV="green"

# Start new environment
docker-compose -f docker-compose.yml -f docker-compose.${NEW_ENV}.yml up -d

# Health check new environment
sleep 60
curl -f http://localhost:8001/health || exit 1
curl -f http://localhost:8002/health || exit 1  
curl -f http://localhost:8003/health || exit 1

# Run smoke tests
cd qa && python slo_tests.py --environment ${NEW_ENV}

# Switch traffic (update load balancer)
./switch-traffic.sh ${NEW_ENV}

# Monitor for 10 minutes
sleep 600

# Stop old environment
docker-compose -f docker-compose.${CURRENT_ENV}.yml down

echo "Blue-green deployment completed"
```

**2. Canary Deployment**
```bash
#!/bin/bash
# canary-deploy.sh

# Deploy canary (10% traffic)
docker-compose up -d --scale translator-worker=1 translator-worker-canary

# Monitor canary performance for 30 minutes
for i in {1..30}; do
    CANARY_ERRORS=$(curl -s http://localhost:8080/metrics | grep 'errors{version="canary"}')
    echo "Canary errors: $CANARY_ERRORS"
    sleep 60
done

# If canary successful, roll out to 50%
docker-compose up -d --scale translator-worker-canary=3

# Monitor for another 30 minutes
# If successful, complete rollout
docker-compose up -d --scale translator-worker-canary=6 --scale translator-worker=0

echo "Canary deployment completed"
```

### Rollback Procedures

**1. Quick Rollback to Previous Version**
```bash
#!/bin/bash
# rollback.sh

PREVIOUS_VERSION="$1"
if [ -z "$PREVIOUS_VERSION" ]; then
    echo "Usage: $0 <previous_version>"
    exit 1
fi

# Stop current services
docker-compose down

# Restore previous configuration
git checkout $PREVIOUS_VERSION -- backend/infra/docker-compose.yml
cp "/backup/versions/${PREVIOUS_VERSION}/.env" backend/infra/

# Start previous version
docker-compose up -d

# Verify rollback
sleep 30
./health-check.sh

echo "Rollback to $PREVIOUS_VERSION completed"
```

### Communication Templates

**1. Maintenance Window Notification**
```
Subject: The HIVE Translation System - Scheduled Maintenance

Dear Users,

We will be performing scheduled maintenance on The HIVE Translation System:

Date: [DATE]
Time: [TIME] - [TIME] (2 hours)
Impact: Service will be unavailable during this window

Maintenance includes:
- System security updates
- Performance optimizations  
- Model updates for improved translation quality

We appreciate your patience and understanding.

The HIVE Operations Team
```

**2. Post-Maintenance Summary**
```
Subject: The HIVE Translation System - Maintenance Completed

Dear Users,

Scheduled maintenance has been completed successfully:

Completed: [DATE] at [TIME]
Duration: [ACTUAL DURATION]
Status: All services operational

Improvements include:
- [LIST OF IMPROVEMENTS]
- [PERFORMANCE ENHANCEMENTS]
- [NEW FEATURES IF ANY]

Thank you for your patience.

The HIVE Operations Team
```

## Monitoring and Alerting

### Alert Definitions and Response Procedures

**Critical Alerts (Immediate Response Required):**

1. **Translation SLO Breach**
   - **Condition**: `translation_ttft_p95_ms > 500 for 2m`
   - **Response**: Scale translator workers, check GPU resources
   - **Escalation**: Platform team after 10 minutes

2. **Service Down**  
   - **Condition**: `up{job=~"stt|mt|tts|livekit"} == 0 for 1m`
   - **Response**: Restart service, check dependencies
   - **Escalation**: On-call engineer immediately

3. **High Error Rate**
   - **Condition**: `rate(http_requests_total{status=~"5.."}[5m]) > 0.05`
   - **Response**: Check logs, scale services if needed
   - **Escalation**: Engineering team after 5 minutes

**Warning Alerts (Response Within 15 Minutes):**

1. **Caption Latency SLO**
   - **Condition**: `caption_latency_p95_ms > 300 for 5m`
   - **Response**: Check STT service performance
   - **Action**: Investigate LocalAgreement-2 configuration

2. **High Resource Usage**
   - **Condition**: `cpu_usage > 80 or memory_usage > 85 for 10m`
   - **Response**: Scale services horizontally
   - **Action**: Consider vertical scaling

3. **Network Quality Issues**
   - **Condition**: `packet_loss_rate > 0.02 for 5m`  
   - **Response**: Check network infrastructure
   - **Action**: Investigate TURN server performance

### Performance Monitoring Runbooks

**1. Translation Latency Investigation**
```bash
# Check end-to-end latency breakdown
curl -s http://localhost:8080/trace/recent | jq '
  .traces[] | {
    total_latency: .duration_ms,
    stt_time: (.spans[] | select(.name=="stt") | .duration_ms),
    mt_time: (.spans[] | select(.name=="mt") | .duration_ms),  
    tts_time: (.spans[] | select(.name=="tts") | .duration_ms)
  }
'

# Identify bottleneck service
# If STT > 200ms: Check GPU utilization, reduce model size
# If MT > 100ms: Scale MT service, check context length
# If TTS > 400ms: Scale TTS service, optimize voice loading
```

**2. Audio Quality Monitoring**
```bash
# Check WebRTC statistics
curl -s http://localhost:7880/stats | jq '
  .rooms[] | {
    room_name: .name,
    participants: .num_participants,
    packet_loss: .quality_stats.packet_loss_rate,
    jitter: .quality_stats.jitter_ms
  }
'

# Monitor Mean Opinion Score (MOS)
curl -s http://localhost:8003/metrics | grep audio_quality_score
```

This runbook provides comprehensive operational procedures for The HIVE Translation System. Keep it updated as the system evolves and new operational patterns emerge.

---

**Document Version**: 1.0  
**Last Updated**: $(date +%Y-%m-%d)  
**Next Review**: $(date -d "+3 months" +%Y-%m-%d)