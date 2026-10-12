"""原生窗口控制，与记账逻辑隔离。"""
import threading


class WindowControls:
    def __init__(self):
        self._window = None
        self._maximized = False
        self._lock = threading.Lock()

    def bind(self, window):
        self._window = window
        window.events.maximized += self._on_maximized
        window.events.restored += self._on_restored

    def _on_maximized(self):
        self._maximized = True

    def _on_restored(self):
        self._maximized = False

    def minimize(self):
        self._window.minimize()

    def toggle_maximize(self):
        with self._lock:
            desired = not self._maximized
            if not desired:
                self._window.restore()
            else:
                self._window.maximize()
            self._maximized = desired
            return {"maximized": desired}

    def close(self):
        self._window.destroy()
