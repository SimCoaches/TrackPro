from PyQt6.QtCore import QObject, pyqtSignal, QByteArray
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard(QObject):
    messageReceived = pyqtSignal(str)

    def __init__(self, name: str = "trackpro_single_instance", parent=None):
        super().__init__(parent)
        self._name = name
        self._server = None

    def is_primary(self) -> bool:
        # Try to create the server; if binding fails, another instance is running
        self._server = QLocalServer(self)
        # Clean up any stale socket files on Unix-like systems
        try:
            QLocalServer.removeServer(self._name)
        except Exception:
            pass
        if not self._server.listen(self._name):
            return False
        self._server.newConnection.connect(self._on_new_connection)
        return True

    def _on_new_connection(self):
        sock = self._server.nextPendingConnection()
        if not sock:
            return
        sock.readyRead.connect(lambda s=sock: self._read_message(s))

    def _read_message(self, sock: QLocalSocket):
        try:
            data: QByteArray = sock.readAll()
            msg = bytes(data).decode("utf-8", errors="ignore")
            if msg:
                self.messageReceived.emit(msg)
        finally:
            sock.disconnectFromServer()

    @staticmethod
    def signal_secondary(name: str = "trackpro_single_instance", message: str = "raise") -> bool:
        sock = QLocalSocket()
        sock.connectToServer(name)
        if not sock.waitForConnected(300):
            return False
        try:
            sock.write(message.encode("utf-8"))
            sock.flush()
            sock.waitForBytesWritten(200)
        finally:
            sock.disconnectFromServer()
        return True


