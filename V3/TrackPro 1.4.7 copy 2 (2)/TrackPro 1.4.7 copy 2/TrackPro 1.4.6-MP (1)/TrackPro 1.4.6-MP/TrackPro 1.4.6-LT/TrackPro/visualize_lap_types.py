#!/usr/bin/env python
"""
Lap Type Visualization Tool

This script visualizes the lap classification results from test reports
to help identify issues with lap type labeling.
"""

import os
import sys
import json
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime

def load_latest_report():
    """Load the most recent test report file."""
    report_dir = Path("test_reports")
    if not report_dir.exists():
        print("No test reports directory found. Run test_lap_type_labeling.py first.")
        return None
    
    report_files = list(report_dir.glob("lap_type_test_*.json"))
    if not report_files:
        print("No test reports found. Run test_lap_type_labeling.py first.")
        return None
    
    # Sort by modification time (most recent first)
    latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading latest report: {latest_report}")
    
    with open(latest_report, 'r') as f:
        return json.load(f)

def load_specific_report(filename):
    """Load a specific test report file."""
    report_path = Path(filename)
    if not report_path.exists():
        print(f"Report file {filename} not found.")
        return None
    
    with open(report_path, 'r') as f:
        return json.load(f)

def visualize_lap_types(report_data):
    """Create a visualization of lap types from report data."""
    if not report_data or 'lap_results' not in report_data:
        print("Invalid report data.")
        return
    
    laps = report_data['lap_results']
    total_laps = len(laps)
    
    if total_laps == 0:
        print("No lap data in report.")
        return
    
    # Create figure and axes
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [1, 3]})
    fig.suptitle(f"Lap Type Classification Analysis - {report_data.get('timestamp', 'Unknown Date')}", fontsize=16)
    
    # Define colors for different lap types
    colors = {
        'OUT': 'green',
        'TIMED': 'blue',
        'IN': 'red',
        'INCOMPLETE': 'gray'
    }
    
    # Create a summary bar for lap types
    lap_types = {'OUT': 0, 'TIMED': 0, 'IN': 0, 'INCOMPLETE': 0}
    for lap in laps:
        lap_state = lap.get('lap_type', 'INCOMPLETE')
        lap_types[lap_state] += 1
    
    # Plot summary bar
    bars = ax1.bar(lap_types.keys(), lap_types.values(), color=[colors[t] for t in lap_types.keys()])
    ax1.set_ylabel("Count")
    ax1.set_title("Lap Type Summary")
    
    # Add count labels on bars
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{int(height)}', ha='center', va='bottom')
    
    # Create detailed lap visualization
    lap_numbers = [lap.get('lap_number', i) for i, lap in enumerate(laps)]
    lap_states = [lap.get('lap_type', 'UNKNOWN') for lap in laps]
    expected_states = [lap.get('expected_type', None) for lap in laps]
    test_results = [lap.get('passed', False) for lap in laps]
    
    # Create detailed lap bar chart
    y_pos = range(len(lap_numbers))
    ax2.barh(y_pos, [1] * len(lap_numbers), color=[colors[state] for state in lap_states])
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"Lap {num}" for num in lap_numbers])
    ax2.set_xlabel("Lap Type")
    ax2.set_xlim(0, 1.5)  # Make room for annotations
    
    # Add lap state annotations and highlight mismatches
    for i, (lap_num, state, expected, passed) in enumerate(zip(lap_numbers, lap_states, expected_states, test_results)):
        # Add lap state label
        ax2.text(1.05, i, state, va='center')
        
        # If there's an expected state and it doesn't match, highlight it
        if expected and not passed:
            ax2.add_patch(patches.Rectangle((0, i-0.4), 1, 0.8, fill=False, 
                                           edgecolor='red', linestyle='--', linewidth=2))
            ax2.text(1.25, i, f"Expected: {expected}", va='center', color='red')
    
    # Add legend
    handles = [patches.Patch(color=colors[key], label=key) for key in colors]
    ax2.legend(handles=handles, title="Lap Types", loc='upper right')
    
    # Add test results
    tests_passed = report_data.get('tests_passed', 0)
    tests_failed = report_data.get('tests_failed', 0)
    all_passed = report_data.get('all_tests_passed', False)
    status_color = 'green' if all_passed else 'red'
    status_text = "PASS" if all_passed else "FAIL"
    
    fig.text(0.5, 0.01, f"Test Status: {status_text} ({tests_passed}/{tests_passed + tests_failed} passed)", 
             ha='center', color=status_color, fontsize=14, weight='bold')
    
    # Adjust layout and save/show
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Save the visualization
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    viz_dir = Path("lap_visualizations")
    viz_dir.mkdir(exist_ok=True)
    plt.savefig(viz_dir / f"lap_types_viz_{timestamp}.png", dpi=150)
    
    print(f"Visualization saved to lap_visualizations/lap_types_viz_{timestamp}.png")
    plt.show()

def visualize_lap_transitions(report_data):
    """Create a visualization of lap transitions from report data."""
    if not report_data or 'lap_results' not in report_data:
        print("Invalid report data.")
        return
    
    laps = report_data['lap_results']
    total_laps = len(laps)
    
    if total_laps == 0:
        print("No lap data in report.")
        return
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.suptitle(f"Lap Transitions Analysis - {report_data.get('timestamp', 'Unknown Date')}", fontsize=16)
    
    # Define colors and markers for different lap types
    colors = {
        'OUT': 'green',
        'TIMED': 'blue',
        'IN': 'red',
        'INCOMPLETE': 'gray'
    }
    
    markers = {
        'OUT': '^',  # Triangle up
        'TIMED': 'o',  # Circle
        'IN': 'v',  # Triangle down
        'INCOMPLETE': 's'  # Square
    }
    
    # Extract data
    lap_numbers = [lap.get('lap_number', i) for i, lap in enumerate(laps)]
    lap_states = [lap.get('lap_type', 'UNKNOWN') for lap in laps]
    durations = [lap.get('duration', 0) for lap in laps]
    started_on_pit = [lap.get('started_pit', False) for lap in laps]
    ended_on_pit = [lap.get('ended_pit', False) for lap in laps]
    
    # Plot lap numbers vs durations with lap type coloring
    for i, (lap_num, state, duration, start_pit, end_pit) in enumerate(
            zip(lap_numbers, lap_states, durations, started_on_pit, ended_on_pit)):
        # Plot point for lap
        ax.scatter(lap_num, duration, color=colors[state], s=100, marker=markers[state], 
                  label=state if state not in ax.get_legend_handles_labels()[1] else "")
        
        # Add lap number label
        ax.annotate(f"{lap_num}", (lap_num, duration), xytext=(5, 5), 
                   textcoords='offset points', fontsize=8)
        
        # Draw connecting lines between consecutive laps
        if i > 0:
            prev_lap_num = lap_numbers[i-1]
            prev_duration = durations[i-1]
            ax.plot([prev_lap_num, lap_num], [prev_duration, duration], 'k-', alpha=0.3)
        
        # Mark pit road status
        if start_pit:
            ax.annotate("P", (lap_num-0.1, duration), color='purple', fontweight='bold')
        if end_pit:
            ax.annotate("P", (lap_num+0.1, duration), color='purple', fontweight='bold')
    
    # Add legend
    handles = [plt.Line2D([0], [0], marker=markers[key], color=colors[key], 
                          label=key, markerfacecolor=colors[key], markersize=10, linestyle='') 
              for key in colors]
    ax.legend(handles=handles, title="Lap Types", loc='upper right')
    
    # Set axis labels
    ax.set_xlabel("Lap Number (SDK)")
    ax.set_ylabel("Lap Duration (seconds)")
    ax.set_title("Lap Duration vs. Lap Number by Type")
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Adjust x-ticks to show all lap numbers
    ax.set_xticks(lap_numbers)
    
    # Add test result summary
    tests_passed = report_data.get('tests_passed', 0)
    tests_failed = report_data.get('tests_failed', 0)
    all_passed = report_data.get('all_tests_passed', False)
    status_color = 'green' if all_passed else 'red'
    status_text = "PASS" if all_passed else "FAIL"
    
    fig.text(0.5, 0.01, f"Test Status: {status_text} ({tests_passed}/{tests_passed + tests_failed} passed)", 
             ha='center', color=status_color, fontsize=14, weight='bold')
    
    # Adjust layout and save/show
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Save the visualization
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    viz_dir = Path("lap_visualizations")
    viz_dir.mkdir(exist_ok=True)
    plt.savefig(viz_dir / f"lap_transitions_viz_{timestamp}.png", dpi=150)
    
    print(f"Visualization saved to lap_visualizations/lap_transitions_viz_{timestamp}.png")
    plt.show()

def main():
    """Main function."""
    # Check if a specific report file was provided
    if len(sys.argv) > 1:
        report_data = load_specific_report(sys.argv[1])
    else:
        report_data = load_latest_report()
    
    if not report_data:
        print("No report data available. Run test_lap_type_labeling.py first.")
        return
    
    # Create visualizations
    visualize_lap_types(report_data)
    visualize_lap_transitions(report_data)

if __name__ == "__main__":
    main() 