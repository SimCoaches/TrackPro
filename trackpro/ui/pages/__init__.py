from .pedals.pedals_page import PedalsPage
from .race_pass.race_pass_page import RacePassPage
from .support.support_page_fixed import SupportPage

__all__ = ['PedalsPage', 'RacePassPage', 'SupportPage']

# Make profile module importable to relative imports used by popups/sidebars
try:
    from .profile import public_profile_page  # noqa: F401
except Exception:
    pass