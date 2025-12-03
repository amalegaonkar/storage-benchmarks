# GDS Crash Debugging Guide

This guide helps debug system crashes during GDS (GPU Direct Storage) tests.

## Quick Debug Collection

Run the debug script to collect all diagnostic information:

```bash
./nixlbench/debug_gds_crash.sh
```

Or use the suite command:
```bash
./nixlbench/nixlbench_suite.sh debug
```

This collects:
- System information (kernel, OS, uptime)
- GPU status and memory usage
- Kernel messages (dmesg)
- System logs (journalctl)
- Kernel module status
- Memory information
- CPU information
- Storage information
- Running processes
- Crash indicators (oops, panic, segfault)

Output is saved to `debug_output/` directory with timestamps.

## Real-time Monitoring

Monitor system during GDS test execution:

**Terminal 1** - Run the test:
```bash
./nixlbench/nixlbench_suite.sh gds-safe /tmp/nvme_raid0/
```

**Terminal 2** - Monitor in real-time:
```bash
./nixlbench/monitor_gds_test.sh
```

Or manually monitor:
```bash
# Watch GPU status
watch -n 1 nvidia-smi

# Watch kernel messages
watch -n 1 'dmesg | tail -20'

# Combined monitoring
watch -n 1 'nvidia-smi; echo; dmesg | tail -10'
```

## Key Things to Check

### 1. Kernel Messages (dmesg)

**Check for errors:**
```bash
dmesg | tail -100 | grep -i "error\|fail\|crash\|panic\|oops"
```

**Check for GDS/NVIDIA issues:**
```bash
dmesg | grep -i "nvidia\|gds\|nvfs" | tail -50
```

**Check for out-of-memory:**
```bash
dmesg | grep -i "out of memory\|oom"
```

**Common crash signatures:**
- `BUG:` - Kernel bug detected
- `Oops:` - Kernel oops (non-fatal error)
- `Kernel panic` - Fatal kernel error
- `segfault` - Segmentation fault
- `Out of memory` - OOM killer activated

### 2. GPU Memory

**Check GPU memory usage:**
```bash
nvidia-smi
```

**Check for GPU memory leaks:**
```bash
# Before test
nvidia-smi --query-gpu=memory.used --format=csv,noheader

# During/after test - compare values
```

**Warning signs:**
- GPU memory usage > 90%
- Memory not being freed after test
- Multiple nixlbench processes holding GPU memory

### 3. System Memory

**Check system memory:**
```bash
free -h
cat /proc/meminfo | grep -i "memavailable\|memfree"
```

**Check for OOM kills:**
```bash
dmesg | grep -i "out of memory\|oom"
grep -i "killed process" /var/log/syslog 2>/dev/null | tail -20
```

### 4. Kernel Module Status

**Check GDS module:**
```bash
lsmod | grep nvidia_fs
modinfo nvidia_fs
```

**Check NVIDIA modules:**
```bash
lsmod | grep nvidia
```

### 5. Process Status

**Check for hung processes:**
```bash
ps aux | grep nixlbench
nvidia-smi pmon -c 1
```

**Check process memory:**
```bash
ps aux --sort=-%mem | head -10
```

## Common Crash Causes

### 1. GPU Memory Exhaustion
**Symptoms:**
- GPU memory usage near 100%
- Test hangs then system becomes unresponsive
- dmesg shows GPU-related errors

**Debug:**
```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
dmesg | grep -i "gpu\|nvidia" | grep -i "error\|fail"
```

**Solution:**
- Reduce buffer size (`--total_buffer_size`)
- Reduce number of threads (`--num_threads`)
- Use smaller test first to verify stability

### 2. Kernel Oops/Panic
**Symptoms:**
- System crash/reboot
- dmesg shows "BUG:" or "Kernel panic"
- System becomes unresponsive

**Debug:**
```bash
dmesg | grep -i "bug\|panic\|oops" | tail -50
```

**Solution:**
- Check kernel version compatibility
- Update NVIDIA driver
- Check for known GDS bugs in your kernel version
- Reduce test intensity

### 3. Out of Memory (OOM)
**Symptoms:**
- System becomes slow then unresponsive
- dmesg shows "Out of memory"
- Processes killed

**Debug:**
```bash
dmesg | grep -i "out of memory\|oom"
free -h
```

**Solution:**
- Reduce buffer sizes
- Close other applications
- Add swap space (if needed)
- Reduce test concurrency

### 4. GDS Module Issues
**Symptoms:**
- Test hangs immediately
- No GPU memory allocation
- Errors about GDS/NVFS

**Debug:**
```bash
lsmod | grep nvidia_fs
dmesg | grep -i "nvfs\|gds"
modinfo nvidia_fs
```

**Solution:**
- Reload GDS module: `sudo modprobe -r nvidia_fs && sudo modprobe nvidia_fs`
- Check module compatibility with driver
- Verify storage hardware supports GDS

## Debugging Workflow

### Before Test
1. **Collect baseline diagnostics:**
   ```bash
   ./nixlbench/debug_gds_crash.sh
   ```

2. **Check system state:**
   ```bash
   nvidia-smi
   free -h
   lsmod | grep nvidia_fs
   ```

3. **Clear kernel ring buffer (optional):**
   ```bash
   sudo dmesg -C  # Clear dmesg (be careful - loses history)
   ```

### During Test
1. **Run monitor in separate terminal:**
   ```bash
   ./nixlbench/monitor_gds_test.sh
   ```

2. **Or manually watch:**
   ```bash
   watch -n 1 'nvidia-smi; echo; dmesg | tail -10'
   ```

### After Crash
1. **Collect post-crash diagnostics:**
   ```bash
   ./nixlbench/debug_gds_crash.sh
   ```

2. **Check kernel messages:**
   ```bash
   dmesg | tail -200 > crash_dmesg.txt
   dmesg | grep -i "error\|fail\|crash\|panic" > crash_errors.txt
   ```

3. **Check GPU state:**
   ```bash
   nvidia-smi > gpu_after_crash.txt
   ```

4. **Review collected files:**
   ```bash
   ls -lh debug_output/
   cat debug_output/SUMMARY_*.txt
   cat debug_output/crash_indicators_*.txt
   ```

## Analyzing Crash Logs

### Check for Patterns

**GPU-related crashes:**
```bash
grep -i "gpu\|nvidia\|cuda" debug_output/dmesg_*.txt | grep -i "error\|fail"
```

**Memory-related crashes:**
```bash
grep -i "memory\|oom\|out of" debug_output/dmesg_*.txt
```

**Kernel bugs:**
```bash
grep -i "bug\|panic\|oops" debug_output/dmesg_*.txt
```

### Compare Before/After

If you collected diagnostics before the test:
```bash
# Compare GPU memory
diff debug_output/gpu_info_before.txt debug_output/gpu_info_after.txt

# Compare kernel modules
diff debug_output/kernel_modules_before.txt debug_output/kernel_modules_after.txt
```

## Prevention Strategies

1. **Start with safe tests:**
   ```bash
   ./nixlbench/nixlbench_suite.sh gds-safe
   ```

2. **Monitor resources:**
   - Keep GPU memory usage < 80%
   - Monitor system memory
   - Watch for kernel errors

3. **Reduce test intensity:**
   - Lower buffer sizes
   - Fewer threads
   - Shorter test duration

4. **Isolate test environment:**
   - Close other GPU applications
   - Stop unnecessary services
   - Use dedicated test system if possible

## Reporting Issues

When reporting crashes, include:

1. **Debug output:**
   ```bash
   ./nixlbench/debug_gds_crash.sh
   tar czf debug_output.tar.gz debug_output/
   ```

2. **Test configuration:**
   - Command used
   - Buffer sizes
   - Number of threads/files
   - Backend type

3. **System information:**
   - Kernel version
   - NVIDIA driver version
   - GPU model
   - CUDA version

4. **Crash details:**
   - When it crashed (during which test)
   - System behavior (hang, reboot, error message)
   - Last kernel messages

## Useful Commands Reference

```bash
# Kernel messages
dmesg | tail -100                    # Last 100 kernel messages
dmesg | grep -i error                # Errors only
dmesg -T | tail -50                  # With timestamps

# GPU monitoring
nvidia-smi                           # Full GPU status
nvidia-smi -l 1                      # Continuous monitoring
nvidia-smi pmon -c 1                 # Process monitoring

# System resources
free -h                              # Memory
top                                  # CPU/memory usage
iostat -x 1                          # I/O statistics

# Process monitoring
ps aux | grep nixlbench              # nixlbench processes
pstree -p                            # Process tree
```

## Emergency Recovery

If system becomes unresponsive:

1. **Try to get shell access:**
   - SSH (if available)
   - Console access
   - Magic SysRq keys (if enabled)

2. **Kill hung processes:**
   ```bash
   pkill -9 nixlbench
   ```

3. **Free GPU memory:**
   ```bash
   # May require killing processes holding GPU memory
   nvidia-smi --gpu-reset  # Reset GPU (if supported)
   ```

4. **Reboot if necessary:**
   ```bash
   sudo reboot
   ```

5. **After reboot, collect crash logs:**
   ```bash
   # Kernel messages may be in /var/log/kern.log
   sudo tail -200 /var/log/kern.log
   
   # Or check journalctl
   sudo journalctl -k -n 200
   ```

