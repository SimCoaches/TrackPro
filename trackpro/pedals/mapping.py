# trackpro/pedals/mapping.py
"""
Single source of truth for pedal mapping.
Used by vJoy output, UI dot positioning, and all percentage displays.
Eliminates duplicate deadzone math that was causing desync between UI and output.
"""

from math import isfinite
from typing import List, Tuple

def apply_deadzone(n: float, dz_min: float, dz_max: float) -> float:
    """Apply deadzone mapping: input outside [dz_min, 1-dz_max] gets clamped and rescaled."""
    # n in [0,1], dz_* in [0,1)
    if n <= dz_min:
        return 0.0
    if n >= 1.0 - dz_max:
        return 1.0
    
    span = 1.0 - dz_min - dz_max
    if span <= 0:
        return 0.0
    
    return (n - dz_min) / span

def eval_curve(x: float, points: List[Tuple[float, float]]) -> float:
    """Evaluate curve at x using polyline interpolation."""
    # x in [0,1], points = list of (x,y) polyline control points
    # Simple monotone polyline; replace with your spline/bezier if needed.
    if not points:
        return x
    
    if x <= points[0][0]:
        return points[0][1]
    
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            t = (x - x0) / max(1e-9, (x1 - x0))
            return y0 + t * (y1 - y0)
    
    return points[-1][1]

def map_raw(raw: float, rmin: float, rmax: float, dz_min: float, dz_max: float, curve_points: List[Tuple[float, float]]) -> Tuple[float, float, float]:
    """
    Single source of truth for all pedal mapping.
    
    Args:
        raw: Raw sensor value
        rmin, rmax: Raw sensor range
        dz_min, dz_max: Deadzone percentages (0.0-1.0)
        curve_points: List of (x,y) curve control points in 0-1 space
    
    Returns:
        (n, x, y) where:
        - n: normalized raw value (0-1, pre-deadzone) 
        - x: post-deadzone value (0-1, for UI dot position)
        - y: final curve output (0-1, for vJoy and displays)
    """
    if rmax <= rmin:
        return 0.0, 0.0, 0.0
    
    # Normalize to 0-1
    n = (raw - rmin) / (rmax - rmin)
    n = 0.0 if not isfinite(n) else max(0.0, min(1.0, n))
    
    # Apply deadzone first
    x = apply_deadzone(n, dz_min, dz_max)
    
    # Then apply curve
    y = eval_curve(x, curve_points)
    
    return n, x, y
