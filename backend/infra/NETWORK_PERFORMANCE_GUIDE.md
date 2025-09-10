# The HIVE - Network Performance Optimization Guide

**Target: Sub-500ms end-to-end translation latency with resilience to network impairments**

## Quick Start - Production Deployment

### 1. Deploy Optimized Stack

```bash
# Clone the repository
git clone https://github.com/your-org/thehive.git
cd thehive/backend/infra

# Deploy with network optimizations
docker-compose -f docker-compose.yml up -d

# Verify all services are running
docker-compose ps
```

### 2. Validate Performance

```bash
# Run comprehensive latency validation
cd network-testing
sudo python3 latency-validator.py --target-latency 500

# Run network impairment tests  
sudo chmod +x tc-impairment.sh
sudo ./tc-impairment.sh eth0
```

### 3. Monitor Performance

- **Grafana Dashboard**: http://localhost:3001
- **Prometheus Metrics**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686
- **LiveKit Console**: http://localhost:7880

---

## Architecture Overview

### Network Path Optimization

```
Client → CoTURN (UDP-first) → LiveKit SFU → Co-located Workers → Client
   ↓         ≤50ms            ≤5ms        ≤450ms          ≤50ms
Sub-500ms end-to-end latency target
```

### Service Co-location Strategy

```yaml
Network Topology (172.20.0.0/16):
├── LiveKit SFU:        172.20.0.10  # Central hub
├── STT Service:        172.20.0.11  # Adjacent to SFU
├── MT Service:         172.20.0.12  # Sequential pipeline
├── TTS Service:        172.20.0.13  # Adjacent to MT
├── CoTURN Server:      172.20.0.5   # NAT traversal
└── Redis Cache:        172.20.0.20  # Centralized state
```

---

## Key Optimizations Implemented

### 1. UDP-First CoTURN Configuration

**File**: `coturn/turnserver.conf`

**Key Features**:
- Aggressive UDP-only policy (`no-tcp`, `force-udp`)
- Reduced timeout values for faster connection establishment
- Expanded port range (49152-65535) for better connectivity
- OS-level socket optimizations (`so-no-delay`, large buffers)

```conf
# Ultra-low latency timeouts
channel-lifetime=300         # Reduced from 600s
permission-lifetime=120      # Reduced from 300s
max-allocate-timeout=30      # Reduced from 60s

# Network performance tuning
udp-recv-buffer-size=1048576  # 1MB receive buffer
udp-send-buffer-size=1048576  # 1MB send buffer
```

### 2. SFU/Worker Co-location

**File**: `docker-compose.yml`

**Key Features**:
- Static IP assignment for predictable routing
- IPC sharing between LiveKit and workers
- Dedicated network with optimized subnet
- Resource limits and sysctls for performance

```yaml
# Example service co-location
stt-service:
  ipc: "container:livekit-server"  # Share IPC namespace
  networks:
    hive-network:
      ipv4_address: 172.20.0.11    # Adjacent to LiveKit (172.20.0.10)
```

### 3. Jitter Buffer & Quality Adaptation

**File**: `audio-optimization.yaml`

**Key Features**:
- Ultra-low latency jitter buffer (20ms target, 100ms max)
- Adaptive redundant encoding (RED) for packet loss resilience
- Advanced packet loss concealment (PLC) with Opus integration
- Dynamic quality adaptation based on network conditions

```yaml
jitter_buffer:
  target_delay: 20ms        # Ultra-low for minimal latency
  adaptive: true            # Dynamic adjustment
  adaptation_speed: fast    # Quick response to changes
```

### 4. LiveKit SFU Optimization  

**File**: `livekit/server-optimized.yaml`

**Key Features**:
- Opus codec with 10ms frame duration for ultra-low latency
- Disabled video processing to optimize for audio-only
- Aggressive congestion control and adaptive bitrate
- WebRTC ICE optimization with UDP preference

```yaml
audio:
  opus:
    frame_duration: 10ms      # Minimal frame size
    dtx: false               # Consistent latency
    fec: true                # Forward error correction
    bitrate: 48000           # Optimized for speech
```

---

## Performance Testing & Validation

### 1. Network Impairment Testing

The `tc-impairment.sh` script tests system resilience under various conditions:

- **Baseline**: Clean network performance
- **Light Impairment**: 1% packet loss
- **Heavy Impairment**: 5% packet loss  
- **High Jitter**: 100-150ms network jitter
- **Bandwidth Limits**: 64-128kbps restrictions
- **Mobile Simulation**: 3G/4G network conditions
- **Stress Test**: Combined impairments

```bash
# Run full impairment test suite
sudo ./tc-impairment.sh eth0

# Monitor results in real-time
tail -f /var/log/hive-network-test.log
```

### 2. Latency Validation

The `latency-validator.py` script provides comprehensive SLO validation:

- **Multi-scenario Testing**: 8 different network conditions
- **Statistical Analysis**: p95, p99, average, and max latency
- **SLO Compliance**: Automated pass/fail against 500ms target
- **Detailed Reporting**: JSON results and human-readable reports

```bash
# Run validation with custom target
python3 latency-validator.py --target-latency 450 --duration 300

# Generate extended report
python3 latency-validator.py --output detailed_results.json
```

---

## Monitoring & Observability

### 1. Grafana Dashboard

**File**: `monitoring/network-performance-dashboard.json`

**Key Panels**:
- End-to-end latency with p95 SLO tracking
- Network path breakdown (WebRTC, SFU, STT, MT, TTS)
- Packet loss and jitter monitoring  
- RED/PLC activation rates
- Audio quality metrics (MOS scores)
- Service health status

### 2. Prometheus Metrics

Key metrics collected for SLO monitoring:

```promql
# p95 end-to-end latency
histogram_quantile(0.95, rate(translation_latency_seconds_bucket[5m]))

# Packet loss rate
rate(network_packets_lost_total[5m]) / rate(network_packets_total[5m]) * 100

# Jitter buffer performance  
jitter_buffer_level_percent
jitter_buffer_underruns_rate
```

### 3. Real-time Alerts

```yaml
# Prometheus alerting rules
- alert: HighTranslationLatency
  expr: histogram_quantile(0.95, rate(translation_latency_seconds_bucket[5m])) > 0.5
  for: 30s
  labels:
    severity: critical
  annotations:
    summary: "Translation latency exceeds SLO"
    
- alert: ExcessivePacketLoss  
  expr: rate(network_packets_lost_total[5m]) / rate(network_packets_total[5m]) > 0.05
  for: 60s
  labels:
    severity: warning
  annotations:
    summary: "Packet loss rate above 5%"
```

---

## Production Deployment Checklist

### Pre-deployment

- [ ] Update `external-ip` in CoTURN configuration
- [ ] Configure TLS certificates for production domains
- [ ] Set strong authentication credentials
- [ ] Allocate sufficient server resources (4+ CPU cores, 8+ GB RAM)
- [ ] Configure firewall rules for UDP ports (3478, 49152-65535)

### Deployment

- [ ] Deploy services with `docker-compose up -d`
- [ ] Verify all services are healthy (`docker-compose ps`)
- [ ] Run network performance validation
- [ ] Configure monitoring and alerting
- [ ] Test end-to-end translation functionality

### Post-deployment

- [ ] Monitor p95 latency continuously  
- [ ] Set up log aggregation and analysis
- [ ] Configure backup and disaster recovery
- [ ] Document operational procedures
- [ ] Schedule regular performance testing

---

## Troubleshooting Guide

### High Latency Issues

1. **Check Service Health**:
   ```bash
   # Verify all services are running
   docker-compose ps
   
   # Check service logs
   docker-compose logs -f livekit stt-service mt-service tts-service
   ```

2. **Network Path Analysis**:
   ```bash
   # Test connectivity to services
   curl -w "@curl-format.txt" http://localhost:8001/health
   curl -w "@curl-format.txt" http://localhost:8002/health
   curl -w "@curl-format.txt" http://localhost:8003/health
   ```

3. **CoTURN Connectivity**:
   ```bash
   # Test STUN/TURN connectivity
   stunclient localhost 3478
   
   # Check CoTURN logs
   docker-compose logs coturn
   ```

### Packet Loss Issues

1. **Verify RED/PLC Configuration**:
   - Check `audio-optimization.yaml` settings
   - Monitor RED activation rates in Grafana
   - Verify PLC concealment effectiveness

2. **Network Interface Optimization**:
   ```bash
   # Check network interface statistics
   cat /proc/net/dev
   
   # Verify buffer sizes
   sysctl net.core.rmem_max
   sysctl net.core.wmem_max
   ```

### Quality Degradation

1. **Monitor Quality Adaptation**:
   - Check adaptive bitrate behavior
   - Verify codec settings (frame duration, FEC)
   - Monitor MOS scores in dashboard

2. **Resource Utilization**:
   ```bash
   # Check CPU/memory usage
   docker stats
   
   # Monitor GPU utilization (if applicable)
   nvidia-smi
   ```

---

## Performance Benchmarks

### Target SLOs

- **p95 End-to-End Latency**: ≤ 500ms
- **p95 Caption Latency**: ≤ 250ms  
- **Packet Loss Resilience**: Up to 5%
- **Jitter Tolerance**: Up to 150ms
- **Audio Quality**: MOS ≥ 3.5
- **Connection Success Rate**: ≥ 98%

### Expected Performance

| Network Condition | p95 Latency | Quality Score | SLO Compliance |
|-------------------|-------------|---------------|----------------|
| Clean Network     | 320ms       | 0.95          | ✅ Pass         |
| 1% Packet Loss   | 380ms       | 0.92          | ✅ Pass         |
| 3% Packet Loss   | 450ms       | 0.88          | ✅ Pass         |
| 5% Packet Loss   | 490ms       | 0.82          | ✅ Pass         |
| 100ms Jitter     | 420ms       | 0.90          | ✅ Pass         |
| 150ms Jitter     | 480ms       | 0.85          | ✅ Pass         |
| Mobile Network    | 460ms       | 0.87          | ✅ Pass         |
| Stress Test       | 520ms       | 0.75          | ⚠️ Warning      |

---

## Advanced Optimizations

### 1. Hardware-Level Optimizations

```bash
# CPU affinity for network interrupts
echo 2 > /proc/irq/24/smp_affinity

# Disable CPU frequency scaling
echo performance > /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Optimize network stack
echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf
echo 'net.ipv4.udp_mem = 65536 131072 262144' >> /etc/sysctl.conf
sysctl -p
```

### 2. Container Optimizations

```yaml
# Docker runtime optimizations
services:
  livekit:
    runtime: nvidia  # GPU runtime if available
    security_opt:
      - no-new-privileges:true
    ulimits:
      memlock: -1
      stack: 67108864
```

### 3. Application-Level Tuning

```python
# Python service optimizations
import asyncio
import uvloop

# Use high-performance event loop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Optimize garbage collection
import gc
gc.set_threshold(700, 10, 10)
```

---

## Support & Maintenance

### Regular Maintenance Tasks

1. **Weekly Performance Reviews**:
   - Analyze p95 latency trends
   - Review packet loss incidents
   - Check audio quality scores

2. **Monthly Optimizations**:
   - Update network configurations based on usage patterns
   - Tune jitter buffer settings
   - Optimize resource allocation

3. **Quarterly Load Testing**:
   - Run comprehensive impairment tests
   - Validate SLO compliance under peak load
   - Update performance benchmarks

### Getting Help

- **Documentation**: Check this guide and inline code comments
- **Monitoring**: Use Grafana dashboards for real-time diagnostics  
- **Testing**: Run validation scripts for automated troubleshooting
- **Logs**: Check service logs for detailed error information

---

**The HIVE Network Performance Optimization - Production Ready ✅**

*This guide provides comprehensive network optimizations for achieving sub-500ms end-to-end translation latency with resilience to real-world network conditions.*