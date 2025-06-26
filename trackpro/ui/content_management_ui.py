"""
TrackPro Content Management UI Components
Racing-themed interface for sharing setups, media, and racing content
"""

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional, Any

# Import the community theme
from .community_ui import CommunityTheme

class ContentCard(QWidget):
    """Base content display card"""
    
    content_clicked = pyqtSignal(dict)
    download_requested = pyqtSignal(str)
    like_requested = pyqtSignal(str)
    share_requested = pyqtSignal(str)
    
    def __init__(self, content_data: Dict[str, Any], user_id: str, parent=None):
        super().__init__(parent)
        self.content_data = content_data
        self.user_id = user_id
        self.is_liked = self._check_if_liked()
        self.setup_ui()
        
    def _check_if_liked(self) -> bool:
        """Check if current user has liked this content"""
        likes = self.content_data.get('likes', [])
        return self.user_id in likes
        
    def setup_ui(self):
        """Setup the content card UI"""
        self.setFixedHeight(280)
        self.setObjectName("community-card")
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with content type and author
        header_layout = QHBoxLayout()
        
        # Content type icon
        content_type = self.content_data.get('content_type', 'setup')
        type_icons = {
            'setup': '⚙️',
            'image': '🖼️',
            'video': '🎥',
            'replay': '📹',
            'telemetry': '📊',
            'guide': '📖'
        }
        
        icon_label = QLabel(type_icons.get(content_type, '📄'))
        icon_label.setFont(QFont('Segoe UI Emoji', 20))
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Content info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        title_label = QLabel(self.content_data.get('title', 'Untitled'))
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        author_label = QLabel(f"by {self.content_data.get('author_username', 'Unknown')}")
        author_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        author_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(author_label)
        
        # Content category/tags
        category = self.content_data.get('category', '')
        if category:
            category_label = QLabel(category.title())
            category_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            category_label.setStyleSheet(f"""
                color: {CommunityTheme.COLORS['primary']};
                background-color: {CommunityTheme.COLORS['accent']};
                padding: 2px 8px;
                border-radius: 10px;
            """)
            category_label.setMaximumWidth(100)
            category_label.setAlignment(Qt.AlignCenter)
            
        header_layout.addWidget(icon_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        if category:
            header_layout.addWidget(category_label)
        
        # Description
        description = self.content_data.get('description', 'No description available.')
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(60)
        
        # Content details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        
        # Track and car info (if applicable)
        track_name = self.content_data.get('track_name')
        car_name = self.content_data.get('car_name')
        if track_name or car_name:
            track_car_text = []
            if track_name:
                track_car_text.append(f"Track: {track_name}")
            if car_name:
                track_car_text.append(f"Car: {car_name}")
            
            track_car_label = QLabel(f"🏎️ {' • '.join(track_car_text)}")
            track_car_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            track_car_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            details_layout.addWidget(track_car_label)
        
        # Upload date and file size
        created_at = self.content_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            time_str = created_at.strftime("%B %d, %Y")
            
            file_size = self.content_data.get('file_size', 0)
            size_str = self._format_file_size(file_size) if file_size else ""
            
            meta_text = f"📅 {time_str}"
            if size_str:
                meta_text += f" • 💾 {size_str}"
                
            meta_label = QLabel(meta_text)
            meta_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            meta_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            details_layout.addWidget(meta_label)
        
        # Stats (likes, downloads, rating)
        stats_layout = QHBoxLayout()
        
        like_count = len(self.content_data.get('likes', []))
        download_count = self.content_data.get('download_count', 0)
        rating = self.content_data.get('average_rating', 0)
        
        if like_count > 0:
            likes_label = QLabel(f"❤️ {like_count}")
            likes_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            likes_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            stats_layout.addWidget(likes_label)
            
        if download_count > 0:
            downloads_label = QLabel(f"⬇️ {download_count}")
            downloads_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            downloads_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            stats_layout.addWidget(downloads_label)
            
        if rating > 0:
            stars = "⭐" * int(rating)
            rating_label = QLabel(f"{stars} {rating:.1f}")
            rating_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            rating_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']};")
            stats_layout.addWidget(rating_label)
            
        stats_layout.addStretch()
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Like button
        like_button = QPushButton("❤️" if self.is_liked else "🤍")
        like_button.setFixedSize(32, 32)
        like_button.clicked.connect(lambda: self.like_requested.emit(self.content_data['id']))
        
        # Download button
        download_button = QPushButton("⬇️")
        download_button.setFixedSize(32, 32)
        download_button.clicked.connect(lambda: self.download_requested.emit(self.content_data['id']))
        
        # Share button
        share_button = QPushButton("📤")
        share_button.setFixedSize(32, 32)
        share_button.clicked.connect(lambda: self.share_requested.emit(self.content_data['id']))
        
        # View details button
        view_button = QPushButton("View Details")
        view_button.clicked.connect(lambda: self.content_clicked.emit(self.content_data))
        
        button_layout.addWidget(like_button)
        button_layout.addWidget(download_button)
        button_layout.addWidget(share_button)
        button_layout.addStretch()
        button_layout.addWidget(view_button)
        
        layout.addLayout(header_layout)
        layout.addWidget(desc_label)
        layout.addLayout(details_layout)
        layout.addLayout(stats_layout)
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
        
    def mousePressEvent(self, event):
        """Handle card click"""
        if event.button() == Qt.LeftButton:
            self.content_clicked.emit(self.content_data)

class ContentBrowserWidget(QWidget):
    """Widget for browsing and managing shared content"""
    
    def __init__(self, content_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.content_manager = content_manager
        self.user_id = user_id
        self.content_items = []
        self.setup_ui()
        self.load_content()
        
    def setup_ui(self):
        """Setup the content browser UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header with search and filters
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Content Library")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search content...")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self.filter_content)
        
        # Content type filter
        self.type_combo = QComboBox()
        self.type_combo.addItems(['All Types', 'Setups', 'Images', 'Videos', 'Replays', 'Telemetry', 'Guides'])
        self.type_combo.currentTextChanged.connect(self.filter_content)
        
        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItems(['All Categories', 'GT3', 'Formula', 'Oval', 'Rally', 'Endurance'])
        self.category_combo.currentTextChanged.connect(self.filter_content)
        
        # Sort options
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['Newest First', 'Oldest First', 'Most Liked', 'Most Downloaded', 'Highest Rated'])
        self.sort_combo.currentTextChanged.connect(self.sort_content)
        
        # Upload button
        upload_button = QPushButton("Upload Content")
        upload_button.clicked.connect(self.show_upload_dialog)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.sort_combo)
        header_layout.addWidget(self.category_combo)
        header_layout.addWidget(self.type_combo)
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(upload_button)
        
        # Filter tabs
        self.tab_widget = QTabWidget()
        
        # All content tab
        self.all_content_scroll = QScrollArea()
        self.all_content_scroll.setWidgetResizable(True)
        self.all_content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.all_content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.all_content_widget = QWidget()
        self.all_content_layout = QGridLayout(self.all_content_widget)
        self.all_content_layout.setAlignment(Qt.AlignTop)
        self.all_content_scroll.setWidget(self.all_content_widget)
        
        # My content tab
        self.my_content_scroll = QScrollArea()
        self.my_content_scroll.setWidgetResizable(True)
        self.my_content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.my_content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.my_content_widget = QWidget()
        self.my_content_layout = QGridLayout(self.my_content_widget)
        self.my_content_layout.setAlignment(Qt.AlignTop)
        self.my_content_scroll.setWidget(self.my_content_widget)
        
        # Liked content tab
        self.liked_content_scroll = QScrollArea()
        self.liked_content_scroll.setWidgetResizable(True)
        self.liked_content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.liked_content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.liked_content_widget = QWidget()
        self.liked_content_layout = QGridLayout(self.liked_content_widget)
        self.liked_content_layout.setAlignment(Qt.AlignTop)
        self.liked_content_scroll.setWidget(self.liked_content_widget)
        
        self.tab_widget.addTab(self.all_content_scroll, "All Content")
        self.tab_widget.addTab(self.my_content_scroll, "My Content")
        self.tab_widget.addTab(self.liked_content_scroll, "Liked")
        
        layout.addLayout(header_layout)
        layout.addWidget(self.tab_widget)
        
    def load_content(self):
        """Load content from the content manager"""
        try:
            # Get all content
            all_content_result = self.content_manager.search_content()
            if all_content_result['success']:
                self.content_items = all_content_result['content']
                self.display_content()
            else:
                self.show_error("Failed to load content")
                
        except Exception as e:
            self.show_error(f"Error loading content: {str(e)}")
            
    def display_content(self):
        """Display content in grid layout across tabs"""
        # Clear existing widgets
        self.clear_layout(self.all_content_layout)
        self.clear_layout(self.my_content_layout)
        self.clear_layout(self.liked_content_layout)
        
        all_content = []
        my_content = []
        liked_content = []
        
        for content in self.content_items:
            content_card = ContentCard(content, self.user_id)
            content_card.content_clicked.connect(self.show_content_details)
            content_card.download_requested.connect(self.download_content)
            content_card.like_requested.connect(self.toggle_like_content)
            content_card.share_requested.connect(self.share_content)
            
            all_content.append(content_card)
            
            # Check if user created this content
            if content.get('created_by') == self.user_id:
                my_content_card = ContentCard(content, self.user_id)
                my_content_card.content_clicked.connect(self.show_content_details)
                my_content_card.download_requested.connect(self.download_content)
                my_content_card.like_requested.connect(self.toggle_like_content)
                my_content_card.share_requested.connect(self.share_content)
                my_content.append(my_content_card)
                
            # Check if user liked this content
            if content_card.is_liked:
                liked_content_card = ContentCard(content, self.user_id)
                liked_content_card.content_clicked.connect(self.show_content_details)
                liked_content_card.download_requested.connect(self.download_content)
                liked_content_card.like_requested.connect(self.toggle_like_content)
                liked_content_card.share_requested.connect(self.share_content)
                liked_content.append(liked_content_card)
        
        # Add cards to grid layouts (3 columns)
        for i, card in enumerate(all_content):
            row = i // 3
            col = i % 3
            self.all_content_layout.addWidget(card, row, col)
            
        for i, card in enumerate(my_content):
            row = i // 3
            col = i % 3
            self.my_content_layout.addWidget(card, row, col)
            
        for i, card in enumerate(liked_content):
            row = i // 3
            col = i % 3
            self.liked_content_layout.addWidget(card, row, col)
            
        # Update tab titles with counts
        self.tab_widget.setTabText(0, f"All Content ({len(all_content)})")
        self.tab_widget.setTabText(1, f"My Content ({len(my_content)})")
        self.tab_widget.setTabText(2, f"Liked ({len(liked_content)})")
        
    def filter_content(self):
        """Filter content based on search input, type, and category"""
        search_text = self.search_input.text().lower()
        selected_type = self.type_combo.currentText()
        selected_category = self.category_combo.currentText()
        
        # Map display names to internal types
        type_mapping = {
            'All Types': '',
            'Setups': 'setup',
            'Images': 'image',
            'Videos': 'video',
            'Replays': 'replay',
            'Telemetry': 'telemetry',
            'Guides': 'guide'
        }
        
        filter_type = type_mapping.get(selected_type, '')
        
        for i in range(self.all_content_layout.count()):
            widget = self.all_content_layout.itemAt(i).widget()
            if isinstance(widget, ContentCard):
                content_title = widget.content_data.get('title', '').lower()
                content_desc = widget.content_data.get('description', '').lower()
                content_type = widget.content_data.get('content_type', '')
                content_category = widget.content_data.get('category', '')
                
                text_match = search_text in content_title or search_text in content_desc
                type_match = (selected_type == 'All Types' or filter_type == content_type)
                category_match = (selected_category == 'All Categories' or 
                                selected_category == content_category)
                
                visible = text_match and type_match and category_match
                widget.setVisible(visible)
                
    def sort_content(self):
        """Sort content based on selected criteria"""
        sort_option = self.sort_combo.currentText()
        
        if sort_option == 'Newest First':
            self.content_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_option == 'Oldest First':
            self.content_items.sort(key=lambda x: x.get('created_at', ''))
        elif sort_option == 'Most Liked':
            self.content_items.sort(key=lambda x: len(x.get('likes', [])), reverse=True)
        elif sort_option == 'Most Downloaded':
            self.content_items.sort(key=lambda x: x.get('download_count', 0), reverse=True)
        elif sort_option == 'Highest Rated':
            self.content_items.sort(key=lambda x: x.get('average_rating', 0), reverse=True)
            
        self.display_content()
        
    def clear_layout(self, layout):
        """Clear all widgets from a layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def show_upload_dialog(self):
        """Show dialog to upload new content"""
        dialog = UploadContentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            content_data = dialog.get_content_data()
            self.upload_content(content_data)
            
    def upload_content(self, content_data: Dict[str, Any]):
        """Upload new content"""
        try:
            result = self.content_manager.upload_content(
                title=content_data['title'],
                description=content_data['description'],
                content_type=content_data['content_type'],
                category=content_data['category'],
                file_path=content_data['file_path'],
                track_name=content_data.get('track_name'),
                car_name=content_data.get('car_name'),
                tags=content_data.get('tags', []),
                privacy_level=content_data.get('privacy_level', 'public')
            )
            
            if result['success']:
                self.show_success("Content uploaded successfully!")
                self.load_content()  # Refresh the list
            else:
                self.show_error(f"Failed to upload content: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error uploading content: {str(e)}")
            
    def download_content(self, content_id: str):
        """Download content"""
        try:
            result = self.content_manager.download_content(content_id)
            if result['success']:
                self.show_success("Content downloaded successfully!")
                # Update download count
                self.load_content()
            else:
                self.show_error(f"Failed to download content: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error downloading content: {str(e)}")
            
    def toggle_like_content(self, content_id: str):
        """Toggle like status for content"""
        try:
            result = self.content_manager.toggle_like_content(content_id)
            if result['success']:
                # Refresh to update like status
                self.load_content()
            else:
                self.show_error(f"Failed to update like status: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error updating like status: {str(e)}")
            
    def share_content(self, content_id: str):
        """Share content"""
        # Find the content item
        content_item = next((item for item in self.content_items if item['id'] == content_id), None)
        if content_item:
            dialog = ShareContentDialog(content_item, self)
            dialog.exec_()
            
    def show_content_details(self, content_data: Dict[str, Any]):
        """Show detailed content information"""
        dialog = ContentDetailsDialog(content_data, self.content_manager, self.user_id, self)
        dialog.exec_()
        
    def show_success(self, message: str):
        """Show success message"""
        QMessageBox.information(self, "Success", message)
        
    def show_error(self, message: str):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)

class UploadContentDialog(QDialog):
    """Dialog for uploading new content"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upload Content")
        self.setFixedSize(500, 700)
        self.selected_file_path = ""
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the upload dialog UI"""
        layout = QVBoxLayout(self)
        
        # Content title
        layout.addWidget(QLabel("Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter content title...")
        layout.addWidget(self.title_input)
        
        # Content type
        layout.addWidget(QLabel("Content Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['setup', 'image', 'video', 'replay', 'telemetry', 'guide'])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Category
        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(['GT3', 'Formula', 'Oval', 'Rally', 'Endurance', 'Other'])
        layout.addWidget(self.category_combo)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe your content...")
        self.description_input.setMaximumHeight(100)
        layout.addWidget(self.description_input)
        
        # File selection
        file_layout = QHBoxLayout()
        layout.addWidget(QLabel("File:"))
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet(f"""
            QLabel {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px dashed {CommunityTheme.COLORS['border']};
                border-radius: 6px;
                padding: 20px;
                text-align: center;
                color: {CommunityTheme.COLORS['text_secondary']};
            }}
        """)
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setMinimumHeight(80)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(browse_button)
        layout.addLayout(file_layout)
        
        # Track name (optional)
        layout.addWidget(QLabel("Track Name (optional):"))
        self.track_input = QLineEdit()
        self.track_input.setPlaceholderText("Enter track name...")
        layout.addWidget(self.track_input)
        
        # Car name (optional)
        layout.addWidget(QLabel("Car Name (optional):"))
        self.car_input = QLineEdit()
        self.car_input.setPlaceholderText("Enter car name...")
        layout.addWidget(self.car_input)
        
        # Tags
        layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g., fast, stable, wet weather...")
        layout.addWidget(self.tags_input)
        
        # Privacy level
        layout.addWidget(QLabel("Privacy Level:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(['public', 'friends', 'private'])
        layout.addWidget(self.privacy_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        upload_button = QPushButton("Upload")
        upload_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(upload_button)
        
        layout.addLayout(button_layout)
        
    def on_type_changed(self):
        """Handle content type change"""
        content_type = self.type_combo.currentText()
        
        # Update file label based on content type
        type_descriptions = {
            'setup': 'Select a car setup file (.sto, .json, etc.)',
            'image': 'Select an image file (.jpg, .png, .gif)',
            'video': 'Select a video file (.mp4, .avi, .mov)',
            'replay': 'Select a replay file (.rpy, .vcr, etc.)',
            'telemetry': 'Select a telemetry file (.csv, .json, etc.)',
            'guide': 'Select a guide file (.pdf, .txt, .md)'
        }
        
        if not self.selected_file_path:
            self.file_label.setText(type_descriptions.get(content_type, 'Select a file'))
        
    def browse_file(self):
        """Browse for file to upload"""
        content_type = self.type_combo.currentText()
        
        # Define file filters based on content type
        filters = {
            'setup': "Setup Files (*.sto *.json *.txt);;All Files (*)",
            'image': "Image Files (*.jpg *.jpeg *.png *.gif *.bmp);;All Files (*)",
            'video': "Video Files (*.mp4 *.avi *.mov *.wmv *.mkv);;All Files (*)",
            'replay': "Replay Files (*.rpy *.vcr *.rec);;All Files (*)",
            'telemetry': "Telemetry Files (*.csv *.json *.txt);;All Files (*)",
            'guide': "Guide Files (*.pdf *.txt *.md *.doc *.docx);;All Files (*)"
        }
        
        file_filter = filters.get(content_type, "All Files (*)")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {content_type.title()} File", "", file_filter
        )
        
        if file_path:
            self.selected_file_path = file_path
            file_name = os.path.basename(file_path)
            self.file_label.setText(f"Selected: {file_name}")
            
            # Auto-fill title if empty
            if not self.title_input.text():
                name_without_ext = os.path.splitext(file_name)[0]
                self.title_input.setText(name_without_ext)
                
    def get_content_data(self) -> Dict[str, Any]:
        """Get the content data from the form"""
        tags = []
        if self.tags_input.text():
            tags = [tag.strip() for tag in self.tags_input.text().split(',') if tag.strip()]
            
        data = {
            'title': self.title_input.text(),
            'description': self.description_input.toPlainText(),
            'content_type': self.type_combo.currentText(),
            'category': self.category_combo.currentText(),
            'file_path': self.selected_file_path,
            'privacy_level': self.privacy_combo.currentText(),
            'tags': tags
        }
        
        # Optional fields
        if self.track_input.text():
            data['track_name'] = self.track_input.text()
            
        if self.car_input.text():
            data['car_name'] = self.car_input.text()
            
        return data

class ShareContentDialog(QDialog):
    """Dialog for sharing content"""
    
    def __init__(self, content_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.content_data = content_data
        self.setWindowTitle("Share Content")
        self.setFixedSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the share dialog UI"""
        layout = QVBoxLayout(self)
        
        # Content info
        title_label = QLabel(f"Share: {self.content_data.get('title', 'Unknown')}")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        layout.addWidget(title_label)
        
        # Share options
        layout.addWidget(QLabel("Share via:"))
        
        # Copy link button
        copy_link_button = QPushButton("📋 Copy Link")
        copy_link_button.clicked.connect(self.copy_link)
        layout.addWidget(copy_link_button)
        
        # Share to activity feed
        share_feed_button = QPushButton("📢 Share to Activity Feed")
        share_feed_button.clicked.connect(self.share_to_feed)
        layout.addWidget(share_feed_button)
        
        # Share to team/club (if member)
        share_team_button = QPushButton("👥 Share to Team/Club")
        share_team_button.clicked.connect(self.share_to_team)
        layout.addWidget(share_team_button)
        
        layout.addStretch()
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
    def copy_link(self):
        """Copy content link to clipboard"""
        # Generate a shareable link
        content_id = self.content_data.get('id', '')
        link = f"trackpro://content/{content_id}"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(link)
        
        QMessageBox.information(self, "Link Copied", "Content link copied to clipboard!")
        
    def share_to_feed(self):
        """Share content to activity feed"""
        QMessageBox.information(self, "Shared", "Content shared to your activity feed!")
        self.accept()
        
    def share_to_team(self):
        """Share content to team or club"""
        QMessageBox.information(self, "Shared", "Content shared to your team/club!")
        self.accept()

class ContentDetailsDialog(QDialog):
    """Dialog showing detailed content information"""
    
    def __init__(self, content_data: Dict[str, Any], content_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.content_data = content_data
        self.content_manager = content_manager
        self.user_id = user_id
        self.setWindowTitle(f"Content: {content_data.get('title', 'Unknown')}")
        self.setFixedSize(700, 600)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the content details dialog UI"""
        layout = QVBoxLayout(self)
        
        # Content header
        header_layout = QHBoxLayout()
        
        # Content type icon
        content_type = self.content_data.get('content_type', 'setup')
        type_icons = {
            'setup': '⚙️',
            'image': '🖼️',
            'video': '🎥',
            'replay': '📹',
            'telemetry': '📊',
            'guide': '📖'
        }
        
        icon_label = QLabel(type_icons.get(content_type, '📄'))
        icon_label.setFont(QFont('Segoe UI Emoji', 32))
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Content info
        info_layout = QVBoxLayout()
        
        title_label = QLabel(self.content_data.get('title', 'Unknown Content'))
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        info_layout.addWidget(title_label)
        
        author_label = QLabel(f"by {self.content_data.get('author_username', 'Unknown')}")
        author_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        author_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        info_layout.addWidget(author_label)
        
        # Category and type
        meta_text = f"{content_type.title()}"
        category = self.content_data.get('category')
        if category:
            meta_text += f" • {category}"
            
        meta_label = QLabel(meta_text)
        meta_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        meta_label.setStyleSheet(f"color: {CommunityTheme.COLORS['primary']};")
        info_layout.addWidget(meta_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Description
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        
        desc_label = QLabel(self.content_data.get('description', 'No description available.'))
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        desc_layout.addWidget(desc_label)
        
        # Details
        details_group = QGroupBox("Details")
        details_layout = QFormLayout(details_group)
        
        # Track and car info
        track_name = self.content_data.get('track_name')
        if track_name:
            details_layout.addRow("Track:", QLabel(track_name))
            
        car_name = self.content_data.get('car_name')
        if car_name:
            details_layout.addRow("Car:", QLabel(car_name))
            
        # Upload date
        created_at = self.content_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = created_at.strftime("%B %d, %Y at %I:%M %p")
            details_layout.addRow("Uploaded:", QLabel(date_str))
            
        # File size
        file_size = self.content_data.get('file_size', 0)
        if file_size:
            size_str = self._format_file_size(file_size)
            details_layout.addRow("File Size:", QLabel(size_str))
            
        # Tags
        tags = self.content_data.get('tags', [])
        if tags:
            tags_str = ", ".join(tags)
            details_layout.addRow("Tags:", QLabel(tags_str))
            
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QFormLayout(stats_group)
        
        like_count = len(self.content_data.get('likes', []))
        stats_layout.addRow("Likes:", QLabel(str(like_count)))
        
        download_count = self.content_data.get('download_count', 0)
        stats_layout.addRow("Downloads:", QLabel(str(download_count)))
        
        rating = self.content_data.get('average_rating', 0)
        if rating > 0:
            stars = "⭐" * int(rating)
            rating_str = f"{stars} {rating:.1f}/5"
            stats_layout.addRow("Rating:", QLabel(rating_str))
            
        # Action buttons
        button_layout = QHBoxLayout()
        
        download_button = QPushButton("⬇️ Download")
        download_button.clicked.connect(self.download_content)
        
        like_button = QPushButton("❤️ Like")
        like_button.clicked.connect(self.toggle_like)
        
        rate_button = QPushButton("⭐ Rate")
        rate_button.clicked.connect(self.rate_content)
        
        share_button = QPushButton("📤 Share")
        share_button.clicked.connect(self.share_content)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(download_button)
        button_layout.addWidget(like_button)
        button_layout.addWidget(rate_button)
        button_layout.addWidget(share_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(header_layout)
        layout.addWidget(desc_group)
        layout.addWidget(details_group)
        layout.addWidget(stats_group)
        layout.addLayout(button_layout)
        
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
        
    def download_content(self):
        """Download the content"""
        try:
            result = self.content_manager.download_content(self.content_data['id'])
            if result['success']:
                QMessageBox.information(self, "Success", "Content downloaded successfully!")
            else:
                QMessageBox.critical(self, "Error", f"Failed to download: {result.get('error', 'Unknown error')}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error downloading content: {str(e)}")
            
    def toggle_like(self):
        """Toggle like status"""
        try:
            result = self.content_manager.toggle_like_content(self.content_data['id'])
            if result['success']:
                QMessageBox.information(self, "Success", "Like status updated!")
            else:
                QMessageBox.critical(self, "Error", f"Failed to update like: {result.get('error', 'Unknown error')}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating like: {str(e)}")
            
    def rate_content(self):
        """Rate the content"""
        rating, ok = QInputDialog.getInt(
            self, "Rate Content", 
            "Rate this content (1-5 stars):", 
            value=5, min=1, max=5
        )
        
        if ok:
            try:
                result = self.content_manager.rate_content(self.content_data['id'], rating)
                if result['success']:
                    QMessageBox.information(self, "Success", "Rating submitted!")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to rate: {result.get('error', 'Unknown error')}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error rating content: {str(e)}")
                
    def share_content(self):
        """Share the content"""
        dialog = ShareContentDialog(self.content_data, self)
        dialog.exec_()

class ContentManagementMainWidget(QWidget):
    """Main content management interface"""
    
    def __init__(self, content_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.content_manager = content_manager
        self.user_id = user_id
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main content management interface"""
        # Apply theme
        self.setStyleSheet(CommunityTheme.get_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Content Management")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_primary']};
            font-size: 24px;
            font-weight: bold;
        """)
        
        # Quick stats
        stats_layout = QHBoxLayout()
        
        # Placeholder stats - these would be loaded from the content manager
        stats_data = [
            ("Setups", "156"),
            ("Images", "89"),
            ("Videos", "23"),
            ("Downloads", "2.1K")
        ]
        
        for stat_name, stat_value in stats_data:
            stat_widget = QWidget()
            stat_widget.setFixedSize(100, 60)
            stat_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {CommunityTheme.COLORS['surface']};
                    border: 1px solid {CommunityTheme.COLORS['border']};
                    border-radius: 8px;
                }}
            """)
            
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(8, 8, 8, 8)
            stat_layout.setSpacing(2)
            
            value_label = QLabel(stat_value)
            value_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
            value_label.setStyleSheet(f"color: {CommunityTheme.COLORS['primary']};")
            value_label.setAlignment(Qt.AlignCenter)
            
            name_label = QLabel(stat_name)
            name_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            name_label.setAlignment(Qt.AlignCenter)
            
            stat_layout.addWidget(value_label)
            stat_layout.addWidget(name_label)
            
            stats_layout.addWidget(stat_widget)
            
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addLayout(stats_layout)
        
        # Main content browser
        self.content_browser = ContentBrowserWidget(self.content_manager, self.user_id)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.content_browser)

if __name__ == "__main__":
    # Test the content management UI components
    app = QApplication(sys.argv)
    
    # Mock content manager for testing
    class MockContentManager:
        def search_content(self):
            return {
                'success': True,
                'content': [
                    {
                        'id': '1',
                        'title': 'GT3 Spa Setup',
                        'description': 'Fast and stable setup for Spa-Francorchamps',
                        'content_type': 'setup',
                        'category': 'GT3',
                        'author_username': 'SpeedDemon',
                        'created_by': 'user123',
                        'track_name': 'Spa-Francorchamps',
                        'car_name': 'McLaren 720S GT3',
                        'created_at': datetime.now().isoformat(),
                        'file_size': 2048,
                        'likes': ['user456'],
                        'download_count': 42,
                        'average_rating': 4.5,
                        'tags': ['fast', 'stable', 'wet']
                    }
                ]
            }
        
        def upload_content(self, **kwargs):
            return {'success': True}
        
        def download_content(self, content_id):
            return {'success': True}
        
        def toggle_like_content(self, content_id):
            return {'success': True}
        
        def rate_content(self, content_id, rating):
            return {'success': True}
    
    mock_manager = MockContentManager()
    
    # Create and show the main content management widget
    content_widget = ContentManagementMainWidget(mock_manager, 'test_user')
    content_widget.show()
    
    sys.exit(app.exec_()) 