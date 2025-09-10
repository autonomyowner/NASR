#!/bin/bash
# Network Impairment Testing for The HIVE Translation System
# Test resilience under various network conditions for sub-500ms SLA

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INTERFACE=${1:-eth0}
LOG_FILE="/var/log/hive-network-test.log"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a $LOG_FILE
}

# Clean up any existing rules
cleanup() {
    log "Cleaning up network impairment rules..."
    tc qdisc del dev $INTERFACE root 2>/dev/null || true
    log "Cleanup complete"
}

# Trap cleanup on exit
trap cleanup EXIT

# Test Scenario 1: Baseline - Clean Network
test_baseline() {
    log "=== BASELINE TEST: Clean Network ==="
    cleanup
    log "Network conditions: No impairment"
    log "Expected: p95 latency <500ms, <1% packet loss"
    sleep 2
}

# Test Scenario 2: 1% Packet Loss (Light Impairment)
test_light_packet_loss() {
    log "=== TEST 2: Light Packet Loss (1%) ==="
    cleanup
    
    # Add 1% packet loss
    tc qdisc add dev $INTERFACE root netem loss 1%
    log "Applied: 1% random packet loss"
    log "Expected: RED/PLC should compensate, <600ms latency"
    sleep 5
    
    # Test with correlation (burst losses)
    tc qdisc change dev $INTERFACE root netem loss 1% 25%
    log "Applied: 1% packet loss with 25% correlation (burst losses)"
    sleep 5
}

# Test Scenario 3: 5% Packet Loss (Heavy Impairment)
test_heavy_packet_loss() {
    log "=== TEST 3: Heavy Packet Loss (5%) ==="
    cleanup
    
    tc qdisc add dev $INTERFACE root netem loss 5%
    log "Applied: 5% random packet loss"
    log "Expected: Significant RED/PLC activation, possible degradation"
    sleep 5
}

# Test Scenario 4: Additional Latency (50ms)
test_additional_latency() {
    log "=== TEST 4: Additional Network Latency (50ms) ==="
    cleanup
    
    tc qdisc add dev $INTERFACE root netem delay 50ms
    log "Applied: 50ms additional latency"
    log "Expected: Total latency <550ms, jitter buffer adaptation"
    sleep 5
    
    # Add jitter
    tc qdisc change dev $INTERFACE root netem delay 50ms 10ms
    log "Applied: 50ms ± 10ms latency with jitter"
    log "Expected: Adaptive jitter buffer should compensate"
    sleep 5
}

# Test Scenario 5: Variable Jitter (Network Instability)
test_jitter() {
    log "=== TEST 5: High Network Jitter ==="
    cleanup
    
    # High jitter simulation
    tc qdisc add dev $INTERFACE root netem delay 30ms 20ms
    log "Applied: 30ms ± 20ms jitter (10-50ms range)"
    log "Expected: Jitter buffer should adapt, possible quality reduction"
    sleep 5
    
    # Add packet reordering
    tc qdisc change dev $INTERFACE root netem delay 30ms 20ms reorder 5% 50%
    log "Applied: Added 5% packet reordering"
    sleep 5
}

# Test Scenario 6: Bandwidth Limitation
test_bandwidth_limit() {
    log "=== TEST 6: Bandwidth Limitation ==="
    cleanup
    
    # Limit bandwidth to 128kbps (challenging for audio)
    tc qdisc add dev $INTERFACE root handle 1: tbf rate 128kbit burst 32kbit latency 400ms
    log "Applied: 128kbps bandwidth limit"
    log "Expected: Adaptive bitrate should reduce quality"
    sleep 5
    
    # Even more restrictive
    tc qdisc change dev $INTERFACE root handle 1: tbf rate 64kbit burst 16kbit latency 400ms
    log "Applied: 64kbps bandwidth limit (extreme)"
    log "Expected: Possible connection issues, minimum quality"
    sleep 5
}

# Test Scenario 7: Mobile Network Simulation
test_mobile_network() {
    log "=== TEST 7: Mobile Network Simulation ==="
    cleanup
    
    # Simulate 3G network conditions
    tc qdisc add dev $INTERFACE root handle 1: netem delay 150ms 50ms loss 2%
    tc qdisc add dev $INTERFACE parent 1:1 handle 10: tbf rate 384kbit burst 32kbit latency 400ms
    log "Applied: 3G simulation - 150ms±50ms latency, 2% loss, 384kbps limit"
    sleep 5
    
    # Simulate 4G network with congestion
    tc qdisc change dev $INTERFACE root handle 1: netem delay 80ms 20ms loss 1%
    tc qdisc change dev $INTERFACE parent 1:1 handle 10: tbf rate 1mbit burst 64kbit latency 300ms
    log "Applied: 4G congestion - 80ms±20ms latency, 1% loss, 1Mbps limit"
    sleep 5
}

# Test Scenario 8: Extreme Conditions (Stress Test)
test_extreme_conditions() {
    log "=== TEST 8: Extreme Network Conditions (Stress Test) ==="
    cleanup
    
    # Combine multiple impairments
    tc qdisc add dev $INTERFACE root handle 1: netem delay 100ms 30ms loss 3% reorder 10% 25%
    tc qdisc add dev $INTERFACE parent 1:1 handle 10: tbf rate 256kbit burst 32kbit latency 500ms
    log "Applied: EXTREME - 100ms±30ms latency, 3% loss, 10% reorder, 256kbps limit"
    log "Expected: System should maintain basic functionality or fail gracefully"
    sleep 10
}

# Real-time monitoring functions
monitor_performance() {
    local duration=${1:-10}
    log "Monitoring network performance for ${duration} seconds..."
    
    # Monitor ping latency to localhost (simulates internal routing)
    ping -c $duration localhost | grep 'time=' | awk '{print $7}' | sed 's/time=//' >> /tmp/ping_results.txt &
    
    # Monitor UDP packet statistics
    ss -u -a -n > /tmp/udp_stats_before.txt
    sleep $duration
    ss -u -a -n > /tmp/udp_stats_after.txt
    
    log "Performance monitoring complete. Check /tmp/ping_results.txt for latency data"
}

# Generate performance report
generate_report() {
    log "=== NETWORK IMPAIRMENT TEST REPORT ==="
    
    if [ -f /tmp/ping_results.txt ]; then
        avg_latency=$(cat /tmp/ping_results.txt | awk '{sum+=$1} END {print sum/NR}' 2>/dev/null || echo "N/A")
        max_latency=$(cat /tmp/ping_results.txt | sort -n | tail -1 2>/dev/null || echo "N/A")
        log "Average Latency: ${avg_latency}ms"
        log "Maximum Latency: ${max_latency}ms"
    fi
    
    log "Test completed at $(date)"
    log "Full log available at: $LOG_FILE"
}

# Main test execution
main() {
    log "Starting The HIVE Network Impairment Testing Suite"
    log "Target Interface: $INTERFACE"
    log "Testing for sub-500ms end-to-end latency resilience"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root for network configuration"
        exit 1
    fi
    
    # Check if tc is available
    if ! command -v tc &> /dev/null; then
        error "tc (traffic control) command not found. Install iproute2 package."
        exit 1
    fi
    
    # Run test scenarios
    test_baseline
    monitor_performance 10
    
    test_light_packet_loss
    monitor_performance 10
    
    test_heavy_packet_loss
    monitor_performance 10
    
    test_additional_latency
    monitor_performance 10
    
    test_jitter
    monitor_performance 10
    
    test_bandwidth_limit
    monitor_performance 10
    
    test_mobile_network
    monitor_performance 15
    
    test_extreme_conditions
    monitor_performance 15
    
    # Final cleanup and report
    cleanup
    generate_report
    
    log "Network impairment testing completed successfully"
}

# Script usage information
usage() {
    echo "Usage: $0 [interface]"
    echo "  interface: Network interface to test (default: eth0)"
    echo ""
    echo "Example: $0 eth0"
    echo ""
    echo "This script tests The HIVE translation system under various network conditions:"
    echo "- Packet loss (1%, 5%)"
    echo "- Additional latency (50ms)"
    echo "- Network jitter"
    echo "- Bandwidth limitations"
    echo "- Mobile network simulation"
    echo "- Extreme stress conditions"
}

# Handle script arguments
case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac