#!/bin/bash
#
# Load GDS Module Script
# Loads the nvidia_fs kernel module for GDS functionality
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=================================="
echo "GDS Module Loader"
echo "=================================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[WARN]${NC} This script requires sudo privileges"
    echo "Please run: sudo $0"
    echo
    echo "Or manually run: sudo modprobe nvidia_fs"
    exit 1
fi

# Check if module exists
echo "[1] Checking if nvidia_fs module exists..."
if modinfo nvidia_fs &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} nvidia_fs module found"
    modinfo nvidia_fs | grep -E "filename|description|version" | head -3
    echo
else
    echo -e "${RED}[ERROR]${NC} nvidia_fs module not found"
    echo "GDS may not be available on this system"
    exit 1
fi

# Check if already loaded
echo "[2] Checking if module is already loaded..."
if lsmod | grep -q "^nvidia_fs"; then
    echo -e "${GREEN}[OK]${NC} nvidia_fs module is already loaded"
    lsmod | grep nvidia_fs
    echo
    exit 0
else
    echo -e "${YELLOW}[INFO]${NC} Module is not loaded"
    echo
fi

# Load the module
echo "[3] Loading nvidia_fs module..."
if modprobe nvidia_fs; then
    echo -e "${GREEN}[OK]${NC} Module loaded successfully"
    echo
    
    # Verify it's loaded
    echo "[4] Verifying module is loaded..."
    if lsmod | grep -q "^nvidia_fs"; then
        echo -e "${GREEN}[OK]${NC} Module verification successful"
        echo
        echo "Module status:"
        lsmod | grep nvidia_fs
        echo
        echo -e "${GREEN}GDS module is ready for use!${NC}"
        echo
        echo "You can now run GDS tests:"
        echo "  ./nixlbench/nixlbench_suite.sh gds-safe /tmp/nvme_raid0/"
        echo
    else
        echo -e "${RED}[ERROR]${NC} Module loaded but not visible in lsmod"
        exit 1
    fi
else
    echo -e "${RED}[ERROR]${NC} Failed to load module"
    echo
    echo "Check dmesg for errors:"
    echo "  dmesg | tail -20"
    exit 1
fi

