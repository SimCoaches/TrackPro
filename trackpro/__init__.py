"""TrackPro package root.

This module intentionally avoids importing heavy UI modules at import time to
ensure headless usage (tests, scripts) works without initializing QtWebEngine.
"""

__version__ = "1.5.6"
__author__ = "Sim Coaches"
__license__ = "Proprietary"
__copyright__ = "Copyright 2025 Sim Coaches"

import logging

# Set higher logging level for noisy HTTP and Supabase libraries
for library in ['urllib3', 'httpcore', 'httpx', 'hpack', 'gotrue', 'postgrest']:
    logging.getLogger(library).setLevel(logging.WARNING)

# Avoid configuring logging at import time to prevent duplicate setup and slow imports
# The application entrypoint is responsible for calling setup_logging()

# Expose a lightweight entrypoint getter to avoid heavy imports by default
def get_main_entrypoint():
    from .modern_main import main
    return main

__all__ = [
    "__version__",
    "get_main_entrypoint",
]