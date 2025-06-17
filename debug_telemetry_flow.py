#!/usr/bin/env python3
"""
Monitor telemetry flow while TrackPro is running.
This script connects to the running TrackPro instance to debug the AI coaching issues.
"""

import time
import logging
import os
import sys
from datetime import datetime

def monitor_log_file():
    """Monitor the TrackPro log file for debug messages."""
    
    # Find the most recent log file
    log_dir = os.path.expanduser("~/Documents/TrackPro_Logs")
    if not os.path.exists(log_dir):
        print(f"❌ Log directory not found: {log_dir}")
        return
    
    # Get the most recent log file
    log_files = [f for f in os.listdir(log_dir) if f.startswith("trackpro_startup_")]
    if not log_files:
        print(f"❌ No log files found in {log_dir}")
        return
    
    log_files.sort(reverse=True)
    latest_log = os.path.join(log_dir, log_files[0])
    
    print(f"📊 Monitoring log file: {latest_log}")
    print("="*80)
    print("🔍 Looking for:")
    print("   - [AI DEBUG] messages from unified telemetry callback")
    print("   - AI coaching start/stop messages")  
    print("   - Telemetry callback counts")
    print("   - SDK instance conflicts")
    print("="*80)
    
    # Monitor the file
    with open(latest_log, 'r', encoding='utf-8') as f:
        # Go to end of file
        f.seek(0, 2)
        
        print(f"🔄 Monitoring started at {datetime.now().strftime('%H:%M:%S')}")
        print("   Waiting for telemetry debug messages...")
        print("   (Enable AI coach to see debug output)")
        
        while True:
            line = f.readline()
            if line:
                # Filter for important debug messages
                if any(keyword in line for keyword in [
                    '[AI DEBUG]', 
                    'AI COACH START', 
                    'AI COACH STOP',
                    'UNIFIED TELEMETRY',
                    'ir.startup',
                    'Multiple SDK',
                    'telemetry_callbacks',
                    'add_telemetry_point'
                ]):
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] {line.strip()}")
                    
                # Also catch any errors
                elif any(keyword in line for keyword in ['ERROR', 'CRITICAL', 'Exception']):
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"🚨 [{timestamp}] {line.strip()}")
            else:
                time.sleep(0.1)

def check_running_processes():
    """Check for multiple iRacing SDK processes."""
    import psutil
    
    print("\n🔍 Checking for potential SDK conflicts:")
    print("-" * 50)
    
    trackpro_processes = []
    iracing_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'trackpro' in cmdline.lower() or 'run_app.py' in cmdline:
                    trackpro_processes.append(f"PID {proc.info['pid']}: {cmdline}")
            
            if 'iracing' in proc.info['name'].lower():
                iracing_processes.append(f"PID {proc.info['pid']}: {proc.info['name']}")
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print(f"📊 TrackPro processes: {len(trackpro_processes)}")
    for proc in trackpro_processes:
        print(f"   {proc}")
    
    print(f"🏁 iRacing processes: {len(iracing_processes)}")
    for proc in iracing_processes:
        print(f"   {proc}")
    
    if len(trackpro_processes) > 1:
        print("⚠️  WARNING: Multiple TrackPro processes detected!")
    
    return len(trackpro_processes), len(iracing_processes)

def main():
    """Main debugging function."""
    print("🔍 TRACKPRO TELEMETRY FLOW DEBUGGER")
    print("=" * 60)
    
    # Check processes first
    tp_count, ir_count = check_running_processes()
    
    if tp_count == 0:
        print("\n❌ No TrackPro processes found. Please start TrackPro first.")
        return
    
    if ir_count == 0:
        print("\n⚠️  No iRacing processes found. Start iRacing and get on track for telemetry.")
    
    print(f"\n✅ Found {tp_count} TrackPro process(es) and {ir_count} iRacing process(es)")
    
    # Start monitoring
    try:
        monitor_log_file()
    except KeyboardInterrupt:
        print(f"\n🛑 Monitoring stopped at {datetime.now().strftime('%H:%M:%S')}")
    except FileNotFoundError as e:
        print(f"\n❌ Could not find log file: {e}")
        print("Make sure TrackPro is running and logging is enabled.")

if __name__ == "__main__":
    main() 