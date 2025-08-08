import os
import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QScrollArea,
    QFrame,
    QMessageBox,
)

from ...avatar_manager import AvatarManager

logger = logging.getLogger(__name__)


class PublicProfilePage(QWidget):
    """Public profile page for a user with banner, avatar, display name, and bio."""

    def __init__(self, global_managers, user_id: str, parent=None):
        super().__init__(parent)
        self.global_managers = global_managers
        self.user_id = user_id
        self.current_user_id: Optional[str] = None
        self.profile: dict = {}

        self._init_ui()
        self._detect_current_user()
        self._load_profile()

    def _init_ui(self) -> None:
        self.setObjectName("PublicProfilePage")
        self.setStyleSheet("""
            QWidget#PublicProfilePage { background-color: #1e1e1e; }
            QLabel#DisplayName { color: #ffffff; font-size: 20px; font-weight: 700; }
            QLabel#Username { color: #c8c8c8; font-size: 13px; }
            QLabel#SectionTitle { color: #ffffff; font-size: 14px; font-weight: 600; }
            QTextEdit#BioEdit { background-color: #252525; border: 1px solid #353535; color: #eaeaea; border-radius: 6px; }
            QPushButton.Primary { background-color: #5865f2; color: #ffffff; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }
            QPushButton.Primary:hover { background-color: #4752c4; }
            QPushButton.Secondary { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3a3a3a; border-radius: 6px; padding: 6px 12px; }
            QPushButton.Secondary:hover { background-color: #333333; }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # Banner
        self.banner = QLabel()
        self.banner.setFixedHeight(180)
        self.banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner.setStyleSheet("background-color: #2a2f3a;")
        self.container_layout.addWidget(self.banner)

        # Header row with avatar and name
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(12)

        # Avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(96, 96)
        self.avatar_label.setStyleSheet("border-radius: 48px; background: #202020;")
        header_layout.addWidget(self.avatar_label, 0, Qt.AlignmentFlag.AlignTop)

        # Name and actions
        name_actions = QVBoxLayout()
        self.display_name_label = QLabel("")
        self.display_name_label.setObjectName("DisplayName")
        self.username_label = QLabel("")
        self.username_label.setObjectName("Username")
        name_actions.addWidget(self.display_name_label)
        name_actions.addWidget(self.username_label)

        # Action buttons row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self.message_btn = QPushButton("Message")
        self.message_btn.setProperty("class", "Primary")
        self.message_btn.setObjectName("MessageButton")
        self.message_btn.setFixedHeight(32)
        self.message_btn.clicked.connect(self._start_dm)
        self.friend_btn = QPushButton("Add Friend")
        self.friend_btn.setProperty("class", "Secondary")
        self.friend_btn.setFixedHeight(32)
        self.friend_btn.clicked.connect(self._send_friend_request)
        actions_row.addWidget(self.message_btn)
        actions_row.addWidget(self.friend_btn)
        actions_row.addStretch()
        name_actions.addLayout(actions_row)

        header_layout.addLayout(name_actions, 1)
        self.container_layout.addWidget(header)

        # Bio section
        bio_card = QFrame()
        bio_layout = QVBoxLayout(bio_card)
        bio_layout.setContentsMargins(16, 16, 16, 16)
        bio_title = QLabel("Bio")
        bio_title.setObjectName("SectionTitle")
        bio_layout.addWidget(bio_title)

        self.bio_view = QLabel("")
        self.bio_view.setWordWrap(True)
        self.bio_edit = QTextEdit()
        self.bio_edit.setObjectName("BioEdit")
        self.bio_edit.setMaximumHeight(120)
        self.bio_edit.setVisible(False)

        bio_layout.addWidget(self.bio_view)
        bio_layout.addWidget(self.bio_edit)

        self.bio_actions = QHBoxLayout()
        self.bio_actions.setSpacing(8)
        self.save_bio_btn = QPushButton("Save Bio")
        self.save_bio_btn.setProperty("class", "Primary")
        self.save_bio_btn.setFixedHeight(32)
        self.save_bio_btn.clicked.connect(self._save_bio)
        self.edit_bio_btn = QPushButton("Edit Bio")
        self.edit_bio_btn.setProperty("class", "Secondary")
        self.edit_bio_btn.setFixedHeight(32)
        self.edit_bio_btn.clicked.connect(self._enter_bio_edit)
        self.bio_actions.addWidget(self.edit_bio_btn)
        self.bio_actions.addWidget(self.save_bio_btn)
        self.bio_actions.addStretch()
        bio_layout.addLayout(self.bio_actions)

        self.container_layout.addWidget(bio_card)

        # Hook up banner click to upload when owner
        self.banner.mousePressEvent = self._on_banner_click

    def _detect_current_user(self) -> None:
        try:
            from ....database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if client and client.auth:
                user_resp = client.auth.get_user()
                if user_resp and user_resp.user:
                    self.current_user_id = getattr(user_resp.user, 'id', None)
        except Exception as e:
            logger.debug(f"Could not detect current user: {e}")

    def _load_profile(self) -> None:
        try:
            from ....database.supabase_client import get_supabase_client
            client = get_supabase_client()
            data = None
            if client:
                try:
                    resp = client.from_("public_user_profiles").select(
                        "user_id, username, display_name, avatar_url, bio, banner_url"
                    ).eq("user_id", self.user_id).single().execute()
                    data = resp.data
                except Exception:
                    resp = client.from_("user_profiles").select(
                        "user_id, username, display_name, avatar_url, bio, banner_url"
                    ).eq("user_id", self.user_id).single().execute()
                    data = resp.data

            self.profile = data or {}
            display_name = self.profile.get('display_name') or self.profile.get('username') or 'User'
            username = self.profile.get('username') or ''

            self.display_name_label.setText(display_name)
            self.username_label.setText(f"@{username}" if username else "")

            # Avatar
            AvatarManager.instance().set_label_avatar(
                self.avatar_label,
                self.profile.get('avatar_url'),
                display_name,
                size=96,
            )

            # Banner
            banner_url = self.profile.get('banner_url')
            if banner_url:
                self._set_banner_from_url(banner_url)
            else:
                self.banner.setText("Click to add a banner")
                self.banner.setStyleSheet(self.banner.styleSheet() + "; color: #c8c8c8;")

            # Bio
            bio_text = self.profile.get('bio') or "No bio yet."
            self.bio_view.setText(bio_text)

            # Owner controls
            is_owner = (self.current_user_id == self.user_id) and bool(self.current_user_id)
            self.edit_bio_btn.setVisible(is_owner)
            self.save_bio_btn.setVisible(False)
            if is_owner:
                self.friend_btn.setEnabled(False)
                self.friend_btn.setText("It's you")
                self.message_btn.setEnabled(False)
                self.message_btn.setText("Account Settings")

        except Exception as e:
            logger.error(f"Error loading public profile: {e}")

    def _set_banner_from_url(self, url: str) -> None:
        try:
            import requests
            r = requests.get(url, timeout=8)
            if r.ok:
                pix = QPixmap()
                if pix.loadFromData(r.content):
                    scaled = pix.scaled(self.banner.width(), self.banner.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    self.banner.setPixmap(scaled)
                    self.banner.setStyleSheet("background-color: #2a2f3a;")
                    self.banner.setText("")
        except Exception as e:
            logger.debug(f"Banner load failed: {e}")

    def resizeEvent(self, event):  # Keep banner scaled on resize
        super().resizeEvent(event)
        if self.banner.pixmap():
            pix = self.banner.pixmap()
            scaled = pix.scaled(self.banner.width(), self.banner.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.banner.setPixmap(scaled)

    def _enter_bio_edit(self) -> None:
        is_owner = (self.current_user_id == self.user_id) and bool(self.current_user_id)
        if not is_owner:
            return
        self.bio_edit.setText(self.bio_view.text())
        self.bio_view.setVisible(False)
        self.bio_edit.setVisible(True)
        self.save_bio_btn.setVisible(True)

    def _save_bio(self) -> None:
        try:
            text = self.bio_edit.toPlainText().strip()
            from ....database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client or not self.current_user_id or self.current_user_id != self.user_id:
                return
            try:
                client.from_("user_profiles").update({"bio": text}).eq("user_id", self.user_id).execute()
            except Exception:
                pass
            self.bio_view.setText(text or "No bio yet.")
            self.bio_view.setVisible(True)
            self.bio_edit.setVisible(False)
            self.save_bio_btn.setVisible(False)
        except Exception as e:
            logger.error(f"Failed to save bio: {e}")
            QMessageBox.warning(self, "Error", "Could not save bio.")

    def _on_banner_click(self, event) -> None:
        is_owner = (self.current_user_id == self.user_id) and bool(self.current_user_id)
        if not is_owner:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose Banner Image", "", "Images (*.png *.jpg *.jpeg)")
        if not file_path:
            return
        self._set_banner_preview_local(file_path)
        self._upload_banner(file_path)

    def _set_banner_preview_local(self, file_path: str) -> None:
        try:
            pix = QPixmap(file_path)
            if not pix.isNull():
                scaled = pix.scaled(self.banner.width(), self.banner.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                self.banner.setPixmap(scaled)
                self.banner.setText("")
        except Exception as e:
            logger.debug(f"Local banner preview failed: {e}")

    def _upload_banner(self, file_path: str) -> None:
        try:
            from ....database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client or not self.current_user_id or self.current_user_id != self.user_id:
                QMessageBox.information(self, "Authentication Required", "Sign in to upload a banner.")
                return

            ext = os.path.splitext(file_path)[1].lower() or ".png"
            storage_path = f"{self.user_id}/banner{ext}"
            with open(file_path, "rb") as f:
                client.storage.from_("banners").upload(storage_path, f, {
                    "contentType": "image/png" if ext == ".png" else "image/jpeg",
                    "upsert": True,
                })

            public_url = client.storage.from_("banners").get_public_url(storage_path)
            if public_url:
                try:
                    client.from_("user_profiles").update({"banner_url": public_url}).eq("user_id", self.user_id).execute()
                except Exception:
                    pass
                self.profile["banner_url"] = public_url
                self._set_banner_from_url(public_url)
                QMessageBox.information(self, "Success", "Banner uploaded!")
        except Exception as e:
            logger.error(f"Banner upload failed: {e}")
            QMessageBox.warning(self, "Upload Failed", "Could not upload banner.")

    def _start_dm(self) -> None:
        try:
            if not self.user_id or (self.current_user_id == self.user_id):
                return
            main_window = self.window()
            if main_window and hasattr(main_window, 'start_direct_private_message'):
                minimal_user_data = {
                    'user_id': self.user_id,
                    'username': self.profile.get('username'),
                    'display_name': self.profile.get('display_name') or self.profile.get('username') or 'User',
                    'avatar_url': self.profile.get('avatar_url'),
                }
                main_window.start_direct_private_message(minimal_user_data)
        except Exception as e:
            logger.debug(f"Failed to start DM: {e}")

    def _send_friend_request(self) -> None:
        try:
            if not self.user_id or (self.current_user_id == self.user_id):
                return
            from ....social.friends_manager import FriendsManager
            fm = FriendsManager()
            result = fm.send_friend_request(self.current_user_id, self.user_id)
            if result and result.get('success'):
                QMessageBox.information(self, "Friend Request", "Request sent!")
                self.friend_btn.setEnabled(False)
                self.friend_btn.setText("Request Sent")
            else:
                msg = (result or {}).get('message', 'Failed to send friend request')
                QMessageBox.warning(self, "Friend Request", msg)
        except Exception as e:
            logger.debug(f"Friend request failed: {e}")


