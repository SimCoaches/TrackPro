"""Videos tab for Race Coach - RaceFlix video courses interface.

This module contains the video courses tab with a Kajabi-like interface
for racing education content.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFrame, QScrollArea, QGridLayout, QLineEdit,
    QProgressBar, QTableWidget, QTableWidgetItem, QTextEdit,
    QStackedWidget, QSplitter, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)


class VideosTab(QWidget):
    """Tab for displaying video courses in a Kajabi-like interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_course = None
        self.current_video = None
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create stacked widget to switch between course browser and course view
        self.stacked_widget = QStackedWidget()
        
        # Create course browser
        self.course_browser = self.create_course_browser()
        self.stacked_widget.addWidget(self.course_browser)
        
        # Create course view
        self.course_view = self.create_course_view()
        self.stacked_widget.addWidget(self.course_view)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Load sample courses
        self.load_sample_courses()

    def create_course_browser(self):
        """Create the main course browsing interface."""
        browser = QWidget()
        layout = QVBoxLayout(browser)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("RaceFlix - Video Coaching")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #e67e22;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search courses...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 14px;
                min-width: 250px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.search_bar.textChanged.connect(self.filter_courses)
        header_layout.addWidget(self.search_bar)
        
        layout.addLayout(header_layout)

        # Filter tabs
        filter_layout = QHBoxLayout()
        
        self.filter_buttons = {}
        filters = ["All", "Beginner", "Intermediate", "Advanced", "New"]
        
        for filter_name in filters:
            btn = QPushButton(filter_name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #444;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: #ccc;
                    font-weight: bold;
                    margin-right: 5px;
                }
                QPushButton:checked {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QPushButton:checked:hover {
                    background-color: #2980b9;
                }
            """)
            btn.clicked.connect(lambda checked, f=filter_name: self.apply_filter(f))
            self.filter_buttons[filter_name] = btn
            filter_layout.addWidget(btn)
        
        # Set "All" as default
        self.filter_buttons["All"].setChecked(True)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Course grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #333;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #666;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #777;
            }
        """)

        self.course_grid_widget = QWidget()
        self.course_grid_layout = QGridLayout(self.course_grid_widget)
        self.course_grid_layout.setSpacing(20)
        self.course_grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area.setWidget(self.course_grid_widget)
        layout.addWidget(scroll_area)

        return browser

    def create_course_view(self):
        """Create the detailed course view with video player."""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with back button
        header = QWidget()
        header.setStyleSheet("background-color: #2c3e50; padding: 15px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        self.back_button = QPushButton("← Back to Courses")
        self.back_button.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #3498db;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                color: #2980b9;
                text-decoration: underline;
            }
        """)
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.show_course_browser)
        header_layout.addWidget(self.back_button)
        
        header_layout.addStretch()
        
        # Course progress
        self.progress_label = QLabel("Progress: 0/0 completed")
        self.progress_label.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        header_layout.addWidget(self.progress_label)
        
        layout.addWidget(header)

        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Video player and details
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        # Video player
        self.video_player = QWebEngineView()
        self.video_player.setMinimumHeight(400)
        self.video_player.setStyleSheet("""
            QWebEngineView {
                background-color: #000;
                border-radius: 8px;
                border: 2px solid #34495e;
            }
        """)
        
        # Load placeholder
        self.load_video_placeholder()
        left_layout.addWidget(self.video_player)

        # Video info
        video_info_widget = QWidget()
        video_info_layout = QVBoxLayout(video_info_widget)
        video_info_layout.setContentsMargins(0, 0, 0, 0)
        video_info_layout.setSpacing(10)

        self.video_title = QLabel("Select a lesson to start")
        self.video_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-bottom: 5px;
        """)
        video_info_layout.addWidget(self.video_title)

        self.video_description = QLabel("")
        self.video_description.setStyleSheet("""
            color: #bdc3c7;
            font-size: 14px;
            line-height: 1.4;
        """)
        self.video_description.setWordWrap(True)
        video_info_layout.addWidget(self.video_description)

        # Video controls
        controls_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("← Previous")
        self.prev_button.setStyleSheet(self.get_button_style())
        self.prev_button.clicked.connect(self.previous_video)
        controls_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next →")
        self.next_button.setStyleSheet(self.get_button_style())
        self.next_button.clicked.connect(self.next_video)
        controls_layout.addWidget(self.next_button)
        
        controls_layout.addStretch()
        
        self.mark_complete_button = QPushButton("Mark as Complete")
        self.mark_complete_button.setStyleSheet(self.get_button_style("#27ae60", "#229954"))
        self.mark_complete_button.clicked.connect(self.mark_video_complete)
        controls_layout.addWidget(self.mark_complete_button)
        
        video_info_layout.addLayout(controls_layout)
        left_layout.addWidget(video_info_widget)

        # Comments section
        comments_widget = self.create_comments_section()
        left_layout.addWidget(comments_widget)

        content_splitter.addWidget(left_panel)

        # Right side - Course modules
        right_panel = self.create_course_modules_panel()
        content_splitter.addWidget(right_panel)

        # Set splitter proportions (70% video, 30% modules)
        content_splitter.setSizes([700, 300])
        
        layout.addWidget(content_splitter)

        return view

    def create_course_modules_panel(self):
        """Create the course modules panel."""
        panel = QWidget()
        panel.setStyleSheet("background-color: #34495e;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Course info
        self.course_title_label = QLabel("Course Title")
        self.course_title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.course_title_label)

        self.course_instructor = QLabel("Instructor: ")
        self.course_instructor.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        layout.addWidget(self.course_instructor)

        # Course stats
        stats_layout = QHBoxLayout()
        
        self.course_level = QLabel("Level: ")
        self.course_level.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        stats_layout.addWidget(self.course_level)
        
        self.course_duration = QLabel("Duration: ")
        self.course_duration.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        stats_layout.addWidget(self.course_duration)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Modules list
        modules_label = QLabel("Course Modules")
        modules_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            margin-top: 15px;
            margin-bottom: 10px;
        """)
        layout.addWidget(modules_label)

        # Modules scroll area
        modules_scroll = QScrollArea()
        modules_scroll.setWidgetResizable(True)
        modules_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #2c3e50;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #7f8c8d;
                border-radius: 4px;
            }
        """)

        self.modules_widget = QWidget()
        self.modules_layout = QVBoxLayout(self.modules_widget)
        self.modules_layout.setContentsMargins(0, 0, 0, 0)
        self.modules_layout.setSpacing(8)
        
        modules_scroll.setWidget(self.modules_widget)
        layout.addWidget(modules_scroll)

        return panel

    def create_comments_section(self):
        """Create the comments section."""
        comments_widget = QWidget()
        comments_layout = QVBoxLayout(comments_widget)
        comments_layout.setContentsMargins(0, 0, 0, 0)
        comments_layout.setSpacing(15)

        # Comments header
        comments_header = QLabel("Discussion")
        comments_header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            margin-top: 20px;
            margin-bottom: 10px;
        """)
        comments_layout.addWidget(comments_header)

        # Add comment form
        comment_form = QWidget()
        comment_form_layout = QVBoxLayout(comment_form)
        comment_form_layout.setContentsMargins(0, 0, 0, 0)
        comment_form_layout.setSpacing(10)

        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Share your thoughts or ask a question...")
        self.comment_input.setMaximumHeight(80)
        self.comment_input.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        comment_form_layout.addWidget(self.comment_input)

        comment_buttons_layout = QHBoxLayout()
        comment_buttons_layout.addStretch()
        
        self.post_comment_button = QPushButton("Post Comment")
        self.post_comment_button.setStyleSheet(self.get_button_style("#3498db", "#2980b9"))
        self.post_comment_button.clicked.connect(self.post_comment)
        comment_buttons_layout.addWidget(self.post_comment_button)
        
        comment_form_layout.addLayout(comment_buttons_layout)
        comments_layout.addWidget(comment_form)

        # Comments list
        comments_scroll = QScrollArea()
        comments_scroll.setWidgetResizable(True)
        comments_scroll.setMaximumHeight(300)
        comments_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #34495e;
                border-radius: 6px;
                background-color: #2c3e50;
            }
            QScrollBar:vertical {
                background: #34495e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #7f8c8d;
                border-radius: 4px;
            }
        """)

        self.comments_widget = QWidget()
        self.comments_layout = QVBoxLayout(self.comments_widget)
        self.comments_layout.setContentsMargins(10, 10, 10, 10)
        self.comments_layout.setSpacing(10)
        self.comments_layout.addStretch()
        
        comments_scroll.setWidget(self.comments_widget)
        comments_layout.addWidget(comments_scroll)

        return comments_widget

    def get_button_style(self, bg_color="#3498db", hover_color="#2980b9"):
        """Get consistent button styling."""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #7f8c8d;
                color: #bdc3c7;
            }}
        """

    def load_sample_courses(self):
        """Load sample course data."""
        self.courses = [
            {
                "id": 1,
                "title": "Racing Fundamentals",
                "description": "Master the basics of racing with proper racing lines, braking techniques, and throttle control.",
                "instructor": "Alex Johnson",
                "level": "beginner",
                "duration": "2h 30m",
                "lessons": 8,
                "modules": [
                    {
                        "id": 1,
                        "title": "Introduction to Racing Lines",
                        "description": "Learn the optimal path around a race track for maximum speed and efficiency.",
                        "duration": "15:30",
                        "video_id": "dQw4w9WgXcQ",  # Sample YouTube ID
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Braking Techniques",
                        "description": "Master threshold braking and trail braking for better corner entry.",
                        "duration": "18:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 3,
                        "title": "Throttle Control",
                        "description": "Smooth throttle application for optimal traction and speed.",
                        "duration": "20:15",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 2,
                "title": "Advanced Cornering",
                "description": "Take your cornering to the next level with advanced techniques and car control.",
                "instructor": "Sarah Martinez",
                "level": "intermediate",
                "duration": "3h 15m",
                "lessons": 12,
                "modules": [
                    {
                        "id": 1,
                        "title": "Trail Braking Mastery",
                        "description": "Advanced trail braking techniques for faster corner entry.",
                        "duration": "22:30",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Oversteer and Understeer",
                        "description": "Understanding and correcting handling characteristics.",
                        "duration": "25:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 3,
                        "title": "Weight Transfer Dynamics",
                        "description": "Master how weight transfer affects your car's handling.",
                        "duration": "19:20",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 3,
                "title": "Race Strategy & Mental Game",
                "description": "Develop winning strategies and mental toughness for competitive racing.",
                "instructor": "Mike Thompson",
                "level": "advanced",
                "duration": "4h 20m",
                "lessons": 15,
                "modules": [
                    {
                        "id": 1,
                        "title": "Race Start Strategies",
                        "description": "Maximize your race starts and first lap positioning.",
                        "duration": "28:15",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Overtaking Techniques",
                        "description": "Safe and effective overtaking in different scenarios.",
                        "duration": "24:30",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 4,
                "title": "Car Setup Fundamentals",
                "description": "Learn how to tune your car for optimal performance on any track.",
                "instructor": "David Chen",
                "level": "intermediate",
                "duration": "2h 45m",
                "lessons": 10,
                "modules": [
                    {
                        "id": 1,
                        "title": "Suspension Basics",
                        "description": "Understanding springs, dampers, and anti-roll bars.",
                        "duration": "16:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Aerodynamics Setup",
                        "description": "Balancing downforce and drag for different tracks.",
                        "duration": "21:30",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 5,
                "title": "Tire Management",
                "description": "Master tire temperatures, pressures, and compound selection.",
                "instructor": "Emma Rodriguez",
                "level": "beginner",
                "duration": "1h 50m",
                "lessons": 6,
                "modules": [
                    {
                        "id": 1,
                        "title": "Understanding Tire Compounds",
                        "description": "Different tire types and when to use them.",
                        "duration": "18:20",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Tire Pressure Optimization",
                        "description": "Finding the perfect pressure for maximum grip.",
                        "duration": "15:40",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 6,
                "title": "Data Analysis Mastery",
                "description": "Use telemetry data to find speed and improve your driving.",
                "instructor": "Alex Johnson",
                "level": "advanced",
                "duration": "3h 30m",
                "lessons": 14,
                "modules": [
                    {
                        "id": 1,
                        "title": "Reading Telemetry Data",
                        "description": "Understanding speed traces, throttle, and brake data.",
                        "duration": "26:15",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Comparing Lap Times",
                        "description": "Analyzing differences between fast and slow laps.",
                        "duration": "23:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            }
        ]
        
        self.display_courses()

    def display_courses(self):
        """Display courses in the grid."""
        # Clear existing courses
        for i in reversed(range(self.course_grid_layout.count())):
            child = self.course_grid_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Add courses to grid
        row, col = 0, 0
        max_cols = 3

        for course in self.courses:
            if self.should_show_course(course):
                course_card = EnhancedCourseCard(course)
                course_card.clicked.connect(lambda checked, c=course: self.open_course(c))
                
                self.course_grid_layout.addWidget(course_card, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        # Add stretch to push cards to top
        self.course_grid_layout.setRowStretch(row + 1, 1)

    def should_show_course(self, course):
        """Check if course should be shown based on current filters."""
        # Check search filter
        search_text = self.search_bar.text().lower()
        if search_text and search_text not in course["title"].lower() and search_text not in course["description"].lower():
            return False
        
        # Check level filter
        active_filter = None
        for filter_name, button in self.filter_buttons.items():
            if button.isChecked():
                active_filter = filter_name
                break
        
        if active_filter and active_filter != "All":
            if active_filter.lower() != course["level"]:
                return False
        
        return True

    def filter_courses(self):
        """Filter courses based on search text."""
        self.display_courses()

    def apply_filter(self, filter_name):
        """Apply level filter."""
        # Uncheck other filters
        for name, button in self.filter_buttons.items():
            if name != filter_name:
                button.setChecked(False)
        
        self.display_courses()

    def open_course(self, course):
        """Open a course in the course view."""
        self.current_course = course
        self.current_video = None
        
        # Update course info
        self.course_title_label.setText(course["title"])
        self.course_instructor.setText(f"Instructor: {course['instructor']}")
        self.course_level.setText(f"Level: {course['level'].capitalize()}")
        self.course_duration.setText(f"Duration: {course['duration']}")
        
        # Update progress
        completed_count = sum(1 for module in course["modules"] if module.get("completed", False))
        total_count = len(course["modules"])
        self.progress_label.setText(f"Progress: {completed_count}/{total_count} completed")
        
        # Clear and populate modules
        self.clear_modules()
        for i, module in enumerate(course["modules"]):
            module_card = VideoModuleCard(module, i + 1)
            module_card.clicked.connect(lambda checked, m=module: self.play_video(m))
            self.modules_layout.addWidget(module_card)
        
        self.modules_layout.addStretch()
        
        # Switch to course view
        self.stacked_widget.setCurrentIndex(1)
        
        # Load first video if available
        if course["modules"]:
            self.play_video(course["modules"][0])

    def play_video(self, module):
        """Play a video module."""
        self.current_video = module
        
        # Update video info
        self.video_title.setText(module["title"])
        self.video_description.setText(module["description"])
        
        # Update navigation buttons
        current_index = self.get_current_video_index()
        self.prev_button.setEnabled(current_index > 0)
        self.next_button.setEnabled(current_index < len(self.current_course["modules"]) - 1)
        
        # Update complete button
        if module.get("completed", False):
            self.mark_complete_button.setText("Completed ✓")
            self.mark_complete_button.setEnabled(False)
        else:
            self.mark_complete_button.setText("Mark as Complete")
            self.mark_complete_button.setEnabled(True)
        
        # Load video
        video_id = module.get("video_id", "")
        if video_id:
            self.load_youtube_video(video_id)
        else:
            self.load_video_placeholder()
        
        # Load comments for this video
        self.load_comments(module["id"])

    def load_youtube_video(self, video_id):
        """Load a YouTube video in the player."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    background: #000;
                    overflow: hidden;
                }}
                .video-container {{
                    position: relative;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                iframe {{
                    width: 100%;
                    height: 100%;
                    border: none;
                }}
                .error-message {{
                    display: none;
                    color: #fff;
                    text-align: center;
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="video-container">
                <iframe 
                    id="videoFrame"
                    src="https://www.youtube.com/embed/{video_id}?autoplay=0&rel=0&modestbranding=1&showinfo=0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen>
                </iframe>
                <div id="errorMessage" class="error-message">
                    <h3>Unable to load video</h3>
                    <p>Please check your internet connection and try again.</p>
                </div>
            </div>
            <script>
                // Error handling
                document.getElementById('videoFrame').onerror = function() {{
                    document.getElementById('videoFrame').style.display = 'none';
                    document.getElementById('errorMessage').style.display = 'block';
                }};
            </script>
        </body>
        </html>
        """
        self.video_player.setHtml(html_content)

    def load_video_placeholder(self):
        """Load placeholder when no video is available."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body, html {
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(135deg, #2c3e50, #34495e);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-family: Arial, sans-serif;
                }
                .placeholder {
                    text-align: center;
                    color: #bdc3c7;
                }
                .play-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                    opacity: 0.7;
                }
                .text {
                    font-size: 18px;
                    margin-bottom: 10px;
                }
                .subtext {
                    font-size: 14px;
                    opacity: 0.8;
                }
            </style>
        </head>
        <body>
            <div class="placeholder">
                <div class="play-icon">▶️</div>
                <div class="text">Select a lesson to start learning</div>
                <div class="subtext">Choose from the course modules on the right</div>
            </div>
        </body>
        </html>
        """
        self.video_player.setHtml(html_content)

    def get_current_video_index(self):
        """Get the index of the current video in the course."""
        if not self.current_course or not self.current_video:
            return -1
        
        for i, module in enumerate(self.current_course["modules"]):
            if module["id"] == self.current_video["id"]:
                return i
        return -1

    def previous_video(self):
        """Play the previous video."""
        current_index = self.get_current_video_index()
        if current_index > 0:
            self.play_video(self.current_course["modules"][current_index - 1])

    def next_video(self):
        """Play the next video."""
        current_index = self.get_current_video_index()
        if current_index < len(self.current_course["modules"]) - 1:
            self.play_video(self.current_course["modules"][current_index + 1])

    def mark_video_complete(self):
        """Mark the current video as complete."""
        if self.current_video:
            self.current_video["completed"] = True
            self.mark_complete_button.setText("Completed ✓")
            self.mark_complete_button.setEnabled(False)
            
            # Update progress
            completed_count = sum(1 for module in self.current_course["modules"] if module.get("completed", False))
            total_count = len(self.current_course["modules"])
            self.progress_label.setText(f"Progress: {completed_count}/{total_count} completed")
            
            # Update module card appearance
            self.refresh_module_cards()

    def refresh_module_cards(self):
        """Refresh the appearance of module cards."""
        for i in range(self.modules_layout.count() - 1):  # -1 for stretch
            item = self.modules_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'update_completion_status'):
                    widget.update_completion_status()

    def clear_modules(self):
        """Clear all module widgets."""
        while self.modules_layout.count() > 0:
            item = self.modules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_course_browser(self):
        """Return to the course browser."""
        self.stacked_widget.setCurrentIndex(0)

    def load_comments(self, video_id):
        """Load comments for a video."""
        # Clear existing comments
        while self.comments_layout.count() > 1:  # Keep the stretch
            item = self.comments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Sample comments (in a real app, these would come from a database)
        sample_comments = [
            {
                "id": 1,
                "author": "RacingPro42",
                "text": "Great explanation of racing lines! This really helped me understand the concept better.",
                "timestamp": "2 hours ago",
                "likes": 5
            },
            {
                "id": 2,
                "author": "SpeedDemon",
                "text": "I've been struggling with this technique. The visual examples make it so much clearer.",
                "timestamp": "1 day ago",
                "likes": 3
            }
        ]
        
        for comment in sample_comments:
            comment_widget = self.create_comment_widget(comment)
            self.comments_layout.insertWidget(self.comments_layout.count() - 1, comment_widget)

    def create_comment_widget(self, comment):
        """Create a widget for displaying a comment."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #34495e;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 5px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Header with author and timestamp
        header_layout = QHBoxLayout()
        
        author_label = QLabel(comment["author"])
        author_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(author_label)
        
        header_layout.addStretch()
        
        timestamp_label = QLabel(comment["timestamp"])
        timestamp_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        header_layout.addWidget(timestamp_label)
        
        layout.addLayout(header_layout)
        
        # Comment text
        text_label = QLabel(comment["text"])
        text_label.setStyleSheet("color: #ecf0f1; font-size: 14px; line-height: 1.4;")
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # Footer with likes
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        likes_label = QLabel(f"👍 {comment['likes']}")
        likes_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        footer_layout.addWidget(likes_label)
        
        layout.addLayout(footer_layout)
        
        return widget

    def post_comment(self):
        """Post a new comment."""
        comment_text = self.comment_input.toPlainText().strip()
        if not comment_text:
            return
        
        # Create new comment
        new_comment = {
            "id": len(self.comments_layout) + 1,
            "author": "You",
            "text": comment_text,
            "timestamp": "Just now",
            "likes": 0
        }
        
        # Add comment widget
        comment_widget = self.create_comment_widget(new_comment)
        self.comments_layout.insertWidget(self.comments_layout.count() - 1, comment_widget)
        
        # Clear input
        self.comment_input.clear()
        
        # Scroll to bottom
        QTimer.singleShot(100, lambda: self.scroll_comments_to_bottom())

    def scroll_comments_to_bottom(self):
        """Scroll comments to bottom."""
        # Find the scroll area parent
        scroll_area = self.comments_widget.parent()
        if hasattr(scroll_area, 'verticalScrollBar'):
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())


class EnhancedCourseCard(QFrame):
    """Enhanced course card widget with better styling."""
    
    clicked = pyqtSignal(bool)

    def __init__(self, course_data, parent=None):
        super().__init__(parent)
        self.course_data = course_data
        
        self.setFixedSize(320, 400)
        self.setStyleSheet("""
            EnhancedCourseCard {
                background-color: #2c3e50;
                border-radius: 12px;
                border: 2px solid transparent;
            }
            EnhancedCourseCard:hover {
                border-color: #3498db;
                background-color: #34495e;
            }
        """)
        
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Thumbnail
        thumbnail = QLabel()
        thumbnail.setFixedHeight(180)
        thumbnail.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #3498db, stop:1 #2980b9);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)
        
        # Add level badge to thumbnail
        badge_text = course_data["level"].upper()
        badge_color = {
            "beginner": "#27ae60",
            "intermediate": "#f39c12", 
            "advanced": "#e74c3c"
        }.get(course_data["level"], "#3498db")
        
        thumbnail_layout = QVBoxLayout(thumbnail)
        thumbnail_layout.setContentsMargins(15, 15, 15, 15)
        
        level_badge = QLabel(badge_text)
        level_badge.setStyleSheet(f"""
            background-color: {badge_color};
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        level_badge.setAlignment(Qt.AlignCenter)
        level_badge.setMaximumWidth(80)
        
        thumbnail_layout.addWidget(level_badge)
        thumbnail_layout.addStretch()
        
        # Play icon
        play_icon = QLabel("▶")
        play_icon.setStyleSheet("""
            color: white;
            font-size: 32px;
            background-color: rgba(0, 0, 0, 0.6);
            border-radius: 25px;
            padding: 10px;
        """)
        play_icon.setAlignment(Qt.AlignCenter)
        play_icon.setFixedSize(50, 50)
        
        thumbnail_layout.addWidget(play_icon, 0, Qt.AlignCenter)
        thumbnail_layout.addStretch()
        
        layout.addWidget(thumbnail)
        
        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(10)
        
        # Title
        title = QLabel(course_data["title"])
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            margin-bottom: 5px;
        """)
        title.setWordWrap(True)
        content_layout.addWidget(title)
        
        # Instructor
        instructor = QLabel(f"by {course_data['instructor']}")
        instructor.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        content_layout.addWidget(instructor)
        
        # Description
        description = QLabel(course_data["description"])
        description.setStyleSheet("""
            color: #95a5a6;
            font-size: 13px;
            line-height: 1.3;
        """)
        description.setWordWrap(True)
        description.setMaximumHeight(60)
        content_layout.addWidget(description)
        
        # Stats
        stats_layout = QHBoxLayout()
        
        duration_label = QLabel(f"🕒 {course_data['duration']}")
        duration_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        stats_layout.addWidget(duration_label)
        
        lessons_label = QLabel(f"📚 {course_data['lessons']} lessons")
        lessons_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        stats_layout.addWidget(lessons_label)
        
        stats_layout.addStretch()
        content_layout.addLayout(stats_layout)
        
        layout.addWidget(content)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        super().mousePressEvent(event)
        self.clicked.emit(True)


class VideoModuleCard(QFrame):
    """Widget for displaying a video module in the course view."""
    
    clicked = pyqtSignal(bool)

    def __init__(self, module_data, module_number, parent=None):
        super().__init__(parent)
        self.module_data = module_data
        self.module_number = module_number
        
        self.setStyleSheet("""
            VideoModuleCard {
                background-color: #2c3e50;
                border-radius: 8px;
                border: 2px solid transparent;
                padding: 5px;
            }
            VideoModuleCard:hover {
                border-color: #3498db;
                background-color: #34495e;
            }
        """)
        
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Module number
        self.number_label = QLabel(str(module_number))
        self.number_label.setStyleSheet("""
            background-color: #3498db;
            color: white;
            border-radius: 18px;
            font-weight: bold;
            font-size: 14px;
            min-width: 36px;
            max-width: 36px;
            min-height: 36px;
            max-height: 36px;
            qproperty-alignment: AlignCenter;
        """)
        layout.addWidget(self.number_label)
        
        # Module info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.title_label = QLabel(module_data["title"])
        self.title_label.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 15px;
        """)
        info_layout.addWidget(self.title_label)
        
        duration_label = QLabel(f"Duration: {module_data['duration']}")
        duration_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        info_layout.addWidget(duration_label)
        
        layout.addLayout(info_layout, 1)
        
        # Status icon
        self.status_icon = QLabel("▶")
        self.status_icon.setStyleSheet("""
            color: #3498db;
            font-size: 18px;
            padding: 5px;
        """)
        layout.addWidget(self.status_icon)
        
        self.update_completion_status()

    def update_completion_status(self):
        """Update the visual status based on completion."""
        if self.module_data.get("completed", False):
            self.status_icon.setText("✓")
            self.status_icon.setStyleSheet("""
                color: #27ae60;
                font-size: 18px;
                font-weight: bold;
                padding: 5px;
            """)
            self.number_label.setStyleSheet("""
                background-color: #27ae60;
                color: white;
                border-radius: 18px;
                font-weight: bold;
                font-size: 14px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
                qproperty-alignment: AlignCenter;
            """)
        else:
            self.status_icon.setText("▶")
            self.status_icon.setStyleSheet("""
                color: #3498db;
                font-size: 18px;
                padding: 5px;
            """)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        super().mousePressEvent(event)
        self.clicked.emit(True) 