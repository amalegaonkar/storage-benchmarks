# FIO Results Plotting

Visualization tools for FIO benchmark results.

## Installation

Install required dependencies:

```bash
pip install -r ../requirements.txt
```

Or if using conda:

```bash
conda install pandas matplotlib numpy
```

## Usage

### Basic Plotting

```bash
./plot_fio_results.py ../results/fio_results.csv
```

This generates 4 plots in the current directory:
- `fio_total_time.png` - Total time to read complete files
- `fio_bandwidth.png` - Bandwidth across file sizes
- `fio_iops.png` - IOPS performance
- `fio_nfs_comparison.png` - NFS direct vs buffered comparison

### Custom Output Prefix

```bash
./plot_fio_results.py ../results/fio_results.csv --output-prefix results_
```

Generates:
- `results_fio_total_time.png`
- `results_fio_bandwidth.png`
- `results_fio_iops.png`
- `results_fio_nfs_comparison.png`

### Save to Specific Directory

```bash
./plot_fio_results.py ../results/fio_results.csv --output-prefix ../results/plots_
```

## Generated Plots

### 1. Total Time Comparison (`fio_total_time.png`)

**Purpose**: Shows how long it takes to read the entire file

**Features**:
- Side-by-side comparison of both storage types
- Logarithmic scales for better visualization
- Separate lines for each IO mode and queue depth
- Y-axis formatted in actual seconds (not scientific notation)

**Use Case**: Compare raw read performance between storage systems

### 2. Bandwidth Comparison (`fio_bandwidth.png`)

**Purpose**: Shows throughput in MB/s across different file sizes

**Features**:
- Identifies which storage performs best at each file size
- Shows how bandwidth scales with file size
- Compares different queue depths

**Use Case**: Understand peak throughput capabilities

### 3. IOPS Comparison (`fio_iops.png`)

**Purpose**: Shows I/O operations per second

**Features**:
- Useful for understanding small I/O performance
- Shows how IOPS changes with file size
- Queue depth impact on IOPS

**Use Case**: Evaluate parallel I/O capabilities

### 4. NFS Direct vs Buffered (`fio_nfs_comparison.png`)

**Purpose**: Bar chart comparing NFS I/O modes

**Features**:
- Three side-by-side comparisons: Time, Bandwidth, IOPS
- Direct I/O vs Buffered (cached) performance
- Uses highest queue depth for comparison
- Only generated if NFS data with both modes exists

**Use Case**: Understand caching impact on NFS performance

## Interpreting Results

### What to Look For

**Total Time**:
- Lower is better
- Should decrease with higher queue depths
- NFS buffered should be faster than direct for cached reads

**Bandwidth**:
- Higher is better
- Should increase with file size (up to storage limit)
- Queue depth impact varies by storage type

**IOPS**:
- Higher is better
- More important for small I/O workloads
- Shows parallelism benefits

**NFS Comparison**:
- Buffered mode uses page cache (faster for re-reads)
- Direct mode bypasses cache (true storage performance)
- Large differences indicate caching benefits

### Common Patterns

1. **Bandwidth increases with file size**: Normal - larger transfers amortize overhead
2. **Higher QD improves NFS performance**: Expected - network benefits from parallelism
3. **Local SSD faster than NFS**: Expected - no network overhead
4. **Buffered NFS much faster**: Cache is working (not representative of storage)
5. **Variance at small file sizes**: Normal - setup overhead dominates

## Examples

### Full Workflow

```bash
# Run benchmark
cd ..
./fio/fio_benchmark.py -o results/today.csv

# Validate results
./utils/validate_results.py results/today.csv

# Generate plots
cd plotting
./plot_fio_results.py ../results/today.csv --output-prefix ../results/today_

# View plots
ls -lh ../results/today_*.png
```

### Batch Processing

```bash
# Plot all CSV files in results directory
for csv in ../results/*.csv; do
    basename="${csv%.csv}"
    ./plot_fio_results.py "$csv" --output-prefix "${basename}_"
done
```

## Customization

The script can be easily modified for:
- Different color schemes (edit color codes in bar charts)
- Additional metrics (add new plotting functions)
- Different layouts (change subplot arrangements)
- Export formats (change `plt.savefig()` format parameter)

Example modifications:

```python
# Change DPI for higher resolution
plt.savefig(filename, dpi=600, bbox_inches='tight')

# Export as PDF instead
plt.savefig(filename.replace('.png', '.pdf'), format='pdf')

# Change color scheme
color='#FF5733'  # Custom hex color
```

## Troubleshooting

### Import Errors

```
ModuleNotFoundError: No module named 'pandas'
```

**Solution**: Install dependencies
```bash
pip install pandas matplotlib numpy
```

### Empty Plots

If plots are generated but empty or missing data:

1. Check CSV file has data: `cat ../results/fio_results.csv`
2. Verify no ERROR rows: `grep ERROR ../results/fio_results.csv`
3. Check column names match expected format
4. Run validation: `../utils/validate_results.py ../results/fio_results.csv`

### Font Warnings

```
Matplotlib font warnings...
```

**Solution**: Usually harmless, but can be fixed:
```bash
# Clear matplotlib cache
rm -rf ~/.cache/matplotlib
```

### Missing NFS Comparison Plot

**Reason**: Only generated when:
- CSV contains NFS storage type
- Both 'direct' and 'buffered' IO modes exist

**Solution**: Run FIO benchmark on NFS mount, which automatically tests both modes

## Tips

1. **Run validation first**: `validate_results.py` catches data issues before plotting
2. **Use descriptive prefixes**: Helps organize multiple plot sets
3. **High-quality exports**: Use `dpi=300` or higher for presentations
4. **Batch plotting**: Process multiple results at once with shell loops
5. **Keep raw CSV files**: Plots can always be regenerated

## Script Details

**Input**: CSV file with columns:
- StorageType, IOMode, FileSize, Bytes, IODepth
- TotalTime_s, BW_MBps, IOPS, LatMean_us

**Output**: PNG files with matplotlib plots

**Dependencies**:
- pandas: CSV parsing and data manipulation
- matplotlib: Plot generation
- numpy: Array operations

**Error Handling**:
- Skips rows with 'ERROR' values
- Handles missing NFS data gracefully
- Validates file existence
- Reports parsing errors with traceback
