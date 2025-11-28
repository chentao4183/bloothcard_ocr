from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable, Dict, List, Optional

# 兼容部分 Python 版本缺少 HCURSOR/HICON/HBRUSH 类型
HCURSOR = getattr(wintypes, "HCURSOR", wintypes.HANDLE)
HICON = getattr(wintypes, "HICON", wintypes.HANDLE)
HBRUSH = getattr(wintypes, "HBRUSH", wintypes.HANDLE)

WM_INPUT = 0x00FF
WM_DESTROY = 0x0002
WM_QUIT = 0x0012
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEKEYBOARD = 1
RIDI_DEVICENAME = 0x20000007
RI_KEY_BREAK = 0x0001
VK_RETURN = 0x0D
VK_BACK = 0x08

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("ulButtons", wintypes.ULONG),
        ("usButtonFlags", wintypes.USHORT),
        ("usButtonData", wintypes.USHORT),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    ]


class RAWHID(ctypes.Structure):
    _fields_ = [
        ("dwSizeHid", wintypes.DWORD),
        ("dwCount", wintypes.DWORD),
        ("bRawData", ctypes.c_byte * 1),
    ]


class RAWINPUTUNION(ctypes.Union):
    _fields_ = [("mouse", RAWMOUSE), ("keyboard", RAWKEYBOARD), ("hid", RAWHID)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("data", RAWINPUTUNION)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROCTYPE),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class HidListener(threading.Thread):
    def __init__(
        self,
        device_keywords: Optional[List[str]],
        digit_length: int,
        require_enter: bool,
        callback: Callable[[str, str], None],
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(daemon=True)
        self._keywords = [kw.lower() for kw in (device_keywords or []) if kw]
        self._digit_length = max(1, digit_length)
        self._require_enter = require_enter
        self._callback = callback
        self._logger = logger or (lambda _msg: None)
        self._running = threading.Event()
        self._hwnd: Optional[int] = None
        self._wndproc_ref: Optional[WNDPROCTYPE] = None
        self._device_names: Dict[int, str] = {}
        self._buffer: str = ""
        self._last_device: str = ""

    def run(self) -> None:
        if not self._prepare_window():
            self._logger("HID 监听：窗口初始化失败，未启用 Raw Input。")
            return
        if not self._register_raw_input():
            self._logger("HID 监听：注册 Raw Input 失败，请确认系统权限。")
            return
        self._running.set()
        msg = wintypes.MSG()
        while self._running.is_set():
            res = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if res == 0 or not self._running.is_set():
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        self._logger("HID 监听退出。")

    def stop(self) -> None:
        self._running.clear()
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_DESTROY, 0, 0)
            user32.PostMessageW(self._hwnd, WM_QUIT, 0, 0)
            self._hwnd = None

    # --- internal helpers -------------------------------------------------
    def _prepare_window(self) -> bool:
        hinstance = kernel32.GetModuleHandleW(None)
        class_name = f"HidListenerWindow_{id(self)}"

        @WNDPROCTYPE
        def _wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_INPUT:
                self._handle_raw_input(lparam)
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, ctypes.c_long(lparam).value)

        wndclass = WNDCLASS()
        wndclass.style = 0
        wndclass.lpfnWndProc = _wnd_proc
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = hinstance
        wndclass.hIcon = None
        wndclass.hCursor = None
        wndclass.hbrBackground = None
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = class_name

        atom = user32.RegisterClassW(ctypes.byref(wndclass))
        if not atom:
            err = kernel32.GetLastError()
            self._logger(f"HID 监听：RegisterClass 失败，错误码 {err}")
            return False

        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "HIDListener",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            err = kernel32.GetLastError()
            self._logger(f"HID 监听：CreateWindowEx 失败，错误码 {err}")
            return False

        self._hwnd = hwnd
        self._wndproc_ref = _wnd_proc
        return True

    def _register_raw_input(self) -> bool:
        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01
        rid.usUsage = 0x06  # keyboard
        rid.dwFlags = RIDEV_INPUTSINK
        rid.hwndTarget = self._hwnd
        if not user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(rid)):
            err = kernel32.GetLastError()
            self._logger(f"HID 监听：RegisterRawInputDevices 失败，错误码 {err}")
            return False
        self._logger("HID 监听已启动，等待刷卡器输入。")
        return True

    def _handle_raw_input(self, lparam) -> None:
        data_size = wintypes.UINT()
        if user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(data_size), ctypes.sizeof(RAWINPUTHEADER)) != 0:
            return
        if not data_size.value:
            return
        buffer = ctypes.create_string_buffer(data_size.value)
        if (
            user32.GetRawInputData(
                lparam,
                RID_INPUT,
                buffer,
                ctypes.byref(data_size),
                ctypes.sizeof(RAWINPUTHEADER),
            )
            != data_size.value
        ):
            return
        raw = ctypes.cast(buffer, ctypes.POINTER(RAWINPUT)).contents
        if raw.header.dwType != RIM_TYPEKEYBOARD:
            return
        keyboard = raw.data.keyboard
        if keyboard.Flags & RI_KEY_BREAK:
            return  # key up
        device_name = self._get_device_name(raw.header.hDevice)
        
        # 调试日志：显示设备名称和按键信息
        self._logger(f"HID调试: 设备={device_name}, VKey={keyboard.VKey}, Flags={keyboard.Flags}")
        
        if self._keywords:
            lower_name = device_name.lower()
            keyword_match = any(kw in lower_name for kw in self._keywords)
            self._logger(f"HID调试: 关键词匹配检查 - 设备名='{lower_name}', 关键词={self._keywords}, 匹配结果={keyword_match}")
            if not keyword_match:
                return
        
        self._last_device = device_name
        if keyboard.VKey == VK_BACK:
            self._buffer = ""
            return
        if keyboard.VKey == VK_RETURN:
            self._logger(f"HID调试: 检测到回车键，缓冲区='{self._buffer}', require_enter={self._require_enter}")
            if self._require_enter:
                self._logger(f"HID调试: 发射缓冲区数据")
                self._emit_buffer()
            return
        char = self._vk_to_digit(keyboard.VKey)
        if char is None:
            self._logger(f"HID调试: 非数字按键 - VKey={keyboard.VKey}")
            return
        self._buffer += char
        self._logger(f"HID调试: 按键输入 - 字符='{char}', 当前缓冲区='{self._buffer}'")
        if not self._require_enter and len(self._buffer) >= self._digit_length:
            self._logger(f"HID调试: 达到数字长度限制，准备发射缓冲区")
            self._emit_buffer()

    def _get_device_name(self, handle) -> str:
        if not handle:
            return "unknown"
        key = int(handle)
        if key in self._device_names:
            return self._device_names[key]
        size = wintypes.UINT(0)
        user32.GetRawInputDeviceInfoW(handle, RIDI_DEVICENAME, None, ctypes.byref(size))
        if not size.value:
            self._device_names[key] = "unknown"
            return "unknown"
        buffer = (wintypes.WCHAR * size.value)()
        if user32.GetRawInputDeviceInfoW(handle, RIDI_DEVICENAME, buffer, ctypes.byref(size)) == -1:
            self._device_names[key] = "unknown"
            return "unknown"
        name = buffer.value
        self._device_names[key] = name
        return name

    def _vk_to_digit(self, vkey: int) -> Optional[str]:
        if 0x30 <= vkey <= 0x39:
            return chr(vkey)
        if 0x60 <= vkey <= 0x69:
            return chr(vkey - 0x30)
        return None

    def _emit_buffer(self) -> None:
        if not self._buffer:
            self._logger(f"HID调试: 缓冲区为空，不发射数据")
            return
        value = self._buffer
        self._buffer = ""
        self._logger(f"HID调试: 准备发射数据 - 原始值='{value}', 长度={len(value)}, 要求长度={self._digit_length}")
        if len(value) < self._digit_length:
            self._logger(f"HID调试: 数据长度不足，忽略")
            return
        if not value.isdigit():
            self._logger(f"HID调试: 数据包含非数字字符，忽略")
            return
        device = self._last_device or "HID"
        final_value = value[-self._digit_length :]
        self._logger(f"HID调试: 发射RFID数据 - 值='{final_value}', 设备='{device}'")
        try:
            self._callback(final_value, device)
        except Exception as e:
            self._logger(f"HID调试: 回调异常 - {e}")
            pass

