#!/bin/bash

# The HIVE QA Test Runner Script
# Comprehensive testing harness for production validation

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../backend/infra"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="${SCRIPT_DIR}/results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
The HIVE QA Test Runner

Usage: $0 [OPTIONS]

OPTIONS:
    -m, --mode MODE         Test mode: quick|comprehensive (default: comprehensive)
    -t, --tests TESTS       Specific test suites (comma-separated)
                           Available: slo_validation,network_resilience,integration_tests,
                                     load_tests,quality_tests,deployment_gates
    -o, --output FILE       Output file for results (default: auto-generated)
    -s, --skip-services     Skip service health checks
    -v, --verbose          Enable verbose logging
    -h, --help             Show this help message

EXAMPLES:
    $0                                    # Run comprehensive tests
    $0 -m quick                          # Run quick validation
    $0 -t slo_validation,deployment_gates # Run specific tests
    $0 -m quick -o results.json -v       # Quick mode with custom output

EOF
}

# Parse command line arguments
MODE="comprehensive"
TESTS=""
OUTPUT_FILE=""
SKIP_SERVICES=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -t|--tests)
            TESTS="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -s|--skip-services)
            SKIP_SERVICES=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate mode
if [[ "$MODE" != "quick" && "$MODE" != "comprehensive" ]]; then
    error "Invalid mode: $MODE. Must be 'quick' or 'comprehensive'"
    exit 1
fi

# Set default output file if not specified
if [[ -z "$OUTPUT_FILE" ]]; then
    OUTPUT_FILE="${RESULTS_DIR}/qa_results_${MODE}_${TIMESTAMP}.json"
fi

# Create results directory
mkdir -p "$RESULTS_DIR"

# Display configuration
log "The HIVE QA Test Runner Configuration:"
log "  Mode: $MODE"
log "  Tests: ${TESTS:-"all"}"
log "  Output: $OUTPUT_FILE"
log "  Skip Services: $SKIP_SERVICES"
log "  Verbose: $VERBOSE"
log ""

# Check Python dependencies
check_python_deps() {
    log "Checking Python dependencies..."
    
    local required_packages=("aiohttp" "numpy" "soundfile" "librosa" "scipy" "matplotlib" "psutil")
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        warning "Missing Python packages: ${missing_packages[*]}"
        log "Installing missing packages..."
        pip install "${missing_packages[@]}"
    else
        success "All Python dependencies available"
    fi
}

# Check service health
check_services() {
    if [[ "$SKIP_SERVICES" == true ]]; then
        warning "Skipping service health checks"
        return 0
    fi
    
    log "Checking service health..."
    
    local services=(
        "STT Service:http://localhost:8001/health"
        "MT Service:http://localhost:8002/health"
        "TTS Service:http://localhost:8003/health"
        "LiveKit:http://localhost:7880/"
    )
    
    local unhealthy_services=()
    
    for service in "${services[@]}"; do
        local name="${service%%:*}"
        local url="${service#*:}"
        
        if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
            success "$name is healthy"
        else
            error "$name is not responding"
            unhealthy_services+=("$name")
        fi
    done
    
    if [[ ${#unhealthy_services[@]} -gt 0 ]]; then
        error "Unhealthy services detected: ${unhealthy_services[*]}"
        log "Attempting to start services..."
        
        if start_services; then
            # Wait for services to be ready
            log "Waiting 30 seconds for services to initialize..."
            sleep 30
            
            # Recheck services
            log "Re-checking service health..."
            for service in "${services[@]}"; do
                local name="${service%%:*}"
                local url="${service#*:}"
                
                if curl -s --max-time 10 "$url" > /dev/null 2>&1; then
                    success "$name is now healthy"
                else
                    error "$name is still not responding"
                    return 1
                fi
            done
        else
            error "Failed to start services"
            return 1
        fi
    fi
    
    success "All services are healthy"
}

# Start backend services
start_services() {
    log "Starting backend services..."
    
    if [[ ! -f "$BACKEND_DIR/docker-compose.yml" ]]; then
        error "Docker compose file not found at $BACKEND_DIR/docker-compose.yml"
        return 1
    fi
    
    cd "$BACKEND_DIR"
    
    # Start services
    if docker-compose up -d; then
        success "Services started successfully"
        return 0
    else
        error "Failed to start services"
        return 1
    fi
}

# Run QA tests
run_tests() {
    log "Starting QA test execution..."
    
    cd "$SCRIPT_DIR"
    
    # Build Python command
    local python_cmd="python test_runner.py --mode $MODE --output \"$OUTPUT_FILE\""
    
    if [[ -n "$TESTS" ]]; then
        # Convert comma-separated tests to space-separated
        local test_args="${TESTS//,/ }"
        python_cmd="$python_cmd --tests $test_args"
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        python_cmd="$python_cmd --verbose"
    fi
    
    log "Executing: $python_cmd"
    log ""
    
    # Execute tests
    if eval "$python_cmd"; then
        local exit_code=$?
        
        if [[ $exit_code -eq 0 ]]; then
            success "QA tests completed successfully - DEPLOYMENT APPROVED"
            return 0
        else
            warning "QA tests completed with issues - check results for details"
            return $exit_code
        fi
    else
        local exit_code=$?
        error "QA tests failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Display results
display_results() {
    log "Test Results Summary:"
    log "  Results file: $OUTPUT_FILE"
    
    if [[ -f "$OUTPUT_FILE" ]]; then
        # Try to extract key metrics from JSON results
        if command -v jq >/dev/null 2>&1; then
            log ""
            log "Key Metrics:"
            
            local success_rate
            success_rate=$(jq -r '.summary.results_summary.success_rate // "N/A"' "$OUTPUT_FILE")
            log "  Success Rate: $success_rate"
            
            local production_ready
            production_ready=$(jq -r '.summary.quality_assessment.production_ready // "N/A"' "$OUTPUT_FILE")
            log "  Production Ready: $production_ready"
            
            local overall_status
            overall_status=$(jq -r '.summary.quality_assessment.overall_status // "N/A"' "$OUTPUT_FILE")
            log "  Overall Status: $overall_status"
            
        else
            warning "jq not installed - cannot parse JSON results"
        fi
        
        log ""
        log "Full results available in: $OUTPUT_FILE"
    else
        warning "Results file not found: $OUTPUT_FILE"
    fi
}

# Cleanup function
cleanup() {
    log "Performing cleanup..."
    # Add any necessary cleanup here
}

# Trap cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    log "Starting The HIVE QA Test Runner"
    log "========================================"
    
    # Check dependencies
    check_python_deps
    
    # Check services
    check_services
    
    # Run tests
    if run_tests; then
        local test_exit_code=$?
        
        # Display results
        display_results
        
        log ""
        if [[ $test_exit_code -eq 0 ]]; then
            success "🎉 QA validation completed successfully!"
            success "The HIVE translation system is ready for production deployment."
        else
            warning "⚠️  QA validation completed with issues."
            warning "Review the test results before proceeding with deployment."
        fi
        
        exit $test_exit_code
    else
        local test_exit_code=$?
        error "❌ QA validation failed!"
        error "The HIVE translation system requires fixes before deployment."
        
        # Still try to display results if available
        display_results
        
        exit $test_exit_code
    fi
}

# Execute main function
main "$@"