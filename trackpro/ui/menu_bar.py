"""Menu bar functionality for MainWindow."""

from .shared_imports import *


def create_menu_bar(main_window):
    """Create the main menu bar for the MainWindow."""
    # Import here to avoid circular imports
    from ..database import supabase, user_manager
    
    menu_bar = main_window.menuBar()
    # File menu
    file_menu = menu_bar.addMenu("&File")
    
    # === PROFILES SECTION ===
    # Add Pedal Profiles menu
    pedal_profiles_menu = file_menu.addMenu("Pedal Profiles")
    
    # Manage profiles action
    manage_profiles_action = QAction("Manage Profiles...", main_window)
    manage_profiles_action.triggered.connect(main_window.show_profile_manager)
    pedal_profiles_menu.addAction(manage_profiles_action)
    
    # Save current profile action
    save_profile_action = QAction("Save Current Settings as Profile...", main_window)
    save_profile_action.triggered.connect(main_window.save_current_profile)
    pedal_profiles_menu.addAction(save_profile_action)
    
    file_menu.addSeparator()
    
    # === CLOUD SYNC & AUTHENTICATION SECTION ===
    # Add Supabase configuration submenu
    supabase_menu = file_menu.addMenu("Cloud Sync")
    
    # Add enable/disable action
    main_window.supabase_enabled_action = QAction("Enable Cloud Sync", main_window)
    main_window.supabase_enabled_action.setCheckable(True)
    main_window.supabase_enabled_action.setChecked(config.supabase_enabled)
    main_window.supabase_enabled_action.triggered.connect(main_window.toggle_supabase)
    supabase_menu.addAction(main_window.supabase_enabled_action)
    
    # Add configure action
    configure_supabase_action = QAction("Configure Credentials...", main_window)
    configure_supabase_action.triggered.connect(main_window.configure_supabase)
    supabase_menu.addAction(configure_supabase_action)
    
    # Add authentication-related actions
    main_window.login_action = file_menu.addAction("Login")
    main_window.login_action.triggered.connect(main_window.show_login_dialog)
    main_window.login_action.setEnabled(config.supabase_enabled)
    
    main_window.signup_action = file_menu.addAction("Sign Up")
    main_window.signup_action.triggered.connect(main_window.show_signup_dialog)
    main_window.signup_action.setEnabled(config.supabase_enabled)
    
    main_window.logout_action = file_menu.addAction("Logout")
    main_window.logout_action.triggered.connect(main_window.logout_user)
    main_window.logout_action.setVisible(False)

    # Add Refresh Login State option
    main_window.refresh_login_action = file_menu.addAction("Refresh Login State")
    main_window.refresh_login_action.triggered.connect(lambda: force_refresh_login_state(main_window))
    
    file_menu.addSeparator()
    
    # === SETTINGS SECTION ===
    # Add Settings submenu
    settings_menu = file_menu.addMenu("Settings")
    
    # Minimize to tray toggle
    main_window.file_minimize_to_tray_action = QAction("Minimize to tray", main_window)
    main_window.file_minimize_to_tray_action.setCheckable(True)
    main_window.file_minimize_to_tray_action.setChecked(config.minimize_to_tray)
    main_window.file_minimize_to_tray_action.triggered.connect(lambda checked: toggle_minimize_to_tray_from_menu(main_window, checked))
    settings_menu.addAction(main_window.file_minimize_to_tray_action)
    
    # Eye tracking settings
    eye_tracking_settings_action = QAction("Eye Tracking Settings...", main_window)
    eye_tracking_settings_action.triggered.connect(main_window.show_eye_tracking_settings)
    settings_menu.addAction(eye_tracking_settings_action)
    
    # Track map overlay settings
    track_map_overlay_action = QAction("Track Map Overlay...", main_window)
    track_map_overlay_action.triggered.connect(main_window.show_track_map_overlay_settings)
    settings_menu.addAction(track_map_overlay_action)
    
    # Add Check for Updates option
    update_action = QAction("Check for Updates", main_window)
    update_action.triggered.connect(main_window.check_for_updates)
    file_menu.addAction(update_action)
    
    # Add separator before Exit
    file_menu.addSeparator()
    
    # Add Exit option
    exit_action = QAction("E&xit", main_window)
    exit_action.setShortcut("Ctrl+Q")
    exit_action.triggered.connect(main_window.close)
    file_menu.addAction(exit_action)
    
    # Add Pedal Config button to menu bar
    main_window.pedal_config_action = QAction("Pedal Config", main_window)
    main_window.pedal_config_action.triggered.connect(main_window.open_pedal_config)
    main_window.pedal_config_action.setCheckable(True)
    main_window.pedal_config_action.setChecked(True)  # Default active section
    menu_bar.addAction(main_window.pedal_config_action)
    
    # Add Race Coach button to menu bar
    main_window.race_coach_action = QAction("Race Coach", main_window)
    main_window.race_coach_action.triggered.connect(main_window.open_race_coach)
    main_window.race_coach_action.setCheckable(True)
    main_window.race_coach_action.setChecked(False)
    main_window.race_coach_action.setToolTip("Login required to access Race Coach features")
    menu_bar.addAction(main_window.race_coach_action)
    
    # Add Race Pass button to menu bar
    main_window.race_pass_action = QAction("Race Pass", main_window)
    main_window.race_pass_action.triggered.connect(main_window.open_race_pass)
    main_window.race_pass_action.setCheckable(True)
    main_window.race_pass_action.setChecked(False)
    main_window.race_pass_action.setToolTip("Login required to access Race Pass features")
    menu_bar.addAction(main_window.race_pass_action)
    
    # Add Community button to menu bar (for backward compatibility)
    main_window.community_action = QAction("🌐 Community", main_window)
    main_window.community_action.triggered.connect(main_window.open_community_interface)
    main_window.community_action.setCheckable(True)
    main_window.community_action.setChecked(False)
    main_window.community_action.setToolTip("Access community features: social, teams, content sharing, and achievements")
    menu_bar.addAction(main_window.community_action)
    
    # Create a container for the auth buttons in the menu bar corner
    auth_container = QWidget()
    auth_layout = QHBoxLayout(auth_container)
    auth_layout.setContentsMargins(5, 2, 5, 2)
    auth_layout.setSpacing(5)
    
    # Add authentication buttons to the container
    auth_layout.addWidget(main_window.community_btn_container)
    auth_layout.addWidget(main_window.account_btn)
    auth_layout.addWidget(main_window.login_btn)
    auth_layout.addWidget(main_window.signup_btn)
    auth_layout.addWidget(main_window.logout_btn)
    
    # Set the container as the corner widget (top right)
    menu_bar.setCornerWidget(auth_container, Qt.Corner.TopRightCorner)
    
    # Style the menu bar for dark theme
    menu_bar.setStyleSheet("""
        QMenuBar {
            background-color: #353535;
            color: #ffffff;
        }
        QMenuBar::item {
            background-color: #353535;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #2a82da;
        }
        QMenu {
            background-color: #353535;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QMenu::item:selected {
            background-color: #2a82da;
        }
        QAction:checked {
            background-color: #2a82da;
            font-weight: bold;
        }
    """)

    # Help menu
    help_menu = main_window.menuBar().addMenu("Help")
    
    about_action = QAction("About TrackPro", main_window)
    about_action.triggered.connect(main_window.show_about)
    help_menu.addAction(about_action)
    
    # Add debugging menu item for email testing
    help_menu.addSeparator()
    test_email_action = QAction("Test Email Configuration", main_window)
    test_email_action.triggered.connect(main_window.test_email_setup)
    help_menu.addAction(test_email_action)
    
    # Add performance optimizer
    optimize_action = QAction("Optimize Performance", main_window)
    optimize_action.triggered.connect(main_window.optimize_performance)
    help_menu.addAction(optimize_action)
    
    # Add authentication refresh option
    help_menu.addSeparator()
    refresh_auth_action = QAction("Refresh Authentication State", main_window)
    refresh_auth_action.triggered.connect(lambda: force_refresh_login_state(main_window))
    help_menu.addAction(refresh_auth_action)


def toggle_minimize_to_tray_from_menu(main_window, checked):
    """Toggle the minimize to tray setting from the menu bar."""
    # Import here to avoid circular imports
    from .system_tray import toggle_minimize_to_tray
    toggle_minimize_to_tray(main_window, checked)


def force_refresh_login_state(main_window):
    """Force a refresh of the authentication state."""
    logger.info("Manually refreshing authentication state")
    
    # Try modern UI method first
    if hasattr(main_window, 'force_auth_refresh_after_login'):
        logger.info("Using modern UI force refresh method")
        success = main_window.force_auth_refresh_after_login()
        if success:
            QMessageBox.information(main_window, "Login State Refreshed", "Authentication state refreshed successfully!")
            return
    
    # Fallback to legacy method
    try:
        from ..database import supabase
        
        # Restore session from file first to ensure we have the latest data
        if hasattr(supabase, '_restore_session'):
            supabase._restore_session()
            
        # Force processEvents to update the UI
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Update the authentication state
        if hasattr(main_window, 'update_auth_state'):
            main_window.update_auth_state()
        
        # Force processEvents again to ensure UI updates
        QApplication.processEvents()
        
        # Get the current user for a message
        user = supabase.get_user()
        if user and ((hasattr(user, 'user') and user.user) or hasattr(user, 'email')):
            user_email = None
            if hasattr(user, 'email'):
                user_email = user.email
            elif hasattr(user, 'user') and hasattr(user.user, 'email'):
                user_email = user.user.email
            
            message = f"Refreshed authentication state. Logged in as: {user_email}"
            QMessageBox.information(main_window, "Login State Refreshed", message)
        else:
            QMessageBox.information(main_window, "Login State Refreshed", "Refreshed authentication state. No user is currently logged in.")
    except Exception as e:
        logger.error(f"Error in force_refresh_login_state: {e}")
        QMessageBox.warning(main_window, "Refresh Error", f"Error refreshing authentication state: {str(e)}") 