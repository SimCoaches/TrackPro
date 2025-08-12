import unittest
import logging


class TestRealtimeSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        from trackpro.database.supabase_client import get_supabase_client
        cls.client = get_supabase_client()

    def test_001_client_initialized(self):
        self.assertIsNotNone(self.client, "Supabase client is None")

    def test_002_has_realtime_api(self):
        has_client_channel = hasattr(self.client, 'channel')
        has_rt = hasattr(getattr(self.client, 'realtime', None), 'channel')
        self.assertTrue(
            has_client_channel or has_rt,
            f"No realtime channel API exposed. client.channel={has_client_channel}, client.realtime.channel={has_rt}"
        )

    def test_003_bind_and_subscribe_via_manager(self):
        # Use CommunityManager which contains fallback logic for sync client
        from trackpro.community.community_manager import CommunityManager
        mgr = CommunityManager()
        # Force refresh to try realtime binding
        mgr.refresh_realtime()
        # Either realtime active or polling fallback must be running
        self.assertTrue(
            getattr(mgr, 'is_realtime_active', False) or getattr(mgr, '_polling_timer', None),
            "Neither realtime nor polling fallback is active after refresh"
        )


if __name__ == "__main__":
    unittest.main()


