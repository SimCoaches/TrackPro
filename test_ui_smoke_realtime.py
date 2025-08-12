import unittest
import time


class TestUISmokeRealtime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Minimal Qt app
        try:
            from PyQt6.QtWidgets import QApplication
        except Exception:
            from PyQt6.QtCore import QCoreApplication as QApplication
        cls._app = QApplication.instance() or QApplication([])

        # Import UI page and manager
        from trackpro.ui.pages.community.community_page import CommunityPage
        from trackpro.community.community_manager import CommunityManager
        cls.mgr = CommunityManager()
        cls.page = CommunityPage()
        # Ensure signals connected
        cls.page.community_manager = cls.mgr

        # Auth user
        from trackpro.database.supabase_client import get_supabase_client
        client = get_supabase_client()
        user_resp = client.auth.get_user() if client else None
        if not (user_resp and getattr(user_resp, 'user', None)):
            raise unittest.SkipTest("No authenticated session for UI realtime test")
        cls.user_id = user_resp.user.id
        cls.mgr.set_current_user(cls.user_id)

        # Pick channel
        channels = cls.mgr.get_channels() or []
        if not channels:
            raise unittest.SkipTest("No channels found")
        public = [c for c in channels if not c.get('is_private', False)]
        cls.channel_id = (public[0]['channel_id'] if public else channels[0]['channel_id'])
        cls.page.current_channel = cls.channel_id

    def test_ui_receives_message(self):
        received = {'ok': False}
        tag = f"[ui-smoke-{int(time.time())}]"

        def on_msg(msg):
            if tag in (msg or {}).get('content', ''):
                received['ok'] = True

        self.mgr.message_received.connect(on_msg)
        ok = self.mgr.send_message(self.channel_id, f"hello ui {tag}")
        self.assertTrue(ok)

        deadline = time.time() + 10
        while time.time() < deadline and not received['ok']:
            try:
                self._app.processEvents()
            except Exception:
                pass
            time.sleep(0.05)

        self.assertTrue(received['ok'], "CommunityPage did not see realtime message in time")


if __name__ == '__main__':
    unittest.main()


