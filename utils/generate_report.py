#!/usr/bin/env python3
"""
Generate Human-Readable Benchmark Report
Creates a comprehensive, formatted report from FIO benchmark results
"""

import csv
import sys
import argparse
from collections import defaultdict
from datetime import datetime
import statistics


def format_time(seconds):
    """Format time in human-readable units"""
    if seconds < 0.001:
        return f"{seconds * 1e6:.0f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"


def format_bytes(bytes_val):
    """Format bytes in human-readable format"""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024**2:
        return f"{bytes_val/1024:.1f} KB"
    elif bytes_val < 1024**3:
        return f"{bytes_val/(1024**2):.1f} MB"
    else:
        return f"{bytes_val/(1024**3):.2f} GB"


def format_bandwidth(mbps):
    """Format bandwidth in human-readable format"""
    if mbps < 1:
        return f"{mbps:.2f} MB/s"
    elif mbps < 1000:
        return f"{mbps:.1f} MB/s"
    else:
        return f"{mbps/1000:.2f} GB/s"


def load_results(csv_file):
    """Load results from CSV file"""
    results = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('TotalTime_s') == 'ERROR':
                    continue
                results.append({
                    'StorageType': row['StorageType'],
                    'IOMode': row['IOMode'],
                    'FileSize': row['FileSize'],
                    'Bytes': int(row['Bytes']),
                    'IODepth': int(row['IODepth']),
                    'TotalTime_s': float(row['TotalTime_s']),
                    'BW_MBps': float(row['BW_MBps']),
                    'IOPS': float(row['IOPS']),
                    'LatMean_us': float(row['LatMean_us']),
                })
        return results
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return None


def generate_report(results, output_file=None):
    """Generate human-readable report"""
    
    if output_file:
        out = open(output_file, 'w')
    else:
        out = sys.stdout
    
    # Header
    print("=" * 80, file=out)
    print("STORAGE BENCHMARK PERFORMANCE REPORT", file=out)
    print("=" * 80, file=out)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=out)
    print(f"Total Tests: {len(results)}", file=out)
    print("=" * 80, file=out)
    print(file=out)
    
    # Overall Summary
    print("EXECUTIVE SUMMARY", file=out)
    print("-" * 80, file=out)
    
    by_storage = defaultdict(list)
    for r in results:
        by_storage[r['StorageType']].append(r)
    
    print(f"\n{'Storage Type':<20} {'Avg Bandwidth':<20} {'Peak Bandwidth':<20} {'Avg IOPS':<15}", file=out)
    print("-" * 80, file=out)
    
    for storage in sorted(by_storage.keys()):
        group = by_storage[storage]
        avg_bw = statistics.mean([r['BW_MBps'] for r in group])
        max_bw = max([r['BW_MBps'] for r in group])
        avg_iops = statistics.mean([r['IOPS'] for r in group])
        
        print(f"{storage:<20} {format_bandwidth(avg_bw):<20} {format_bandwidth(max_bw):<20} {avg_iops:>12,.0f}", file=out)
    
    print(file=out)
    
    # Key Findings
    print("KEY FINDINGS", file=out)
    print("-" * 80, file=out)
    
    # Find best performers
    best_nfs_qd128 = max([r for r in results if r['StorageType'] == 'NFS_Mount' and r['IODepth'] == 128], 
                         key=lambda x: x['BW_MBps'], default=None)
    best_local_qd128 = max([r for r in results if r['StorageType'] == 'Local_SSD' and r['IODepth'] == 128], 
                           key=lambda x: x['BW_MBps'], default=None)
    
    if best_nfs_qd128:
        print(f"• NFS Peak Performance: {format_bandwidth(best_nfs_qd128['BW_MBps'])} "
              f"({best_nfs_qd128['FileSize']} file, QD={best_nfs_qd128['IODepth']}, {best_nfs_qd128['IOMode']} I/O)", file=out)
        print(f"  Read time: {format_time(best_nfs_qd128['TotalTime_s'])}", file=out)
    
    if best_local_qd128:
        print(f"• Local SSD Peak Performance: {format_bandwidth(best_local_qd128['BW_MBps'])} "
              f"({best_local_qd128['FileSize']} file, QD={best_local_qd128['IODepth']})", file=out)
        print(f"  Read time: {format_time(best_local_qd128['TotalTime_s'])}", file=out)
    
    print(file=out)
    
    # Detailed Performance by Storage Type
    for storage in sorted(by_storage.keys()):
        print("=" * 80, file=out)
        print(f"{storage.upper()} PERFORMANCE", file=out)
        print("=" * 80, file=out)
        print(file=out)
        
        storage_results = by_storage[storage]
        
        # Group by file size
        by_filesize = defaultdict(list)
        for r in storage_results:
            by_filesize[r['FileSize']].append(r)
        
        # Table header
        print(f"{'File Size':<12} {'IO Mode':<12} {'QD':<6} {'Time':<15} {'Bandwidth':<20} {'IOPS':<12} {'Latency':<15}", file=out)
        print("-" * 80, file=out)
        
        for filesize in sorted(by_filesize.keys(), key=lambda x: by_filesize[x][0]['Bytes']):
            group = by_filesize[filesize]
            for r in sorted(group, key=lambda x: (x['IOMode'], x['IODepth'])):
                print(f"{r['FileSize']:<12} {r['IOMode']:<12} {r['IODepth']:<6} "
                      f"{format_time(r['TotalTime_s']):<15} {format_bandwidth(r['BW_MBps']):<20} "
                      f"{r['IOPS']:>10,.0f}  {r['LatMean_us']/1000:.2f} ms", file=out)
        
        print(file=out)
        
        # Performance insights
        print("Performance Insights:", file=out)
        
        # Compare QD=1 vs QD=128 for each file size
        for filesize in sorted(by_filesize.keys(), key=lambda x: by_filesize[x][0]['Bytes']):
            group = by_filesize[filesize]
            qd1_results = [r for r in group if r['IODepth'] == 1]
            qd128_results = [r for r in group if r['IODepth'] == 128]
            
            if qd1_results and qd128_results:
                # Use direct I/O for comparison if available
                qd1 = next((r for r in qd1_results if r['IOMode'] == 'direct'), qd1_results[0])
                qd128 = next((r for r in qd128_results if r['IOMode'] == 'direct'), qd128_results[0])
                
                if qd1['BW_MBps'] > 0:
                    improvement = ((qd128['BW_MBps'] - qd1['BW_MBps']) / qd1['BW_MBps']) * 100
                    print(f"  • {filesize}: QD=128 improves bandwidth by {improvement:.1f}% "
                          f"({format_bandwidth(qd1['BW_MBps'])} → {format_bandwidth(qd128['BW_MBps'])})", file=out)
        
        print(file=out)
    
    # NFS Comparison (Direct vs Buffered)
    nfs_results = [r for r in results if r['StorageType'] == 'NFS_Mount']
    if nfs_results:
        print("=" * 80, file=out)
        print("NFS: DIRECT I/O vs BUFFERED I/O COMPARISON", file=out)
        print("=" * 80, file=out)
        print(file=out)
        
        by_filesize_nfs = defaultdict(lambda: {'direct': [], 'buffered': []})
        for r in nfs_results:
            by_filesize_nfs[r['FileSize']][r['IOMode']].append(r)
        
        print(f"{'File Size':<12} {'QD':<6} {'Direct BW':<20} {'Buffered BW':<20} {'Winner':<15}", file=out)
        print("-" * 80, file=out)
        
        for filesize in sorted(by_filesize_nfs.keys(), key=lambda x: by_filesize_nfs[x]['direct'][0]['Bytes'] if by_filesize_nfs[x]['direct'] else 0):
            data = by_filesize_nfs[filesize]
            
            for qd in [1, 128]:
                direct = next((r for r in data['direct'] if r['IODepth'] == qd), None)
                buffered = next((r for r in data['buffered'] if r['IODepth'] == qd), None)
                
                if direct and buffered:
                    direct_bw = format_bandwidth(direct['BW_MBps'])
                    buffered_bw = format_bandwidth(buffered['BW_MBps'])
                    winner = "Direct" if direct['BW_MBps'] > buffered['BW_MBps'] else "Buffered"
                    
                    print(f"{filesize:<12} {qd:<6} {direct_bw:<20} {buffered_bw:<20} {winner:<15}", file=out)
        
        print(file=out)
    
    # Recommendations
    print("=" * 80, file=out)
    print("RECOMMENDATIONS", file=out)
    print("=" * 80, file=out)
    print(file=out)
    
    print("Workload Matching:", file=out)
    print("  • Small files (< 1MB): Use Local SSD for lower latency", file=out)
    print("  • Single-threaded workloads: Use Local SSD (2-5 GB/s)", file=out)
    print("  • Multi-threaded/high-concurrency: Use NFS with QD=128 (30+ GB/s)", file=out)
    print("  • Large file transfers: Use NFS with Direct I/O and QD=128", file=out)
    print(file=out)
    
    print("Configuration Tips:", file=out)
    print("  • For NFS: Always use Direct I/O for high-concurrency workloads", file=out)
    print("  • For Local SSD: QD=128 provides 2x improvement over QD=1", file=out)
    print("  • Buffered I/O on NFS doesn't scale well with high queue depth", file=out)
    print(file=out)
    
    # Footer
    print("=" * 80, file=out)
    print("End of Report", file=out)
    print("=" * 80, file=out)
    
    if output_file:
        out.close()
        print(f"\nReport saved to: {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Generate human-readable benchmark report',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('csv_file', help='Input CSV file with benchmark results')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    results = load_results(args.csv_file)
    if results is None:
        sys.exit(1)
    
    if len(results) == 0:
        print("Error: No valid results found", file=sys.stderr)
        sys.exit(1)
    
    generate_report(results, args.output)


if __name__ == "__main__":
    main()

