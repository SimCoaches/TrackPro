"""Dialog for managing pedal profiles."""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
    QFormLayout, QMessageBox, QInputDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ..database.pedal_profiles import PedalProfileManager
from ..database.supabase_client import supabase

logger = logging.getLogger(__name__)

class PedalProfileDialog(QDialog):
    """Dialog for managing pedal profiles."""
    
    # Signal emitted when a profile is selected for loading
    profile_selected = pyqtSignal(dict)
    
    def __init__(self, parent=None, current_calibration=None):
        """Initialize the pedal profile dialog.
        
        Args:
            parent: Parent widget
            current_calibration: Current pedal calibration data to potentially save
        """
        super().__init__(parent)
        self.setWindowTitle("Pedal Profiles")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Store current calibration
        self.current_calibration = current_calibration or {}
        
        # List of profiles
        self.profile_list = []
        
        self.setup_ui()
        self.load_profiles()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Authentication required message (initially hidden)
        self.auth_message = QLabel("You must be logged in to use pedal profiles.")
        self.auth_message.setStyleSheet("color: red;")
        self.auth_message.setVisible(False)
        main_layout.addWidget(self.auth_message)
        
        # Login button (initially hidden)
        self.login_button = QPushButton("Sign In")
        self.login_button.clicked.connect(self.open_login_dialog)
        self.login_button.setVisible(False)
        main_layout.addWidget(self.login_button)
        
        # User info layout
        user_layout = QHBoxLayout()
        main_layout.addLayout(user_layout)
        
        self.user_label = QLabel("Not logged in")
        user_layout.addWidget(self.user_label)
        
        user_layout.addStretch()
        
        # Profiles label
        profiles_label = QLabel("Your Profiles")
        profiles_label.setFont(QFont(profiles_label.font().family(), 12, QFont.Weight.Bold))
        main_layout.addWidget(profiles_label)
        
        # Profiles list
        self.profiles_list_widget = QListWidget()
        self.profiles_list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.profiles_list_widget.itemSelectionChanged.connect(self.on_profile_selection_changed)
        main_layout.addWidget(self.profiles_list_widget)
        
        # Horizontal line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)
        
        # Profile details form
        details_layout = QFormLayout()
        main_layout.addLayout(details_layout)
        
        # Name field
        self.name_input = QLineEdit()
        details_layout.addRow("Name:", self.name_input)
        
        # Description field
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        details_layout.addRow("Description:", self.description_input)
        
        # Button layout
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        # Save button
        self.save_button = QPushButton("Save Current Settings")
        self.save_button.clicked.connect(self.save_current_profile)
        button_layout.addWidget(self.save_button)
        
        # Load button
        self.load_button = QPushButton("Load Selected Profile")
        self.load_button.clicked.connect(self.load_selected_profile)
        self.load_button.setEnabled(False)
        button_layout.addWidget(self.load_button)
        
        # Delete button
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_selected_profile)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        # Update authentication state
        self.update_auth_state()
    
    def update_auth_state(self):
        """Update UI based on authentication state."""
        try:
            is_authenticated = supabase.is_authenticated()
            
            # Update visibility of auth message and login button
            self.auth_message.setVisible(not is_authenticated)
            self.login_button.setVisible(not is_authenticated)
            
            # Update user label
            if is_authenticated:
                user_response = supabase.get_user()
                if user_response and hasattr(user_response, 'user'):
                    email = user_response.user.email if hasattr(user_response.user, 'email') else "Unknown"
                    self.user_label.setText(f"Logged in as: {email}")
                else:
                    self.user_label.setText("Logged in")
            else:
                self.user_label.setText("Not logged in")
            
            # Enable/disable controls based on auth
            self.profiles_list_widget.setEnabled(is_authenticated)
            self.name_input.setEnabled(is_authenticated)
            self.description_input.setEnabled(is_authenticated)
            self.save_button.setEnabled(is_authenticated)
            
            # If authenticated, load profiles
            if is_authenticated:
                self.load_profiles()
        except Exception as e:
            logger.error(f"Error updating auth state: {e}")
    
    def open_login_dialog(self):
        """Open the login dialog."""
        try:
            # Get the main window
            from ..auth.login_dialog import LoginDialog
            
            # Create and show the login dialog
            dialog = LoginDialog(self)
            result = dialog.exec()
            
            # Update auth state
            self.update_auth_state()
        except Exception as e:
            logger.error(f"Error opening login dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not open login dialog: {str(e)}")
    
    def load_profiles(self):
        """Load profiles from Supabase."""
        try:
            # Clear current list
            self.profiles_list_widget.clear()
            self.profile_list = []
            
            # Check if authenticated
            if not supabase.is_authenticated():
                return
            
            # Get profiles
            profiles = PedalProfileManager.get_profiles()
            self.profile_list = profiles
            
            # Add to list widget
            for profile in profiles:
                item = QListWidgetItem(profile.get('name', 'Unnamed Profile'))
                item.setData(Qt.ItemDataRole.UserRole, profile.get('id'))
                self.profiles_list_widget.addItem(item)
            
            # Update UI
            self.name_input.clear()
            self.description_input.clear()
            self.load_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Error loading profiles: {e}")
            QMessageBox.critical(self, "Error", f"Could not load profiles: {str(e)}")
    
    def on_profile_selection_changed(self):
        """Handle profile selection change."""
        selected_items = self.profiles_list_widget.selectedItems()
        if selected_items:
            # Enable buttons
            self.load_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            
            # Get profile ID
            profile_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
            
            # Find profile in list
            for profile in self.profile_list:
                if profile.get('id') == profile_id:
                    # Update form
                    self.name_input.setText(profile.get('name', ''))
                    self.description_input.setText(profile.get('description', ''))
                    return
        else:
            # Disable buttons
            self.load_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            
            # Clear form
            self.name_input.clear()
            self.description_input.clear()
    
    def save_current_profile(self):
        """Save the current calibration as a profile."""
        try:
            # Check if authenticated
            if not supabase.is_authenticated():
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to save profiles.")
                return
            
            # Check if we have calibration data
            if not self.current_calibration:
                QMessageBox.warning(self, "No Calibration", "No current calibration data to save.")
                return
            
            # Get name
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Name Required", "Please provide a name for this profile.")
                self.name_input.setFocus()
                return
            
            # Get description
            description = self.description_input.toPlainText().strip()
            
            # Extract calibration data for each pedal
            throttle_calibration = self.current_calibration.get('throttle', {})
            brake_calibration = self.current_calibration.get('brake', {})
            clutch_calibration = self.current_calibration.get('clutch', {})
            
            # Check if updating existing profile
            selected_items = self.profiles_list_widget.selectedItems()
            profile_id = None
            if selected_items:
                # Ask if user wants to update or create new
                choice = QMessageBox.question(
                    self,
                    "Update Profile",
                    f"Do you want to update the selected profile '{selected_items[0].text()}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if choice == QMessageBox.StandardButton.Yes:
                    profile_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
            
            # Save profile
            profile = PedalProfileManager.save_profile(
                name=name,
                description=description,
                throttle_calibration=throttle_calibration,
                brake_calibration=brake_calibration,
                clutch_calibration=clutch_calibration,
                profile_id=profile_id
            )
            
            # Show success message
            QMessageBox.information(
                self, 
                "Profile Saved", 
                f"Pedal profile '{name}' saved successfully."
            )
            
            # Reload profiles
            self.load_profiles()
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            QMessageBox.critical(self, "Error", f"Could not save profile: {str(e)}")
    
    def load_selected_profile(self):
        """Load the selected profile."""
        try:
            # Check if there's a selection
            selected_items = self.profiles_list_widget.selectedItems()
            if not selected_items:
                return
            
            # Get profile ID
            profile_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
            
            # Find profile in list
            for profile in self.profile_list:
                if profile.get('id') == profile_id:
                    # Emit signal with profile data
                    self.profile_selected.emit(profile)
                    
                    # Show success message
                    QMessageBox.information(
                        self, 
                        "Profile Loaded", 
                        f"Pedal profile '{profile.get('name')}' loaded successfully."
                    )
                    
                    # Close dialog
                    self.accept()
                    return
            
            # If we get here, something went wrong
            QMessageBox.warning(self, "Profile Not Found", "Could not find the selected profile.")
            
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            QMessageBox.critical(self, "Error", f"Could not load profile: {str(e)}")
    
    def delete_selected_profile(self):
        """Delete the selected profile."""
        try:
            # Check if there's a selection
            selected_items = self.profiles_list_widget.selectedItems()
            if not selected_items:
                return
            
            # Confirm deletion
            profile_name = selected_items[0].text()
            choice = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the profile '{profile_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if choice != QMessageBox.StandardButton.Yes:
                return
            
            # Get profile ID
            profile_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
            
            # Delete profile
            success = PedalProfileManager.delete_profile(profile_id)
            
            if success:
                # Show success message
                QMessageBox.information(
                    self, 
                    "Profile Deleted", 
                    f"Pedal profile '{profile_name}' deleted successfully."
                )
                
                # Reload profiles
                self.load_profiles()
            else:
                QMessageBox.warning(self, "Deletion Failed", "Could not delete the profile.")
            
        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            QMessageBox.critical(self, "Error", f"Could not delete profile: {str(e)}")
            
    def set_current_calibration(self, calibration):
        """Set the current calibration data for saving.
        
        Args:
            calibration: Dictionary of calibration data keyed by pedal name
        """
        self.current_calibration = calibration 