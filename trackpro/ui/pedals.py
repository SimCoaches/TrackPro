"""
Compatibility module for legacy imports.
Re-exports PedalsPage from the correct location.
"""
# Robust import to handle current tree (trackpro/ui/pages/pedals)
try:
    from .pages.pedals.pedals_page import PedalsPage
except ImportError:
    # Fallback for different structures
    try:
        from .pages.pedals import PedalsPage  # type: ignore
    except ImportError:
        raise ImportError(
            "Could not import PedalsPage. Check trackpro/ui/pages/pedals/pedals_page.py exists."
        )

__all__ = ['PedalsPage']
