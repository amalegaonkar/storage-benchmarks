#!/bin/bash
#
# NIXLBench Runner Script
# Handles ETCD setup and runs nixlbench for storage benchmarking
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
ETCD_IMAGE="quay.io/coreos/etcd:v3.5.1"
ETCD_CONTAINER="nixl-etcd"
ETCD_PORT="2379"

# Check if nixlbench is in PATH
if ! command -v nixlbench &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} nixlbench not found in PATH"
    echo "Please set PATH and LD_LIBRARY_PATH:"
    echo "  export PATH=\"\$(pwd)/install/nixlbench/bin:\$PATH\""
    echo "  export LD_LIBRARY_PATH=\"\$(pwd)/install/nixl/lib/aarch64-linux-gnu:\$LD_LIBRARY_PATH\""
    exit 1
fi

# Function to check if ETCD is running
check_etcd() {
    docker ps --filter "name=$ETCD_CONTAINER" --format "{{.ID}}" 2>/dev/null | grep -q .
}

# Function to start ETCD
start_etcd() {
    if check_etcd; then
        echo -e "${GREEN}[OK]${NC} ETCD container already running"
        return 0
    fi
    
    echo -e "${YELLOW}[INFO]${NC} Starting ETCD server..."
    
    # Check if container exists but is stopped
    if docker ps -a --filter "name=$ETCD_CONTAINER" --format "{{.ID}}" | grep -q .; then
        echo -e "${YELLOW}[INFO]${NC} Starting existing ETCD container..."
        docker start "$ETCD_CONTAINER"
    else
        echo -e "${YELLOW}[INFO]${NC} Creating new ETCD container..."
        docker run -d \
            -p "${ETCD_PORT}:2379" \
            --name "$ETCD_CONTAINER" \
            "$ETCD_IMAGE" \
            etcd \
            --advertise-client-urls=http://0.0.0.0:2379 \
            --listen-client-urls=http://0.0.0.0:2379
    fi
    
    # Wait for ETCD to be ready
    echo -e "${YELLOW}[INFO]${NC} Waiting for ETCD to be ready..."
    sleep 2
    
    if check_etcd; then
        echo -e "${GREEN}[OK]${NC} ETCD server started"
        return 0
    else
        echo -e "${RED}[ERROR]${NC} Failed to start ETCD"
        return 1
    fi
}

# Function to stop ETCD
stop_etcd() {
    if check_etcd; then
        echo -e "${YELLOW}[INFO]${NC} Stopping ETCD container..."
        docker stop "$ETCD_CONTAINER" 2>/dev/null || true
        echo -e "${GREEN}[OK]${NC} ETCD stopped"
    fi
}

# Parse arguments
AUTO_START_ETCD=true
STOP_ETCD=false
NIXLBENCH_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-etcd)
            AUTO_START_ETCD=false
            shift
            ;;
        --stop-etcd)
            STOP_ETCD=true
            shift
            ;;
        *)
            NIXLBENCH_ARGS+=("$1")
            shift
            ;;
    esac
done

# Handle stop request
if [ "$STOP_ETCD" = true ]; then
    stop_etcd
    exit 0
fi

# Start ETCD if needed
if [ "$AUTO_START_ETCD" = true ]; then
    if ! start_etcd; then
        echo -e "${RED}[ERROR]${NC} Cannot proceed without ETCD"
        echo "You can try running without ETCD: $0 --no-etcd [nixlbench args...]"
        exit 1
    fi
fi

# Run nixlbench with provided arguments
echo -e "${GREEN}[INFO]${NC} Running nixlbench..."

# For POSIX backend, ensure filepath is a directory
# nixlbench creates test files inside the specified directory
for i in "${!NIXLBENCH_ARGS[@]}"; do
    arg="${NIXLBENCH_ARGS[$i]}"
    if [[ "$arg" == --filepath=* ]]; then
        FILEPATH="${arg#--filepath=}"
        # If it's a file (exists as file or has extension and doesn't exist as dir), use parent directory
        if [ -f "$FILEPATH" ] || ([[ "$FILEPATH" == *.* ]] && [ ! -d "$FILEPATH" ]); then
            FILEPATH_DIR=$(dirname "$FILEPATH")
            echo -e "${YELLOW}[INFO]${NC} POSIX backend requires directory path, not file path"
            echo -e "${YELLOW}[INFO]${NC} Using directory: $FILEPATH_DIR (from provided path: $FILEPATH)"
            NIXLBENCH_ARGS[$i]="--filepath=$FILEPATH_DIR"
            FILEPATH="$FILEPATH_DIR"
        fi
        # Ensure directory exists
        if [ -n "$FILEPATH" ] && [ ! -d "$FILEPATH" ]; then
            echo -e "${YELLOW}[INFO]${NC} Creating directory: $FILEPATH"
            mkdir -p "$FILEPATH"
        fi
        break
    fi
done

echo "Command: nixlbench ${NIXLBENCH_ARGS[*]}"
echo

nixlbench "${NIXLBENCH_ARGS[@]}"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo
    echo -e "${GREEN}[OK]${NC} nixlbench completed successfully"
else
    echo
    echo -e "${RED}[ERROR]${NC} nixlbench failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE

