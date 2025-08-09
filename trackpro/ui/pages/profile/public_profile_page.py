import os
import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QBrush, QPen
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
from ....community.private_messaging_widget import PrivateConversationWidget
from ....community.community_manager import CommunityManager

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
        # Message button is not used on public page layout anymore
        self.message_btn.setVisible(False)
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

        # Content row: left column (bio) + right column (DM panel)
        self.content_row = QHBoxLayout()
        self.content_row.setContentsMargins(12, 8, 12, 12)
        self.content_row.setSpacing(12)
        self.container_layout.addLayout(self.content_row)

        # Left: Bio section
        self.left_col = QVBoxLayout()
        self.left_col.setContentsMargins(0, 0, 0, 0)
        self.left_col.setSpacing(12)
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
        # Public page is display-only; hide edit controls by default
        self.edit_bio_btn.setVisible(False)
        self.save_bio_btn.setVisible(False)
        self.bio_actions.addWidget(self.edit_bio_btn)
        self.bio_actions.addWidget(self.save_bio_btn)
        self.bio_actions.addStretch()
        bio_layout.addLayout(self.bio_actions)
        self.left_col.addWidget(bio_card)

        # iRacing stats card (public display)
        self.iracing_card = QFrame()
        self.iracing_card.setObjectName("IRacingCard")
        self.iracing_card.setStyleSheet(
            "QFrame#IRacingCard { background-color: #1e1e1e; border: 1px solid #2d2d2d; border-radius: 8px; }"
        )
        self.iracing_layout = QVBoxLayout(self.iracing_card)
        self.iracing_layout.setContentsMargins(16, 16, 16, 16)

        ir_title = QLabel("iRacing")
        ir_title.setObjectName("SectionTitle")
        self.iracing_layout.addWidget(ir_title)

        from PyQt6.QtWidgets import QFormLayout
        self.iracing_form = QFormLayout()
        self.iracing_form.setContentsMargins(0, 8, 0, 0)

        def make_label():
            lbl = QLabel("")
            lbl.setStyleSheet("color: #eaeaea;")
            return lbl

        self.iracing_labels = {
            "road_ir": make_label(),
            "oval_ir": make_label(),
            "dirt_road_ir": make_label(),
            "dirt_oval_ir": make_label(),
            "road_sr": make_label(),
            "oval_sr": make_label(),
            "dirt_road_sr": make_label(),
            "dirt_oval_sr": make_label(),
            "licenses": make_label(),
            "wins": make_label(),
            "starts": make_label(),
            "win_rate": make_label(),
            "last_updated": make_label(),
        }

        self.iracing_form.addRow("Road iRating:", self.iracing_labels["road_ir"])
        self.iracing_form.addRow("Oval iRating:", self.iracing_labels["oval_ir"])
        self.iracing_form.addRow("Dirt Road iRating:", self.iracing_labels["dirt_road_ir"])
        self.iracing_form.addRow("Dirt Oval iRating:", self.iracing_labels["dirt_oval_ir"])
        self.iracing_form.addRow("Road SR:", self.iracing_labels["road_sr"])
        self.iracing_form.addRow("Oval SR:", self.iracing_labels["oval_sr"])
        self.iracing_form.addRow("Dirt Road SR:", self.iracing_labels["dirt_road_sr"])
        self.iracing_form.addRow("Dirt Oval SR:", self.iracing_labels["dirt_oval_sr"])
        self.iracing_form.addRow("Licenses:", self.iracing_labels["licenses"])
        self.iracing_form.addRow("Wins:", self.iracing_labels["wins"])
        self.iracing_form.addRow("Starts:", self.iracing_labels["starts"])
        self.iracing_form.addRow("Win Rate:", self.iracing_labels["win_rate"])
        self.iracing_form.addRow("Last Updated:", self.iracing_labels["last_updated"])

        self.iracing_layout.addLayout(self.iracing_form)

        # Owner-only refresh button
        self.refresh_iracing_btn = QPushButton("Refresh iRacing Data")
        self.refresh_iracing_btn.setProperty("class", "Secondary")
        self.refresh_iracing_btn.setFixedHeight(30)
        self.refresh_iracing_btn.clicked.connect(self._refresh_iracing_data)
        self.refresh_iracing_btn.setVisible(False)
        self.iracing_layout.addWidget(self.refresh_iracing_btn)

        # Owner-only link button (preferred secure flow)
        self.link_iracing_btn = QPushButton("Link iRacing")
        self.link_iracing_btn.setProperty("class", "Secondary")
        self.link_iracing_btn.setFixedHeight(30)
        self.link_iracing_btn.clicked.connect(self._link_iracing)
        self.link_iracing_btn.setVisible(False)
        self.iracing_layout.addWidget(self.link_iracing_btn)

        self.left_col.addWidget(self.iracing_card)
        self.left_col.addStretch()
        self.content_row.addLayout(self.left_col, 1)

        # Right: DM panel (conversation with this user)
        self.dm_panel = QFrame()
        self.dm_panel.setObjectName("DmPanel")
        self.dm_panel.setStyleSheet("QFrame#DmPanel { background-color: #1e1e1e; border: 1px solid #2d2d2d; border-radius: 8px; }")
        self.dm_layout = QVBoxLayout(self.dm_panel)
        self.dm_layout.setContentsMargins(0, 0, 0, 0)
        self.dm_layout.setSpacing(0)
        # Placeholder header
        self.dm_header = QLabel("Direct Messages")
        self.dm_header.setStyleSheet("color: #ffffff; font-weight: 700; padding: 10px 12px; background: #252525; border-bottom: 1px solid #2d2d2d;")
        self.dm_layout.addWidget(self.dm_header)
        # Container for conversation widget
        self.dm_conversation_widget: PrivateConversationWidget | None = None
        self.content_row.addWidget(self.dm_panel, 2)

        # Hook up banner click to upload when owner
        self.banner.mousePressEvent = self._on_banner_click
        
        # Initial friend button state will be set when profile loads

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
        data = None
        try:
            from ....database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if client:
                # 1) Prefer public view that contains banner_url
                try:
                    resp = client.from_("public_user_profiles").select(
                        "user_id, username, display_name, avatar_url, bio, banner_url"
                    ).eq("user_id", self.user_id).single().execute()
                    data = resp.data
                except Exception:
                    data = None
                # 2) Fallback to user_profiles without banner_url (column may not exist)
                if not data:
                    try:
                        resp = client.from_("user_profiles").select(
                            "user_id, username, display_name, avatar_url, bio"
                        ).eq("user_id", self.user_id).single().execute()
                        data = resp.data
                    except Exception:
                        data = None

            # Apply profile fields safely
            self.profile = data or {}
            display_name = self.profile.get("display_name") or self.profile.get("username") or "User"
            username = self.profile.get("username") or ""
            self.display_name_label.setText(display_name)
            self.username_label.setText(f"@{username}" if username else "")

            # Avatar (fallback to bucket if missing URL)
            try:
                AvatarManager.instance().set_label_avatar(
                    self.avatar_label,
                    self.profile.get("avatar_url"),
                    display_name,
                    size=96,
                )
                if not self.profile.get("avatar_url"):
                    self._try_load_avatar_from_bucket(display_name)
            except Exception:
                pass

            # Banner (only if we actually have a URL)
            try:
                banner_url = self.profile.get("banner_url")
                if banner_url:
                    self._set_banner_from_url(banner_url)
                else:
                    self.banner.setText("Click to add a banner")
                    self.banner.setStyleSheet(self.banner.styleSheet() + "; color: #c8c8c8;")
            except Exception:
                pass

            # Bio display-only
            try:
                bio_text = self.profile.get("bio") or "No bio yet."
                self.bio_view.setText(bio_text)
            except Exception:
                pass

            # Public page controls
            try:
                is_owner = (self.current_user_id == self.user_id) and bool(self.current_user_id)
                self.edit_bio_btn.setVisible(False)
                self.save_bio_btn.setVisible(False)
                self.message_btn.setVisible(False)
                if is_owner:
                    self.friend_btn.setEnabled(False)
                    self.friend_btn.setText("It's you")
                    # Allow the owner to refresh their iRacing data
                    self.refresh_iracing_btn.setVisible(True)
                    self.link_iracing_btn.setVisible(True)
                else:
                    # Update friend button to show Friends ✓ or Add Friend
                    self._update_friend_button_state()
                    self.refresh_iracing_btn.setVisible(False)
                    self.link_iracing_btn.setVisible(False)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error loading public profile: {e}")
        finally:
            # Always prepare DM panel so messages appear without extra clicks
            try:
                self._prepare_dm_panel()
            except Exception:
                pass

            # Load iRacing snapshot for display
            try:
                self._load_iracing_snapshot()
            except Exception as _e:
                pass

    def _format_sr_with_class(self, sr_value: float, license_class: Optional[str]) -> str:
        try:
            if sr_value is None:
                return "-"
            sr = float(sr_value)
            cls = (license_class or "").strip()
            return f"{cls} {sr:.2f}" if cls else f"{sr:.2f}"
        except Exception:
            return "-"

    def _load_iracing_snapshot(self) -> None:
        """Load iRacing stats snapshot from Supabase if available, else show placeholders."""
        # Defaults
        for key, lbl in self.iracing_labels.items():
            try:
                lbl.setText("-")
            except Exception:
                pass

        try:
            from ....database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client or not self.user_id:
                return

            data = None
            # Prefer a public view if present
            try:
                resp = client.from_("public_user_iracing_snapshot").select("*").eq("user_id", self.user_id).single().execute()
                data = getattr(resp, "data", None)
            except Exception:
                data = None
            if not data:
                try:
                    resp = client.from_("user_iracing_snapshot").select("*").eq("user_id", self.user_id).single().execute()
                    data = getattr(resp, "data", None)
                except Exception:
                    data = None

            if not data:
                # No snapshot yet
                self.iracing_labels["last_updated"].setText("No data")
                return

            # Populate labels safely
            get = lambda k, d=None: (data.get(k) if isinstance(data, dict) else None) if d is None else (data.get(k, d) if isinstance(data, dict) else d)

            self.iracing_labels["road_ir"].setText(str(get("road_irating", "-")))
            self.iracing_labels["oval_ir"].setText(str(get("oval_irating", "-")))
            self.iracing_labels["dirt_road_ir"].setText(str(get("dirt_road_irating", "-")))
            self.iracing_labels["dirt_oval_ir"].setText(str(get("dirt_oval_irating", "-")))

            self.iracing_labels["road_sr"].setText(self._format_sr_with_class(get("road_sr"), get("road_license")))
            self.iracing_labels["oval_sr"].setText(self._format_sr_with_class(get("oval_sr"), get("oval_license")))
            self.iracing_labels["dirt_road_sr"].setText(self._format_sr_with_class(get("dirt_road_sr"), get("dirt_road_license")))
            self.iracing_labels["dirt_oval_sr"].setText(self._format_sr_with_class(get("dirt_oval_sr"), get("dirt_oval_license")))

            licenses = []
            for k in ("road_license", "oval_license", "dirt_road_license", "dirt_oval_license"):
                val = get(k)
                if val:
                    licenses.append(val)
            self.iracing_labels["licenses"].setText(", ".join(licenses) if licenses else "-")

            wins = get("wins", None)
            starts = get("starts", None)
            self.iracing_labels["wins"].setText(str(wins) if wins is not None else "-")
            self.iracing_labels["starts"].setText(str(starts) if starts is not None else "-")

            try:
                if wins is not None and starts and int(starts) > 0:
                    rate = (float(wins) / float(starts)) * 100.0
                    self.iracing_labels["win_rate"].setText(f"{rate:.1f}%")
                else:
                    self.iracing_labels["win_rate"].setText("-")
            except Exception:
                self.iracing_labels["win_rate"].setText("-")

            self.iracing_labels["last_updated"].setText(str(get("last_updated", "-")))
        except Exception as e:
            logger.debug(f"Could not load iRacing snapshot: {e}")

    def _refresh_iracing_data(self) -> None:
        """Owner-only: attempt to fetch iRacing data via Data API using env credentials and update UI.

        This does not store credentials and will best-effort upsert to Supabase if a table exists.
        """
        try:
            is_owner = (self.current_user_id == self.user_id) and bool(self.current_user_id)
            if not is_owner:
                return

            import os
            import requests
            # Prefer full cookie set if available
            cookies = self._load_iracing_cookies() or {}
            if not cookies:
                # Back-compat: single cookie path
                session_cookie = getattr(self, "_iracing_session_cookie", None) or self._load_iracing_session_cookie()
                try:
                    main_window = self.window()
                    if hasattr(main_window, "_iracing_session_cookie"):
                        session_cookie = getattr(main_window, "_iracing_session_cookie") or session_cookie
                except Exception:
                    pass
                if session_cookie:
                    cookies = {"irsso_membersv2": session_cookie}
            if not cookies:
                QMessageBox.information(self, "iRacing", "Link your iRacing account first (no password stored). Click 'Link iRacing'.")
                return

            session = requests.Session()
            session.headers.update({"User-Agent": "TrackPro/IRacingLink"})
            # Attach cookies for both domains used by iRacing
            try:
                for k, v in cookies.items():
                    try:
                        session.cookies.set(k, v, domain="members-ng.iracing.com")
                        session.cookies.set(k, v, domain=".iracing.com")
                    except Exception:
                        pass
            except Exception:
                pass

            def fetch_iracing_json(data_url: str, timeout: float = 12.0):
                """GET Data API endpoint; follow 'link' indirection if present."""
                try:
                    r = session.get(data_url, timeout=timeout)
                    if not r.ok:
                        return None
                    content_type = r.headers.get("Content-Type", "")
                    data = r.json() if content_type.startswith("application/json") else None
                    if isinstance(data, dict) and data.get("link"):
                        link_resp = session.get(data["link"], timeout=timeout)
                        if link_resp.ok and link_resp.headers.get("Content-Type", "").startswith("application/json"):
                            return link_resp.json()
                        return None
                    return data
                except Exception:
                    return None

            # Fetch profile summary (includes licenses)
            summary = fetch_iracing_json("https://members-ng.iracing.com/data/member/summary") or {}

            # Fetch career stats (wins/starts)
            career = fetch_iracing_json("https://members-ng.iracing.com/data/stats/member/career") or {}

            # Map into snapshot dict (best-effort keys)
            snap = {}
            try:
                # Some responses embed category arrays; normalize
                licenses = summary.get("licenses") or summary.get("licenses_info") or {}
                if isinstance(licenses, list):
                    # Convert list of {category, ...} to dict
                    _dict = {}
                    for item in licenses:
                        cat = (item.get("category") or item.get("category_name") or "").lower()
                        _dict[cat] = item
                    licenses = _dict
                # Per category mappings (keys may vary; guard with get)
                for cat_key, prefix in (
                    ("road", "road"),
                    ("oval", "oval"),
                    ("dirt_road", "dirt_road"),
                    ("dirt_oval", "dirt_oval"),
                ):
                    lic = (licenses.get(cat_key) if isinstance(licenses, dict) else None) or {}
                    snap[f"{prefix}_irating"] = lic.get("irating") or lic.get("iRating") or lic.get("i_rating")
                    snap[f"{prefix}_sr"] = lic.get("safety_rating") or lic.get("safetyRating") or lic.get("sr")
                    snap[f"{prefix}_license"] = lic.get("license_level") or lic.get("license") or lic.get("class")
            except Exception:
                pass

            try:
                totals = career.get("career") or career.get("overall") or career
                if isinstance(totals, list):
                    # Pick overall or first
                    totals = next((x for x in totals if (x.get("category") or "").lower() == "overall"), totals[0] if totals else {})
                snap["wins"] = (totals or {}).get("wins")
                snap["starts"] = (totals or {}).get("starts") or (totals or {}).get("races")
            except Exception:
                pass

            # Update UI immediately
            def set_opt(k, v):
                if v is None:
                    return
                if k in ("road_sr", "oval_sr", "dirt_road_sr", "dirt_oval_sr"):
                    # License text requires both SR and class; try to find class
                    cls_key = k.replace("_sr", "_license")
                    cls_val = snap.get(cls_key)
                    self.iracing_labels[k].setText(self._format_sr_with_class(v, cls_val))
                elif k in self.iracing_labels:
                    self.iracing_labels[k].setText(str(v))

            mapping = {
                "road_ir": snap.get("road_irating"),
                "oval_ir": snap.get("oval_irating"),
                "dirt_road_ir": snap.get("dirt_road_irating"),
                "dirt_oval_ir": snap.get("dirt_oval_irating"),
                "road_sr": snap.get("road_sr"),
                "oval_sr": snap.get("oval_sr"),
                "dirt_road_sr": snap.get("dirt_road_sr"),
                "dirt_oval_sr": snap.get("dirt_oval_sr"),
                "wins": snap.get("wins"),
                "starts": snap.get("starts"),
            }
            for k, v in mapping.items():
                set_opt(k, v)

            # Licenses combined text
            licenses_list = []
            for key in ("road_license", "oval_license", "dirt_road_license", "dirt_oval_license"):
                if snap.get(key):
                    licenses_list.append(str(snap[key]))
            if licenses_list:
                self.iracing_labels["licenses"].setText(", ".join(licenses_list))

            # Win rate
            try:
                wins = snap.get("wins")
                starts = snap.get("starts")
                if wins is not None and starts and int(starts) > 0:
                    rate = (float(wins) / float(starts)) * 100.0
                    self.iracing_labels["win_rate"].setText(f"{rate:.1f}%")
            except Exception:
                pass

            from datetime import datetime
            self.iracing_labels["last_updated"].setText(datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

            # Best-effort upsert to Supabase if table exists
            try:
                from ....database.supabase_client import get_supabase_client
                client = get_supabase_client()
                if client:
                    payload = dict(snap)
                    payload["user_id"] = self.user_id
                    payload["last_updated"] = datetime.utcnow().isoformat() + "Z"
                    try:
                        client.from_("user_iracing_snapshot").upsert(payload, on_conflict="user_id").execute()
                    except Exception:
                        # Ignore if table not present or RLS blocks
                        pass
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error refreshing iRacing data: {e}")
            QMessageBox.warning(self, "iRacing", "Could not refresh iRacing data.")

    def _link_iracing(self) -> None:
        """Open a secure web view to members-ng.iracing.com for user login. We only capture the session cookie; we never see or store the password."""
        try:
            is_owner = (self.current_user_id == self.user_id) and bool(self.current_user_id)
            if not is_owner:
                return

            # Lazy import to avoid hard dependency at import time
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            from PyQt6.QtWidgets import QDialog, QVBoxLayout

            dialog = QDialog(self)
            dialog.setWindowTitle("Link iRacing Account")
            layout = QVBoxLayout(dialog)
            web = QWebEngineView(dialog)
            layout.addWidget(web)

            # Accumulate all iRacing cookies; Data API sometimes needs multiple
            self._iracing_cookies = getattr(self, "_iracing_cookies", {})

            def handle_cookie_added(cookie):
                try:
                    name = bytes(cookie.name()).decode("utf-8", errors="ignore")
                    value = bytes(cookie.value()).decode("utf-8", errors="ignore")
                    domain = cookie.domain()
                    if domain and ("iracing.com" in domain):
                        self._iracing_cookies[name] = value
                        # Save to main window for global reuse
                        try:
                            main_window = self.window()
                            if main_window:
                                setattr(main_window, "_iracing_session_cookie", self._iracing_cookies.get("authtoken") or self._iracing_cookies.get("irsso_membersv2") or value)
                                setattr(main_window, "_iracing_cookies", dict(self._iracing_cookies))
                        except Exception:
                            pass
                        # Heuristic: when we have an auth-bearing cookie, attempt verification
                        if name.lower() in ("authtoken", "irsso_membersv2", "irsso", "iracing_ui"):
                            # Persist securely for future app sessions
                            try:
                                self._save_iracing_cookies(self._iracing_cookies)
                            except Exception:
                                pass
                            # Best-effort: verify link and persist identity
                            try:
                                if self._persist_iracing_link_identity(self._iracing_cookies):
                                    dialog.accept()
                                    QMessageBox.information(self, "iRacing", "iRacing linked. You can now refresh iRacing data.")
                            except Exception:
                                pass
                except Exception:
                    pass

            # Connect to cookie store
            profile = web.page().profile()
            try:
                cookie_store = profile.cookieStore()
                cookie_store.cookieAdded.connect(handle_cookie_added)
            except Exception:
                pass

            # Navigate to iRacing members login page (must use QUrl)
            from PyQt6.QtCore import QUrl
            web.load(QUrl("https://members-ng.iracing.com/"))
            dialog.resize(900, 700)
            dialog.exec()

        except Exception as e:
            logger.error(f"iRacing link error: {e}")
            QMessageBox.warning(self, "iRacing", "Could not open iRacing login.")

    def _save_iracing_cookies(self, cookies: dict) -> None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            ir = data.get("iracing", {})
            ir.update({
                "cookies": cookies,
                "saved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z"
            })
            data["iracing"] = ir
            ssm.save_session(data)
        except Exception as e:
            logger.debug(f"Could not save iRacing cookie: {e}")

    def _load_iracing_session_cookie(self) -> str | None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            ir = data.get("iracing") or {}
            # Backward compatibility: return single cookie if present
            return (ir.get("cookies") or {}).get("authtoken") or (ir.get("cookies") or {}).get("irsso_membersv2") or ir.get("session_cookie")
        except Exception:
            return None

    def _load_iracing_cookies(self) -> dict | None:
        try:
            from ....auth.secure_session import SecureSessionManager
            ssm = SecureSessionManager("TrackPro")
            data = ssm.load_session() or {}
            return (data.get("iracing") or {}).get("cookies") or None
        except Exception:
            return None

    def _persist_iracing_link_identity(self, cookies_source) -> bool:
        """Fetch member identity and persist link in Supabase if a connections table exists."""
        try:
            import requests
            session = requests.Session()
            session.headers.update({"User-Agent": "TrackPro/IRacingLink"})
            # Accept either a cookie string or dict of cookies
            if isinstance(cookies_source, dict):
                for k, v in cookies_source.items():
                    session.cookies.set(k, v, domain="members-ng.iracing.com")
            else:
                session.cookies.set("irsso_membersv2", str(cookies_source), domain="members-ng.iracing.com")
            # Fetch summary to get cust_id/username
            def fetch(url):
                r = session.get(url, timeout=12)
                if not r.ok:
                    return None
                j = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
                if isinstance(j, dict) and j.get("link"):
                    rr = session.get(j["link"], timeout=12)
                    if rr.ok and rr.headers.get("Content-Type", "").startswith("application/json"):
                        return rr.json()
                    return None
                return j
            summary = fetch("https://members-ng.iracing.com/data/member/summary") or {}
            cust_id = summary.get("cust_id") or summary.get("customer_id") or None
            username = summary.get("display_name") or summary.get("member_name") or None
            if not cust_id:
                return False
            from ....database.supabase_client import get_supabase_client
            supa = get_supabase_client()
            if not supa:
                return True
            payload = {
                "user_id": self.user_id,
                "provider": "iracing",
                "external_id": str(cust_id),
                "username": username,
                "linked_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            }
            try:
                supa.from_("user_connections").upsert(payload, on_conflict="user_id,provider").execute()
            except Exception:
                # If the table doesn't exist, ignore
                pass
            return True
        except Exception as e:
            logger.debug(f"Persist link identity failed: {e}")
            return False

    def _update_friend_button_state(self) -> None:
        try:
            if not self.current_user_id or not self.user_id or self.current_user_id == self.user_id:
                return
            from ....social.friends_manager import FriendsManager, FriendshipStatus
            fm = FriendsManager()
            fr = fm.get_friendship_status(self.current_user_id, self.user_id)
            is_friends = bool(fr and fr.get('status') == FriendshipStatus.ACCEPTED.value)
            if is_friends:
                self.friend_btn.setText("Friends  ✓")
                self.friend_btn.setProperty("class", "Secondary")
                self.friend_btn.setStyleSheet(self.friend_btn.styleSheet() + "; background-color: #2d3e2b; color: #a6e3a1;")
                try:
                    self.friend_btn.clicked.disconnect()
                except Exception:
                    pass
                self.friend_btn.clicked.connect(self._confirm_unfriend)
            else:
                self.friend_btn.setText("Add Friend")
                try:
                    self.friend_btn.clicked.disconnect()
                except Exception:
                    pass
                self.friend_btn.clicked.connect(self._send_friend_request)
        except Exception:
            pass

    def _confirm_unfriend(self) -> None:
        try:
            if not self.current_user_id or not self.user_id:
                return
            name = self.profile.get('display_name') or self.profile.get('username') or 'this user'
            reply = QMessageBox.question(
                self,
                "Unfriend",
                f"Are you sure you want to unfriend {name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                from ....social.friends_manager import FriendsManager
                fm = FriendsManager()
                res = fm.remove_friend(self.current_user_id, self.user_id)
                if res.get('success'):
                    QMessageBox.information(self, "Unfriend", "Friend removed.")
                    self._update_friend_button_state()
                    # After unfriend, DMs become disabled until friended again
                    self._set_dm_disabled_state(True, reason="Add as friend to message")
                else:
                    QMessageBox.warning(self, "Unfriend", res.get('message') or "Failed to remove friend.")
        except Exception as e:
            logger.debug(f"Unfriend failed: {e}")

    def _try_load_avatar_from_bucket(self, display_name: str) -> None:
        """Best-effort: find avatar in Supabase 'avatars' bucket and show it.
        Also updates `user_profiles.avatar_url` if we discover a public URL.
        """
        try:
            from ....database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client or not self.user_id:
                return
            # List files under avatars/<user_id>/
            try:
                files = client.storage.from_("avatars").list(self.user_id)
            except Exception:
                files = None
            if not files:
                return
            # Pick the most recent-looking or first file
            first = files[0]
            name = first.get('name') if isinstance(first, dict) else getattr(first, 'name', None)
            if not name:
                return
            storage_path = f"{self.user_id}/{name}"
            public_url = client.storage.from_("avatars").get_public_url(storage_path)
            if not public_url:
                return
            # Show it and persist to profile table if possible
            AvatarManager.instance().set_label_avatar(self.avatar_label, public_url, display_name, size=96)
            self.profile['avatar_url'] = public_url
            try:
                client.from_("user_profiles").update({"avatar_url": public_url}).eq("user_id", self.user_id).execute()
            except Exception:
                pass
        except Exception:
            pass

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
            # Ensure DM panel exists and focused
            if not self.dm_conversation_widget:
                self._prepare_dm_panel()
            # Focus the message input if available
            try:
                if self.dm_conversation_widget and hasattr(self.dm_conversation_widget, 'message_input'):
                    self.dm_conversation_widget.message_input.setFocus()
            except Exception:
                pass
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


    # ----------------------------
    # Direct Messages on Profile
    # ----------------------------
    def _prepare_dm_panel(self) -> None:
        try:
            # If viewing own profile, hide DM panel content
            if self.current_user_id == self.user_id:
                self._set_dm_disabled_state(True, reason="Direct Messages")
                return
            # Require authentication
            if not self.current_user_id:
                self._set_dm_disabled_state(True, reason="Sign in to message")
                return
            # Bind manager and ensure user id
            mgr = CommunityManager()
            mgr.set_current_user(self.current_user_id)
            # Connect realtime once
            try:
                if not hasattr(self, '_dm_rt_connected'):
                    mgr.private_message_received.connect(self._on_realtime_private_message)
                    self._dm_rt_connected = True
            except Exception:
                pass
            # Get or create conversation with this profile user
            conversation_id = mgr.get_or_create_conversation(self.user_id)
            if not conversation_id:
                # No conversation; enforce friendship
                self._set_dm_disabled_state(True, reason="Add as friend to message")
                return
            conversation_data = mgr.get_conversation_data(conversation_id)
            if not conversation_data:
                self._set_dm_disabled_state(True, reason="Add as friend to message")
                return
            # Build/replace conversation widget
            if self.dm_conversation_widget:
                try:
                    self.dm_conversation_widget.setParent(None)
                except Exception:
                    pass
            self.dm_conversation_widget = PrivateConversationWidget(conversation_data, parent=self.dm_panel)
            self.dm_layout.addWidget(self.dm_conversation_widget, 1)
            # Hook send
            self.dm_conversation_widget.message_sent.connect(lambda text: self._send_dm(conversation_id, text))
            # Load existing messages
            messages = mgr.get_private_messages(conversation_id) or []
            current_user_id = self.current_user_id
            for m in messages:
                is_own = bool(current_user_id and m.get('sender_id') == current_user_id)
                # Ensure basic user profile for display
                if not m.get('user_profiles'):
                    if is_own:
                        m['user_profiles'] = {'user_id': current_user_id, 'display_name': 'You', 'username': 'You', 'avatar_url': None}
                    else:
                        m['user_profiles'] = {
                            'user_id': self.user_id,
                            'display_name': self.profile.get('display_name') or self.profile.get('username') or 'User',
                            'username': self.profile.get('username'),
                            'avatar_url': self.profile.get('avatar_url'),
                        }
                self.dm_conversation_widget.add_message(m, is_own_message=is_own)
            # Ensure we land on the latest message after layout settles
            try:
                QTimer.singleShot(0, self.dm_conversation_widget.messages_list.scrollToBottom)
                QTimer.singleShot(120, self.dm_conversation_widget.messages_list.scrollToBottom)
            except Exception:
                pass
            # Mark as read and clear glow on sidebar
            mgr.mark_private_messages_as_read(conversation_id)
            self._clear_sidebar_glow_for_user(self.user_id)
        except Exception as e:
            logger.debug(f"DM panel setup failed: {e}")
            self._set_dm_disabled_state(True, reason="Direct Messages")

    def _send_dm(self, conversation_id: str, text: str) -> None:
        try:
            mgr = CommunityManager()
            mgr.set_current_user(self.current_user_id)
            mgr.send_private_message(conversation_id, text)
        except Exception:
            pass

    def _on_realtime_private_message(self, message_data: dict) -> None:
        try:
            cw = self.dm_conversation_widget
            if not cw:
                return
            if message_data.get('conversation_id') != getattr(cw, 'conversation_id', None):
                return
            is_own = bool(self.current_user_id and message_data.get('sender_id') == self.current_user_id)
            self.dm_conversation_widget.add_message(message_data, is_own_message=is_own)
            # Immediately mark messages as read and clear glow
            try:
                CommunityManager().mark_private_messages_as_read(message_data.get('conversation_id'))
            except Exception:
                pass
            self._clear_sidebar_glow_for_user(self.user_id)
        except Exception:
            pass

    def _clear_sidebar_glow_for_user(self, user_id: str) -> None:
        try:
            main_window = self.window()
            if main_window and hasattr(main_window, 'online_users_sidebar') and main_window.online_users_sidebar:
                sidebar = main_window.online_users_sidebar
                if hasattr(sidebar, 'clear_unread_glow_for_user'):
                    sidebar.clear_unread_glow_for_user(user_id)
        except Exception:
            pass

    def _set_dm_disabled_state(self, disabled: bool, reason: str = "Direct Messages") -> None:
        try:
            # Update header title
            title = reason
            self.dm_header.setText(title)
            # Replace conversation widget with an empty spacer/info when disabled
            if disabled:
                if self.dm_conversation_widget:
                    try:
                        self.dm_conversation_widget.setParent(None)
                    except Exception:
                        pass
                placeholder = QLabel("Direct messages are available for friends only.")
                placeholder.setStyleSheet("color: #9aa0a6; padding: 12px;")
                # Remove existing stretch/content if any
                while self.dm_layout.count() > 1:
                    item = self.dm_layout.takeAt(1)
                    if item and item.widget():
                        item.widget().setParent(None)
                self.dm_layout.addWidget(placeholder, 1)
            else:
                self.dm_header.setText("Direct Messages")
        except Exception:
            pass

