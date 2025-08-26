from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import pyqtSignal, pyqtProperty


class UserIconButton(QPushButton):
    onlineChanged = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._online = False
        self.setProperty("online", False)
        self.setCheckable(True)

    def getOnline(self) -> bool:
        return self._online

    def setOnline(self, value: bool):
        if self._online == value:
            return
        self._online = value
        self.setProperty("online", value)
        # Update per-instance style so collapsed icons show a blue outline when online
        try:
            if value:
                self.setStyleSheet("UserIconButton { background: transparent; border: 2px solid #3a8bff; border-radius: 16px; padding: 0px; }")
            else:
                self.setStyleSheet("UserIconButton { background: transparent; border: 2px solid transparent; border-radius: 16px; padding: 0px; }")
        except Exception:
            pass
        try:
            self.style().unpolish(self)
            self.style().polish(self)
        except Exception:
            pass
        self.update()
        self.onlineChanged.emit(value)

    online = pyqtProperty(bool, fget=getOnline, fset=setOnline, notify=onlineChanged)


