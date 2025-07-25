"""System tray functionality for MainWindow."""

from .shared_imports import *
from PyQt6.QtCore import QObject, QTimer


def setup_system_tray(main_window):
    """Set up system tray functionality for the MainWindow."""
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.warning("System tray is not available on this system")
        return
    
    # Create system tray icon
    main_window.tray_icon = QSystemTrayIcon(main_window)
    
    # Set icon - try to use our custom TrackPro tray icon
    try:
        # Try to load our custom tray icon
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "trackpro_tray.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            logger.info(f"Loaded custom tray icon from: {icon_path}")
        else:
            # Try PNG version
            png_icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "trackpro_tray.png")
            if os.path.exists(png_icon_path):
                icon = QIcon(png_icon_path)
                logger.info(f"Loaded custom tray icon (PNG) from: {png_icon_path}")
            else:
                # Fallback to window icon
                icon = main_window.windowIcon()
                if icon.isNull():
                    # Final fallback to system icon
                    icon = main_window.style().standardIcon(main_window.style().SP_ComputerIcon)
                    logger.warning("Using system fallback icon for tray")
                else:
                    logger.info("Using window icon for tray")
        
        main_window.tray_icon.setIcon(icon)
        
    except Exception as e:
        logger.warning(f"Could not set tray icon: {e}")
        # Use a standard system icon as fallback
        icon = main_window.style().standardIcon(main_window.style().SP_ComputerIcon)
        main_window.tray_icon.setIcon(icon)
    
    # Create tray menu
    tray_menu = QMenu()
    
    # Show/Hide action
    show_action = QAction("Show TrackPro", main_window)
    show_action.triggered.connect(lambda: show_from_tray(main_window))
    tray_menu.addAction(show_action)
    
    # Settings submenu
    settings_menu = tray_menu.addMenu("Settings")
    
    # Minimize to tray toggle
    main_window.minimize_to_tray_action = QAction("Minimize to tray", main_window)
    main_window.minimize_to_tray_action.setCheckable(True)
    main_window.minimize_to_tray_action.setChecked(config.minimize_to_tray)
    main_window.minimize_to_tray_action.triggered.connect(lambda checked: toggle_minimize_to_tray(main_window, checked))
    settings_menu.addAction(main_window.minimize_to_tray_action)
    
    tray_menu.addSeparator()
    
    # Exit action
    exit_action = QAction("Exit TrackPro", main_window)
    exit_action.triggered.connect(lambda: exit_application(main_window))
    tray_menu.addAction(exit_action)
    
    # Set the menu
    main_window.tray_icon.setContextMenu(tray_menu)
    
    # Connect double-click to show window
    main_window.tray_icon.activated.connect(lambda reason: tray_icon_activated(main_window, reason))
    
    # Set tooltip
    main_window.tray_icon.setToolTip("TrackPro - Racing Telemetry System")
    
    # Show the tray icon
    main_window.tray_icon.show()
    
    logger.info("System tray initialized successfully")


def tray_icon_activated(main_window, reason):
    """Handle tray icon activation."""
    if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
        show_from_tray(main_window)


def show_from_tray(main_window):
    """Show the main window from system tray."""
    main_window.show()
    main_window.raise_()
    main_window.activateWindow()
    logger.info("Window restored from system tray")


def toggle_minimize_to_tray(main_window, checked):
    """Toggle the minimize to tray setting."""
    config.set('ui.minimize_to_tray', checked)
    logger.info(f"Minimize to tray setting changed to: {checked}")
    
    # Update both menu actions to stay in sync
    if hasattr(main_window, 'minimize_to_tray_action'):
        main_window.minimize_to_tray_action.setChecked(checked)
    if hasattr(main_window, 'file_minimize_to_tray_action'):
        main_window.file_minimize_to_tray_action.setChecked(checked)
    
    # Show a notification about the setting change
    if hasattr(main_window, 'tray_icon') and main_window.tray_icon.isVisible():
        message = "TrackPro will minimize to tray when closed" if checked else "TrackPro will exit when closed"
        main_window.tray_icon.showMessage("Settings Changed", message, QSystemTrayIcon.MessageIcon.Information, 3000)


def exit_application(main_window):
    """Exit the application completely - FORCE KILL ALL PROCESSES."""
    logger.info("FORCE EXIT requested from system tray")
    
    # Hide tray icon first
    if hasattr(main_window, 'tray_icon'):
        main_window.tray_icon.hide()
    
    # Temporarily disable minimize to tray to force actual exit
    original_setting = config.minimize_to_tray
    config.set('ui.minimize_to_tray', False)
    
    # Force kill all TrackPro processes immediately
    try:
        logger.info("🔫 System tray force killing all TrackPro processes...")
        
        # Use subprocess utility to hide windows
        from ..utils.subprocess_utils import run_subprocess
        
        kill_commands = [
            ['taskkill', '/F', '/IM', 'TrackPro*.exe'],
            ['taskkill', '/F', '/T', '/IM', 'TrackPro_v1.5.3.exe'],
            ['powershell', '-Command', "Get-Process | Where-Object {$_.ProcessName -like '*TrackPro*'} | Stop-Process -Force"],
        ]
        
        for cmd in kill_commands:
            try:
                run_subprocess(cmd, hide_window=True, capture_output=True, text=True, check=False, timeout=3)
            except:
                pass
                
    except Exception as e:
        logger.warning(f"Error during system tray force kill: {e}")
    
    # Clean up lock file
    try:
        import tempfile
        import os
        lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except:
        pass
    
    # Force quit application
    try:
        QApplication.instance().quit()
    except:
        import sys
        sys.exit(0) 