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

# --- 明确声明GetRawInputBuffer函数原型 --------------------------------
# https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getrawinputbuffer
user32.GetRawInputBuffer.argtypes = [
    ctypes.POINTER(ctypes.c_char),  # pData
    ctypes.POINTER(wintypes.UINT),  # pcbSize
    wintypes.UINT                   # cbSizeHeader
]
user32.GetRawInputBuffer.restype = wintypes.UINT


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
        self._logger("HID 监听已启动，正在轮询原始输入数据。")
        
        # 由于没有创建实际窗口，我们需要使用GetRawInputData直接轮询
        try:
            # 首先获取输入设备信息
            rid = RAWINPUTDEVICE()
            rid.usUsagePage = wintypes.USHORT(0x01)
            rid.usUsage = wintypes.USHORT(0x06)  # 键盘
            rid.dwFlags = wintypes.DWORD(0)
            rid.hwndTarget = 0
            
            while self._running.is_set():
                # 检查是否有输入数据可用
                data_size = wintypes.UINT()
                res = user32.GetRawInputBuffer(None, ctypes.byref(data_size), ctypes.sizeof(RAWINPUTHEADER))
                if res == -1:
                    err = kernel32.GetLastError()
                    if err != 87:  # 87 是 ERROR_INVALID_PARAMETER，通常是因为没有可用数据
                        self._logger(f"HID 监听：GetRawInputBuffer 错误: {err}")
                elif res == 0 and data_size.value > 0:
                    # 分配缓冲区
                    buffer = (ctypes.c_char * data_size.value)()
                    count = user32.GetRawInputBuffer(buffer, ctypes.byref(data_size), ctypes.sizeof(RAWINPUTHEADER))
                    if count > 0:
                        # 处理输入数据
                        current_pos = 0
                        for _ in range(count):
                            raw_input = ctypes.cast(buffer + current_pos, ctypes.POINTER(RAWINPUT)).contents
                            if raw_input.header.dwType == RIM_TYPEKEYBOARD:
                                self._handle_keyboard_input(raw_input.data.keyboard, raw_input.header.hDevice)
                            current_pos += raw_input.header.dwSize
                
                # 短暂休眠，避免CPU占用过高
                import time
                time.sleep(0.01)
        except Exception as e:
            self._logger(f"HID 监听：轮询异常: {e}")
        finally:
            self._logger("HID 监听退出。")

    def stop(self) -> None:
        self._running.clear()
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_DESTROY, 0, 0)
            user32.PostMessageW(self._hwnd, WM_QUIT, 0, 0)
            self._hwnd = None

    # --- internal helpers -------------------------------------------------
    def _prepare_window(self) -> bool:
        """准备窗口以接收Raw Input - 简化版本，避免窗口创建问题"""
        try:
            # 由于窗口创建存在ctypes类型问题，我们改用简单的方法
            # 直接使用现有的hwnd=0来监听所有设备
            self._hwnd = wintypes.HWND(0)
            self._logger("HID 监听：使用简化模式，不需要创建窗口")
            return True
        except Exception as e:
            self._logger(f"HID 监听：准备异常: {e}")
            return False

    def _register_raw_input(self) -> bool:
        """注册Raw Input设备"""
        try:
            # 创建原始输入设备数组
            rid = RAWINPUTDEVICE()
            rid.usUsagePage = wintypes.USHORT(0x01)  # 通用桌面控制
            rid.usUsage = wintypes.USHORT(0x06)      # 键盘
            rid.dwFlags = wintypes.DWORD(0)  # 不使用RIDEV_INPUTSINK，因为hwndTarget为0
            rid.hwndTarget = self._hwnd

            # 注册设备
            # 确保传递正确的参数类型
            num_devices = wintypes.UINT(1)
            size = wintypes.UINT(ctypes.sizeof(rid))
            
            if not user32.RegisterRawInputDevices(
                ctypes.byref(rid),
                num_devices,
                size
            ):
                err = kernel32.GetLastError()
                self._logger(f"HID 监听：RegisterRawInputDevices 失败，错误码 {err}")
                return False

            self._logger("HID 监听已启动，等待刷卡器输入。")
            return True
        except Exception as e:
            self._logger(f"HID 监听：注册 Raw Input 异常: {e}")
            return False

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        """窗口过程 - 处理Raw Input消息"""
        if msg == WM_INPUT:
            self._handle_raw_input(lparam)
        elif msg == WM_DESTROY:
            self._hwnd = None
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _handle_raw_input(self, lparam):
        """处理原始输入数据"""
        try:
            # 获取输入数据大小
            data_size = wintypes.UINT()
            if not user32.GetRawInputData(
                ctypes.cast(lparam, wintypes.HRAWINPUT),
                RID_INPUT,
                None,
                ctypes.byref(data_size),
                ctypes.sizeof(RAWINPUTHEADER)
            ):
                # 分配缓冲区并获取输入数据
                raw_input = RAWINPUT()
                if user32.GetRawInputData(
                    ctypes.cast(lparam, wintypes.HRAWINPUT),
                    RID_INPUT,
                    ctypes.byref(raw_input),
                    ctypes.byref(data_size),
                    ctypes.sizeof(RAWINPUTHEADER)
                ) == data_size:
                    # 处理键盘输入
                    if raw_input.header.dwType == RIM_TYPEKEYBOARD:
                        self._handle_keyboard_input(raw_input.data.keyboard, raw_input.header.hDevice)
        except Exception as e:
            self._logger(f"HID 监听：处理原始输入异常: {e}")
    
    def _handle_keyboard_input(self, keyboard, hDevice):
        """处理键盘输入数据"""
        try:
            # 只处理按下事件（非释放事件）
            if not keyboard.Flags & RI_KEY_BREAK:
                device_name = self._get_device_name(hDevice)
                # 检查设备名称是否符合关键词过滤条件
                if not self._keywords or any(kw in device_name.lower() for kw in self._keywords):
                    digit = self._vk_to_digit(keyboard.VKey)
                    if digit:
                        self._buffer += digit
                        self._last_device = device_name
                        self._logger(f"HID 监听：收到数字 {digit} 来自 {device_name}")
                        # 检查是否达到指定长度且不需要回车
                        if not self._require_enter and len(self._buffer) >= self._digit_length:
                            self._emit_buffer()
                    elif keyboard.VKey == VK_RETURN:
                        # 处理回车键
                        if self._buffer and self._require_enter:
                            self._emit_buffer()
                    elif keyboard.VKey == VK_BACK:
                        # 处理退格键
                        if self._buffer:
                            self._buffer = self._buffer[:-1]
        except Exception as e:
            self._logger(f"HID 监听：处理键盘输入异常: {e}")

    def _get_device_name(self, handle) -> str:
        """获取设备名称"""
        if handle in self._device_names:
            return self._device_names[handle]

        try:
            # 获取设备名称长度
            name_size = wintypes.UINT()
            if not user32.GetRawInputDeviceInfoW(
                ctypes.cast(handle, wintypes.HRAWINPUTDEVINFO),
                RIDI_DEVICENAME,
                None,
                ctypes.byref(name_size)
            ):
                # 分配缓冲区并获取设备名称
                name_buffer = ctypes.create_unicode_buffer(name_size.value)
                if user32.GetRawInputDeviceInfoW(
                    ctypes.cast(handle, wintypes.HRAWINPUTDEVINFO),
                    RIDI_DEVICENAME,
                    name_buffer,
                    ctypes.byref(name_size)
                ):
                    # 提取设备名称（从\Device\开头的路径中提取友好名称）
                    device_name = name_buffer.value
                    if "\\\\?\\HID" in device_name:
                        # 对于HID设备，尝试提取更友好的名称
                        device_name = device_name.split("\\")[-1]
                    self._device_names[handle] = device_name
                    return device_name
        except Exception as e:
            self._logger(f"HID 监听：获取设备名称异常: {e}")

        return f"设备_{hex(handle)[2:10]}"

    def _vk_to_digit(self, vkey) -> Optional[str]:
        """将虚拟键码转换为数字字符"""
        # 数字键0-9的虚拟键码
        vk_digits = {
            0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4",
            0x35: "5", 0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9"
        }
        # 小键盘数字键的虚拟键码
        vk_numpad = {
            0x60: "0", 0x61: "1", 0x62: "2", 0x63: "3", 0x64: "4",
            0x65: "5", 0x66: "6", 0x67: "7", 0x68: "8", 0x69: "9"
        }
        return vk_digits.get(vkey) or vk_numpad.get(vkey)

    def _emit_buffer(self) -> None:
        """发送缓冲区中的完整卡号数据"""
        if self._buffer and self._callback:
            try:
                self._logger(f"HID 监听：发送完整卡号 {self._buffer} 来自 {self._last_device}")
                self._callback(self._buffer, self._last_device)
                self._buffer = ""  # 清空缓冲区
            except Exception as e:
                self._logger(f"HID 监听：发送数据回调异常: {e}")

    def process_bluetooth_data(self, data: str, device_info: str) -> None:
        """处理蓝牙设备数据"""
        if self._callback:
            try:
                self._logger(f"蓝牙数据处理: 数据='{data}', 设备='{device_info}'")
                self._callback(data, device_info)
            except Exception as e:
                self._logger(f"蓝牙数据处理异常: {e}")
        else:
            self._logger(f"警告: 未设置蓝牙数据回调函数")

