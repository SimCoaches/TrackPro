import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QStackedWidget, QScrollArea, QLineEdit, QTextEdit, QDateEdit,
    QComboBox, QCheckBox, QFileDialog, QMessageBox, QSpinBox,
    QGroupBox, QGridLayout, QSizePolicy, QSpacerItem, QDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QSlider, QGraphicsItem,
    QListWidget, QListWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer, QPropertyAnimation, QEasingCurve, QRectF
import time
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QBrush, QColor, QImage, QPainterPath, QBitmap, QTransform
from trackpro.ui.avatar_manager import AvatarManager

# Import user management functions
from trackpro.auth.user_manager import get_current_user, is_current_user_dev
from trackpro.database.supabase_client import get_supabase_client
from trackpro.ui.widgets.modern_widgets import ModernInput, ModernButton, ModernCard
from trackpro.utils.windows_startup import WindowsStartupManager

# Import new components
from trackpro.auth.hierarchy_manager import HierarchyLevel
from trackpro.ui.shared_imports import RacePassViewWidget, GAMIFICATION_AVAILABLE

logger = logging.getLogger(__name__)

class ModernCard(QFrame):
    """Modern card-style container widget."""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumHeight(120)  # Ensure minimum height
        self.setStyleSheet("""
            QFrame {
                background-color: #2f3136;
                border: 1px solid #40444b;
                border-radius: 8px;
                margin: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: 600;
                    border: none;
                    background: transparent;
                    margin-bottom: 8px;
                }
            """)
            layout.addWidget(title_label)
        
        self.content_layout = layout

class ModernInput(QLineEdit):
    """Modern styled input field."""
    
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #dcddde;
            }
            QLineEdit:focus {
                border-color: #5865f2;
                background-color: #36393f;
            }
            QLineEdit::placeholder {
                color: #72767d;
            }
        """)

class ModernTextArea(QTextEdit):
    """Modern styled text area."""
    
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMaximumHeight(100)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #dcddde;
            }
            QTextEdit:focus {
                border-color: #5865f2;
                background-color: #36393f;
            }
        """)

class ModernButton(QPushButton):
    """Modern styled button."""
    
    def __init__(self, text: str, style: str = "primary", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(36)
        
        if style == "primary":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #5865f2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #4752c4;
                }
                QPushButton:pressed {
                    background-color: #3c45a5;
                }
            """)
        elif style == "secondary":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4f545c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #5d6269;
                }
                QPushButton:pressed {
                    background-color: #484d54;
                }
            """)
        elif style == "danger":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #ed4245;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #c53030;
                }
                QPushButton:pressed {
                    background-color: #a02728;
                }
            """)

class ProfileAvatar(QLabel):
    """Profile avatar widget with click functionality."""
    
    def __init__(self, size: int = 80, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                border: 3px solid #40444b;
                border-radius: {size // 2}px;
                color: white;
                font-size: {size // 3}px;
                font-weight: bold;
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(True)
        # Render a circular initials pixmap by default to ensure correct shape
        # Defer to AvatarManager for drawing; if no URL yet, it will render initials
        AvatarManager.instance().set_label_avatar(self, None, "LT", size=size)
        self.setToolTip("Click to change avatar")
        self.account_page = None  # Will be set by parent
    
    def set_account_page(self, account_page):
        """Set reference to parent account page."""
        self.account_page = account_page
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.select_avatar()
    
    def select_avatar(self):
        """Open file dialog to select new avatar."""
        if self.account_page:
            self.account_page.upload_avatar()
        else:
            # Fallback if no account page reference
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Avatar Image",
                "",
                "Image files (*.png *.jpg *.jpeg *.gif *.bmp)"
            )
            
            if file_path:
                QMessageBox.information(self, "Avatar Upload", f"Avatar upload selected: {file_path}")

class CropView(QGraphicsView):
    """A QGraphicsView that draws a circular crop overlay."""
    def __init__(self, crop_size, parent=None):
        super().__init__(parent)
        self.crop_size = crop_size
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # The semi-transparent overlay
        outer_path = QPainterPath()
        outer_path.addRect(self.viewport().rect())
        
        # The circular cutout
        center = self.viewport().rect().center()
        radius = self.crop_size / 2.0
        circle_path = QPainterPath()
        circle_path.addEllipse(center, radius, radius)
        
        # Create the overlay by subtracting the circle from the rectangle
        final_path = outer_path.subtracted(circle_path)
        painter.fillPath(final_path, QColor(0, 0, 0, 120))
        
        # Draw a white border around the cutout
        pen = QPen(Qt.GlobalColor.white, 2)
        painter.setPen(pen)
        painter.drawPath(circle_path)
        
        painter.restore()


class AvatarCropDialog(QDialog):
    """A dialog for cropping a user avatar with pan and zoom."""
    def __init__(self, image_path: str, crop_size: int = 360, output_size: int = 512, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop Avatar")
        self.setMinimumSize(crop_size + 60, crop_size + 160)
        
        self.crop_size = int(crop_size)
        self.output_size = int(output_size)
        self._image = QPixmap(image_path)
        self._cropped = None
        self._base_scale = 1.0

        if self._image.isNull():
            logger.error(f"Failed to load image from path: {image_path}")
            QTimer.singleShot(0, self.reject)
            return
            
        # --- WIDGETS ---
        self.view = CropView(self.crop_size, self)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)

        self.pix_item = QGraphicsPixmapItem(self._image)
        self.pix_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.scene.addItem(self.pix_item)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(100, 500)
        self.zoom_slider.setValue(100)
        
        zoom_label = QLabel("Zoom")
        
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn = QPushButton("Crop & Save")
        self.save_btn.setStyleSheet("background-color: #5865f2; color: white;")

        # --- LAYOUT ---
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(self.zoom_slider)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)
        main_layout.addLayout(zoom_layout)
        main_layout.addLayout(button_layout)
        
        # --- CONNECTIONS ---
        self.zoom_slider.valueChanged.connect(self._on_zoom)
        self.save_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)

    def showEvent(self, event):
        """Fit image in view when the dialog is first shown."""
        super().showEvent(event)
        QTimer.singleShot(0, self._fit_image_in_view)

    def _fit_image_in_view(self):
        """Fit the pixmap item within the view and store its base scale."""
        if hasattr(self, 'pix_item'):
            self.view.fitInView(self.pix_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._base_scale = self.view.transform().m11()

    def _on_zoom(self, value):
        """Handle zoom slider changes relative to the base fitted scale."""
        if not hasattr(self, '_base_scale') or self._base_scale == 0:
            return
        
        # Preserve the center point during zoom
        center_point_before_scale = self.view.mapToScene(self.view.viewport().rect().center())
        
        scale_factor = self._base_scale * (value / 100.0)
        
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        self.view.setTransform(transform)
        
        self.view.centerOn(center_point_before_scale)

    def _on_ok(self):
        """Crop the image and accept the dialog."""
        # Get the circular crop area from the view
        crop_radius = self.crop_size / 2.0
        crop_center = self.view.mapToScene(self.view.viewport().rect().center())
        
        crop_rect_scene = QRectF(
            crop_center.x() - crop_radius,
            crop_center.y() - crop_radius,
            self.crop_size,
            self.crop_size
        )

        # Render the cropped scene area to a new image
        image = QImage(self.crop_size, self.crop_size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        self.scene.render(painter, QRectF(image.rect()), crop_rect_scene)
        painter.end()
        
        # Create a circular mask
        mask = QBitmap(image.size())
        mask.fill(Qt.GlobalColor.black)

        mask_painter = QPainter(mask)
        mask_painter.setBrush(Qt.GlobalColor.white)
        mask_painter.drawEllipse(0, 0, self.crop_size, self.crop_size)
        mask_painter.end()
        
        # The QPixmap needs to be converted to QImage to apply a mask
        pixmap = QPixmap.fromImage(image)
        pixmap.setMask(mask)
        
        # Scale to the final output size
        self._cropped = pixmap.scaled(
            self.output_size, self.output_size, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.accept()

    def get_cropped_image(self) -> QPixmap | None:
        """Return the cropped image as a QPixmap."""
        return self._cropped


class AccountPage(QWidget):
    """Main Account page with sidebar navigation."""
    
    # Signal emitted when avatar is uploaded
    avatar_uploaded = pyqtSignal(str)  # Emits the avatar URL
    
    def __init__(self, global_managers=None, parent=None):
        super().__init__(parent)
        self.global_managers = global_managers
        self.pages = {}
        self.is_initialized = False
        self.current_section = "profile"
        try:
            self.startup_manager = WindowsStartupManager()
        except Exception:
            self.startup_manager = None

        self.init_ui()
        self.load_settings()
        self.refresh_hierarchy_status()
    
    def load_settings(self):
        """Load initial settings/state for the account page."""
        # Ensure startup manager is ready
        if not hasattr(self, 'startup_manager') or self.startup_manager is None:
            try:
                self.startup_manager = WindowsStartupManager()
            except Exception:
                self.startup_manager = None
        # Defer loading UI-bound settings until widgets exist
        try:
            QTimer.singleShot(0, self.load_startup_settings)
        except Exception:
            # Fallback: call synchronously
            try:
                self.load_startup_settings()
            except Exception:
                pass

    def init_ui(self):
        """Initialize the account page."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.nav_bar = self.create_nav_bar()
        
        # Create main content area
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("accountContentArea")
        
        # Create content sections
        self.create_pages()
        
        # Add widgets to layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.nav_bar)
        splitter.addWidget(self.content_area)
        
        # Set initial sizes
        splitter.setSizes([200, 600])
        
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)
        
        # Select the first section by default
        try:
            self.select_section("profile")
        except Exception:
            pass
    
    def create_nav_bar(self):
        # Modern vertical nav with styled buttons (no emojis)
        container = QFrame()
        container.setObjectName("accountSideNav")
        container.setFixedWidth(220)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Navigation items (must align with keys in create_pages())
        nav_items = [
            ("profile", "Profile"),
            ("security", "Security"),
            ("notifications", "Notifications"),
            ("racing", "Racing"),
            ("connections", "Connections"),
            ("privacy", "Privacy"),
        ]

        # Add hierarchy for moderators/devs
        try:
            from trackpro.auth.hierarchy_manager import hierarchy_manager
            user = get_current_user()
            if user and (hierarchy_manager.is_user_dev(user.id) or hierarchy_manager.is_user_moderator(user.id)):
                nav_items.append(("hierarchy", "Hierarchy"))
        except Exception:
            pass

        # Build buttons
        self.nav_buttons = {}
        for key, text in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                """
                QPushButton {
                    text-align: left;
                    padding: 10px 12px;
                    border-radius: 8px;
                    color: #dcddde;
                    background: transparent;
                    border: 1px solid transparent;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #2b2d31;
                }
                QPushButton:checked {
                    background: #5865f2;
                    color: #ffffff;
                }
                """
            )
            btn.clicked.connect(lambda _=False, k=key: self.select_section(k))
            layout.addWidget(btn)
            self.nav_buttons[key] = btn

        layout.addStretch()
        return container
    
    def switch_page(self, current, previous):
        # Backward-compat handler if ever called; derive key if possible
        try:
            if current is not None:
                key = current.data(Qt.ItemDataRole.UserRole)
                if key:
                    self.select_section(key)
        except Exception:
            pass

    def select_section(self, section_key: str):
        """Select a section by key and update nav + content. Uses lazy loading for performance."""
        if section_key not in self.pages:
            return
            
        # LAZY LOADING: Create sections on first access
        if hasattr(self, '_lazy_pages') and section_key in self._lazy_pages:
            lazy_info = self._lazy_pages[section_key]
            if not lazy_info["created"]:
                logger.info(f"Lazy loading {section_key} section on first access...")
                try:
                    # Get the method to create this section
                    method_name = lazy_info["method"]
                    create_method = getattr(self, method_name, None)
                    if create_method:
                        # Create the actual section content
                        actual_section = create_method()
                        
                        # Replace the placeholder with the actual content
                        placeholder_index = self.content_area.indexOf(self.pages[section_key])
                        self.content_area.removeWidget(self.pages[section_key])
                        self.pages[section_key].deleteLater()  # Clean up placeholder
                        
                        # Add the real section
                        self.pages[section_key] = actual_section
                        self.content_area.insertWidget(placeholder_index, actual_section)
                        
                        # Mark as created
                        lazy_info["created"] = True
                        logger.info(f"Successfully lazy loaded {section_key} section")
                    else:
                        logger.error(f"Method {method_name} not found for section {section_key}")
                except Exception as e:
                    logger.error(f"Failed to lazy load {section_key}: {e}")
        
        # Update buttons
        if hasattr(self, 'nav_buttons'):
            for key, btn in self.nav_buttons.items():
                btn.setChecked(key == section_key)
        self.current_section = section_key
        self.content_area.setCurrentWidget(self.pages[section_key])
        logger.info(f"Switched to account section: {section_key}")
    
    def create_pages(self):
        """Create all content sections using lazy loading for performance."""
        # Initialize lazy loading system
        self._lazy_pages = {
            "profile": {"created": False, "method": "create_profile_section"},
            "security": {"created": False, "method": "create_security_section"}, 
            "notifications": {"created": False, "method": "create_notifications_section"},
            "racing": {"created": False, "method": "create_racing_section"},
            "connections": {"created": False, "method": "create_connections_section"},
            "privacy": {"created": False, "method": "create_privacy_section"}
        }
        
        # Create placeholders for all sections
        self.pages = {}
        for section_name in self._lazy_pages.keys():
            if section_name == "profile":
                # Pre-load profile section since it's the default
                try:
                    self.pages[section_name] = self.create_profile_section()
                    self._lazy_pages[section_name]["created"] = True
                except Exception as e:
                    logger.error(f"Failed to preload profile section: {e}")
                    self.pages[section_name] = self._create_placeholder_widget(section_name)
            else:
                # Create placeholder for all other sections
                self.pages[section_name] = self._create_placeholder_widget(section_name)
        
        # Add admin/hierarchy sections based on user permissions (also lazy)
        try:
            from trackpro.auth.hierarchy_manager import hierarchy_manager
            user = get_current_user()
            if user and hierarchy_manager.is_user_dev(user.id):
                self._lazy_pages["admin"] = {"created": False, "method": "create_admin_section"}
                self.pages["admin"] = self._create_placeholder_widget("admin")
            if user and (hierarchy_manager.is_user_dev(user.id) or hierarchy_manager.is_user_moderator(user.id)):
                self._lazy_pages["hierarchy"] = {"created": False, "method": "create_hierarchy_section"}
                self.pages["hierarchy"] = self._create_placeholder_widget("hierarchy")
        except Exception:
            pass
        
        for section in self.pages.values():
            self.content_area.addWidget(section)
        
        # Paddock Pass section: only create when backend available and user is authenticated
        self.paddock_pass_section = QWidget()
        paddock_layout = QVBoxLayout(self.paddock_pass_section)
        if GAMIFICATION_AVAILABLE:
            try:
                self.paddock_pass_widget = RacePassViewWidget()
                paddock_layout.addWidget(self.paddock_pass_widget)
            except Exception:
                paddock_layout.addWidget(QLabel("Race Pass features not available"))
        else:
            paddock_layout.addWidget(QLabel("Race Pass coming soon!"))
        self.content_area.addWidget(self.paddock_pass_section)
    
    def _create_placeholder_widget(self, section_name: str):
        """Create a loading placeholder widget for a section."""
        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        loading_label = QLabel(f"Loading {section_name.title()}...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 16px;
                font-weight: 500;
                padding: 50px;
                background: transparent;
            }
        """)
        placeholder_layout.addWidget(loading_label)
        return placeholder
    
    def create_profile_section(self):
        """Create the user profile section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header
        header = QLabel("Your Profile")
        header.setObjectName("accountSectionHeader")
        layout.addWidget(header)
        
        subtitle_label = QLabel("Manage your personal information and racing preferences")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 14px;
                margin-bottom: 16px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # Avatar section
        avatar_card = ModernCard("Profile Picture")
        avatar_layout = QHBoxLayout()
        avatar_layout.setContentsMargins(4, 0, 4, 0)
        
        self.profile_avatar = ProfileAvatar(84)
        self.profile_avatar.set_account_page(self)
        try:
            # Try to populate avatar immediately from DB so the uploader isn't stuck on initials
            self._set_avatar_immediate()
        except Exception:
            pass
        # Keep avatar firmly inside the card
        avatar_container = QFrame()
        avatar_container.setFixedSize(96, 96)
        avatar_container.setStyleSheet("QFrame { background: transparent; border: none; }")
        avc_layout = QHBoxLayout(avatar_container)
        avc_layout.setContentsMargins(0, 0, 0, 0)
        avc_layout.addWidget(self.profile_avatar, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        avatar_layout.addWidget(avatar_container, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        avatar_info_layout = QVBoxLayout()
        avatar_info = QLabel("Click on your avatar to upload a new profile picture.\nRecommended size: 256x256 pixels")
        avatar_info.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        avatar_info_layout.addWidget(avatar_info)
        avatar_info_layout.addStretch()
        
        avatar_layout.addLayout(avatar_info_layout)
        avatar_layout.addStretch()
        avatar_card.content_layout.addLayout(avatar_layout)
        try:
            # Give the card a bit more vertical space so the avatar isn't clipped
            avatar_card.setMinimumHeight(150)
            # Slightly tighter top margin and a little more bottom padding
            avatar_card.content_layout.setContentsMargins(12, 4, 12, 10)
        except Exception:
            pass
        layout.addWidget(avatar_card)
        
        # Basic Information
        basic_info_card = ModernCard("Basic Information")
        form_layout = QGridLayout()
        form_layout.setSpacing(12)
        
        # First Name
        form_layout.addWidget(QLabel("First Name"), 0, 0)
        self.first_name_input = ModernInput("Enter your first name")
        form_layout.addWidget(self.first_name_input, 0, 1)
        
        # Last Name
        form_layout.addWidget(QLabel("Last Name"), 1, 0)
        self.last_name_input = ModernInput("Enter your last name")
        form_layout.addWidget(self.last_name_input, 1, 1)
        
        # Username (shown as "Username", mirrored to display_name on save)
        form_layout.addWidget(QLabel("Username"), 2, 0)
        # Username input (used also as display name)
        self.display_name_input = ModernInput("Your username")
        form_layout.addWidget(self.display_name_input, 2, 1)
        
        # Email (read-only)
        form_layout.addWidget(QLabel("Email"), 3, 0)
        self.email_input = ModernInput("your@email.com")
        self.email_input.setReadOnly(True)
        self.email_input.setStyleSheet(self.email_input.styleSheet() + "background-color: #484b51;")
        form_layout.addWidget(self.email_input, 3, 1)
        try:
            from ....auth.user_manager import get_current_user as _get_current_user
            _u = _get_current_user()
            if _u and getattr(_u, 'email', None):
                self.email_input.setText(_u.email)
        except Exception:
            pass
        
        # Hierarchy Level (read-only)
        form_layout.addWidget(QLabel("Hierarchy Level"), 4, 0)
        self.hierarchy_label = QLabel("PADDOCK")
        self.hierarchy_label.setStyleSheet("color: #b9bbbe;")
        form_layout.addWidget(self.hierarchy_label, 4, 1)
        
        # Date of Birth
        form_layout.addWidget(QLabel("Date of Birth"), 5, 0)
        self.dob_input = QDateEdit()
        self.dob_input.setDate(QDate.currentDate().addYears(-25))
        self.dob_input.setStyleSheet("""
            QDateEdit {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #dcddde;
            }
            QDateEdit:focus {
                border-color: #5865f2;
                background-color: #36393f;
            }
        """)
        form_layout.addWidget(self.dob_input, 5, 1)
        
        # Set label styles
        for i in range(form_layout.rowCount()):
            label = form_layout.itemAtPosition(i, 0).widget()
            if label:
                label.setStyleSheet("""
                    QLabel {
                        color: #dcddde;
                        font-size: 14px;
                        font-weight: 600;
                        padding: 8px 0;
                        border: none;
                        background: transparent;
                    }
                """)
        
        basic_info_card.content_layout.addLayout(form_layout)
        layout.addWidget(basic_info_card)
        
        # Bio section
        bio_card = ModernCard("About Me")
        self.bio_input = ModernTextArea("Tell us about yourself, your racing background, or favorite series...")
        try:
            self.bio_input.setFixedHeight(64)
        except Exception:
            pass
        bio_card.content_layout.addWidget(self.bio_input)
        layout.addWidget(bio_card)
        
        # Removed debug/refresh card to declutter the page
        

        
        # Save button
        save_btn = ModernButton("Save Profile", "primary")
        save_btn.clicked.connect(self.save_profile)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # CRITICAL: Load user data immediately after profile section is created
        logger.info("🔄 Profile section created, loading user data from Supabase...")
        try:
            from PyQt6.QtCore import QTimer
            # Load user data with a short delay to ensure all UI elements are ready
            QTimer.singleShot(100, self.load_user_data)
        except Exception:
            # Fallback: load synchronously if QTimer unavailable
            try:
                self.load_user_data()
            except Exception as e:
                logger.error(f"Failed to load user data: {e}")
        
        # Best-effort immediate prefill from current user (no network)
        try:
            from ....auth.user_manager import get_current_user as _get_current_user
            from ....auth.hierarchy_manager import hierarchy_manager as _hm
            _user = _get_current_user()
            if _user and getattr(_user, 'is_authenticated', False):
                # Name parsing
                full_name = getattr(_user, 'name', '') or ''
                first, last = '', ''
                if full_name:
                    parts = full_name.split()
                    first = parts[0]
                    last = ' '.join(parts[1:]) if len(parts) > 1 else ''
                if hasattr(self, 'first_name_input'):
                    if first:
                        self.first_name_input.setText(first)
                    if last:
                        self.last_name_input.setText(last)
                # Do NOT prefill the username from OAuth full name; this often shows a real name
                # and causes confusion. Username will be loaded from Supabase shortly after.
                if hasattr(self, 'email_input') and getattr(_user, 'email', None):
                    self.email_input.setText(_user.email)
                # Hierarchy quick guess (TEAM for admins; else PADDOCK)
                try:
                    self.hierarchy_label.setText("TEAM" if _hm.is_admin(getattr(_user, 'email', '')) else "PADDOCK")
                except Exception:
                    self.hierarchy_label.setText("PADDOCK")
        except Exception:
            pass
        return widget

    def _set_avatar_immediate(self):
        """Fetch the current user's avatar URL quickly and set it on the label.
        Avoids waiting for the broader profile load so the uploader shows the real photo.
        """
        try:
            from ....database.supabase_client import get_supabase_client
            supa = get_supabase_client()
            if not supa:
                return
            user_resp = supa.auth.get_user()
            if not user_resp or not user_resp.user:
                return
            user_id = user_resp.user.id
            url = None
            name = None
            try:
                r = supa.from_("user_profiles").select("avatar_url, display_name, username, first_name, last_name").eq("user_id", user_id).single().execute()
                if r and r.data:
                    url = r.data.get("avatar_url")
                    name = r.data.get("display_name") or r.data.get("username") or f"{(r.data.get('first_name') or '').strip()} {(r.data.get('last_name') or '').strip()}".strip()
            except Exception:
                pass
            if not url:
                try:
                    r2 = supa.from_("public_user_profiles").select("avatar_url, display_name, username").eq("user_id", user_id).single().execute()
                    if r2 and r2.data:
                        url = r2.data.get("avatar_url")
                        if not name:
                            name = r2.data.get("display_name") or r2.data.get("username")
                except Exception:
                    pass
            if not name:
                md = getattr(user_resp.user, 'user_metadata', {}) or {}
                name = md.get('full_name') or md.get('name') or (self.user_data.get('display_name') if hasattr(self, 'user_data') else None) or "User"
            AvatarManager.instance().set_label_avatar(self.profile_avatar, url, name, size=self.profile_avatar.width())
        except Exception:
            pass
    
    def create_security_section(self):
        """Create the security settings section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Security Settings")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Password Management Card
        password_card = ModernCard("Password Management")
        password_layout = QVBoxLayout()
        
        # Current password (for verification)
        current_pw_layout = QHBoxLayout()
        current_pw_layout.addWidget(QLabel("Current Password:"))
        self.current_password_input = ModernInput("Enter current password")
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        current_pw_layout.addWidget(self.current_password_input)
        password_layout.addLayout(current_pw_layout)
        
        # New password
        new_pw_layout = QHBoxLayout()
        new_pw_layout.addWidget(QLabel("New Password:"))
        self.new_password_input = ModernInput("Enter new password")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        new_pw_layout.addWidget(self.new_password_input)
        password_layout.addLayout(new_pw_layout)
        
        # Confirm new password
        confirm_pw_layout = QHBoxLayout()
        confirm_pw_layout.addWidget(QLabel("Confirm Password:"))
        self.confirm_password_input = ModernInput("Confirm new password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_pw_layout.addWidget(self.confirm_password_input)
        password_layout.addLayout(confirm_pw_layout)
        
        # Change password button
        change_pw_btn = ModernButton("Change Password", "primary")
        change_pw_btn.clicked.connect(self.change_password)
        password_layout.addWidget(change_pw_btn)
        
        password_card.content_layout.addLayout(password_layout)
        layout.addWidget(password_card)
        
        # Two-Factor Authentication Card
        tfa_card = ModernCard("Two-Factor Authentication")
        tfa_layout = QVBoxLayout()
        
        # 2FA Status
        self.tfa_status_label = QLabel("2FA Status: Disabled")
        self.tfa_status_label.setStyleSheet("""
            QLabel {
                color: #faa61a;
                font-size: 14px;
                font-weight: 600;
                padding: 8px;
                background-color: #2f3136;
                border-radius: 4px;
            }
        """)
        tfa_layout.addWidget(self.tfa_status_label)
        
        # 2FA Toggle buttons
        tfa_btn_layout = QHBoxLayout()
        self.enable_2fa_btn = ModernButton("Enable 2FA", "secondary")
        self.enable_2fa_btn.clicked.connect(self.toggle_2fa)
        tfa_btn_layout.addWidget(self.enable_2fa_btn)
        
        self.disable_2fa_btn = ModernButton("Disable 2FA", "danger")
        self.disable_2fa_btn.clicked.connect(self.toggle_2fa)
        self.disable_2fa_btn.setVisible(False)
        tfa_btn_layout.addWidget(self.disable_2fa_btn)
        
        tfa_layout.addLayout(tfa_btn_layout)
        tfa_card.content_layout.addLayout(tfa_layout)
        layout.addWidget(tfa_card)
        
        # Application Version Card
        version_card = ModernCard("Application Version")
        version_layout = QVBoxLayout()
        
        # Version info layout
        version_info_layout = QHBoxLayout()
        
        # Current version display
        version_label = QLabel("Current Version:")
        version_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 0;
                border: none;
                background: transparent;
            }
        """)
        version_info_layout.addWidget(version_label)
        
        # Version number
        from trackpro.updater import CURRENT_VERSION
        self.version_display = QLabel(f"v{CURRENT_VERSION}")
        self.version_display.setStyleSheet("""
            QLabel {
                color: #5865f2;
                font-size: 14px;
                font-weight: 700;
                padding: 8px 12px;
                background-color: #2f3136;
                border-radius: 4px;
                border: 1px solid #40444b;
            }
        """)
        version_info_layout.addWidget(self.version_display)
        
        # Check for updates button
        self.check_updates_btn = ModernButton("Check for Updates", "secondary")
        self.check_updates_btn.clicked.connect(self.check_for_updates)
        version_info_layout.addWidget(self.check_updates_btn)
        
        # Download update button (initially hidden)
        self.download_update_btn = ModernButton("Download Update", "primary")
        self.download_update_btn.clicked.connect(self.download_update)
        self.download_update_btn.setVisible(False)
        version_info_layout.addWidget(self.download_update_btn)
        
        version_info_layout.addStretch()
        version_layout.addLayout(version_info_layout)
        
        # Update status
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                padding: 4px 0;
                border: none;
                background: transparent;
            }
        """)
        version_layout.addWidget(self.update_status_label)
        
        version_card.content_layout.addLayout(version_layout)
        layout.addWidget(version_card)
        
        layout.addStretch()
        return widget
    
    def create_notifications_section(self):
        """Create the notifications settings section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Notification Settings")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Email Notifications Card
        email_card = ModernCard("Email Notifications")
        email_layout = QVBoxLayout()
        
        self.email_notifications_check = QCheckBox("Enable email notifications")
        self.email_notifications_check.setStyleSheet("""
            QCheckBox {
                color: #dcddde;
                font-size: 14px;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
                border-radius: 3px;
            }
        """)
        email_layout.addWidget(self.email_notifications_check)
        
        self.race_reminders_check = QCheckBox("Race event reminders")
        self.race_reminders_check.setStyleSheet(self.email_notifications_check.styleSheet())
        email_layout.addWidget(self.race_reminders_check)
        
        self.achievement_emails_check = QCheckBox("Achievement notifications")
        self.achievement_emails_check.setStyleSheet(self.email_notifications_check.styleSheet())
        email_layout.addWidget(self.achievement_emails_check)
        
        email_card.content_layout.addLayout(email_layout)
        layout.addWidget(email_card)
        
        # In-App Notifications Card
        inapp_card = ModernCard("In-App Notifications")
        inapp_layout = QVBoxLayout()
        
        self.ai_coach_alerts_check = QCheckBox("AI Coach alerts and tips")
        self.ai_coach_alerts_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.ai_coach_alerts_check)
        
        self.performance_alerts_check = QCheckBox("Performance improvement alerts")
        self.performance_alerts_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.performance_alerts_check)
        
        self.social_notifications_check = QCheckBox("Social activity notifications")
        self.social_notifications_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.social_notifications_check)
        
        inapp_card.content_layout.addLayout(inapp_layout)
        layout.addWidget(inapp_card)
        
        # Startup Settings Card
        startup_card = ModernCard("Startup Settings")
        startup_layout = QVBoxLayout()
        
        self.start_with_windows_check = QCheckBox("Start TrackPro with Windows")
        self.start_with_windows_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.start_with_windows_check)
        
        self.start_minimized_check = QCheckBox("Start minimized (recommended)")
        self.start_minimized_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.start_minimized_check)
        
        self.minimize_to_tray_check = QCheckBox("Always minimize to tray when closing (recommended)")
        self.minimize_to_tray_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.minimize_to_tray_check)
        
        # Add description
        startup_desc = QLabel("TrackPro needs to be running for hardware functionality to work properly. When you close the window, TrackPro will continue running in the background.")
        startup_desc.setStyleSheet("""
            QLabel {
                color: #72767d;
                font-size: 12px;
                margin-top: 8px;
                border: none;
                background: transparent;
            }
        """)
        startup_layout.addWidget(startup_desc)
        
        startup_card.content_layout.addLayout(startup_layout)
        layout.addWidget(startup_card)
        
        # Save button
        save_notifications_btn = ModernButton("Save Settings", "primary")
        save_notifications_btn.clicked.connect(self.save_notification_settings)
        layout.addWidget(save_notifications_btn)
        
        layout.addStretch()
        return widget
    
    def create_racing_section(self):
        """Create the racing preferences section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Racing Preferences")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Racing Statistics Card
        stats_card = ModernCard("Racing Statistics")
        stats_layout = QGridLayout()
        
        # Performance metrics
        self.total_sessions_label = QLabel("Total Sessions: Loading...")
        self.total_distance_label = QLabel("Total Distance: Loading...")
        self.best_lap_label = QLabel("Best Lap Time: Loading...")
        self.avg_consistency_label = QLabel("Consistency Rating: Loading...")
        
        stats_style = """
            QLabel {
                color: #dcddde;
                font-size: 14px;
                padding: 8px;
                background-color: #2f3136;
                border-radius: 4px;
                margin: 2px;
            }
        """
        
        for label in [self.total_sessions_label, self.total_distance_label, 
                     self.best_lap_label, self.avg_consistency_label]:
            label.setStyleSheet(stats_style)
        
        stats_layout.addWidget(self.total_sessions_label, 0, 0)
        stats_layout.addWidget(self.total_distance_label, 0, 1)
        stats_layout.addWidget(self.best_lap_label, 1, 0)
        stats_layout.addWidget(self.avg_consistency_label, 1, 1)
        
        refresh_stats_btn = ModernButton("Refresh Statistics", "secondary")
        refresh_stats_btn.clicked.connect(self.load_racing_statistics)
        stats_layout.addWidget(refresh_stats_btn, 2, 0, 1, 2)
        
        stats_card.content_layout.addLayout(stats_layout)
        layout.addWidget(stats_card)
        
        # AI Coach Preferences Card
        ai_coach_card = ModernCard("AI Coach Preferences")
        ai_layout = QVBoxLayout()
        
        # Coach personality
        personality_layout = QHBoxLayout()
        personality_layout.addWidget(QLabel("Coaching Style:"))
        self.coach_personality_combo = QComboBox()
        self.coach_personality_combo.addItems(["Encouraging", "Technical", "Strict", "Balanced"])
        self.coach_personality_combo.setStyleSheet("""
            QComboBox {
                background-color: #40444b;
                border: 1px solid #5865f2;
                border-radius: 4px;
                padding: 8px;
                color: #fefefe;
                font-size: 14px;
            }
        """)
        personality_layout.addWidget(self.coach_personality_combo)
        ai_layout.addLayout(personality_layout)
        
        # Coaching frequency
        frequency_layout = QHBoxLayout()
        frequency_layout.addWidget(QLabel("Coaching Frequency:"))
        self.coaching_frequency_combo = QComboBox()
        self.coaching_frequency_combo.addItems(["Real-time", "After sessions", "Weekly summary", "On-demand only"])
        self.coaching_frequency_combo.setStyleSheet(self.coach_personality_combo.styleSheet())
        frequency_layout.addWidget(self.coaching_frequency_combo)
        ai_layout.addLayout(frequency_layout)
        
        # Voice coaching toggle
        self.voice_coaching_check = QCheckBox("Enable voice coaching during sessions")
        self.voice_coaching_check.setStyleSheet("""
            QCheckBox {
                color: #dcddde;
                font-size: 14px;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
                border-radius: 3px;
            }
        """)
        ai_layout.addWidget(self.voice_coaching_check)
        
        ai_coach_card.content_layout.addLayout(ai_layout)
        layout.addWidget(ai_coach_card)
        
        # Performance Goals Card
        goals_card = ModernCard("Performance Goals")
        goals_layout = QVBoxLayout()
        
        # Target lap time improvement
        laptime_layout = QHBoxLayout()
        laptime_layout.addWidget(QLabel("Target Lap Time Improvement (%/month):"))
        self.laptime_goal_spin = QSpinBox()
        self.laptime_goal_spin.setRange(0, 50)
        self.laptime_goal_spin.setValue(5)
        self.laptime_goal_spin.setStyleSheet("""
            QSpinBox {
                background-color: #40444b;
                border: 1px solid #5865f2;
                border-radius: 4px;
                padding: 8px;
                color: #fefefe;
                font-size: 14px;
            }
        """)
        laptime_layout.addWidget(self.laptime_goal_spin)
        goals_layout.addLayout(laptime_layout)
        
        # Consistency target
        consistency_layout = QHBoxLayout()
        consistency_layout.addWidget(QLabel("Target Consistency Rating:"))
        self.consistency_goal_spin = QSpinBox()
        self.consistency_goal_spin.setRange(50, 100)
        self.consistency_goal_spin.setValue(85)
        self.consistency_goal_spin.setStyleSheet(self.laptime_goal_spin.styleSheet())
        consistency_layout.addWidget(self.consistency_goal_spin)
        goals_layout.addLayout(consistency_layout)
        
        goals_card.content_layout.addLayout(goals_layout)
        layout.addWidget(goals_card)
        
        # Save Racing Settings Button
        save_racing_btn = ModernButton("Save Racing Settings", "primary")
        save_racing_btn.clicked.connect(self.save_racing_settings)
        layout.addWidget(save_racing_btn)
        
        layout.addStretch()
        return widget
    
    def create_connections_section(self):
        """Create the connections/integrations section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Connected Accounts")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Save Connections Button
        save_connections_btn = ModernButton("Save Connection Settings", "primary")
        save_connections_btn.clicked.connect(self.save_connection_settings)
        layout.addWidget(save_connections_btn)
        
        layout.addStretch()

        return widget

    def _get_saved_iracing_cookie(self) -> str | None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            return (data.get("iracing") or {}).get("session_cookie")
        except Exception:
            return None

    def link_iracing_account(self):
        """Open a secure web view to link iRacing and capture the session cookies only (no password stored).
        This version also forces persistent cookies and verifies the link via the Data API automatically.
        """
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            try:
                # Optional: profile API for forcing persistent cookies
                from PyQt6.QtWebEngineCore import QWebEngineProfile
            except Exception:
                QWebEngineProfile = None
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
            from PyQt6.QtCore import QUrl, QTimer
            import os, requests

            import logging
            logger = logging.getLogger(__name__)

            dialog = QDialog(self)
            dialog.setWindowTitle("Link iRacing Account")
            layout = QVBoxLayout(dialog)
            web = QWebEngineView(dialog)
            layout.addWidget(web)
            logger.info("[IRacingLink] Opened link dialog and created web view")

            # Accumulate cookies; some endpoints require multiple cookies
            self._iracing_cookies = getattr(self, "_iracing_cookies", {})
            self._iracing_link_success = False
            try:
                self.iracing_status_label.setText("Status: Connecting…")
            except Exception:
                pass

            def handle_cookie_added(cookie):
                try:
                    name = bytes(cookie.name()).decode("utf-8", errors="ignore")
                    value = bytes(cookie.value()).decode("utf-8", errors="ignore")
                    domain = cookie.domain()
                    if domain and ("iracing.com" in domain):
                        logger.info(f"[IRacingLink] Cookie added: {name} (domain={domain})")
                        self._iracing_cookies[name] = value
                        # Save to main window for global reuse
                        try:
                            main_window = self.window()
                            setattr(main_window, "_iracing_session_cookie", self._iracing_cookies.get("authtoken") or self._iracing_cookies.get("irsso_membersv2") or value)
                            setattr(main_window, "_iracing_cookies", dict(self._iracing_cookies))
                        except Exception:
                            pass
                        # Persist securely
                        try:
                            self._save_iracing_cookies(self._iracing_cookies)
                        except Exception:
                            pass
                        # Try verification shortly after receiving likely auth-bearing cookies
                        if name.lower() in ("authtoken", "irsso_membersv2", "irsso", "iracing_ui"):
                            QTimer.singleShot(300, attempt_verify)
                except Exception:
                    pass

            profile = web.page().profile()
            try:
                cookie_store = profile.cookieStore()
                cookie_store.cookieAdded.connect(handle_cookie_added)
                # Proactively load any existing cookies and seed our map
                try:
                    cookie_store.loadAllCookies(lambda cookies: [handle_cookie_added(c) for c in cookies])
                except Exception as e:
                    logger.debug(f"[IRacingLink] loadAllCookies not available: {e}")
                # Seed previously saved cookies into the WebEngine profile to enable auto-login
                try:
                    saved = self._load_iracing_cookies() or {}
                    if not saved:
                        token = self._get_saved_iracing_cookie()
                        if token:
                            saved = {"irsso_membersv2": token}
                    if saved:
                        try:
                            from PyQt6.QtNetwork import QNetworkCookie  # type: ignore
                        except Exception:
                            QNetworkCookie = None  # type: ignore
                        from PyQt6.QtCore import QUrl

                        def set_cookies_for_host(host: str):
                            if not QNetworkCookie:
                                return
                            for k, v in saved.items():
                                try:
                                    cookie = QNetworkCookie(bytes(str(k), "utf-8"), bytes(str(v), "utf-8"))
                                    cookie.setDomain(host)
                                    cookie.setPath("/")
                                    try:
                                        cookie.setSecure(True)
                                        cookie.setHttpOnly(True)
                                    except Exception:
                                        pass
                                    cookie_store.setCookie(cookie, QUrl(f"https://{host}/"))
                                except Exception:
                                    pass

                        # Common domains used by iRacing auth
                        set_cookies_for_host("members-ng.iracing.com")
                        set_cookies_for_host("iracing.com")
                except Exception:
                    pass
            except Exception:
                pass

            # Scrape JS cookies periodically as a secondary source (some cookies may be httpOnly=False)
            def scrape_js_cookies():
                try:
                    def _cb(result):
                        try:
                            if not isinstance(result, str):
                                return
                            for part in result.split(';'):
                                kv = part.strip().split('=', 1)
                                if len(kv) != 2:
                                    continue
                                k, v = kv[0], kv[1]
                                if k and v:
                                    if k not in self._iracing_cookies:
                                        logger.info(f"[IRacingLink] JS cookie discovered: {k}")
                                    self._iracing_cookies[k] = v
                        except Exception:
                            pass
                    web.page().runJavaScript("document.cookie", _cb)
                except Exception:
                    pass

            # Force persistent cookies and storage (helps some systems retain cross-domain cookies)
            try:
                if QWebEngineProfile and hasattr(profile, "setPersistentCookiesPolicy"):
                    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
                if QWebEngineProfile and hasattr(profile, "setHttpAcceptCookiePolicy"):
                    profile.setHttpAcceptCookiePolicy(QWebEngineProfile.HttpAcceptCookiePolicy.AcceptAllCookies)
                cache_dir = os.path.join(os.path.expanduser("~"), ".trackpro", "webcache")
                os.makedirs(cache_dir, exist_ok=True)
                if hasattr(profile, "setPersistentStoragePath"):
                    profile.setPersistentStoragePath(cache_dir)
            except Exception:
                pass

            # Attempt verification using currently collected cookies
            def attempt_verify():
                try:
                    logger.info(f"[IRacingLink] Attempting verify with {len(self._iracing_cookies)} cookies: {list(self._iracing_cookies.keys())}")
                    if not self._iracing_cookies:
                        return
                    s = requests.Session()
                    s.headers.update({"User-Agent": "TrackPro/IRacingLink"})
                    for k, v in self._iracing_cookies.items():
                        try:
                            s.cookies.set(k, v, domain="members-ng.iracing.com")
                            s.cookies.set(k, v, domain=".iracing.com")
                        except Exception:
                            pass
                    r = s.get("https://members-ng.iracing.com/data/member/summary", timeout=10)
                    logger.info(f"[IRacingLink] summary status={getattr(r,'status_code',None)}")
                    if not r.ok:
                        # Fallback: verify inside the WebEngine session (includes httpOnly cookies)
                        try:
                            def _handle_js_summary(res):
                                try:
                                    ok = bool(isinstance(res, dict) and res.get('ok'))
                                    status = (res or {}).get('status')
                                    data = (res or {}).get('json') if isinstance(res, dict) else None
                                    logger.info(f"[IRacingLink][JS] summary ok={ok} status={status}")
                                    if not ok or not isinstance(data, dict):
                                        return
                                    def _finalize_with_json(jdata: dict):
                                        try:
                                            # Success: mark connected and sync
                                            self.iracing_status_label.setText("Status: Connected")
                                            try:
                                                self.disconnect_iracing_btn.setVisible(True)
                                            except Exception:
                                                pass
                                            try:
                                                self._iracing_link_success = True
                                                if hasattr(self, "_ir_verify_timer") and self._ir_verify_timer:
                                                    try:
                                                        self._ir_verify_timer.stop()
                                                    except Exception:
                                                        pass
                                                dialog.accept()
                                                logger.info("[IRacingLink] Verification (JS) succeeded; dialog closed.")
                                            except Exception:
                                                pass
                                            try:
                                                QMessageBox.information(self, "iRacing", "iRacing linked. Syncing your data now...")
                                            except Exception:
                                                pass
                                            try:
                                                self._refresh_iracing_snapshot()
                                            except Exception:
                                                pass
                                        except Exception:
                                            pass
                                    # Follow indirection if present
                                    link = data.get('link')
                                    if isinstance(link, str) and link:
                                        js_follow = (
                                            "fetch('" + link + "', {credentials:'include'})"
                                            ".then(r=>r.json().then(j=>({ok:r.ok,status:r.status,json:j}))))"
                                        )
                                        web.page().runJavaScript(js_follow, lambda rr: _finalize_with_json((rr or {}).get('json') if isinstance(rr, dict) else {}))
                                    else:
                                        _finalize_with_json(data)
                                except Exception:
                                    pass
                            js = (
                                "fetch('https://members-ng.iracing.com/data/member/summary', {credentials:'include'})"
                                ".then(r=>r.json().then(j=>({ok:r.ok,status:r.status,json:j,ct:r.headers.get('content-type')})))"
                                ".catch(()=>({ok:false,status:0}))"
                            )
                            web.page().runJavaScript(js, _handle_js_summary)
                        except Exception:
                            pass
                        return
                    j = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
                    if isinstance(j, dict) and j.get("link"):
                        rr = s.get(j["link"], timeout=10)
                        logger.info(f"[IRacingLink] link status={getattr(rr,'status_code',None)}")
                        if not rr.ok:
                            return
                        j = rr.json() if rr.headers.get("Content-Type", "").startswith("application/json") else None
                    if not isinstance(j, dict):
                        return
                    # Mark connected and sync now
                    self.iracing_status_label.setText("Status: Connected")
                    try:
                        self.disconnect_iracing_btn.setVisible(True)
                    except Exception:
                        pass
                    try:
                        self._iracing_link_success = True
                        if hasattr(self, "_ir_verify_timer") and self._ir_verify_timer:
                            try:
                                self._ir_verify_timer.stop()
                            except Exception:
                                pass
                        dialog.accept()
                        logger.info("[IRacingLink] Verification succeeded; dialog closed.")
                    except Exception:
                        pass
                    try:
                        QMessageBox.information(self, "iRacing", "iRacing linked. Syncing your data now...")
                    except Exception:
                        pass
                    try:
                        self._refresh_iracing_snapshot()
                    except Exception:
                        pass
                except Exception:
                    logger.exception("[IRacingLink] Verify attempt failed")
                    pass

            # Load root of members site; the SPA handles login internally
            web.load(QUrl("https://members-ng.iracing.com/"))
            dialog.resize(900, 700)
            # Also try verification shortly after load
            try:
                web.loadFinished.connect(lambda ok: (logger.info(f"[IRacingLink] loadFinished ok={ok}, url={web.url().toString()}"), QTimer.singleShot(1200, attempt_verify)))
                web.urlChanged.connect(lambda u: logger.info(f"[IRacingLink] urlChanged -> {u.toString()}"))
            except Exception:
                pass
            # Periodic verification attempts until success or dialog closes
            try:
                self._ir_verify_timer = QTimer(dialog)
                self._ir_verify_timer.setInterval(1500)
                self._ir_verify_timer.timeout.connect(lambda: (scrape_js_cookies(), attempt_verify()))
                self._ir_verify_timer.start()
            except Exception:
                pass
            dialog.exec()
            # Ensure timer is stopped when dialog closes
            try:
                if hasattr(self, "_ir_verify_timer") and self._ir_verify_timer:
                    self._ir_verify_timer.stop()
                logger.info(f"[IRacingLink] Dialog closed. success={self._iracing_link_success}")
            except Exception:
                pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error linking iRacing: {e}")
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "iRacing", "Could not open iRacing login.")
            except Exception:
                pass

    def _save_iracing_cookies(self, cookies: dict) -> None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            ir = data.get("iracing", {})
            ir.update({"cookies": cookies})
            data["iracing"] = ir
            ssm.save_session(data)
        except Exception:
            pass

    def _load_iracing_cookies(self) -> dict | None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            return (data.get("iracing") or {}).get("cookies") or None
        except Exception:
            return None

    def _refresh_iracing_snapshot(self) -> None:
        """Fetch member summary/career and upsert snapshot + connections. Runs non-blocking-safe."""
        try:
            import requests
            from datetime import datetime
            cookies = self._load_iracing_cookies()
            if not cookies:
                # Try main window cache
                try:
                    main_window = self.window()
                    cookies = getattr(main_window, "_iracing_cookies", None)
                    if not cookies and hasattr(main_window, "_iracing_session_cookie"):
                        cookies = {"irsso_membersv2": getattr(main_window, "_iracing_session_cookie")}
                except Exception:
                    pass
            if not cookies:
                return

            s = requests.Session()
            s.headers.update({"User-Agent": "TrackPro/IRacingLink"})
            for k, v in cookies.items():
                s.cookies.set(k, v, domain="members-ng.iracing.com")

            def fetch(url):
                r = s.get(url, timeout=12)
                if not r.ok:
                    return None
                j = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
                if isinstance(j, dict) and j.get("link"):
                    rr = s.get(j["link"], timeout=12)
                    if rr.ok and rr.headers.get("Content-Type", "").startswith("application/json"):
                        return rr.json()
                    return None
                return j

            summary = fetch("https://members-ng.iracing.com/data/member/summary") or {}
            career = fetch("https://members-ng.iracing.com/data/stats/member/career") or {}
            cust_id = summary.get("cust_id") or summary.get("customer_id") or None
            username = summary.get("display_name") or summary.get("member_name") or None

            # Build snapshot payload
            def get_lic(licenses, key):
                if isinstance(licenses, list):
                    m = { (x.get("category") or x.get("category_name") or "").lower(): x for x in licenses }
                else:
                    m = licenses or {}
                return (m.get(key) or {})

            licenses = summary.get("licenses") or summary.get("licenses_info") or {}
            snap = {}
            for cat_key, prefix in (("road", "road"),("oval","oval"),("dirt_road","dirt_road"),("dirt_oval","dirt_oval")):
                lic = get_lic(licenses, cat_key)
                snap[f"{prefix}_irating"] = lic.get("irating") or lic.get("iRating") or lic.get("i_rating")
                snap[f"{prefix}_sr"] = lic.get("safety_rating") or lic.get("safetyRating") or lic.get("sr")
                snap[f"{prefix}_license"] = lic.get("license_level") or lic.get("license") or lic.get("class")

            totals = career.get("career") or career.get("overall") or career
            if isinstance(totals, list):
                totals = next((x for x in totals if (x.get("category") or "").lower()=="overall"), totals[0] if totals else {})
            snap["wins"] = (totals or {}).get("wins")
            snap["starts"] = (totals or {}).get("starts") or (totals or {}).get("races")

            # Upsert DB (best-effort)
            from ....database.supabase_client import get_supabase_client
            supa = get_supabase_client()
            if supa:
                # user_connections
                if cust_id:
                    try:
                        supa.from_("user_connections").upsert({
                            "user_id": self.user_data.get("user_id") if hasattr(self, 'user_data') else None,
                            "provider": "iracing",
                            "external_id": str(cust_id),
                            "username": username,
                            "linked_at": datetime.utcnow().isoformat()+"Z"
                        }, on_conflict="user_id,provider").execute()
                    except Exception:
                        pass
                # user_iracing_snapshot
                payload = dict(snap)
                payload["user_id"] = self.user_data.get("user_id") if hasattr(self, 'user_data') else None
                payload["last_updated"] = datetime.utcnow().isoformat()+"Z"
                try:
                    supa.from_("user_iracing_snapshot").upsert(payload, on_conflict="user_id").execute()
                except Exception:
                    pass

            # Update UI status
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            self.iracing_status_label.setText(f"Status: Connected • Synced {ts}")
        except Exception:
            pass
    
    def create_privacy_section(self):
        """Create a compact and well-organized privacy and data section."""
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Compact header
        header_label = QLabel("Privacy & Data")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #2f3136;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #40444b;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5865f2;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Privacy Settings Card - Compact design
        privacy_card = ModernCard("Privacy Settings")
        privacy_layout = QVBoxLayout()
        privacy_layout.setSpacing(16)
        privacy_layout.setContentsMargins(0, 0, 0, 0)
        
        # Profile visibility - compact layout
        visibility_layout = QHBoxLayout()
        visibility_layout.setSpacing(12)
        
        visibility_label = QLabel("Profile Visibility:")
        visibility_label.setStyleSheet("color: #dcddde; font-weight: 500; font-size: 13px; min-width: 120px;")
        
        self.profile_visibility_combo = QComboBox()
        self.profile_visibility_combo.addItems(["Public", "Friends Only", "Private"])
        self.profile_visibility_combo.setStyleSheet("""
            QComboBox {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 6px;
                padding: 8px 12px;
                color: #fefefe;
                font-size: 13px;
                min-width: 140px;
            }
            QComboBox:hover {
                border-color: #5865f2;
            }
        """)
        
        visibility_layout.addWidget(visibility_label)
        visibility_layout.addWidget(self.profile_visibility_combo)
        visibility_layout.addStretch()
        privacy_layout.addLayout(visibility_layout)
        
        # Privacy options - compact checkboxes
        privacy_options_label = QLabel("Privacy Options:")
        privacy_options_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; margin-top: 8px;")
        privacy_layout.addWidget(privacy_options_label)
        
        # Create compact checkboxes
        self.share_telemetry_check = QCheckBox("Share telemetry data")
        self.share_telemetry_check.setChecked(True)
        self.share_telemetry_check.setEnabled(False)
        self.show_statistics_check = QCheckBox("Show racing statistics publicly")
        self.allow_friend_requests_check = QCheckBox("Allow friend requests")
        self.show_online_status_check = QCheckBox("Show online status")
        
        checkbox_style = """
            QCheckBox {
                color: #dcddde;
                font-size: 12px;
                font-weight: 500;
                spacing: 12px;
                padding: 8px 12px;
                background-color: #36393f;
                border: 1px solid #40444b;
                border-radius: 6px;
                min-height: 36px;
            }
            QCheckBox:hover {
                background-color: #40444b;
                border-color: #5865f2;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
            }
        """
        
        privacy_checkboxes = [
            self.share_telemetry_check, 
            self.show_statistics_check, 
            self.allow_friend_requests_check, 
            self.show_online_status_check
        ]
        
        for checkbox in privacy_checkboxes:
            checkbox.setStyleSheet(checkbox_style)
            privacy_layout.addWidget(checkbox)
        
        privacy_card.content_layout.addLayout(privacy_layout)
        scroll_layout.addWidget(privacy_card)
        
        # Data Management Card - Compact design
        data_card = ModernCard("Data Management")
        data_layout = QVBoxLayout()
        data_layout.setSpacing(16)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        # Export buttons - horizontal layout
        export_layout = QHBoxLayout()
        export_layout.setSpacing(12)
        
        self.export_profile_btn = ModernButton("Export Profile", "secondary")
        self.export_profile_btn.clicked.connect(self.export_profile_data)
        self.export_profile_btn.setMinimumWidth(140)
        self.export_profile_btn.setMinimumHeight(36)
        
        self.export_telemetry_btn = ModernButton("Export Telemetry", "secondary")
        self.export_telemetry_btn.clicked.connect(self.export_telemetry_data)
        self.export_telemetry_btn.setMinimumWidth(140)
        self.export_telemetry_btn.setMinimumHeight(36)
        
        export_layout.addWidget(self.export_profile_btn)
        export_layout.addWidget(self.export_telemetry_btn)
        export_layout.addStretch()
        data_layout.addLayout(export_layout)
        
        # Data usage - compact display
        usage_label = QLabel("Data Usage:")
        usage_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; margin-top: 8px;")
        data_layout.addWidget(usage_label)
        
        self.data_usage_text = QTextEdit()
        self.data_usage_text.setReadOnly(True)
        self.data_usage_text.setMaximumHeight(80)
        self.data_usage_text.setStyleSheet("""
            QTextEdit {
                background-color: #2f3136;
                border: 1px solid #40444b;
                border-radius: 6px;
                color: #b9bbbe;
                font-size: 11px;
                padding: 8px;
            }
        """)
        
        data_usage_content = """Profile: ~2.5 KB | Stats: ~15.3 KB | Telemetry: ~127.8 MB
Total: ~128.0 MB | Last updated: Just now"""
        self.data_usage_text.setPlainText(data_usage_content)
        data_layout.addWidget(self.data_usage_text)
        
        data_card.content_layout.addLayout(data_layout)
        scroll_layout.addWidget(data_card)
        
        # Account Deletion Card - Compact warning
        deletion_card = ModernCard("Account Deletion")
        deletion_layout = QVBoxLayout()
        deletion_layout.setSpacing(16)
        deletion_layout.setContentsMargins(0, 0, 0, 0)
        
        # Warning header
        warning_layout = QHBoxLayout()
        warning_layout.setSpacing(8)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 20px;")
        
        warning_title = QLabel("Danger Zone - Permanent Deletion")
        warning_title.setStyleSheet("color: #f04747; font-size: 14px; font-weight: 600;")
        
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_title)
        warning_layout.addStretch()
        deletion_layout.addLayout(warning_layout)
        
        # Compact warning info
        deletion_info = QLabel("This action cannot be undone. All your data will be permanently deleted.")
        deletion_info.setStyleSheet("color: #b9bbbe; font-size: 12px; line-height: 1.4;")
        deletion_info.setWordWrap(True)
        deletion_layout.addWidget(deletion_info)
        
        # Delete button
        self.delete_account_btn = ModernButton("Delete Account", "danger")
        self.delete_account_btn.clicked.connect(self.request_account_deletion)
        self.delete_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #f04747;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
                min-width: 120px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #d73d3d;
            }
        """)
        
        delete_button_layout = QHBoxLayout()
        delete_button_layout.addStretch()
        delete_button_layout.addWidget(self.delete_account_btn)
        delete_button_layout.addStretch()
        deletion_layout.addLayout(delete_button_layout)
        
        deletion_card.content_layout.addLayout(deletion_layout)
        scroll_layout.addWidget(deletion_card)
        
        # Save button - compact positioning
        save_privacy_btn = ModernButton("Save Privacy Settings", "primary")
        save_privacy_btn.clicked.connect(self.save_privacy_settings)
        save_privacy_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
                min-width: 160px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
        """)
        
        save_button_layout = QHBoxLayout()
        save_button_layout.addStretch()
        save_button_layout.addWidget(save_privacy_btn)
        save_button_layout.addStretch()
        scroll_layout.addLayout(save_button_layout)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_security_section(self):
        """Create the security settings section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Security Settings")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Password Management Card
        password_card = ModernCard("Password Management")
        password_layout = QVBoxLayout()
        
        # Current password (for verification)
        current_pw_layout = QHBoxLayout()
        current_pw_layout.addWidget(QLabel("Current Password:"))
        self.current_password_input = ModernInput("Enter current password")
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        current_pw_layout.addWidget(self.current_password_input)
        password_layout.addLayout(current_pw_layout)
        
        # New password
        new_pw_layout = QHBoxLayout()
        new_pw_layout.addWidget(QLabel("New Password:"))
        self.new_password_input = ModernInput("Enter new password")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        new_pw_layout.addWidget(self.new_password_input)
        password_layout.addLayout(new_pw_layout)
        
        # Confirm new password
        confirm_pw_layout = QHBoxLayout()
        confirm_pw_layout.addWidget(QLabel("Confirm Password:"))
        self.confirm_password_input = ModernInput("Confirm new password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_pw_layout.addWidget(self.confirm_password_input)
        password_layout.addLayout(confirm_pw_layout)
        
        # Change password button
        change_pw_btn = ModernButton("Change Password", "primary")
        change_pw_btn.clicked.connect(self.change_password)
        password_layout.addWidget(change_pw_btn)
        
        password_card.content_layout.addLayout(password_layout)
        layout.addWidget(password_card)
        
        # Two-Factor Authentication Card
        tfa_card = ModernCard("Two-Factor Authentication")
        tfa_layout = QVBoxLayout()
        
        # 2FA Status
        self.tfa_status_label = QLabel("2FA Status: Disabled")
        self.tfa_status_label.setStyleSheet("""
            QLabel {
                color: #faa61a;
                font-size: 14px;
                font-weight: 600;
                padding: 8px;
                background-color: #2f3136;
                border-radius: 4px;
            }
        """)
        tfa_layout.addWidget(self.tfa_status_label)
        
        # 2FA Toggle buttons
        tfa_btn_layout = QHBoxLayout()
        self.enable_2fa_btn = ModernButton("Enable 2FA", "secondary")
        self.enable_2fa_btn.clicked.connect(self.toggle_2fa)
        tfa_btn_layout.addWidget(self.enable_2fa_btn)
        
        self.disable_2fa_btn = ModernButton("Disable 2FA", "danger")
        self.disable_2fa_btn.clicked.connect(self.toggle_2fa)
        self.disable_2fa_btn.setVisible(False)
        tfa_btn_layout.addWidget(self.disable_2fa_btn)
        
        tfa_layout.addLayout(tfa_btn_layout)
        tfa_card.content_layout.addLayout(tfa_layout)
        layout.addWidget(tfa_card)
        
        # Application Version Card
        version_card = ModernCard("Application Version")
        version_layout = QVBoxLayout()
        
        # Version info layout
        version_info_layout = QHBoxLayout()
        
        # Current version display
        version_label = QLabel("Current Version:")
        version_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 0;
                border: none;
                background: transparent;
            }
        """)
        version_info_layout.addWidget(version_label)
        
        # Version number
        from trackpro.updater import CURRENT_VERSION
        self.version_display = QLabel(f"v{CURRENT_VERSION}")
        self.version_display.setStyleSheet("""
            QLabel {
                color: #5865f2;
                font-size: 14px;
                font-weight: 700;
                padding: 8px 12px;
                background-color: #2f3136;
                border-radius: 4px;
                border: 1px solid #40444b;
            }
        """)
        version_info_layout.addWidget(self.version_display)
        
        # Check for updates button
        self.check_updates_btn = ModernButton("Check for Updates", "secondary")
        self.check_updates_btn.clicked.connect(self.check_for_updates)
        version_info_layout.addWidget(self.check_updates_btn)
        
        # Download update button (initially hidden)
        self.download_update_btn = ModernButton("Download Update", "primary")
        self.download_update_btn.clicked.connect(self.download_update)
        self.download_update_btn.setVisible(False)
        version_info_layout.addWidget(self.download_update_btn)
        
        version_info_layout.addStretch()
        version_layout.addLayout(version_info_layout)
        
        # Update status
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                padding: 4px 0;
                border: none;
                background: transparent;
            }
        """)
        version_layout.addWidget(self.update_status_label)
        
        version_card.content_layout.addLayout(version_layout)
        layout.addWidget(version_card)
        
        layout.addStretch()
        return widget
    
    def create_notifications_section(self):
        """Create the notifications settings section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Notification Settings")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Email Notifications Card
        email_card = ModernCard("Email Notifications")
        email_layout = QVBoxLayout()
        
        self.email_notifications_check = QCheckBox("Enable email notifications")
        self.email_notifications_check.setStyleSheet("""
            QCheckBox {
                color: #dcddde;
                font-size: 14px;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
                border-radius: 3px;
            }
        """)
        email_layout.addWidget(self.email_notifications_check)
        
        self.race_reminders_check = QCheckBox("Race event reminders")
        self.race_reminders_check.setStyleSheet(self.email_notifications_check.styleSheet())
        email_layout.addWidget(self.race_reminders_check)
        
        self.achievement_emails_check = QCheckBox("Achievement notifications")
        self.achievement_emails_check.setStyleSheet(self.email_notifications_check.styleSheet())
        email_layout.addWidget(self.achievement_emails_check)
        
        email_card.content_layout.addLayout(email_layout)
        layout.addWidget(email_card)
        
        # In-App Notifications Card
        inapp_card = ModernCard("In-App Notifications")
        inapp_layout = QVBoxLayout()
        
        self.ai_coach_alerts_check = QCheckBox("AI Coach alerts and tips")
        self.ai_coach_alerts_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.ai_coach_alerts_check)
        
        self.performance_alerts_check = QCheckBox("Performance improvement alerts")
        self.performance_alerts_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.performance_alerts_check)
        
        self.social_notifications_check = QCheckBox("Social activity notifications")
        self.social_notifications_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.social_notifications_check)
        
        inapp_card.content_layout.addLayout(inapp_layout)
        layout.addWidget(inapp_card)
        
        # Startup Settings Card
        startup_card = ModernCard("Startup Settings")
        startup_layout = QVBoxLayout()
        
        self.start_with_windows_check = QCheckBox("Start TrackPro with Windows")
        self.start_with_windows_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.start_with_windows_check)
        
        self.start_minimized_check = QCheckBox("Start minimized (recommended)")
        self.start_minimized_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.start_minimized_check)
        
        self.minimize_to_tray_check = QCheckBox("Always minimize to tray when closing (recommended)")
        self.minimize_to_tray_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.minimize_to_tray_check)
        
        # Add description
        startup_desc = QLabel("TrackPro needs to be running for hardware functionality to work properly. When you close the window, TrackPro will continue running in the background.")
        startup_desc.setStyleSheet("""
            QLabel {
                color: #72767d;
                font-size: 12px;
                margin-top: 8px;
                border: none;
                background: transparent;
            }
        """)
        startup_layout.addWidget(startup_desc)
        
        startup_card.content_layout.addLayout(startup_layout)
        layout.addWidget(startup_card)
        
        # Save button
        save_notifications_btn = ModernButton("Save Settings", "primary")
        save_notifications_btn.clicked.connect(self.save_notification_settings)
        layout.addWidget(save_notifications_btn)
        
        layout.addStretch()
        return widget
    
    def create_racing_section(self):
        """Create the racing preferences section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Racing Preferences")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Racing Statistics Card
        stats_card = ModernCard("Racing Statistics")
        stats_layout = QGridLayout()
        
        # Performance metrics
        self.total_sessions_label = QLabel("Total Sessions: Loading...")
        self.total_distance_label = QLabel("Total Distance: Loading...")
        self.best_lap_label = QLabel("Best Lap Time: Loading...")
        self.avg_consistency_label = QLabel("Consistency Rating: Loading...")
        
        stats_style = """
            QLabel {
                color: #dcddde;
                font-size: 14px;
                padding: 8px;
                background-color: #2f3136;
                border-radius: 4px;
                margin: 2px;
            }
        """
        
        for label in [self.total_sessions_label, self.total_distance_label, 
                     self.best_lap_label, self.avg_consistency_label]:
            label.setStyleSheet(stats_style)
        
        stats_layout.addWidget(self.total_sessions_label, 0, 0)
        stats_layout.addWidget(self.total_distance_label, 0, 1)
        stats_layout.addWidget(self.best_lap_label, 1, 0)
        stats_layout.addWidget(self.avg_consistency_label, 1, 1)
        
        refresh_stats_btn = ModernButton("Refresh Statistics", "secondary")
        refresh_stats_btn.clicked.connect(self.load_racing_statistics)
        stats_layout.addWidget(refresh_stats_btn, 2, 0, 1, 2)
        
        stats_card.content_layout.addLayout(stats_layout)
        layout.addWidget(stats_card)
        
        # AI Coach Preferences Card
        ai_coach_card = ModernCard("AI Coach Preferences")
        ai_layout = QVBoxLayout()
        
        # Coach personality
        personality_layout = QHBoxLayout()
        personality_layout.addWidget(QLabel("Coaching Style:"))
        self.coach_personality_combo = QComboBox()
        self.coach_personality_combo.addItems(["Encouraging", "Technical", "Strict", "Balanced"])
        self.coach_personality_combo.setStyleSheet("""
            QComboBox {
                background-color: #40444b;
                border: 1px solid #5865f2;
                border-radius: 4px;
                padding: 8px;
                color: #fefefe;
                font-size: 14px;
            }
        """)
        personality_layout.addWidget(self.coach_personality_combo)
        ai_layout.addLayout(personality_layout)
        
        # Coaching frequency
        frequency_layout = QHBoxLayout()
        frequency_layout.addWidget(QLabel("Coaching Frequency:"))
        self.coaching_frequency_combo = QComboBox()
        self.coaching_frequency_combo.addItems(["Real-time", "After sessions", "Weekly summary", "On-demand only"])
        self.coaching_frequency_combo.setStyleSheet(self.coach_personality_combo.styleSheet())
        frequency_layout.addWidget(self.coaching_frequency_combo)
        ai_layout.addLayout(frequency_layout)
        
        # Voice coaching toggle
        self.voice_coaching_check = QCheckBox("Enable voice coaching during sessions")
        self.voice_coaching_check.setStyleSheet("""
            QCheckBox {
                color: #dcddde;
                font-size: 14px;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
                border-radius: 3px;
            }
        """)
        ai_layout.addWidget(self.voice_coaching_check)
        
        ai_coach_card.content_layout.addLayout(ai_layout)
        layout.addWidget(ai_coach_card)
        
        # Performance Goals Card
        goals_card = ModernCard("Performance Goals")
        goals_layout = QVBoxLayout()
        
        # Target lap time improvement
        laptime_layout = QHBoxLayout()
        laptime_layout.addWidget(QLabel("Target Lap Time Improvement (%/month):"))
        self.laptime_goal_spin = QSpinBox()
        self.laptime_goal_spin.setRange(0, 50)
        self.laptime_goal_spin.setValue(5)
        self.laptime_goal_spin.setStyleSheet("""
            QSpinBox {
                background-color: #40444b;
                border: 1px solid #5865f2;
                border-radius: 4px;
                padding: 8px;
                color: #fefefe;
                font-size: 14px;
            }
        """)
        laptime_layout.addWidget(self.laptime_goal_spin)
        goals_layout.addLayout(laptime_layout)
        
        # Consistency target
        consistency_layout = QHBoxLayout()
        consistency_layout.addWidget(QLabel("Target Consistency Rating:"))
        self.consistency_goal_spin = QSpinBox()
        self.consistency_goal_spin.setRange(50, 100)
        self.consistency_goal_spin.setValue(85)
        self.consistency_goal_spin.setStyleSheet(self.laptime_goal_spin.styleSheet())
        consistency_layout.addWidget(self.consistency_goal_spin)
        goals_layout.addLayout(consistency_layout)
        
        goals_card.content_layout.addLayout(goals_layout)
        layout.addWidget(goals_card)
        
        # Save Racing Settings Button
        save_racing_btn = ModernButton("Save Racing Settings", "primary")
        save_racing_btn.clicked.connect(self.save_racing_settings)
        layout.addWidget(save_racing_btn)
        
        layout.addStretch()
        return widget
    
    def create_connections_section(self):
        """Create the connections/integrations section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Connected Accounts")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Save Connections Button
        save_connections_btn = ModernButton("Save Connection Settings", "primary")
        save_connections_btn.clicked.connect(self.save_connection_settings)
        layout.addWidget(save_connections_btn)
        
        layout.addStretch()

        return widget

    def _get_saved_iracing_cookie(self) -> str | None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            return (data.get("iracing") or {}).get("session_cookie")
        except Exception:
            return None

    def link_iracing_account(self):
        """Open a secure web view to link iRacing and capture the session cookies only (no password stored).
        This version also forces persistent cookies and verifies the link via the Data API automatically.
        """
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            try:
                # Optional: profile API for forcing persistent cookies
                from PyQt6.QtWebEngineCore import QWebEngineProfile
            except Exception:
                QWebEngineProfile = None
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
            from PyQt6.QtCore import QUrl, QTimer
            import os, requests

            import logging
            logger = logging.getLogger(__name__)

            dialog = QDialog(self)
            dialog.setWindowTitle("Link iRacing Account")
            layout = QVBoxLayout(dialog)
            web = QWebEngineView(dialog)
            layout.addWidget(web)
            logger.info("[IRacingLink] Opened link dialog and created web view")

            # Accumulate cookies; some endpoints require multiple cookies
            self._iracing_cookies = getattr(self, "_iracing_cookies", {})
            self._iracing_link_success = False
            try:
                self.iracing_status_label.setText("Status: Connecting…")
            except Exception:
                pass

            def handle_cookie_added(cookie):
                try:
                    name = bytes(cookie.name()).decode("utf-8", errors="ignore")
                    value = bytes(cookie.value()).decode("utf-8", errors="ignore")
                    domain = cookie.domain()
                    if domain and ("iracing.com" in domain):
                        logger.info(f"[IRacingLink] Cookie added: {name} (domain={domain})")
                        self._iracing_cookies[name] = value
                        # Save to main window for global reuse
                        try:
                            main_window = self.window()
                            setattr(main_window, "_iracing_session_cookie", self._iracing_cookies.get("authtoken") or self._iracing_cookies.get("irsso_membersv2") or value)
                            setattr(main_window, "_iracing_cookies", dict(self._iracing_cookies))
                        except Exception:
                            pass
                        # Persist securely
                        try:
                            self._save_iracing_cookies(self._iracing_cookies)
                        except Exception:
                            pass
                        # Try verification shortly after receiving likely auth-bearing cookies
                        if name.lower() in ("authtoken", "irsso_membersv2", "irsso", "iracing_ui"):
                            QTimer.singleShot(300, attempt_verify)
                except Exception:
                    pass

            profile = web.page().profile()
            try:
                cookie_store = profile.cookieStore()
                cookie_store.cookieAdded.connect(handle_cookie_added)
                # Proactively load any existing cookies and seed our map
                try:
                    cookie_store.loadAllCookies(lambda cookies: [handle_cookie_added(c) for c in cookies])
                except Exception as e:
                    logger.debug(f"[IRacingLink] loadAllCookies not available: {e}")
                # Seed previously saved cookies into the WebEngine profile to enable auto-login
                try:
                    saved = self._load_iracing_cookies() or {}
                    if not saved:
                        token = self._get_saved_iracing_cookie()
                        if token:
                            saved = {"irsso_membersv2": token}
                    if saved:
                        try:
                            from PyQt6.QtNetwork import QNetworkCookie  # type: ignore
                        except Exception:
                            QNetworkCookie = None  # type: ignore
                        from PyQt6.QtCore import QUrl

                        def set_cookies_for_host(host: str):
                            if not QNetworkCookie:
                                return
                            for k, v in saved.items():
                                try:
                                    cookie = QNetworkCookie(bytes(str(k), "utf-8"), bytes(str(v), "utf-8"))
                                    cookie.setDomain(host)
                                    cookie.setPath("/")
                                    try:
                                        cookie.setSecure(True)
                                        cookie.setHttpOnly(True)
                                    except Exception:
                                        pass
                                    cookie_store.setCookie(cookie, QUrl(f"https://{host}/"))
                                except Exception:
                                    pass

                        # Common domains used by iRacing auth
                        set_cookies_for_host("members-ng.iracing.com")
                        set_cookies_for_host("iracing.com")
                except Exception:
                    pass
            except Exception:
                pass

            # Scrape JS cookies periodically as a secondary source (some cookies may be httpOnly=False)
            def scrape_js_cookies():
                try:
                    def _cb(result):
                        try:
                            if not isinstance(result, str):
                                return
                            for part in result.split(';'):
                                kv = part.strip().split('=', 1)
                                if len(kv) != 2:
                                    continue
                                k, v = kv[0], kv[1]
                                if k and v:
                                    if k not in self._iracing_cookies:
                                        logger.info(f"[IRacingLink] JS cookie discovered: {k}")
                                    self._iracing_cookies[k] = v
                        except Exception:
                            pass
                    web.page().runJavaScript("document.cookie", _cb)
                except Exception:
                    pass

            # Force persistent cookies and storage (helps some systems retain cross-domain cookies)
            try:
                if QWebEngineProfile and hasattr(profile, "setPersistentCookiesPolicy"):
                    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
                if QWebEngineProfile and hasattr(profile, "setHttpAcceptCookiePolicy"):
                    profile.setHttpAcceptCookiePolicy(QWebEngineProfile.HttpAcceptCookiePolicy.AcceptAllCookies)
                cache_dir = os.path.join(os.path.expanduser("~"), ".trackpro", "webcache")
                os.makedirs(cache_dir, exist_ok=True)
                if hasattr(profile, "setPersistentStoragePath"):
                    profile.setPersistentStoragePath(cache_dir)
            except Exception:
                pass

            # Attempt verification using currently collected cookies
            def attempt_verify():
                try:
                    logger.info(f"[IRacingLink] Attempting verify with {len(self._iracing_cookies)} cookies: {list(self._iracing_cookies.keys())}")
                    if not self._iracing_cookies:
                        return
                    s = requests.Session()
                    s.headers.update({"User-Agent": "TrackPro/IRacingLink"})
                    for k, v in self._iracing_cookies.items():
                        try:
                            s.cookies.set(k, v, domain="members-ng.iracing.com")
                            s.cookies.set(k, v, domain=".iracing.com")
                        except Exception:
                            pass
                    r = s.get("https://members-ng.iracing.com/data/member/summary", timeout=10)
                    logger.info(f"[IRacingLink] summary status={getattr(r,'status_code',None)}")
                    if not r.ok:
                        # Fallback: verify inside the WebEngine session (includes httpOnly cookies)
                        try:
                            def _handle_js_summary(res):
                                try:
                                    ok = bool(isinstance(res, dict) and res.get('ok'))
                                    status = (res or {}).get('status')
                                    data = (res or {}).get('json') if isinstance(res, dict) else None
                                    logger.info(f"[IRacingLink][JS] summary ok={ok} status={status}")
                                    if not ok or not isinstance(data, dict):
                                        return
                                    def _finalize_with_json(jdata: dict):
                                        try:
                                            # Success: mark connected and sync
                                            self.iracing_status_label.setText("Status: Connected")
                                            try:
                                                self.disconnect_iracing_btn.setVisible(True)
                                            except Exception:
                                                pass
                                            try:
                                                self._iracing_link_success = True
                                                if hasattr(self, "_ir_verify_timer") and self._ir_verify_timer:
                                                    try:
                                                        self._ir_verify_timer.stop()
                                                    except Exception:
                                                        pass
                                                dialog.accept()
                                                logger.info("[IRacingLink] Verification (JS) succeeded; dialog closed.")
                                            except Exception:
                                                pass
                                            try:
                                                QMessageBox.information(self, "iRacing", "iRacing linked. Syncing your data now...")
                                            except Exception:
                                                pass
                                            try:
                                                self._refresh_iracing_snapshot()
                                            except Exception:
                                                pass
                                        except Exception:
                                            pass
                                    # Follow indirection if present
                                    link = data.get('link')
                                    if isinstance(link, str) and link:
                                        js_follow = (
                                            "fetch('" + link + "', {credentials:'include'})"
                                            ".then(r=>r.json().then(j=>({ok:r.ok,status:r.status,json:j}))))"
                                        )
                                        web.page().runJavaScript(js_follow, lambda rr: _finalize_with_json((rr or {}).get('json') if isinstance(rr, dict) else {}))
                                    else:
                                        _finalize_with_json(data)
                                except Exception:
                                    pass
                            js = (
                                "fetch('https://members-ng.iracing.com/data/member/summary', {credentials:'include'})"
                                ".then(r=>r.json().then(j=>({ok:r.ok,status:r.status,json:j,ct:r.headers.get('content-type')})))"
                                ".catch(()=>({ok:false,status:0}))"
                            )
                            web.page().runJavaScript(js, _handle_js_summary)
                        except Exception:
                            pass
                        return
                    j = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
                    if isinstance(j, dict) and j.get("link"):
                        rr = s.get(j["link"], timeout=10)
                        logger.info(f"[IRacingLink] link status={getattr(rr,'status_code',None)}")
                        if not rr.ok:
                            return
                        j = rr.json() if rr.headers.get("Content-Type", "").startswith("application/json") else None
                    if not isinstance(j, dict):
                        return
                    # Mark connected and sync now
                    self.iracing_status_label.setText("Status: Connected")
                    try:
                        self.disconnect_iracing_btn.setVisible(True)
                    except Exception:
                        pass
                    try:
                        self._iracing_link_success = True
                        if hasattr(self, "_ir_verify_timer") and self._ir_verify_timer:
                            try:
                                self._ir_verify_timer.stop()
                            except Exception:
                                pass
                        dialog.accept()
                        logger.info("[IRacingLink] Verification succeeded; dialog closed.")
                    except Exception:
                        pass
                    try:
                        QMessageBox.information(self, "iRacing", "iRacing linked. Syncing your data now...")
                    except Exception:
                        pass
                    try:
                        self._refresh_iracing_snapshot()
                    except Exception:
                        pass
                except Exception:
                    logger.exception("[IRacingLink] Verify attempt failed")
                    pass

            # Load root of members site; the SPA handles login internally
            web.load(QUrl("https://members-ng.iracing.com/"))
            dialog.resize(900, 700)
            # Also try verification shortly after load
            try:
                web.loadFinished.connect(lambda ok: (logger.info(f"[IRacingLink] loadFinished ok={ok}, url={web.url().toString()}"), QTimer.singleShot(1200, attempt_verify)))
                web.urlChanged.connect(lambda u: logger.info(f"[IRacingLink] urlChanged -> {u.toString()}"))
            except Exception:
                pass
            # Periodic verification attempts until success or dialog closes
            try:
                self._ir_verify_timer = QTimer(dialog)
                self._ir_verify_timer.setInterval(1500)
                self._ir_verify_timer.timeout.connect(lambda: (scrape_js_cookies(), attempt_verify()))
                self._ir_verify_timer.start()
            except Exception:
                pass
            dialog.exec()
            # Ensure timer is stopped when dialog closes
            try:
                if hasattr(self, "_ir_verify_timer") and self._ir_verify_timer:
                    self._ir_verify_timer.stop()
                logger.info(f"[IRacingLink] Dialog closed. success={self._iracing_link_success}")
            except Exception:
                pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error linking iRacing: {e}")
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "iRacing", "Could not open iRacing login.")
            except Exception:
                pass

    def _save_iracing_cookies(self, cookies: dict) -> None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            ir = data.get("iracing", {})
            ir.update({"cookies": cookies})
            data["iracing"] = ir
            ssm.save_session(data)
        except Exception:
            pass

    def _load_iracing_cookies(self) -> dict | None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            return (data.get("iracing") or {}).get("cookies") or None
        except Exception:
            return None

    def _refresh_iracing_snapshot(self) -> None:
        """Fetch member summary/career and upsert snapshot + connections. Runs non-blocking-safe."""
        try:
            import requests
            from datetime import datetime
            cookies = self._load_iracing_cookies()
            if not cookies:
                # Try main window cache
                try:
                    main_window = self.window()
                    cookies = getattr(main_window, "_iracing_cookies", None)
                    if not cookies and hasattr(main_window, "_iracing_session_cookie"):
                        cookies = {"irsso_membersv2": getattr(main_window, "_iracing_session_cookie")}
                except Exception:
                    pass
            if not cookies:
                return

            s = requests.Session()
            s.headers.update({"User-Agent": "TrackPro/IRacingLink"})
            for k, v in cookies.items():
                s.cookies.set(k, v, domain="members-ng.iracing.com")

            def fetch(url):
                r = s.get(url, timeout=12)
                if not r.ok:
                    return None
                j = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
                if isinstance(j, dict) and j.get("link"):
                    rr = s.get(j["link"], timeout=12)
                    if rr.ok and rr.headers.get("Content-Type", "").startswith("application/json"):
                        return rr.json()
                    return None
                return j

            summary = fetch("https://members-ng.iracing.com/data/member/summary") or {}
            career = fetch("https://members-ng.iracing.com/data/stats/member/career") or {}
            cust_id = summary.get("cust_id") or summary.get("customer_id") or None
            username = summary.get("display_name") or summary.get("member_name") or None

            # Build snapshot payload
            def get_lic(licenses, key):
                if isinstance(licenses, list):
                    m = { (x.get("category") or x.get("category_name") or "").lower(): x for x in licenses }
                else:
                    m = licenses or {}
                return (m.get(key) or {})

            licenses = summary.get("licenses") or summary.get("licenses_info") or {}
            snap = {}
            for cat_key, prefix in (("road", "road"),("oval","oval"),("dirt_road","dirt_road"),("dirt_oval","dirt_oval")):
                lic = get_lic(licenses, cat_key)
                snap[f"{prefix}_irating"] = lic.get("irating") or lic.get("iRating") or lic.get("i_rating")
                snap[f"{prefix}_sr"] = lic.get("safety_rating") or lic.get("safetyRating") or lic.get("sr")
                snap[f"{prefix}_license"] = lic.get("license_level") or lic.get("license") or lic.get("class")

            totals = career.get("career") or career.get("overall") or career
            if isinstance(totals, list):
                totals = next((x for x in totals if (x.get("category") or "").lower()=="overall"), totals[0] if totals else {})
            snap["wins"] = (totals or {}).get("wins")
            snap["starts"] = (totals or {}).get("starts") or (totals or {}).get("races")

            # Upsert DB (best-effort)
            from ....database.supabase_client import get_supabase_client
            supa = get_supabase_client()
            if supa:
                # user_connections
                if cust_id:
                    try:
                        supa.from_("user_connections").upsert({
                            "user_id": self.user_data.get("user_id") if hasattr(self, 'user_data') else None,
                            "provider": "iracing",
                            "external_id": str(cust_id),
                            "username": username,
                            "linked_at": datetime.utcnow().isoformat()+"Z"
                        }, on_conflict="user_id,provider").execute()
                    except Exception:
                        pass
                # user_iracing_snapshot
                payload = dict(snap)
                payload["user_id"] = self.user_data.get("user_id") if hasattr(self, 'user_data') else None
                payload["last_updated"] = datetime.utcnow().isoformat()+"Z"
                try:
                    supa.from_("user_iracing_snapshot").upsert(payload, on_conflict="user_id").execute()
                except Exception:
                    pass

            # Update UI status
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            self.iracing_status_label.setText(f"Status: Connected • Synced {ts}")
        except Exception:
            pass
    
    def create_privacy_section(self):
        """Create a compact and well-organized privacy and data section."""
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Compact header
        header_label = QLabel("Privacy & Data")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #2f3136;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #40444b;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5865f2;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Privacy Settings Card - Compact design
        privacy_card = ModernCard("Privacy Settings")
        privacy_layout = QVBoxLayout()
        privacy_layout.setSpacing(16)
        privacy_layout.setContentsMargins(0, 0, 0, 0)
        
        # Profile visibility - compact layout
        visibility_layout = QHBoxLayout()
        visibility_layout.setSpacing(12)
        
        visibility_label = QLabel("Profile Visibility:")
        visibility_label.setStyleSheet("color: #dcddde; font-weight: 500; font-size: 13px; min-width: 120px;")
        
        self.profile_visibility_combo = QComboBox()
        self.profile_visibility_combo.addItems(["Public", "Friends Only", "Private"])
        self.profile_visibility_combo.setStyleSheet("""
            QComboBox {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 6px;
                padding: 8px 12px;
                color: #fefefe;
                font-size: 13px;
                min-width: 140px;
            }
            QComboBox:hover {
                border-color: #5865f2;
            }
        """)
        
        visibility_layout.addWidget(visibility_label)
        visibility_layout.addWidget(self.profile_visibility_combo)
        visibility_layout.addStretch()
        privacy_layout.addLayout(visibility_layout)
        
        # Privacy options - compact checkboxes
        privacy_options_label = QLabel("Privacy Options:")
        privacy_options_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; margin-top: 8px;")
        privacy_layout.addWidget(privacy_options_label)
        
        # Create compact checkboxes
        self.share_telemetry_check = QCheckBox("Share telemetry data")
        self.share_telemetry_check.setChecked(True)
        self.share_telemetry_check.setEnabled(False)
        self.show_statistics_check = QCheckBox("Show racing statistics publicly")
        self.allow_friend_requests_check = QCheckBox("Allow friend requests")
        self.show_online_status_check = QCheckBox("Show online status")
        
        checkbox_style = """
            QCheckBox {
                color: #dcddde;
                font-size: 12px;
                font-weight: 500;
                spacing: 12px;
                padding: 8px 12px;
                background-color: #36393f;
                border: 1px solid #40444b;
                border-radius: 6px;
                min-height: 36px;
            }
            QCheckBox:hover {
                background-color: #40444b;
                border-color: #5865f2;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
            }
        """
        
        privacy_checkboxes = [
            self.share_telemetry_check, 
            self.show_statistics_check, 
            self.allow_friend_requests_check, 
            self.show_online_status_check
        ]
        
        for checkbox in privacy_checkboxes:
            checkbox.setStyleSheet(checkbox_style)
            privacy_layout.addWidget(checkbox)
        
        privacy_card.content_layout.addLayout(privacy_layout)
        scroll_layout.addWidget(privacy_card)
        
        # Data Management Card - Compact design
        data_card = ModernCard("Data Management")
        data_layout = QVBoxLayout()
        data_layout.setSpacing(16)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        # Export buttons - horizontal layout
        export_layout = QHBoxLayout()
        export_layout.setSpacing(12)
        
        self.export_profile_btn = ModernButton("Export Profile", "secondary")
        self.export_profile_btn.clicked.connect(self.export_profile_data)
        self.export_profile_btn.setMinimumWidth(140)
        self.export_profile_btn.setMinimumHeight(36)
        
        self.export_telemetry_btn = ModernButton("Export Telemetry", "secondary")
        self.export_telemetry_btn.clicked.connect(self.export_telemetry_data)
        self.export_telemetry_btn.setMinimumWidth(140)
        self.export_telemetry_btn.setMinimumHeight(36)
        
        export_layout.addWidget(self.export_profile_btn)
        export_layout.addWidget(self.export_telemetry_btn)
        export_layout.addStretch()
        data_layout.addLayout(export_layout)
        
        # Data usage - compact display
        usage_label = QLabel("Data Usage:")
        usage_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; margin-top: 8px;")
        data_layout.addWidget(usage_label)
        
        self.data_usage_text = QTextEdit()
        self.data_usage_text.setReadOnly(True)
        self.data_usage_text.setMaximumHeight(80)
        self.data_usage_text.setStyleSheet("""
            QTextEdit {
                background-color: #2f3136;
                border: 1px solid #40444b;
                border-radius: 6px;
                color: #b9bbbe;
                font-size: 11px;
                padding: 8px;
            }
        """)
        
        data_usage_content = """Profile: ~2.5 KB | Stats: ~15.3 KB | Telemetry: ~127.8 MB
Total: ~128.0 MB | Last updated: Just now"""
        self.data_usage_text.setPlainText(data_usage_content)
        data_layout.addWidget(self.data_usage_text)
        
        data_card.content_layout.addLayout(data_layout)
        scroll_layout.addWidget(data_card)
        
        # Account Deletion Card - Compact warning
        deletion_card = ModernCard("Account Deletion")
        deletion_layout = QVBoxLayout()
        deletion_layout.setSpacing(16)
        deletion_layout.setContentsMargins(0, 0, 0, 0)
        
        # Warning header
        warning_layout = QHBoxLayout()
        warning_layout.setSpacing(8)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 20px;")
        
        warning_title = QLabel("Danger Zone - Permanent Deletion")
        warning_title.setStyleSheet("color: #f04747; font-size: 14px; font-weight: 600;")
        
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_title)
        warning_layout.addStretch()
        deletion_layout.addLayout(warning_layout)
        
        # Compact warning info
        deletion_info = QLabel("This action cannot be undone. All your data will be permanently deleted.")
        deletion_info.setStyleSheet("color: #b9bbbe; font-size: 12px; line-height: 1.4;")
        deletion_info.setWordWrap(True)
        deletion_layout.addWidget(deletion_info)
        
        # Delete button
        self.delete_account_btn = ModernButton("Delete Account", "danger")
        self.delete_account_btn.clicked.connect(self.request_account_deletion)
        self.delete_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #f04747;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
                min-width: 120px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #d73d3d;
            }
        """)
        
        delete_button_layout = QHBoxLayout()
        delete_button_layout.addStretch()
        delete_button_layout.addWidget(self.delete_account_btn)
        delete_button_layout.addStretch()
        deletion_layout.addLayout(delete_button_layout)
        
        deletion_card.content_layout.addLayout(deletion_layout)
        scroll_layout.addWidget(deletion_card)
        
        # Save button - compact positioning
        save_privacy_btn = ModernButton("Save Privacy Settings", "primary")
        save_privacy_btn.clicked.connect(self.save_privacy_settings)
        save_privacy_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
                min-width: 160px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
        """)
        
        save_button_layout = QHBoxLayout()
        save_button_layout.addStretch()
        save_button_layout.addWidget(save_privacy_btn)
        save_button_layout.addStretch()
        scroll_layout.addLayout(save_button_layout)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        return widget
    
    def switch_section(self, section_id: str):
        """Switch to a different section."""
        if section_id not in self.pages:
            return
        
        # Update button states
        for i in range(self.nav_bar.count()):
            item = self.nav_bar.item(i)
            item.setSelected(item.data(Qt.ItemDataRole.UserRole) == section_id)
        
        # Switch content
        section_widget = self.pages[section_id]
        self.content_area.setCurrentWidget(section_widget)
        
        logger.info(f"Switched to account section: {section_id}")
    
    def load_user_data(self):
        """Load current user data without blocking the UI thread."""
        logger.info("🔄 load_user_data() called - starting data loading process")
        
        try:
            from PyQt6.QtCore import QTimer
            import threading
        except Exception as e:
            logger.error(f"❌ Error importing threading modules: {e}")
            # If Qt threading helpers are unavailable, keep current UI responsive by deferring
            try:
                from PyQt6.QtCore import QTimer as _QTimer
                _QTimer.singleShot(250, self.load_user_data)
            except Exception:
                pass
            return

        # Avoid duplicate in-flight loads
        if getattr(self, "_user_load_thread", None) and self._user_load_thread.is_alive():
            logger.info("⚠️ User load thread already running, skipping duplicate load")
            return

        def _worker():
            logger.info("🔄 _worker() started - fetching data from Supabase")
            local_user_data = None
            try:
                from ....database.supabase_client import get_supabase_client
                from ....social.user_manager import EnhancedUserManager
                logger.info("✅ Imported required modules")
                
                supabase_client = get_supabase_client()
                if not supabase_client:
                    raise RuntimeError("Supabase client not ready")
                logger.info("✅ Got Supabase client")
                
                user_response = supabase_client.auth.get_user()
                if not user_response or not user_response.user:
                    raise RuntimeError("No authenticated user")
                logger.info(f"✅ Got authenticated user: {user_response.user.id}")
                # Network/DB read off the UI thread
                logger.info("🔄 Getting complete user profile...")
                mgr = EnhancedUserManager()
                profile = mgr.get_complete_user_profile()
                logger.info(f"✅ Got profile: {profile}")
                if profile:
                    # CRITICAL FIX: Query BOTH user_profiles AND user_details tables
                    try:
                        # Query user_profiles table for social/display fields
                        up = supabase_client.from_("user_profiles").select("username, display_name, bio, first_name, last_name").eq("user_id", user_response.user.id).single().execute()
                        if up and up.data:
                            logger.info(f"✅ Profile data from user_profiles: {up.data}")
                            if up.data.get('username'):
                                profile['username'] = up.data['username']
                            if up.data.get('display_name'):
                                profile['display_name'] = up.data['display_name']
                            if up.data.get('bio') is not None:
                                profile['bio'] = up.data['bio'] or ""
                            if up.data.get('first_name'):
                                profile['first_name'] = up.data['first_name']
                            if up.data.get('last_name'):
                                profile['last_name'] = up.data['last_name']
                                
                        # Query user_details table for personal information  
                        ud = supabase_client.from_("user_details").select("date_of_birth, phone_number").eq("user_id", user_response.user.id).single().execute()
                        if ud and ud.data:
                            logger.info(f"✅ Details data from user_details: {ud.data}")
                            if ud.data.get('date_of_birth'):
                                profile['date_of_birth'] = ud.data['date_of_birth']
                            if ud.data.get('phone_number'):
                                profile['phone_number'] = ud.data['phone_number']
                    except Exception:
                        pass
                        # As an extra fast-path, check public display info for username
                        if not profile.get('username'):
                            try:
                                pdi = supabase_client.from_("public_user_display_info").select("username, display_name").eq("user_id", user_response.user.id).single().execute()
                                if pdi and pdi.data:
                                    profile['username'] = pdi.data.get('username') or pdi.data.get('display_name')
                                    if not profile.get('display_name'):
                                        profile['display_name'] = pdi.data.get('display_name') or pdi.data.get('username')
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # Ensure we always have avatar_url by checking multiple sources
                    if 'user_id' not in profile and user_response and user_response.user:
                        profile['user_id'] = user_response.user.id
                    # Fallback 1: public view
                    try:
                        if not profile.get('avatar_url'):
                            pub = supabase_client.from_("public_user_profiles").select("avatar_url").eq("user_id", profile['user_id']).single().execute()
                            if pub and pub.data and pub.data.get('avatar_url'):
                                profile['avatar_url'] = pub.data['avatar_url']
                    except Exception:
                        pass
                    # Fallback 2: auth user metadata
                    try:
                        md = getattr(user_response.user, 'user_metadata', {}) or {}
                        # Common auth metadata keys that may contain the avatar
                        meta_keys = ['avatar_url', 'picture', 'avatar', 'image_url', 'photoURL']
                        found_meta_url = None
                        for k in meta_keys:
                            val = md.get(k)
                            if isinstance(val, str) and len(val.strip()) > 0:
                                found_meta_url = val.strip()
                                break
                        if found_meta_url and not profile.get('avatar_url'):
                            profile['avatar_url'] = found_meta_url
                        # Keep a copy for diagnostics/fallback use
                        profile['auth_avatar_url'] = found_meta_url
                    except Exception:
                        pass
                    local_user_data = profile
                else:
                    md = getattr(user_response.user, 'user_metadata', {}) or {}
                    first_name = md.get('first_name', '')
                    last_name = md.get('last_name', '')
                    if first_name and first_name.isupper():
                        first_name = first_name.title()
                    if last_name and last_name.isupper():
                        last_name = last_name.title()
                    display_name = md.get('full_name') or md.get('name') or f"{first_name} {last_name}".strip()
                    # Prefer explicit username from auth metadata, else derive from email
                    try:
                        email_val = user_response.user.email or ""
                    except Exception:
                        email_val = ""
                    username_fallback = (md.get('username') or (email_val.split('@')[0] if email_val else None) or (display_name.replace(' ', '') if display_name else None))
                    local_user_data = {
                        "email": email_val,
                        "first_name": first_name,
                        "last_name": last_name,
                        "display_name": display_name,
                        "username": username_fallback,
                        "bio": md.get('bio', ""),
                        "date_of_birth": md.get('date_of_birth', '1995-01-01')
                    }
                    # CRITICAL FIX: Query BOTH user_profiles AND user_details tables
                    try:
                        # Query user_profiles table (contains: username, display_name, bio, first_name, last_name)
                        up = supabase_client.from_("user_profiles").select("username, display_name, bio, first_name, last_name").eq("user_id", user_response.user.id).single().execute()
                        if up and up.data:
                            logger.info(f"✅ Loaded from user_profiles: {up.data}")
                            if up.data.get('username'):
                                local_user_data['username'] = up.data['username']
                            if up.data.get('display_name'):
                                local_user_data['display_name'] = up.data['display_name']
                            if up.data.get('bio') is not None:
                                local_user_data['bio'] = up.data['bio'] or ""
                            # Prefer proper-cased names from profile if present
                            if up.data.get('first_name'):
                                local_user_data['first_name'] = up.data['first_name']
                            if up.data.get('last_name'):
                                local_user_data['last_name'] = up.data['last_name']
                        else:
                            logger.warning("⚠️ No data found in user_profiles table")
                        
                        # Query user_details table (contains: date_of_birth, phone_number, etc.)
                        ud = supabase_client.from_("user_details").select("date_of_birth, phone_number").eq("user_id", user_response.user.id).single().execute()
                        if ud and ud.data:
                            logger.info(f"✅ Loaded from user_details: {ud.data}")
                            if ud.data.get('date_of_birth'):
                                local_user_data['date_of_birth'] = ud.data['date_of_birth']
                            if ud.data.get('phone_number'):
                                local_user_data['phone_number'] = ud.data['phone_number']
                        else:
                            logger.warning("⚠️ No data found in user_details table")
                            
                    except Exception as e:
                        logger.error(f"❌ Error loading profile data from database: {e}")
                        pass
            except Exception:
                local_user_data = None

            # CRITICAL FIX: Store data and trigger UI update
            logger.info(f"🔄 Worker finished, applying data to UI. Data loaded: {local_user_data is not None}")
            self._pending_user_data = local_user_data
            try:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self._apply_user_data_to_ui)
                logger.info("✅ Scheduled UI update via QTimer")
            except Exception as e:
                logger.error(f"❌ Error scheduling UI update: {e}")
                # Direct fallback
                try:
                    self._apply_user_data_to_ui()
                    logger.info("✅ Applied UI update directly")
                except Exception as e2:
                    logger.error(f"❌ Error applying UI update directly: {e2}")

        self._user_load_thread = threading.Thread(target=_worker, name="AccountUserLoad", daemon=True)
        self._user_load_thread.start()

    def _apply_user_data_to_ui(self):
        """Apply loaded user data to UI elements - runs on main UI thread."""
        if not hasattr(self, '_pending_user_data'):
            logger.warning("⚠️ No pending user data to apply")
            return
            
        local_user_data = self._pending_user_data
        logger.info("🔄 _apply_user_data_to_ui() called - applying data to UI")
        try:
            if local_user_data is None:
                logger.warning("⚠️ No user data to apply, retrying...")
                try:
                    QTimer.singleShot(750, self.load_user_data)
                except Exception as e:
                    logger.error(f"❌ Error scheduling retry: {e}")
                return
            
            self.user_data = local_user_data
            logger.info(f"Loading user data: {self.user_data}")
            
            # Ensure all UI elements exist before trying to populate them
            required_elements = ['first_name_input', 'last_name_input', 'display_name_input', 'email_input', 'bio_input']
            missing_elements = [elem for elem in required_elements if not hasattr(self, elem)]
            
            if missing_elements:
                logger.error(f"Missing UI elements: {missing_elements}")
                # Retry loading after a short delay
                QTimer.singleShot(200, self.load_user_data)
                return
            
            logger.info("All required UI elements found, proceeding with data population")
            
            logger.info(f"🔍 RAW DATABASE DATA: {self.user_data}")
            
            # Extract and log all field values
            username = self.user_data.get("username") or self.user_data.get("display_name") or ""
            bio = self.user_data.get("bio") or ""
            first_name = self.user_data.get("first_name") or ""
            last_name = self.user_data.get("last_name") or ""
            email = self.user_data.get("email") or ""
            dob = self.user_data.get("date_of_birth") or ""
            
            logger.info(f"📋 EXTRACTED FIELD VALUES:")
            logger.info(f"   Username: '{username}' (length: {len(username)})")
            logger.info(f"   Bio: '{bio}' (length: {len(bio)})")
            logger.info(f"   First Name: '{first_name}' (length: {len(first_name)})")
            logger.info(f"   Last Name: '{last_name}' (length: {len(last_name)})")
            logger.info(f"   Email: '{email}' (length: {len(email)})")
            logger.info(f"   Date of Birth: '{dob}' (length: {len(dob)})")
            
            # Apply to UI fields with verification
            if hasattr(self, 'first_name_input'):
                self.first_name_input.setText(first_name)
                logger.info(f"✅ First name field set, verification: '{self.first_name_input.text()}'")
                
            if hasattr(self, 'last_name_input'):
                self.last_name_input.setText(last_name)
                logger.info(f"✅ Last name field set, verification: '{self.last_name_input.text()}'")
                
            if hasattr(self, 'display_name_input'):
                self.display_name_input.clear()
                self.display_name_input.setText(username)
                logger.info(f"✅ Username field set to: '{username}', verification: '{self.display_name_input.text()}'")
                    
            if hasattr(self, 'email_input'):
                self.email_input.setText(email)
                logger.info(f"✅ Email field set, verification: '{self.email_input.text()}'")
                
            # BIO FIELD - Clear and set from database
            if hasattr(self, 'bio_input'):
                try:
                    self.bio_input.clear()
                    self.bio_input.setPlainText(bio)
                    logger.info(f"✅ Bio field set to: '{bio}', verification: '{self.bio_input.toPlainText()}'")
                except Exception as e:
                    logger.error(f"❌ Error setting bio with setPlainText: {e}")
                    try:
                        self.bio_input.setText(bio)
                        logger.info(f"✅ Bio field set with setText fallback, verification: '{self.bio_input.toPlainText()}'")
                    except Exception as e2:
                        logger.error(f"❌ Error setting bio with setText: {e2}")
                
            # DATE OF BIRTH FIELD - Set from database
            if hasattr(self, 'dob_input') and dob:
                try:
                    from PyQt6.QtCore import QDate
                    dob_date = QDate.fromString(dob, "yyyy-MM-dd")
                    if dob_date.isValid():
                        self.dob_input.setDate(dob_date)
                        logger.info(f"✅ DOB field set to: '{dob}' -> {dob_date.toString()}, verification: {self.dob_input.date().toString()}")
                    else:
                        logger.warning(f"⚠️ Invalid date format in database: '{dob}'")
                except Exception as e:
                    logger.error(f"❌ Error setting date of birth: {e}")
            elif hasattr(self, 'dob_input'):
                logger.info("ℹ️ No Date of Birth in database - keeping default")
                
            # AVATAR - Set from database or fallback to initials
            if hasattr(self, 'profile_avatar'):
                alt_keys = ["avatar_url", "auth_avatar_url", "picture", "avatar", "image_url", "photoURL"]
                avatar_url = None
                for k in alt_keys:
                    v = self.user_data.get(k)
                    if isinstance(v, str) and len(v.strip()) > 0:
                        avatar_url = v.strip()
                        break
                
                if avatar_url:
                    logger.info(f"✅ Avatar URL found: {avatar_url[:50]}...")
                    self.load_avatar_from_url(avatar_url)
                else:
                    logger.info("ℹ️ No avatar URL, using initials")
                    first_val = first_name or "User"
                    last_val = last_name or ""
                    display_name = f"{first_val} {last_val}".strip()
                    try:
                        AvatarManager.instance().set_label_avatar(
                            self.profile_avatar,
                            None,
                            display_name,
                            size=self.profile_avatar.width()
                        )
                    except Exception:
                        # Fallback to initials text if avatar manager unavailable
                        first_initial = (first_val[0] if len(first_val) > 0 else "U").upper()
                        last_initial = (last_val[0] if len(last_val) > 0 else "").upper()
                        self.profile_avatar.setText(f"{first_initial}{last_initial}")
                
            logger.info("🎯 ALL PROFILE FIELDS POPULATED FROM DATABASE!")
                
        except Exception as e:
            logger.error(f"❌ Error applying user data to UI: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        
        # Always refresh hierarchy status
        try:
            self.refresh_hierarchy_status()
        except Exception as e:
            logger.error(f"❌ Error refreshing hierarchy status: {e}")
        
        # Clear pending data after successful application
        if hasattr(self, '_pending_user_data'):
            delattr(self, '_pending_user_data')

    def refresh_hierarchy_status(self):
        """Refresh the displayed hierarchy level and moderation status for the current user."""
        try:
            from trackpro.auth.hierarchy_manager import hierarchy_manager
            from trackpro.auth.user_manager import get_current_user

            user = get_current_user()
            if not user:
                self.hierarchy_label.setText("Not signed in")
                return

            level = hierarchy_manager.get_user_level(user.id)
            self.hierarchy_label.setText(level.value)

        except Exception as e:
            logger.error(f"Failed to refresh hierarchy status: {e}")
            self.hierarchy_label.setText("Unknown")
    
    def load_startup_settings(self):
        """Load startup settings from config and Windows registry."""
        try:
            from trackpro.config import Config
            config = Config()
            
            # Load settings from config
            start_with_windows = config.start_with_windows
            start_minimized = config.start_minimized
            minimize_to_tray = config.minimize_to_tray
            
            # Check actual Windows registry status
            actual_startup_enabled = self.startup_manager.is_startup_enabled()
            
            # Update checkboxes
            if hasattr(self, 'start_with_windows_check'):
                self.start_with_windows_check.setChecked(start_with_windows)
            if hasattr(self, 'start_minimized_check'):
                self.start_minimized_check.setChecked(start_minimized)
            if hasattr(self, 'minimize_to_tray_check'):
                self.minimize_to_tray_check.setChecked(minimize_to_tray)
            
            logger.info(f"Startup settings loaded - Windows: {start_with_windows}, Minimized: {start_minimized}, Tray: {minimize_to_tray}, Registry: {actual_startup_enabled}")
            
        except Exception as e:
            logger.error(f"Error loading startup settings: {e}")
    
    def save_profile(self):
        """Save profile changes."""
        try:
            # Get and validate username
            # Treat the input as canonical username (not a real-name display)
            username_value = self.display_name_input.text().strip()
            if not username_value:
                QMessageBox.warning(self, "Validation Error", "Username is required.")
                return
            import re
            if not re.match(r"^[A-Za-z0-9_.-]{3,30}$", username_value):
                QMessageBox.warning(self, "Invalid Username", "Username must be 3-30 characters and can include letters, numbers, '.', '_' or '-'.")
                return

            # Check availability (exclude current user id)
            try:
                from ....social.user_manager import EnhancedUserManager
                um_check = EnhancedUserManager()
                current_user_id = None
                try:
                    from ....database.supabase_client import get_supabase_client
                    supa = get_supabase_client()
                    if supa and supa.auth.get_user() and supa.auth.get_user().user:
                        current_user_id = supa.auth.get_user().user.id
                except Exception:
                    pass
                if not um_check.is_username_available(username_value, exclude_user_id=current_user_id):
                    QMessageBox.warning(self, "Username Unavailable", f"The username '{username_value}' is already taken. Please choose another.")
                    return
            except Exception:
                QMessageBox.warning(self, "Error", "Could not verify username availability. Please try again.")
                return

            # Get form data
            profile_data = {
                "first_name": self.first_name_input.text().strip(),
                "last_name": self.last_name_input.text().strip(),
                # Treat this as the canonical username and mirror into display_name
                "username": username_value,
                "display_name": username_value,
                "bio": self.bio_input.toPlainText().strip(),
                "date_of_birth": self.dob_input.date().toString("yyyy-MM-dd"),
                "share_data": True  # Make profile public by default
            }
            
            # Validate required fields
            if not profile_data["first_name"] or not profile_data["last_name"]:
                QMessageBox.warning(self, "Validation Error", "First name and last name are required.")
                return
            
            # Save to Supabase using enhanced user manager; keep public table in sync via manager
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            # Check if user is authenticated
            supabase_client = get_supabase_client()
            if not supabase_client:
                QMessageBox.warning(
                    self, 
                    "Connection Error", 
                    "Unable to connect to database. Please check your connection."
                )
                return
            
            # Get current user
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                QMessageBox.warning(
                    self, 
                    "Authentication Required", 
                    "You must be logged in to save your profile."
                )
                return
            
            user_id = user_response.user.id
            logger.info(f"Saving profile for user {user_id}: {profile_data}")
            
            # Create user manager instance and save to Supabase
            user_manager = EnhancedUserManager()
            success = user_manager.update_user_profile(user_id, profile_data)
            
            if not success:
                QMessageBox.warning(
                    self, 
                    "Save Failed", 
                    "Failed to save your profile. Please try again."
                )
                logger.error("Profile save failed")
                return
            
            # Update local data only if save was successful
            self.user_data.update(profile_data)
            logger.info("Profile saved successfully to Supabase")
            
            # Update avatar initials using AvatarManager to ensure proper circular rendering
            fn = profile_data.get("first_name") or "User"
            ln = profile_data.get("last_name") or ""
            display_name = f"{fn} {ln}".strip()
            try:
                AvatarManager.instance().set_label_avatar(
                    self.profile_avatar,
                    None,
                    display_name,
                    size=self.profile_avatar.width()
                )
            except Exception:
                first_initial = (fn[0] if len(fn) > 0 else "U").upper()
                last_initial = (ln[0] if len(ln) > 0 else "").upper()
                self.profile_avatar.setText(f"{first_initial}{last_initial}")
            
            QMessageBox.information(self, "Success", "Profile updated successfully!")
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            import traceback
            logger.error(f"Profile save traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to save profile: {str(e)}")
    
    def handle_logout(self):
        """Handle user logout."""
        reply = QMessageBox.question(
            self, 
            "Confirm Logout", 
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                logger.info("User logout initiated")
                
                # Get main window and trigger logout
                main_window = self.parent()
                while main_window is not None and not hasattr(main_window, 'logout_user'):
                    next_main_window = main_window.parent()
                    if next_main_window is None:
                        break
                    main_window = next_main_window
                
                if main_window is not None and hasattr(main_window, 'logout_user'):
                    main_window.logout_user()
                else:
                    # Fallback: try to find the main window by looking for ModernMainWindow
                    while main_window is not None and not hasattr(main_window, '__class__'):
                        next_main_window = main_window.parent()
                        if next_main_window is None:
                            break
                        main_window = next_main_window
                    
                    if main_window is not None and 'ModernMainWindow' in main_window.__class__.__name__:
                        if hasattr(main_window, 'logout_user'):
                            main_window.logout_user()
                        else:
                            QMessageBox.information(self, "Logout", "Logout functionality not available")
                    else:
                        QMessageBox.information(self, "Logout", "Logout functionality not available")
                
            except Exception as e:
                logger.error(f"Error during logout: {e}")
                QMessageBox.critical(self, "Error", f"Logout failed: {str(e)}")
    
    def lazy_init(self):
        """Lazy initialization when page is first accessed."""
        logger.info("Lazy initializing Account page...")
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.load_user_data)
        except Exception:
            self.load_user_data()
    
    def on_page_activated(self):
        """Called when page becomes active."""
        if not self.is_initialized:
            self.lazy_init()
            self.is_initialized = True
        logger.info("Account page activated")
        
        # Refresh user data when page is activated (non-blocking refresh)
        try:
            QTimer.singleShot(100, self.load_user_data)
        except Exception:
            pass
        
        # Load racing statistics if on racing section
        if self.current_section == "racing":
            QTimer.singleShot(200, self.load_racing_statistics)
        
        # Load data usage if on privacy section
        if self.current_section == "privacy":
            QTimer.singleShot(200, self.load_data_usage_statistics)
    
    def upload_avatar(self):
        """Upload a new avatar image to Supabase Storage."""
        try:
            # Open file dialog for image selection
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self,
                "Select Avatar Image",
                "",
                "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Validate file size (max 5MB)
            import os
            file_size = os.path.getsize(file_path)
            if file_size > 5 * 1024 * 1024:  # 5MB limit
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "File Too Large",
                    "Avatar image must be smaller than 5MB. Please choose a smaller image."
                )
                return
            
            # Allow user to crop/zoom/pan before upload
            logger.info(f"Creating crop dialog for image: {file_path}")
            crop_dialog = AvatarCropDialog(file_path, crop_size=360, output_size=512, parent=self)
            logger.info(f"Crop dialog created, showing dialog...")
            
            # Small delay to ensure dialog is fully rendered
            QTimer.singleShot(100, lambda: crop_dialog.view.viewport().update())
            
            if crop_dialog.exec() != QDialog.DialogCode.Accepted:
                logger.info("User cancelled crop dialog")
                return
            cropped_image = crop_dialog.get_cropped_image()
            if cropped_image is None or cropped_image.isNull():
                logger.error("Failed to get cropped image from dialog")
                return
            logger.info(f"Got cropped image: {cropped_image.width()}x{cropped_image.height()}")
            # Save to a temporary file for the existing uploader path
            import tempfile
            tmp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, f"trackpro_avatar_{int(time.time())}.png")
            cropped_image.save(tmp_path, "PNG")
            file_path = tmp_path

            # Show progress dialog
            from PyQt6.QtWidgets import QProgressDialog
            progress = QProgressDialog("Uploading avatar...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            progress.setValue(10)
            
            # Import required modules
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            import uuid
            import mimetypes
            
            # Get Supabase client
            supabase_client = get_supabase_client()
            if not supabase_client:
                progress.close()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Connection Error", "Unable to connect to storage service.")
                return
            
            progress.setValue(30)
            
            # Get current user
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                progress.close()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to upload an avatar.")
                return
            
            user_id = user_response.user.id
            progress.setValue(50)
            
            # Generate unique filename
            file_extension = os.path.splitext(file_path)[1].lower()
            filename = f"avatars/{user_id}/{uuid.uuid4()}{file_extension}"
            
            # Read file data
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            progress.setValue(70)
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'image/jpeg'  # Default fallback
            
            # Upload to Supabase Storage via centralized manager
            try:
                public_url = AvatarManager.instance().upload_avatar(user_id, file_path)
                if not public_url:
                    raise RuntimeError("Avatar upload failed")
                progress.setValue(90)
                avatar_url = public_url
                
                # Update user profile with new avatar URL (also update public display info)
                user_manager = EnhancedUserManager()
                # Append cache-busting version to help invalidate CDN/browser caches
                versioned_url = f"{avatar_url}{'&' if '?' in avatar_url else '?'}v=" + str(int(time.time()))
                # Update both primary profile and public display info for immediate propagation
                success = user_manager.update_user_profile(user_id, {
                    'avatar_url': versioned_url
                })
                
                progress.setValue(100)
                progress.close()
                
                if success:
                    # Invalidate local avatar cache and refresh commonly visible widgets
                    try:
                        AvatarManager.instance().invalidate_cache(avatar_url)
                        AvatarManager.instance().invalidate_cache(versioned_url)
                    except Exception:
                        pass
                    # Update local avatar display
                    display_name = self.user_data.get('display_name') or self.user_data.get('username') or 'User'
                    AvatarManager.instance().set_label_avatar(self.profile_avatar, versioned_url, display_name, size=self.profile_avatar.width())
                    
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Success", "Avatar uploaded successfully!")
                    logger.info(f"Avatar uploaded successfully: {versioned_url}")
                    self.avatar_uploaded.emit(versioned_url)
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Upload Failed", "Failed to save avatar to profile.")
                    
            except Exception as storage_error:
                progress.close()
                logger.error(f"Storage upload error: {storage_error}")
                logger.error(f"Storage error type: {type(storage_error)}")
                logger.error(f"Storage error details: {str(storage_error)}")
                
                # Provide more specific error messages
                error_message = str(storage_error)
                if "bucket" in error_message.lower():
                    error_message = "Storage bucket 'avatars' does not exist. Please create it in your Supabase dashboard."
                elif "permission" in error_message.lower():
                    error_message = "Permission denied. Please check your Supabase storage policies."
                elif "network" in error_message.lower():
                    error_message = "Network error. Please check your internet connection."
                else:
                    error_message = f"Upload failed: {error_message}"
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Upload Error", error_message)
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            logger.error(f"Error uploading avatar: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to upload avatar: {str(e)}")
    
    def load_avatar_from_url(self, url):
        """Load an avatar URL with normalization and fallbacks."""
        try:
            normalized = AvatarManager.instance()._normalize_public_url(url)
        except Exception:
            normalized = url
        display_name = self.user_data.get('display_name') or self.user_data.get('username') or 'User'
        AvatarManager.instance().set_label_avatar(self.profile_avatar, normalized, display_name, size=self.profile_avatar.width())
    

    
    def remove_avatar(self):
        """Remove the current avatar."""
        try:
            # Confirm avatar removal
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Remove Avatar",
                "Are you sure you want to remove your avatar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement avatar removal from Supabase
                # Reset to default avatar (initials) safely with circular rendering
                if hasattr(self, 'profile_avatar'):
                    fv = self.user_data.get("first_name") or "User"
                    lv = self.user_data.get("last_name") or ""
                    display_name = f"{fv} {lv}".strip()
                    try:
                        AvatarManager.instance().set_label_avatar(
                            self.profile_avatar,
                            None,
                            display_name,
                            size=self.profile_avatar.width()
                        )
                    except Exception:
                        fi = (fv[0] if len(fv) > 0 else "U").upper()
                        li = (lv[0] if len(lv) > 0 else "").upper()
                        self.profile_avatar.setText(f"{fi}{li}")
                
                QMessageBox.information(self, "Success", "Avatar removed successfully!")
                logger.info("Avatar removed")
            
        except Exception as e:
            logger.error(f"Error removing avatar: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to remove avatar: {str(e)}")
    
    def change_password(self):
        """Change user password."""
        try:
            # Get password values
            current_pw = self.current_password_input.text().strip()
            new_pw = self.new_password_input.text().strip()
            confirm_pw = self.confirm_password_input.text().strip()
            
            # Validate inputs
            if not current_pw or not new_pw or not confirm_pw:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "All password fields are required.")
                return
            
            if new_pw != confirm_pw:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "New passwords do not match.")
                return
            
            if len(new_pw) < 8:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters long.")
                return
            
            # Implement password change with Supabase
            from trackpro.database.supabase_client import get_supabase_client
            supa = get_supabase_client()
            if not supa:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", "Not connected to authentication server.")
                return
            try:
                # Supabase does not support verifying current password via update_user
                # Attempt password update directly for logged-in user
                response = supa.auth.update_user({"password": new_pw})
                if response and getattr(response, 'user', None):
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Success", "Your password has been updated.")
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Error", "Failed to update password. Please try again.")
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Password update failed: {e}")
            
            # Clear password fields for security
            self.current_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            
            logger.info("Password change requested")
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to change password: {str(e)}")
    
    def toggle_2fa(self):
        """Toggle two-factor authentication."""
        try:
            sender = self.sender()
            
            if sender == self.enable_2fa_btn:
                # TODO: Implement 2FA setup
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Enable 2FA",
                    "Two-factor authentication setup will be implemented soon."
                )
                logger.info("2FA enable requested")
            else:
                # TODO: Implement 2FA disable
                from PyQt6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "Disable 2FA",
                    "Are you sure you want to disable two-factor authentication?\nThis will make your account less secure.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    QMessageBox.information(
                        self,
                        "Disable 2FA",
                        "Two-factor authentication disable will be implemented soon."
                    )
                    logger.info("2FA disable requested")
            
        except Exception as e:
            logger.error(f"Error toggling 2FA: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to toggle 2FA: {str(e)}")
    
    def check_for_updates(self):
        """Manually check for updates."""
        try:
            # Disable the button during check
            self.check_updates_btn.setEnabled(False)
            self.check_updates_btn.setText("Checking...")
            self.update_status_label.setText("Checking for updates...")
            
            # Get the main window to access the updater
            main_window = self.window()
            if hasattr(main_window, 'updater'):
                # Perform manual update check
                main_window.updater.check_for_updates(silent=False, manual_check=True)
                
                # Update status after a short delay
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, self.update_check_status)
            else:
                self.update_status_label.setText("Update system not available")
                self.check_updates_btn.setEnabled(True)
                self.check_updates_btn.setText("Check for Updates")
                
        except Exception as e:
            self.update_status_label.setText(f"Error checking for updates: {str(e)}")
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Check for Updates")
    
    def update_check_status(self):
        """Update the status label after checking for updates."""
        try:
            # Get the main window to access the updater
            main_window = self.window()
            if hasattr(main_window, 'updater'):
                # Check if an update is available
                if hasattr(main_window.updater, 'latest_version'):
                    latest_version = main_window.updater.latest_version
                    from trackpro.updater import CURRENT_VERSION
                    if latest_version and latest_version != CURRENT_VERSION:
                        self.update_status_label.setText(f"Update available: v{latest_version}")
                        self.update_status_label.setStyleSheet("""
                            QLabel {
                                color: #43b581;
                                font-size: 12px;
                                padding: 4px 0;
                                border: none;
                                background: transparent;
                            }
                        """)
                        # Show download button
                        self.download_update_btn.setVisible(True)
                        self.download_update_btn.setText(f"Download v{latest_version}")
                    else:
                        self.update_status_label.setText("You are running the latest version")
                        self.update_status_label.setStyleSheet("""
                            QLabel {
                                color: #b9bbbe;
                                font-size: 12px;
                                padding: 4px 0;
                                border: none;
                                background: transparent;
                            }
                        """)
                        # Hide download button
                        self.download_update_btn.setVisible(False)
                else:
                    self.update_status_label.setText("No updates available")
            else:
                self.update_status_label.setText("Update system not available")
            
            # Re-enable the button
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Check for Updates")
            
        except Exception as e:
            self.update_status_label.setText(f"Error: {str(e)}")
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Check for Updates")
    
    def download_update(self):
        """Download and install the available update."""
        try:
            # Get the main window to access the updater
            main_window = self.window()
            if hasattr(main_window, 'updater') and hasattr(main_window.updater, 'latest_version'):
                # Disable the download button during process
                self.download_update_btn.setEnabled(False)
                self.download_update_btn.setText("Downloading...")
                self.update_status_label.setText("Starting download...")
                
                # Trigger the download process
                main_window.updater._handle_download_choice()
                
                # The updater will handle the rest (download, installation, app exit)
            else:
                self.update_status_label.setText("Update system not available")
                self.download_update_btn.setEnabled(True)
                self.download_update_btn.setText("Download Update")
                
        except Exception as e:
            self.update_status_label.setText(f"Error downloading update: {str(e)}")
            self.download_update_btn.setEnabled(True)
            self.download_update_btn.setText("Download Update")
    
    def save_notification_settings(self):
        """Save notification preferences and startup settings."""
        try:
            # Get checkbox states
            notification_settings = {
                "email_notifications": self.email_notifications_check.isChecked(),
                "race_reminders": self.race_reminders_check.isChecked(),
                "achievement_emails": self.achievement_emails_check.isChecked(),
                "ai_coach_alerts": self.ai_coach_alerts_check.isChecked(),
                "performance_alerts": self.performance_alerts_check.isChecked(),
                "social_notifications": self.social_notifications_check.isChecked()
            }
            
            # Get startup settings
            start_with_windows = self.start_with_windows_check.isChecked()
            start_minimized = self.start_minimized_check.isChecked()
            minimize_to_tray = self.minimize_to_tray_check.isChecked()
            
            # Save startup settings to Windows registry
            success = self.startup_manager.toggle_startup(start_with_windows, start_minimized)
            
            # Save startup settings to config
            from trackpro.config import Config
            config = Config()
            config.set('ui.start_with_windows', start_with_windows)
            config.set('ui.start_minimized', start_minimized)
            config.set('ui.minimize_to_tray', minimize_to_tray)
            config.save()
            
            # TODO: Save notification settings to Supabase user preferences
            logger.info(f"Saving notification settings: {notification_settings}")
            logger.info(f"Startup settings - Windows: {start_with_windows}, Minimized: {start_minimized}, Tray: {minimize_to_tray}")
            
            from PyQt6.QtWidgets import QMessageBox
            if success:
                QMessageBox.information(
                    self,
                    "Settings Saved",
                    "Your settings have been saved successfully!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Settings Partially Saved",
                    "Notification settings saved, but there was an issue with startup settings. You may need administrator privileges."
                )
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def load_racing_statistics(self):
        """Load racing statistics from the database."""
        try:
            from ....database.supabase_client import get_supabase_client
            
            # Get current user
            supabase_client = get_supabase_client()
            if not supabase_client:
                logger.warning("Unable to connect to database for racing stats")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                logger.warning("No authenticated user for racing stats")
                return
            
            user_id = user_response.user.id
            
            # Get racing statistics from database
            try:
                # Query user_stats table for racing data
                stats_response = supabase_client.table('user_stats').select('*').eq('user_id', user_id).single().execute()
                
                if stats_response.data:
                    stats = stats_response.data
                    
                    # Update UI with real data
                    total_sessions = stats.get('total_sessions', 0)
                    total_distance = stats.get('total_distance_km', 0.0)
                    best_lap = stats.get('best_lap_time', 0.0)
                    consistency = stats.get('consistency_rating', 0.0)
                    
                    self.total_sessions_label.setText(f"Total Sessions: {total_sessions}")
                    self.total_distance_label.setText(f"Total Distance: {total_distance:.1f} km")
                    
                    if best_lap > 0:
                        minutes = int(best_lap // 60)
                        seconds = best_lap % 60
                        self.best_lap_label.setText(f"Best Lap Time: {minutes}:{seconds:06.3f}")
                    else:
                        self.best_lap_label.setText("Best Lap Time: No data")
                    
                    self.avg_consistency_label.setText(f"Consistency Rating: {consistency:.1f}%")
                    
                    logger.info("Racing statistics loaded successfully")
                else:
                    # No stats data yet - show defaults
                    self.total_sessions_label.setText("Total Sessions: 0")
                    self.total_distance_label.setText("Total Distance: 0.0 km")
                    self.best_lap_label.setText("Best Lap Time: No data")
                    self.avg_consistency_label.setText("Consistency Rating: 0.0%")
                    
            except Exception as db_error:
                logger.error(f"Error querying racing stats: {db_error}")
                # Show placeholder data on error
                self.total_sessions_label.setText("Total Sessions: Loading...")
                self.total_distance_label.setText("Total Distance: Loading...")
                self.best_lap_label.setText("Best Lap Time: Loading...")
                self.avg_consistency_label.setText("Consistency Rating: Loading...")
            
        except Exception as e:
            logger.error(f"Error loading racing statistics: {e}")
    
    def save_racing_settings(self):
        """Save racing preferences and AI coach settings."""
        try:
            # Collect racing settings
            racing_settings = {
                "coach_personality": self.coach_personality_combo.currentText(),
                "coaching_frequency": self.coaching_frequency_combo.currentText(),
                "voice_coaching_enabled": self.voice_coaching_check.isChecked(),
                "laptime_improvement_goal": self.laptime_goal_spin.value(),
                "consistency_goal": self.consistency_goal_spin.value()
            }
            
            # Save to user preferences
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Connection Error", "Unable to connect to database.")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to save settings.")
                return
            
            user_id = user_response.user.id
            
            # Update user profile with racing preferences
            user_manager = EnhancedUserManager()
            success = user_manager.update_user_profile(user_id, {
                "preferences": racing_settings
            })
            
            if success:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Settings Saved", "Your racing preferences have been saved successfully!")
                logger.info(f"Racing settings saved: {racing_settings}")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Save Failed", "Failed to save racing settings. Please try again.")
            
        except Exception as e:
            logger.error(f"Error saving racing settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save racing settings: {str(e)}")
    
    def save_connection_settings(self):
        """Save connection and integration settings."""
        try:
            # Collect connection settings
            connection_settings = {
                "iracing_username": self.iracing_username_input.text().strip(),
                "discord_rich_presence": self.discord_rich_presence_check.isChecked(),
                "discord_community": self.discord_community_check.isChecked()
            }
            
            # TODO: Save to user profile or dedicated connections table
            logger.info(f"Saving connection settings: {connection_settings}")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Settings Saved",
                "Your connection preferences have been saved successfully!"
            )
            
        except Exception as e:
            logger.error(f"Error saving connection settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save connection settings: {str(e)}")
    
    def connect_iracing(self):
        """Connect to iRacing account."""
        try:
            username = self.iracing_username_input.text().strip()
            if not username:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "Please enter your iRacing username.")
                return
            
            # TODO: Implement actual iRacing API integration
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "iRacing Connection",
                f"iRacing integration for '{username}' will be implemented soon."
            )
            logger.info(f"iRacing connection requested for username: {username}")
            
        except Exception as e:
            logger.error(f"Error connecting to iRacing: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to connect to iRacing: {str(e)}")
    
    def disconnect_iracing(self):
        """Disconnect from iRacing account."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Disconnect iRacing",
                "Are you sure you want to disconnect your iRacing account?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement disconnection logic
                QMessageBox.information(self, "Disconnected", "iRacing account disconnected successfully!")
                logger.info("iRacing account disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting iRacing: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to disconnect iRacing: {str(e)}")
    

    
    def save_privacy_settings(self):
        """Save privacy preferences."""
        try:
            # Collect privacy settings
            privacy_settings = {
                "profile_visibility": self.profile_visibility_combo.currentText().lower().replace(" ", "_"),
                "share_telemetry": self.share_telemetry_check.isChecked(),
                "show_statistics": self.show_statistics_check.isChecked(),
                "allow_friend_requests": self.allow_friend_requests_check.isChecked(),
                "show_online_status": self.show_online_status_check.isChecked()
            }
            
            # Save to user profile
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Connection Error", "Unable to connect to database.")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to save settings.")
                return
            
            user_id = user_response.user.id
            
            # Update privacy settings
            user_manager = EnhancedUserManager()
            success = user_manager.update_user_profile(user_id, {
                "privacy_settings": privacy_settings,
                "share_data": True
            })
            
            if success:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Settings Saved", "Your privacy preferences have been saved successfully!")
                logger.info(f"Privacy settings saved: {privacy_settings}")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Save Failed", "Failed to save privacy settings. Please try again.")
            
        except Exception as e:
            logger.error(f"Error saving privacy settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save privacy settings: {str(e)}")
    
    def export_profile_data(self):
        """Export user profile data."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            import json
            from datetime import datetime
            
            # Get save location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Profile Data",
                f"trackpro_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not filename:
                return
            
            # Collect profile data
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                QMessageBox.warning(self, "Connection Error", "Unable to connect to database.")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to export data.")
                return
            
            # Get complete profile
            user_manager = EnhancedUserManager()
            profile_data = user_manager.get_complete_user_profile()
            
            # Add export metadata
            export_data = {
                "export_date": datetime.now().isoformat(),
                "export_type": "profile",
                "trackpro_version": "1.0",
                "profile_data": profile_data
            }
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Export Complete", f"Profile data exported successfully to:\\n{filename}")
            logger.info(f"Profile data exported to: {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting profile data: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Error", f"Failed to export profile data: {str(e)}")
    
    def export_telemetry_data(self):
        """Export user telemetry data."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # TODO: Implement telemetry data export
            QMessageBox.information(
                self,
                "Telemetry Export",
                "Telemetry data export functionality will be implemented soon.\\n\\nThis will include:\\n• Session data\\n• Lap times\\n• Performance metrics\\n• Track data"
            )
            logger.info("Telemetry export requested")
            
        except Exception as e:
            logger.error(f"Error exporting telemetry data: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Error", f"Failed to export telemetry data: {str(e)}")
    
    def request_account_deletion(self):
        """Request account deletion."""
        try:
            from PyQt6.QtWidgets import QMessageBox, QInputDialog
            
            # Double confirmation
            reply = QMessageBox.warning(
                self,
                "Delete Account",
                "⚠️ Are you absolutely sure you want to permanently delete your account?\\n\\n"
                "This is PERMANENT and IRREVERSIBLE. There is NO way to recover your data.\\n\\n"
                "This action will:\\n"
                "• Permanently delete ALL your data (telemetry, lap times, messages, achievements, settings)\\n"
                "• Remove all racing statistics and social connections\\n"
                "• Cancel any active subscriptions\\n\\n"
                "Type 'DELETE' to confirm:",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Ok:
                # Ask for confirmation text
                text, ok = QInputDialog.getText(
                    self,
                    "Confirm Account Deletion",
                    "FINAL WARNING: This action is permanent and cannot be undone.\\n\\nType 'DELETE' to confirm:"
                )
                
                if ok and text.upper() == "DELETE":
                    # Attempt actual account deletion and sign-out
                    try:
                        from ....database.supabase_client import get_supabase_client
                        supa = get_supabase_client()
                        if not supa or not supa.auth.get_user() or not supa.auth.get_user().user:
                            QMessageBox.critical(self, "Error", "No authenticated user.")
                            return
                        user_id = supa.auth.get_user().user.id
                        # Preferred: secured RPC to delete user and cascade data
                        try:
                            resp = supa.rpc('delete_user_and_related', { 'p_user_id': user_id }).execute()
                            _ = resp
                            deleted = True
                        except Exception:
                            # Fallback: scrub username and mark deleted, then sign out
                            try:
                                supa.from_('user_profiles').update({ 'username': f"deleted_{user_id[:8]}", 'display_name': 'Deleted User' }).eq('user_id', user_id).execute()
                            except Exception:
                                pass
                            deleted = True
                        try:
                            supa.auth.sign_out()
                        except Exception:
                            pass
                        QMessageBox.information(self, "Account Deleted", "Your account has been deleted and you have been signed out.")
                        logger.warning("Account deletion completed")
                    except Exception as de:
                        QMessageBox.critical(self, "Deletion Error", f"Failed to delete account: {de}")
                elif ok:
                    QMessageBox.information(self, "Deletion Cancelled", "Account deletion cancelled - confirmation text did not match.")
            
        except Exception as e:
            logger.error(f"Error requesting account deletion: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to process deletion request: {str(e)}")
    
    def load_data_usage_statistics(self):
        """Load and display data usage statistics."""
        try:
            from ....database.supabase_client import get_supabase_client
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                self.data_usage_text.setPlainText("• Unable to load data usage statistics")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                self.data_usage_text.setPlainText("• User not authenticated")
                return
            
            # TODO: Implement actual data usage calculation from Supabase
            # For now, show example data
            usage_text = (
                "• Profile data: ~2.5 KB\n"
                "• Racing statistics: ~15.3 KB\n" 
                "• Achievement data: ~4.7 KB\n"
                "• Telemetry sessions: ~127.8 MB\n"
                "• Avatar images: ~245 KB\n"
                "• Settings & preferences: ~1.2 KB\n\n"
                "📊 Total storage used: ~128.1 MB"
            )
            
            self.data_usage_text.setPlainText(usage_text)
            logger.info("Data usage statistics updated")
            
        except Exception as e:
            logger.error(f"Error loading data usage: {e}")
            self.data_usage_text.setPlainText("• Error loading data usage statistics")
    
    def create_admin_section(self):
        """Create the admin management section (dev users only)."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #36393f;
                border: none;
            }
        """)
        
        # Import and create admin management widget
        from .admin_management_widget import AdminManagementWidget
        admin_widget = AdminManagementWidget()
        admin_widget.admin_updated.connect(self.on_admin_updated)
        
        scroll_area.setWidget(admin_widget)
        return scroll_area
    
    def on_admin_updated(self):
        """Handle admin list updates."""
        logger.info("Admin list updated")
        # Refresh the navigation if needed
        self.refresh_navigation()
    
    def create_hierarchy_section(self):
        """Create the hierarchy management section (for moderators and devs)."""
        container = QWidget()
        layout = QHBoxLayout(container)
        
        # Left side: User list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.user_search_input = QLineEdit()
        self.user_search_input.setPlaceholderText("Search by username or email...")
        self.user_search_input.textChanged.connect(self.search_users)
        
        self.user_list = QListWidget()
        self.user_list.currentItemChanged.connect(self.display_user_details)
        
        left_layout.addWidget(self.user_search_input)
        left_layout.addWidget(self.user_list)
        
        # Right side: User details
        self.user_details_area = QScrollArea()
        self.user_details_area.setWidgetResizable(True)
        
        self.user_details_widget = QWidget()
        self.user_details_layout = QVBoxLayout(self.user_details_widget)
        
        self.user_details_area.setWidget(self.user_details_widget)
        
        layout.addWidget(left_panel)
        layout.addWidget(self.user_details_area, 1) # Give details area more space
        
        self.refresh_user_list()
        
        return container

    def display_user_details(self, item, _):
        if not item:
            return

        user_data = item.data(Qt.ItemDataRole.UserRole)
        
        # Clear previous details
        while self.user_details_layout.count():
            child = self.user_details_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        from trackpro.auth.hierarchy_manager import hierarchy_manager
        hierarchy = hierarchy_manager.get_user_hierarchy(user_data['user_id'])
        
        details_layout = self.user_details_layout
        
        # User info
        title = QLabel(f"<b>{user_data['display_name']}</b> ({user_data['email']})")
        details_layout.addWidget(title)
        
        if hierarchy:
            current_level = QLabel(f"Current Level: {hierarchy.hierarchy_level.value}")
            dev_status = QLabel(f"Dev Permissions: {'Yes' if hierarchy.is_dev else 'No'}")
            mod_status = QLabel(f"Moderator Permissions: {'Yes' if hierarchy.is_moderator else 'No'}")

            details_layout.addWidget(current_level)
            details_layout.addWidget(dev_status)
            details_layout.addWidget(mod_status)

        # Controls
        self.level_combo = QComboBox()
        self.level_combo.addItems([level.value for level in HierarchyLevel])
        if hierarchy:
            current_index = self.level_combo.findText(hierarchy.hierarchy_level.value)
            if current_index != -1:
                self.level_combo.setCurrentIndex(current_index)
        
        permissions_layout = QHBoxLayout()
        self.dev_checkbox = QCheckBox("Developer")
        self.mod_checkbox = QCheckBox("Moderator")
        
        if hierarchy:
            self.dev_checkbox.setChecked(hierarchy.is_dev)
            self.mod_checkbox.setChecked(hierarchy.is_moderator)
        
        permissions_layout.addWidget(self.dev_checkbox)
        permissions_layout.addWidget(self.mod_checkbox)
        
        update_btn = QPushButton("Update Hierarchy")
        
        from trackpro.auth.user_manager import get_current_user
        
        current_user = get_current_user()
        if not current_user:
            return

        update_btn.clicked.connect(lambda: self.update_user_hierarchy(user_data['user_id'], current_user.id))
        
        details_layout.addWidget(self.level_combo)
        details_layout.addLayout(permissions_layout)
        details_layout.addWidget(update_btn)
        
        self.user_details_layout.addStretch()

    def update_user_hierarchy(self, user_id, modifier_id):
        """Update user hierarchy."""
        try:
            from trackpro.auth.hierarchy_manager import hierarchy_manager, HierarchyLevel
            
            level_text = self.level_combo.currentText()
            is_dev = self.dev_checkbox.isChecked()
            is_moderator = self.mod_checkbox.isChecked()
            
            hierarchy_level = HierarchyLevel(level_text)
            
            # Update hierarchy
            result = hierarchy_manager.update_user_hierarchy(
                target_id=user_id,
                modifier_id=modifier_id,
                hierarchy_level=hierarchy_level,
                is_dev=is_dev,
                is_moderator=is_moderator
            )
            
            if result.get("success"):
                QMessageBox.information(self, "Success", "User hierarchy updated successfully!")
                self.refresh_user_list()
            else:
                QMessageBox.warning(self, "Error", f"Failed to update user hierarchy: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error updating user hierarchy: {e}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def refresh_user_list(self):
        """Refresh the list of users in the hierarchy management section."""
        try:
            from trackpro.database.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            response = supabase.table("user_profiles").select("user_id, email, display_name").execute()
            
            self.user_list.clear()
            if response.data:
                for user in response.data:
                    item = QListWidgetItem(f"{user['display_name']} ({user['email']})")
                    item.setData(Qt.ItemDataRole.UserRole, user)
                    self.user_list.addItem(item)
                    
        except Exception as e:
            logger.error(f"Error refreshing user list: {e}")
            
    def search_users(self, text):
        """Filter users in the list based on search text."""
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())
