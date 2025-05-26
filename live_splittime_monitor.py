#!/usr/bin/env python3
"""
Live SplitTimeInfo Monitor for iRacing

This script connects to a live iRacing session and monitors the SplitTimeInfo
section of SessionInfo to detect if it gets updated with actual sector times
after lap completion.

Usage:
1. Start iRacing and join a session
2. Run this script
3. Complete a few laps
4. Check the output for SplitTimeInfo changes

This will answer the research question: Does iRacing update SplitTimeInfo 
with actual sector times after lap completion?
"""

import sys
import os
import time
import json
import yaml
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add the trackpro module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

try:
    from trackpro.race_coach.pyirsdk import irsdk
except ImportError:
    try:
        import irsdk
    except ImportError:
        print("❌ Error: pyirsdk not found. Please install irsdk or ensure trackpro.race_coach.pyirsdk is available.")
        sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SplitTimeMonitor:
    """Monitor SplitTimeInfo for updates during live iRacing session."""
    
    def __init__(self):
        self.ir = irsdk.IRSDK()
        self.last_session_info_hash = None
        self.last_lap_completed = -1
        self.splittime_snapshots = []
        self.sector_time_history = []
        self.is_connected = False
        
        # Monitoring state
        self.monitoring_start_time = time.time()
        self.lap_completion_events = []
        
    def connect(self) -> bool:
        """Connect to iRacing."""
        logger.info("🔌 Connecting to iRacing...")
        
        if self.ir.startup():
            if self.ir.is_connected:
                self.is_connected = True
                logger.info("✅ Connected to iRacing successfully!")
                return True
            else:
                logger.error("❌ iRacing is running but not in a session")
                return False
        else:
            logger.error("❌ iRacing is not running")
            return False
    
    def disconnect(self):
        """Disconnect from iRacing."""
        if self.ir:
            self.ir.shutdown()
        self.is_connected = False
        logger.info("🔌 Disconnected from iRacing")
    
    def _get_session_info_raw(self) -> Optional[str]:
        """Get raw SessionInfo string from iRacing using the correct pyirsdk method."""
        try:
            if not self.ir or not self.ir.is_connected:
                return None
            
            # Method 1: Try _get_session_info_binary to get raw session info
            if hasattr(self.ir, '_get_session_info_binary'):
                try:
                    session_info_binary = self.ir._get_session_info_binary('SessionInfo')
                    if session_info_binary:
                        return session_info_binary.decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.debug(f"_get_session_info_binary failed: {e}")
            
            # Method 2: Try accessing shared memory directly
            if hasattr(self.ir, '_shared_mem') and hasattr(self.ir, '_header'):
                try:
                    header = self.ir._header
                    if header and header.session_info_len > 0:
                        start = header.session_info_offset
                        end = start + header.session_info_len
                        session_info_raw = self.ir._shared_mem[start:end].rstrip(b'\x00').decode('utf-8', errors='ignore')
                        return session_info_raw
                except Exception as e:
                    logger.debug(f"Direct shared memory access failed: {e}")
            
            # Method 3: Try dictionary access (fallback)
            if hasattr(self.ir, '__getitem__'):
                try:
                    session_info = self.ir['SessionInfo']
                    if isinstance(session_info, str):
                        return session_info
                except Exception as e:
                    logger.debug(f"Dictionary access failed: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None
    
    def extract_splittime_info(self, session_info_raw: str) -> Dict[str, Any]:
        """Extract and analyze SplitTimeInfo from SessionInfo."""
        try:
            # Extract YAML content (excluding telemetry data)
            lines = session_info_raw.split('\n')
            yaml_lines = []
            
            for line in lines:
                if not line.strip():
                    yaml_lines.append(line)
                    continue
                
                # Stop at telemetry data (lines with many spaces)
                if '                    ' in line and line.count(' ') > 20:
                    break
                
                yaml_lines.append(line)
            
            yaml_content = '\n'.join(yaml_lines)
            session_data = yaml.safe_load(yaml_content)
            
            if not session_data:
                return {'error': 'Failed to parse SessionInfo YAML'}
            
            # Extract SplitTimeInfo
            split_time_info = session_data.get('SplitTimeInfo', {})
            if not split_time_info:
                return {'error': 'No SplitTimeInfo found'}
            
            return {
                'timestamp': time.time(),
                'split_time_info': split_time_info,
                'all_keys': list(split_time_info.keys()),
                'sectors': split_time_info.get('Sectors', [])
            }
            
        except Exception as e:
            return {'error': f'Error extracting SplitTimeInfo: {e}'}
    
    def analyze_sector_timing_data(self, split_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze SplitTimeInfo for timing data."""
        if 'error' in split_info:
            return split_info
        
        analysis = {
            'has_timing_data': False,
            'timing_fields': [],
            'sector_timing_data': [],
            'lap_timing_data': {}
        }
        
        split_time_info = split_info['split_time_info']
        
        # Check for lap-level timing data
        lap_timing_fields = ['LastLapTime', 'BestLapTime', 'CurrentLapTime']
        for field in lap_timing_fields:
            if field in split_time_info:
                analysis['lap_timing_data'][field] = split_time_info[field]
                analysis['has_timing_data'] = True
        
        # Check for sector-level timing data
        sectors = split_time_info.get('Sectors', [])
        for i, sector in enumerate(sectors):
            if isinstance(sector, dict):
                sector_timing = {
                    'sector_num': sector.get('SectorNum', i),
                    'start_pct': sector.get('SectorStartPct', 0.0),
                    'timing_fields': {}
                }
                
                # Look for timing fields in sector
                timing_fields = ['SectorTime', 'BestSectorTime', 'CurrentSectorTime']
                for field in timing_fields:
                    if field in sector:
                        sector_timing['timing_fields'][field] = sector[field]
                        analysis['has_timing_data'] = True
                
                analysis['sector_timing_data'].append(sector_timing)
        
        return analysis
    
    def monitor_session(self, duration_minutes: int = 30):
        """Monitor the session for SplitTimeInfo updates."""
        logger.info(f"🔍 Starting SplitTimeInfo monitoring for {duration_minutes} minutes...")
        logger.info("📋 Monitoring for:")
        logger.info("   - SessionInfo hash changes")
        logger.info("   - Lap completion events")
        logger.info("   - SplitTimeInfo timing data updates")
        logger.info("   - Sector timing fields")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # Initial SessionInfo capture
        session_info = self._get_session_info_raw()
        if session_info:
            initial_split_info = self.extract_splittime_info(session_info)
            if 'error' not in initial_split_info:
                logger.info("📊 Initial SplitTimeInfo captured")
                logger.info(f"   Keys: {initial_split_info['all_keys']}")
                logger.info(f"   Sectors: {len(initial_split_info['sectors'])}")
                
                initial_analysis = self.analyze_sector_timing_data(initial_split_info)
                if initial_analysis['has_timing_data']:
                    logger.info("✅ Initial timing data found!")
                    logger.info(f"   Lap timing: {initial_analysis['lap_timing_data']}")
                    for sector in initial_analysis['sector_timing_data']:
                        if sector['timing_fields']:
                            logger.info(f"   Sector {sector['sector_num']}: {sector['timing_fields']}")
                else:
                    logger.info("❌ No initial timing data found")
        
        # Monitoring loop
        frame_count = 0
        last_log_time = time.time()
        
        while time.time() < end_time and self.ir.is_connected:
            self.ir.freeze_var_buffer_latest()
            frame_count += 1
            
            # Get current telemetry
            current_lap_completed = self.ir['LapCompleted']
            current_lap = self.ir['Lap']
            lap_dist_pct = self.ir['LapDistPct']
            session_time = self.ir['SessionTime']
            
            # Check for lap completion
            if current_lap_completed > self.last_lap_completed:
                logger.info(f"🏁 LAP COMPLETED: {self.last_lap_completed} -> {current_lap_completed}")
                
                # Record lap completion event
                lap_event = {
                    'timestamp': time.time(),
                    'session_time': session_time,
                    'lap_completed': current_lap_completed,
                    'current_lap': current_lap,
                    'lap_dist_pct': lap_dist_pct
                }
                self.lap_completion_events.append(lap_event)
                
                # Immediately check SessionInfo for updates
                session_info = self._get_session_info_raw()
                session_info_hash = hash(session_info) if session_info else None
                
                logger.info(f"📊 Checking SessionInfo after lap completion...")
                
                if session_info_hash != self.last_session_info_hash:
                    logger.info("✅ SessionInfo changed after lap completion!")
                    
                    # Extract and analyze SplitTimeInfo
                    split_info = self.extract_splittime_info(session_info)
                    if 'error' not in split_info:
                        analysis = self.analyze_sector_timing_data(split_info)
                        
                        # Store snapshot
                        snapshot = {
                            'lap_completed': current_lap_completed,
                            'timestamp': time.time(),
                            'split_info': split_info,
                            'analysis': analysis
                        }
                        self.splittime_snapshots.append(snapshot)
                        
                        # Log findings
                        if analysis['has_timing_data']:
                            logger.info("🎯 TIMING DATA FOUND IN SPLITTIME!")
                            
                            if analysis['lap_timing_data']:
                                logger.info(f"   📊 Lap timing: {analysis['lap_timing_data']}")
                            
                            for sector in analysis['sector_timing_data']:
                                if sector['timing_fields']:
                                    logger.info(f"   🏁 Sector {sector['sector_num']}: {sector['timing_fields']}")
                        else:
                            logger.info("❌ No timing data found in SplitTimeInfo")
                            # Log what we DID find for debugging
                            logger.info(f"   📋 SplitTimeInfo keys: {split_info.get('all_keys', [])}")
                            logger.info(f"   🏁 Sectors found: {len(split_info.get('sectors', []))}")
                            if split_info.get('sectors'):
                                for i, sector in enumerate(split_info['sectors'][:3]):  # Show first 3 sectors
                                    logger.info(f"      S{i}: {sector}")
                    else:
                        logger.error(f"❌ Failed to extract SplitTimeInfo: {split_info.get('error', 'unknown error')}")
                    
                    self.last_session_info_hash = session_info_hash
                else:
                    logger.info("❌ SessionInfo unchanged after lap completion")
                
                self.last_lap_completed = current_lap_completed
            
            # Periodic status update
            if time.time() - last_log_time > 30:  # Every 30 seconds
                elapsed = time.time() - start_time
                remaining = (end_time - time.time()) / 60
                logger.info(f"📊 Status: {elapsed/60:.1f}min elapsed, {remaining:.1f}min remaining")
                logger.info(f"   Frames processed: {frame_count}")
                logger.info(f"   Lap completions detected: {len(self.lap_completion_events)}")
                logger.info(f"   SplitTimeInfo snapshots: {len(self.splittime_snapshots)}")
                last_log_time = time.time()
            
            time.sleep(0.1)  # 10Hz monitoring
        
        logger.info("🏁 Monitoring completed")
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of findings."""
        report = {
            'monitoring_duration': time.time() - self.monitoring_start_time,
            'lap_completions': len(self.lap_completion_events),
            'splittime_snapshots': len(self.splittime_snapshots),
            'timing_data_found': False,
            'findings': []
        }
        
        # Analyze snapshots for timing data
        for snapshot in self.splittime_snapshots:
            analysis = snapshot['analysis']
            if analysis['has_timing_data']:
                report['timing_data_found'] = True
                
                finding = {
                    'lap_completed': snapshot['lap_completed'],
                    'timestamp': snapshot['timestamp'],
                    'lap_timing': analysis['lap_timing_data'],
                    'sector_timing': []
                }
                
                for sector in analysis['sector_timing_data']:
                    if sector['timing_fields']:
                        finding['sector_timing'].append({
                            'sector_num': sector['sector_num'],
                            'timing_data': sector['timing_fields']
                        })
                
                report['findings'].append(finding)
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print a formatted report of findings."""
        logger.info("\n" + "="*60)
        logger.info("📊 SPLITTIME MONITORING REPORT")
        logger.info("="*60)
        
        logger.info(f"⏱️ Monitoring Duration: {report['monitoring_duration']/60:.1f} minutes")
        logger.info(f"🏁 Lap Completions Detected: {report['lap_completions']}")
        logger.info(f"📸 SplitTimeInfo Snapshots: {report['splittime_snapshots']}")
        
        if report['timing_data_found']:
            logger.info("✅ TIMING DATA FOUND IN SPLITTIME!")
            logger.info(f"📊 Findings: {len(report['findings'])} laps with timing data")
            
            for finding in report['findings']:
                logger.info(f"\n🏁 Lap {finding['lap_completed']}:")
                
                if finding['lap_timing']:
                    logger.info(f"   📊 Lap Timing: {finding['lap_timing']}")
                
                if finding['sector_timing']:
                    logger.info(f"   🏁 Sector Timing:")
                    for sector in finding['sector_timing']:
                        logger.info(f"      S{sector['sector_num']}: {sector['timing_data']}")
        else:
            logger.info("❌ NO TIMING DATA FOUND IN SPLITTIME")
            logger.info("   SplitTimeInfo appears to contain only static sector boundaries")
        
        logger.info("\n🎯 CONCLUSION:")
        if report['timing_data_found']:
            logger.info("   ✅ iRacing DOES update SplitTimeInfo with sector times!")
            logger.info("   💡 Recommendation: Use as validation/fallback for live detection")
        else:
            logger.info("   ❌ iRacing does NOT update SplitTimeInfo with sector times")
            logger.info("   💡 Recommendation: Continue with live crossing detection method")

def main():
    """Main monitoring function."""
    logger.info("🔬 Live SplitTimeInfo Monitor for iRacing")
    logger.info("=" * 50)
    
    monitor = SplitTimeMonitor()
    
    try:
        # Connect to iRacing
        if not monitor.connect():
            logger.error("❌ Failed to connect to iRacing")
            logger.info("💡 Make sure iRacing is running and you're in a session")
            return
        
        # Start monitoring
        logger.info("🚀 Starting monitoring...")
        logger.info("💡 Complete a few laps to test SplitTimeInfo updates")
        logger.info("🛑 Press Ctrl+C to stop monitoring early")
        
        report = monitor.monitor_session(duration_minutes=15)  # 15 minute default
        
        # Print results
        monitor.print_report(report)
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"splittime_monitor_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'report': report,
                'snapshots': monitor.splittime_snapshots,
                'lap_events': monitor.lap_completion_events
            }, f, indent=2, default=str)
        
        logger.info(f"💾 Detailed results saved to: {filename}")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Monitoring stopped by user")
        if monitor.splittime_snapshots:
            report = monitor.generate_report()
            monitor.print_report(report)
    
    except Exception as e:
        logger.error(f"❌ Error during monitoring: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        monitor.disconnect()

if __name__ == "__main__":
    main() 