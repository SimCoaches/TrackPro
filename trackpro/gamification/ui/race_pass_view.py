from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QGridLayout, 
                             QProgressBar, QGroupBox, QTabWidget, QSplitter, QSizePolicy,
                             QMessageBox, QDialog, QLineEdit, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter
import requests
import json
import logging

from .enhanced_quest_view import EnhancedQuestViewWidget
from ..supabase_gamification import (
    get_current_season, get_race_pass_rewards, get_user_race_pass_progress,
    purchase_premium_race_pass, get_user_profile
)

logger = logging.getLogger(__name__)

# Import Stripe integration with fallback
try:
    from ..stripe_integration import stripe_processor, process_race_pass_payment, create_race_pass_checkout
except ImportError:
    logger.warning("Stripe integration not available. Payment features will be disabled.")
    stripe_processor = None
    process_race_pass_payment = None
    create_race_pass_checkout = None

class StripePaymentDialog(QDialog):
    """Dialog for handling Stripe payment for premium race pass."""
    
    def __init__(self, parent=None, amount=9.99):
        super().__init__(parent)
        self.amount = amount
        self.setWindowTitle("Unlock Premium Race Pass")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Premium Race Pass")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e67e22; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(f"Unlock premium rewards for ${amount:.2f}/month\nRecurring monthly subscription")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #FFF; margin-bottom: 20px;")
        layout.addWidget(desc)
        
        # Payment form
        form_layout = QFormLayout()
        
        self.card_number = QLineEdit()
        self.card_number.setPlaceholderText("1234 5678 9012 3456")
        self.card_number.setStyleSheet("padding: 8px; border: 1px solid #555; border-radius: 4px; background: #2a2a2a; color: white;")
        form_layout.addRow("Card Number:", self.card_number)
        
        expiry_layout = QHBoxLayout()
        self.expiry_month = QLineEdit()
        self.expiry_month.setPlaceholderText("MM")
        self.expiry_month.setMaxLength(2)
        self.expiry_month.setFixedWidth(50)
        self.expiry_year = QLineEdit()
        self.expiry_year.setPlaceholderText("YY")
        self.expiry_year.setMaxLength(2)
        self.expiry_year.setFixedWidth(50)
        self.cvv = QLineEdit()
        self.cvv.setPlaceholderText("123")
        self.cvv.setMaxLength(4)
        self.cvv.setFixedWidth(60)
        
        for field in [self.expiry_month, self.expiry_year, self.cvv]:
            field.setStyleSheet("padding: 8px; border: 1px solid #555; border-radius: 4px; background: #2a2a2a; color: white;")
        
        expiry_layout.addWidget(self.expiry_month)
        expiry_layout.addWidget(QLabel("/"))
        expiry_layout.addWidget(self.expiry_year)
        expiry_layout.addStretch()
        expiry_layout.addWidget(QLabel("CVV:"))
        expiry_layout.addWidget(self.cvv)
        
        form_layout.addRow("Expiry / CVV:", expiry_layout)
        
        self.cardholder_name = QLineEdit()
        self.cardholder_name.setPlaceholderText("John Doe")
        self.cardholder_name.setStyleSheet("padding: 8px; border: 1px solid #555; border-radius: 4px; background: #2a2a2a; color: white;")
        form_layout.addRow("Cardholder Name:", self.cardholder_name)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(f"Subscribe ${amount:.2f}/month")
        button_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        button_box.accepted.connect(self.process_payment)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2a2a2a;
                color: white;
            }
            QLabel {
                color: white;
            }
        """)
    
    def process_payment(self):
        """Process the payment using Stripe."""
        # Validate fields
        if not all([self.card_number.text(), self.expiry_month.text(), 
                   self.expiry_year.text(), self.cvv.text(), self.cardholder_name.text()]):
            QMessageBox.warning(self, "Invalid Input", "Please fill in all fields.")
            return
        
        # Check if Stripe is available and configured
        if not stripe_processor or not stripe_processor.is_configured():
            # Fallback to demo mode
            QMessageBox.information(self, "Demo Mode", 
                                   "Stripe is not configured. Running in demo mode.\n\n"
                                   "Premium Race Pass unlocked successfully!")
            self.accept()
            return
        
        # Disable the button during processing
        ok_button = self.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok)
        ok_button.setEnabled(False)
        ok_button.setText("Processing...")
        
        try:
            # Get user email (you might want to get this from the logged-in user)
            user_email = "user@example.com"  # Replace with actual user email
            user_name = self.cardholder_name.text()
            
            # Process payment
            success, payment_data = process_race_pass_payment(user_email, user_name)
            
            if success:
                QMessageBox.information(self, "Payment Successful", 
                                       "Premium Race Pass unlocked successfully!\n\n"
                                       f"Payment ID: {payment_data.get('payment_intent_id', 'N/A')}")
                self.accept()
            else:
                error_msg = payment_data.get('error', 'Unknown error occurred')
                QMessageBox.critical(self, "Payment Failed", 
                                   f"Payment could not be processed:\n{error_msg}")
                
        except Exception as e:
            QMessageBox.critical(self, "Payment Error", 
                               f"An error occurred during payment processing:\n{str(e)}")
        finally:
            # Re-enable the button
            ok_button.setEnabled(True)
            ok_button.setText(f"Subscribe ${self.amount:.2f}/month")

class PaymentWorker(QThread):
    """Worker thread for processing Stripe payments."""
    payment_completed = pyqtSignal(bool, str)
    
    def __init__(self, payment_data):
        super().__init__()
        self.payment_data = payment_data
    
    def run(self):
        """Process payment in background thread."""
        try:
            # Mock Stripe API call
            # In a real implementation, you would use the Stripe Python library here
            success = True
            message = "Payment processed successfully"
            self.payment_completed.emit(success, message)
        except Exception as e:
            self.payment_completed.emit(False, str(e))

class RacePassOverviewWidget(QWidget):
    """Overview tab showing quick stats and progress summary."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RacePassOverviewWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Race Pass Overview")
        title_font = QFont("Arial", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #e67e22; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Create a splitter for side-by-side layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left side - Current Progress
        progress_frame = self._create_progress_section()
        splitter.addWidget(progress_frame)
        
        # Right side - Quick Actions & Stats
        actions_frame = self._create_actions_section()
        splitter.addWidget(actions_frame)
        
        # Set splitter proportions
        splitter.setSizes([60, 40])  # 60% for progress, 40% for actions
        
        main_layout.addStretch()
        
    def _create_progress_section(self):
        """Create the current progress section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(15)
        
        # Section title
        section_title = QLabel("Current Season Progress")
        section_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #FFF; margin-bottom: 10px;")
        layout.addWidget(section_title)
        
        # Season info
        self.season_name_label = QLabel("Season 1: Genesis")
        self.season_name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.season_name_label.setStyleSheet("color: #e67e22;")
        layout.addWidget(self.season_name_label)
        
        # Current tier display
        tier_layout = QHBoxLayout()
        self.current_tier_label = QLabel("Current Tier: 5")
        self.current_tier_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.current_tier_label.setStyleSheet("color: #FFF;")
        tier_layout.addWidget(self.current_tier_label)
        tier_layout.addStretch()
        
        self.max_tier_label = QLabel("/ 50")
        self.max_tier_label.setFont(QFont("Arial", 12))
        self.max_tier_label.setStyleSheet("color: #AAA;")
        tier_layout.addWidget(self.max_tier_label)
        layout.addLayout(tier_layout)
        
        # Progress bar to next tier
        progress_label = QLabel("Progress to Next Tier:")
        progress_label.setStyleSheet("color: #CCC; font-size: 10pt;")
        layout.addWidget(progress_label)
        
        self.tier_progress_bar = QProgressBar()
        self.tier_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #333;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #e67e22;
                border-radius: 3px;
            }
        """)
        self.tier_progress_bar.setValue(65)  # Placeholder
        layout.addWidget(self.tier_progress_bar)
        
        # XP info
        xp_layout = QHBoxLayout()
        self.current_xp_label = QLabel("1,250 XP")
        self.current_xp_label.setStyleSheet("color: #3498db; font-weight: bold;")
        xp_layout.addWidget(self.current_xp_label)
        
        xp_layout.addWidget(QLabel(" / "))
        
        self.next_tier_xp_label = QLabel("2,000 XP")
        self.next_tier_xp_label.setStyleSheet("color: #AAA;")
        xp_layout.addWidget(self.next_tier_xp_label)
        xp_layout.addStretch()
        layout.addLayout(xp_layout)
        
        # Time remaining
        self.time_remaining_label = QLabel("28 days remaining")
        self.time_remaining_label.setStyleSheet("color: #f39c12; font-weight: bold; margin-top: 10px;")
        layout.addWidget(self.time_remaining_label)
        
        return frame
        
    def _create_actions_section(self):
        """Create the quick actions and stats section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(15)
        
        # Section title
        section_title = QLabel("Quick Actions")
        section_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #FFF; margin-bottom: 10px;")
        layout.addWidget(section_title)
        
        # Premium pass status/purchase
        self.premium_status_frame = QFrame()
        self.premium_status_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #e67e22;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        premium_layout = QVBoxLayout(self.premium_status_frame)
        
        self.premium_status_label = QLabel("Premium Pass")
        self.premium_status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.premium_status_label.setStyleSheet("color: #e67e22;")
        premium_layout.addWidget(self.premium_status_label)
        
        self.premium_purchase_button = QPushButton("Subscribe $9.99/month")
        self.premium_purchase_button.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:pressed {
                background-color: #a04000;
            }
        """)
        self.premium_purchase_button.clicked.connect(self.on_purchase_premium)
        premium_layout.addWidget(self.premium_purchase_button)
        
        layout.addWidget(self.premium_status_frame)
        
        # Quick stats
        stats_title = QLabel("Season Stats")
        stats_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_title.setStyleSheet("color: #FFF; margin-top: 15px;")
        layout.addWidget(stats_title)
        
        # Stats grid
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #1a1a1a; border-radius: 5px; padding: 10px;")
        stats_layout = QGridLayout(stats_frame)
        
        # Completed quests
        stats_layout.addWidget(QLabel("Quests Completed:"), 0, 0)
        self.quests_completed_label = QLabel("12")
        self.quests_completed_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        stats_layout.addWidget(self.quests_completed_label, 0, 1)
        
        # Total XP earned
        stats_layout.addWidget(QLabel("Total XP Earned:"), 1, 0)
        self.total_xp_label = QLabel("5,420")
        self.total_xp_label.setStyleSheet("color: #3498db; font-weight: bold;")
        stats_layout.addWidget(self.total_xp_label, 1, 1)
        
        # Rewards claimed
        stats_layout.addWidget(QLabel("Rewards Claimed:"), 2, 0)
        self.rewards_claimed_label = QLabel("8 / 15")
        self.rewards_claimed_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        stats_layout.addWidget(self.rewards_claimed_label, 2, 1)
        
        layout.addWidget(stats_frame)
        layout.addStretch()
        
        return frame
        
    def on_purchase_premium(self):
        """Handle premium pass purchase using Stripe Checkout."""
        # Check if Stripe is available and configured
        if not create_race_pass_checkout:
            # Fallback to demo mode
            QMessageBox.information(self, "Demo Mode", 
                                   "Stripe is not configured. Running in demo mode.\n\n"
                                   "Premium Race Pass subscription activated!")
            self._activate_premium()
            return
        
        try:
            # Create Stripe Checkout session
            user_email = "user@example.com"  # Replace with actual user email from auth
            success, checkout_data = create_race_pass_checkout(user_email)
            
            if success:
                # Open Stripe Checkout directly in browser
                import webbrowser
                checkout_url = checkout_data.get('checkout_url')
                webbrowser.open(checkout_url)
                
                # For demo purposes, simulate successful payment after a delay
                QMessageBox.information(self, "Demo Mode", 
                                       "In a real implementation, the user would complete payment on Stripe's secure checkout page.\n\n"
                                       "For demo purposes, activating premium now...")
                self._activate_premium()
                    
            else:
                error_msg = checkout_data.get('error', 'Unknown error occurred')
                QMessageBox.critical(self, "Checkout Error", 
                                   f"Could not create checkout session:\n{error_msg}")
                
        except Exception as e:
            QMessageBox.critical(self, "Payment Error", 
                               f"An error occurred:\n{str(e)}")
    
    def _activate_premium(self):
        """Activate premium pass (called after successful payment)."""
        self.premium_purchase_button.setText("Premium Active ✓")
        self.premium_purchase_button.setEnabled(False)
        self.premium_purchase_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 10pt;
            }
        """)
        self.premium_status_label.setText("Premium Pass Active ✓")
        
        # Notify parent widget if it has the premium activation method
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'race_pass_track_widget'):
                parent_widget.race_pass_track_widget.premium_active = True
                # Refresh the track widget
                current_tier = 5  # You might want to get this from actual data
                parent_widget.race_pass_track_widget._load_placeholder_tiers(50, current_tier, premium_active=True)
                break
            parent_widget = parent_widget.parent()
        
    def update_overview_data(self, season_data, user_progress, stats):
        """Update the overview with current data."""
        if season_data:
            self.season_name_label.setText(season_data.get('name', 'Current Season'))
            
        if user_progress:
            current_tier = user_progress.get('current_tier', 0)
            max_tier = user_progress.get('max_tier', 50)
            self.current_tier_label.setText(f"Current Tier: {current_tier}")
            self.max_tier_label.setText(f"/ {max_tier}")
            
            # Update progress bar
            progress = user_progress.get('tier_progress', 0)
            self.tier_progress_bar.setValue(int(progress))
            
            # Update XP labels
            current_xp = user_progress.get('current_xp', 0)
            next_tier_xp = user_progress.get('next_tier_xp', 1000)
            self.current_xp_label.setText(f"{current_xp:,} XP")
            self.next_tier_xp_label.setText(f"{next_tier_xp:,} XP")
            
        if stats:
            self.quests_completed_label.setText(str(stats.get('quests_completed', 0)))
            self.total_xp_label.setText(f"{stats.get('total_xp', 0):,}")
            claimed = stats.get('rewards_claimed', 0)
            available = stats.get('rewards_available', 0)
            self.rewards_claimed_label.setText(f"{claimed} / {available}")


class RacePassTrackWidget(QWidget):
    """The actual race pass track showing all tiers and rewards with horizontal scrolling."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RacePassTrackWidget")
        self.premium_active = False
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Compact title and season info
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 4)
        
        title_label = QLabel("Race Pass - Season 1: Genesis")
        title_font = QFont("Arial", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.season_progress_label = QLabel("Your Tier: 5 / 50 | Ends in: 28 days")
        self.season_progress_label.setStyleSheet("color: #DDD; font-size: 10pt;")
        header_layout.addWidget(self.season_progress_label)
        
        main_layout.addLayout(header_layout)

        # Compact premium pass purchase section
        purchase_frame = QFrame()
        purchase_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #e67e22;
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 8px;
                max-height: 60px;
            }
        """)
        purchase_layout = QHBoxLayout(purchase_frame)
        purchase_layout.setContentsMargins(8, 4, 8, 4)
        purchase_layout.setSpacing(12)
        
        # Compact premium pass info - single line
        premium_info_layout = QHBoxLayout()
        premium_title = QLabel("Premium Race Pass")
        premium_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        premium_title.setStyleSheet("color: #e67e22;")
        
        premium_desc = QLabel("• Exclusive rewards • Double XP • Season-long access")
        premium_desc.setStyleSheet("color: #CCC; font-size: 9pt;")
        
        premium_info_layout.addWidget(premium_title)
        premium_info_layout.addWidget(QLabel(" - "))
        premium_info_layout.addWidget(premium_desc)
        premium_info_layout.addStretch()
        purchase_layout.addLayout(premium_info_layout)
        
        # TrackCoins balance display
        from .trackcoins_store import TrackCoinsBalanceWidget
        self.trackcoins_balance = TrackCoinsBalanceWidget()
        purchase_layout.addWidget(self.trackcoins_balance)
        
        # Compact purchase button with TrackCoins
        self.purchase_pass_button = QPushButton("Unlock for 1,000 🪙")
        self.purchase_pass_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #f39c12;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10pt;
                min-width: 140px;
                max-height: 36px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #27ae60;
                color: white;
            }
        """)
        self.purchase_pass_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.purchase_pass_button.clicked.connect(self.on_purchase_pass)
        purchase_layout.addWidget(self.purchase_pass_button)
        
        # Get TrackCoins button
        get_coins_btn = QPushButton("Get TrackCoins")
        get_coins_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 12px;
                background-color: #3498db;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 9pt;
                min-width: 100px;
                max-height: 36px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        get_coins_btn.clicked.connect(self.open_trackcoins_store)
        purchase_layout.addWidget(get_coins_btn)
        
        main_layout.addWidget(purchase_frame)

        # Compact track type selector
        track_selector_layout = QHBoxLayout()
        track_selector_layout.setContentsMargins(0, 4, 0, 8)
        track_selector_layout.addWidget(QLabel("View:"))
        
        self.free_track_btn = QPushButton("Free Track")
        self.premium_track_btn = QPushButton("Premium Track")
        self.both_tracks_btn = QPushButton("Both Tracks")
        
        for btn in [self.free_track_btn, self.premium_track_btn, self.both_tracks_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    background-color: #333;
                    color: white;
                    border: 1px solid #555;
                    border-radius: 4px;
                    margin-right: 4px;
                    font-size: 9pt;
                    max-height: 28px;
                }
                QPushButton:hover {
                    background-color: #444;
                }
                QPushButton:checked {
                    background-color: #e67e22;
                    border-color: #e67e22;
                }
            """)
            btn.setCheckable(True)
        
        self.both_tracks_btn.setChecked(True)  # Default view
        
        self.free_track_btn.clicked.connect(lambda: self.set_track_view('free'))
        self.premium_track_btn.clicked.connect(lambda: self.set_track_view('premium'))
        self.both_tracks_btn.clicked.connect(lambda: self.set_track_view('both'))
        
        track_selector_layout.addWidget(self.free_track_btn)
        track_selector_layout.addWidget(self.premium_track_btn)
        track_selector_layout.addWidget(self.both_tracks_btn)
        track_selector_layout.addStretch()
        
        main_layout.addLayout(track_selector_layout)

        # Horizontal Scroll Area for Tiers
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: transparent; 
            }
            QScrollBar:horizontal {
                border: none;
                background: #2a2a2a;
                height: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background: #e67e22;
                border-radius: 7px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #d35400;
            }
        """)
        
        self.tiers_container = QWidget()
        self.tiers_layout = QHBoxLayout(self.tiers_container)
        self.tiers_layout.setContentsMargins(10, 15, 10, 15)  # Better margins for readability
        self.tiers_layout.setSpacing(15)  # Increased spacing between tiers for better separation
        
        scroll_area.setWidget(self.tiers_container)
        scroll_area.setMinimumHeight(480)  # Increased height with space saved from compact header
        main_layout.addWidget(scroll_area)

        # Load placeholder data
        self.current_view = 'both'
        self._load_placeholder_tiers(50, current_tier=5, premium_active=False)
    
    def resizeEvent(self, event):
        """Handle resize events to make the layout more responsive."""
        super().resizeEvent(event)
        
        # Adjust premium section layout based on width
        if hasattr(self, 'purchase_pass_button'):
            available_width = self.width()
            if available_width < 900:  # Small screens - stack vertically
                self._make_premium_section_compact()
            else:  # Larger screens - keep horizontal
                self._make_premium_section_horizontal()
        
        # Adjust tier card sizes based on available width
        if hasattr(self, 'tiers_layout'):
            available_width = self.width() - 100  # Account for margins and scrollbar
            if available_width > 1400:  # Large screens
                self._update_tier_card_sizes(280, 18)
            elif available_width > 1000:  # Medium screens
                self._update_tier_card_sizes(250, 15)
            else:  # Small screens
                self._update_tier_card_sizes(220, 12)
    
    def _update_tier_card_sizes(self, card_width, spacing):
        """Update tier card sizes and spacing for responsive design."""
        self.tiers_layout.setSpacing(spacing)
        # Update existing tier cards
        for i in range(self.tiers_layout.count()):
            item = self.tiers_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'setMaximumWidth'):
                    widget.setMaximumWidth(card_width)
                    widget.setMinimumWidth(min(220, card_width - 20))
    
    def _make_premium_section_compact(self):
        """Make premium section more compact for small screens."""
        if hasattr(self, 'purchase_pass_button'):
            self.purchase_pass_button.setText("1,000 🪙")
            self.purchase_pass_button.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    background-color: #f39c12;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 9pt;
                    min-width: 80px;
                    max-height: 32px;
                }
                QPushButton:hover {
                    background-color: #e67e22;
                }
                QPushButton:pressed {
                    background-color: #d35400;
                }
                QPushButton:disabled {
                    background-color: #27ae60;
                    color: white;
                }
            """)
    
    def _make_premium_section_horizontal(self):
        """Make premium section horizontal for larger screens."""
        if hasattr(self, 'purchase_pass_button'):
            self.purchase_pass_button.setText("Unlock for 1,000 🪙")
            self.purchase_pass_button.setStyleSheet("""
                QPushButton {
                    padding: 8px 16px;
                    background-color: #f39c12;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 10pt;
                    min-width: 140px;
                    max-height: 36px;
                }
                QPushButton:hover {
                    background-color: #e67e22;
                }
                QPushButton:pressed {
                    background-color: #d35400;
                }
                QPushButton:disabled {
                    background-color: #27ae60;
                    color: white;
                }
            """)

    def set_track_view(self, view_type):
        """Set which track(s) to display."""
        self.current_view = view_type
        
        # Update button states
        self.free_track_btn.setChecked(view_type == 'free')
        self.premium_track_btn.setChecked(view_type == 'premium')
        self.both_tracks_btn.setChecked(view_type == 'both')
        
        # Reload tiers with new view
        current_tier = int(self.season_progress_label.text().split("Your Tier: ")[1].split(" / ")[0])
        num_tiers = int(self.season_progress_label.text().split(" / ")[1].split(" | ")[0])
        self._load_placeholder_tiers(num_tiers, current_tier, self.premium_active)

    def _load_placeholder_tiers(self, num_tiers, current_tier=0, premium_active=False):
        """Populates the horizontal tiers view with placeholder data."""
        # Clear existing tiers
        while self.tiers_layout.count():
            child = self.tiers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create tier widgets horizontally
        for i in range(1, min(num_tiers + 1, 21)):  # Limit to 20 tiers for demo
            unlocked = i <= current_tier
            
            # Create different reward types for variety including TrackCoins
            if i % 5 == 0:
                free_reward = {"name": f"Milestone Reward", "type": "XP Boost", "rarity": "epic", "icon": "🏆"}
            elif i % 3 == 0:
                free_reward = {"name": f"{i*25} TrackCoins", "type": "Currency", "rarity": "common", "icon": "🪙"}
            else:
                free_reward = {"name": f"XP Boost +{i*50}", "type": "XP Boost", "rarity": "common", "icon": "⭐"}
            
            # Premium rewards are more frequent and valuable
            if i % 2 == 0:
                if i % 10 == 0:
                    premium_reward = {"name": f"Legendary Skin", "type": "Cosmetic", "rarity": "legendary", "icon": "👑"}
                elif i % 6 == 0:
                    premium_reward = {"name": f"{i*100} TrackCoins", "type": "Currency", "rarity": "rare", "icon": "🪙"}
                elif i % 5 == 0:
                    premium_reward = {"name": f"Epic Car Decal", "type": "Cosmetic", "rarity": "epic", "icon": "🎨"}
                else:
                    premium_reward = {"name": f"Premium Badge", "type": "Cosmetic", "rarity": "rare", "icon": "💎"}
            else:
                premium_reward = None

            tier_widget = self._create_horizontal_tier_widget(i, free_reward, premium_reward, unlocked, premium_active)
            self.tiers_layout.addWidget(tier_widget)
        
        self.tiers_layout.addStretch()

    def _create_horizontal_tier_widget(self, tier_num, free_reward, premium_reward, unlocked, premium_active):
        """Creates a widget for a single tier in the horizontal Race Pass."""
        tier_frame = QFrame()
        tier_frame.setObjectName(f"TierFrame{tier_num}")
        tier_frame.setFrameShape(QFrame.Shape.StyledPanel)
        tier_frame.setFrameShadow(QFrame.Shadow.Raised)
        tier_frame.setMinimumWidth(220)  # Increased minimum width for better text readability
        tier_frame.setMaximumWidth(280)  # Allow more flexibility
        tier_frame.setMinimumHeight(380)  # Increased height for better content fit with larger reward boxes
        
        # Styling based on unlock status
        if unlocked:
            tier_frame.setStyleSheet("""
                QFrame {
                    background-color: #3a3a3a;
                    border: 2px solid #e67e22;
                    border-radius: 12px;
                    padding: 10px;
                }
            """)
        else:
            tier_frame.setStyleSheet("""
                QFrame {
                    background-color: #2c2c2c;
                    border: 2px solid #555;
                    border-radius: 12px;
                    padding: 10px;
                }
            """)

        layout = QVBoxLayout(tier_frame)
        layout.setSpacing(10)

        # Tier number at top
        tier_label = QLabel(f"TIER {tier_num}")
        tier_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        tier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if unlocked: 
            tier_label.setStyleSheet("color: #e67e22; background-color: #1a1a1a; padding: 5px; border-radius: 5px;")
        else:
            tier_label.setStyleSheet("color: #888; background-color: #1a1a1a; padding: 5px; border-radius: 5px;")
        layout.addWidget(tier_label)

        # Show rewards based on current view
        if self.current_view in ['free', 'both']:
            free_widget = self._create_horizontal_reward_display("FREE", free_reward, unlocked, False)
            layout.addWidget(free_widget)
        
        if self.current_view in ['premium', 'both'] and premium_reward:
            premium_widget = self._create_horizontal_reward_display("PREMIUM", premium_reward, unlocked and premium_active, True, premium_active)
            layout.addWidget(premium_widget)
        elif self.current_view == 'premium' and not premium_reward:
            # Empty premium slot
            empty_widget = QLabel("No Premium\nReward")
            empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_widget.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            layout.addWidget(empty_widget)

        layout.addStretch()
        return tier_frame

    def _create_horizontal_reward_display(self, track_type, reward_data, is_unlocked, is_premium, premium_active=False):
        """Creates a display for a single reward in horizontal layout."""
        reward_widget = QFrame()
        reward_widget.setMinimumHeight(130)  # Increased minimum height for better text fit
        reward_widget.setMaximumHeight(160)  # Allow more flexibility for future images
        
        # Styling based on track type and unlock status
        if is_premium and premium_active:
            border_color = "#FFD700"  # Bright gold for premium
        elif is_premium and not premium_active:
            border_color = "#666"     # Gray for locked premium
        else:
            border_color = "#32CD32"  # Bright green for free
            
        if is_unlocked or (is_premium and premium_active):
            bg_color = "#1a1a1a"
        else:
            bg_color = "#0f0f0f"
            
        # Add gradient effect for better visual appeal
        if is_unlocked or (is_premium and premium_active):
            gradient_bg = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {bg_color}, stop:1 rgba(26, 26, 26, 0.8))"
        else:
            gradient_bg = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {bg_color}, stop:1 rgba(15, 15, 15, 0.8))"
        
        reward_widget.setStyleSheet(f"""
            QFrame {{
                background: {gradient_bg};
                border: 3px solid {border_color};
                border-radius: 10px;
                padding: 8px;
            }}
        """)
        
        reward_layout = QVBoxLayout(reward_widget)
        reward_layout.setContentsMargins(10, 10, 10, 10)
        reward_layout.setSpacing(6)

        # Track type label
        track_label_text = track_type
        if is_premium and not premium_active:
            track_label_text += " 🔒"
        
        track_label = QLabel(track_label_text)
        track_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))  # Increased font size for better readability
        track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        track_label.setFixedHeight(25)  # Fixed height for consistent layout
        
        if is_premium and premium_active:
            track_label.setStyleSheet("""
                color: #FFD700; 
                font-weight: bold; 
                background-color: rgba(255, 215, 0, 0.2); 
                border: 1px solid rgba(255, 215, 0, 0.5);
                border-radius: 5px; 
                padding: 4px;
            """)
        elif is_premium and not premium_active:
            track_label.setStyleSheet("""
                color: #888; 
                font-weight: bold;
                background-color: rgba(136, 136, 136, 0.1);
                border: 1px solid rgba(136, 136, 136, 0.3);
                border-radius: 5px; 
                padding: 4px;
            """)
        else:
            track_label.setStyleSheet("""
                color: #32CD32; 
                font-weight: bold; 
                background-color: rgba(50, 205, 50, 0.2); 
                border: 1px solid rgba(50, 205, 50, 0.5);
                border-radius: 5px; 
                padding: 4px;
            """)
        
        reward_layout.addWidget(track_label)

        # Reward icon (placeholder for future image support)
        icon_container = QFrame()
        icon_container.setFixedHeight(50)
        icon_container.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        reward_icon = QLabel(reward_data.get("icon", "🎁"))
        reward_icon.setFont(QFont("Arial", 24))  # Larger icon for better visibility
        reward_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(reward_icon)
        reward_layout.addWidget(icon_container)
        
        # Reward name with better formatting
        reward_name = QLabel(reward_data["name"])
        reward_name.setFont(QFont("Arial", 13, QFont.Weight.Bold))  # Larger font for better readability
        reward_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reward_name.setWordWrap(True)
        reward_name.setMinimumHeight(50)  # More space for text
        reward_name.setMaximumHeight(70)  # Allow more space for longer names
        
        if is_unlocked or (is_premium and premium_active):
            reward_name.setStyleSheet("""
                color: white; 
                font-weight: bold; 
                background-color: rgba(255, 255, 255, 0.1); 
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px; 
                padding: 6px;
                line-height: 1.2;
            """)
        else:
            reward_name.setStyleSheet("""
                color: #BBB; 
                font-weight: bold;
                background-color: rgba(187, 187, 187, 0.05);
                border: 1px solid rgba(187, 187, 187, 0.1);
                border-radius: 6px; 
                padding: 6px;
                line-height: 1.2;
            """)
            
        reward_layout.addWidget(reward_name)
        
        return reward_widget

    def on_purchase_pass(self):
        """Handle premium pass purchase using TrackCoins."""
        if self.premium_active:
            return
        
        # Check if user has enough TrackCoins
        required_coins = 1000
        current_balance = self.trackcoins_balance.balance
        
        if current_balance >= required_coins:
            # Confirm purchase
            reply = QMessageBox.question(self, "Unlock Premium Race Pass", 
                                       f"Unlock Premium Race Pass for {required_coins:,} TrackCoins?\n\n"
                                       f"Current balance: {current_balance:,} 🪙\n"
                                       f"After purchase: {current_balance - required_coins:,} 🪙\n\n"
                                       f"You'll get:\n"
                                       f"• Exclusive premium rewards\n"
                                       f"• Double XP progression\n"
                                       f"• Premium cosmetics\n"
                                       f"• Access for entire season",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                # Spend TrackCoins and activate premium
                self.trackcoins_balance.update_balance(current_balance - required_coins)
                self._activate_premium_track()
                
                QMessageBox.information(self, "Premium Unlocked!", 
                                       f"🎉 Premium Race Pass unlocked!\n\n"
                                       f"Spent: {required_coins:,} 🪙\n"
                                       f"Remaining balance: {current_balance - required_coins:,} 🪙")
        else:
            # Not enough TrackCoins
            needed = required_coins - current_balance
            QMessageBox.warning(self, "Insufficient TrackCoins", 
                               f"You need {required_coins:,} TrackCoins to unlock the Premium Race Pass.\n\n"
                               f"Current balance: {current_balance:,} 🪙\n"
                               f"You need {needed:,} more TrackCoins.\n\n"
                               f"Would you like to purchase TrackCoins?")
            
            # Open TrackCoins store
            self.open_trackcoins_store()
    
    def open_trackcoins_store(self):
        """Open the TrackCoins store."""
        from .trackcoins_store import TrackCoinsStoreWidget
        
        # Create store dialog
        store_dialog = QDialog(self)
        store_dialog.setWindowTitle("TrackCoins Store")
        store_dialog.setModal(True)
        store_dialog.resize(800, 600)
        
        layout = QVBoxLayout(store_dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create store widget
        store_widget = TrackCoinsStoreWidget()
        store_widget.set_balance(self.trackcoins_balance.balance)  # Set current balance
        
        # Connect signals
        store_widget.coins_purchased.connect(self._on_coins_purchased)
        
        layout.addWidget(store_widget)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(store_dialog.accept)
        layout.addWidget(close_btn)
        
        store_dialog.exec()
    
    def _on_coins_purchased(self, coins):
        """Handle when TrackCoins are purchased."""
        current_balance = self.trackcoins_balance.balance
        new_balance = current_balance + coins
        self.trackcoins_balance.update_balance(new_balance)
    
    def _activate_premium_track(self):
        """Activate premium track (called after successful payment)."""
        self.premium_active = True
        self.purchase_pass_button.setText("Premium Pass Active ✓")
        self.purchase_pass_button.setEnabled(False)
        
        # Update premium track button availability
        self.premium_track_btn.setEnabled(True)
        
        # Re-render tiers with premium active
        current_tier = int(self.season_progress_label.text().split("Your Tier: ")[1].split(" / ")[0])
        num_tiers = int(self.season_progress_label.text().split(" / ")[1].split(" | ")[0])
        self._load_placeholder_tiers(num_tiers, current_tier, premium_active=True)
        
        # Show success message
        QMessageBox.information(self, "Premium Unlocked!", 
                               "🎉 Premium Race Pass subscription activated!\n\n"
                               "You now have access to:\n"
                               "• Exclusive premium rewards\n"
                               "• Double XP progression\n"
                               "• Premium cosmetics\n"
                               "• Special milestone rewards\n\n"
                               "Subscription: $9.99/month")


class RacePassViewWidget(QWidget):
    """Main Race Pass widget with tabbed interface like Fortnite's battle pass."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RacePassViewWidget")
        
        # Set minimum size to ensure tabs display properly
        self.setMinimumSize(800, 600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Main title
        title_label = QLabel("Race Pass")
        title_font = QFont("Arial", 20, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #e67e22; margin-bottom: 15px;")
        main_layout.addWidget(title_label)

        # Create tab widget for different sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(600)  # Ensure minimum height
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #222;
                border-radius: 3px;
                margin-top: 15px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #333;
                color: #CCC;
                padding: 12px 30px;
                margin-right: 3px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-size: 13pt;
                font-weight: bold;
                min-width: 100px;
                min-height: 30px;
                max-width: 150px;
            }
            QTabBar::tab:selected {
                background-color: #444;
                color: white;
                border-bottom: 3px solid #e67e22;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
                color: #e67e22;
            }
            QTabBar {
                qproperty-drawBase: 0;
                font-size: 13pt;
            }
        """)

        # Create the four main tabs
        
        # 1. Overview Tab
        self.overview_widget = RacePassOverviewWidget(self)
        self.tab_widget.addTab(self.overview_widget, "Overview")
        
        # 2. Race Pass Track Tab
        self.race_pass_track_widget = RacePassTrackWidget(self)
        self.tab_widget.addTab(self.race_pass_track_widget, "Pass")
        
        # 3. TrackCoins Store Tab
        from .trackcoins_store import TrackCoinsStoreWidget
        self.trackcoins_store_widget = TrackCoinsStoreWidget(self)
        self.tab_widget.addTab(self.trackcoins_store_widget, "TrackCoins")
        
        # 4. Quests Tab
        self.quests_widget = EnhancedQuestViewWidget(self)
        self.tab_widget.addTab(self.quests_widget, "Quests")
        
        # Connect TrackCoins signals
        self.trackcoins_store_widget.coins_purchased.connect(self._on_trackcoins_purchased)

        main_layout.addWidget(self.tab_widget)

        # Load initial data
        self.load_race_pass_data()

    def showEvent(self, event):
        """Handle show event to ensure proper sizing."""
        super().showEvent(event)
        # Force the tab widget to update its size
        self.tab_widget.updateGeometry()
        self.updateGeometry()

    def load_race_pass_data(self):
        """Load race pass data from Supabase with fallback to offline mode."""
        try:
            # Try to load real data from Supabase if available
            from ..supabase_gamification import get_current_season, get_user_race_pass_progress
            
            # Check if we have network connectivity
            try:
                season_result = get_current_season()
                progress_result = get_user_race_pass_progress()
                
                if season_result[0] and progress_result[0]:
                    # We have real data, use it
                    season_data = season_result[0]
                    user_progress = progress_result[0]
                    
                    stats = {
                        'quests_completed': user_progress.get('quests_completed', 0),
                        'total_xp': user_progress.get('total_xp', 0),
                        'rewards_claimed': user_progress.get('rewards_claimed', 0),
                        'rewards_available': user_progress.get('rewards_available', 0)
                    }
                    
                    self.overview_widget.update_overview_data(season_data, user_progress, stats)
                    return
                    
            except Exception as network_error:
                # Network error - fall back to offline mode
                print(f"Race Pass: Network error, using offline mode: {network_error}")
                
        except ImportError as import_error:
            # Supabase modules not available - use offline mode
            print(f"Race Pass: Supabase not available, using offline mode: {import_error}")
        except Exception as e:
            # Any other error - use offline mode
            print(f"Race Pass: Error loading data, using offline mode: {e}")
        
        # Fallback to placeholder data (offline mode)
        season_data = {
            'name': 'Season 1: Genesis (Offline Mode)',
            'ends_in_days': 28
        }
        
        user_progress = {
            'current_tier': 5,
            'max_tier': 50,
            'tier_progress': 65,
            'current_xp': 1250,
            'next_tier_xp': 2000
        }
        
        stats = {
            'quests_completed': 12,
            'total_xp': 5420,
            'rewards_claimed': 8,
            'rewards_available': 15
        }
        
        self.overview_widget.update_overview_data(season_data, user_progress, stats)
    
    def _on_trackcoins_purchased(self, coins):
        """Handle when TrackCoins are purchased from the store tab."""
        # Update the balance in the race pass track widget
        if hasattr(self.race_pass_track_widget, 'trackcoins_balance'):
            current_balance = self.race_pass_track_widget.trackcoins_balance.balance
            new_balance = current_balance + coins
            self.race_pass_track_widget.trackcoins_balance.update_balance(new_balance)

    def update_race_pass_data(self, season_info, tiers_data, user_progress):
        """
        Updates the entire Race Pass view with new data.
        This method maintains compatibility with existing code.
        """
        # Update the race pass track widget
        if hasattr(self.race_pass_track_widget, 'update_race_pass_data'):
            self.race_pass_track_widget.update_race_pass_data(season_info, tiers_data, user_progress)
        
        # Update overview
        stats = {
            'quests_completed': user_progress.get('quests_completed', 0),
            'total_xp': user_progress.get('total_xp', 0),
            'rewards_claimed': user_progress.get('rewards_claimed', 0),
            'rewards_available': len(tiers_data) if tiers_data else 0
        }
        self.overview_widget.update_overview_data(season_info, user_progress, stats)


# Example usage (for testing standalone)
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    # Set a dark theme for testing
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    app.setPalette(dark_palette)

    main_window = QMainWindow()
    race_pass_view = RacePassViewWidget()
    main_window.setCentralWidget(race_pass_view)
    main_window.setWindowTitle("Race Pass View Test")
    main_window.setGeometry(100, 100, 1000, 800)
    main_window.show()

    sys.exit(app.exec()) 