"""Windows frameless chrome: retain native sizing and taskbar behaviour."""
import ctypes
from ctypes import wintypes


RESIZE_HITS = {'left': 10, 'right': 11, 'top': 12, 'top-left': 13,
               'top-right': 14, 'bottom': 15, 'bottom-left': 16, 'bottom-right': 17}
WINDOW_STYLE = 0x00C00000 | 0x00040000 | 0x00080000 | 0x00020000 | 0x00010000


def resize_hit(x, y, width, height, edge=7):
    """Client coordinates; corners take precedence over edges."""
    if not (0 <= x < width and 0 <= y < height):
        return 0
    left, right = x < edge, x >= width - edge
    top, bottom = y < edge, y >= height - edge
    if top and left: return 13
    if top and right: return 14
    if bottom and left: return 16
    if bottom and right: return 17
    if left: return 10
    if right: return 11
    if top: return 12
    if bottom: return 15
    return 0


def centered_bounds(work, width, height):
    """Physical monitor coordinates, including negative monitor origins."""
    left, top, right, bottom = work
    width, height = min(width, right-left), min(height, bottom-top)
    return left+(right-left-width)//2, top+(bottom-top-height)//2, width, height


class MonitorInfo(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]


class MinMaxInfo(ctypes.Structure):
    _fields_ = [(name, wintypes.POINT) for name in
                ('ptReserved', 'ptMaxSize', 'ptMaxPosition', 'ptMinTrackSize', 'ptMaxTrackSize')]


class NativeWindow:
    def __init__(self, window):
        self.window = window
        self.form = window.native
        from System.Windows.Forms import FormBorderStyle
        # Keep WinForms and Windows in agreement about a normal, resizable window.
        # Only its frame is hidden by NCCALCSIZE; do not remove WS_CAPTION.
        self.form.FormBorderStyle = FormBorderStyle.Sizable
        self.form.ControlBox = True
        self.form.MinimizeBox = True
        self.form.MaximizeBox = True
        self.form.ShowInTaskbar = True
        self.hwnd = self.form.Handle.ToInt64()
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.comctl = ctypes.WinDLL('comctl32', use_last_error=True)
        self._configure_api()
        self._callback = self.callback_type(self._window_proc)
        if not self.comctl.SetWindowSubclass(self.hwnd, self._callback, 1, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        # Taskbar activation/minimization needs standard overlapped-window semantics.
        style = self.user.GetWindowLongW(self.hwnd, -16)
        self.user.SetWindowLongW(self.hwnd, -16, (style | WINDOW_STYLE) & ~0x80000000)
        self.user.SetWindowPos(self.hwnd, None, 0, 0, 0, 0, 0x0027)
        self.center()

    def _configure_api(self):
        u, c = self.user, self.comctl
        self.callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND,
            wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_size_t, ctypes.c_size_t)
        c.SetWindowSubclass.argtypes = [wintypes.HWND, self.callback_type, ctypes.c_size_t, ctypes.c_size_t]
        c.SetWindowSubclass.restype = wintypes.BOOL
        c.RemoveWindowSubclass.argtypes = [wintypes.HWND, self.callback_type, ctypes.c_size_t]
        c.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
        c.DefSubclassProc.restype = ctypes.c_ssize_t
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetWindowLongW.restype = wintypes.LONG
        u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
        u.SetWindowLongW.restype = wintypes.LONG
        u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        u.SetWindowPos.restype = wintypes.BOOL
        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        u.MonitorFromPoint.restype = wintypes.HMONITOR
        u.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        u.MonitorFromWindow.restype = wintypes.HMONITOR
        u.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
        u.IsZoomed.argtypes = [wintypes.HWND]
        u.IsIconic.argtypes = [wintypes.HWND]
        u.GetDpiForWindow.argtypes = [wintypes.HWND]
        u.GetDpiForWindow.restype = wintypes.UINT
        u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
        u.SendMessageW.restype = ctypes.c_ssize_t

    def monitor_info(self, monitor=None):
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        monitor = monitor or self.user.MonitorFromWindow(self.hwnd, 2)
        if not self.user.GetMonitorInfoW(monitor, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        return info

    def rect(self):
        rect = wintypes.RECT()
        self.user.GetWindowRect(self.hwnd, ctypes.byref(rect))
        return rect

    def center(self):
        from System.Drawing import Point, Size
        from System.Windows.Forms import FormStartPosition
        # Use the primary screen consistently, independent of cursor/taskbar location.
        info = self.monitor_info(self.user.MonitorFromWindow(None, 1))
        work = info.rcWork
        self.form.StartPosition = FormStartPosition.Manual
        # MinimumSize may exceed a small screen's work area at high DPI.
        self.form.MinimumSize = Size(min(self.form.MinimumSize.Width, work.right-work.left),
                                     min(self.form.MinimumSize.Height, work.bottom-work.top))
        x, y, width, height = centered_bounds((work.left, work.top, work.right, work.bottom),
                                             self.form.Width, self.form.Height)
        self.form.Size = Size(width, height)
        self.form.Location = Point(x, y)
        self.initial_bounds = (x, y, width, height)
        self.initial_work = (work.left, work.top, work.right, work.bottom)

    def client_bounds(self):
        rect = wintypes.RECT()
        self.user.GetClientRect(self.hwnd, ctypes.byref(rect))
        origin = wintypes.POINT()
        self.user.ClientToScreen(self.hwnd, ctypes.byref(origin))
        return origin.x, origin.y, origin.x+rect.right, origin.y+rect.bottom

    def _window_proc(self, hwnd, message, wparam, lparam, subclass_id, ref_data):
        # Delegate all business and normal WinForms messages to its original proc.
        try:
            if message == 0x0083:  # WM_NCCALCSIZE
                if self.user.IsZoomed(hwnd):
                    work = self.monitor_info().rcWork
                    client = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
                    client.left, client.top = work.left, work.top
                    client.right, client.bottom = work.right, work.bottom
                return 0
            if message == 0x0084 and not self.user.IsZoomed(hwnd):  # WM_NCHITTEST
                rect = self.rect()
                x, y = ctypes.c_short(lparam & 0xffff).value, ctypes.c_short((lparam >> 16) & 0xffff).value
                hit = resize_hit(x-rect.left, y-rect.top, rect.right-rect.left, rect.bottom-rect.top,
                                 max(6, round(7*self.user.GetDpiForWindow(hwnd)/96)))
                if hit: return hit
            if message == 0x0024:  # WM_GETMINMAXINFO: maximize within the taskbar work area
                result = self.comctl.DefSubclassProc(hwnd, message, wparam, lparam)
                info = self.monitor_info()
                bounds = ctypes.cast(lparam, ctypes.POINTER(MinMaxInfo)).contents
                bounds.ptMaxPosition.x = info.rcWork.left-info.rcMonitor.left
                bounds.ptMaxPosition.y = info.rcWork.top-info.rcMonitor.top
                bounds.ptMaxSize.x = info.rcWork.right-info.rcWork.left
                bounds.ptMaxSize.y = info.rcWork.bottom-info.rcWork.top
                return result
            if message == 0x0082:  # WM_NCDESTROY
                self.comctl.RemoveWindowSubclass(hwnd, self._callback, subclass_id)
        except Exception:
            # Never propagate a Python exception across the native callback boundary.
            pass
        return self.comctl.DefSubclassProc(hwnd, message, wparam, lparam)

    def start_resize(self, direction):
        if direction not in RESIZE_HITS:
            raise ValueError('无效的缩放方向')
        from System import Action
        def begin():
            if not self.user.IsZoomed(self.hwnd) and not self.user.IsIconic(self.hwnd):
                self.user.ReleaseCapture()
                point = wintypes.POINT()
                self.user.GetCursorPos(ctypes.byref(point))
                packed = (point.x & 0xffff) | ((point.y & 0xffff) << 16)
                self.user.SendMessageW(self.hwnd, 0x0112, 0xF000 | (RESIZE_HITS[direction]-9), packed)
        # The native sizing loop must run on the WinForms UI thread.
        self.form.BeginInvoke(Action(begin))
        return True

    def verify(self):
        """Exercise the real HWND, used only with an isolated smoke-test ledger."""
        style = self.user.GetWindowLongW(self.hwnd, -16)
        if style & WINDOW_STYLE != WINDOW_STYLE:
            raise RuntimeError('缺少原生缩放或任务栏窗口样式')
        rect = self.rect()
        x, y, initial_width, initial_height = self.initial_bounds
        if (rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top) != (x,y,initial_width,initial_height):
            raise RuntimeError('实际启动窗口位置与居中位置不一致')
        width, height = rect.right-rect.left, rect.bottom-rect.top
        points = [(rect.left, rect.top, 13), (rect.right-1, rect.top, 14),
                  (rect.left, rect.bottom-1, 16), (rect.right-1, rect.bottom-1, 17),
                  (rect.left, rect.top+height//2, 10), (rect.right-1, rect.top+height//2, 11),
                  (rect.left+width//2, rect.top, 12), (rect.left+width//2, rect.bottom-1, 15)]
        for x, y, expected in points:
            packed = (x & 0xffff) | ((y & 0xffff) << 16)
            if self.user.SendMessageW(self.hwnd, 0x0084, 0, packed) != expected:
                raise RuntimeError('窗口边缘缩放命中测试失败')
        self.user.SetWindowPos(self.hwnd, None, 0, 0, width-24, height-24, 0x0016)
        resized = self.rect()
        if resized.right-resized.left != width-24:
            raise RuntimeError('原生窗口尺寸未更新')
        self.user.SetWindowPos(self.hwnd, None, 0, 0, width, height, 0x0016)
        x, y, width, height = self.initial_bounds
        left, top, right, bottom = self.initial_work
        if abs(2*x+width-left-right)>1 or abs(2*y+height-top-bottom)>1:
            raise RuntimeError('窗口未居中')
        # SC_MINIMIZE is the standard system command used by the taskbar.
        self.user.SendMessageW(self.hwnd, 0x0112, 0xF020, 0)
        if not self.user.IsIconic(self.hwnd):
            raise RuntimeError('系统最小化指令未生效')
        self.window.restore()
        return {'edge_hit_tests': 8, 'native_resize': 'passed',
                'system_minimize': 'passed', 'startup_center': 'passed'}
