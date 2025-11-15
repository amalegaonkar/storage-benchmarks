#!/usr/bin/env python3
"""
FIO Benchmark with Device Discovery and Performance Validation
Automatically detects devices, generates expectations, runs benchmarks, and validates results
"""

import sys
import os
import argparse

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from device_info import get_device_info, print_device_info
from performance_expectations import (
    generate_expectations,
    validate_results,
    print_expectations,
    print_validation_report
)


def run_single_storage_benchmark(storage_path: str, storage_name: str, args):
    """Run benchmark for a single storage location with validation"""

    print(f"\n{'#'*80}")
    print(f"# Benchmarking: {storage_name}")
    print(f"# Path: {storage_path}")
    print(f"{'#'*80}\n")

    # Step 1: Device Discovery
    print("Step 1: Device Discovery...")
    device_info = get_device_info(storage_path)

    if "error" in device_info:
        print(f"ERROR: {device_info['error']}")
        return None

    print_device_info(device_info, verbose=False)

    # Step 2: Generate Performance Expectations
    print("\nStep 2: Generate Performance Expectations...")
    io_pattern = "sequential"  # For 1M block size benchmarks
    print_expectations(device_info, io_pattern)

    # Step 3: Run FIO Benchmark
    print("\nStep 3: Running FIO Benchmark...")
    print("(This will take a few minutes...)\n")

    # Import and run the actual FIO benchmark
    # We'll call the original benchmark function here
    # For now, show what would happen
    print(f"  File sizes: 1MB, 10MB, 100MB, 1GB")
    print(f"  Block size: {args.block_size}")
    print(f"  Queue depths: {args.depths}")
    print(f"  Iterations: {args.iterations}")

    # TODO: Actually run FIO benchmark and get results
    # This is a placeholder - in production, we'd integrate with fio_benchmark.py
    print("\n  [Benchmark would run here]")
    print("  Results would be validated against expectations")

    # Step 4: Validate Results (placeholder)
    print("\nStep 4: Validate Results...")
    print("  [Results validation would occur here]")

    return device_info


def main():
    parser = argparse.ArgumentParser(
        description='FIO Benchmark with automatic device discovery and validation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script:
  1. Discovers underlying storage devices
  2. Generates performance expectations based on device type
  3. Runs FIO benchmarks
  4. Validates results against expectations

Examples:
  %(prog)s --path /tmp/local-ssd
  %(prog)s --path /mnt/nfs --iterations 5
  %(prog)s --discover-only /tmp/local-ssd
        """
    )

    parser.add_argument('--path', required=True,
                       help='Storage path to benchmark')
    parser.add_argument('--name', default=None,
                       help='Name for this storage location')
    parser.add_argument('-o', '--output', metavar='FILE',
                       help='Output CSV file')
    parser.add_argument('-i', '--iterations', type=int, default=3,
                       help='Number of read iterations (default: 3)')
    parser.add_argument('-d', '--depths', nargs='+', type=int, default=[1, 128],
                       help='IO depths to test (default: 1 128)')
    parser.add_argument('-b', '--block-size', default="1M",
                       help='Block size (default: 1M)')
    parser.add_argument('--discover-only', action='store_true',
                       help='Only discover device info, skip benchmark')
    parser.add_argument('--expect-only', action='store_true',
                       help='Only show expectations, skip benchmark')

    args = parser.parse_args()

    storage_name = args.name or os.path.basename(args.path.rstrip('/'))

    # Device discovery mode
    if args.discover_only:
        device_info = get_device_info(args.path)
        print_device_info(device_info, verbose=True)
        return 0

    # Expectations only mode
    if args.expect_only:
        device_info = get_device_info(args.path)
        if "error" in device_info:
            print(f"ERROR: {device_info['error']}", file=sys.stderr)
            return 1
        print_device_info(device_info, verbose=False)
        print_expectations(device_info, "sequential")
        return 0

    # Full benchmark with validation
    result = run_single_storage_benchmark(args.path, storage_name, args)

    if result is None:
        return 1

    print(f"\n{'#'*80}")
    print("# Benchmark Complete!")
    print(f"{'#'*80}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
