#!/usr/bin/env python3
"""
Plot FIO Complete File Read Benchmark Results
Shows total time to read entire file
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import argparse


def convert_bytes_to_readable(bytes_val):
    """Convert bytes to human readable format"""
    if bytes_val < 1024:
        return f"{bytes_val}B"
    elif bytes_val < 1024**2:
        return f"{bytes_val/1024:.0f}KB"
    elif bytes_val < 1024**3:
        return f"{bytes_val/1024**2:.0f}MB"
    else:
        return f"{bytes_val/1024**3:.1f}GB"


def plot_total_time_comparison(df, output_prefix=""):
    """Plot total time to read complete file"""
    from matplotlib.ticker import FuncFormatter

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    storage_types = df['StorageType'].unique()

    for idx, storage_type in enumerate(storage_types):
        ax = ax1 if idx == 0 else ax2
        storage_df = df[df['StorageType'] == storage_type].copy()

        # Plot each IO mode with different queue depths
        for io_mode in storage_df['IOMode'].unique():
            for io_depth in sorted(storage_df['IODepth'].unique()):
                mode_df = storage_df[
                    (storage_df['IOMode'] == io_mode) &
                    (storage_df['IODepth'] == io_depth)
                ].sort_values('Bytes')

                label = f"{io_mode}_qd{io_depth}"
                ax.plot(mode_df['Bytes'], mode_df['TotalTime_s'],
                       marker='o', linewidth=2, markersize=8, label=label)

        ax.set_xlabel('File Size', fontsize=12, fontweight='bold')
        
        # Determine best time unit based on data range
        # Prefer milliseconds/microseconds over seconds for better readability
        time_values = storage_df['TotalTime_s'].values
        max_time = np.max(time_values)
        min_time = np.min(time_values[time_values > 0])
        
        if max_time < 0.001:  # All times < 1ms, use microseconds
            time_unit = 'microseconds'
            time_multiplier = 1e6
            ax.set_ylabel('Total Time to Read File (μs)', fontsize=12, fontweight='bold')
            
            def format_time(x, pos):
                """Format y-axis in microseconds"""
                if x == 0:
                    return '0'
                val = x * time_multiplier
                if val >= 1000:
                    return f'{val/1000:.1f}ms'
                elif val >= 100:
                    return f'{val:.0f}μs'
                elif val >= 10:
                    return f'{val:.1f}μs'
                else:
                    return f'{val:.2f}μs'
        elif max_time < 10:  # Times < 10s, use milliseconds (preferred)
            time_unit = 'milliseconds'
            time_multiplier = 1e3
            ax.set_ylabel('Total Time to Read File (ms)', fontsize=12, fontweight='bold')
            
            def format_time(x, pos):
                """Format y-axis in milliseconds"""
                if x == 0:
                    return '0'
                val = x * time_multiplier
                if val >= 1000:
                    return f'{val/1000:.2f}s'
                elif val >= 100:
                    return f'{val:.0f}ms'
                elif val >= 10:
                    return f'{val:.1f}ms'
                else:
                    return f'{val:.2f}ms'
        else:  # Very large times, use seconds but show ms for small values
            time_unit = 'mixed'
            ax.set_ylabel('Total Time to Read File', fontsize=12, fontweight='bold')
            
            def format_time(x, pos):
                """Format y-axis with automatic unit selection"""
                if x == 0:
                    return '0'
                if x >= 1:
                    return f'{x:.1f}s'
                elif x >= 0.001:
                    return f'{x*1000:.0f}ms'
                else:
                    return f'{x*1e6:.0f}μs'
        
        ax.set_title(f'{storage_type}: Time to Read Complete File', fontsize=14, fontweight='bold')
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.yaxis.set_major_formatter(FuncFormatter(format_time))

        ax.grid(True, alpha=0.3, which='both', linestyle='--')
        ax.legend(fontsize=10, loc='best')

        xticks = sorted(storage_df['Bytes'].unique())
        ax.set_xticks(xticks)
        ax.set_xticklabels([convert_bytes_to_readable(x) for x in xticks], rotation=45)

    plt.tight_layout()
    filename = f"{output_prefix}fio_total_time.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename}")
    plt.close()

def plot_bandwidth_comparison(df, output_prefix=""):
    """Plot bandwidth across file sizes"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    storage_types = df['StorageType'].unique()

    for idx, storage_type in enumerate(storage_types):
        ax = ax1 if idx == 0 else ax2
        storage_df = df[df['StorageType'] == storage_type].copy()

        for io_mode in storage_df['IOMode'].unique():
            for io_depth in sorted(storage_df['IODepth'].unique()):
                mode_df = storage_df[
                    (storage_df['IOMode'] == io_mode) &
                    (storage_df['IODepth'] == io_depth)
                ].sort_values('Bytes')

                label = f"{io_mode}_qd{io_depth}"
                ax.plot(mode_df['Bytes'], mode_df['BW_MBps'],
                       marker='o', linewidth=2, markersize=8, label=label)

        ax.set_xlabel('File Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('Bandwidth (MB/s)', fontsize=12, fontweight='bold')
        ax.set_title(f'{storage_type}: Bandwidth vs File Size', fontsize=14, fontweight='bold')
        ax.set_xscale('log')
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3, which='both', linestyle='--')
        ax.legend(fontsize=10, loc='best')

        xticks = sorted(storage_df['Bytes'].unique())
        ax.set_xticks(xticks)
        ax.set_xticklabels([convert_bytes_to_readable(x) for x in xticks], rotation=45)

    plt.tight_layout()
    filename = f"{output_prefix}fio_bandwidth.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename}")
    plt.close()


def plot_iops_comparison(df, output_prefix=""):
    """Plot IOPS across file sizes"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    storage_types = df['StorageType'].unique()

    for idx, storage_type in enumerate(storage_types):
        ax = ax1 if idx == 0 else ax2
        storage_df = df[df['StorageType'] == storage_type].copy()

        for io_mode in storage_df['IOMode'].unique():
            for io_depth in sorted(storage_df['IODepth'].unique()):
                mode_df = storage_df[
                    (storage_df['IOMode'] == io_mode) &
                    (storage_df['IODepth'] == io_depth)
                ].sort_values('Bytes')

                label = f"{io_mode}_qd{io_depth}"
                ax.plot(mode_df['Bytes'], mode_df['IOPS'],
                       marker='s', linewidth=2, markersize=8, label=label)

        ax.set_xlabel('File Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('IOPS', fontsize=12, fontweight='bold')
        ax.set_title(f'{storage_type}: IOPS vs File Size', fontsize=14, fontweight='bold')
        ax.set_xscale('log')
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3, which='both', linestyle='--')
        ax.legend(fontsize=10, loc='best')

        xticks = sorted(storage_df['Bytes'].unique())
        ax.set_xticks(xticks)
        ax.set_xticklabels([convert_bytes_to_readable(x) for x in xticks], rotation=45)

    plt.tight_layout()
    filename = f"{output_prefix}fio_iops.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename}")
    plt.close()


def plot_nfs_comparison_bars(df, output_prefix=""):
    """Bar chart comparing direct vs buffered for NFS"""
    nfs_df = df[df['StorageType'].str.contains('NFS', case=False)]

    if nfs_df.empty or len(nfs_df['IOMode'].unique()) < 2:
        print("Skipping NFS comparison (insufficient data)")
        return

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    file_sizes = sorted(nfs_df['Bytes'].unique())
    io_depth = nfs_df['IODepth'].max()

    # Filter for highest queue depth
    plot_df = nfs_df[nfs_df['IODepth'] == io_depth]

    x = np.arange(len(file_sizes))
    width = 0.35

    # Get data for each mode
    direct_time = []
    buffered_time = []
    direct_bw = []
    buffered_bw = []
    direct_iops = []
    buffered_iops = []

    for size in file_sizes:
        # Direct I/O
        direct_data = plot_df[(plot_df['Bytes'] == size) & (plot_df['IOMode'] == 'direct')]
        if len(direct_data) > 0:
            direct_time.append(direct_data['TotalTime_s'].values[0])
            direct_bw.append(direct_data['BW_MBps'].values[0])
            direct_iops.append(direct_data['IOPS'].values[0])
        else:
            direct_time.append(0)
            direct_bw.append(0)
            direct_iops.append(0)

        # Buffered I/O
        buffered_data = plot_df[(plot_df['Bytes'] == size) & (plot_df['IOMode'] == 'buffered')]
        if len(buffered_data) > 0:
            buffered_time.append(buffered_data['TotalTime_s'].values[0])
            buffered_bw.append(buffered_data['BW_MBps'].values[0])
            buffered_iops.append(buffered_data['IOPS'].values[0])
        else:
            buffered_time.append(0)
            buffered_bw.append(0)
            buffered_iops.append(0)

    # Determine best time unit for bar chart
    # Prefer milliseconds/microseconds over seconds
    max_time = max(max(direct_time) if direct_time else 0, max(buffered_time) if buffered_time else 0)
    min_time = min([t for t in direct_time + buffered_time if t > 0]) if any(direct_time + buffered_time) else 0
    
    if max_time < 0.001:  # All times < 1ms, use microseconds
        time_multiplier = 1e6
        time_unit_label = 'Total Time (μs)'
        direct_time_display = [t * time_multiplier for t in direct_time]
        buffered_time_display = [t * time_multiplier for t in buffered_time]
    elif max_time < 10:  # Times < 10s, use milliseconds (preferred)
        time_multiplier = 1e3
        time_unit_label = 'Total Time (ms)'
        direct_time_display = [t * time_multiplier for t in direct_time]
        buffered_time_display = [t * time_multiplier for t in buffered_time]
    else:  # Very large times, use seconds
        time_multiplier = 1
        time_unit_label = 'Total Time (seconds)'
        direct_time_display = direct_time
        buffered_time_display = buffered_time
    
    # Plot 1: Total Time
    axes[0].bar(x - width/2, direct_time_display, width, label='Direct I/O', color='#2E86AB')
    axes[0].bar(x + width/2, buffered_time_display, width, label='Buffered (Cached)', color='#A23B72')
    axes[0].set_xlabel('File Size', fontsize=12, fontweight='bold')
    axes[0].set_ylabel(time_unit_label, fontsize=12, fontweight='bold')
    axes[0].set_title(f'NFS: Time to Read Complete File (qd={io_depth})', fontsize=13, fontweight='bold')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([convert_bytes_to_readable(s) for s in file_sizes], rotation=45, ha='right')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3, axis='y')

    # Plot 2: Bandwidth
    axes[1].bar(x - width/2, direct_bw, width, label='Direct I/O', color='#2E86AB')
    axes[1].bar(x + width/2, buffered_bw, width, label='Buffered (Cached)', color='#A23B72')
    axes[1].set_xlabel('File Size', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Bandwidth (MB/s)', fontsize=12, fontweight='bold')
    axes[1].set_title(f'NFS: Bandwidth Comparison (qd={io_depth})', fontsize=13, fontweight='bold')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([convert_bytes_to_readable(s) for s in file_sizes], rotation=45, ha='right')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3, axis='y')

    # Plot 3: IOPS
    axes[2].bar(x - width/2, direct_iops, width, label='Direct I/O', color='#2E86AB')
    axes[2].bar(x + width/2, buffered_iops, width, label='Buffered (Cached)', color='#A23B72')
    axes[2].set_xlabel('File Size', fontsize=12, fontweight='bold')
    axes[2].set_ylabel('IOPS', fontsize=12, fontweight='bold')
    axes[2].set_title(f'NFS: IOPS Comparison (qd={io_depth})', fontsize=13, fontweight='bold')
    axes[2].set_xticks(x)
    axes[2].set_xticklabels([convert_bytes_to_readable(s) for s in file_sizes], rotation=45, ha='right')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    filename = f"{output_prefix}fio_nfs_comparison.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot FIO complete file read benchmark results')
    parser.add_argument('input_file', help='Input CSV file')
    parser.add_argument('--output-prefix', default='', help='Prefix for output files')

    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input_file)
        print(f"Loaded {len(df)} records from {args.input_file}\n")

        # Filter out errors
        df = df[df['TotalTime_s'] != 'ERROR']
        df['TotalTime_s'] = pd.to_numeric(df['TotalTime_s'])
        df['BW_MBps'] = pd.to_numeric(df['BW_MBps'])
        df['IOPS'] = pd.to_numeric(df['IOPS'])
        df['LatMean_us'] = pd.to_numeric(df['LatMean_us'])

        print(f"{'='*60}")
        print("Generating plots...")
        print(f"{'='*60}\n")

        plot_total_time_comparison(df, args.output_prefix)
        plot_bandwidth_comparison(df, args.output_prefix)
        plot_iops_comparison(df, args.output_prefix)
        plot_nfs_comparison_bars(df, args.output_prefix)

        print(f"\n{'='*60}")
        print("All plots generated!")
        print(f"{'='*60}")

    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
