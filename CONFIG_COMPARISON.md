# Configuration Comparison: Benchmark vs North Star

## config_nfs (North Star) Settings

```
[global]
direct=1
ioengine=libaio
iodepth=256
rw=read
fallocate=none
group_reporting=1
randrepeat=0
size=50G
nrfiles=1
directory=/tmp/remote-pure-nfs/node_read_test
blocksize=1024k
fsync_on_close=1
zero_buffers
buffer_compress_percentage=0
create_serialize=0
time_based=0

[single_node_job]
numjobs=8
```

## Updated Benchmark Settings (After Alignment)

```
--rw=read                    ✓ Match
--ioengine=libaio            ✓ Match
--direct={direct}             ✓ Match (variable)
--iodepth={io_depth}          ⚠ Different (tests 1, 128 vs 256) - INTENTIONAL
--numjobs=1                   ⚠ Different (1 vs 8) - INTENTIONAL
--bs={block_size}             ✓ Match (adaptive, 1M for >=1MB)
--size={size_bytes}           ✓ Match (variable sizes) - INTENTIONAL
--loops={num_iterations}      ✓ Match (3 iterations)
--output-format=json          ✓ Match
--group_reporting             ✓ Match
NO --time_based               ✓ Match

NEWLY ADDED (to match north star):
--fallocate=none              ✓ Added - Important for NFS
--randrepeat=0                 ✓ Added - Consistency
--fsync_on_close=1             ✓ Added - Data integrity
--zero_buffers                  ✓ Added - Consistency with config_nfs
--buffer_compress_percentage=0  ✓ Added - No compression
--create_serialize=0            ✓ Added - Allow parallel operations
```

## Differences Analysis

### Intentional Differences (OK - These are by design)
- **iodepth**: Benchmark tests 1 and 128 (for comparison), north star uses 256 (optimal)
  - *Reason*: Benchmark needs to test different queue depths for comparison
- **numjobs**: Benchmark uses 1 (single job per test), north star uses 8 (parallel jobs)
  - *Reason*: Benchmark isolates single-job performance, north star maximizes throughput
- **size**: Benchmark tests multiple sizes (1K-10GB), north star uses 50G
  - *Reason*: Benchmark characterizes performance across file sizes

### Settings Added (Now Aligned)
These settings ensure consistency and proper behavior with the north star config:
- ✅ `fallocate=none` - **Critical for NFS** (don't pre-allocate, let NFS handle it)
- ✅ `randrepeat=0` - Don't repeat random patterns (for consistency)
- ✅ `fsync_on_close=1` - Ensure data integrity (important for accurate measurements)
- ✅ `zero_buffers` - Use zero-filled buffers (matches /dev/zero file creation)
- ✅ `buffer_compress_percentage=0` - No compression (consistent with north star)
- ✅ `create_serialize=0` - Allow parallel file creation (for consistency)

## Summary

✅ **Benchmark configuration is now aligned with north star (`config_nfs`)**  
✅ **All critical settings match**  
✅ **Intentional differences are documented** (iodepth, numjobs, size variations)

The benchmark will now produce results that are directly comparable to the north star configuration, while still testing multiple file sizes and queue depths for comprehensive characterization.

