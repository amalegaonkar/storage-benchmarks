#!/usr/bin/env python3
"""
Device Discovery and Information Gathering
Finds underlying storage device and gathers detailed specifications
"""

import subprocess
import os
import sys
import re
from typing import Dict, Optional, Tuple
from pathlib import Path


def run_cmd(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run command and return result"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            timeout=30
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {' '.join(cmd)}", file=sys.stderr)
        return subprocess.CompletedProcess(cmd, 1, "", "Timeout")
    except Exception as e:
        print(f"Command failed: {' '.join(cmd)}: {e}", file=sys.stderr)
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def find_mount_point(path: str) -> str:
    """Find the mount point for a given path"""
    path = os.path.abspath(path)

    # Walk up the directory tree until we find a mount point
    while path != '/':
        if os.path.ismount(path):
            return path
        path = os.path.dirname(path)

    return '/'


def get_device_from_path(path: str) -> Tuple[Optional[str], str]:
    """
    Find the underlying device for a filesystem path

    Returns:
        (device_path, mount_point) or (None, mount_point) if not found
    """
    mount_point = find_mount_point(path)

    # Read /proc/mounts to find the device
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == mount_point:
                    device = parts[0]

                    # Resolve symlinks (e.g., /dev/disk/by-uuid/...)
                    if device.startswith('/dev/'):
                        try:
                            device = os.path.realpath(device)
                        except:
                            pass

                    return device, mount_point
    except Exception as e:
        print(f"Error reading /proc/mounts: {e}", file=sys.stderr)

    return None, mount_point


def get_device_type(device: str) -> str:
    """Determine device type (nvme, sda, nfs, etc.)"""
    if not device:
        return "unknown"

    if device.startswith('//') or ':' in device:
        # Network device (NFS, CIFS, etc.)
        return "network"

    if not device.startswith('/dev/'):
        return "virtual"

    device_name = os.path.basename(device)

    if device_name.startswith('nvme'):
        return "nvme"
    elif device_name.startswith('sd'):
        return "scsi"  # Could be SATA, SAS, or USB
    elif device_name.startswith('vd'):
        return "virtio"
    elif device_name.startswith('hd'):
        return "ide"
    elif device_name.startswith('md'):
        return "raid"
    elif device_name.startswith('dm'):
        return "lvm"
    else:
        return "unknown"


def get_underlying_devices(device: str) -> list:
    """
    Get underlying physical devices for virtual devices (LVM, RAID, etc.)

    Args:
        device: Device path (e.g., /dev/dm-0)

    Returns:
        List of underlying device paths
    """
    underlying = []

    # Try lsblk to get the device hierarchy
    out = run_cmd(["lsblk", "-no", "NAME,TYPE", device], check=False)
    if out.returncode == 0:
        lines = out.stdout.strip().split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                name, dev_type = parts[0], parts[1]
                # Look for physical devices (disk, part)
                if dev_type in ['disk', 'part'] and name not in os.path.basename(device):
                    # Clean up the name (remove tree characters)
                    clean_name = name.replace('├─', '').replace('└─', '').replace('│', '').strip()
                    underlying.append(f'/dev/{clean_name}')

    # If lsblk didn't work, try dmsetup for LVM
    if not underlying and device.startswith('/dev/dm-'):
        out = run_cmd(["sudo", "dmsetup", "deps", "-o", "devname", device], check=False)
        if out.returncode == 0:
            # Parse output like: 1 dependencies	: (sda1)
            for line in out.stdout.splitlines():
                if 'dependencies' in line and ':' in line:
                    deps_part = line.split(':', 1)[1]
                    # Extract device names from parentheses
                    matches = re.findall(r'\(([^)]+)\)', deps_part)
                    for match in matches:
                        underlying.append(f'/dev/{match}')

    return underlying


def get_base_device(device: str) -> str:
    """Get base device (remove partition number)"""
    # For NVMe: /dev/nvme0n1p1 -> /dev/nvme0n1
    # For SCSI: /dev/sda1 -> /dev/sda

    if 'nvme' in device:
        # Remove partition number (p1, p2, etc.)
        match = re.match(r'(/dev/nvme\d+n\d+)', device)
        if match:
            return match.group(1)
    else:
        # Remove trailing digits
        match = re.match(r'(/dev/[a-z]+)', device)
        if match:
            return match.group(1)

    return device


def get_nvme_info(device: str) -> Dict:
    """Get NVMe device information"""
    info = {
        "device": device,
        "type": "nvme",
        "interface": "NVMe"
    }

    # Get controller info
    out = run_cmd(["sudo", "nvme", "id-ctrl", device, "-H"], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            line_lower = line.lower()
            if "model" in line_lower or "mn" in line_lower:
                if ":" in line:
                    info["model"] = line.split(":", 1)[1].strip()
            if "serial" in line_lower or "sn" in line_lower:
                if ":" in line:
                    info["serial"] = line.split(":", 1)[1].strip()
            if "frmw" in line_lower or "firmware" in line_lower:
                if ":" in line:
                    info["firmware"] = line.split(":", 1)[1].strip()

    # Get SMART info
    out = run_cmd(["sudo", "nvme", "smart-log", device], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            line_lower = line.lower()
            if "temperature" in line_lower and ":" in line:
                info["temperature"] = line.split(":", 1)[1].strip()
            if "percentage used" in line_lower and ":" in line:
                info["wear"] = line.split(":", 1)[1].strip()
            if "data_units_written" in line_lower and ":" in line:
                info["data_written"] = line.split(":", 1)[1].strip()

    # Get power state
    out = run_cmd(["sudo", "nvme", "get-feature", device, "-f", "0x02", "-H"], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            if "Power State" in line and ":" in line:
                info["power_state"] = line.split(":", 1)[1].strip()

    # Get namespace info
    out = run_cmd(["sudo", "nvme", "id-ns", device, "-H"], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            line_lower = line.lower()
            if "nsze" in line_lower or "size" in line_lower:
                if ":" in line:
                    info["capacity"] = line.split(":", 1)[1].strip()

    return info


def get_scsi_info(device: str) -> Dict:
    """Get SCSI/SATA device information using hdparm and smartctl"""
    info = {
        "device": device,
        "type": "scsi",
        "interface": "SATA/SAS"
    }

    # Try hdparm for basic info
    out = run_cmd(["sudo", "hdparm", "-I", device], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.startswith("Model Number:"):
                info["model"] = line.split(":", 1)[1].strip()
            elif line.startswith("Serial Number:"):
                info["serial"] = line.split(":", 1)[1].strip()
            elif line.startswith("Firmware Revision:"):
                info["firmware"] = line.split(":", 1)[1].strip()

    # Try smartctl for more detailed info
    out = run_cmd(["sudo", "smartctl", "-i", device], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.startswith("Device Model:") or line.startswith("Model Family:"):
                if "model" not in info:
                    info["model"] = line.split(":", 1)[1].strip()
            elif line.startswith("Serial Number:"):
                if "serial" not in info:
                    info["serial"] = line.split(":", 1)[1].strip()
            elif line.startswith("Firmware Version:"):
                if "firmware" not in info:
                    info["firmware"] = line.split(":", 1)[1].strip()
            elif line.startswith("Rotation Rate:"):
                rotation = line.split(":", 1)[1].strip()
                info["rotation_rate"] = rotation
                if "Solid State Device" in rotation or "0" in rotation:
                    info["media_type"] = "SSD"
                else:
                    info["media_type"] = "HDD"
            elif line.startswith("User Capacity:"):
                info["capacity"] = line.split(":", 1)[1].strip()

    # Get SMART health
    out = run_cmd(["sudo", "smartctl", "-H", device], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            if "SMART overall-health" in line:
                info["health"] = line.split(":", 1)[1].strip()

    # Get temperature
    out = run_cmd(["sudo", "smartctl", "-A", device], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            if "Temperature" in line or "Airflow_Temperature" in line:
                parts = line.split()
                if len(parts) >= 10:
                    info["temperature"] = f"{parts[9]}°C"
                break

    return info


def get_network_info(device: str, mount_point: str) -> Dict:
    """Get network filesystem information"""
    info = {
        "device": device,
        "type": "network",
        "mount_point": mount_point
    }

    # Parse device for NFS info
    if ':' in device:
        parts = device.split(':')
        info["server"] = parts[0]
        info["export"] = parts[1] if len(parts) > 1 else ""
        info["protocol"] = "NFS"
    elif device.startswith('//'):
        info["protocol"] = "CIFS/SMB"
        info["share"] = device

    # Get mount options
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4 and parts[1] == mount_point:
                    info["filesystem"] = parts[2]
                    info["options"] = parts[3]
                    break
    except:
        pass

    # Try to ping server if NFS
    if "server" in info:
        out = run_cmd(["ping", "-c", "1", "-W", "1", info["server"]], check=False)
        info["server_reachable"] = out.returncode == 0

        # Try to get server stats
        out = run_cmd(["nfsstat", "-m"], check=False)
        if out.returncode == 0:
            capture = False
            for line in out.stdout.splitlines():
                if mount_point in line:
                    capture = True
                elif capture:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        info[key.strip().lower().replace(" ", "_")] = value.strip()
                    elif line.strip() == "":
                        break

    return info


def get_lvm_info(device: str) -> Dict:
    """Get LVM/device mapper information"""
    info = {
        "device": device,
        "type": "lvm",
        "interface": "LVM/Device Mapper"
    }

    # Get LVM volume info
    out = run_cmd(["sudo", "lvdisplay", device], check=False)
    if out.returncode == 0:
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.startswith("LV Name"):
                info["lv_name"] = line.split(None, 2)[2] if len(line.split(None, 2)) > 2 else ""
            elif line.startswith("VG Name"):
                info["vg_name"] = line.split(None, 2)[2] if len(line.split(None, 2)) > 2 else ""
            elif line.startswith("LV Size"):
                info["capacity"] = line.split(None, 2)[2] if len(line.split(None, 2)) > 2 else ""

    # Get underlying devices
    underlying = get_underlying_devices(device)
    if underlying:
        info["underlying_devices"] = underlying
        info["num_underlying"] = len(underlying)

        # Try to get info from first underlying device
        if len(underlying) > 0:
            base_dev = get_base_device(underlying[0])
            base_type = get_device_type(base_dev)

            if base_type == "nvme":
                physical_info = get_nvme_info(base_dev)
            elif base_type == "scsi":
                physical_info = get_scsi_info(base_dev)
            else:
                physical_info = {}

            # Add physical device info with prefix
            for key, value in physical_info.items():
                if key not in ["device", "type", "interface"]:
                    info[f"physical_{key}"] = value

            # Copy important fields directly
            if "model" in physical_info:
                info["model"] = physical_info["model"]
            if "media_type" in physical_info:
                info["media_type"] = physical_info["media_type"]

    return info


def get_device_info(path: str) -> Dict:
    """
    Get comprehensive device information for a filesystem path

    Args:
        path: Filesystem path to analyze

    Returns:
        Dictionary with device information
    """
    result = {
        "path": os.path.abspath(path),
        "exists": os.path.exists(path)
    }

    if not result["exists"]:
        result["error"] = "Path does not exist"
        return result

    # Find device and mount point
    device, mount_point = get_device_from_path(path)
    result["mount_point"] = mount_point
    result["device"] = device

    if not device:
        result["error"] = "Could not determine device"
        return result

    # Determine device type
    dev_type = get_device_type(device)
    result["device_type"] = dev_type

    # Get detailed info based on type
    if dev_type == "nvme":
        base_device = get_base_device(device)
        result.update(get_nvme_info(base_device))
    elif dev_type == "scsi":
        base_device = get_base_device(device)
        result.update(get_scsi_info(base_device))
    elif dev_type == "lvm":
        result.update(get_lvm_info(device))
    elif dev_type == "network":
        result.update(get_network_info(device, mount_point))
    else:
        result["info"] = f"Device type {dev_type} - detailed info not available"

    # Get filesystem info
    try:
        stat = os.statvfs(path)
        result["filesystem_info"] = {
            "block_size": stat.f_bsize,
            "total_blocks": stat.f_blocks,
            "free_blocks": stat.f_bfree,
            "available_blocks": stat.f_bavail,
            "total_size_gb": (stat.f_blocks * stat.f_frsize) / (1024**3),
            "free_size_gb": (stat.f_bfree * stat.f_frsize) / (1024**3),
            "used_percent": 100 * (1 - stat.f_bavail / stat.f_blocks) if stat.f_blocks > 0 else 0
        }
    except Exception as e:
        result["filesystem_info"] = {"error": str(e)}

    return result


def print_device_info(info: Dict, verbose: bool = False):
    """Pretty print device information"""
    print(f"\n{'='*70}")
    print(f"Device Information")
    print(f"{'='*70}\n")

    print(f"Path:         {info.get('path', 'N/A')}")
    print(f"Mount Point:  {info.get('mount_point', 'N/A')}")
    print(f"Device:       {info.get('device', 'N/A')}")
    print(f"Device Type:  {info.get('device_type', 'N/A')}")

    if "error" in info:
        print(f"\nError: {info['error']}")
        return

    print()

    # Device-specific info
    if info.get('device_type') == 'nvme' or info.get('device_type') == 'scsi':
        if "model" in info:
            print(f"Model:        {info['model']}")
        if "serial" in info:
            print(f"Serial:       {info['serial']}")
        if "firmware" in info:
            print(f"Firmware:     {info['firmware']}")
        if "capacity" in info:
            print(f"Capacity:     {info['capacity']}")
        if "media_type" in info:
            print(f"Media Type:   {info['media_type']}")
        if "temperature" in info:
            print(f"Temperature:  {info['temperature']}")
        if "wear" in info:
            print(f"Wear Level:   {info['wear']}")
        if "health" in info:
            print(f"Health:       {info['health']}")

    elif info.get('device_type') == 'lvm':
        if "lv_name" in info:
            print(f"LV Name:      {info['lv_name']}")
        if "vg_name" in info:
            print(f"VG Name:      {info['vg_name']}")
        if "capacity" in info:
            print(f"Capacity:     {info['capacity']}")
        if "underlying_devices" in info:
            print(f"Physical Devs: {', '.join(info['underlying_devices'])}")
        print()
        if "model" in info:
            print(f"Physical Model:     {info['model']}")
        if "media_type" in info:
            print(f"Physical Type:      {info['media_type']}")
        if "physical_temperature" in info:
            print(f"Physical Temp:      {info['physical_temperature']}")
        if "physical_health" in info:
            print(f"Physical Health:    {info['physical_health']}")

    elif info.get('device_type') == 'network':
        if "protocol" in info:
            print(f"Protocol:     {info['protocol']}")
        if "server" in info:
            print(f"Server:       {info['server']}")
        if "export" in info:
            print(f"Export:       {info['export']}")
        if "server_reachable" in info:
            status = "Yes" if info['server_reachable'] else "No"
            print(f"Reachable:    {status}")
        if "options" in info:
            print(f"Mount Opts:   {info['options']}")

    # Filesystem info
    if "filesystem_info" in info and "error" not in info["filesystem_info"]:
        fs = info["filesystem_info"]
        print(f"\nFilesystem:")
        print(f"  Total Size:   {fs['total_size_gb']:.2f} GB")
        print(f"  Free Space:   {fs['free_size_gb']:.2f} GB")
        print(f"  Used:         {fs['used_percent']:.1f}%")
        print(f"  Block Size:   {fs['block_size']} bytes")

    if verbose:
        print(f"\n{'='*70}")
        print("Full Details:")
        print(f"{'='*70}\n")
        import json
        print(json.dumps(info, indent=2))

    print(f"\n{'='*70}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Discover and gather information about storage devices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /tmp/local-ssd
  %(prog)s /mnt/nfs --verbose
  %(prog)s /dev/nvme0n1 --json
        """
    )

    parser.add_argument('path', help='Filesystem path or device to analyze')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show all details')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    # Get device info
    info = get_device_info(args.path)

    if args.json:
        import json
        print(json.dumps(info, indent=2))
    else:
        print_device_info(info, verbose=args.verbose)


if __name__ == "__main__":
    main()
