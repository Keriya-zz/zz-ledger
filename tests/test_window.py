import unittest
from zzledger.window import WindowControls


class Event:
    def __init__(self): self.callbacks = []
    def __iadd__(self, callback): self.callbacks.append(callback); return self
    def emit(self):
        for callback in self.callbacks: callback()


class FakeWindow:
    def __init__(self):
        self.events = type('Events', (), {'maximized': Event(), 'restored': Event(), 'before_show': Event(), 'shown': Event()})()
        self.actions = []
    def maximize(self): self.actions.append('maximize'); self.events.maximized.emit()
    def restore(self): self.actions.append('restore'); self.events.restored.emit()
    def minimize(self): self.actions.append('minimize')
    def destroy(self): self.actions.append('close')


class WindowTests(unittest.TestCase):
    def test_toggle_and_external_restore(self):
        api = WindowControls(); window = FakeWindow(); api.bind(window)
        self.assertEqual(api.toggle_maximize(), {'maximized': True})
        self.assertEqual(api.toggle_maximize(), {'maximized': False})
        window.maximize()
        self.assertEqual(api.toggle_maximize(), {'maximized': False})
        api.minimize(); api.close()
        self.assertEqual(window.actions[-2:], ['minimize', 'close'])


if __name__ == '__main__': unittest.main()
