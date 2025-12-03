#!/bin/bash
#
# NIXLBench Storage Benchmark Suite
# Codifies standard nixlbench test configurations
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/../results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Default parameters
DEFAULT_FILEPATH="/tmp/nvme_raid0/"
DEFAULT_BACKEND="POSIX"
DEFAULT_API_TYPE="URING"
DEFAULT_STORAGE_ENABLE_DIRECT=true
DEFAULT_MAX_BATCH_SIZE=256
DEFAULT_START_BATCH_SIZE=256
DEFAULT_NUM_ITER=2048
DEFAULT_TOTAL_BUFFER_SIZE=34359738368  # 32 GiB
DEFAULT_MAX_BLOCK_SIZE=16777216         # 16 MiB
DEFAULT_START_BLOCK_SIZE=1048576        # 1 MiB
DEFAULT_OP_TYPE="READ"
DEFAULT_NUM_FILES=16
DEFAULT_NUM_THREADS=16
DEFAULT_INITIATOR_SEG_TYPE="DRAM"

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

# Function to check prerequisites
check_prerequisites() {
    local check_gds=${1:-false}
    
    print_status "info" "Checking prerequisites..."
    
    # Check if nixlbench is in PATH
    if ! command -v nixlbench &> /dev/null; then
        print_status "error" "nixlbench not found in PATH"
        echo "Please set PATH and LD_LIBRARY_PATH:"
        echo "  export PATH=\"\$(pwd)/install/nixlbench/bin:\$PATH\""
        echo "  export LD_LIBRARY_PATH=\"\$(pwd)/install/nixl/lib/aarch64-linux-gnu:\$LD_LIBRARY_PATH\""
        return 1
    fi
    
    # Check if storage directory exists
    if [ ! -d "$DEFAULT_FILEPATH" ]; then
        print_status "warn" "Storage directory $DEFAULT_FILEPATH does not exist"
        read -p "Create directory? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mkdir -p "$DEFAULT_FILEPATH"
            print_status "ok" "Created directory $DEFAULT_FILEPATH"
        else
            print_status "error" "Cannot proceed without storage directory"
            return 1
        fi
    fi
    
    # Check GDS kernel module if running GDS tests
    if [ "$check_gds" = true ]; then
        # Check if module is loaded (nvidia_fs is the actual module name)
        if lsmod | grep -q "^nvidia_fs\|^gds\|^nvidia_gds"; then
            print_status "ok" "GDS kernel module (nvidia_fs) is loaded"
        else
            # Check if module exists (even if not loaded)
            if modinfo nvidia_fs &>/dev/null || modinfo gds &>/dev/null || modinfo nvidia_gds &>/dev/null; then
                print_status "warn" "GDS kernel module exists but not loaded"
                echo "  Attempting to load: sudo modprobe nvidia_fs"
                if sudo modprobe nvidia_fs 2>&1; then
                    print_status "ok" "GDS kernel module (nvidia_fs) loaded successfully"
                else
                    print_status "error" "Failed to load GDS kernel module"
                    echo "  Try manually: sudo modprobe nvidia_fs"
                    echo "  Or: sudo modprobe gds"
                    echo "  Then retry the test"
                    return 1
                fi
            else
                print_status "error" "GDS kernel module not available on this system"
                echo ""
                echo "GDS (GPU Direct Storage) requires:"
                echo "  - NVIDIA driver with GDS support (580.x+)"
                echo "  - GDS kernel module (nvidia_fs, gds, or nvidia_gds)"
                echo "  - Compatible storage hardware"
                echo ""
                echo "To install GDS:"
                echo "  sudo apt-get install nvidia-gds"
                echo "  sudo modprobe nvidia_fs"
                return 1
            fi
        fi
    fi
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    
    print_status "ok" "Prerequisites check passed"
    return 0
}

# Function to run a single nixlbench test
run_nixlbench_test() {
    local test_name=$1
    local backend=$2
    local filepath=$3
    local api_type=${4:-""}
    local op_type=$5
    local num_files=$6
    local num_threads=$7
    local total_buffer_size=$8
    local initiator_seg_type=${9:-"DRAM"}
    local output_file="${RESULTS_DIR}/nixlbench_${test_name}_${TIMESTAMP}.out"
    
    print_status "info" "Running test: $test_name"
    print_status "info" "  Backend: $backend"
    print_status "info" "  Filepath: $filepath"
    print_status "info" "  Operation: $op_type"
    print_status "info" "  Files: $num_files, Threads: $num_threads"
    print_status "info" "  Buffer Size: $((total_buffer_size / 1024 / 1024 / 1024)) GiB"
    
    # Build command
    local cmd=(
        "nixlbench"
        "--backend=$backend"
        "--filepath=$filepath"
        "--storage_enable_direct"
        "--max_batch_size=$DEFAULT_MAX_BATCH_SIZE"
        "--start_batch_size=$DEFAULT_START_BATCH_SIZE"
        "--num_iter=$DEFAULT_NUM_ITER"
        "--total_buffer_size=$total_buffer_size"
        "--max_block_size=$DEFAULT_MAX_BLOCK_SIZE"
        "--start_block_size=$DEFAULT_START_BLOCK_SIZE"
        "--op_type=$op_type"
        "--num_files=$num_files"
        "--num_threads=$num_threads"
        "--initiator_seg_type=$initiator_seg_type"
    )
    
    # Add API type for POSIX backend
    if [ "$backend" = "POSIX" ] && [ -n "$api_type" ]; then
        cmd+=("--posix_api_type=$api_type")
    fi
    
    # Run command and save output with timeout
    print_status "info" "Command: ${cmd[*]}"
    print_status "info" "Output: $output_file"
    
    # Set timeout based on test type (GDS tests may take longer)
    local timeout_seconds=600  # 10 minutes default
    if [ "$backend" = "GDS" ] || [ "$backend" = "GDS_MT" ]; then
        timeout_seconds=1800  # 30 minutes for GDS tests
    fi
    
    print_status "info" "Timeout: ${timeout_seconds}s"
    
    # Run with timeout
    if timeout "$timeout_seconds" "${cmd[@]}" 2>&1 | tee "$output_file"; then
        # Check if output file contains results (not just hanging)
        if grep -q "B/W (GB/Sec)" "$output_file" 2>/dev/null; then
            print_status "ok" "Test $test_name completed"
            echo "  Results saved to: $output_file"
            return 0
        else
            print_status "warn" "Test $test_name completed but no results found in output"
            echo "  Check output file: $output_file"
            return 1
        fi
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            print_status "error" "Test $test_name timed out after ${timeout_seconds}s"
            echo "  This may indicate the test is hung or taking too long"
            echo "  Check output file: $output_file"
        else
            print_status "error" "Test $test_name failed with exit code $exit_code"
            echo "  Check output file: $output_file"
        fi
        return 1
    fi
}

# Function to run GDS backend tests
run_gds_tests() {
    local filepath=${1:-$DEFAULT_FILEPATH}
    
    echo
    echo "=================================="
    echo "GDS Backend Tests"
    echo "=================================="
    echo
    
    # Check prerequisites including GDS module
    if ! check_prerequisites true; then
        print_status "error" "Cannot run GDS tests - prerequisites not met"
        return 1
    fi
    
    print_status "warn" "GDS tests use VRAM and may take longer or require GPU resources"
    print_status "info" "GDS module check:"
    
    # Check if nvidia_fs module is loaded
    if lsmod | grep -q "^nvidia_fs"; then
        print_status "ok" "GDS kernel module (nvidia_fs) is loaded"
    else
        print_status "warn" "GDS kernel module (nvidia_fs) is not loaded"
        echo "  Attempting to load GDS module..."
        if sudo modprobe nvidia_fs 2>/dev/null; then
            print_status "ok" "GDS kernel module loaded successfully"
        else
            print_status "error" "Failed to load GDS module automatically"
            echo "  Please load manually: sudo modprobe nvidia_fs"
            echo "  Then retry the test"
            return 1
        fi
    fi
    
    print_status "info" "If tests hang, check:"
    echo "  1. GPU/CUDA availability (nvidia-smi)"
    echo "  2. GPU memory availability"
    echo "  3. GDS driver/kernel module loaded (lsmod | grep nvidia_fs)"
    echo "  4. Test files may need pre-allocation"
    echo
    
    # Check GPU memory availability before running GDS tests
    print_status "info" "Checking GPU memory availability..."
    if command -v nvidia-smi &> /dev/null; then
        local gpu_mem_info=$(nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader,nounits 2>/dev/null | head -n1)
        if [ -n "$gpu_mem_info" ]; then
            local total_mem=$(echo "$gpu_mem_info" | cut -d',' -f1 | tr -d ' ')
            local free_mem=$(echo "$gpu_mem_info" | cut -d',' -f2 | tr -d ' ')
            print_status "info" "GPU Memory: ${free_mem}MB free / ${total_mem}MB total"
            
            # Warn if less than 70GB free (64GB test needs ~66GB)
            if [ "$free_mem" -lt 70000 ]; then
                print_status "warn" "Low GPU memory (${free_mem}MB free)"
                echo "  Large GDS tests may cause system instability"
                echo "  Consider running smaller tests first"
            fi
        fi
    fi
    echo
    
    # GDS Test 1: Start with smaller, safer test - 32 GiB, 1 file, 1 thread
    # This uses less VRAM and is less likely to crash
    print_status "info" "Starting with conservative test (1 thread) to verify stability"
    run_nixlbench_test \
        "gds_32g_1f_1t" \
        "GDS" \
        "$filepath" \
        "" \
        "READ" \
        1 \
        1 \
        34359738368 \
        "VRAM"
    
    # GDS Test 2: 32 GiB buffer, 8 files, 8 threads
    # 32 GiB / 8 threads = 4 GiB per thread (sufficient)
    # More conservative than 16 threads
    run_nixlbench_test \
        "gds_32g_8f_8t" \
        "GDS" \
        "$filepath" \
        "" \
        "READ" \
        8 \
        8 \
        34359738368 \
        "VRAM"
    
    # GDS Test 3: 64 GiB buffer, 16 files, 16 threads (most intensive)
    # Note: 32 GiB doesn't work with 16 threads because:
    # max_block_size * max_batch_size = 16 MiB * 256 = 4 GiB per thread
    # 32 GiB / 16 threads = 2 GiB per thread (insufficient)
    # 64 GiB / 16 threads = 4 GiB per thread (sufficient)
    # WARNING: This is the most resource-intensive test - may cause system instability/crashes
    print_status "warn" "Skipping intensive 16-thread test to prevent system crashes"
    print_status "info" "To run intensive test manually (at your own risk):"
    echo "  nixlbench --backend=GDS --filepath=$filepath --storage_enable_direct"
    echo "    --max_batch_size=256 --start_batch_size=256 --num_iter=2048"
    echo "    --total_buffer_size=68719476736 --max_block_size=16777216"
    echo "    --start_block_size=1048576 --op_type=READ"
    echo "    --num_files=16 --num_threads=16 --initiator_seg_type=VRAM"
    echo
    print_status "info" "If you need 16-thread test, consider:"
    echo "  1. Running on a dedicated test system"
    echo "  2. Reducing buffer size or threads"
    echo "  3. Monitoring system resources closely"
    echo
}

# Function to run safe GDS backend tests (skips intensive 16-thread test)
run_gds_tests_safe() {
    local filepath=${1:-$DEFAULT_FILEPATH}
    
    echo
    echo "=================================="
    echo "GDS Backend Tests (Safe Mode)"
    echo "=================================="
    echo
    
    # Check prerequisites including GDS module
    if ! check_prerequisites true; then
        print_status "error" "Cannot run GDS tests - prerequisites not met"
        return 1
    fi
    
    print_status "info" "Running safe GDS tests only (1-8 threads, no 16-thread test)"
    print_status "info" "GDS module check:"
    
    # Check if nvidia_fs module is loaded
    if lsmod | grep -q "^nvidia_fs"; then
        print_status "ok" "GDS kernel module (nvidia_fs) is loaded"
    else
        print_status "warn" "GDS kernel module (nvidia_fs) is not loaded"
        echo "  Attempting to load GDS module..."
        if sudo modprobe nvidia_fs 2>/dev/null; then
            print_status "ok" "GDS kernel module loaded successfully"
        else
            print_status "error" "Failed to load GDS module automatically"
            echo "  Please load manually: sudo modprobe nvidia_fs"
            echo "  Then retry the test"
            return 1
        fi
    fi
    
    # Check GPU memory availability
    print_status "info" "Checking GPU memory availability..."
    if command -v nvidia-smi &> /dev/null; then
        local gpu_mem_info=$(nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader,nounits 2>/dev/null | head -n1)
        if [ -n "$gpu_mem_info" ]; then
            local total_mem=$(echo "$gpu_mem_info" | cut -d',' -f1 | tr -d ' ')
            local free_mem=$(echo "$gpu_mem_info" | cut -d',' -f2 | tr -d ' ')
            print_status "info" "GPU Memory: ${free_mem}MB free / ${total_mem}MB total"
        fi
    fi
    echo
    
    # GDS Test 1: 32 GiB, 1 file, 1 thread (safest)
    run_nixlbench_test \
        "gds_32g_1f_1t" \
        "GDS" \
        "$filepath" \
        "" \
        "READ" \
        1 \
        1 \
        34359738368 \
        "VRAM"
    
    # GDS Test 2: 32 GiB buffer, 8 files, 8 threads
    # 32 GiB / 8 threads = 4 GiB per thread (sufficient)
    run_nixlbench_test \
        "gds_32g_8f_8t" \
        "GDS" \
        "$filepath" \
        "" \
        "READ" \
        8 \
        8 \
        34359738368 \
        "VRAM"
}

# Function to run POSIX backend tests
run_posix_tests() {
    local filepath=${1:-$DEFAULT_FILEPATH}
    local api_type=${2:-"URING"}
    
    echo
    echo "=================================="
    echo "POSIX Backend Tests (API: $api_type)"
    echo "=================================="
    echo
    
    # POSIX Test 1: Single file, single thread
    run_nixlbench_test \
        "posix_${api_type}_32g_1f_1t" \
        "POSIX" \
        "$filepath" \
        "$api_type" \
        "READ" \
        1 \
        1 \
        34359738368 \
        "DRAM"
    
    # POSIX Test 2: 16 files, 16 threads, 64 GiB, READ
    # Note: 32 GiB doesn't work with 16 threads because:
    # max_block_size * max_batch_size = 16 MiB * 256 = 4 GiB per thread
    # 32 GiB / 16 threads = 2 GiB per thread (insufficient)
    # 64 GiB / 16 threads = 4 GiB per thread (sufficient)
    run_nixlbench_test \
        "posix_${api_type}_64g_16f_16t_read" \
        "POSIX" \
        "$filepath" \
        "$api_type" \
        "READ" \
        16 \
        16 \
        68719476736 \
        "DRAM"
    
    # POSIX Test 3: 16 files, 16 threads, 64 GiB, WRITE
    run_nixlbench_test \
        "posix_${api_type}_64g_16f_16t_write" \
        "POSIX" \
        "$filepath" \
        "$api_type" \
        "WRITE" \
        16 \
        16 \
        68719476736 \
        "DRAM"
}

# Function to run all tests
run_all_tests() {
    local filepath=${1:-$DEFAULT_FILEPATH}
    
    echo "=================================="
    echo "NIXLBench Storage Benchmark Suite"
    echo "Started: $(date)"
    echo "=================================="
    echo
    
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Run GDS tests (skip if GDS module not available)
    if check_prerequisites true 2>/dev/null; then
        run_gds_tests "$filepath"
    else
        print_status "warn" "Skipping GDS tests - GDS module not available"
        echo "  Run POSIX tests instead: ./nixlbench/nixlbench_suite.sh posix"
        echo
    fi
    
    # Run POSIX tests with URING API
    run_posix_tests "$filepath" "URING"
    
    echo
    echo "=================================="
    echo "All Tests Complete"
    echo "Finished: $(date)"
    echo "=================================="
    echo
    echo "Results saved to: $RESULTS_DIR"
    echo
}

# Function to run custom test
run_custom_test() {
    local backend=$1
    local filepath=$2
    local api_type=$3
    local op_type=$4
    local num_files=$5
    local num_threads=$6
    local total_buffer_size=$7
    local initiator_seg_type=${8:-"DRAM"}
    
    local test_name="custom_${backend}_${op_type}_${num_files}f_${num_threads}t"
    
    if ! check_prerequisites; then
        exit 1
    fi
    
    run_nixlbench_test \
        "$test_name" \
        "$backend" \
        "$filepath" \
        "$api_type" \
        "$op_type" \
        "$num_files" \
        "$num_threads" \
        "$total_buffer_size" \
        "$initiator_seg_type"
}

# Main script
main() {
    case "${1:-all}" in
        "all")
            run_all_tests "${2:-$DEFAULT_FILEPATH}"
            ;;
        "gds")
            if ! check_prerequisites true; then exit 1; fi
            run_gds_tests "${2:-$DEFAULT_FILEPATH}"
            ;;
        "gds-safe")
            if ! check_prerequisites true; then exit 1; fi
            run_gds_tests_safe "${2:-$DEFAULT_FILEPATH}"
            ;;
        "debug")
            # Run debug collection
            if [ -f "$(dirname "$0")/debug_gds_crash.sh" ]; then
                "$(dirname "$0")/debug_gds_crash.sh"
            else
                echo "Debug script not found"
                exit 1
            fi
            ;;
        "posix")
            if ! check_prerequisites; then exit 1; fi
            run_posix_tests "${2:-$DEFAULT_FILEPATH}" "${3:-URING}"
            ;;
        "custom")
            shift
            if [ $# -lt 7 ]; then
                echo "Usage: $0 custom <backend> <filepath> <api_type> <op_type> <num_files> <num_threads> <total_buffer_size> [initiator_seg_type]"
                echo "Example: $0 custom POSIX /tmp/nvme_raid0/ URING READ 16 16 34359738368 DRAM"
                exit 1
            fi
            run_custom_test "$@"
            ;;
        "help"|"-h"|"--help")
            echo "NIXLBench Storage Benchmark Suite"
            echo
            echo "Usage: $0 [command] [options]"
            echo
            echo "Commands:"
            echo "  all [filepath]              Run all tests (default)"
            echo "  gds [filepath]              Run GDS backend tests (skips intensive 16-thread test)"
            echo "  gds-safe [filepath]         Run only safe GDS tests (1-8 threads)"
            echo "  posix [filepath] [api_type] Run POSIX backend tests"
            echo "  debug                       Collect system diagnostics for crash debugging"
            echo "  custom <args...>            Run custom test"
            echo "  help                        Show this help"
            echo
            echo "Examples:"
            echo "  $0 all /tmp/nvme_raid0/"
            echo "  $0 gds /tmp/nvme_raid0/"
            echo "  $0 posix /tmp/nvme_raid0/ URING"
            echo "  $0 custom POSIX /tmp/nvme_raid0/ URING READ 16 16 34359738368 DRAM"
            echo
            echo "Default filepath: $DEFAULT_FILEPATH"
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"

