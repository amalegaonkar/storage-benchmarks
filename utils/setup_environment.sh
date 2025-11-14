#!/bin/bash
#
# Setup Script for Storage Benchmarks
# Creates necessary directories and validates the environment
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "Storage Benchmark Setup"
echo "=================================="
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    local status=$1
    local message=$2

    if [ "$status" = "ok" ]; then
        echo -e "${GREEN}[OK]${NC} $message"
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}[WARN]${NC} $message"
    elif [ "$status" = "error" ]; then
        echo -e "${RED}[ERROR]${NC} $message"
    else
        echo "[ ] $message"
    fi
}

# Check for required tools
echo "Checking required tools..."
echo

REQUIRED_TOOLS=("fio" "python3" "dd")
OPTIONAL_TOOLS=("iozone" "iostat" "vmstat")

ALL_REQUIRED_PRESENT=true

for tool in "${REQUIRED_TOOLS[@]}"; do
    if command_exists "$tool"; then
        version=$(${tool} --version 2>&1 | head -n1 || echo "unknown")
        print_status "ok" "$tool installed: $version"
    else
        print_status "error" "$tool NOT installed"
        ALL_REQUIRED_PRESENT=false
    fi
done

echo

for tool in "${OPTIONAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        print_status "ok" "$tool installed (optional)"
    else
        print_status "warn" "$tool not installed (optional, recommended)"
    fi
done

echo

if [ "$ALL_REQUIRED_PRESENT" = false ]; then
    echo -e "${RED}Missing required tools. Please install them:${NC}"
    echo "  Ubuntu/Debian: sudo apt-get install fio python3 coreutils"
    echo "  RHEL/CentOS:   sudo yum install fio python3"
    exit 1
fi

# Create benchmark directories
echo "Creating benchmark directories..."
echo

STORAGE_DIRS=(
    "/tmp/local-ssd"
    "/tmp/remote-pure-nfs"
)

for dir in "${STORAGE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        print_status "ok" "$dir already exists"
    else
        if mkdir -p "$dir" 2>/dev/null; then
            print_status "ok" "Created $dir"
        else
            print_status "warn" "Cannot create $dir (may need sudo)"
        fi
    fi
done

echo

# Create results and logs directories
RESULT_DIRS=(
    "results"
    "logs"
)

for dir in "${RESULT_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_status "ok" "Created $dir/"
    else
        print_status "ok" "$dir/ exists"
    fi
done

echo

# Check Python modules
echo "Checking Python environment..."
echo

PYTHON_MODULES=("json" "subprocess" "argparse")

for module in "${PYTHON_MODULES[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        print_status "ok" "Python module '$module' available"
    else
        print_status "error" "Python module '$module' missing"
    fi
done

echo

# Make scripts executable
echo "Setting executable permissions..."
echo

if [ -f "fio/fio_benchmark.py" ]; then
    chmod +x fio/fio_benchmark.py
    print_status "ok" "fio/fio_benchmark.py is executable"
fi

if [ -f "utils/cleanup.sh" ]; then
    chmod +x utils/cleanup.sh
    print_status "ok" "utils/cleanup.sh is executable"
fi

echo

# Disk space check
echo "Checking available disk space..."
echo

check_disk_space() {
    local path=$1
    local required_gb=$2

    if [ -d "$path" ]; then
        available_kb=$(df "$path" | tail -1 | awk '{print $4}')
        available_gb=$((available_kb / 1024 / 1024))

        if [ $available_gb -ge $required_gb ]; then
            print_status "ok" "$path has ${available_gb}GB available (need ${required_gb}GB)"
        else
            print_status "warn" "$path has only ${available_gb}GB available (need ${required_gb}GB)"
        fi
    else
        print_status "warn" "$path does not exist"
    fi
}

for dir in "${STORAGE_DIRS[@]}"; do
    check_disk_space "$dir" 2
done

echo
echo "=================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================="
echo
echo "Next steps:"
echo "  1. Verify storage paths in config.json"
echo "  2. Run benchmark: ./fio/fio_benchmark.py"
echo "  3. View results: cat results/*.csv"
echo
