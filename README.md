# Storage Benchmarks

Comprehensive storage performance testing suite for comparing different storage backends (Local SSD, NFS, etc.)

## Features

- **FIO Benchmarks**: Advanced I/O testing with customizable parameters
- **DD Benchmarks**: Simple sequential read/write tests
- **Validation Tools**: Automated result validation and anomaly detection
- **Visualization**: Professional plotting of benchmark results
- **Easy Configuration**: JSON-based configuration for storage locations and test parameters
- **CSV Output**: Easy-to-analyze results format

## Quick Start

### 1. Setup Environment

```bash
# Run setup script to check dependencies and create directories
./utils/setup_environment.sh
```

### 2. Configure Storage Locations

Edit `config.json` to match your storage setup:

```json
{
  "storage_locations": {
    "Local_SSD": "/tmp/local-ssd/",
    "NFS_Mount": "/tmp/remote-pure-nfs/"
  }
}
```

### 3. Run Benchmarks

```bash
# Run FIO benchmark (recommended)
./fio/fio_benchmark.py -o results/fio_results.csv

# Or run DD benchmark for quick tests
./benchmarks/dd/dd_benchmark.sh > results/dd_results.csv
```

### 4. Analyze Results

```bash
# Validate results and check for anomalies
./utils/validate_results.py results/fio_results.csv

# View raw results
cat results/fio_results.csv
```

### 5. Visualize Results

```bash
# Install plotting dependencies (first time only)
pip install -r requirements.txt

# Generate plots
./plotting/plot_fio_results.py results/fio_results.csv

# View generated plots: fio_total_time.png, fio_bandwidth.png, fio_iops.png, fio_nfs_comparison.png
```

## Directory Structure

```
storage-benchmarks/
├── fio/                        # FIO benchmark scripts
│   └── fio_benchmark.py        # Main FIO benchmark
├── benchmarks/
│   ├── dd/                     # DD benchmarks
│   │   └── dd_benchmark.sh     # Simple DD sequential test
│   └── iozone/                 # IOZone benchmarks (future)
├── plotting/                   # Visualization tools
│   ├── plot_fio_results.py     # Plot FIO results
│   └── README.md               # Plotting documentation
├── utils/                      # Utility scripts
│   ├── setup_environment.sh    # Environment setup
│   ├── cleanup.sh              # Clean test files
│   └── validate_results.py     # Result validation
├── results/                    # Benchmark results (CSV)
├── logs/                       # Log files
├── config.json                 # Configuration file
└── requirements.txt            # Python dependencies
```

## FIO Benchmark

The FIO benchmark is the most comprehensive test, measuring complete file read performance.

### Usage

```bash
./fio/fio_benchmark.py [OPTIONS]
```

**Options:**
- `-o, --output FILE`: Output CSV file (default: stdout)
- `-i, --iterations N`: Number of read iterations (default: 3)
- `-d, --depths N1 N2 ...`: IO depths to test (default: 1 128)
- `-b, --block-size SIZE`: Block size (default: 1M)
- `--use-urandom`: Use /dev/urandom for test files (slower but realistic data)

**Examples:**

```bash
# Basic run with defaults
./fio/fio_benchmark.py -o results/baseline.csv

# Test with 5 iterations and multiple queue depths
./fio/fio_benchmark.py -i 5 -d 1 8 32 128 -o results/detailed.csv

# Quick test with smaller block size
./fio/fio_benchmark.py -b 512k -i 2 -o results/quick.csv
```

### Test Parameters

- **File Sizes**: 1MB, 10MB, 100MB, 1GB
- **Storage Types**: Configurable via `config.json`
- **I/O Modes**:
  - Direct I/O (bypasses page cache)
  - Buffered I/O (only for NFS)
- **Queue Depths**: 1 (sequential), 128 (parallel)
- **Block Size**: 1M (optimized for throughput)

### Output Metrics

The CSV output includes:

- `StorageType`: Storage location name
- `IOMode`: direct or buffered
- `FileSize`: Human-readable file size
- `Bytes`: Actual bytes in file
- `IODepth`: Queue depth tested
- `TotalTime_s`: Time to read complete file once (seconds)
- `BW_MBps`: Bandwidth (MB/s)
- `IOPS`: I/O operations per second
- `LatMean_us`: Mean latency (microseconds)
- `LatP99_us`: 99th percentile latency (microseconds)

## DD Benchmark

Simple sequential I/O test using the `dd` command.

### Usage

```bash
./benchmarks/dd/dd_benchmark.sh > results/dd_results.csv
```

**Features:**
- Sequential read/write tests
- Multiple file sizes (100M, 1G, 10G)
- 3 iterations per test
- Direct I/O mode
- Automatic cache clearing (requires sudo for best results)

## Utility Scripts

### Setup Environment

```bash
./utils/setup_environment.sh
```

Checks for required tools, creates directories, and validates the environment.

### Cleanup

```bash
# Clean only test files
./utils/cleanup.sh

# Clean test files and results
./utils/cleanup.sh --results

# Clean everything (test files, results, logs)
./utils/cleanup.sh --all

# Dry run (see what would be deleted)
./utils/cleanup.sh --all --dry-run
```

### Validate Results

```bash
# Full validation with anomaly detection
./utils/validate_results.py results/fio_results.csv

# Summary only
./utils/validate_results.py --summary-only results/fio_results.csv

# Verbose output
./utils/validate_results.py -v results/fio_results.csv
```

The validator checks for:
- Failed tests
- High variance in results
- Suspiciously low bandwidth
- Summary statistics by storage type and file size

## Plotting Results

Visualize benchmark results with professional-quality plots.

### Installation

First time only, install plotting dependencies:

```bash
pip install -r requirements.txt
```

Or with conda:

```bash
conda install pandas matplotlib numpy
```

### Generate Plots

```bash
# Basic usage
./plotting/plot_fio_results.py results/fio_results.csv

# Custom output prefix
./plotting/plot_fio_results.py results/fio_results.csv --output-prefix mytest_

# Save to specific directory
./plotting/plot_fio_results.py results/fio_results.csv --output-prefix results/plots_
```

### Generated Plots

Four plots are automatically generated:

1. **fio_total_time.png**: Total time to read complete files
   - Compares both storage types side-by-side
   - Shows impact of queue depth on read time
   - Logarithmic scales for clarity

2. **fio_bandwidth.png**: Bandwidth (MB/s) across file sizes
   - Identifies peak throughput capabilities
   - Shows how bandwidth scales with file size
   - Compares different I/O modes and queue depths

3. **fio_iops.png**: I/O operations per second
   - Important for small I/O workloads
   - Shows parallelism benefits
   - Queue depth impact visualization

4. **fio_nfs_comparison.png**: NFS direct vs buffered I/O
   - Bar chart comparing I/O modes
   - Side-by-side: Time, Bandwidth, IOPS
   - Only generated when NFS data with both modes exists

### Example Workflow

```bash
# Run benchmark and immediately plot
./fio/fio_benchmark.py -o results/test.csv && \
./plotting/plot_fio_results.py results/test.csv

# Batch process multiple results
for csv in results/*.csv; do
    ./plotting/plot_fio_results.py "$csv" --output-prefix "${csv%.csv}_"
done
```

For detailed plotting documentation, see [plotting/README.md](plotting/README.md).

## Configuration

Edit `config.json` to customize:

```json
{
  "storage_locations": {
    "Local_SSD": "/mnt/local-ssd/",
    "NFS_Mount": "/mnt/nfs/",
    "Custom_Storage": "/path/to/storage/"
  },
  "file_sizes": [
    {"name": "1MB", "bytes": 1048576, "filename": "test_1MB.bin"},
    {"name": "10MB", "bytes": 10485760, "filename": "test_10MB.bin"}
  ],
  "fio_settings": {
    "block_size": "1M",
    "io_depths": [1, 32, 128],
    "num_iterations": 3,
    "use_zero_device": true
  }
}
```

## Requirements

### Core Requirements

- **FIO**: Flexible I/O Tester
  ```bash
  sudo apt-get install fio  # Ubuntu/Debian
  sudo yum install fio      # RHEL/CentOS
  ```

- **Python 3**: For FIO benchmark and validation scripts

- **Standard Unix tools**: dd, bash, coreutils

### Plotting Requirements (Optional)

For visualization features:

```bash
pip install -r requirements.txt
```

This installs:
- pandas (≥1.3.0) - CSV data analysis
- matplotlib (≥3.4.0) - Plot generation
- numpy (≥1.21.0) - Numerical operations

## Tips & Best Practices

1. **Cache Effects**: For accurate results, ensure proper cache clearing between runs
2. **File Creation**: Use `/dev/zero` (default) for faster test file creation
3. **Queue Depths**:
   - QD=1 for sequential workloads
   - QD=32-128 for parallel/random workloads
4. **Block Size**:
   - 1M for throughput testing
   - 4k for IOPS testing
5. **Iterations**: Use at least 3 iterations to account for variance
6. **NFS Tuning**: Consider testing both direct and buffered I/O modes

## Improvements Made

This implementation improves upon the original script:

1. **Fixed Issues**:
   - Corrected comment about iterations (was "3 times", code said 2)
   - Better error handling and reporting
   - Proper timeout handling
   - Added P99 latency metrics

2. **Enhanced Features**:
   - Command-line argument parsing
   - Configurable parameters (iterations, queue depths, block size)
   - Optional /dev/urandom for realistic data
   - Timestamps in output
   - File size validation
   - Directory auto-creation
   - Better error messages with context

3. **Added Tools**:
   - Environment setup script
   - Cleanup utility
   - Result validation tool
   - DD benchmark for comparison
   - Configuration file support
   - Professional plotting scripts with matplotlib

4. **Better Usability**:
   - Separated stdout (data) and stderr (logs)
   - CSV output to file or stdout
   - Progress indicators
   - Summary statistics
   - Dry-run mode for cleanup

## Troubleshooting

### Permission Errors

If you get permission errors accessing `/tmp/local-ssd/` or `/tmp/remote-pure-nfs/`:

```bash
sudo mkdir -p /tmp/local-ssd /tmp/remote-pure-nfs
sudo chown $USER:$USER /tmp/local-ssd /tmp/remote-pure-nfs
```

### FIO Not Found

Install FIO:
```bash
sudo apt-get update && sudo apt-get install fio
```

### Low Performance on NFS

1. Check NFS mount options: `mount | grep nfs`
2. Verify network connectivity: `ping <nfs-server>`
3. Check NFS server load: `nfsstat -c`

## Next Steps

After running benchmarks:

1. **Visualize Results**: Generate plots to see performance comparisons
2. **Analyze Results**: Use the validation tool to check for anomalies
3. **Compare Storage**: Look at bandwidth differences between storage types
4. **Tune Parameters**: Adjust block sizes, queue depths based on workload
5. **Share Findings**: Use generated plots in reports and presentations

## Contributing

Improvements welcome! Areas for enhancement:
- IOZone integration
- Random I/O patterns
- Write benchmarks
- Mixed read/write workloads
- Latency histograms

## License

MIT License - Feel free to use and modify
