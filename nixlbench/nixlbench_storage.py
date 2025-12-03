#!/usr/bin/env python3
"""
NIXLBench Storage Benchmark Script
Runs nixlbench with POSIX backend for storage performance testing
"""

import subprocess
import json
import os
import sys
import argparse
from datetime import datetime

# Default configuration
DEFAULT_STORAGE_LOCATIONS = {
    "Local_SSD": "/tmp/local-ssd/",
    "NFS_Mount": "/tmp/remote-pure-nfs/",
}

DEFAULT_FILE_SIZES = [
    ("1MB", 1024**2),
    ("10MB", 10 * 1024**2),
    ("100MB", 100 * 1024**2),
    ("1GB", 1024**3),
]

DEFAULT_BLOCK_SIZES = [4096, 65536, 1048576]  # 4K, 64K, 1M
DEFAULT_NUM_ITERATIONS = 1000
DEFAULT_NUM_THREADS = 1


def check_etcd_running():
    """Check if ETCD is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=quay.io/coreos/etcd", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return len(result.stdout.strip()) > 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_etcd():
    """Start ETCD in Docker if not running"""
    if check_etcd_running():
        print("[INFO] ETCD is already running")
        return True
    
    print("[INFO] Starting ETCD server in Docker...")
    try:
        subprocess.run(
            ["docker", "run", "-d", "-p", "2379:2379", "--name", "nixl-etcd", "quay.io/coreos/etcd:v3.5.1"],
            check=True,
            capture_output=True
        )
        print("[OK] ETCD server started")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to start ETCD: {e}")
        print("[INFO] You can start ETCD manually with:")
        print("  docker run -d -p 2379:2379 quay.io/coreos/etcd:v3.5.1")
        return False


def run_nixlbench(storage_path, filepath, block_size, op_type="READ", 
                  num_iter=1000, num_threads=1, backend="POSIX", 
                  api_type="AIO", use_etcd=True):
    """
    Run nixlbench with specified parameters
    
    Args:
        storage_path: Base storage path
        filepath: Full path to test file
        block_size: Block size in bytes
        op_type: Operation type (READ or WRITE)
        num_iter: Number of iterations
        num_threads: Number of threads
        backend: Backend type (POSIX, UCX, etc.)
        api_type: API type for POSIX (AIO, URING, POSIXAIO)
        use_etcd: Whether to use ETCD runtime
    """
    
    # Ensure file exists for READ operations
    if op_type == "READ" and not os.path.exists(filepath):
        print(f"[WARN] Test file {filepath} does not exist, skipping READ test")
        return None
    
    # Build nixlbench command
    cmd = [
        "nixlbench",
        f"--backend={backend}",
        f"--filepath={filepath}",
        f"--op_type={op_type}",
        f"--start_block_size={block_size}",
        f"--max_block_size={block_size}",
        f"--num_iter={num_iter}",
        f"--num_threads={num_threads}",
        f"--initiator_seg_type=DRAM",
        f"--target_seg_type=DRAM",
    ]
    
    if backend == "POSIX":
        cmd.append(f"--posix_api_type={api_type}")
    
    if use_etcd:
        cmd.append("--runtime_type=ETCD")
        cmd.append("--etcd_endpoints=http://localhost:2379")
    else:
        # Try without runtime_type - may not work if ETCD is required
        # For storage backends, ETCD should be optional
        pass
    
    print(f"\n[INFO] Running nixlbench: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            print(f"[ERROR] nixlbench failed with return code {result.returncode}")
            print(f"[ERROR] stderr: {result.stderr}")
            return None
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        print("[ERROR] nixlbench timed out")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to run nixlbench: {e}")
        return None


def create_test_file(filepath, size_bytes):
    """Create a test file of specified size"""
    if os.path.exists(filepath):
        print(f"[INFO] Test file {filepath} already exists")
        return True
    
    print(f"[INFO] Creating test file {filepath} ({size_bytes} bytes)...")
    try:
        with open(filepath, 'wb') as f:
            # Write in chunks to avoid memory issues
            chunk_size = 1024 * 1024  # 1MB chunks
            remaining = size_bytes
            while remaining > 0:
                chunk = min(chunk_size, remaining)
                f.write(b'\x00' * chunk)
                remaining -= chunk
        print(f"[OK] Test file created")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create test file: {e}")
        return False


def parse_nixlbench_output(output):
    """Parse nixlbench output to extract performance metrics"""
    # This is a placeholder - actual parsing depends on nixlbench output format
    metrics = {}
    
    # Try to extract bandwidth, IOPS, latency from output
    lines = output.split('\n')
    for line in lines:
        if 'bandwidth' in line.lower() or 'bw' in line.lower():
            # Extract bandwidth value
            pass
        if 'iops' in line.lower():
            # Extract IOPS value
            pass
        if 'latency' in line.lower() or 'lat' in line.lower():
            # Extract latency value
            pass
    
    return metrics


def run_benchmark_suite(storage_locations=None, file_sizes=None, 
                        block_sizes=None, num_iterations=1000, 
                        num_threads=1, backend="POSIX", api_type="AIO",
                        use_etcd=True, output_file=None):
    """
    Run comprehensive nixlbench storage benchmark suite
    
    Args:
        storage_locations: Dict of storage name -> path
        file_sizes: List of (name, size_bytes) tuples
        block_sizes: List of block sizes in bytes
        num_iterations: Number of iterations per test
        num_threads: Number of threads
        backend: Backend type
        api_type: POSIX API type
        use_etcd: Whether to use ETCD
        output_file: Output CSV file path
    """
    
    if storage_locations is None:
        storage_locations = DEFAULT_STORAGE_LOCATIONS
    
    if file_sizes is None:
        file_sizes = DEFAULT_FILE_SIZES
    
    if block_sizes is None:
        block_sizes = DEFAULT_BLOCK_SIZES
    
    # Start ETCD if needed
    if use_etcd:
        if not start_etcd():
            print("[WARN] ETCD not available, trying without ETCD runtime...")
            use_etcd = False
    
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 60)
    print("NIXLBench Storage Benchmark Suite")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    
    for storage_name, storage_path in storage_locations.items():
        print(f"\n{'='*60}")
        print(f"Testing: {storage_name} ({storage_path})")
        print(f"{'='*60}")
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        for file_name, file_size in file_sizes:
            filepath = os.path.join(storage_path, f"test_{file_name}.bin")
            
            # Create test file if it doesn't exist
            if not create_test_file(filepath, file_size):
                continue
            
            for block_size in block_sizes:
                # Skip if block size is larger than file size
                if block_size > file_size:
                    continue
                
                print(f"\n--- File: {file_name}, Block Size: {block_size} bytes ---")
                
                # Run READ test
                read_result = run_nixlbench(
                    storage_path=storage_path,
                    filepath=filepath,
                    block_size=block_size,
                    op_type="READ",
                    num_iter=num_iterations,
                    num_threads=num_threads,
                    backend=backend,
                    api_type=api_type,
                    use_etcd=use_etcd
                )
                
                if read_result:
                    results.append({
                        "timestamp": timestamp,
                        "storage": storage_name,
                        "storage_path": storage_path,
                        "file_name": file_name,
                        "file_size": file_size,
                        "block_size": block_size,
                        "op_type": "READ",
                        "backend": backend,
                        "api_type": api_type,
                        "num_threads": num_threads,
                        "output": read_result["stdout"]
                    })
    
    # Save results to CSV if output file specified
    if output_file:
        save_results_to_csv(results, output_file)
    
    print("\n" + "=" * 60)
    print(f"Benchmark Complete: {datetime.now()}")
    print("=" * 60)
    
    return results


def save_results_to_csv(results, output_file):
    """Save results to CSV file"""
    import csv
    
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "storage", "storage_path", "file_name", "file_size",
            "block_size", "op_type", "backend", "api_type", "num_threads", "output"
        ])
        
        for result in results:
            writer.writerow([
                result["timestamp"],
                result["storage"],
                result["storage_path"],
                result["file_name"],
                result["file_size"],
                result["block_size"],
                result["op_type"],
                result["backend"],
                result["api_type"],
                result["num_threads"],
                result["output"].replace('\n', ' ').replace('\r', ' ')
            ])
    
    print(f"\n[OK] Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="NIXLBench Storage Benchmark")
    parser.add_argument("-c", "--config", help="JSON config file", default="config.json")
    parser.add_argument("-o", "--output", help="Output CSV file", 
                       default=f"results/nixlbench_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    parser.add_argument("--backend", default="POSIX", choices=["POSIX", "UCX", "GDS"],
                       help="Backend type")
    parser.add_argument("--api-type", default="AIO", choices=["AIO", "URING", "POSIXAIO"],
                       help="POSIX API type")
    parser.add_argument("--no-etcd", action="store_true", help="Don't use ETCD runtime")
    parser.add_argument("--num-iter", type=int, default=1000, help="Number of iterations")
    parser.add_argument("--num-threads", type=int, default=1, help="Number of threads")
    
    args = parser.parse_args()
    
    # Load config if exists
    storage_locations = DEFAULT_STORAGE_LOCATIONS
    file_sizes = DEFAULT_FILE_SIZES
    
    if os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
            if "storage_locations" in config:
                storage_locations = config["storage_locations"]
            if "file_sizes" in config:
                file_sizes = [(s["name"], s["bytes"]) for s in config["file_sizes"]]
    
    run_benchmark_suite(
        storage_locations=storage_locations,
        file_sizes=file_sizes,
        num_iterations=args.num_iter,
        num_threads=args.num_threads,
        backend=args.backend,
        api_type=args.api_type,
        use_etcd=not args.no_etcd,
        output_file=args.output
    )


if __name__ == "__main__":
    main()

