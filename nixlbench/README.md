# NIXLBench Storage Benchmark Suite

This directory contains scripts for running NIXLBench storage performance tests.

## Prerequisites

1. **Build NIXL and nixlbench** (if not already done):
   ```bash
   ./utils/build_nixl.sh
   ```

2. **Set environment variables**:
   ```bash
   export PATH="$(pwd)/install/nixlbench/bin:$PATH"
   export LD_LIBRARY_PATH="$(pwd)/install/nixl/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH"
   ```

3. **Start ETCD** (required for nixlbench):
   ```bash
   ./nixlbench/run_nixlbench.sh --stop-etcd  # Stop if running
   docker run -d -p 2379:2379 --name nixl-etcd quay.io/coreos/etcd:v3.5.1
   ```

4. **GDS Module** (only required for GDS backend tests):
   ```bash
   # Check if GDS module (nvidia_fs) is available
   sudo lsmod | grep nvidia_fs
   sudo modinfo nvidia_fs
   
   # If available but not loaded, load it:
   sudo modprobe nvidia_fs
   ```
   
   **Note**: The GDS kernel module is named `nvidia_fs` (not `gds` or `nvidia_gds`).
   If GDS module is not available, GDS tests will be skipped automatically.
   Use POSIX backend tests instead, which don't require GDS.

## Scripts

### 1. `nixlbench_suite.sh` - Comprehensive Benchmark Suite

Main script that codifies standard nixlbench test configurations.

**Usage:**
```bash
# Run all tests (GDS + POSIX)
./nixlbench/nixlbench_suite.sh all [filepath]

# Run only GDS backend tests
./nixlbench/nixlbench_suite.sh gds [filepath]

# Run only POSIX backend tests
./nixlbench/nixlbench_suite.sh posix [filepath] [api_type]

# Run safe GDS tests only (skips intensive 16-thread test)
./nixlbench/nixlbench_suite.sh gds-safe [filepath]

# Collect system diagnostics for crash debugging
./nixlbench/nixlbench_suite.sh debug

# Run custom test
./nixlbench/nixlbench_suite.sh custom <backend> <filepath> <api_type> <op_type> <num_files> <num_threads> <total_buffer_size> [initiator_seg_type]
```

**Examples:**
```bash
# Run all tests with default path
./nixlbench/nixlbench_suite.sh all

# Run all tests with custom path
./nixlbench/nixlbench_suite.sh all /tmp/local-ssd/

# Run GDS tests only
./nixlbench/nixlbench_suite.sh gds /tmp/nvme_raid0/

# Run POSIX tests with URING API
./nixlbench/nixlbench_suite.sh posix /tmp/nvme_raid0/ URING

# Run custom test
./nixlbench/nixlbench_suite.sh custom POSIX /tmp/nvme_raid0/ URING READ 16 16 34359738368 DRAM
```

**Test Configurations:**

The suite includes the following standard tests:

#### GDS Backend Tests:
- **gds_32g_1f_1t**: 32 GiB buffer, 1 file, 1 thread, VRAM (safest)
- **gds_32g_8f_8t**: 32 GiB buffer, 8 files, 8 threads, VRAM
- **gds_64g_16f_16t**: 64 GiB buffer, 16 files, 16 threads, VRAM (skipped by default - may cause crashes)

**Note**: The intensive 16-thread test is skipped by default to prevent system crashes.
Use `gds-safe` command to run only safe tests (1-8 threads).

#### POSIX Backend Tests (URING API):
- **posix_uring_32g_1f_1t**: Single file, single thread
- **posix_uring_32g_16f_16t_read**: 16 files, 16 threads, 32 GiB, READ
- **posix_uring_64g_16f_16t_read**: 16 files, 16 threads, 64 GiB, READ
- **posix_uring_64g_16f_16t_write**: 16 files, 16 threads, 64 GiB, WRITE

**Output:**
- Results are saved to `results/nixlbench_<test_name>_<timestamp>.out`
- Each test output includes full nixlbench output with performance metrics

### 2. `run_nixlbench.sh` - Simple Wrapper

Helper script that automatically starts ETCD and runs nixlbench commands.

**Usage:**
```bash
# Run nixlbench with automatic ETCD management
./nixlbench/run_nixlbench.sh [nixlbench arguments...]

# Stop ETCD
./nixlbench/run_nixlbench.sh --stop-etcd

# Run without ETCD (if supported)
./nixlbench/run_nixlbench.sh --no-etcd [nixlbench arguments...]
```

**Examples:**
```bash
# Simple POSIX test
./nixlbench/run_nixlbench.sh --backend POSIX --filepath /tmp/nvme_raid0/ --op_type READ

# GDS test with VRAM
./nixlbench/run_nixlbench.sh --backend GDS --filepath /tmp/nvme_raid0/ --initiator_seg_type VRAM --op_type READ
```

### 3. `nixlbench_storage.py` - Python Benchmark Script

Python script for running nixlbench tests (alternative to shell script).

**Usage:**
```bash
./nixlbench/nixlbench_storage.py [options]
```

## Standard Test Parameters

Based on engineering usage patterns:

- **Batch Size**: 256 (max and start)
- **Iterations**: 2048
- **Block Sizes**: 1 MiB (start) to 16 MiB (max)
- **Buffer Sizes**: 32 GiB or 64 GiB
- **Files/Threads**: 1, 8, or 16
- **Direct I/O**: Enabled (`--storage_enable_direct`)
- **POSIX API**: URING (for POSIX backend)
- **GDS**: VRAM initiator segment type

## Test File Paths

**Important**: For POSIX and GDS backends, provide a **directory path**, not a file path. nixlbench will create test files inside the specified directory.

Example:
```bash
# Correct - directory path
--filepath /tmp/nvme_raid0/

# Incorrect - file path (will fail)
--filepath /tmp/nvme_raid0/test.bin
```

## Results Analysis

Results are saved to `results/` directory with timestamps. Each output file contains:
- Performance metrics (bandwidth, IOPS, latency)
- Test configuration parameters
- Full nixlbench output

To analyze results:
```bash
# View results
ls -lh results/nixlbench_*.out

# Compare different test runs
diff results/nixlbench_posix_uring_32g_16f_16t_read_*.out
```

## Troubleshooting

### GDS Tests Hang or Fail
**Symptom**: GDS tests hang or show "GDS kernel module not available"

**Cause**: GDS (GPU Direct Storage) requires the `nvidia_fs` kernel module that may not be available on all systems.

**Solution**:
```bash
# Check if GDS module (nvidia_fs) exists
sudo modinfo nvidia_fs
sudo lsmod | grep nvidia_fs

# If module exists but not loaded, load it:
sudo modprobe nvidia_fs

# If module doesn't exist, GDS is not available on this system
# Use POSIX backend instead:
./nixlbench/nixlbench_suite.sh posix /tmp/nvme_raid0/ URING
```

**Note**: GDS module (`nvidia_fs`) availability depends on:
- NVIDIA driver version (580.x+ typically includes GDS)
- Kernel support for GDS
- Storage hardware compatibility

If GDS is not available, POSIX backend provides similar functionality without GDS requirements.

### ETCD Not Running
```bash
# Check if ETCD is running
docker ps | grep etcd

# Start ETCD
docker run -d -p 2379:2379 --name nixl-etcd quay.io/coreos/etcd:v3.5.1
```

### Library Not Found
```bash
# Ensure LD_LIBRARY_PATH is set
export LD_LIBRARY_PATH="$(pwd)/install/nixl/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH"
```

### Filepath Error
- Ensure you're using a directory path, not a file path
- Directory must exist (script will create it if needed)

### Test Timeout
- GDS tests have a 30-minute timeout
- POSIX tests have a 10-minute timeout
- If tests timeout, check system resources and storage performance

### System Crashes During GDS Tests
**Symptom**: System crashes, hangs, or becomes unresponsive during GDS tests

**Debugging**:
```bash
# Collect comprehensive diagnostics
./nixlbench/debug_gds_crash.sh

# Or use suite command
./nixlbench/nixlbench_suite.sh debug

# Monitor system during test (in separate terminal)
./nixlbench/monitor_gds_test.sh
```

**Common causes**:
- GPU memory exhaustion
- Kernel oops/panic
- Out of memory (OOM)
- GDS module issues

**Solutions**:
- Use safe mode: `./nixlbench/nixlbench_suite.sh gds-safe`
- Reduce buffer sizes and thread counts
- Check kernel logs: `dmesg | tail -100`
- Monitor GPU memory: `nvidia-smi -l 1`
- See `DEBUGGING.md` for detailed debugging guide

## Debugging Tools

### `debug_gds_crash.sh` - Crash Diagnostics
Collects comprehensive system diagnostics to help debug GDS test crashes.

**Usage:**
```bash
./nixlbench/debug_gds_crash.sh
```

Collects:
- System information (kernel, OS, uptime)
- GPU status and memory usage
- Kernel messages (dmesg)
- System logs (journalctl)
- Kernel module status
- Memory and CPU information
- Crash indicators (oops, panic, segfault)

Output saved to `debug_output/` directory with timestamps.

### `monitor_gds_test.sh` - Real-time Monitoring
Monitors system resources during GDS test execution.

**Usage:**
```bash
# Run in separate terminal while test is running
./nixlbench/monitor_gds_test.sh
```

Monitors:
- GPU memory usage
- GPU processes
- System memory
- Recent kernel errors
- nixlbench processes
- CPU load

See `DEBUGGING.md` for detailed debugging guide and troubleshooting steps.

## Integration with Main Benchmark Suite

To integrate nixlbench into the main benchmark suite (`run_all_benchmarks.sh`), add:

```bash
# Run nixlbench suite
if [ -f "./nixlbench/nixlbench_suite.sh" ]; then
    echo "Running NIXLBench tests..."
    ./nixlbench/nixlbench_suite.sh all
fi
```

