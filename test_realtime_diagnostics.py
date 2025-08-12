import unittest
import logging


class TestRealtimeDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        from trackpro.database.supabase_client import get_supabase_client
        cls.client = get_supabase_client()
        from trackpro.community.community_manager import CommunityManager
        cls.mgr = CommunityManager()

    def test_001_log_client_capabilities(self):
        c = self.client
        self.assertIsNotNone(c, "Supabase client missing")
        has_client_channel = hasattr(c, 'channel')
        has_rt_channel = hasattr(getattr(c, 'realtime', None), 'channel')
        logging.info(f"client.channel={has_client_channel}, client.realtime.channel={has_rt_channel}, type={type(c)}")
        # not asserting true; just logging

    def test_002_official_bind_returns_bool(self):
        ok = self.mgr._bind_realtime_single_channel()
        logging.info(f"_bind_realtime_single_channel returned: {ok}")
        # We expect False on SyncClient when unsupported

    def test_003_direct_ws_join_flag(self):
        # Ensure direct WS join flag flips to True after starting fallback
        try:
            self.mgr._start_direct_realtime_fallback()
        except Exception:
            pass
        # Give it a moment to receive join ack
        import time
        time.sleep(1.0)
        joined = bool(getattr(self.mgr, '_direct_rt_joined', False))
        logging.info(f"_direct_rt_joined={joined}")
        # Not asserting; diagnostic only


if __name__ == '__main__':
    unittest.main()


