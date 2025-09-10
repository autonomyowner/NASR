#!/bin/bash

# The HIVE LiveKit SFU Development Setup Script
# Automated setup for local development environment with optimized LiveKit configuration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_TEMPLATE="$SCRIPT_DIR/.env.template"

log_info "Starting The HIVE LiveKit SFU development setup..."
log_info "Project root: $PROJECT_ROOT"
log_info "Infrastructure directory: $SCRIPT_DIR"

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check OpenSSL for key generation
    if ! command -v openssl &> /dev/null; then
        log_warning "OpenSSL not found. Will use fallback key generation."
    fi
    
    log_success "Prerequisites check completed"
}

# Generate secure random keys
generate_key() {
    local length=$1
    if command -v openssl &> /dev/null; then
        openssl rand -hex $length
    else
        # Fallback using /dev/urandom
        tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w $((length * 2)) | head -n 1
    fi
}

# Setup environment file
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [[ -f "$ENV_FILE" ]]; then
        log_warning "Environment file already exists: $ENV_FILE"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing environment file"
            return 0
        fi
    fi
    
    if [[ ! -f "$ENV_TEMPLATE" ]]; then
        log_error "Environment template not found: $ENV_TEMPLATE"
        exit 1
    fi
    
    log_info "Generating secure keys..."
    
    # Generate secure keys
    LIVEKIT_API_KEY=$(generate_key 16)
    LIVEKIT_SECRET_KEY=$(generate_key 32)
    AUTH_SERVICE_API_KEY=$(generate_key 32)
    TURN_SECRET_KEY=$(generate_key 32)
    REST_API_SECRET=$(generate_key 16)
    
    # Copy template and substitute keys
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    
    # Replace placeholder values with generated keys
    sed -i.bak "s/LIVEKIT_API_KEY=devkey/LIVEKIT_API_KEY=$LIVEKIT_API_KEY/" "$ENV_FILE"
    sed -i.bak "s/LIVEKIT_SECRET_KEY=devsecret/LIVEKIT_SECRET_KEY=$LIVEKIT_SECRET_KEY/" "$ENV_FILE"
    sed -i.bak "s/AUTH_SERVICE_API_KEY=/AUTH_SERVICE_API_KEY=$AUTH_SERVICE_API_KEY/" "$ENV_FILE"
    sed -i.bak "s/TURN_SECRET_KEY=your-ultra-secure-secret-key-change-in-production/TURN_SECRET_KEY=$TURN_SECRET_KEY/" "$ENV_FILE"
    sed -i.bak "s/REST_API_SECRET=rest-api-secret-change-me/REST_API_SECRET=$REST_API_SECRET/" "$ENV_FILE"
    
    # Set development-specific values
    sed -i.bak "s/ENVIRONMENT=development/ENVIRONMENT=development/" "$ENV_FILE"
    sed -i.bak "s/DEBUG_MODE=true/DEBUG_MODE=true/" "$ENV_FILE"
    
    # Clean up backup file
    rm -f "$ENV_FILE.bak"
    
    log_success "Environment configuration created: $ENV_FILE"
    log_info "Generated secure keys for development use"
}

# Setup CoTURN certificates (self-signed for development)
setup_coturn_certs() {
    log_info "Setting up CoTURN certificates..."
    
    local cert_dir="$SCRIPT_DIR/coturn/certs"
    mkdir -p "$cert_dir"
    
    if [[ -f "$cert_dir/turn_server_cert.pem" ]]; then
        log_info "CoTURN certificates already exist"
        return 0
    fi
    
    log_info "Generating self-signed certificates for development..."
    
    # Generate private key
    openssl genpkey -algorithm RSA -out "$cert_dir/turn_server_pkey.pem" -pkcs8 2>/dev/null || {
        log_warning "Failed to generate RSA key, trying alternative method"
        openssl genrsa -out "$cert_dir/turn_server_pkey.pem" 2048 2>/dev/null
    }
    
    # Generate self-signed certificate
    openssl req -new -x509 -key "$cert_dir/turn_server_pkey.pem" \
        -out "$cert_dir/turn_server_cert.pem" -days 365 \
        -subj "/C=US/ST=Development/L=LocalDev/O=TheHive/OU=SFU/CN=localhost" 2>/dev/null
    
    # Create CA certificate (same as server cert for development)
    cp "$cert_dir/turn_server_cert.pem" "$cert_dir/ca_cert.pem"
    
    # Generate DH parameters (this can take a while)
    log_info "Generating DH parameters (this may take a few minutes)..."
    openssl dhparam -out "$cert_dir/dhparam.pem" 2048 2>/dev/null || {
        log_warning "Failed to generate DH parameters, using built-in defaults"
        echo "# Using built-in DH parameters" > "$cert_dir/dhparam.pem"
    }
    
    log_success "CoTURN certificates generated"
}

# Start services
start_services() {
    log_info "Starting LiveKit SFU infrastructure..."
    
    cd "$SCRIPT_DIR"
    
    # Pull latest images
    log_info "Pulling Docker images..."
    docker-compose pull
    
    # Start core infrastructure services first
    log_info "Starting core services (Redis, CoTURN)..."
    docker-compose up -d redis coturn
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    timeout 30 bash -c 'until docker-compose exec redis redis-cli ping; do sleep 1; done' || {
        log_error "Redis failed to start within 30 seconds"
        docker-compose logs redis
        exit 1
    }
    
    # Start LiveKit SFU
    log_info "Starting LiveKit SFU..."
    docker-compose up -d livekit
    
    # Wait for LiveKit to be ready
    log_info "Waiting for LiveKit to be ready..."
    timeout 60 bash -c 'until curl -f http://localhost:7880/health >/dev/null 2>&1; do sleep 2; done' || {
        log_error "LiveKit failed to start within 60 seconds"
        docker-compose logs livekit
        exit 1
    }
    
    # Start translation services
    log_info "Starting translation services..."
    docker-compose up -d stt-service mt-service tts-service auth-service
    
    # Start translator workers
    log_info "Starting translator workers..."
    docker-compose up -d translator-worker
    
    # Start monitoring services
    log_info "Starting monitoring services..."
    docker-compose up -d prometheus grafana jaeger
    
    log_success "All services started successfully!"
}

# Health check
health_check() {
    log_info "Performing health checks..."
    
    local failed=0
    
    # Check LiveKit
    if curl -f http://localhost:7880/health >/dev/null 2>&1; then
        log_success "✓ LiveKit SFU is healthy"
    else
        log_error "✗ LiveKit SFU health check failed"
        failed=1
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        log_success "✓ Redis is healthy"
    else
        log_error "✗ Redis health check failed"
        failed=1
    fi
    
    # Check CoTURN (check if port is listening)
    if nc -z localhost 3478 2>/dev/null; then
        log_success "✓ CoTURN is healthy"
    else
        log_error "✗ CoTURN health check failed"
        failed=1
    fi
    
    # Check Auth Service
    if curl -f http://localhost:8003/health >/dev/null 2>&1; then
        log_success "✓ Auth Service is healthy"
    else
        log_warning "⚠ Auth Service health check failed (may still be starting)"
    fi
    
    # Check Translation Services
    for service in stt mt tts; do
        local port
        case $service in
            stt) port=8000 ;;
            mt) port=8001 ;;
            tts) port=8002 ;;
        esac
        
        if curl -f http://localhost:$port/health >/dev/null 2>&1; then
            log_success "✓ ${service^^} Service is healthy"
        else
            log_warning "⚠ ${service^^} Service health check failed (may still be starting)"
        fi
    done
    
    if [[ $failed -eq 0 ]]; then
        log_success "All core services are healthy!"
        return 0
    else
        log_error "Some services failed health checks"
        return 1
    fi
}

# Display service information
show_service_info() {
    log_info "Service endpoints:"
    echo
    echo "🎯 Core Services:"
    echo "  LiveKit SFU:          http://localhost:7880"
    echo "  LiveKit WebSocket:    ws://localhost:7880"
    echo "  CoTURN STUN/TURN:     stun:localhost:3478"
    echo "  Redis:                redis://localhost:6379"
    echo
    echo "🔐 Authentication:"
    echo "  JWT Auth Service:     http://localhost:8003"
    echo "  Auth API Docs:        http://localhost:8003/docs"
    echo
    echo "🌐 Translation Services:"
    echo "  STT Service:          http://localhost:8000"
    echo "  MT Service:           http://localhost:8001"
    echo "  TTS Service:          http://localhost:8002"
    echo
    echo "📊 Monitoring:"
    echo "  Grafana:              http://localhost:3001"
    echo "  Prometheus:           http://localhost:9090"
    echo "  Jaeger:               http://localhost:16686"
    echo
    echo "🔑 Credentials:"
    echo "  Grafana:              admin / admin123"
    echo "  API Key:              $(grep AUTH_SERVICE_API_KEY $ENV_FILE | cut -d= -f2)"
    echo
    echo "📝 Configuration Files:"
    echo "  Environment:          $ENV_FILE"
    echo "  LiveKit Config:       $SCRIPT_DIR/livekit/server-optimized.yaml"
    echo "  CoTURN Config:        $SCRIPT_DIR/coturn/turnserver-optimized.conf"
    echo
    log_success "The HIVE LiveKit SFU is ready for development! 🚀"
    echo
    echo "Next steps:"
    echo "1. Start the frontend: npm run dev (in project root)"
    echo "2. Test call functionality at http://localhost:5173/call"
    echo "3. Monitor performance at http://localhost:3001 (Grafana)"
    echo "4. View logs: docker-compose logs -f [service-name]"
}

# Cleanup function
cleanup() {
    if [[ "${1:-}" == "stop" ]]; then
        log_info "Stopping all services..."
        cd "$SCRIPT_DIR"
        docker-compose down
        log_success "All services stopped"
    fi
}

# Main execution
main() {
    case "${1:-setup}" in
        "setup"|"start")
            check_prerequisites
            setup_environment
            setup_coturn_certs
            start_services
            sleep 5  # Give services time to fully start
            if health_check; then
                show_service_info
            else
                log_warning "Some services may still be starting. Run 'docker-compose logs' to check status."
                show_service_info
            fi
            ;;
        "stop")
            cleanup "stop"
            ;;
        "status")
            health_check
            show_service_info
            ;;
        "logs")
            cd "$SCRIPT_DIR"
            docker-compose logs -f "${2:-}"
            ;;
        "restart")
            cleanup "stop"
            sleep 2
            main "start"
            ;;
        "health")
            health_check
            ;;
        *)
            echo "Usage: $0 {setup|start|stop|restart|status|health|logs [service]}"
            echo
            echo "Commands:"
            echo "  setup/start  - Setup and start all services"
            echo "  stop         - Stop all services"
            echo "  restart      - Restart all services"
            echo "  status       - Show service status and endpoints"
            echo "  health       - Run health checks"
            echo "  logs [srv]   - Show logs (optionally for specific service)"
            exit 1
            ;;
    esac
}

# Trap cleanup on script exit
trap 'cleanup' EXIT

# Run main function with all arguments
main "$@"