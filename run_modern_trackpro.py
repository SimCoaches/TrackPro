"""Run script for the modern TrackPro interface.

This script launches TrackPro with the new modern UI framework.
"""

import sys
import os
from pathlib import Path

# Add trackpro to the path
current_dir = Path(__file__).parent
trackpro_path = current_dir / "trackpro"
sys.path.insert(0, str(trackpro_path))

# Import and run the modern TrackPro
try:
    from trackpro.modern_main import main as modern_main
    print("🚀 Starting Modern TrackPro...")
    sys.exit(modern_main())
except ImportError as e:
    print(f"❌ Error importing modern TrackPro: {e}")
    print("Falling back to test UI...")
    
    # Fallback to test UI
    try:
        exec(open("test_new_ui.py").read())
    except Exception as fallback_error:
        print(f"❌ Fallback also failed: {fallback_error}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error running modern TrackPro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)