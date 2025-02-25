import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.main import main

def show_error_dialog(message):
    """Show an error dialog that works in windowed mode."""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication([])
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("TrackPro Error")
        error_box.setText(message)
        error_box.exec_()
    except Exception:
        # Fallback to console if PyQt fails
        print(message)
        input("Press Enter to exit...")

if __name__ == "__main__":
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Test mode - exiting")
        sys.exit(0)
        
    try:
        main()
    except Exception as e:
        error_message = f"Error running TrackPro: {str(e)}"
        show_error_dialog(error_message) 