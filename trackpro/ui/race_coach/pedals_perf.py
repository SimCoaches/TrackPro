"""
Compat passthrough so `import trackpro.ui.race_coach.pedals_perf` works.
It re-exports the real code from `trackpro.race_coach.pedals_perf`.
"""
from ...race_coach.pedals_perf import *  # relative up to `trackpro`, then `race_coach`
