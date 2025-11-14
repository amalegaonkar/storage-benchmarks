#!/usr/bin/env python3
"""
Validate and analyze benchmark results
Checks for anomalies, errors, and provides summary statistics
"""

import sys
import csv
import argparse
from pathlib import Path
from collections import defaultdict
import statistics


def load_csv_results(filepath):
    """Load results from CSV file"""
    results = []

    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip error rows
                if row.get('TotalTime_s') == 'ERROR':
                    results.append({**row, 'error': True})
                else:
                    # Convert numeric fields
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
                        'LatP99_us': float(row.get('LatP99_us', 0)),
                        'error': False
                    })

        return results

    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Failed to parse CSV: {e}", file=sys.stderr)
        return None


def validate_results(results):
    """Check for errors and anomalies"""

    print("="*70)
    print("VALIDATION REPORT")
    print("="*70)
    print()

    total_tests = len(results)
    error_tests = sum(1 for r in results if r.get('error'))
    success_tests = total_tests - error_tests

    print(f"Total Tests:    {total_tests}")
    print(f"Successful:     {success_tests}")
    print(f"Failed:         {error_tests}")
    print()

    if error_tests > 0:
        print("FAILED TESTS:")
        for r in results:
            if r.get('error'):
                print(f"  - {r['StorageType']} {r['FileSize']} {r['IOMode']} QD={r['IODepth']}")
        print()

    # Check for anomalies in successful tests
    valid_results = [r for r in results if not r.get('error')]

    if not valid_results:
        print("No valid results to analyze.")
        return False

    # Group by storage and file size
    groups = defaultdict(list)
    for r in valid_results:
        key = (r['StorageType'], r['FileSize'], r['IOMode'])
        groups[key].append(r)

    print("PERFORMANCE ANOMALIES:")
    print()

    anomalies_found = False

    for key, group in groups.items():
        storage, filesize, iomode = key

        # Check bandwidth consistency
        bandwidths = [r['BW_MBps'] for r in group]

        if len(bandwidths) >= 2:
            mean_bw = statistics.mean(bandwidths)
            stdev_bw = statistics.stdev(bandwidths) if len(bandwidths) > 1 else 0

            # Flag if std dev is > 20% of mean
            if mean_bw > 0 and (stdev_bw / mean_bw) > 0.20:
                anomalies_found = True
                print(f"  HIGH VARIANCE: {storage} {filesize} {iomode}")
                print(f"    Bandwidth: {mean_bw:.1f} ± {stdev_bw:.1f} MB/s (CV={stdev_bw/mean_bw*100:.1f}%)")
                print()

        # Check for suspiciously low bandwidth
        for r in group:
            expected_min_bw = 10  # MB/s minimum expected
            if r['BW_MBps'] < expected_min_bw:
                anomalies_found = True
                print(f"  LOW BANDWIDTH: {storage} {filesize} {iomode} QD={r['IODepth']}")
                print(f"    Bandwidth: {r['BW_MBps']:.1f} MB/s (< {expected_min_bw} MB/s)")
                print()

    if not anomalies_found:
        print("  No anomalies detected.")
        print()

    return error_tests == 0 and not anomalies_found


def print_summary(results):
    """Print summary statistics"""

    print("="*70)
    print("PERFORMANCE SUMMARY")
    print("="*70)
    print()

    valid_results = [r for r in results if not r.get('error')]

    if not valid_results:
        print("No valid results to summarize.")
        return

    # Group by storage type
    by_storage = defaultdict(list)
    for r in valid_results:
        by_storage[r['StorageType']].append(r)

    print(f"{'Storage Type':<20} {'Avg BW (MB/s)':<15} {'Max BW (MB/s)':<15} {'Avg IOPS':<12}")
    print("-"*70)

    for storage, group in sorted(by_storage.items()):
        avg_bw = statistics.mean([r['BW_MBps'] for r in group])
        max_bw = max([r['BW_MBps'] for r in group])
        avg_iops = statistics.mean([r['IOPS'] for r in group])

        print(f"{storage:<20} {avg_bw:<15.1f} {max_bw:<15.1f} {avg_iops:<12.0f}")

    print()

    # Breakdown by file size
    print("Performance by File Size:")
    print()

    by_filesize = defaultdict(list)
    for r in valid_results:
        key = (r['StorageType'], r['FileSize'])
        by_filesize[key].append(r)

    print(f"{'Storage':<15} {'File Size':<10} {'Avg Time (s)':<15} {'Avg BW (MB/s)':<15}")
    print("-"*70)

    for (storage, filesize), group in sorted(by_filesize.items()):
        avg_time = statistics.mean([r['TotalTime_s'] for r in group])
        avg_bw = statistics.mean([r['BW_MBps'] for r in group])

        print(f"{storage:<15} {filesize:<10} {avg_time:<15.2f} {avg_bw:<15.1f}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description='Validate and analyze benchmark results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('csv_file', help='Path to results CSV file')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed output')
    parser.add_argument('--summary-only', action='store_true',
                       help='Only show summary, skip validation')

    args = parser.parse_args()

    # Load results
    results = load_csv_results(args.csv_file)

    if results is None:
        sys.exit(1)

    if len(results) == 0:
        print("WARNING: No results found in CSV file", file=sys.stderr)
        sys.exit(1)

    # Validate
    if not args.summary_only:
        valid = validate_results(results)
    else:
        valid = True

    # Summary
    print_summary(results)

    # Exit code
    if not valid:
        sys.exit(1)


if __name__ == "__main__":
    main()
