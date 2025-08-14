import unittest
import sys

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer


class CommunityRealtimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure a Qt application exists
        if QCoreApplication.instance() is None:
            cls._app = QCoreApplication(sys.argv)
        else:
            cls._app = QCoreApplication.instance()

    def setUp(self):
        # Reset singleton to ensure clean state per test
        from trackpro.community.community_manager import CommunityManager
        CommunityManager.reset_instance()
        self.cm = CommunityManager()

    def _spin_events(self, ms=50):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def test_message_signal_emits_on_insert_poll_payload(self):
        received = []
        self.cm.message_received.connect(lambda m: received.append(m))

        payload = {"new": {"channel_id": "test-channel", "content": "hello"}, "_source": "poll"}
        # Invoke handler directly; should emit on UI thread via QTimer.singleShot
        self.cm._on_message_inserted(payload)
        self._spin_events(50)

        self.assertTrue(received, "Expected message_received to be emitted")
        self.assertEqual(received[0].get("content"), "hello")
        self.assertEqual(received[0].get("channel_id"), "test-channel")

    def test_health_monitor_started(self):
        # Health monitor should create a reconnect timer
        has_timer = hasattr(self.cm, "_reconnect_timer") and self.cm._reconnect_timer is not None
        self.assertTrue(has_timer, "Expected realtime health monitor timer to be initialized")


if __name__ == "__main__":
    unittest.main(verbosity=2)


