# The HIVE Translation System - Development Setup Guide

Welcome to The HIVE development team! This guide will help you set up a complete development environment for contributing to our real-time translation system.

## 📋 Prerequisites

### System Requirements

**Minimum Development Setup:**
- **OS**: Ubuntu 20.04+ / macOS 11+ / Windows 10+ with WSL2
- **CPU**: 8 CPU cores (Intel Core i7 or AMD Ryzen 7)
- **RAM**: 16GB (32GB recommended for full stack development)
- **Storage**: 100GB free space (SSD recommended)
- **Network**: Stable internet connection (50+ Mbps recommended)

**Recommended Development Setup:**
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 12+ CPU cores (Intel Core i9 or AMD Ryzen 9)
- **RAM**: 32GB+
- **Storage**: 200GB+ NVMe SSD
- **GPU**: NVIDIA GPU with 8GB+ VRAM (for ML model development)
- **Network**: Gigabit ethernet connection

### Required Software

1. **Docker & Docker Compose**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker $USER
   
   # macOS (via Homebrew)
   brew install docker docker-compose
   ```

2. **Node.js 18+ and npm**
   ```bash
   # Using Node Version Manager (recommended)
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   source ~/.bashrc
   nvm install 18
   nvm use 18
   
   # Verify installation
   node --version  # Should show v18.x.x
   npm --version   # Should show 9.x.x+
   ```

3. **Python 3.9+ with pip**
   ```bash
   # Ubuntu/Debian
   sudo apt install -y python3.9 python3.9-pip python3.9-venv
   
   # macOS (via Homebrew)
   brew install python@3.9
   
   # Create development virtual environment
   python3.9 -m venv ~/.venv/thehive-dev
   source ~/.venv/thehive-dev/bin/activate
   ```

4. **Git with LFS**
   ```bash
   # Ubuntu/Debian
   sudo apt install -y git git-lfs
   
   # macOS
   brew install git git-lfs
   
   # Configure Git LFS
   git lfs install
   ```

### Optional but Recommended

1. **NVIDIA CUDA Toolkit** (for GPU acceleration)
   ```bash
   # Ubuntu/Debian
   wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda_12.2.0_535.54.03_linux.run
   sudo sh cuda_12.2.0_535.54.03_linux.run
   
   # Add to PATH
   echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
   echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
   source ~/.bashrc
   ```

2. **Development Tools**
   ```bash
   # Ubuntu/Debian
   sudo apt install -y build-essential curl wget vim htop iotop
   
   # macOS
   xcode-select --install
   brew install curl wget htop
   ```

---

## 🚀 Quick Setup (5 Minutes)

For developers who want to get started immediately:

```bash
# 1. Clone repository
git clone https://github.com/yourusername/thehive.git
cd thehive

# 2. Copy environment template
cd backend/infra
cp .env.template .env

# 3. Start all services
docker-compose up -d

# 4. Start frontend (in new terminal)
cd ../../
npm install
npm run dev

# 5. Verify setup
curl http://localhost:8001/health  # STT service
curl http://localhost:8002/health  # MT service  
curl http://localhost:8003/health  # TTS service
curl http://localhost:8004/health  # Auth service

# 6. Access the application
open http://localhost:5173
```

**If all health checks pass, you're ready to develop! 🎉**

---

## 🛠️ Detailed Development Setup

### 1. Repository Setup

```bash
# Clone with all submodules
git clone --recursive https://github.com/yourusername/thehive.git
cd thehive

# If already cloned without --recursive
git submodule update --init --recursive

# Set up Git hooks for code quality
cp .githooks/* .git/hooks/
chmod +x .git/hooks/*
```

### 2. Frontend Development Environment

```bash
# Navigate to project root
cd thehive

# Install all dependencies
npm install

# Install additional development tools
npm install -g typescript eslint prettier

# Verify TypeScript configuration
npx tsc --noEmit

# Start development server with hot reload
npm run dev

# In another terminal, start signaling server
npm run dev:signaling

# Or start both simultaneously
npm run dev:both
```

**Frontend Structure:**
```
src/
├── components/          # React components (24 components)
│   ├── translation/     # Translation-specific UI
│   └── ...             # Website and call interface components
├── hooks/              # Custom React hooks (17 hooks)  
│   ├── useWebRTC.ts    # Main WebRTC functionality
│   ├── useTranslated*.ts # Translation-related hooks
│   └── ...             # Audio, device, and utility hooks
├── services/           # API clients and utilities
├── types/              # TypeScript type definitions
└── ...
```

**Key Development Commands:**
```bash
# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test
```

### 3. Backend Services Development

#### Core Services Setup

```bash
cd backend/infra

# Create development environment file
cp .env.template .env

# Edit configuration for development
vim .env
```

**Key Development Configuration:**
```bash
# .env for development
ENVIRONMENT=development
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# LiveKit Configuration
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_SECRET_KEY=devsecret

# Service URLs (for local development)
STT_SERVICE_URL=ws://localhost:8001/ws
MT_SERVICE_URL=http://localhost:8002
TTS_SERVICE_URL=http://localhost:8003
AUTH_SERVICE_URL=http://localhost:8004

# Development optimizations
STT_MODEL_SIZE=tiny.en          # Faster loading for development
MT_CONTEXT_LENGTH=256           # Smaller context for faster processing
TTS_VOICE_PRELOAD=false         # Disable voice preloading in dev
CHUNK_DURATION_MS=500           # Larger chunks for easier debugging
```

#### Start All Services

```bash
# Start core infrastructure
docker-compose up -d redis livekit coturn

# Start translation services
docker-compose up -d stt-service mt-service tts-service auth-service

# Start monitoring stack (optional for development)
docker-compose up -d prometheus grafana jaeger

# Verify all services
docker-compose ps
```

**Expected Output:**
```
Name                    State    Ports
----------------------------------------
hive-redis             Up       6379/tcp
hive-livekit          Up       7880/tcp, 7881/tcp
hive-coturn           Up       3478/udp, 5349/tcp
hive-stt-service      Up       8001/tcp
hive-mt-service       Up       8002/tcp  
hive-tts-service      Up       8003/tcp
hive-auth-service     Up       8004/tcp
```

#### Individual Service Development

**STT Service Development:**
```bash
cd backend/services/stt

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python app.py --dev --log-level DEBUG

# Run tests
python -m pytest tests/ -v

# Run benchmarks
python benchmark.py --iterations 10
```

**MT Service Development:**
```bash
cd backend/services/mt

# Install dependencies
pip install -r requirements.txt

# Download development models
python -c "
from transformers import MarianMTModel, MarianTokenizer
model_name = 'Helsinki-NLP/opus-mt-en-es'
model = MarianMTModel.from_pretrained(model_name)
tokenizer = MarianTokenizer.from_pretrained(model_name)
print('Development models loaded successfully')
"

# Run service
python app.py --dev

# Run performance tests
python -m pytest tests/test_performance.py -v
```

**TTS Service Development:**
```bash
cd backend/services/tts

# Install dependencies (includes TTS engines)
pip install -r requirements.txt

# Test TTS engines
python test_tts.py --engine piper
python test_tts.py --engine speecht5

# Run service
python app.py --dev

# Run synthesis tests
python -m pytest tests/ -v
```

### 4. Database and State Management

**Redis Development Setup:**
```bash
# Connect to Redis for debugging
redis-cli -h localhost -p 6379

# Common Redis debugging commands
redis-cli info
redis-cli keys "*"
redis-cli flushall  # Clear all data (development only!)

# Monitor Redis operations
redis-cli monitor
```

**LiveKit Development:**
```bash
# Access LiveKit admin interface
open http://localhost:7880

# Test room creation
curl -X POST http://localhost:7880/twirp/livekit.RoomService/CreateRoom \
  -H "Authorization: Bearer devkey" \
  -d '{"name": "dev-test-room"}'

# List active rooms
curl http://localhost:7880/twirp/livekit.RoomService/ListRooms \
  -H "Authorization: Bearer devkey"
```

---

## 🧪 Testing Setup

### Unit Tests

```bash
# Frontend tests
npm test
npm run test:coverage

# Backend service tests
cd backend/services/stt && python -m pytest tests/ -v
cd backend/services/mt && python -m pytest tests/ -v  
cd backend/services/tts && python -m pytest tests/ -v
```

### Integration Tests

```bash
# Start all services first
cd backend/infra && docker-compose up -d

# Run integration tests
cd ../../qa
python -m pytest integration_tests.py -v

# Run SLO validation tests
python slo_tests.py --environment development
```

### Load Testing

```bash
# Install load testing tools
cd qa
pip install -r requirements.txt

# Run basic load test
python load_tests.py --concurrent 5 --duration 60

# Run translation pipeline test
python test_runner.py --test translation_pipeline --iterations 100
```

### End-to-End Testing

```bash
# Install Playwright for E2E tests
npm install -g @playwright/test
npx playwright install

# Run E2E tests
cd qa/e2e
npx playwright test

# Run specific test suite
npx playwright test --grep "translation functionality"
```

---

## 🔧 Development Tools and IDE Setup

### VS Code Configuration

Create `.vscode/settings.json`:
```json
{
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "python.defaultInterpreterPath": "~/.venv/thehive-dev/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "files.associations": {
    "*.env*": "properties"
  }
}
```

**Recommended VS Code Extensions:**
- TypeScript and JavaScript
- Python
- Docker
- GitLens
- Prettier - Code formatter
- ESLint
- Python Docstring Generator
- REST Client

### Debugging Configuration

**Frontend Debugging (.vscode/launch.json):**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug React App",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/node_modules/.bin/vite",
      "args": ["--mode", "development"],
      "console": "integratedTerminal",
      "internalConsoleOptions": "neverOpen"
    }
  ]
}
```

**Backend Service Debugging:**
```python
# Add to service files for debugging
import debugpy
debugpy.listen(5678)
print("Waiting for debugger attach...")
debugpy.wait_for_client()
```

---

## 📊 Development Monitoring

### Local Monitoring Setup

```bash
# Start monitoring stack
cd backend/infra
docker-compose up -d prometheus grafana jaeger

# Access monitoring interfaces
open http://localhost:3001    # Grafana (admin/hive2024)
open http://localhost:9090    # Prometheus
open http://localhost:16686   # Jaeger tracing
```

### Custom Metrics for Development

```python
# Add custom metrics to your development code
from backend.observability.metrics import get_metrics

metrics = get_metrics("my-dev-component")
metrics.record_processing_time(duration_ms)
metrics.record_custom_metric("debug_counter", 1)
```

### Log Analysis

```bash
# View logs from all services
docker-compose logs -f

# Filter logs by service
docker-compose logs -f stt-service

# Search logs for errors
docker-compose logs | grep -E "(ERROR|CRITICAL|EXCEPTION)"

# Export logs for analysis
docker-compose logs --since "1h" > development-logs.txt
```

---

## 🌟 Development Workflow

### 1. Feature Development Process

```bash
# 1. Create feature branch
git checkout -b feature/new-translation-feature

# 2. Make changes and test locally
npm run dev
# Test your changes at http://localhost:5173

# 3. Run full test suite
npm test
cd qa && python run_tests.sh

# 4. Check code quality
npm run lint
npm run type-check

# 5. Commit changes
git add .
git commit -m "feat: add new translation feature

- Implement real-time caption synchronization
- Add German language support
- Update voice selection UI
- Tests: add unit tests for new components"

# 6. Push and create PR
git push origin feature/new-translation-feature
```

### 2. Testing Your Changes

**Frontend Changes:**
```bash
# Hot reload testing
npm run dev
# Navigate to http://localhost:5173/call
# Test translation functionality

# Component testing
npm test -- --watch
# Test specific component
npm test CallInterface
```

**Backend Changes:**
```bash
# Restart specific service after changes
docker-compose restart stt-service

# Test API endpoints
curl -X POST http://localhost:8001/transcribe \
  -F "audio=@test-files/sample.wav"

# Check service health
curl http://localhost:8001/health
```

### 3. Performance Testing

```bash
# Quick performance check
cd qa
python slo_tests.py --quick

# Latency validation
cd backend/infra/network-testing
python latency-validator.py --iterations 50

# Memory usage monitoring
docker stats --no-stream | grep -E "(stt|mt|tts)"
```

---

## 🐛 Common Development Issues

### 1. Docker Issues

**Problem**: Services won't start
```bash
# Solution: Check Docker daemon and clean up
sudo systemctl start docker
docker system prune -f
docker-compose down && docker-compose up -d
```

**Problem**: Port conflicts
```bash
# Solution: Check what's using ports
sudo lsof -i :8001
sudo lsof -i :8002
sudo lsof -i :8003
# Kill conflicting processes or change ports in docker-compose.yml
```

### 2. Node.js/npm Issues

**Problem**: Module not found or version conflicts
```bash
# Solution: Clean install
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**Problem**: TypeScript compilation errors
```bash
# Solution: Check TypeScript version and configuration
npx tsc --version
npx tsc --noEmit
# Update @types/* packages if needed
npm update @types/*
```

### 3. Python/ML Model Issues

**Problem**: GPU not detected
```bash
# Solution: Check CUDA installation
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
# Reinstall PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Problem**: Model download failures
```bash
# Solution: Manual model download
cd backend/services/stt
python -c "
from faster_whisper import WhisperModel
model = WhisperModel('base.en', device='cpu')
print('Model downloaded successfully')
"
```

### 4. WebRTC Issues

**Problem**: Audio not working in development
```bash
# Solution: Use HTTPS or localhost exception
# Add to browser flags: --unsafely-treat-insecure-origin-as-secure=http://localhost:5173
# Or set up local HTTPS development
```

**Problem**: TURN server not connecting
```bash
# Solution: Check CoTURN configuration
docker-compose logs coturn
sudo ufw allow 3478/udp
sudo ufw allow 5349/tcp
```

---

## 📚 Development Resources

### Documentation
- [React 19 Documentation](https://react.dev/)
- [LiveKit Client SDK](https://docs.livekit.io/client-sdks/js/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

### Internal Resources
- **Architecture**: See `CLAUDE.md` for system architecture
- **API Reference**: See `SERVICE_CLIENT_SPECS.md` for complete API docs
- **Runbook**: See `RUNBOOK.md` for operational procedures
- **Troubleshooting**: See `TROUBLESHOOTING.md` for common issues

### Team Communication
- **Slack**: #the-hive-dev for development discussions
- **Slack**: #the-hive-alerts for system notifications
- **GitHub**: Use issues for bug reports and feature requests
- **Weekly Standups**: Tuesdays 10 AM PST / 1 PM EST

---

## 🎯 Development Checklist

### Before Starting Development
- [ ] All prerequisites installed and verified
- [ ] Repository cloned and submodules updated
- [ ] Docker services running and healthy
- [ ] Frontend development server running
- [ ] All health checks passing
- [ ] Development branch created from main

### Before Submitting PR
- [ ] All tests passing (unit, integration, E2E)
- [ ] TypeScript compilation successful
- [ ] ESLint and Prettier checks passing
- [ ] SLO targets met (TTFT <500ms, accuracy >95%)
- [ ] Performance tests completed
- [ ] Documentation updated if needed
- [ ] Code reviewed by at least one team member

### Before Merging
- [ ] CI/CD pipeline passing
- [ ] Integration tests in staging environment
- [ ] Performance regression tests completed
- [ ] Security review if touching auth/security components
- [ ] Deployment plan reviewed

---

## 🚀 Next Steps

Once your development environment is set up:

1. **Explore the Codebase**: Start with `src/components/Call.tsx` and `backend/agents/translator_worker.py`
2. **Run Example Tests**: Execute the QA test suite to understand system behavior
3. **Make Your First Contribution**: Look for issues labeled "good first issue" 
4. **Join Team Meetings**: Attend weekly standups and architecture discussions
5. **Read Documentation**: Review all documentation files for deeper understanding

Welcome to The HIVE development team! Happy coding! 🎉

---

**Need Help?**
- Slack: #the-hive-dev
- Email: dev-team@thehive.com
- Office Hours: Daily 2-3 PM PST

**Document Version**: 1.0  
**Last Updated**: $(date +%Y-%m-%d)  
**Next Review**: $(date -d "+1 month" +%Y-%m-%d)