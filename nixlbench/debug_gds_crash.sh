#!/bin/bash
#
# GDS Crash Debugging Script
# Collects system diagnostics to help debug GDS test crashes
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEBUG_DIR="${DEBUG_DIR:-./debug_output}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to print status
print_status() {
    local status=$1
    local message=$2
    case $status in
        "ok") echo -e "${GREEN}[OK]${NC} $message" ;;
        "warn") echo -e "${YELLOW}[WARN]${NC} $message" ;;
        "error") echo -e "${RED}[ERROR]${NC} $message" ;;
        "info") echo -e "${BLUE}[INFO]${NC} $message" ;;
        *) echo "[ ] $message" ;;
    esac
}

echo "=================================="
echo "GDS Crash Debugging Tool"
echo "Started: $(date)"
echo "=================================="
echo

mkdir -p "$DEBUG_DIR"

# 1. System Information
print_status "info" "Collecting system information..."
{
    echo "=== System Information ==="
    echo "Hostname: $(hostname)"
    echo "Uptime: $(uptime)"
    echo "Kernel: $(uname -r)"
    echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')"
    echo "Date: $(date)"
    echo
} | tee "$DEBUG_DIR/system_info_${TIMESTAMP}.txt"

# 2. GPU Information
print_status "info" "Collecting GPU information..."
if command -v nvidia-smi &> /dev/null; then
    {
        echo "=== GPU Information ==="
        nvidia-smi
        echo
        echo "=== GPU Memory Details ==="
        nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,temperature.gpu,power.draw,power.limit --format=csv
        echo
        echo "=== GPU Processes ==="
        nvidia-smi pmon -c 1
        echo
    } | tee "$DEBUG_DIR/gpu_info_${TIMESTAMP}.txt"
else
    print_status "warn" "nvidia-smi not found"
fi

# 3. Kernel Messages (dmesg)
print_status "info" "Collecting kernel messages (dmesg)..."
{
    echo "=== Recent Kernel Messages (last 100 lines) ==="
    dmesg | tail -100
    echo
    echo "=== Kernel Errors ==="
    dmesg | grep -i "error\|fail\|crash\|panic\|oops\|bug" | tail -50
    echo
    echo "=== GDS/NVIDIA related messages ==="
    dmesg | grep -i "nvidia\|gds\|nvfs" | tail -50
    echo
} | tee "$DEBUG_DIR/dmesg_${TIMESTAMP}.txt"

# 4. System Logs
print_status "info" "Collecting system logs..."
{
    echo "=== Recent System Log (journalctl, last 100 lines) ==="
    journalctl -n 100 --no-pager 2>/dev/null || echo "journalctl not available"
    echo
    echo "=== System Log Errors ==="
    journalctl -p err -n 50 --no-pager 2>/dev/null || echo "journalctl not available"
    echo
} | tee "$DEBUG_DIR/system_logs_${TIMESTAMP}.txt"

# 5. Kernel Module Status
print_status "info" "Checking kernel modules..."
{
    echo "=== NVIDIA Modules ==="
    lsmod | grep -i nvidia
    echo
    echo "=== GDS Module (nvidia_fs) ==="
    lsmod | grep nvidia_fs || echo "nvidia_fs module not loaded"
    echo
    echo "=== Module Information ==="
    if lsmod | grep -q nvidia_fs; then
        modinfo nvidia_fs 2>/dev/null || echo "Cannot get nvidia_fs module info"
    fi
    echo
} | tee "$DEBUG_DIR/kernel_modules_${TIMESTAMP}.txt"

# 6. Memory Information
print_status "info" "Collecting memory information..."
{
    echo "=== System Memory ==="
    free -h
    echo
    echo "=== Memory Details ==="
    cat /proc/meminfo | head -20
    echo
    echo "=== GPU Memory (if available) ==="
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv
    fi
    echo
} | tee "$DEBUG_DIR/memory_info_${TIMESTAMP}.txt"

# 7. CPU Information
print_status "info" "Collecting CPU information..."
{
    echo "=== CPU Information ==="
    lscpu | head -20
    echo
    echo "=== CPU Load ==="
    uptime
    echo
    echo "=== Top Processes ==="
    ps aux --sort=-%mem | head -10
    echo
} | tee "$DEBUG_DIR/cpu_info_${TIMESTAMP}.txt"

# 8. Storage Information
print_status "info" "Collecting storage information..."
{
    echo "=== Mounted Filesystems ==="
    df -h
    echo
    echo "=== Block Devices ==="
    lsblk
    echo
    echo "=== Storage Test Directory ==="
    if [ -d "/tmp/nvme_raid0" ]; then
        ls -lh /tmp/nvme_raid0/ | head -20
        echo
        echo "Disk space:"
        df -h /tmp/nvme_raid0/
    fi
    echo
} | tee "$DEBUG_DIR/storage_info_${TIMESTAMP}.txt"

# 9. Running Processes
print_status "info" "Checking for nixlbench processes..."
{
    echo "=== nixlbench Processes ==="
    ps aux | grep nixlbench | grep -v grep || echo "No nixlbench processes running"
    echo
    echo "=== GPU Processes ==="
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi pmon -c 1
    fi
    echo
} | tee "$DEBUG_DIR/processes_${TIMESTAMP}.txt"

# 10. System Resource Limits
print_status "info" "Checking system limits..."
{
    echo "=== ulimit ==="
    ulimit -a
    echo
    echo "=== /proc/sys/kernel limits ==="
    cat /proc/sys/kernel/pid_max 2>/dev/null && echo "pid_max"
    cat /proc/sys/vm/overcommit_memory 2>/dev/null && echo "overcommit_memory"
    echo
} | tee "$DEBUG_DIR/limits_${TIMESTAMP}.txt"

# 11. Recent Crash Indicators
print_status "info" "Checking for crash indicators..."
{
    echo "=== Oops Messages ==="
    dmesg | grep -i "oops\|bug\|warn" | tail -20
    echo
    echo "=== Panic Messages ==="
    dmesg | grep -i "panic" | tail -20
    echo
    echo "=== Segmentation Faults ==="
    dmesg | grep -i "segfault\|segmentation" | tail -20
    echo
    echo "=== Out of Memory ==="
    dmesg | grep -i "out of memory\|oom" | tail -20
    echo
    echo "=== GPU Related Errors ==="
    dmesg | grep -i "gpu\|nvidia\|cuda" | grep -i "error\|fail" | tail -20
    echo
} | tee "$DEBUG_DIR/crash_indicators_${TIMESTAMP}.txt"

# 12. Create summary report
print_status "info" "Creating summary report..."
{
    echo "=================================="
    echo "GDS Crash Debug Summary"
    echo "Generated: $(date)"
    echo "=================================="
    echo
    echo "Files collected:"
    ls -lh "$DEBUG_DIR"/*_${TIMESTAMP}.txt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo
    echo "=== Quick Status Check ==="
    echo
    echo "GPU Status:"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=name,memory.free,temperature.gpu --format=csv,noheader | head -1
    else
        echo "  nvidia-smi not available"
    fi
    echo
    echo "GDS Module:"
    if lsmod | grep -q nvidia_fs; then
        echo "  [OK] nvidia_fs module is loaded"
    else
        echo "  [WARN] nvidia_fs module is NOT loaded"
    fi
    echo
    echo "Recent Errors (last 5):"
    dmesg | grep -i "error\|fail\|crash\|panic" | tail -5 || echo "  No recent errors found"
    echo
    echo "GPU Memory Usage:"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader | head -1
    fi
    echo
    echo "=== Recommendations ==="
    echo
    if ! lsmod | grep -q nvidia_fs; then
        echo "1. Load GDS module: sudo modprobe nvidia_fs"
    fi
    echo "2. Check dmesg_${TIMESTAMP}.txt for kernel errors"
    echo "3. Check crash_indicators_${TIMESTAMP}.txt for crash signatures"
    echo "4. Review gpu_info_${TIMESTAMP}.txt for GPU memory issues"
    echo "5. Check if system has enough GPU memory for test"
    echo
} | tee "$DEBUG_DIR/SUMMARY_${TIMESTAMP}.txt"

echo
echo "=================================="
print_status "ok" "Debug information collected"
echo "=================================="
echo
echo "Output directory: $DEBUG_DIR"
echo "Summary report: $DEBUG_DIR/SUMMARY_${TIMESTAMP}.txt"
echo
echo "Key files to check:"
echo "  1. $DEBUG_DIR/dmesg_${TIMESTAMP}.txt - Kernel messages"
echo "  2. $DEBUG_DIR/crash_indicators_${TIMESTAMP}.txt - Crash signatures"
echo "  3. $DEBUG_DIR/gpu_info_${TIMESTAMP}.txt - GPU status"
echo "  4. $DEBUG_DIR/kernel_modules_${TIMESTAMP}.txt - Module status"
echo
echo "To view recent kernel errors:"
echo "  tail -50 $DEBUG_DIR/dmesg_${TIMESTAMP}.txt | grep -i error"
echo
echo "To monitor in real-time during test:"
echo "  watch -n 1 'nvidia-smi; echo; dmesg | tail -20'"
echo

