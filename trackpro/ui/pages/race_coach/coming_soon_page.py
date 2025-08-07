import logging
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PyQt6.QtCore import Qt
from ...modern.shared.base_page import BasePage


logger = logging.getLogger(__name__)


class RaceCoachComingSoonPage(BasePage):
    """Race Coach page placeholder shown while the feature is in development."""

    def __init__(self, global_managers=None):
        super().__init__("Race Coach", global_managers)

    def init_page(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        self._create_coming_soon_content(layout)

    def _create_coming_soon_content(self, layout: QVBoxLayout) -> None:
        # Main container
        main_frame = QFrame()
        main_frame.setStyleSheet(
            """
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #333;
                border-radius: 12px;
                padding: 40px;
            }
            """
        )
        main_layout = QVBoxLayout(main_frame)
        main_layout.setSpacing(25)

        # Title
        title_label = QLabel("Race Coach")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            color: #ffffff;
            font-size: 36px;
            font-weight: bold;
            text-align: center;
            """
        )
        main_layout.addWidget(title_label)

        # Coming soon badge
        coming_soon_label = QLabel("COMING SOON")
        coming_soon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        coming_soon_label.setStyleSheet(
            """
            color: #00d4ff;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            background-color: rgba(0, 212, 255, 0.1);
            border: 2px solid #00d4ff;
            border-radius: 20px;
            padding: 8px 20px;
            """
        )
        main_layout.addWidget(coming_soon_label)

        # Description
        desc_label = QLabel(
            "We're building an all-new Race Coach experience!\n\n"
            "Get ready for:\n"
            "• Real-time AI voice coaching\n"
            "• Telemetry-driven insights and lap comparisons\n"
            "• Braking and throttle optimization guidance\n"
            "• SuperLap ghost and sector-by-sector analysis\n"
            "• Personalized training plans and goals\n"
            "• RaceFlix video library with pro tips"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            """
            color: #cccccc;
            font-size: 16px;
            text-align: center;
            line-height: 1.6;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
            """
        )
        main_layout.addWidget(desc_label)

        # Progress indicator
        progress_frame = QFrame()
        progress_frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 20px;
            }
            """
        )
        progress_layout = QVBoxLayout(progress_frame)

        progress_title = QLabel("Development Progress")
        progress_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_title.setStyleSheet(
            """
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
            """
        )
        progress_layout.addWidget(progress_title)

        progress_bar_frame = QFrame()
        progress_bar_frame.setStyleSheet(
            """
            QFrame {
                background-color: #333;
                border-radius: 10px;
                padding: 3px;
            }
            """
        )
        progress_bar_layout = QHBoxLayout(progress_bar_frame)
        progress_bar_layout.setContentsMargins(0, 0, 0, 0)

        progress_fill = QFrame()
        progress_fill.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff, stop:1 #0099cc);
                border-radius: 7px;
            }
            """
        )
        progress_fill.setFixedWidth(233)
        progress_bar_layout.addWidget(progress_fill)
        progress_bar_layout.addStretch()
        progress_layout.addWidget(progress_bar_frame)

        progress_text = QLabel("70% Complete")
        progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_text.setStyleSheet(
            """
            color: #00d4ff;
            font-size: 14px;
            font-weight: bold;
            text-align: center;
            margin-top: 5px;
            """
        )
        progress_layout.addWidget(progress_text)

        main_layout.addWidget(progress_frame)

        main_layout.addStretch()
        layout.addWidget(main_frame)

    def on_page_activated(self):
        super().on_page_activated()
        logger.info("🎓 Race Coach Coming Soon page activated")

    def lazy_init(self):
        logger.info("🎓 Race Coach Coming Soon page lazy initialization")

    def cleanup(self):
        logger.info("🧹 Race Coach Coming Soon page cleanup")
        super().cleanup()


