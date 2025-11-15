#!/usr/bin/env python3
"""
Performance Expectations and Hypothesis Generation
Predicts expected performance based on device characteristics
"""

import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass
class PerformanceRange:
    """Expected performance range"""
    metric: str
    min_value: float
    max_value: float
    typical_value: float
    unit: str
    confidence: str  # "high", "medium", "low"

    def __str__(self):
        return f"{self.metric}: {self.typical_value} {self.unit} (range: {self.min_value}-{self.max_value})"

    def check_value(self, value: float) -> Tuple[bool, str]:
        """Check if a value meets expectations"""
        if value >= self.min_value and value <= self.max_value:
            deviation = abs(value - self.typical_value) / self.typical_value * 100
            if deviation < 10:
                return True, "excellent"
            elif deviation < 25:
                return True, "good"
            else:
                return True, "acceptable"
        elif value < self.min_value:
            return False, f"below_minimum ({value} < {self.min_value})"
        else:
            return False, f"above_maximum ({value} > {self.max_value})"


class DevicePerformanceProfile:
    """Performance profile for different device types"""

    # NVMe Performance Profiles
    NVME_PROFILES = {
        "consumer_gen3": {
            "seq_read_mbps": (2000, 3500, 3000),
            "seq_write_mbps": (1000, 3000, 2000),
            "rand_read_iops": (200000, 500000, 400000),
            "rand_write_iops": (100000, 400000, 300000),
            "latency_us": (50, 150, 100),
            "interface": "PCIe Gen3 x4"
        },
        "consumer_gen4": {
            "seq_read_mbps": (5000, 7400, 7000),
            "seq_write_mbps": (4000, 7000, 6000),
            "rand_read_iops": (500000, 1000000, 800000),
            "rand_write_iops": (400000, 900000, 700000),
            "latency_us": (30, 100, 60),
            "interface": "PCIe Gen4 x4"
        },
        "enterprise_gen3": {
            "seq_read_mbps": (2000, 3500, 3200),
            "seq_write_mbps": (2000, 3200, 3000),
            "rand_read_iops": (400000, 800000, 700000),
            "rand_write_iops": (300000, 700000, 600000),
            "latency_us": (20, 80, 50),
            "interface": "PCIe Gen3 x4"
        },
        "enterprise_gen4": {
            "seq_read_mbps": (6000, 7500, 7000),
            "seq_write_mbps": (5000, 7000, 6500),
            "rand_read_iops": (800000, 1500000, 1200000),
            "rand_write_iops": (700000, 1300000, 1000000),
            "latency_us": (10, 60, 30),
            "interface": "PCIe Gen4 x4"
        }
    }

    # SATA SSD Profiles
    SATA_SSD_PROFILES = {
        "sata_ssd": {
            "seq_read_mbps": (400, 550, 500),
            "seq_write_mbps": (300, 520, 450),
            "rand_read_iops": (60000, 100000, 90000),
            "rand_write_iops": (50000, 90000, 80000),
            "latency_us": (100, 300, 200),
            "interface": "SATA 6Gb/s"
        }
    }

    # HDD Profiles
    HDD_PROFILES = {
        "hdd_7200rpm": {
            "seq_read_mbps": (100, 200, 150),
            "seq_write_mbps": (100, 180, 140),
            "rand_read_iops": (80, 150, 120),
            "rand_write_iops": (80, 140, 110),
            "latency_us": (8000, 15000, 12000),
            "interface": "SATA"
        },
        "hdd_10000rpm": {
            "seq_read_mbps": (150, 250, 200),
            "seq_write_mbps": (150, 230, 190),
            "rand_read_iops": (120, 200, 160),
            "rand_write_iops": (110, 180, 140),
            "latency_us": (5000, 10000, 7000),
            "interface": "SAS"
        }
    }

    # Network Storage Profiles
    NETWORK_PROFILES = {
        "nfs_1gbe": {
            "seq_read_mbps": (80, 120, 110),
            "seq_write_mbps": (70, 115, 100),
            "rand_read_iops": (1000, 5000, 3000),
            "rand_write_iops": (500, 3000, 2000),
            "latency_us": (200, 1000, 500),
            "interface": "1GbE Network"
        },
        "nfs_10gbe": {
            "seq_read_mbps": (800, 1200, 1100),
            "seq_write_mbps": (700, 1150, 1000),
            "rand_read_iops": (10000, 50000, 30000),
            "rand_write_iops": (5000, 30000, 20000),
            "latency_us": (100, 500, 300),
            "interface": "10GbE Network"
        },
        "nfs_25gbe": {
            "seq_read_mbps": (2000, 3000, 2800),
            "seq_write_mbps": (1800, 2900, 2600),
            "rand_read_iops": (50000, 150000, 100000),
            "rand_write_iops": (30000, 100000, 70000),
            "latency_us": (50, 300, 150),
            "interface": "25GbE Network"
        }
    }


def identify_device_profile(device_info: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Identify the performance profile for a device

    Args:
        device_info: Device information from device_info.py

    Returns:
        (profile_name, profile_dict) or (None, None)
    """
    device_type = device_info.get('device_type', '').lower()
    model = device_info.get('model', '').lower()

    # NVMe devices
    if device_type == 'nvme':
        # Try to determine generation from model or interface
        if any(x in model for x in ['980 pro', '990 pro', 'sn850', 'sn850x', 'p5 plus', 'firecuda 530']):
            return "consumer_gen4", DevicePerformanceProfile.NVME_PROFILES["consumer_gen4"]
        elif any(x in model for x in ['980', '970 evo', 'sn750', 'p5']):
            return "consumer_gen3", DevicePerformanceProfile.NVME_PROFILES["consumer_gen3"]
        elif any(x in model for x in ['optane', 'p4800', 'p5800', 'pm1733', 'pm9a3']):
            return "enterprise_gen4", DevicePerformanceProfile.NVME_PROFILES["enterprise_gen4"]
        elif any(x in model for x in ['pm983', 'pm963', 'intel p3']):
            return "enterprise_gen3", DevicePerformanceProfile.NVME_PROFILES["enterprise_gen3"]
        else:
            # Default to consumer Gen3
            return "consumer_gen3", DevicePerformanceProfile.NVME_PROFILES["consumer_gen3"]

    # SATA/SCSI devices
    elif device_type == 'scsi':
        media_type = device_info.get('media_type', '').upper()
        rotation = device_info.get('rotation_rate', '').lower()

        if media_type == 'SSD' or 'solid state' in rotation:
            return "sata_ssd", DevicePerformanceProfile.SATA_SSD_PROFILES["sata_ssd"]
        elif '10000' in rotation or '10k' in rotation:
            return "hdd_10000rpm", DevicePerformanceProfile.HDD_PROFILES["hdd_10000rpm"]
        elif '7200' in rotation or '7.2k' in rotation or media_type == 'HDD':
            return "hdd_7200rpm", DevicePerformanceProfile.HDD_PROFILES["hdd_7200rpm"]
        else:
            # Default to 7200 RPM HDD
            return "hdd_7200rpm", DevicePerformanceProfile.HDD_PROFILES["hdd_7200rpm"]

    # Network storage
    elif device_type == 'network':
        protocol = device_info.get('protocol', '').upper()
        options = device_info.get('options', '').lower()

        # Try to detect network speed from mount options or nfsstat
        # This is a heuristic approach
        if '25g' in options or '25000' in str(device_info):
            return "nfs_25gbe", DevicePerformanceProfile.NETWORK_PROFILES["nfs_25gbe"]
        elif '10g' in options or '10000' in str(device_info):
            return "nfs_10gbe", DevicePerformanceProfile.NETWORK_PROFILES["nfs_10gbe"]
        else:
            # Default to 1GbE
            return "nfs_1gbe", DevicePerformanceProfile.NETWORK_PROFILES["nfs_1gbe"]

    return None, None


def generate_expectations(device_info: Dict, io_pattern: str = "sequential") -> List[PerformanceRange]:
    """
    Generate performance expectations for a device

    Args:
        device_info: Device information from device_info.py
        io_pattern: "sequential" or "random"

    Returns:
        List of PerformanceRange objects
    """
    profile_name, profile = identify_device_profile(device_info)

    if not profile:
        return []

    expectations = []

    # Determine confidence based on how well we know the device
    confidence = "high" if device_info.get('model') else "medium"
    if device_info.get('device_type') == 'network':
        confidence = "medium"  # Network performance is more variable

    # Sequential read bandwidth
    if io_pattern == "sequential":
        min_bw, max_bw, typ_bw = profile["seq_read_mbps"]
        expectations.append(PerformanceRange(
            metric="Sequential Read Bandwidth",
            min_value=min_bw,
            max_value=max_bw,
            typical_value=typ_bw,
            unit="MB/s",
            confidence=confidence
        ))

    # Random IOPS (4K)
    elif io_pattern == "random":
        min_iops, max_iops, typ_iops = profile["rand_read_iops"]
        expectations.append(PerformanceRange(
            metric="Random Read IOPS (4K)",
            min_value=min_iops,
            max_value=max_iops,
            typical_value=typ_iops,
            unit="IOPS",
            confidence=confidence
        ))

    # Latency
    min_lat, max_lat, typ_lat = profile["latency_us"]
    expectations.append(PerformanceRange(
        metric="Average Latency",
        min_value=min_lat,
        max_value=max_lat,
        typical_value=typ_lat,
        unit="μs",
        confidence=confidence
    ))

    return expectations


def validate_results(device_info: Dict, benchmark_results: Dict, io_pattern: str = "sequential") -> Dict:
    """
    Validate benchmark results against expectations

    Args:
        device_info: Device information
        benchmark_results: Results from FIO benchmark
        io_pattern: "sequential" or "random"

    Returns:
        Validation report dictionary
    """
    expectations = generate_expectations(device_info, io_pattern)
    profile_name, profile = identify_device_profile(device_info)

    report = {
        "device": device_info.get('device', 'Unknown'),
        "profile": profile_name or "Unknown",
        "io_pattern": io_pattern,
        "checks": [],
        "overall_status": "UNKNOWN"
    }

    if not expectations:
        report["overall_status"] = "NO_EXPECTATIONS"
        report["message"] = "Could not generate expectations for this device"
        return report

    # Check bandwidth
    if "BW_MBps" in benchmark_results:
        bw = benchmark_results["BW_MBps"]
        for expect in expectations:
            if "Bandwidth" in expect.metric:
                passed, status = expect.check_value(bw)
                report["checks"].append({
                    "metric": expect.metric,
                    "expected": f"{expect.typical_value} {expect.unit} (range: {expect.min_value}-{expect.max_value})",
                    "actual": f"{bw} {expect.unit}",
                    "status": status,
                    "passed": passed
                })

    # Check IOPS
    if "IOPS" in benchmark_results:
        iops = benchmark_results["IOPS"]
        for expect in expectations:
            if "IOPS" in expect.metric:
                passed, status = expect.check_value(iops)
                report["checks"].append({
                    "metric": expect.metric,
                    "expected": f"{expect.typical_value} {expect.unit} (range: {expect.min_value}-{expect.max_value})",
                    "actual": f"{iops} {expect.unit}",
                    "status": status,
                    "passed": passed
                })

    # Check latency
    if "LatMean_us" in benchmark_results:
        lat = benchmark_results["LatMean_us"]
        for expect in expectations:
            if "Latency" in expect.metric:
                passed, status = expect.check_value(lat)
                report["checks"].append({
                    "metric": expect.metric,
                    "expected": f"{expect.typical_value} {expect.unit} (range: {expect.min_value}-{expect.max_value})",
                    "actual": f"{lat} {expect.unit}",
                    "status": status,
                    "passed": passed
                })

    # Determine overall status
    if report["checks"]:
        all_passed = all(check["passed"] for check in report["checks"])
        any_excellent = any("excellent" in check["status"] for check in report["checks"])
        any_good = any("good" in check["status"] for check in report["checks"])

        if all_passed:
            if any_excellent:
                report["overall_status"] = "EXCELLENT"
            elif any_good:
                report["overall_status"] = "GOOD"
            else:
                report["overall_status"] = "ACCEPTABLE"
        else:
            report["overall_status"] = "FAIL"

    return report


def print_expectations(device_info: Dict, io_pattern: str = "sequential"):
    """Print expected performance for a device"""
    profile_name, profile = identify_device_profile(device_info)

    print(f"\n{'='*70}")
    print(f"Performance Expectations")
    print(f"{'='*70}\n")

    print(f"Device:       {device_info.get('device', 'Unknown')}")
    print(f"Type:         {device_info.get('device_type', 'Unknown')}")
    if device_info.get('model'):
        print(f"Model:        {device_info['model']}")

    if not profile_name:
        print(f"\nCould not determine performance profile for this device.")
        return

    print(f"Profile:      {profile_name}")
    print(f"Interface:    {profile.get('interface', 'Unknown')}")
    print(f"\nExpected Performance ({io_pattern}):")
    print(f"{'-'*70}")

    expectations = generate_expectations(device_info, io_pattern)

    for expect in expectations:
        print(f"  {expect.metric}:")
        print(f"    Typical:  {expect.typical_value} {expect.unit}")
        print(f"    Range:    {expect.min_value} - {expect.max_value} {expect.unit}")
        print(f"    Confidence: {expect.confidence}")
        print()

    print(f"{'='*70}\n")


def print_validation_report(report: Dict):
    """Print validation report"""
    print(f"\n{'='*70}")
    print(f"Performance Validation Report")
    print(f"{'='*70}\n")

    print(f"Device:       {report['device']}")
    print(f"Profile:      {report['profile']}")
    print(f"I/O Pattern:  {report['io_pattern']}")
    print(f"Overall:      {report['overall_status']}")

    if "message" in report:
        print(f"\n{report['message']}")
        return

    print(f"\n{'Metric':<30} {'Expected':<25} {'Actual':<20} {'Status'}")
    print(f"{'-'*70}")

    for check in report["checks"]:
        status_symbol = "✓" if check["passed"] else "✗"
        print(f"{check['metric']:<30} {check['expected']:<25} {check['actual']:<20} {status_symbol} {check['status']}")

    print(f"\n{'='*70}\n")


def main():
    import argparse
    import json
    from device_info import get_device_info

    parser = argparse.ArgumentParser(
        description='Generate performance expectations for storage devices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /tmp/local-ssd
  %(prog)s /mnt/nfs --io-pattern random
  %(prog)s /dev/nvme0n1 --validate results.json
        """
    )

    parser.add_argument('path', help='Filesystem path or device')
    parser.add_argument('--io-pattern', choices=['sequential', 'random'],
                       default='sequential', help='I/O pattern to predict')
    parser.add_argument('--validate', metavar='RESULTS_JSON',
                       help='Validate against benchmark results (JSON file)')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    # Get device info
    device_info = get_device_info(args.path)

    if "error" in device_info:
        print(f"Error: {device_info['error']}", file=sys.stderr)
        return 1

    # Validation mode
    if args.validate:
        try:
            with open(args.validate, 'r') as f:
                results = json.load(f)

            report = validate_results(device_info, results, args.io_pattern)

            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print_validation_report(report)

        except Exception as e:
            print(f"Error reading results file: {e}", file=sys.stderr)
            return 1

    # Expectation mode
    else:
        if args.json:
            expectations = generate_expectations(device_info, args.io_pattern)
            output = {
                "device": device_info.get('device'),
                "profile": identify_device_profile(device_info)[0],
                "io_pattern": args.io_pattern,
                "expectations": [
                    {
                        "metric": e.metric,
                        "min": e.min_value,
                        "max": e.max_value,
                        "typical": e.typical_value,
                        "unit": e.unit,
                        "confidence": e.confidence
                    }
                    for e in expectations
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            print_expectations(device_info, args.io_pattern)

    return 0


if __name__ == "__main__":
    sys.exit(main())
