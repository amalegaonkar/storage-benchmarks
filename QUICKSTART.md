# Quick Start Guide

Get up and running with storage benchmarks in 4 steps!

## Step 1: Setup (30 seconds)

```bash
# Check dependencies and create directories
./utils/setup_environment.sh
```

## Step 2: Run Benchmarks (5-30 minutes depending on storage)

**Option A: Run everything (recommended)**
```bash
./run_all_benchmarks.sh
```

**Option B: Run FIO only (more detailed)**
```bash
./fio/fio_benchmark.py -o results/fio_results.csv
```

**Option C: Run DD only (quick test)**
```bash
./benchmarks/dd/dd_benchmark.sh > results/dd_results.csv
```

## Step 3: View Results

```bash
# Validate and analyze results
./utils/validate_results.py results/fio_results.csv

# View raw CSV
cat results/fio_results.csv

# Or open in Excel/LibreOffice
libreoffice results/fio_results.csv
```

## Step 4: Visualize (Optional)

```bash
# Install plotting dependencies (first time only)
pip install -r requirements.txt

# Generate plots
./plotting/plot_fio_results.py results/fio_results.csv

# View generated plots
ls -lh fio_*.png
```

**Generated plots:**
- `fio_total_time.png` - Complete file read times
- `fio_bandwidth.png` - Bandwidth comparison
- `fio_iops.png` - IOPS performance
- `fio_nfs_comparison.png` - NFS direct vs buffered

## Common Tasks

### Custom Test Parameters

```bash
# Test with different queue depths
./fio/fio_benchmark.py -d 1 8 32 128 -o results/custom.csv

# More iterations for accuracy
./fio/fio_benchmark.py -i 5 -o results/accurate.csv

# Smaller block size (4k IOPS test)
./fio/fio_benchmark.py -b 4k -o results/iops.csv
```

### Device Discovery

```bash
# Discover what device is backing a filesystem path
./utils/device_info.py /tmp/local-ssd

# Show expected performance for the device
./utils/performance_expectations.py /tmp/local-ssd

# Combine both: discover device and show expectations
./fio/fio_benchmark_with_validation.py --path /tmp/local-ssd --expect-only
```

### Cleanup

```bash
# Remove test files only
./utils/cleanup.sh

# Remove everything (test files + results)
./utils/cleanup.sh --all

# See what would be deleted (dry run)
./utils/cleanup.sh --all --dry-run
```

### Change Storage Locations

Edit `config.json`:
```json
{
  "storage_locations": {
    "My_SSD": "/mnt/ssd/",
    "My_NFS": "/mnt/nfs/"
  }
}
```

Then run benchmarks normally.

## Understanding Results

**CSV Columns:**
- `BW_MBps`: Bandwidth in MB/s (higher is better)
- `TotalTime_s`: Time to read complete file (lower is better)
- `IOPS`: I/O operations per second (higher is better)
- `LatMean_us`: Average latency in microseconds (lower is better)

**Quick Analysis:**
```bash
# Best bandwidth per storage type
cat results/fio_results.csv | grep -v ERROR | sort -t, -k7 -rn | head -5

# Worst performing tests
cat results/fio_results.csv | grep -v ERROR | sort -t, -k7 -n | head -5
```

## Troubleshooting

**"fio not installed"**
```bash
sudo apt-get install fio
```

**"Permission denied"**
```bash
sudo mkdir -p /tmp/local-ssd /tmp/remote-pure-nfs
sudo chown $USER:$USER /tmp/local-ssd /tmp/remote-pure-nfs
```

**"High variance" in validation**
- Normal for network storage
- Rerun with more iterations: `-i 5`
- Check for background processes

## Next Steps

1. Run benchmarks on all your storage systems
2. Compare results using the validation tool
3. Generate plots to visualize performance differences
4. Tune storage based on findings
5. Share plots in reports and presentations

For detailed documentation, see:
- [README.md](README.md) - Full documentation
- [plotting/README.md](plotting/README.md) - Plotting guide
