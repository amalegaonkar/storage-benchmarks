#!/usr/bin/env python3
"""
FIO Benchmark - Complete File Read Time
Measures time to read ENTIRE file (not time-based)
"""

import subprocess
import json
import os
import sys
import argparse
from datetime import datetime

# --- Default Configuration ---
DEFAULT_FILE_SIZES = [
    ("1MB", 1024**2, "test_1MB.bin"),
    ("10MB", 10 * 1024**2, "test_10MB.bin"),
    ("100MB", 100 * 1024**2, "test_100MB.bin"),
    ("1GB", 1024**3, "test_1GB.bin"),
]

DEFAULT_STORAGE_LOCATIONS = {
    "Local_SSD": "/tmp/local-ssd/",
    "NFS_Mount": "/tmp/remote-pure-nfs/",
}

DEFAULT_BLOCK_SIZE = "1M"
DEFAULT_IO_DEPTHS = [1, 128]
DEFAULT_NUM_ITERATIONS = 3  # Read the file 3 times for average


def create_test_file(filepath, size_bytes, use_zero=True):
    """
    Create a test file if it doesn't exist

    Args:
        filepath: Path to the test file
        size_bytes: Size of the file in bytes
        use_zero: If True, use /dev/zero (faster), else /dev/urandom (realistic data)
    """
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        if file_size == size_bytes:
            return True
        else:
            print(f"  WARNING: File exists but size mismatch ({file_size} vs {size_bytes}), recreating...",
                  file=sys.stderr)

    print(f"  Creating: {filepath} ({size_bytes / (1024**2):.1f} MB)...", file=sys.stderr)

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    source = '/dev/zero' if use_zero else '/dev/urandom'

    try:
        subprocess.run([
            'dd', f'if={source}', f'of={filepath}',
            f'bs=1M', f'count={size_bytes // (1024**2)}', 'status=none'
        ], check=True, timeout=300)
        return True
    except subprocess.TimeoutExpired:
        print(f"  ERROR: File creation timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return False


def run_fio_test(filepath, size_bytes, io_depth, direct, test_name, num_iterations, block_size):
    """
    Run FIO test - read ENTIRE file (not time-based)

    Returns:
        dict: Results dictionary with metrics, or None on failure
    """

    fio_cmd = [
        'fio',
        f'--name={test_name}',
        '--rw=read',
        f'--filename={filepath}',
        f'--size={size_bytes}',
        f'--bs={block_size}',
        f'--direct={direct}',
        '--ioengine=libaio',
        '--numjobs=1',
        f'--iodepth={io_depth}',
        f'--loops={num_iterations}',  # Read file N times
        '--output-format=json',
        '--group_reporting',
        # NO --time_based, so it reads the complete file
    ]

    try:
        result = subprocess.run(fio_cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            print(f"  FIO ERROR: {error_msg[:100]}", file=sys.stderr)
            return None

        fio_output = json.loads(result.stdout)
        read_stats = fio_output['jobs'][0]['read']

        # Get actual runtime and bytes read
        runtime_ms = read_stats.get('runtime', 0)  # milliseconds
        io_bytes = read_stats.get('io_bytes', 0)

        # Calculate total time for one complete read
        total_time_s = (runtime_ms / 1000) / num_iterations if num_iterations > 0 else 0

        # Calculate bandwidth
        bw_mbps = (size_bytes / (1024**2)) / total_time_s if total_time_s > 0 else 0

        # Get latency
        lat_ns = read_stats.get('lat_ns', {})
        lat_mean_us = lat_ns.get('mean', 0) / 1000 if lat_ns.get('mean') else 0
        lat_p99_us = lat_ns.get('percentile', {}).get('99.000000', 0) / 1000

        # Get IOPS
        iops = read_stats.get('iops', 0)

        return {
            'total_time_s': total_time_s,
            'bw_mbps': bw_mbps,
            'iops': iops,
            'lat_mean_us': lat_mean_us,
            'lat_p99_us': lat_p99_us,
            'bytes_read': io_bytes,
        }

    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT: Test exceeded 600s", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"  JSON PARSE ERROR: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  FAILED: {e}", file=sys.stderr)
        return None


def run_benchmark_suite(storage_locations=None, file_sizes=None, io_depths=None,
                       num_iterations=DEFAULT_NUM_ITERATIONS, block_size=DEFAULT_BLOCK_SIZE,
                       use_zero=True, output_file=None):
    """Run complete file read benchmark"""

    # Use defaults if not provided
    storage_locations = storage_locations or DEFAULT_STORAGE_LOCATIONS
    file_sizes = file_sizes or DEFAULT_FILE_SIZES
    io_depths = io_depths or DEFAULT_IO_DEPTHS

    # Prepare output
    if output_file:
        output_handle = open(output_file, 'w')
    else:
        output_handle = sys.stdout

    # Print CSV header
    print("StorageType,IOMode,FileSize,Bytes,IODepth,TotalTime_s,BW_MBps,IOPS,LatMean_us,LatP99_us",
          file=output_handle)

    print(f"\n{'='*70}", file=sys.stderr)
    print(f"FIO Complete File Read Benchmark", file=sys.stderr)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"Reading entire file {num_iterations} times, block size {block_size}", file=sys.stderr)
    print(f"{'='*70}\n", file=sys.stderr)

    test_count = 0
    success_count = 0
    fail_count = 0

    for loc_name, base_path in storage_locations.items():
        print(f"\n[{loc_name}] ({base_path})", file=sys.stderr)

        # Test both direct and buffered for NFS, only direct for local SSD
        test_modes = [("direct", 1), ("buffered", 0)] if "NFS" in loc_name else [("direct", 1)]

        for file_name, size_bytes, filename in file_sizes:
            filepath = os.path.join(base_path, filename)

            if not create_test_file(filepath, size_bytes, use_zero):
                print(f"  Skipping {file_name} - file creation failed", file=sys.stderr)
                continue

            for mode_name, direct in test_modes:
                for io_depth in io_depths:
                    test_count += 1
                    test_name = f"{loc_name}_{file_name}_{mode_name}_qd{io_depth}"

                    print(f"  [{test_count}] {file_name} {mode_name} qd={io_depth}...",
                          file=sys.stderr, end=' ')

                    results = run_fio_test(filepath, size_bytes, io_depth, direct, test_name,
                                          num_iterations, block_size)

                    if results:
                        success_count += 1
                        print(f"{loc_name},{mode_name},{file_name},{size_bytes},{io_depth},"
                              f"{results['total_time_s']:.4f},{results['bw_mbps']:.2f},"
                              f"{results['iops']:.2f},{results['lat_mean_us']:.2f},"
                              f"{results['lat_p99_us']:.2f}", file=output_handle)
                        output_handle.flush()
                        print(f"{results['total_time_s']:.2f}s ({results['bw_mbps']:.1f} MB/s, "
                              f"{results['iops']:.0f} IOPS)", file=sys.stderr)
                    else:
                        fail_count += 1
                        print(f"{loc_name},{mode_name},{file_name},{size_bytes},{io_depth},"
                              f"ERROR,ERROR,ERROR,ERROR,ERROR", file=output_handle)
                        output_handle.flush()
                        print("FAILED", file=sys.stderr)

    print(f"\n{'='*70}", file=sys.stderr)
    print(f"Benchmark complete!", file=sys.stderr)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"Tests: {test_count} total, {success_count} passed, {fail_count} failed", file=sys.stderr)
    print(f"{'='*70}\n", file=sys.stderr)

    if output_file:
        output_handle.close()
        print(f"Results written to: {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='FIO Storage Benchmark - Complete File Read Test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with defaults
  %(prog)s -o results.csv                     # Save results to file
  %(prog)s -i 5 -d 1 8 32                     # 5 iterations, test QD 1,8,32
  %(prog)s --use-urandom                      # Use /dev/urandom for test files
        """
    )

    parser.add_argument('-o', '--output', metavar='FILE',
                       help='Output CSV file (default: stdout)')
    parser.add_argument('-i', '--iterations', type=int, default=DEFAULT_NUM_ITERATIONS,
                       help=f'Number of read iterations (default: {DEFAULT_NUM_ITERATIONS})')
    parser.add_argument('-d', '--depths', nargs='+', type=int, default=DEFAULT_IO_DEPTHS,
                       help=f'IO depths to test (default: {DEFAULT_IO_DEPTHS})')
    parser.add_argument('-b', '--block-size', default=DEFAULT_BLOCK_SIZE,
                       help=f'Block size (default: {DEFAULT_BLOCK_SIZE})')
    parser.add_argument('--use-urandom', action='store_true',
                       help='Use /dev/urandom instead of /dev/zero for test files (slower)')

    args = parser.parse_args()

    # Check for FIO
    try:
        result = subprocess.run(['fio', '--version'], capture_output=True, check=True)
        print(f"Using FIO: {result.stdout.decode().strip()}", file=sys.stderr)
    except FileNotFoundError:
        print("ERROR: fio not installed. Install with: sudo apt-get install fio", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not run fio: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        run_benchmark_suite(
            io_depths=args.depths,
            num_iterations=args.iterations,
            block_size=args.block_size,
            use_zero=not args.use_urandom,
            output_file=args.output
        )
    except KeyboardInterrupt:
        print("\n\nCancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
