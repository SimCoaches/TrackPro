"""Simple launcher for the modern TrackPro UI.

This script provides a clean way to launch just the modern UI without
all the complexity of the full TrackPro initialization.
"""

import sys
import os
import logging
import signal
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add trackpro to the path
current_dir = Path(__file__).parent
trackpro_path = current_dir / "trackpro"
sys.path.insert(0, str(trackpro_path))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
    QApplication.quit()

def main():
    """Launch the modern TrackPro UI."""
    logger.info("🚀 Launching Modern TrackPro UI...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set Qt attributes BEFORE creating QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    
    # Fix Qt WebEngine issues
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("TrackPro Modern")
    app.setApplicationVersion("1.5.5-modern")
    app.setOrganizationDomain("simcoaches.com")
    
    try:
        # Import the NEW modular modern UI
        from trackpro.ui.modern import ModernMainWindow
        
        # Create the modern window
        logger.info("🏗️ Creating modular modern UI with separated page architecture...")
        window = ModernMainWindow()
        
        # Show the window
        window.show()
        window.raise_()
        window.activateWindow()
        
        logger.info("✅ Modular TrackPro UI launched successfully!")
        
        # Start the event loop
        return app.exec()
            
    except Exception as e:
        logger.error(f"❌ Error launching modern UI: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())