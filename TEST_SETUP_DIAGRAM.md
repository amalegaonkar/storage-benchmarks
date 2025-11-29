# Storage Benchmark Test Setup Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Benchmark Test System                             │
│                    (nbutme-gh200-1)                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                             │
        ▼                                             ▼
┌───────────────┐                           ┌───────────────┐
│  Local SSD    │                           │   NFS Mount   │
│               │                           │               │
│ /tmp/local-ssd│                           │/tmp/remote-   │
│               │                           │ pure-nfs      │
│               │                           │               │
│  NVMe SSD     │                           │  Pure Storage │
│  (Direct)     │                           │  NFS Server   │
│               │                           │               │
│  Storage:     │                           │  Storage:     │
│  ~664GB       │                           │  ~1022GB      │
└───────────────┘                           └───────────────┘
        │                                             │
        │                                             │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  FIO Benchmark  │
                    │     Script      │
                    │ fio_benchmark.py│
                    └─────────────────┘
```

## Test Execution Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Benchmark Execution Flow                     │
└─────────────────────────────────────────────────────────────────────┘

1. SETUP PHASE
   ┌─────────────────────────────────────────┐
   │  run_all_benchmarks.sh                  │
   │  ├─ Check environment                  │
   │  ├─ Validate tools (fio, python3, dd) │
   │  ├─ Create test directories            │
   │  └─ Check disk space                   │
   └─────────────────────────────────────────┘
                    │
                    ▼
2. FILE CREATION
   ┌─────────────────────────────────────────┐
   │  For each file size:                    │
   │  ├─ 1K, 4K, 10K, 100K                  │
   │  ├─ 1MB, 10MB, 100MB                   │
   │  └─ 1GB, 10GB                          │
   │                                         │
   │  create_test_file()                     │
   │  ├─ Check if file exists               │
   │  ├─ Create with dd                     │
   │  │  ├─ Small files: bs=file_size       │
   │  │  └─ Large files: bs=1MB            │
   │  └─ Source: /dev/zero (fast)          │
   └─────────────────────────────────────────┘
                    │
                    ▼
3. BENCHMARK EXECUTION
   ┌─────────────────────────────────────────┐
   │  For each Storage Type:                 │
   │  ├─ Local_SSD                          │
   │  └─ NFS_Mount                          │
   │                                         │
   │  For each File Size:                    │
   │  ├─ Determine block size               │
   │  │  ├─ < 1MB: block_size = file_size  │
   │  │  └─ >= 1MB: block_size = 1MB       │
   │  │                                         │
   │  For each IO Mode:                      │
   │  ├─ Local_SSD: direct only            │
   │  └─ NFS_Mount: direct + buffered      │
   │                                         │
   │  For each Queue Depth:                  │
   │  ├─ QD=1 (sequential)                 │
   │  └─ QD=128 (high concurrency)          │
   │                                         │
   │  run_fio_test()                         │
   │  ├─ Execute FIO command                │
   │  ├─ Read file 3 times (--loops=3)     │
   │  ├─ Collect metrics                    │
   │  └─ Calculate averages                 │
   └─────────────────────────────────────────┘
                    │
                    ▼
4. RESULTS COLLECTION
   ┌─────────────────────────────────────────┐
   │  CSV Output:                           │
   │  StorageType,IOMode,FileSize,Bytes,    │
   │  IODepth,TotalTime_s,BW_MBps,IOPS,     │
   │  LatMean_us,LatP99_us                  │
   │                                         │
   │  Saved to:                             │
   │  results/fio_YYYYMMDD_HHMMSS.csv       │
   └─────────────────────────────────────────┘
                    │
                    ▼
5. VALIDATION
   ┌─────────────────────────────────────────┐
   │  validate_results.py                   │
   │  ├─ Check for errors                   │
   │  ├─ Detect anomalies                  │
   │  ├─ Calculate statistics               │
   │  └─ Generate summary                   │
   └─────────────────────────────────────────┘
```

## Test Matrix

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Test Matrix                                  │
└─────────────────────────────────────────────────────────────────────┘

Storage Types:    2 (Local_SSD, NFS_Mount)
File Sizes:       9 (1K, 4K, 10K, 100K, 1MB, 10MB, 100MB, 1GB, 10GB)
IO Modes:         Local_SSD: 1 (direct)
                  NFS_Mount: 2 (direct, buffered)
Queue Depths:     2 (1, 128)
Iterations:       3 (read file 3 times, average results)

Total Tests:      54
  = 2 storage × 9 files × (1+2 modes avg) × 2 QD
  = 2 × 9 × 1.5 × 2 = 54 tests
```

## FIO Command Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FIO Command Breakdown                             │
└─────────────────────────────────────────────────────────────────────┘

fio
├── --name=<test_name>              # Unique test identifier
├── --rw=read                       # Read operation only
├── --filename=<filepath>           # Test file path
├── --size=<file_size_bytes>        # File size in bytes
├── --bs=<block_size>               # Block size (adaptive)
│   ├── < 1MB: file size            # e.g., "1K", "4K", "100K"
│   └── >= 1MB: "1M"                # Fixed 1MB for larger files
├── --direct=<0|1>                  # 1=direct I/O, 0=buffered
├── --ioengine=libaio               # Linux async I/O engine
├── --numjobs=1                     # Single job per test
├── --iodepth=<1|128>                # Queue depth
├── --loops=3                        # Read file 3 times
├── --output-format=json             # JSON output for parsing
└── --group_reporting                # Aggregate reporting

NO --time_based                      # Reads complete file (not time-based)
```

## Storage Configuration Details

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Storage Configuration                             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ LOCAL SSD                                                           │
├─────────────────────────────────────────────────────────────────────┤
│ Path:        /tmp/local-ssd/                                       │
│ Type:        NVMe SSD (Direct block device)                        │
│ Available:   ~664GB                                                 │
│ IO Modes:    Direct I/O only (O_DIRECT)                            │
│              └─ Bypasses OS page cache                             │
│                                                                     │
│ Test Files:  test_1K.bin through test_10GB.bin                    │
│ Block Size:  Adaptive (file size for <1MB, 1MB for >=1MB)         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ NFS MOUNT                                                           │
├─────────────────────────────────────────────────────────────────────┤
│ Path:        /tmp/remote-pure-nfs/                                 │
│ Type:        Network File System (Pure Storage backend)            │
│ Available:   ~1022GB                                               │
│ IO Modes:    Direct I/O (O_DIRECT)                                 │
│              └─ Bypasses OS page cache                              │
│              Buffered I/O                                           │
│              └─ Uses OS page cache                                  │
│                                                                     │
│ Test Files:  test_1K.bin through test_10GB.bin                    │
│ Block Size:  Adaptive (file size for <1MB, 1MB for >=1MB)         │
│                                                                     │
│ Network:     High-speed network to Pure Storage array              │
│              Supports high concurrency (QD=128+)                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Test Execution Sequence

```
┌─────────────────────────────────────────────────────────────────────┐
│              Detailed Test Execution Sequence                        │
└─────────────────────────────────────────────────────────────────────┘

For Storage: Local_SSD
│
├─ File: 1K
│  ├─ [Test 1] direct, QD=1   → Measure: time, BW, IOPS, latency
│  └─ [Test 2] direct, QD=128  → Measure: time, BW, IOPS, latency
│
├─ File: 4K
│  ├─ [Test 3] direct, QD=1   → Measure: time, BW, IOPS, latency
│  └─ [Test 4] direct, QD=128  → Measure: time, BW, IOPS, latency
│
├─ ... (continues for all file sizes)
│
└─ File: 10GB
   ├─ [Test 17] direct, QD=1   → Measure: time, BW, IOPS, latency
   └─ [Test 18] direct, QD=128 → Measure: time, BW, IOPS, latency

For Storage: NFS_Mount
│
├─ File: 1K
│  ├─ [Test 19] direct, QD=1    → Measure: time, BW, IOPS, latency
│  ├─ [Test 20] direct, QD=128  → Measure: time, BW, IOPS, latency
│  ├─ [Test 21] buffered, QD=1  → Measure: time, BW, IOPS, latency
│  └─ [Test 22] buffered, QD=128 → Measure: time, BW, IOPS, latency
│
├─ File: 4K
│  ├─ [Test 23] direct, QD=1    → Measure: time, BW, IOPS, latency
│  ├─ [Test 24] direct, QD=128  → Measure: time, BW, IOPS, latency
│  ├─ [Test 25] buffered, QD=1  → Measure: time, BW, IOPS, latency
│  └─ [Test 26] buffered, QD=128 → Measure: time, BW, IOPS, latency
│
├─ ... (continues for all file sizes)
│
└─ File: 10GB
   ├─ [Test 51] direct, QD=1    → Measure: time, BW, IOPS, latency
   ├─ [Test 52] direct, QD=128  → Measure: time, BW, IOPS, latency
   ├─ [Test 53] buffered, QD=1   → Measure: time, BW, IOPS, latency
   └─ [Test 54] buffered, QD=128 → Measure: time, BW, IOPS, latency
```

## Metrics Collected

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Metrics Per Test                                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────┬──────────────────────────────────────────────┐
│ Metric              │ Description                                   │
├─────────────────────┼──────────────────────────────────────────────┤
│ TotalTime_s         │ Time to read complete file once (seconds)    │
│                     │ (runtime / iterations)                        │
├─────────────────────┼──────────────────────────────────────────────┤
│ BW_MBps             │ Bandwidth in MB/s                            │
│                     │ (file_size_MB / total_time_s)                │
├─────────────────────┼──────────────────────────────────────────────┤
│ IOPS                │ I/O Operations Per Second                    │
│                     │ (from FIO read statistics)                     │
├─────────────────────┼──────────────────────────────────────────────┤
│ LatMean_us          │ Mean latency in microseconds                  │
│                     │ (average time per I/O operation)              │
├─────────────────────┼──────────────────────────────────────────────┤
│ LatP99_us           │ 99th percentile latency in microseconds      │
│                     │ (99% of I/Os complete within this time)        │
└─────────────────────┴──────────────────────────────────────────────┘
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Flow                                    │
└─────────────────────────────────────────────────────────────────────┘

Test File Creation:
  /dev/zero ──[dd]──> test_1K.bin ──> /tmp/local-ssd/
  /dev/zero ──[dd]──> test_1K.bin ──> /tmp/remote-pure-nfs/
  ... (for all file sizes)

Benchmark Execution:
  FIO ──[read]──> test_1K.bin ──> Collect metrics ──> JSON output
  FIO ──[read]──> test_1K.bin ──> Collect metrics ──> JSON output
  ... (3 iterations, averaged)

Results Processing:
  JSON ──[parse]──> Metrics ──[format]──> CSV row
  CSV rows ──[write]──> results/fio_YYYYMMDD_HHMMSS.csv

Validation:
  CSV ──[load]──> Results ──[analyze]──> Validation Report
  CSV ──[load]──> Results ──[summarize]──> Performance Summary
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Component Interaction                             │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ run_all_     │
│ benchmarks.sh│
└──────┬───────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌──────────────┐  ┌──────────────┐
│ setup_       │  │ fio_         │
│ environment  │  │ benchmark.py │
│ .sh          │  └──────┬───────┘
└──────────────┘         │
                         │
                         ├──────────────┐
                         │              │
                         ▼              ▼
                   ┌──────────┐   ┌──────────┐
                   │ create_ │   │ run_fio_ │
                   │ test_    │   │ test()   │
                   │ file()   │   └────┬─────┘
                   └──────────┘        │
                                        │
                                        ▼
                              ┌─────────────────┐
                              │   FIO Tool      │
                              │   (libaio)      │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ Local SSD     │  │ NFS Mount    │  │ Results CSV  │
            │ Storage       │  │ Storage      │  │ File         │
            └──────────────┘  └──────────────┘  └──────┬───────┘
                                                         │
                                                         ▼
                                              ┌──────────────────┐
                                              │ validate_        │
                                              │ results.py       │
                                              └──────────────────┘
```

