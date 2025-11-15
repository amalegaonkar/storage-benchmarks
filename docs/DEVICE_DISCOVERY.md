## Device Discovery and Performance Expectations

Automatically discover storage devices and generate performance hypotheses based on device characteristics.

## Features

- **Auto-Discovery**: Finds underlying storage devices from filesystem paths
- **Device Information**: Gathers detailed specs for NVMe, SATA, and network storage
- **Performance Profiling**: Identifies device capabilities (Gen3/Gen4, enterprise/consumer, etc.)
- **Hypothesis Generation**: Predicts expected performance based on device specs
- **Result Validation**: Compares actual results against expectations

## Quick Start

### 1. Discover Device Information

```bash
# Basic device discovery
./utils/device_info.py /tmp/local-ssd

# Verbose output
./utils/device_info.py /mnt/nfs --verbose

# JSON output
./utils/device_info.py /dev/nvme0n1 --json
```

### 2. Generate Performance Expectations

```bash
# Show expected performance
./utils/performance_expectations.py /tmp/local-ssd

# For random I/O workload
./utils/performance_expectations.py /tmp/local-ssd --io-pattern random

# JSON output
./utils/performance_expectations.py /tmp/local-ssd --json
```

### 3. Integrated Benchmark with Validation

```bash
# Discover device and show expectations
./fio/fio_benchmark_with_validation.py --path /tmp/local-ssd --discover-only

# Show only expectations
./fio/fio_benchmark_with_validation.py --path /tmp/local-ssd --expect-only

# Full benchmark with validation (coming soon)
./fio/fio_benchmark_with_validation.py --path /tmp/local-ssd
```

## Device Discovery

### How It Works

1. **Find Mount Point**: Walks up directory tree to find where path is mounted
2. **Identify Device**: Reads `/proc/mounts` to find underlying device
3. **Resolve Symlinks**: Follows `/dev/disk/by-uuid/` to actual device
4. **Determine Type**: Identifies NVMe, SATA, NFS, etc.
5. **Gather Details**: Calls appropriate tools (nvme-cli, hdparm, smartctl)

### Supported Device Types

#### NVMe Devices

Gathered information:
- Model, serial number, firmware version
- Capacity and namespace info
- Temperature and wear level
- Power state
- Data units written

Requirements:
- `nvme-cli` package
- sudo access

Example:
```bash
sudo apt-get install nvme-cli
./utils/device_info.py /dev/nvme0n1
```

#### SATA/SAS Devices

Gathered information:
- Model, serial, firmware
- Media type (SSD vs HDD)
- Rotation rate (for HDDs)
- Temperature
- SMART health status

Requirements:
- `hdparm` and `smartmontools` packages
- sudo access

Example:
```bash
sudo apt-get install hdparm smartmontools
./utils/device_info.py /dev/sda
```

#### Network Storage

Gathered information:
- NFS server and export path
- Mount options
- Server reachability
- Protocol (NFS, CIFS, etc.)
- Network filesystem stats

Example:
```bash
./utils/device_info.py /mnt/nfs
```

### Example Output

```
======================================================================
Device Information
======================================================================

Path:         /tmp/local-ssd
Mount Point:  /tmp
Device:       /dev/nvme0n1
Device Type:  nvme

Model:        Samsung SSD 980 PRO 1TB
Serial:       S5GXNX0R123456
Firmware:     5B2QGXA7
Capacity:     1,000,204,886,016 bytes
Temperature:  35°C
Wear Level:   1%

Filesystem:
  Total Size:   931.51 GB
  Free Space:   850.23 GB
  Used:         8.7%
  Block Size:   4096 bytes

======================================================================
```

## Performance Expectations

### Device Profiles

The system includes pre-defined performance profiles for common device types:

#### NVMe Profiles

- **Consumer Gen3** (e.g., Samsung 970 EVO, WD SN750)
  - Sequential Read: 3000 MB/s (range: 2000-3500)
  - Random Read: 400K IOPS (range: 200K-500K)
  - Latency: 100 μs (range: 50-150)

- **Consumer Gen4** (e.g., Samsung 980 PRO, WD SN850)
  - Sequential Read: 7000 MB/s (range: 5000-7400)
  - Random Read: 800K IOPS (range: 500K-1M)
  - Latency: 60 μs (range: 30-100)

- **Enterprise Gen3** (e.g., Intel P3700, Samsung PM983)
  - Sequential Read: 3200 MB/s (range: 2000-3500)
  - Random Read: 700K IOPS (range: 400K-800K)
  - Latency: 50 μs (range: 20-80)

- **Enterprise Gen4** (e.g., Intel Optane, Samsung PM1733)
  - Sequential Read: 7000 MB/s (range: 6000-7500)
  - Random Read: 1.2M IOPS (range: 800K-1.5M)
  - Latency: 30 μs (range: 10-60)

#### SATA SSD Profiles

- **SATA SSD** (e.g., Samsung 870 EVO, Crucial MX500)
  - Sequential Read: 500 MB/s (range: 400-550)
  - Random Read: 90K IOPS (range: 60K-100K)
  - Latency: 200 μs (range: 100-300)

#### HDD Profiles

- **7200 RPM HDD**
  - Sequential Read: 150 MB/s (range: 100-200)
  - Random Read: 120 IOPS (range: 80-150)
  - Latency: 12 ms (range: 8-15 ms)

- **10000 RPM HDD**
  - Sequential Read: 200 MB/s (range: 150-250)
  - Random Read: 160 IOPS (range: 120-200)
  - Latency: 7 ms (range: 5-10 ms)

#### Network Storage Profiles

- **NFS over 1GbE**
  - Sequential Read: 110 MB/s (range: 80-120)
  - Random Read: 3K IOPS (range: 1K-5K)
  - Latency: 500 μs (range: 200-1000)

- **NFS over 10GbE**
  - Sequential Read: 1100 MB/s (range: 800-1200)
  - Random Read: 30K IOPS (range: 10K-50K)
  - Latency: 300 μs (range: 100-500)

- **NFS over 25GbE**
  - Sequential Read: 2800 MB/s (range: 2000-3000)
  - Random Read: 100K IOPS (range: 50K-150K)
  - Latency: 150 μs (range: 50-300)

### Profile Detection

The system automatically identifies the correct profile by analyzing:

1. **Device Type**: NVMe, SCSI, Network
2. **Model Name**: Matches known model patterns
3. **Media Type**: SSD vs HDD (from SMART data)
4. **Interface**: PCIe generation, network speed
5. **Rotation Rate**: 7200 vs 10000 RPM

### Hypothesis Generation

```bash
./utils/performance_expectations.py /tmp/local-ssd
```

Output:
```
======================================================================
Performance Expectations
======================================================================

Device:       /dev/nvme0n1
Type:         nvme
Model:        Samsung SSD 980 PRO 1TB
Profile:      consumer_gen4
Interface:    PCIe Gen4 x4

Expected Performance (sequential):
----------------------------------------------------------------------
  Sequential Read Bandwidth:
    Typical:  7000 MB/s
    Range:    5000 - 7400 MB/s
    Confidence: high

  Average Latency:
    Typical:  60 μs
    Range:    30 - 100 μs
    Confidence: high

======================================================================
```

### Result Validation

Compare benchmark results against expectations:

```bash
# Run benchmark and save results
./fio/fio_benchmark.py -o results/test.csv

# Validate against expectations
./utils/performance_expectations.py /tmp/local-ssd --validate results/test.json
```

Validation output:
```
======================================================================
Performance Validation Report
======================================================================

Device:       /dev/nvme0n1
Profile:      consumer_gen4
I/O Pattern:  sequential
Overall:      EXCELLENT

Metric                         Expected                  Actual               Status
----------------------------------------------------------------------
Sequential Read Bandwidth      7000 MB/s (5000-7400)    6850 MB/s            ✓ excellent
Average Latency                60 μs (30-100)           58 μs                ✓ excellent

======================================================================
```

### Validation Statuses

- **EXCELLENT**: Within 10% of typical value
- **GOOD**: Within 25% of typical value
- **ACCEPTABLE**: Within expected range but >25% deviation
- **FAIL**: Outside expected range
- **NO_EXPECTATIONS**: Could not determine device profile

## Use Cases

### 1. Verify New Hardware

When deploying new storage, verify it performs as expected:

```bash
# Discover device specs
./utils/device_info.py /new/storage --verbose

# Show expected performance
./utils/performance_expectations.py /new/storage

# Run benchmark and validate
./fio/fio_benchmark.py -o results/new_storage.csv
# Then compare against expectations
```

### 2. Troubleshoot Performance Issues

If storage seems slow:

```bash
# Check device health
./utils/device_info.py /slow/storage

# See what performance should be
./utils/performance_expectations.py /slow/storage

# Run benchmark to confirm
./fio/fio_benchmark.py -o results/slow_storage.csv
```

### 3. Compare Storage Options

Evaluate different storage backends:

```bash
for path in /tmp/local-ssd /mnt/nfs /mnt/ceph; do
    echo "=== $path ==="
    ./utils/device_info.py $path
    ./utils/performance_expectations.py $path
done
```

### 4. Document Infrastructure

Generate device inventory:

```bash
for path in /data1 /data2 /data3; do
    ./utils/device_info.py $path --json >> inventory.json
done
```

## Advanced Usage

### Custom Performance Profiles

Edit `utils/performance_expectations.py` to add custom profiles:

```python
CUSTOM_PROFILES = {
    "my_custom_nvme": {
        "seq_read_mbps": (8000, 10000, 9000),
        "seq_write_mbps": (7000, 9000, 8000),
        "rand_read_iops": (1000000, 1500000, 1200000),
        "rand_write_iops": (900000, 1400000, 1100000),
        "latency_us": (10, 50, 25),
        "interface": "PCIe Gen5 x4"
    }
}
```

### Programmatic Usage

```python
from device_info import get_device_info
from performance_expectations import generate_expectations, validate_results

# Get device info
info = get_device_info("/tmp/local-ssd")

# Generate expectations
expectations = generate_expectations(info, "sequential")

# Run benchmark (your code here)
results = {"BW_MBps": 6850, "IOPS": 800000, "LatMean_us": 58}

# Validate
report = validate_results(info, results, "sequential")

if report["overall_status"] in ["EXCELLENT", "GOOD"]:
    print("Storage performing as expected!")
else:
    print(f"Performance issue detected: {report['overall_status']}")
```

## Requirements

### Core Requirements

- Python 3.6+
- Standard Linux utilities (mount, /proc/mounts)

### Optional Requirements

For full functionality:

```bash
# NVMe devices
sudo apt-get install nvme-cli

# SATA/SAS devices
sudo apt-get install hdparm smartmontools

# Network storage
sudo apt-get install nfs-common cifs-utils

# All of the above
sudo apt-get install nvme-cli hdparm smartmontools nfs-common
```

### Sudo Access

Some operations require sudo:
- Reading NVMe/SATA device info
- Accessing SMART data
- Clearing filesystem caches

Configure sudo to allow specific commands without password (optional):

```bash
# Add to /etc/sudoers.d/storage-benchmarks
youruser ALL=(ALL) NOPASSWD: /usr/sbin/nvme
youruser ALL=(ALL) NOPASSWD: /usr/sbin/hdparm
youruser ALL=(ALL) NOPASSWD: /usr/sbin/smartctl
```

## Troubleshooting

### "nvme: command not found"

Install nvme-cli:
```bash
sudo apt-get install nvme-cli
```

### "Permission denied" errors

Either:
1. Run with sudo: `sudo ./utils/device_info.py /dev/nvme0n1`
2. Configure passwordless sudo (see Requirements above)

### "Could not determine device profile"

The device may not match known patterns. Either:
1. Add a custom profile (see Advanced Usage)
2. Manually specify expected performance
3. Use the benchmark without validation

### Network device not detected

Check if mounted:
```bash
mount | grep nfs
df -h | grep <path>
```

### Temperature/SMART data missing

Ensure smartmontools is installed:
```bash
sudo apt-get install smartmontools
sudo smartctl -a /dev/sda
```

## Limitations

1. **Profile Detection**: Based on heuristics and known models. May not recognize all devices.
2. **Network Performance**: Highly variable based on network conditions, server load, etc.
3. **Sudo Requirements**: Many operations require elevated privileges
4. **Linux Only**: Currently supports Linux systems only
5. **Pre-defined Profiles**: Limited to common device types

## Future Enhancements

- [ ] Machine learning-based profile detection
- [ ] Real-time performance monitoring
- [ ] Historical performance tracking
- [ ] Automatic tuning recommendations
- [ ] Support for more device types (iSCSI, Ceph, etc.)
- [ ] Windows and macOS support
- [ ] Web-based dashboard
- [ ] Alert generation for performance degradation

## Contributing

To add support for new device types or improve detection:

1. Update `device_info.py` with new detection logic
2. Add performance profiles to `performance_expectations.py`
3. Test with actual hardware
4. Submit pull request with documentation

## Examples

See `examples/device_discovery/` for complete examples and scripts.
