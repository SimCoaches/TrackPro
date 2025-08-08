from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QGridLayout, 
                             QProgressBar, QGroupBox, QTabWidget, QSplitter, QSizePolicy,
                             QMessageBox, QDialog, QLineEdit, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter
import json
import logging

logger = logging.getLogger(__name__)

# Import Stripe integration with fallback
try:
    from ..stripe_integration import stripe_processor, process_race_pass_payment, create_race_pass_checkout
except ImportError:
    logger.warning("Stripe integration not available. Payment features will be disabled.")
    stripe_processor = None
    process_race_pass_payment = None
    create_race_pass_checkout = None

class TrackCoinsStoreWidget(QWidget):
    """TrackCoins store widget for purchasing virtual currency."""
    
    coins_purchased = pyqtSignal(int)  # Signal emitted when coins are purchased
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TrackCoinsStoreWidget")
        self.user_trackcoins = 0  # Current user balance
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("TrackCoins Store")
        title_font = QFont("Arial", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #f39c12; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Current balance display
        balance_frame = self._create_balance_display()
        main_layout.addWidget(balance_frame)
        
        # TrackCoins packages
        packages_frame = self._create_packages_section()
        main_layout.addWidget(packages_frame)
        
        # Info section
        info_frame = self._create_info_section()
        main_layout.addWidget(info_frame)
        
        main_layout.addStretch()
    
    def _create_balance_display(self):
        """Create the current balance display."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 2px solid #f39c12;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        
        # TrackCoins icon and balance
        coin_icon = QLabel("🪙")
        coin_icon.setFont(QFont("Arial", 24))
        layout.addWidget(coin_icon)
        
        balance_layout = QVBoxLayout()
        balance_title = QLabel("Your TrackCoins")
        balance_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        balance_title.setStyleSheet("color: #f39c12;")
        
        self.balance_label = QLabel(f"{self.user_trackcoins:,}")
        self.balance_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.balance_label.setStyleSheet("color: white;")
        
        balance_layout.addWidget(balance_title)
        balance_layout.addWidget(self.balance_label)
        layout.addLayout(balance_layout)
        
        layout.addStretch()
        
        # Quick purchase button
        quick_buy_btn = QPushButton("Quick Buy 1,000 🪙")
        quick_buy_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        quick_buy_btn.clicked.connect(lambda: self.purchase_trackcoins(1000, 9.99))
        layout.addWidget(quick_buy_btn)
        
        return frame
    
    def _create_packages_section(self):
        """Create the TrackCoins packages section."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # Section title
        section_title = QLabel("TrackCoins Packages")
        section_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #FFF; margin-bottom: 10px;")
        layout.addWidget(section_title)
        
        # Packages grid
        packages_layout = QGridLayout()
        packages_layout.setSpacing(10)
        
        # Define packages (coins, price, bonus_text, popular)
        packages = [
            (500, 4.99, "", False),
            (1000, 9.99, "+100 Bonus!", False),
            (2500, 19.99, "+500 Bonus!", True),  # Most popular
            (5000, 39.99, "+1000 Bonus!", False),
            (10000, 79.99, "+2500 Bonus!", False),
            (25000, 149.99, "+7500 Bonus!", False)
        ]
        
        for i, (coins, price, bonus, popular) in enumerate(packages):
            package_widget = self._create_package_widget(coins, price, bonus, popular)
            row = i // 3
            col = i % 3
            packages_layout.addWidget(package_widget, row, col)
        
        layout.addLayout(packages_layout)
        return frame
    
    def _create_package_widget(self, coins, price, bonus_text, popular=False):
        """Create a single package widget."""
        frame = QFrame()
        
        if popular:
            frame.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border: 3px solid #f39c12;
                    border-radius: 12px;
                    padding: 15px;
                }
            """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border: 2px solid #555;
                    border-radius: 12px;
                    padding: 15px;
                }
            """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Popular badge
        if popular:
            popular_label = QLabel("MOST POPULAR")
            popular_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            popular_label.setStyleSheet("""
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 4px;
                border-radius: 4px;
                margin-bottom: 5px;
            """)
            layout.addWidget(popular_label)
        
        # Coin icon and amount
        coin_layout = QHBoxLayout()
        coin_icon = QLabel("🪙")
        coin_icon.setFont(QFont("Arial", 20))
        coin_layout.addWidget(coin_icon)
        
        coin_amount = QLabel(f"{coins:,}")
        coin_amount.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        coin_amount.setStyleSheet("color: #f39c12;")
        coin_layout.addWidget(coin_amount)
        coin_layout.addStretch()
        layout.addLayout(coin_layout)
        
        # Bonus text
        if bonus_text:
            bonus_label = QLabel(bonus_text)
            bonus_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bonus_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 10pt;")
            layout.addWidget(bonus_label)
        
        # Price
        price_label = QLabel(f"${price:.2f}")
        price_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_label.setStyleSheet("color: white; margin: 5px 0;")
        layout.addWidget(price_label)
        
        # Purchase button
        purchase_btn = QPushButton("Purchase")
        purchase_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        purchase_btn.clicked.connect(lambda: self.purchase_trackcoins(coins, price))
        layout.addWidget(purchase_btn)
        
        return frame
    
    def _create_info_section(self):
        """Create the info section about TrackCoins."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # Section title
        section_title = QLabel("About TrackCoins")
        section_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #FFF; margin-bottom: 10px;")
        layout.addWidget(section_title)
        
        # Info text
        info_text = QLabel("""
• TrackCoins are TrackPro's virtual currency
• Use TrackCoins to unlock Race Pass (1,000 🪙)
• Earn TrackCoins through quests and achievements
• Purchase TrackCoins to unlock premium content instantly
• TrackCoins never expire and carry over between seasons
        """)
        info_text.setStyleSheet("color: #CCC; line-height: 1.4;")
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        return frame
    
    def purchase_trackcoins(self, coins, price):
        """Handle TrackCoins purchase."""
        # Check if Stripe is available and configured
        if not create_race_pass_checkout:
            # Fallback to demo mode
            QMessageBox.information(self, "Demo Mode", 
                                   f"Stripe is not configured. Running in demo mode.\n\n"
                                   f"Purchased {coins:,} TrackCoins for ${price:.2f}!")
            self._add_trackcoins(coins)
            return
        
        try:
            # Create Stripe Checkout session for TrackCoins
            user_email = "user@example.com"  # Replace with actual user email from auth
            success, checkout_data = self._create_trackcoins_checkout(user_email, coins, price)
            
            if success:
                # Open Stripe Checkout directly in browser
                import webbrowser
                checkout_url = checkout_data.get('checkout_url')
                webbrowser.open(checkout_url)
                
                # For demo purposes, simulate successful payment
                QMessageBox.information(self, "Demo Mode", 
                                       f"In a real implementation, the user would complete payment on Stripe's secure checkout page.\n\n"
                                       f"For demo purposes, adding {coins:,} TrackCoins now...")
                self._add_trackcoins(coins)
                    
            else:
                error_msg = checkout_data.get('error', 'Unknown error occurred')
                QMessageBox.critical(self, "Checkout Error", 
                                   f"Could not create checkout session:\n{error_msg}")
                
        except Exception as e:
            QMessageBox.critical(self, "Payment Error", 
                               f"An error occurred:\n{str(e)}")
    
    def _create_trackcoins_checkout(self, user_email, coins, price):
        """Create Stripe checkout session for TrackCoins purchase."""
        # This would integrate with your Stripe system
        # For now, return demo data
        return True, {"checkout_url": "https://checkout.stripe.com/demo"}
    
    def _add_trackcoins(self, coins):
        """Add TrackCoins to user balance."""
        try:
            # Persist balance via server (optional top-up path)
            from ..supabase_gamification import supabase
            user = supabase.get_user()
            user_id = getattr(user, 'id', None) or (getattr(user, 'user', None).id if getattr(user, 'user', None) else None)
            if user_id:
                # Use add_trackcoins by calling spend/add pair or direct table update if allowed
                res = supabase.client.rpc('add_trackcoins', {
                    'p_user_id': user_id,
                    'p_amount': coins,
                    'p_reason': 'store_topup'
                }).execute()
        except Exception:
            pass
        self.user_trackcoins += coins
        self.balance_label.setText(f"{self.user_trackcoins:,}")
        self.coins_purchased.emit(coins)
        
        # Show success message
        QMessageBox.information(self, "Purchase Successful!", 
                               f"🎉 Successfully purchased {coins:,} TrackCoins!\n\n"
                               f"New balance: {self.user_trackcoins:,} 🪙")
    
    def spend_trackcoins(self, amount):
        """Spend TrackCoins (returns True if successful)."""
        try:
            from ..supabase_gamification import spend_trackcoins
            ok, _ = spend_trackcoins(amount, 'store_purchase')
            if ok:
                self.user_trackcoins = max(0, self.user_trackcoins - amount)
                self.balance_label.setText(f"{self.user_trackcoins:,}")
                return True
            return False
        except Exception:
            # Fallback to local balance
            if self.user_trackcoins >= amount:
                self.user_trackcoins -= amount
                self.balance_label.setText(f"{self.user_trackcoins:,}")
                return True
            return False
    
    def get_balance(self):
        """Get current TrackCoins balance."""
        return self.user_trackcoins
    
    def set_balance(self, amount):
        """Set TrackCoins balance (for loading from database)."""
        self.user_trackcoins = amount
        self.balance_label.setText(f"{self.user_trackcoins:,}")


class TrackCoinsBalanceWidget(QWidget):
    """Small widget to display TrackCoins balance in other parts of the app."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.balance = 0
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Coin icon
        coin_icon = QLabel("🪙")
        coin_icon.setFont(QFont("Arial", 14))
        layout.addWidget(coin_icon)
        
        # Balance
        self.balance_label = QLabel("0")
        self.balance_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.balance_label.setStyleSheet("color: #f39c12;")
        layout.addWidget(self.balance_label)
        
        # Style the widget
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(243, 156, 18, 0.1);
                border: 1px solid #f39c12;
                border-radius: 6px;
            }
        """)
        
        self.setMaximumWidth(100)
    
    def update_balance(self, balance):
        """Update the displayed balance."""
        self.balance = balance
        self.balance_label.setText(f"{balance:,}") 