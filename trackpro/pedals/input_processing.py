from __future__ import annotations

def apply_deadzones_norm(v: float, dz_min: float, dz_max: float) -> float:
    """
    v: normalized raw [0..1] (after axis min/max calibration)
    dz_min/dz_max: fractions [0..1]
    Behavior matches Mikey branch:
      - hard floor until dz_min
      - linear remap of [dz_min .. 1 - dz_max] -> [0 .. 1]
      - clamp at ends
    """
    if v <= dz_min:
        return 0.0
    span = max(1e-6, 1.0 - dz_min - dz_max)
    v = (v - dz_min) / span
    return 0.0 if v <= 0 else (1.0 if v >= 1.0 else v)
