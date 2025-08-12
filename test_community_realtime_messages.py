import unittest
import uuid
import time
import logging


def _ensure_qapp():
    """Ensure a Qt application instance exists for signal delivery."""
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:
        from PyQt6.QtCore import QCoreApplication as QApplication  # Fallback to core app
    app = QApplication.instance()
    if app is None:
        try:
            app = QApplication([])
        except Exception:
            # As a last resort, create a core-only app
            from PyQt6.QtCore import QCoreApplication
            app = QCoreApplication([])
    return app


class TestCommunityRealtimeMessages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        # Ensure Qt app exists so CommunityManager PyQt signals can fire
        cls._app = _ensure_qapp()

        # Get supabase client and authenticated user
        from trackpro.database.supabase_client import get_supabase_client
        cls.client = get_supabase_client()
        if not cls.client:
            raise unittest.SkipTest("Supabase client not available; cannot run realtime tests")

        try:
            user_resp = cls.client.auth.get_user()
            cls.user_id = user_resp.user.id if (user_resp and getattr(user_resp, 'user', None)) else None
        except Exception:
            cls.user_id = None

        if not cls.user_id:
            raise unittest.SkipTest("No authenticated user; realtime messaging tests require login")

        # Community manager under test
        from trackpro.community.community_manager import CommunityManager
        cls.manager = CommunityManager()
        cls.manager.set_current_user(cls.user_id)

        # Pick a public text channel to avoid RLS complications
        channels = cls.manager.get_channels() or []
        if not channels:
            raise unittest.SkipTest("No community channels available to test against")
        # Prefer a non-private text channel; otherwise first channel
        public_text = [c for c in channels if (not c.get('is_private', False))]
        cls.channel_id = (public_text[0]['channel_id'] if public_text else channels[0]['channel_id'])

    def test_001_realtime_or_polling_active(self):
        # Refresh realtime binds
        try:
            self.manager.refresh_realtime()
        except Exception:
            pass

        # Assert at least one path is usable
        active = bool(getattr(self.manager, 'is_realtime_active', False))
        has_poll_timer = bool(getattr(self.manager, '_polling_timer', None))
        joined_ws = bool(getattr(self.manager, '_direct_rt_joined', False))
        self.assertTrue(active or has_poll_timer or joined_ws, "No realtime/polling path is active")

    def test_002_insert_message_emits_signal(self):
        # Connect to signal and send a tagged message
        received = {
            'hit': False,
            'payload': None,
        }

        unique_tag = f"[rt-test-{uuid.uuid4().hex[:8]}]"

        def on_message(msg):
            try:
                content = (msg or {}).get('content', '')
                if unique_tag in content:
                    received['hit'] = True
                    received['payload'] = msg
            except Exception:
                pass

        # Attach listener
        self.manager.message_received.connect(on_message)

        # Send the message via API under test
        ok = self.manager.send_message(self.channel_id, f"hello from test {unique_tag}")
        self.assertTrue(ok, "send_message returned False")

        # Process events for up to 10 seconds to allow realtime/polling delivery
        deadline = time.time() + 10.0
        while time.time() < deadline and not received['hit']:
            # Process Qt events to drive signal delivery
            try:
                self._app.processEvents()
            except Exception:
                pass
            time.sleep(0.05)

        self.assertTrue(received['hit'], "Did not receive message via realtime/polling within timeout")
        self.assertIsNotNone(received['payload'].get('channel_id'), "Received message missing channel_id")
        self.assertIsNotNone(received['payload'].get('message_id'), "Received message missing message_id")

    def test_003_sender_name_is_computed(self):
        # Validate that on realtime path we synthesize sender_name from profile data
        received = {
            'name': None,
        }
        tag = f"[rt-name-{uuid.uuid4().hex[:6]}]"

        def on_message(msg):
            content = (msg or {}).get('content', '')
            if tag in content:
                received['name'] = msg.get('sender_name')

        self.manager.message_received.connect(on_message)
        ok = self.manager.send_message(self.channel_id, f"check name {tag}")
        self.assertTrue(ok, "send_message returned False")

        deadline = time.time() + 7.0
        while time.time() < deadline and not received['name']:
            try:
                self._app.processEvents()
            except Exception:
                pass
            time.sleep(0.05)

        self.assertTrue(bool(received['name']), "sender_name was not populated on received message")


if __name__ == "__main__":
    unittest.main()


