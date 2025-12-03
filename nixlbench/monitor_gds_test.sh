#!/bin/bash
#
# Real-time GDS Test Monitor
# Monitors system during GDS test execution
#

set -e

MONITOR_INTERVAL=${MONITOR_INTERVAL:-2}  # seconds
LOG_FILE="${LOG_FILE:-./gds_monitor_$(date +%Y%m%d_%H%M%S).log}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=================================="
echo "GDS Test Monitor"
echo "Monitoring interval: ${MONITOR_INTERVAL}s"
echo "Log file: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo "=================================="
echo

# Function to get timestamp
timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Function to log with timestamp
log() {
    echo "[$(timestamp)] $*" | tee -a "$LOG_FILE"
}

# Trap Ctrl+C
trap 'echo; log "Monitoring stopped"; exit 0' INT

log "Starting GDS test monitoring..."

while true; do
    {
        echo "=========================================="
        echo "Timestamp: $(timestamp)"
        echo "=========================================="
        echo
        
        # GPU Status
        if command -v nvidia-smi &> /dev/null; then
            echo "--- GPU Status ---"
            nvidia-smi --query-gpu=index,name,memory.used,memory.free,memory.total,temperature.gpu,power.draw --format=csv,noheader
            echo
            
            echo "--- GPU Processes ---"
            nvidia-smi pmon -c 1 | head -10
            echo
        fi
        
        # System Memory
        echo "--- System Memory ---"
        free -h | head -2
        echo
        
        # Recent dmesg errors
        echo "--- Recent Kernel Messages (errors/warnings) ---"
        dmesg | tail -5 | grep -i "error\|warn\|fail" || echo "No recent errors"
        echo
        
        # nixlbench processes
        echo "--- nixlbench Processes ---"
        ps aux | grep nixlbench | grep -v grep || echo "No nixlbench processes"
        echo
        
        # CPU Load
        echo "--- System Load ---"
        uptime
        echo
        
    } | tee -a "$LOG_FILE"
    
    sleep "$MONITOR_INTERVAL"
done

