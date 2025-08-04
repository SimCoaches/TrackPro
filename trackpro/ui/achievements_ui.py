"""Achievements UI Components for TrackPro."""

import os
import sys
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QComboBox, QCheckBox, QGroupBox, QFormLayout, QScrollArea,
    QFrame, QSizePolicy, QMessageBox, QDialog, QTabWidget, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor
from .social_ui import SocialTheme
from trackpro.social import achievements_manager, reputation_manager

logger = logging.getLogger(__name__)

class AchievementCard(QFrame):
    """Individual achievement display card."""
    
    def __init__(self, achievement_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.achievement_data = achievement_data
        self.init_ui()
    
    def init_ui(self):
        """Initialize the achievement card UI."""
        self.setFixedSize(280, 160)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SocialTheme.COLORS['surface']};
                border: 2px solid {self._get_rarity_color()};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header with icon and rarity
        header_layout = QHBoxLayout()
        
        # Achievement icon
        icon_label = QLabel(self._get_achievement_icon())
        icon_label.setFont(QFont('Segoe UI', 24))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Rarity badge
        rarity = self.achievement_data.get('rarity', 'common')
        rarity_label = QLabel(rarity.upper())
        rarity_label.setFont(SocialTheme.FONTS['caption'])
        rarity_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self._get_rarity_color()};
                color: white;
                padding: 2px 8px;
                border-radius: 10px;
                font-weight: bold;
            }}
        """)
        rarity_label.setFixedHeight(20)
        
        header_layout.addWidget(icon_label)
        header_layout.addStretch()
        header_layout.addWidget(rarity_label)
        
        # Achievement name
        name_label = QLabel(self.achievement_data.get('name', 'Unknown Achievement'))
        name_label.setFont(SocialTheme.FONTS['subheading'])
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(40)
        
        # Description
        desc_label = QLabel(self.achievement_data.get('description', 'No description'))
        desc_label.setFont(SocialTheme.FONTS['caption'])
        desc_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        
        # Progress or unlock status
        if self.achievement_data.get('is_unlocked', False):
            unlock_date = self.achievement_data.get('unlocked_at')
            if unlock_date:
                date_obj = datetime.fromisoformat(unlock_date.replace('Z', '+00:00'))
                status_text = f"🏆 Unlocked {date_obj.strftime('%b %d, %Y')}"
            else:
                status_text = "🏆 Unlocked"
            
            status_label = QLabel(status_text)
            status_label.setFont(SocialTheme.FONTS['caption'])
            status_label.setStyleSheet(f"color: {SocialTheme.COLORS['success']};")
        else:
            # Show progress if available
            progress = self.achievement_data.get('user_progress', {})
            if progress:
                status_label = self._create_progress_widget(progress)
            else:
                status_label = QLabel("🔒 Locked")
                status_label.setFont(SocialTheme.FONTS['caption'])
                status_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        layout.addLayout(header_layout)
        layout.addWidget(name_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(status_label)
    
    def _get_rarity_color(self) -> str:
        """Get color based on achievement rarity."""
        rarity_colors = {
            'common': '#6B7280',
            'rare': '#3B82F6',
            'epic': '#8B5CF6',
            'legendary': '#F59E0B'
        }
        rarity = self.achievement_data.get('rarity', 'common')
        return rarity_colors.get(rarity, rarity_colors['common'])
    
    def _get_achievement_icon(self) -> str:
        """Get icon based on achievement category."""
        category_icons = {
            'racing': '🏁',
            'social': '👥',
            'collection': '📚',
            'milestone': '🎯',
            'special': '⭐'
        }
        category = self.achievement_data.get('category', 'racing')
        return category_icons.get(category, '🏆')
    
    def _create_progress_widget(self, progress: Dict[str, Any]) -> QWidget:
        """Create progress display widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress text
        progress_text = "In Progress"
        progress_label = QLabel(progress_text)
        progress_label.setFont(SocialTheme.FONTS['caption'])
        progress_label.setStyleSheet(f"color: {SocialTheme.COLORS['warning']};")
        
        layout.addWidget(progress_label)
        
        return widget

class AchievementsWidget(QWidget):
    """Main achievements display widget."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.achievements_data = []
        self.init_ui()
        self.load_achievements()
    
    def init_ui(self):
        """Initialize the achievements UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Achievements")
        title_label.setFont(SocialTheme.FONTS['heading'])
        
        # Stats
        self.stats_label = QLabel("Loading...")
        self.stats_label.setFont(SocialTheme.FONTS['body'])
        self.stats_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)
        
        # Filter tabs
        self.filter_tabs = QTabWidget()
        
        # All achievements
        self.all_tab = QScrollArea()
        self.all_widget = QWidget()
        self.all_layout = QGridLayout(self.all_widget)
        self.all_tab.setWidget(self.all_widget)
        self.all_tab.setWidgetResizable(True)
        
        # Unlocked achievements
        self.unlocked_tab = QScrollArea()
        self.unlocked_widget = QWidget()
        self.unlocked_layout = QGridLayout(self.unlocked_widget)
        self.unlocked_tab.setWidget(self.unlocked_widget)
        self.unlocked_tab.setWidgetResizable(True)
        
        # Showcased achievements
        self.showcased_tab = QScrollArea()
        self.showcased_widget = QWidget()
        self.showcased_layout = QGridLayout(self.showcased_widget)
        self.showcased_tab.setWidget(self.showcased_widget)
        self.showcased_tab.setWidgetResizable(True)
        
        self.filter_tabs.addTab(self.all_tab, "All")
        self.filter_tabs.addTab(self.unlocked_tab, "Unlocked")
        self.filter_tabs.addTab(self.showcased_tab, "Showcased")
        self.filter_tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.filter_tabs)
    
    def load_achievements(self):
        """Load user achievements."""
        try:
            self.achievements_data = achievements_manager.get_user_achievements(self.current_user_id)
            self.update_stats()
            self.populate_achievements()
        except Exception as e:
            logger.error(f"Error loading achievements: {e}")
    
    def update_stats(self):
        """Update achievement statistics."""
        total_achievements = len(self.achievements_data)
        unlocked_achievements = len([a for a in self.achievements_data if a.get('is_unlocked', False)])
        
        self.stats_label.setText(f"{unlocked_achievements}/{total_achievements} Unlocked")
    
    def populate_achievements(self):
        """Populate achievement displays."""
        current_tab = self.filter_tabs.currentIndex()
        
        if current_tab == 0:  # All
            self.populate_tab(self.achievements_data, self.all_layout)
        elif current_tab == 1:  # Unlocked
            unlocked = [a for a in self.achievements_data if a.get('is_unlocked', False)]
            self.populate_tab(unlocked, self.unlocked_layout)
        elif current_tab == 2:  # Showcased
            try:
                showcased = achievements_manager.get_showcased_achievements(self.current_user_id)
                self.populate_tab(showcased, self.showcased_layout)
            except Exception as e:
                logger.error(f"Error loading showcased achievements: {e}")
    
    def populate_tab(self, achievements: List[Dict[str, Any]], layout: QGridLayout):
        """Populate a specific tab with achievements."""
        # Clear existing items
        for i in reversed(range(layout.count())):
            child = layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add achievements in grid
        row, col = 0, 0
        max_cols = 3
        
        for achievement in achievements:
            card = AchievementCard(achievement)
            layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Add stretch to fill remaining space
        layout.setRowStretch(row + 1, 1)
    
    def on_tab_changed(self, index):
        """Handle tab change."""
        self.populate_achievements()

class XPProgressWidget(QFrame):
    """XP and level progress display widget."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_xp_data()
    
    def init_ui(self):
        """Initialize the XP progress UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SocialTheme.COLORS['surface']};
                border: 1px solid {SocialTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Experience & Level")
        title_label.setFont(SocialTheme.FONTS['subheading'])
        
        self.level_label = QLabel("Level 1")
        self.level_label.setFont(SocialTheme.FONTS['heading'])
        self.level_label.setStyleSheet(f"color: {SocialTheme.COLORS['accent']};")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.level_label)
        
        # XP Progress bar
        self.xp_progress = QProgressBar()
        self.xp_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {SocialTheme.COLORS['border']};
                border-radius: 8px;
                text-align: center;
                background-color: {SocialTheme.COLORS['background']};
                height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: {SocialTheme.COLORS['accent']};
                border-radius: 6px;
            }}
        """)
        
        self.xp_label = QLabel("0 / 1000 XP")
        self.xp_label.setFont(SocialTheme.FONTS['caption'])
        self.xp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.xp_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        # XP Categories
        categories_layout = QHBoxLayout()
        self.category_labels = {}
        
        categories = [
            ('Racing', 'racing_xp', '🏁'),
            ('Social', 'social_xp', '👥'),
            ('Learning', 'learning_xp', '📚'),
            ('Coaching', 'coaching_xp', '🎓')
        ]
        
        for name, key, icon in categories:
            category_widget = QVBoxLayout()
            
            icon_label = QLabel(icon)
            icon_label.setFont(QFont('Segoe UI', 16))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            name_label = QLabel(name)
            name_label.setFont(SocialTheme.FONTS['caption'])
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            xp_label = QLabel("0 XP")
            xp_label.setFont(SocialTheme.FONTS['caption'])
            xp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            xp_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
            
            category_widget.addWidget(icon_label)
            category_widget.addWidget(name_label)
            category_widget.addWidget(xp_label)
            
            categories_layout.addLayout(category_widget)
            self.category_labels[key] = xp_label
        
        layout.addLayout(header_layout)
        layout.addWidget(self.xp_progress)
        layout.addWidget(self.xp_label)
        layout.addLayout(categories_layout)
    
    def load_xp_data(self):
        """Load and display XP data."""
        try:
            from trackpro.social import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(self.current_user_id)
            
            if user_profile:
                level = user_profile.get('level', 1)
                total_xp = user_profile.get('total_xp', 0)
                
                # Calculate XP for current level
                current_level_xp = self._calculate_level_xp(level)
                next_level_xp = self._calculate_level_xp(level + 1)
                progress_xp = total_xp - current_level_xp
                needed_xp = next_level_xp - current_level_xp
                
                # Update displays
                self.level_label.setText(f"Level {level}")
                self.xp_label.setText(f"{progress_xp:,} / {needed_xp:,} XP")
                
                progress_percent = int((progress_xp / needed_xp) * 100) if needed_xp > 0 else 100
                self.xp_progress.setValue(progress_percent)
                
                # Update category XP
                categories = ['racing_xp', 'social_xp', 'learning_xp', 'coaching_xp']
                for category in categories:
                    xp_value = user_profile.get(category, 0)
                    if category in self.category_labels:
                        self.category_labels[category].setText(f"{xp_value:,} XP")
                        
        except Exception as e:
            logger.error(f"Error loading XP data: {e}")
    
    def _calculate_level_xp(self, level: int) -> int:
        """Calculate total XP needed for a specific level."""
        # Simple formula: XP = (level - 1)^2 * 1000
        return max(0, (level - 1) ** 2 * 1000)

class StreaksWidget(QFrame):
    """User streaks display widget."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_streaks()
    
    def init_ui(self):
        """Initialize the streaks UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SocialTheme.COLORS['surface']};
                border: 1px solid {SocialTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        title_label = QLabel("Current Streaks")
        title_label.setFont(SocialTheme.FONTS['subheading'])
        
        # Streaks container
        self.streaks_layout = QVBoxLayout()
        
        layout.addWidget(title_label)
        layout.addLayout(self.streaks_layout)
        layout.addStretch()
    
    def load_streaks(self):
        """Load and display user streaks."""
        try:
            streaks = achievements_manager.get_user_streaks(self.current_user_id)
            
            # Clear existing streaks
            for i in reversed(range(self.streaks_layout.count())):
                child = self.streaks_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            if not streaks:
                no_streaks_label = QLabel("No active streaks")
                no_streaks_label.setFont(SocialTheme.FONTS['caption'])
                no_streaks_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
                self.streaks_layout.addWidget(no_streaks_label)
                return
            
            # Add streak items
            for streak in streaks:
                streak_widget = self.create_streak_item(streak)
                self.streaks_layout.addWidget(streak_widget)
                
        except Exception as e:
            logger.error(f"Error loading streaks: {e}")
    
    def create_streak_item(self, streak: Dict[str, Any]) -> QWidget:
        """Create a streak display item."""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {SocialTheme.COLORS['background']};
                border: 1px solid {SocialTheme.COLORS['border']};
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 4px;
            }}
        """)
        
        layout = QHBoxLayout(widget)
        
        # Streak icon
        streak_icons = {
            'login': '📅',
            'practice': '🏁',
            'improvement': '📈',
            'social': '👥',
            'challenge': '🎯'
        }
        
        streak_type = streak.get('streak_type', 'login')
        icon_label = QLabel(streak_icons.get(streak_type, '🔥'))
        icon_label.setFont(QFont('Segoe UI', 16))
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Streak info
        info_layout = QVBoxLayout()
        
        name_label = QLabel(streak_type.replace('_', ' ').title())
        name_label.setFont(SocialTheme.FONTS['body'])
        
        current_count = streak.get('current_count', 0)
        best_count = streak.get('best_count', 0)
        is_active = streak.get('is_active', True)
        
        if is_active:
            status_text = f"🔥 {current_count} days (Best: {best_count})"
            status_color = SocialTheme.COLORS['success']
        else:
            status_text = f"💔 Broken (Best: {best_count})"
            status_color = SocialTheme.COLORS['text_secondary']
        
        status_label = QLabel(status_text)
        status_label.setFont(SocialTheme.FONTS['caption'])
        status_label.setStyleSheet(f"color: {status_color};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(status_label)
        
        layout.addWidget(icon_label)
        layout.addLayout(info_layout)
        layout.addStretch()
        
        return widget

class ReputationWidget(QFrame):
    """User reputation display widget."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_reputation_data()
    
    def init_ui(self):
        """Initialize the reputation UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SocialTheme.COLORS['surface']};
                border: 1px solid {SocialTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Community Reputation")
        title_label.setFont(SocialTheme.FONTS['subheading'])
        
        self.reputation_score_label = QLabel("0")
        self.reputation_score_label.setFont(SocialTheme.FONTS['heading'])
        self.reputation_score_label.setStyleSheet(f"color: {SocialTheme.COLORS['accent']};")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.reputation_score_label)
        
        # Reputation level
        self.level_label = QLabel("Newcomer")
        self.level_label.setFont(SocialTheme.FONTS['body'])
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Progress to next level
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {SocialTheme.COLORS['border']};
                border-radius: 8px;
                text-align: center;
                background-color: {SocialTheme.COLORS['background']};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {SocialTheme.COLORS['warning']};
                border-radius: 6px;
            }}
        """)
        
        self.progress_label = QLabel("Progress to next level")
        self.progress_label.setFont(SocialTheme.FONTS['caption'])
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        layout.addLayout(header_layout)
        layout.addWidget(self.level_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
    
    def load_reputation_data(self):
        """Load and display reputation data."""
        try:
            level_info = reputation_manager.get_reputation_level_info(self.current_user_id)
            
            if level_info:
                reputation_score = level_info.get('current_reputation', 0)
                current_level = level_info.get('current_level', 'newcomer')
                next_level = level_info.get('next_level')
                points_to_next = level_info.get('points_to_next', 0)
                progress_percentage = level_info.get('progress_percentage', 0)
                
                # Update displays
                self.reputation_score_label.setText(str(reputation_score))
                self.level_label.setText(current_level.title())
                
                if next_level:
                    self.progress_bar.setValue(int(progress_percentage))
                    self.progress_label.setText(f"{points_to_next} points to {next_level.title()}")
                else:
                    self.progress_bar.setValue(100)
                    self.progress_label.setText("Maximum level reached!")
                    
        except Exception as e:
            logger.error(f"Error loading reputation data: {e}")

class GamificationMainWidget(QWidget):
    """Main gamification interface combining all elements."""
    
    def __init__(self, achievements_manager=None, reputation_manager=None, current_user_id: str = None, parent=None):
        super().__init__(parent)
        self.achievements_manager = achievements_manager
        self.reputation_manager = reputation_manager
        self.current_user_id = current_user_id
        self.init_ui()
    
    def init_ui(self):
        """Initialize the gamification UI."""
        layout = QVBoxLayout(self)
        
        # Top row - XP and Reputation
        top_layout = QHBoxLayout()
        
        self.xp_widget = XPProgressWidget(self.current_user_id)
        self.reputation_widget = ReputationWidget(self.current_user_id)
        
        top_layout.addWidget(self.xp_widget)
        top_layout.addWidget(self.reputation_widget)
        
        # Middle row - Streaks
        self.streaks_widget = StreaksWidget(self.current_user_id)
        self.streaks_widget.setMaximumHeight(200)
        
        # Bottom - Achievements
        self.achievements_widget = AchievementsWidget(self.current_user_id)
        
        layout.addLayout(top_layout)
        layout.addWidget(self.streaks_widget)
        layout.addWidget(self.achievements_widget)
    
    def refresh_data(self):
        """Refresh all gamification data."""
        self.xp_widget.load_xp_data()
        self.reputation_widget.load_reputation_data()
        self.streaks_widget.load_streaks()
        self.achievements_widget.load_achievements()

# Export components
__all__ = [
    'AchievementCard',
    'AchievementsWidget',
    'XPProgressWidget',
    'StreaksWidget',
    'ReputationWidget',
    'GamificationMainWidget'
] 