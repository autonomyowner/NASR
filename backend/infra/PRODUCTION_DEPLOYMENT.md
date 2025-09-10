# The HIVE LiveKit SFU Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying The HIVE's optimized LiveKit SFU infrastructure in production with sub-500ms end-to-end translation latency.

## Performance Targets

- **p95 TTFT (Time-to-First-Token)**: ≤ 450ms
- **p95 Caption Latency**: ≤ 250ms
- **End-to-End Translation Latency**: <500ms
- **Network Resilience**: 1-5% packet loss, 50-150ms jitter tolerance
- **Concurrent Sessions**: 100+ simultaneous translation sessions

## Architecture Components

### Core Infrastructure
- **LiveKit SFU**: Ultra-low latency audio routing
- **CoTURN**: UDP-first STUN/TURN server
- **Redis**: Session state and scaling
- **JWT Auth Service**: Secure room access control

### Translation Pipeline
- **STT Service**: Real-time speech recognition
- **MT Service**: Incremental machine translation
- **TTS Service**: Streaming text-to-speech synthesis
- **Translator Workers**: Co-located LiveKit participants

### Monitoring Stack
- **Prometheus**: Metrics collection
- **Grafana**: Performance dashboards
- **Jaeger**: Distributed tracing
- **Custom SLO monitoring**: Translation latency tracking

## Pre-Deployment Checklist

### Infrastructure Requirements

#### Minimum Hardware Specifications
```
Production Node (Single-Node Deployment):
- CPU: 8 vCPUs (Intel Xeon or AMD EPYC)
- RAM: 16GB (32GB recommended)  
- Storage: 100GB SSD (NVMe preferred)
- GPU: 1x NVIDIA T4 or better (for translation services)
- Network: 1Gbps symmetric bandwidth
- OS: Ubuntu 22.04 LTS or equivalent

Multi-Node Deployment:
- LiveKit SFU Node: 4 vCPUs, 8GB RAM
- Translation Services Node: 8 vCPUs, 16GB RAM, 1x GPU
- Database/Redis Node: 2 vCPUs, 4GB RAM
- Load Balancer: 2 vCPUs, 4GB RAM
```

#### Network Requirements
- **Public IP Address**: Required for CoTURN server
- **Domain Names**: 
  - `sfu.yourdomain.com` (LiveKit SFU)
  - `turn.yourdomain.com` (CoTURN server)
  - `api.yourdomain.com` (Auth service)
- **SSL Certificates**: Let's Encrypt or commercial certificates
- **Firewall Rules**: See network configuration section

### Software Prerequisites
- Docker 24.0+ and Docker Compose 2.0+
- Kubernetes 1.25+ (for multi-node deployment)
- NVIDIA Container Runtime (for GPU acceleration)
- Certbot (for SSL certificate management)

## Step-by-Step Deployment

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/yourusername/thehive.git
cd thehive/backend/infra

# Copy and configure environment file
cp .env.template .env
```

### 2. Security Configuration

#### Generate Secure Keys
```bash
# Generate secure random keys
export LIVEKIT_API_KEY=$(openssl rand -hex 16)
export LIVEKIT_SECRET_KEY=$(openssl rand -hex 32)
export AUTH_SERVICE_API_KEY=$(openssl rand -hex 32)
export TURN_SECRET_KEY=$(openssl rand -hex 32)

# Update .env file with generated keys
sed -i "s/LIVEKIT_API_KEY=devkey/LIVEKIT_API_KEY=$LIVEKIT_API_KEY/" .env
sed -i "s/LIVEKIT_SECRET_KEY=devsecret/LIVEKIT_SECRET_KEY=$LIVEKIT_SECRET_KEY/" .env
sed -i "s/AUTH_SERVICE_API_KEY=/AUTH_SERVICE_API_KEY=$AUTH_SERVICE_API_KEY/" .env
sed -i "s/TURN_SECRET_KEY=your-ultra-secure-secret-key-change-in-production/TURN_SECRET_KEY=$TURN_SECRET_KEY/" .env
```

#### Configure Production Settings
```bash
# Set production environment
sed -i 's/ENVIRONMENT=development/ENVIRONMENT=production/' .env
sed -i 's/DEBUG_MODE=true/DEBUG_MODE=false/' .env

# Configure domains (replace with your domains)
sed -i 's/COTURN_SERVER_NAME=turn.thehive.local/COTURN_SERVER_NAME=turn.yourdomain.com/' .env
sed -i 's/NODE_IP=127.0.0.1/NODE_IP=YOUR_SERVER_IP/' .env
sed -i 's/EXTERNAL_IP=/EXTERNAL_IP=YOUR_PUBLIC_IP/' .env
```

### 3. SSL Certificate Setup

#### Using Let's Encrypt
```bash
# Install Certbot
sudo apt update && sudo apt install -y certbot

# Generate certificates for your domains
sudo certbot certonly --standalone -d sfu.yourdomain.com
sudo certbot certonly --standalone -d turn.yourdomain.com
sudo certbot certonly --standalone -d api.yourdomain.com

# Create certificate directories
sudo mkdir -p /etc/ssl/thehive/
sudo cp /etc/letsencrypt/live/turn.yourdomain.com/fullchain.pem /etc/ssl/thehive/turn_cert.pem
sudo cp /etc/letsencrypt/live/turn.yourdomain.com/privkey.pem /etc/ssl/thehive/turn_key.pem

# Update .env with certificate paths
echo "COTURN_CERT_FILE=/etc/ssl/thehive/turn_cert.pem" >> .env
echo "COTURN_KEY_FILE=/etc/ssl/thehive/turn_key.pem" >> .env
```

### 4. Network Configuration

#### Firewall Rules
```bash
# Allow SSH
sudo ufw allow 22

# LiveKit SFU
sudo ufw allow 7880/tcp    # HTTP/WebSocket
sudo ufw allow 7881/tcp    # gRPC API
sudo ufw allow 50000:50199/udp  # RTC ports

# CoTURN
sudo ufw allow 3478/udp    # STUN/TURN UDP
sudo ufw allow 3478/tcp    # STUN/TURN TCP  
sudo ufw allow 5349/tcp    # TURNS TLS
sudo ufw allow 49152:49252/udp  # Relay ports

# HTTP/HTTPS for API and monitoring
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8003/tcp    # Auth service
sudo ufw allow 3001/tcp    # Grafana (restrict in production)

# Enable firewall
sudo ufw --force enable
```

#### DNS Configuration
```dns
# Add these DNS records to your domain:
sfu.yourdomain.com.     A    YOUR_PUBLIC_IP
turn.yourdomain.com.    A    YOUR_PUBLIC_IP  
api.yourdomain.com.     A    YOUR_PUBLIC_IP

# Optional: Add STUN/TURN SRV records
_stun._udp.yourdomain.com. SRV 10 0 3478 turn.yourdomain.com.
_turn._udp.yourdomain.com. SRV 10 0 3478 turn.yourdomain.com.
```

### 5. Database Setup (Optional)

#### PostgreSQL for CoTURN User Management
```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE coturn;
CREATE USER coturn WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE coturn TO coturn;
\q
EOF

# Update .env with database settings
echo "DB_HOST=localhost" >> .env
echo "DB_NAME=coturn" >> .env
echo "DB_USER=coturn" >> .env  
echo "DB_PASS=secure_password_here" >> .env
```

### 6. Deploy Services

#### Single-Node Deployment
```bash
# Pull all images
docker-compose pull

# Start core services
docker-compose up -d redis coturn livekit

# Wait for core services to be ready
sleep 30

# Start translation services  
docker-compose up -d stt-service mt-service tts-service auth-service

# Start translator workers
docker-compose up -d translator-worker

# Start monitoring
docker-compose up -d prometheus grafana jaeger

# Verify all services are running
docker-compose ps
```

#### Multi-Node Kubernetes Deployment
```bash
# Create namespace
kubectl create namespace thehive-sfu

# Apply configuration
kubectl apply -f translator-deployment.yaml

# Deploy LiveKit SFU
kubectl apply -f livekit-deployment.yaml

# Deploy translation services
kubectl apply -f translation-services.yaml

# Deploy monitoring stack
kubectl apply -f monitoring.yaml

# Check deployment status
kubectl get pods -n thehive-sfu
```

### 7. Load Balancer Configuration

#### NGINX Configuration
```nginx
# /etc/nginx/sites-available/thehive-sfu
upstream livekit_backend {
    least_conn;
    server localhost:7880 max_fails=3 fail_timeout=30s;
}

upstream auth_backend {
    least_conn;  
    server localhost:8003 max_fails=3 fail_timeout=30s;
}

# LiveKit SFU
server {
    listen 443 ssl http2;
    server_name sfu.yourdomain.com;

    ssl_certificate /etc/ssl/thehive/sfu_cert.pem;
    ssl_private_key /etc/ssl/thehive/sfu_key.pem;
    
    # WebSocket support
    location / {
        proxy_pass http://livekit_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for real-time communication
        proxy_connect_timeout 10s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
}

# Auth Service
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/thehive/api_cert.pem;
    ssl_private_key /etc/ssl/thehive/api_key.pem;
    
    location /auth/ {
        proxy_pass http://auth_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://auth_backend/health;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name sfu.yourdomain.com api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 8. Monitoring Setup

#### Configure Grafana Dashboards
```bash
# Access Grafana at https://yourdomain.com:3001
# Default credentials: admin / admin123 (change immediately)

# Import pre-built dashboards
curl -X POST \
  -H "Content-Type: application/json" \
  -d @grafana-dashboards/livekit-sfu.json \
  http://admin:admin123@localhost:3001/api/dashboards/db

curl -X POST \
  -H "Content-Type: application/json" \
  -d @grafana-dashboards/translation-slos.json \
  http://admin:admin123@localhost:3001/api/dashboards/db
```

#### Set Up Alerting
```yaml
# alerts.yaml - Prometheus alerting rules
groups:
- name: livekit-sfu
  rules:
  - alert: HighTranslationLatency
    expr: histogram_quantile(0.95, translation_latency_seconds) > 0.45
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Translation latency exceeding SLO"
      description: "p95 translation latency is {{ $value }}s, exceeding 450ms SLO"
      
  - alert: LiveKitDown
    expr: up{job="livekit"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "LiveKit SFU is down"
      
  - alert: HighPacketLoss
    expr: packet_loss_rate > 0.02
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High packet loss detected"
      description: "Packet loss rate is {{ $value }}%, consider investigating network"
```

### 9. Health Checks and Validation

#### Automated Health Check Script
```bash
#!/bin/bash
# health-check.sh

FAILED=0

# Check LiveKit SFU
if curl -f http://localhost:7880/health >/dev/null 2>&1; then
    echo "✓ LiveKit SFU is healthy"
else
    echo "✗ LiveKit SFU health check failed"
    FAILED=1
fi

# Check Auth Service  
if curl -f http://localhost:8003/health >/dev/null 2>&1; then
    echo "✓ Auth Service is healthy"
else
    echo "✗ Auth Service health check failed"
    FAILED=1
fi

# Check CoTURN
if nc -z localhost 3478; then
    echo "✓ CoTURN is healthy"
else
    echo "✗ CoTURN health check failed"
    FAILED=1
fi

# Check Translation Services
for service in stt mt tts; do
    port=$([ "$service" = "stt" ] && echo 8000 || [ "$service" = "mt" ] && echo 8001 || echo 8002)
    if curl -f http://localhost:$port/health >/dev/null 2>&1; then
        echo "✓ $service service is healthy"
    else
        echo "⚠ $service service health check failed"
    fi
done

if [ $FAILED -eq 0 ]; then
    echo "🎉 All core services are healthy"
    exit 0
else
    echo "❌ Some critical services failed health checks"
    exit 1
fi
```

#### Performance Validation
```bash
# Test end-to-end latency
curl -X POST http://localhost:8003/auth/token/room \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_SERVICE_API_KEY" \
  -d '{"room_name":"test-room","participant_name":"test-user","role":"speaker"}'

# Run load test (requires additional tooling)
# artillery run --config artillery-config.yaml load-test.yaml
```

### 10. Backup and Recovery

#### Database Backup
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/thehive/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL (if using)
if [ "$DB_HOST" != "" ]; then
    pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_DIR/coturn.sql"
fi

# Backup Redis
docker exec redis redis-cli --rdb - > "$BACKUP_DIR/redis.rdb"

# Backup configuration
cp -r /etc/ssl/thehive "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# Create tarball
tar czf "/backup/thehive_backup_$(date +%Y%m%d_%H%M%S).tar.gz" -C "/backup" "thehive"
```

## Production Optimization

### Performance Tuning

#### Kernel Parameters
```bash
# /etc/sysctl.conf optimizations
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144  
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 30000
net.ipv4.tcp_congestion_control = bbr

# Apply changes
sudo sysctl -p
```

#### Docker Resource Limits
```yaml
# Update docker-compose.yml with resource limits
services:
  livekit:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
          
  translator-worker:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Security Hardening

#### Additional Security Measures
```bash
# Install fail2ban for brute force protection
sudo apt install -y fail2ban

# Configure fail2ban for SSH and web services
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
EOF

# Restart fail2ban
sudo systemctl restart fail2ban

# Set up automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### SSL Security Configuration
```nginx
# Strong SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# Security headers
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
```

## Maintenance

### Regular Maintenance Tasks

#### Weekly Tasks
```bash
# Update SSL certificates (automated)
certbot renew --quiet

# Clean Docker images and containers
docker system prune -f

# Check disk space
df -h

# Review logs for errors
docker-compose logs --tail=100 livekit | grep ERROR
```

#### Monthly Tasks
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d

# Review performance metrics
# Access Grafana dashboards and check SLOs

# Backup verification
# Restore backup to test environment and validate
```

### Troubleshooting

#### Common Issues

**High Latency**
```bash
# Check network latency to translation services
ping -c 10 stt-service
ping -c 10 mt-service  
ping -c 10 tts-service

# Check system resources
htop
iostat -x 1

# Check Docker container resources
docker stats
```

**Connection Issues**
```bash
# Test STUN/TURN server
stunclient --mode test --server turn.yourdomain.com:3478

# Check firewall rules
sudo ufw status verbose

# Test WebSocket connection
wscat -c ws://sfu.yourdomain.com:7880
```

**Audio Quality Issues**
```bash
# Check packet loss
ss -i

# Review audio codec settings in LiveKit config
docker-compose exec livekit cat /etc/livekit/server-optimized.yaml | grep -A 10 audio

# Check translator worker logs
docker-compose logs translator-worker | grep audio
```

## Support and Monitoring

### Key Metrics to Monitor

1. **Translation Latency**: p95, p99 end-to-end latency
2. **Audio Quality**: Packet loss, jitter, MOS scores
3. **System Resources**: CPU, memory, disk usage
4. **Network Performance**: Bandwidth utilization, connection counts
5. **Service Health**: Up time, error rates

### Alerting Thresholds

- **Critical**: p95 latency > 500ms, any service down > 1 minute
- **Warning**: p95 latency > 400ms, packet loss > 1%, CPU > 80%
- **Info**: New room created, worker scaled up/down

### Log Analysis

#### Important Log Locations
- **LiveKit**: `docker-compose logs livekit`
- **CoTURN**: `docker-compose logs coturn`
- **Translation Services**: `docker-compose logs stt-service mt-service tts-service`
- **System**: `/var/log/syslog`, `/var/log/nginx/`

### Performance Benchmarking

#### Load Testing
```bash
# Install artillery for load testing
npm install -g artillery

# Run translation latency benchmark
artillery run load-tests/translation-latency.yaml

# Monitor results in Grafana during test
```

This production deployment guide ensures optimal performance for The HIVE's real-time translation system with comprehensive monitoring, security, and maintenance procedures.