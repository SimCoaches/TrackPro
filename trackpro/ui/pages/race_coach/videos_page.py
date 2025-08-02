import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QStackedWidget, QSplitter,
    QTextEdit, QProgressBar, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class CourseCard(QFrame):
    course_selected = pyqtSignal(dict)
    
    def __init__(self, course_data, parent=None):
        super().__init__(parent)
        self.course_data = course_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedSize(300, 200)
        self.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #2a82da;
                background-color: #333;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        thumbnail = QLabel()
        thumbnail.setFixedSize(280, 120)
        thumbnail.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #555;
            border-radius: 4px;
        """)
        thumbnail.setText("📹 Course Thumbnail")
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thumbnail)
        
        title = QLabel(self.course_data.get("title", "Course Title"))
        title.setStyleSheet("""
            color: #e0e0e0;
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        description = QLabel(self.course_data.get("description", "Course description"))
        description.setStyleSheet("""
            color: #aaa;
            font-size: 11px;
        """)
        description.setWordWrap(True)
        layout.addWidget(description)
        
        layout.addStretch()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.course_selected.emit(self.course_data)

class VideoPlayerWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        video_area = QLabel()
        video_area.setFixedHeight(400)
        video_area.setStyleSheet("""
            background-color: #000;
            border: 1px solid #555;
            border-radius: 4px;
        """)
        video_area.setText("🎬 Video Player Area\nClick a course to start watching")
        video_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_area.setStyleSheet(video_area.styleSheet() + "color: #888; font-size: 16px;")
        layout.addWidget(video_area)
        
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶️ Play")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        controls_layout.addWidget(self.play_btn)
        
        progress_bar = QProgressBar()
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #2a2a2a;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 3px;
            }
        """)
        progress_bar.setValue(0)
        controls_layout.addWidget(progress_bar, 1)
        
        time_label = QLabel("00:00 / 00:00")
        time_label.setStyleSheet("color: #aaa; font-size: 12px;")
        controls_layout.addWidget(time_label)
        
        layout.addLayout(controls_layout)

class CourseContentWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        title = QLabel("📚 Course Content")
        title.setStyleSheet("""
            color: #e0e0e0;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        lessons_scroll = QScrollArea()
        lessons_scroll.setWidgetResizable(True)
        lessons_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        lessons_widget = QWidget()
        lessons_layout = QVBoxLayout(lessons_widget)
        
        sample_lessons = [
            "1. Introduction to Racing Lines",
            "2. Braking Techniques",
            "3. Cornering Fundamentals",
            "4. Throttle Control",
            "5. Advanced Techniques"
        ]
        
        for lesson in sample_lessons:
            lesson_btn = QPushButton(lesson)
            lesson_btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    background-color: #333;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #444;
                    border-color: #2a82da;
                }
            """)
            lessons_layout.addWidget(lesson_btn)
        
        lessons_layout.addStretch()
        lessons_scroll.setWidget(lessons_widget)
        layout.addWidget(lessons_scroll)

class VideosPage(BasePage):
    def __init__(self, global_managers=None):
        super().__init__("Race Coach Videos", global_managers)
        
    def init_page(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header = QLabel("🎬 RaceFlix - Video Courses")
        header.setObjectName("page-header")
        header.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #2a82da;
            margin-bottom: 10px;
        """)
        layout.addWidget(header)
        
        self.stacked_widget = QStackedWidget()
        
        self.course_browser = self.create_course_browser()
        self.stacked_widget.addWidget(self.course_browser)
        
        self.course_view = self.create_course_view()
        self.stacked_widget.addWidget(self.course_view)
        
        layout.addWidget(self.stacked_widget)
        
    def create_course_browser(self):
        browser = QWidget()
        layout = QVBoxLayout(browser)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        search_layout = QHBoxLayout()
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search courses...")
        search_box.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        search_layout.addWidget(search_box)
        
        filter_combo = QComboBox()
        filter_combo.addItems(["All Courses", "Beginner", "Intermediate", "Advanced"])
        filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
                min-width: 120px;
            }
        """)
        search_layout.addWidget(filter_combo)
        
        layout.addLayout(search_layout)
        
        courses_scroll = QScrollArea()
        courses_scroll.setWidgetResizable(True)
        courses_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        courses_widget = QWidget()
        courses_layout = QGridLayout(courses_widget)
        courses_layout.setSpacing(15)
        
        sample_courses = [
            {"title": "Racing Fundamentals", "description": "Learn the basics of sim racing"},
            {"title": "Advanced Techniques", "description": "Master advanced racing techniques"},
            {"title": "Setup Tuning", "description": "Optimize your car setup"},
            {"title": "Track Analysis", "description": "Analyze tracks like a pro"},
        ]
        
        for i, course in enumerate(sample_courses):
            course_card = CourseCard(course)
            course_card.course_selected.connect(self.open_course)
            row, col = divmod(i, 2)
            courses_layout.addWidget(course_card, row, col)
        
        courses_layout.setRowStretch(courses_layout.rowCount(), 1)
        courses_scroll.setWidget(courses_widget)
        layout.addWidget(courses_scroll)
        
        return browser
        
    def create_course_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        back_btn = QPushButton("← Back to Courses")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)
        
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.video_player = VideoPlayerWidget()
        content_splitter.addWidget(self.video_player)
        
        self.course_content = CourseContentWidget()
        content_splitter.addWidget(self.course_content)
        
        content_splitter.setSizes([600, 300])
        layout.addWidget(content_splitter)
        
        return view
    
    def lazy_init(self):
        logger.info("🎬 Lazy initializing Videos page...")
    
    def open_course(self, course_data):
        logger.info(f"Opening course: {course_data.get('title')}")
        self.stacked_widget.setCurrentIndex(1)
    
    def on_page_activated(self):
        super().on_page_activated()