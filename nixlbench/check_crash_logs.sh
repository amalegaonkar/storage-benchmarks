#!/bin/bash
#
# Check Crash Logs (requires sudo)
# Run this script to check kernel logs for crash signatures
#

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="${LOG_DIR:-./crash_logs}"

mkdir -p "$LOG_DIR"

echo "=================================="
echo "Crash Log Analysis"
echo "=================================="
echo

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges to read kernel logs"
    echo "Please run: sudo $0"
    exit 1
fi

echo "[1] Checking recent kernel messages (dmesg)..."
{
    echo "=== Last 200 kernel messages ==="
    dmesg | tail -200
    echo
} | tee "$LOG_DIR/dmesg_recent_${TIMESTAMP}.txt"

echo
echo "[2] Checking for crash signatures..."
{
    echo "=== Kernel Errors ==="
    dmesg | grep -i "error\|fail" | tail -50
    echo
    
    echo "=== Kernel Panics ==="
    dmesg | grep -i "panic" | tail -20
    echo
    
    echo "=== Kernel Oops ==="
    dmesg | grep -i "oops\|bug" | tail -20
    echo
    
    echo "=== Segmentation Faults ==="
    dmesg | grep -i "segfault\|segmentation" | tail -20
    echo
    
    echo "=== Out of Memory ==="
    dmesg | grep -i "out of memory\|oom" | tail -20
    echo
    
    echo "=== GDS/NVIDIA Related ==="
    dmesg | grep -i "gds\|nvfs\|nvidia" | tail -50
    echo
    
    echo "=== nixlbench Related ==="
    dmesg | grep -i "nixlbench" | tail -20
    echo
} | tee "$LOG_DIR/crash_signatures_${TIMESTAMP}.txt"

echo
echo "[3] Checking system logs around crash time..."
# Check logs from 21:38 to 21:42 (when test was running)
{
    echo "=== Kernel Logs (21:38-21:42) ==="
    journalctl -k --since "2025-12-01 21:38:00" --until "2025-12-01 21:42:00" 2>/dev/null || echo "journalctl not available"
    echo
} | tee "$LOG_DIR/kernel_logs_crash_window_${TIMESTAMP}.txt"

echo
echo "[4] Checking /var/log/kern.log..."
if [ -f /var/log/kern.log ]; then
    {
        echo "=== Recent kern.log (last 200 lines) ==="
        tail -200 /var/log/kern.log
        echo
        
        echo "=== kern.log Errors ==="
        grep -i "error\|fail\|crash\|panic\|oops\|bug" /var/log/kern.log | tail -50
        echo
        
        echo "=== kern.log GDS/NVIDIA ==="
        grep -i "gds\|nvfs\|nvidia" /var/log/kern.log | tail -50
        echo
    } | tee "$LOG_DIR/kern_log_${TIMESTAMP}.txt"
else
    echo "kern.log not found"
fi

echo
echo "[5] Checking boot logs..."
{
    echo "=== Last Boot ==="
    journalctl -b -1 --no-pager 2>/dev/null | tail -100 || echo "Previous boot log not available"
    echo
} | tee "$LOG_DIR/boot_log_${TIMESTAMP}.txt"

echo
echo "=================================="
echo "Analysis Complete"
echo "=================================="
echo
echo "Logs saved to: $LOG_DIR"
echo
echo "Key findings:"
echo "  - Check: $LOG_DIR/crash_signatures_${TIMESTAMP}.txt"
echo "  - Check: $LOG_DIR/kern_log_${TIMESTAMP}.txt"
echo "  - Check: $LOG_DIR/boot_log_${TIMESTAMP}.txt"
echo

