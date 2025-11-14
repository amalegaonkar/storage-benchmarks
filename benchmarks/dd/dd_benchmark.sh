#!/bin/bash
#
# Simple DD Benchmark Script
# Quick sequential read/write test using dd
#

set -e

# Configuration
BLOCK_SIZE="1M"
FILE_SIZES=(
    "100M:100"
    "1G:1024"
    "10G:10240"
)

STORAGE_LOCATIONS=(
    "Local_SSD:/tmp/local-ssd"
    "NFS_Mount:/tmp/remote-pure-nfs"
)

TEST_FILE="dd_test.bin"
ITERATIONS=3

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=================================="
echo "DD Sequential I/O Benchmark"
echo "Block size: $BLOCK_SIZE"
echo "Iterations: $ITERATIONS"
echo "=================================="
echo

# Print CSV header
echo "StorageType,Operation,FileSize,Iteration,Bandwidth_MBps,Time_s"

for storage_entry in "${STORAGE_LOCATIONS[@]}"; do
    IFS=':' read -r storage_name storage_path <<< "$storage_entry"

    echo
    echo -e "${GREEN}Testing: $storage_name${NC}" >&2

    # Create directory if needed
    mkdir -p "$storage_path" 2>/dev/null || true

    for size_entry in "${FILE_SIZES[@]}"; do
        IFS=':' read -r size_name count <<< "$size_entry"

        filepath="$storage_path/$TEST_FILE"

        echo -e "\n  File size: $size_name" >&2

        # Write test
        echo -n "    Write: " >&2

        write_speeds=()

        for iter in $(seq 1 $ITERATIONS); do
            # Clear cache
            sync
            echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true

            # Run dd write
            result=$(dd if=/dev/zero of="$filepath" bs=$BLOCK_SIZE count=$count oflag=direct 2>&1 || true)

            # Parse bandwidth
            bandwidth=$(echo "$result" | grep -oP '\d+(\.\d+)? MB/s' | grep -oP '\d+(\.\d+)?' | head -1 || echo "0")
            time_s=$(echo "$result" | grep -oP '\d+(\.\d+)? s,' | grep -oP '\d+(\.\d+)?' | head -1 || echo "0")

            if [ -n "$bandwidth" ] && [ "$bandwidth" != "0" ]; then
                write_speeds+=("$bandwidth")
                echo "$storage_name,write,$size_name,$iter,$bandwidth,$time_s"
                echo -n "$bandwidth " >&2
            fi
        done

        echo "MB/s" >&2

        # Read test
        echo -n "    Read:  " >&2

        read_speeds=()

        for iter in $(seq 1 $ITERATIONS); do
            # Clear cache
            sync
            echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true

            # Run dd read
            result=$(dd if="$filepath" of=/dev/null bs=$BLOCK_SIZE iflag=direct 2>&1 || true)

            # Parse bandwidth
            bandwidth=$(echo "$result" | grep -oP '\d+(\.\d+)? MB/s' | grep -oP '\d+(\.\d+)?' | head -1 || echo "0")
            time_s=$(echo "$result" | grep -oP '\d+(\.\d+)? s,' | grep -oP '\d+(\.\d+)?' | head -1 || echo "0")

            if [ -n "$bandwidth" ] && [ "$bandwidth" != "0" ]; then
                read_speeds+=("$bandwidth")
                echo "$storage_name,read,$size_name,$iter,$bandwidth,$time_s"
                echo -n "$bandwidth " >&2
            fi
        done

        echo "MB/s" >&2

        # Cleanup
        rm -f "$filepath"
    done
done

echo
echo "=================================="
echo "DD Benchmark Complete!"
echo "=================================="
