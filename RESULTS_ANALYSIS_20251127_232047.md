# Benchmark Results Analysis - Extended File Size Suite
**Date**: 2025-11-27 23:20:47  
**File**: `results/fio_20251127_232047.csv`

## Overview

This benchmark includes the **extended file size suite** with smaller files (1K-100K) and larger files (up to 10GB), providing comprehensive performance characterization across the full spectrum of file sizes.

**Test Configuration**:
- **File Sizes**: 1K, 4K, 10K, 100K, 1MB, 10MB, 100MB, 1GB, 10GB
- **Queue Depths**: 1 (sequential), 128 (high concurrency)
- **IO Modes**: Direct I/O (both), Buffered I/O (NFS only)
- **Total Tests**: 54 (all successful)

---

## Executive Summary

| Storage Type | Avg BW (MB/s) | Max BW (MB/s) | Avg IOPS |
|--------------|---------------|---------------|----------|
| **Local_SSD** | 1,671.8 | 4,933.4 | 2,968 |
| **NFS_Mount** | 3,168.9 | **40,156.9** | 3,743 |

**Key Findings**:
1. ✅ **All 54 tests passed** - No failures
2. 🚀 **NFS achieves 40+ GB/s** with high concurrency (QD=128, 10GB file)
3. 📊 **Small files (< 1MB)** show low bandwidth due to overhead (expected)
4. ⚡ **Local SSD** shows consistent 2-5 GB/s performance
5. 🔥 **NFS scaling** is dramatic: 1.8 GB/s (QD=1) → 40 GB/s (QD=128) for 10GB files

---

## Detailed Performance Analysis

### 1. Small Files (< 1MB) - Overhead Dominated

#### **Local_SSD Performance**

| File Size | QD=1 BW | QD=128 BW | IOPS | Latency (μs) |
|-----------|---------|-----------|------|--------------|
| 1K | 2.9 MB/s | 2.9 MB/s | 3,000 | 36-29 |
| 4K | 11.7 MB/s | 11.7 MB/s | 3,000 | 38-30 |
| 10K | 29.3 MB/s | 29.3 MB/s | 3,000 | 38-30 |
| 100K | 293.0 MB/s | 293.0 MB/s | 3,000 | 73-307 |

**Analysis**:
- ⚠️ **Low bandwidth** is **expected** for tiny files - overhead dominates
- ✅ **Consistent 3,000 IOPS** across all small files (likely measurement limit)
- ✅ **Latency is excellent**: 30-40μs for most files
- 📝 **100K file** shows first signs of real throughput (293 MB/s)

#### **NFS_Mount Performance**

**Direct I/O**:
| File Size | QD=1 BW | QD=128 BW | IOPS | Latency (μs) |
|-----------|---------|-----------|------|--------------|
| 1K | 0.7 MB/s | 1.0 MB/s | 750-1000 | 531-352 |
| 4K | 5.9 MB/s | 5.9 MB/s | 1,500 | 336-284 |
| 10K | 9.8 MB/s | 14.7 MB/s | 1000-1500 | 369-285 |
| 100K | 97.7 MB/s | 146.5 MB/s | 1000-1500 | 472-428 |

**Buffered I/O**:
| File Size | QD=1 BW | QD=128 BW | IOPS | Latency (μs) |
|-----------|---------|-----------|------|--------------|
| 1K | 1.5 MB/s | 1.5 MB/s | 1,500 | 303-292 |
| 4K | 5.9 MB/s | 5.9 MB/s | 1,500 | 323-310 |
| 10K | 14.7 MB/s | 14.7 MB/s | 1,500 | 310-309 |
| 100K | 146.5 MB/s | 97.7 MB/s | 1500-1000 | 438-462 |

**Analysis**:
- ⚠️ **Very low bandwidth** for tiny files (1K-4K) - network overhead dominates
- ✅ **Buffered I/O helps** for small files (1.5 MB/s vs 0.7-1.0 MB/s)
- 📈 **Performance improves** as file size increases (100K shows 97-146 MB/s)
- ⏱️ **Higher latency** than Local SSD (300-500μs vs 30-40μs) - network overhead

**Key Insight**: Small files are **overhead-dominated**. Bandwidth measurements are not meaningful for files < 100K. Focus on **latency and IOPS** for small file performance.

---

### 2. Medium Files (1MB - 100MB) - Throughput Scaling

#### **Local_SSD Performance**

| File Size | QD=1 BW | QD=128 BW | Improvement | Latency (μs) |
|-----------|---------|-----------|-------------|--------------|
| 1MB | 1,500 MB/s | 1,500 MB/s | 0% | 627-629 |
| 10MB | 2,000 MB/s | 3,750 MB/s | **87%** | 487-2273 |
| 100MB | 2,256 MB/s | 4,839 MB/s | **114%** | 440-19698 |
| 1GB | 2,265 MB/s | 4,923 MB/s | **117%** | 441-25812 |

**Analysis**:
- ✅ **Consistent baseline**: ~2,200-2,300 MB/s at QD=1
- 🚀 **Excellent scaling**: Up to 4,900 MB/s with QD=128
- 📊 **Scaling improves** with larger files (more parallelism benefit)
- ⏱️ **Latency increases** with QD=128 (expected - more concurrent I/O)

#### **NFS_Mount Performance**

**Direct I/O**:
| File Size | QD=1 BW | QD=128 BW | Improvement | Latency (μs) |
|-----------|---------|-----------|-------------|--------------|
| 1MB | 600 MB/s | 750 MB/s | 25% | 1126-1006 |
| 10MB | 1,200 MB/s | **6,000 MB/s** | **400%** | 798-1282 |
| 100MB | 1,493 MB/s | **15,000 MB/s** | **905%** | 664-4706 |
| 1GB | 1,554 MB/s | **32,681 MB/s** | **2005%** | 640-3708 |

**Buffered I/O**:
| File Size | QD=1 BW | QD=128 BW | Latency (μs) |
|-----------|---------|-----------|--------------|
| 1MB | 429 MB/s | 429 MB/s | 1838-1907 |
| 10MB | 1,111 MB/s | 1,200 MB/s | 838-4032 |
| 100MB | 1,449 MB/s | 1,422 MB/s | 680-34756 |
| 1GB | 1,471 MB/s | 1,462 MB/s | 673-80846 |

**Analysis**:
- ✅ **Baseline (QD=1)**: ~1,200-1,600 MB/s (direct I/O)
- 🔥 **Exceptional scaling**: Up to **32,681 MB/s** with QD=128 (1GB file)
- ⚠️ **Buffered I/O** doesn't scale well with QD=128 (latency spikes to 80ms)
- 📈 **Scaling improves dramatically** with larger files

**Key Insight**: NFS performance is **highly concurrency-dependent**. For high-throughput workloads, use **direct I/O with high queue depth**.

---

### 3. Large Files (10GB) - Sustained Performance

#### **Local_SSD Performance**

| Configuration | Bandwidth | IOPS | Time (s) | Latency (μs) |
|---------------|-----------|------|----------|--------------|
| QD=1 | 1,452 MB/s | 1,452 | 7.05 | 425 |
| QD=128 | **4,933 MB/s** | 4,933 | 2.08 | 25,924 |

**Analysis**:
- ✅ **Consistent performance**: ~1,450 MB/s (QD=1), ~4,930 MB/s (QD=128)
- ⚡ **Fast**: 10GB read in 2.08 seconds with QD=128
- 📊 **Scales well**: 3.4x improvement with high concurrency

#### **NFS_Mount Performance**

**Direct I/O**:
| Configuration | Bandwidth | IOPS | Time (s) | Latency (μs) |
|---------------|-----------|------|----------|--------------|
| QD=1 | 1,838 MB/s | 1,838 | 5.57 | 541 |
| QD=128 | **40,157 MB/s** | 40,157 | 0.26 | 3,163 |

**Buffered I/O**:
| Configuration | Bandwidth | IOPS | Time (s) | Latency (μs) |
|---------------|-----------|------|----------|--------------|
| QD=1 | 1,646 MB/s | 1,646 | 6.22 | 602 |
| QD=128 | 1,621 MB/s | 1,621 | 6.32 | 77,542 |

**Analysis**:
- 🚀 **Outstanding performance**: **40+ GB/s** with QD=128 direct I/O
- ⚡ **Extremely fast**: 10GB read in **0.26 seconds** (260ms!)
- ⚠️ **Buffered I/O** doesn't scale (latency spikes to 77ms)
- 📊 **22x improvement** from QD=1 to QD=128 (direct I/O)

**Key Insight**: For large file workloads on NFS, **direct I/O with QD=128** is essential. Buffered I/O actually performs worse with high concurrency.

---

## Performance Comparison by File Size

### Small Files (< 1MB)
- **Winner**: **Local_SSD** (lower latency, higher IOPS)
- **Reason**: Network overhead dominates for NFS
- **Use Case**: Small file workloads → Use Local SSD

### Medium Files (1MB - 1GB)
- **QD=1**: **Local_SSD** is faster (2,200 MB/s vs 1,200-1,600 MB/s)
- **QD=128**: **NFS** can be faster (up to 32,681 MB/s vs 4,923 MB/s)
- **Use Case**: 
  - Single-threaded → Local SSD
  - Multi-threaded/high-concurrency → NFS with QD=128

### Large Files (10GB)
- **QD=1**: **NFS** slightly faster (1,838 MB/s vs 1,452 MB/s)
- **QD=128**: **NFS significantly faster** (40,157 MB/s vs 4,933 MB/s)
- **Use Case**: Large file workloads → NFS with high concurrency

---

## Key Insights & Recommendations

### 1. **File Size Matters**
- **Small files (< 100K)**: Overhead dominates, bandwidth measurements not meaningful
- **Medium files (1MB-1GB)**: Good for testing scaling behavior
- **Large files (10GB)**: Best for sustained throughput measurement

### 2. **Concurrency is Critical for NFS**
- **Low concurrency (QD=1)**: Local SSD is competitive or faster
- **High concurrency (QD=128)**: NFS can achieve 8x higher throughput
- **Recommendation**: Use NFS for parallel/multi-threaded workloads

### 3. **IO Mode Selection**
- **Direct I/O**: Essential for high-concurrency NFS workloads
- **Buffered I/O**: Better for small files, but doesn't scale with concurrency
- **Recommendation**: Use direct I/O for production workloads

### 4. **Latency Considerations**
- **Local SSD**: Consistent 30-500μs latency
- **NFS QD=1**: 500-800μs latency (network overhead)
- **NFS QD=128**: 3-4ms latency (acceptable for high-throughput workloads)
- **NFS Buffered QD=128**: 77ms latency (too high, avoid)

### 5. **Workload Matching**

| Workload Type | Recommended Storage | Configuration |
|--------------|---------------------|---------------|
| Small files (< 1MB) | Local SSD | Any QD |
| Single-threaded large files | Local SSD | QD=1 |
| Multi-threaded large files | NFS | QD=128, Direct I/O |
| High-throughput batch jobs | NFS | QD=128, Direct I/O |
| Low-latency requirements | Local SSD | QD=1 |

---

## Anomalies & Expected Behaviors

### Expected "Anomalies" (Not Real Problems)

1. **Low Bandwidth for Small Files**
   - ⚠️ Flagged as "LOW BANDWIDTH" but **expected**
   - Files < 1MB are overhead-dominated
   - Focus on latency/IOPS, not bandwidth

2. **High Variance for Large Files**
   - ⚠️ Flagged as "HIGH VARIANCE" but **expected**
   - Variance comes from comparing QD=1 vs QD=128
   - Shows the benefit of parallel I/O

### Real Performance Characteristics

1. **NFS Scaling**
   - CV=129% for 10GB files (QD=1 vs QD=128)
   - This is **legitimate scaling**, not an anomaly
   - Validated by "north star" benchmark (40+ GB/s)

2. **Local SSD Consistency**
   - CV=77% for 10GB files
   - Shows consistent scaling with queue depth
   - Predictable performance

---

## Conclusion

The extended file size suite provides comprehensive performance characterization:

✅ **Small Files**: Overhead-dominated, Local SSD has lower latency  
✅ **Medium Files**: NFS scales dramatically with concurrency  
✅ **Large Files**: NFS achieves 40+ GB/s with proper tuning  

**Bottom Line**: 
- **Local SSD**: Best for low-latency, single-threaded workloads (2-5 GB/s)
- **NFS**: Best for high-throughput, multi-threaded workloads (40+ GB/s with QD=128)

The benchmark successfully demonstrates that **Pure Storage NFS can achieve exceptional performance** (40+ GB/s) when properly configured with high concurrency, validating the "north star" benchmark results.


