"""
Compat layer for legacy imports:
    import trackpro.ui.race_coach as rc
    from trackpro.ui.race_coach import <Names from trackpro.race_coach.ui>
We re-export all public names from the real module: trackpro.race_coach.ui
"""
# Absolute import to the real module is safest and clearest.
from trackpro.race_coach.ui import *  # re-export UI symbols
