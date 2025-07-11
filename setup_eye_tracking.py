#!/usr/bin/env python3
"""Setup script for EyeTrax eye tracking integration with TrackPro.

This script installs the necessary dependencies and sets up eye tracking
capabilities for the TrackPro racing application.
"""

import sys
import subprocess
import importlib
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def install_package(package_name, pip_name=None):
    """Install a package using pip if it's not already installed."""
    if pip_name is None:
        pip_name = package_name
    
    try:
        importlib.import_module(package_name)
        logger.info(f"✓ {package_name} is already installed")
        return True
    except ImportError:
        logger.info(f"Installing {pip_name}...")
        try:
            # Use py instead of python on Windows
            python_cmd = "py" if sys.platform == "win32" else "python"
            # Add CREATE_NO_WINDOW flag to hide command window on Windows
            if sys.platform == "win32":
                CREATE_NO_WINDOW = 0x08000000
                subprocess.check_call([python_cmd, "-m", "pip", "install", pip_name], creationflags=CREATE_NO_WINDOW)
            else:
                subprocess.check_call([python_cmd, "-m", "pip", "install", pip_name])
            logger.info(f"✓ Successfully installed {pip_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Failed to install {pip_name}: {e}")
            return False


def check_camera_access():
    """Check if camera access is working."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                logger.info("✓ Camera access is working")
                return True
            else:
                logger.warning("⚠ Camera opened but couldn't read frame")
                return False
        else:
            logger.warning("⚠ Could not open camera")
            return False
    except Exception as e:
        logger.error(f"✗ Camera access check failed: {e}")
        return False


def setup_eye_tracking():
    """Set up eye tracking dependencies and test installation."""
    logger.info("Setting up EyeTrax eye tracking for TrackPro...")
    
    # Check Python version compatibility
    python_version = sys.version_info
    if python_version >= (3, 13):
        logger.warning("⚠ Python 3.13+ detected. EyeTrax requires Python 3.11-3.12 due to mediapipe compatibility.")
        logger.info("Options:")
        logger.info("1. Install Python 3.11 or 3.12 for eye tracking")
        logger.info("2. Use basic OpenCV eye tracking (limited functionality)")
        logger.info("3. Wait for mediapipe to support Python 3.13")
        
        # Install basic OpenCV support only
        packages = [
            ("cv2", "opencv-python"),
            ("numpy", "numpy"),
            ("scipy", "scipy")
        ]
        logger.info("Installing basic eye tracking dependencies...")
    else:
        # Full EyeTrax support for Python 3.11-3.12
        packages = [
            ("cv2", "opencv-python"),
            ("numpy", "numpy"),
            ("mediapipe", "mediapipe"),
            ("eyetrax", "eyetrax"),
            ("scipy", "scipy")
        ]
    
    success = True
    
    # Install packages
    for module_name, pip_name in packages:
        if not install_package(module_name, pip_name):
            success = False
    
    if not success:
        logger.error("✗ Some packages failed to install")
        return False
    
    # Test eye tracking import based on Python version
    python_version = sys.version_info
    if python_version >= (3, 13):
        logger.info("✓ Basic eye tracking dependencies installed for Python 3.13+")
        logger.warning("⚠ Advanced EyeTrax features not available - see PYTHON_COMPATIBILITY.md")
    else:
        try:
            from eyetrax import GazeEstimator
            logger.info("✓ EyeTrax import successful")
        except ImportError as e:
            logger.error(f"✗ EyeTrax import failed: {e}")
            return False
    
    # Test camera access
    if not check_camera_access():
        logger.warning("⚠ Camera access test failed - eye tracking may not work properly")
    
    logger.info("✓ Eye tracking setup completed successfully!")
    logger.info("\nTo use eye tracking in TrackPro:")
    logger.info("1. Start TrackPro")
    logger.info("2. Go to the Race Coach section")
    logger.info("3. Click 'Calibrate Eye Tracking' before starting a session")
    logger.info("4. Eye tracking data will appear in the telemetry analysis")
    
    return True


def test_integration():
    """Test the eye tracking integration."""
    logger.info("Testing TrackPro eye tracking integration...")
    
    try:
        # Test imports
        from trackpro.race_coach.eye_tracking_manager import EyeTrackingManager
        from trackpro.race_coach.widgets.gaze_graph import GazeGraphWidget
        
        # Test initialization
        manager = EyeTrackingManager()
        if manager.is_available():
            logger.info("✓ Eye tracking manager is available")
        else:
            logger.warning("⚠ Eye tracking manager not available - check EyeTrax installation")
        
        # Test widget creation
        widget = GazeGraphWidget()
        logger.info("✓ Gaze visualization widget created successfully")
        
        logger.info("✓ Integration test passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Integration test failed: {e}")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("EyeTrax Eye Tracking Setup for TrackPro")
    print("=" * 60)
    
    if not setup_eye_tracking():
        logger.error("Setup failed!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Testing integration...")
    print("=" * 60)
    
    if test_integration():
        logger.info("🎉 Eye tracking setup completed successfully!")
    else:
        logger.warning("⚠ Setup completed but integration test failed")
    
    print("\n" + "=" * 60)
    print("Setup complete! You can now use eye tracking in TrackPro.")
    print("=" * 60)


if __name__ == "__main__":
    main() 