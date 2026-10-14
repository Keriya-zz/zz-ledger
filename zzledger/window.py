"""原生窗口控制，与记账逻辑隔离。"""
import threading


class WindowControls:
    def __init__(self):
        self._window = None
        self._maximized = False
        self._lock = threading.Lock()
        self._native = None
        self._native_ready = threading.Event()

    def bind(self, window):
        self._window = window
        window.events.maximized += self._on_maximized
        window.events.restored += self._on_restored
        window.events.before_show += self._prepare_native
        window.events.shown += self._center_shown

    def _prepare_native(self):
        from .native_window import NativeWindow
        self._native = NativeWindow(self._window)

    def _center_shown(self):
        from System import Action
        if self._native:
            self._window.native.Invoke(Action(self._native.center))
            self._native_ready.set()

    def start_resize(self, direction):
        return self._native.start_resize(direction) if self._native else False

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
