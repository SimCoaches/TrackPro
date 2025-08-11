"""
Modern TrackPro Application with Authentication System.

This module provides the main application class for the modern TrackPro UI,
integrating all the authentication features from the original app.
"""

import sys
import time
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer, Qt

# Import authentication and database components
from trackpro.database import supabase
from trackpro.auth.oauth_handler import OAuthHandler
from trackpro.ui.modern import ModernMainWindow

logger = logging.getLogger(__name__)


class ModernTrackProApp:
    """Modern TrackPro application with complete authentication system."""
    
    def __init__(self, oauth_handler=None, start_time=None, app=None):
        """Initialize the modern TrackPro application."""
        self.start_time = start_time
        self.oauth_handler = oauth_handler
        self.window = None
        self.app = app or QApplication.instance()
        self.cleanup_completed = False
        # Track if the user has already completed profile requirements this session
        self.profile_completion_done = False
        
        # Initialize OAuth callback server attributes early
        self.oauth_callback_server = None
        self.oauth_port = None
        
        # Global system references
        self.global_iracing_api = None
        self.global_hardware = None
        self.global_output = None
        self.global_pedal_data_queue = None
        self.global_handbrake_hardware = None
        self.global_handbrake_data_queue = None
        
        if not self.app:
            # Create QApplication only if none exists; avoid resetting attributes after creation
            self.app = QApplication.instance() or QApplication(sys.argv)
        
        # Set up URL scheme handling for OAuth redirects (like original app)
        self.setup_url_scheme_handling()
        
        # Initialize the OAuth handler
        if not self.oauth_handler:
            self.oauth_handler = OAuthHandler()
        
        # Create the modern main window with OAuth handler
        self.create_main_window()
        
        # Connect quit handler
        self.app.aboutToQuit.connect(self.cleanup)
        
        logger.info("🚀 Modern TrackPro App initialized with authentication")
    
    def set_global_iracing_api(self, iracing_api):
        """Set the global iRacing API instance."""
        self.global_iracing_api = iracing_api
        logger.info("✅ Global iRacing API set for modern app")
        
        # Pass to window if it exists
        if self.window and hasattr(self.window, 'set_global_iracing_api'):
            self.window.set_global_iracing_api(iracing_api)
    
    def set_global_pedal_system(self, hardware, output, data_queue):
        """Set the global pedal system instances."""
        self.global_hardware = hardware
        self.global_output = output
        self.global_pedal_data_queue = data_queue
        logger.info("✅ Global pedal system set for modern app")
        
        # Pass to window if it exists
        if self.window and hasattr(self.window, 'set_global_pedal_system'):
            self.window.set_global_pedal_system(hardware, output, data_queue)
    
    def set_global_handbrake_system(self, handbrake_hardware, handbrake_data_queue):
        """Set the global handbrake system instances."""
        self.global_handbrake_hardware = handbrake_hardware
        self.global_handbrake_data_queue = handbrake_data_queue
        logger.info("✅ Global handbrake system set for modern app")
        
        # Pass to window if it exists
        if self.window and hasattr(self.window, 'set_global_handbrake_system'):
            self.window.set_global_handbrake_system(handbrake_hardware, handbrake_data_queue)
    
    def setup_oauth_callback_server(self):
        """Set up OAuth callback server (adapted from original TrackProApp)."""
        # Skip if already set up
        if self.oauth_callback_server is not None:
            return
            
        try:
            import socket
            
            # Check if port 3000 is available
            ports_to_try = [3000, 3001, 3002, 3003, 8080, 8081, 8082, 8083]
            selected_port = None
            
            for port in ports_to_try:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('127.0.0.1', port))
                    sock.close()
                    selected_port = port
                    break
                except socket.error:
                    continue
            
            if selected_port:
                self.oauth_port = selected_port
                # Let the oauth_handler.setup_callback_server handle port selection internally
                self.oauth_callback_server = self.oauth_handler.setup_callback_server(port=selected_port)
                if self.oauth_callback_server:
                    self.oauth_handler.oauth_port = self.oauth_port
                    logger.info(f"✅ OAuth callback server started on port {self.oauth_port}")
                else:
                    logger.error("❌ OAuth callback server failed to start")
                    self.oauth_callback_server = None
                    self.oauth_port = None
            else:
                logger.warning("⚠️ No available ports for OAuth callback server")
                self.oauth_callback_server = None
                self.oauth_port = None
                
        except Exception as e:
            logger.error(f"❌ Error setting up OAuth callback server: {e}")
            self.oauth_callback_server = None
            self.oauth_port = None
    
    def ensure_oauth_server_ready(self):
        """Ensure OAuth callback server is ready when needed."""
        if self.oauth_callback_server is None:
            logger.info("🔄 Setting up OAuth callback server on demand...")
            self.setup_oauth_callback_server()
    
    def create_main_window(self):
        """Create the main window with authentication support."""
        try:
            # Create the modern main window with OAuth handler
            self.window = ModernMainWindow(oauth_handler=self.oauth_handler)
            
            # Pass global systems to the window
            if self.global_iracing_api and hasattr(self.window, 'set_global_iracing_api'):
                self.window.set_global_iracing_api(self.global_iracing_api)
            
            if self.global_hardware and hasattr(self.window, 'set_global_pedal_system'):
                self.window.set_global_pedal_system(self.global_hardware, self.global_output, self.global_pedal_data_queue)
            
            # Connect authentication signals
            if hasattr(self.oauth_handler, 'auth_completed'):
                self.oauth_handler.auth_completed.connect(self.handle_auth_state_change)
            # Also react to profile completion requirement signals emitted during OAuth
            if hasattr(self.oauth_handler, 'profile_completion_required'):
                try:
                    self.oauth_handler.profile_completion_required.connect(lambda _res: QTimer.singleShot(0, self.ensure_profile_completion))
                except Exception:
                    pass
            
            # Ensure OAuth callback server is ready immediately
            self.ensure_oauth_server_ready()
            
            # PERFORMANCE: Non-blocking auth check during startup
            # Don't block the UI for authentication check - do it in background
            from PyQt6.QtCore import QTimer, QThread
            try:
                # Ensure we're on the main thread
                if QThread.currentThread() == self.app.thread():
                    QTimer.singleShot(100, self.perform_background_auth_check)
                else:
                    logger.warning("Not on main thread - skipping background auth check")
            except Exception as e:
                logger.error(f"Error setting up background auth check: {e}")
            
            # Connect window closing to cleanup
            self.window.destroyed.connect(self.cleanup)
            
            logger.info("✅ Modern main window created with non-blocking authentication")
            
        except Exception as e:
            logger.error(f"❌ Error creating main window: {e}")
            raise
    
    def handle_auth_state_change(self, is_authenticated):
        """Handle authentication state changes - SIMPLIFIED TO PREVENT CRASHES."""
        try:
            logger.info(f"🔐 Authentication state changed: {is_authenticated}")
            
            # SIMPLIFIED: Only update the main window's auth state
            # Defer all other operations to prevent immediate crashes
            if hasattr(self.window, 'update_auth_state'):
                self.window.update_auth_state(is_authenticated)
                logger.info("✅ Main window auth state updated")
            
            # DEFER: Schedule online status updates to prevent blocking/crashes
            from PyQt6.QtCore import QTimer
            if is_authenticated:
                QTimer.singleShot(2000, lambda: self._deferred_online_status_update(True))
                # Enforce profile completion shortly after login
                QTimer.singleShot(300, self.ensure_profile_completion)
            else:
                QTimer.singleShot(2000, lambda: self._deferred_online_status_update(False))
                
        except Exception as e:
            logger.error(f"❌ Error handling auth state change: {e}")
            # Don't let auth errors crash the app

    def ensure_profile_completion(self):
        """Ensure the authenticated user completes required profile fields."""
        try:
            # Skip if already satisfied in this session
            if getattr(self, 'profile_completion_done', False):
                return
            from trackpro.database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client:
                return
            session = client.auth.get_session()
            if not session or not getattr(session, 'user', None):
                return
            user_id = session.user.id
            user_email = getattr(session.user, 'email', '')
            from trackpro.social.user_manager import EnhancedUserManager
            mgr = EnhancedUserManager()
            profile = mgr.get_complete_user_profile(user_id)
            username = (profile.get('username') if profile else '') or ''
            display_name = (profile.get('display_name') if profile else '') or ''

            # Only prompt when BOTH identifiers are missing. If either exists, consider complete.
            requires_completion = not ((username or '').strip() or (display_name or '').strip())

            if requires_completion:
                # Prompt mandatory profile completion
                try:
                    from trackpro.auth.profile_completion_dialog import ProfileCompletionDialog
                    dlg = ProfileCompletionDialog(user_id, user_email, parent=self.window)
                    # Mark as done when the dialog reports completion
                    try:
                        dlg.profile_completed.connect(lambda _ok: setattr(self, 'profile_completion_done', True))
                    except Exception:
                        pass
                    dlg.exec()
                    # If user completed, avoid re-prompting in this session
                    if not self.profile_completion_done:
                        # Re-check profile once in case it was created without signal
                        profile_after = mgr.get_complete_user_profile(user_id)
                        if profile_after and ((profile_after.get('username') or '').strip() or (profile_after.get('display_name') or '').strip()):
                            self.profile_completion_done = True
                except Exception as e:
                    logger.error(f"Error showing profile completion dialog: {e}")
            else:
                # Already complete; don't prompt again this session
                self.profile_completion_done = True
        except Exception as e:
            logger.debug(f"ensure_profile_completion skipped: {e}")
    
    def _deferred_online_status_update(self, is_online):
        """Deferred online status update to prevent immediate crashes."""
        try:
            logger.info(f"🔄 Executing deferred online status update: {is_online}")
            from trackpro.database.supabase_client import get_supabase_client
            from trackpro.social.user_manager import EnhancedUserManager
            
            client = get_supabase_client()
            if client:
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    user_id = session.user.id
                    user_manager = EnhancedUserManager()
                    user_manager.update_online_status(user_id, is_online)
                    logger.info(f"✅ Set user {user_id} as {'online' if is_online else 'offline'}")
        except Exception as e:
            logger.warning(f"Could not update online status: {e}")
    
    def perform_background_auth_check(self):
        """Perform authentication check in background without blocking UI."""
        try:
            logger.info("🔐 Performing background authentication check...")
            
            # Check if Supabase is enabled first (fast local check)
            from trackpro.config import config
            if not config.supabase_enabled:
                logger.info("Supabase disabled in config - skipping auth check")
                self.handle_auth_state_change(False)
                return
            
            # Try a quick local session check first
            try:
                # Check if we have a local session file (fast check)
                import os
                auth_file = os.path.join(os.path.expanduser("~"), ".trackpro", "auth.json")
                if os.path.exists(auth_file):
                    logger.info("Found local auth file - attempting quick session restore")
                    # This will be fast if session is valid
                    is_authenticated = supabase.is_authenticated()
                    self.handle_auth_state_change(is_authenticated)
                else:
                    logger.info("No local auth file found - user not authenticated")
                    self.handle_auth_state_change(False)
            except Exception as e:
                logger.warning(f"Background auth check failed: {e}")
                # Don't block UI - assume not authenticated
                self.handle_auth_state_change(False)
                
        except Exception as e:
            logger.error(f"❌ Error in background auth check: {e}")
            # Don't block UI - assume not authenticated
            self.handle_auth_state_change(False)
    
    def show_login_dialog(self):
        """Show the login dialog."""
        try:
            from trackpro.auth.login_dialog import LoginDialog
            
            # Create and show login dialog
            login_dialog = LoginDialog(self.window, oauth_handler=self.oauth_handler)
            result = login_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user logged in)
                self.handle_auth_state_change(True)
            
            return result == 1
            
        except Exception as e:
            logger.error(f"❌ Error showing login dialog: {e}")
            QMessageBox.critical(
                self.window, 
                "Authentication Error", 
                f"Could not open login dialog: {str(e)}"
            )
            return False
    
    def setup_url_scheme_handling(self):
        """Set up URL scheme handling for OAuth redirects (from original app)."""
        try:
            # Register the application to handle the trackpro:// URL scheme
            self.register_url_scheme()
            
            # Check if the application was launched with a URL scheme
            args = self.app.arguments()
            for arg in args:
                if arg.startswith("trackpro://") or arg.startswith("app://"):
                    logger.info(f"Application launched with URL scheme: {arg}")
                    # Delay handling until window is ready
                    QTimer.singleShot(1000, lambda: self.handle_oauth_redirect(arg))
                    break
        except Exception as e:
            logger.warning(f"Error setting up URL scheme handling: {e}")
    
    def register_url_scheme(self):
        """Register the trackpro:// URL scheme with Windows."""
        try:
            import sys
            import winreg
            
            if getattr(sys, 'frozen', False):  # Only register when running as executable
                exe_path = sys.executable
                
                try:
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\trackpro")
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:TrackPro Protocol")
                    winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
                    winreg.CloseKey(key)
                    
                    cmd_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\trackpro\shell\open\command")
                    winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, f'"{exe_path}" "%1"')
                    winreg.CloseKey(cmd_key)
                    
                    logger.info("✅ Successfully registered trackpro:// URL scheme")
                except Exception as reg_error:
                    logger.warning(f"Could not register URL scheme: {reg_error}")
        except ImportError:
            logger.warning("winreg not available - URL scheme registration skipped")
        except Exception as e:
            logger.warning(f"Error registering URL scheme: {e}")
    
    def handle_oauth_redirect(self, url):
        """Handle OAuth redirects from the URL scheme."""
        logger.info(f"Handling OAuth redirect from URL: {url}")
        try:
            # Bring window to foreground
            self.bring_window_to_foreground()
            
            # Check if this is just a completion notification
            if "auth-complete" in url:
                logger.info("OAuth authentication completion notification received")
                if self.window:
                    QTimer.singleShot(0, lambda: QMessageBox.information(
                        self.window,
                        "Authentication Complete",
                        "You have been successfully logged in to TrackPro!"
                    ))
                return
            
            # Extract authorization code if present
            import re
            code_match = re.search(r"code=([^&]+)", url)
            if code_match:
                auth_code = code_match.group(1)
                logger.info(f"Received authorization code via URL scheme: {auth_code[:10]}...")
                
        except Exception as e:
            logger.error(f"Error handling OAuth redirect: {e}")
    
    def bring_window_to_foreground(self):
        """Bring the TrackPro window to the foreground."""
        try:
            if self.window:
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()
                
                # Force focus on Windows
                try:
                    import ctypes
                    hwnd = int(self.window.winId())
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.BringWindowToTop(hwnd)
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    logger.info("✅ Successfully brought window to foreground")
                except Exception as win_error:
                    logger.warning(f"Could not use Windows API to bring window forward: {win_error}")
                    
        except Exception as e:
            logger.error(f"Error bringing window to foreground: {e}")
    
    def run(self):
        """Run the application."""
        try:
            # Show the main window
            if self.window:
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()
                
                # Process events to make window responsive
                QApplication.processEvents()
                
                logger.info("🚀 Modern TrackPro UI is running")
                
                # Start the event loop
                exit_code = self.app.exec()
                
                # Cleanup before exit
                self.cleanup()
                
                return exit_code
            else:
                logger.error("❌ No main window to show")
                return 1
                
        except Exception as e:
            logger.error(f"❌ Error running application: {e}")
            logger.error(traceback.format_exc())
            return 1
    
    def cleanup(self):
        """Clean up resources before application closes."""
        if self.cleanup_completed:
            return
        
        logger.info("🧹 Cleaning up modern TrackPro app...")
        self.cleanup_completed = True
        
        try:

            
            # Clean up system tray icon first
            if self.window and hasattr(self.window, 'tray_icon') and self.window.tray_icon:
                try:
                    self.window.tray_icon.hide()
                    self.window.tray_icon.deleteLater()
                    logger.info("✅ System tray icon cleaned up from main app")
                except Exception as e:
                    logger.error(f"Error cleaning up tray icon from main app: {e}")
            
            # Shutdown OAuth callback server
            if hasattr(self, 'oauth_callback_server') and self.oauth_callback_server:
                try:
                    if hasattr(self.oauth_handler, 'shutdown_callback_server'):
                        self.oauth_handler.shutdown_callback_server(self.oauth_callback_server)
                    logger.info("✅ OAuth callback server shut down")
                except Exception as e:
                    logger.error(f"Error shutting down OAuth server: {e}")
            
            # Clean up window
            if self.window:
                try:
                    if hasattr(self.window, 'cleanup'):
                        self.window.cleanup()
                    logger.info("✅ Window cleaned up")
                except Exception as e:
                    logger.error(f"Error cleaning up window: {e}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("🧹 Modern TrackPro app cleanup completed")
        
        # Force quit the application to ensure it closes properly
        try:
            if self.app:
                logger.info("🚪 Scheduling application quit...")
                QTimer.singleShot(100, self.app.quit)  # Delayed quit
                # Backup exit mechanism in case quit() doesn't work
                QTimer.singleShot(1000, lambda: self.app.exit(0))
        except Exception as e:
            logger.error(f"Error during force quit: {e}")
            # Last resort - force system exit
            import sys
            sys.exit(0)


def main():
    """Main entry point for the modern TrackPro application."""
    try:
        # Parse command line arguments
        import sys
        start_minimized = "--minimized" in sys.argv
        
        app = ModernTrackProApp()
        
        # If starting minimized, hide the window initially
        if start_minimized and app.window:
            app.window.hide()
            logger.info("🚀 TrackPro starting minimized")
        
        return app.run()
    except KeyboardInterrupt:
        logger.info("🛑 Modern TrackPro interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Error running modern TrackPro: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())