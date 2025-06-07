#!/usr/bin/env python3
"""
TrackPro Startup Performance Benchmark
======================================

This script measures TrackPro's startup performance and provides detailed timing information.
Run this script to verify the performance improvements.

Usage:
    python benchmark_startup.py [--runs=5] [--detailed]
"""

import time
import sys
import os
import subprocess
import argparse
import statistics
from datetime import datetime

def measure_startup_time(run_number=1, detailed=False):
    """Measure the time it takes for TrackPro to start up."""
    print(f"\n--- Run {run_number} ---")
    
    # Record start time
    start_time = time.time()
    
    try:
        # Start TrackPro process
        if detailed:
            print("Starting TrackPro process...")
            
        # Use a timeout to prevent hanging
        process = subprocess.Popen(
            [sys.executable, "run_app.py", "--dev"],  # Use dev mode to allow multiple instances
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for process to start (look for specific output indicating startup)
        startup_detected = False
        ui_ready_time = None
        full_startup_time = None
        
        while True:
            # Check if process is still running
            if process.poll() is not None:
                break
                
            # Read output line by line
            try:
                line = process.stdout.readline()
                if line:
                    if detailed:
                        print(f"  {line.strip()}")
                    
                    # Look for UI ready indicator
                    if "Creating interface..." in line and ui_ready_time is None:
                        ui_ready_time = time.time() - start_time
                        if detailed:
                            print(f"  ** UI Creation Started: {ui_ready_time:.3f}s")
                    
                    # Look for startup complete indicator
                    if "Core initialization complete" in line and full_startup_time is None:
                        full_startup_time = time.time() - start_time
                        if detailed:
                            print(f"  ** Core Startup Complete: {full_startup_time:.3f}s")
                        startup_detected = True
                        break
                        
                # Timeout after 60 seconds
                if time.time() - start_time > 60:
                    print("  ERROR: Startup timeout (60s)")
                    break
                    
            except Exception as e:
                if detailed:
                    print(f"  Error reading output: {e}")
                break
        
        # Terminate the process
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        
        total_time = time.time() - start_time
        
        return {
            'total_time': total_time,
            'ui_ready_time': ui_ready_time,
            'core_complete_time': full_startup_time,
            'startup_detected': startup_detected
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            'total_time': None,
            'ui_ready_time': None,
            'core_complete_time': None,
            'startup_detected': False
        }

def run_benchmark(num_runs=5, detailed=False):
    """Run the startup benchmark multiple times and calculate statistics."""
    print("TrackPro Startup Performance Benchmark")
    print("=" * 40)
    print(f"Timestamp: {datetime.now()}")
    print(f"Number of runs: {num_runs}")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    # Check if TrackPro exists
    if not os.path.exists("run_app.py"):
        print("\nERROR: run_app.py not found. Please run this script from the TrackPro directory.")
        return
    
    print("\nStarting benchmark runs...")
    
    results = []
    ui_times = []
    core_times = []
    total_times = []
    
    for i in range(num_runs):
        result = measure_startup_time(i + 1, detailed)
        results.append(result)
        
        if result['ui_ready_time']:
            ui_times.append(result['ui_ready_time'])
        if result['core_complete_time']:
            core_times.append(result['core_complete_time'])
        if result['total_time']:
            total_times.append(result['total_time'])
        
        # Brief pause between runs
        time.sleep(2)
    
    # Calculate statistics
    print("\n" + "=" * 40)
    print("BENCHMARK RESULTS")
    print("=" * 40)
    
    if ui_times:
        print(f"\nUI Ready Time:")
        print(f"  Average: {statistics.mean(ui_times):.3f}s")
        print(f"  Median:  {statistics.median(ui_times):.3f}s")
        print(f"  Min:     {min(ui_times):.3f}s")
        print(f"  Max:     {max(ui_times):.3f}s")
        if len(ui_times) > 1:
            print(f"  StdDev:  {statistics.stdev(ui_times):.3f}s")
    
    if core_times:
        print(f"\nCore Startup Time:")
        print(f"  Average: {statistics.mean(core_times):.3f}s")
        print(f"  Median:  {statistics.median(core_times):.3f}s")
        print(f"  Min:     {min(core_times):.3f}s")
        print(f"  Max:     {max(core_times):.3f}s")
        if len(core_times) > 1:
            print(f"  StdDev:  {statistics.stdev(core_times):.3f}s")
    
    if total_times:
        print(f"\nTotal Process Time:")
        print(f"  Average: {statistics.mean(total_times):.3f}s")
        print(f"  Median:  {statistics.median(total_times):.3f}s")
        print(f"  Min:     {min(total_times):.3f}s")
        print(f"  Max:     {max(total_times):.3f}s")
        if len(total_times) > 1:
            print(f"  StdDev:  {statistics.stdev(total_times):.3f}s")
    
    # Success rate
    successful_runs = sum(1 for r in results if r['startup_detected'])
    success_rate = (successful_runs / num_runs) * 100
    print(f"\nSuccess Rate: {successful_runs}/{num_runs} ({success_rate:.1f}%)")
    
    # Performance assessment
    print(f"\nPERFORMANCE ASSESSMENT:")
    if core_times:
        avg_core_time = statistics.mean(core_times)
        if avg_core_time < 3:
            print("  ✅ EXCELLENT - Core startup under 3 seconds")
        elif avg_core_time < 5:
            print("  ✅ GOOD - Core startup under 5 seconds")
        elif avg_core_time < 10:
            print("  ⚠️  ACCEPTABLE - Core startup under 10 seconds")
        else:
            print("  ❌ POOR - Core startup over 10 seconds")
    
    if ui_times:
        avg_ui_time = statistics.mean(ui_times)
        if avg_ui_time < 1:
            print("  ✅ EXCELLENT - UI ready under 1 second")
        elif avg_ui_time < 2:
            print("  ✅ GOOD - UI ready under 2 seconds")
        elif avg_ui_time < 5:
            print("  ⚠️  ACCEPTABLE - UI ready under 5 seconds")
        else:
            print("  ❌ POOR - UI ready over 5 seconds")
    
    print("\nBenchmark complete!")

def main():
    """Main function to parse arguments and run benchmark."""
    parser = argparse.ArgumentParser(description='Benchmark TrackPro startup performance')
    parser.add_argument('--runs', type=int, default=5, help='Number of runs to perform (default: 5)')
    parser.add_argument('--detailed', action='store_true', help='Show detailed output during runs')
    
    args = parser.parse_args()
    
    run_benchmark(args.runs, args.detailed)

if __name__ == "__main__":
    main() 