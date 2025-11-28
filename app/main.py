from __future__ import annotations

import asyncio
import concurrent.futures
import datetime as dt
import json
import os
import sys
import threading
import tkinter as tk
import uuid
import logging
import platform
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Optional

# 配置基本日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.debug("程序开始初始化...")
logger.debug(f"Python版本: {platform.python_version()}")
logger.debug(f"操作系统: {platform.system()} {platform.release()}")
logger.debug(f"当前工作目录: {os.getcwd()}")

import requests
from bleak.backends.device import BLEDevice

try:
    logger.debug("尝试导入BleManager等模块...")
    from app.ble.ble_manager import BleManager  # type: ignore
    from app.config_manager import AppConfig, ConfigManager, OCRField, Rect, ServiceVersionConfig
    from app.hid_listener_simple import SimpleHidListener as HidListener  # type: ignore
    
    from app.system_devices import ConnectedDevice  # type: ignore
    logger.debug("成功导入所有模块")
except Exception as e:
    logger.error(f"导入模块失败: {e}")
    try:
        logger.debug("尝试相对导入...")
        from .ble.ble_manager import BleManager  # type: ignore
        from .config_manager import AppConfig, ConfigManager, OCRField, Rect, ServiceVersionConfig  # type: ignore
        from .hid_listener_simple import SimpleHidListener as HidListener  # type: ignore
        
        from .system_devices import ConnectedDevice  # type: ignore
        logger.debug("成功相对导入所有模块")
    except Exception as e:
        logger.error(f"相对导入模块失败: {e}")
        raise


def _human_now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _startup_command() -> str:
    exe = Path(sys.argv[0]).resolve()
    if exe.suffix.lower() == ".exe":
        return str(exe)
    python = Path(sys.executable).resolve()
    module = Path(__file__).resolve()
    return f'"{python}" "{module}"'


def set_startup(enabled: bool) -> None:
    if os.name != "nt":
        return
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, "BLEBlueTool", 0, winreg.REG_SZ, _startup_command())
            else:
                try:
                    winreg.DeleteValue(key, "BLEBlueTool")
                except FileNotFoundError:
                    pass
    except Exception:
        pass


class FieldDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Widget, title: str, field: Optional[OCRField] = None):
        self._field = field
        super().__init__(parent, title)

    def body(self, master: tk.Frame) -> tk.Widget | None:
        ttk.Label(master, text="名称").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        ttk.Label(master, text="参数名").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        ttk.Label(master, text="默认值").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        ttk.Label(master, text="识别示例").grid(row=3, column=0, sticky="e", padx=4, pady=4)

        self.name_var = tk.StringVar(value=self._field.name if self._field else "")
        self.param_var = tk.StringVar(value=self._field.param_name if self._field else "")
        self.default_var = tk.StringVar(value=self._field.default_value if self._field else "")
        self.sample_var = tk.StringVar(value=self._field.sample_value if self._field else "")

        ttk.Entry(master, textvariable=self.name_var).grid(row=0, column=1, pady=4, sticky="ew")
        ttk.Entry(master, textvariable=self.param_var).grid(row=1, column=1, pady=4, sticky="ew")
        ttk.Entry(master, textvariable=self.default_var).grid(row=2, column=1, pady=4, sticky="ew")
        ttk.Entry(master, textvariable=self.sample_var).grid(row=3, column=1, pady=4, sticky="ew")

        master.columnconfigure(1, weight=1)
        return master

    def validate(self) -> bool:
        if not self.name_var.get().strip():
            messagebox.showerror("提示", "名称不能为空")
            return False
        if not self.param_var.get().strip():
            messagebox.showerror("提示", "参数名不能为空")
            return False
        return True

    def apply(self) -> None:
        self.result = {
            "name": self.name_var.get().strip(),
            "param_name": self.param_var.get().strip(),
            "default_value": self.default_var.get().strip(),
            "sample_value": self.sample_var.get().strip(),
        }


class BindingDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Widget,
        card_info: Dict[str, str],
        field_values: Dict[str, str],
        auto_submit: bool,
        auto_seconds: int,
        on_submit,
        on_cancel,
    ):
        super().__init__(master)
        self.card_info = card_info
        self.field_values = field_values
        self.auto_submit = auto_submit
        self.remaining = max(0, auto_seconds)
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.title("信息绑定确认")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        ttk.Label(self, text=f"卡号 8H: {card_info.get('hex', 'N/A')} / 10D: {card_info.get('dec', 'N/A')}").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        ttk.Label(self, text=f"来源: {card_info.get('source', '未知')}").pack(anchor="w", padx=10, pady=(0, 10))

        columns = ("param", "value")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=8)
        self.tree.heading("param", text="参数名")
        self.tree.heading("value", text="值")
        self.tree.column("param", width=120, anchor="w")
        self.tree.column("value", width=250, anchor="w")
        for key, val in field_values.items():
            self.tree.insert("", tk.END, values=(key, val))
        self.tree.pack(fill="both", expand=True, padx=10)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, foreground="#555555").pack(anchor="w", padx=10, pady=(4, 0))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        self.submit_btn = ttk.Button(btn_frame, text="提交", command=self._submit)
        self.submit_btn.pack(side="right", padx=4)
        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side="right", padx=4)

        if self.auto_submit and self.remaining > 0:
            self.status_var.set(f"{self.remaining} 秒后自动提交")
            self.after(1000, self._tick)

    def _tick(self) -> None:
        if not self.auto_submit:
            return
        self.remaining -= 1
        if self.remaining <= 0:
            self.status_var.set("正在自动提交...")
            self._submit()
        else:
            self.status_var.set(f"{self.remaining} 秒后自动提交")
            self.after(1000, self._tick)

    def _submit(self) -> None:
        self.submit_btn.configure(state=tk.DISABLED)
        if callable(self.on_submit):
            self.on_submit()

    def _cancel(self) -> None:
        if callable(self.on_cancel):
            self.on_cancel()
        self.destroy()

    def show_result(self, text: str) -> None:
        self.status_var.set(text)


class FloatInputWindow(tk.Toplevel):
    def __init__(self, master: tk.Widget, on_submit):
        super().__init__(master)
        self.on_submit = on_submit
        self.title("浮球输入")
        self.geometry("220x120")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._hide)

        ttk.Label(self, text="手动输入卡号 8H/10D").pack(pady=(10, 4))
        self.entry = ttk.Entry(self)
        self.entry.pack(fill="x", padx=10, pady=4)
        ttk.Button(self, text="注入", command=self._submit).pack(pady=4)

    def _submit(self) -> None:
        value = self.entry.get().strip()
        if not value:
            return
        if callable(self.on_submit):
            self.on_submit(value)
        self.entry.delete(0, tk.END)

    def _hide(self) -> None:
        self.withdraw()


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BLE 蓝牙工具 (Windows)")
        self.root.geometry("1024x680")
        self.root.minsize(960, 600)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.config_path = Path(__file__).resolve().parent.parent / "app_settings.json"
        self.config_manager = ConfigManager(self.config_path)
        self.config = self.config_manager.load()

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

        self.manager = BleManager()
        self.manager.set_callbacks(
            on_log=self.append_log,
            on_devices_updated=self.on_devices_updated,
            on_device_event=self.on_device_event,
            on_card_data=self.on_card_data,
        )

        self.loop = asyncio.new_event_loop()
        self.manager.assign_loop(self.loop)
        self.loop_thread = threading.Thread(target=self._run_loop, name="ble-loop", daemon=True)
        self.loop_thread.start()

        self.scanned_devices: List[ConnectedDevice] = []
        self.latest_card: Optional[Dict[str, str]] = None
        self.pending_binding_payload: Optional[Dict] = None
        self.binding_dialog: Optional[BindingDialog] = None
        self.float_window: Optional[FloatInputWindow] = None
        self.hid_listener: Optional[HidListener] = None

        self.hid_accepting: bool = True
        self.bound_hid_device: Optional[str] = None
        self.hid_expected_label: str = ""

        self.status_var = tk.StringVar(value="未连接")
        self.card_var = tk.StringVar(value="未检测到刷卡")

        self._build_layout()
        self._refresh_ocr_tree()
        self._refresh_service_form()
        self._refresh_backend_form()
        if self.config.backend.enable_float_input:
            self._ensure_float_window(show=True)
        
        # 应用程序初始化完成后自动启动HID监听器
        self._restart_hid_listener()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _build_layout(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.tab_ble = ttk.Frame(self.notebook, padding=10)
        self.tab_ocr = ttk.Frame(self.notebook, padding=10)
        self.tab_service = ttk.Frame(self.notebook, padding=10)
        self.tab_backend = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab_ble, text="蓝牙配置")
        self.notebook.add(self.tab_ocr, text="OCR配置")
        self.notebook.add(self.tab_service, text="服务配置")
        self.notebook.add(self.tab_backend, text="后台配置")

        self._build_ble_tab()
        self._build_ocr_tab()
        self._build_service_tab()
        self._build_backend_tab()

        log_frame = ttk.LabelFrame(self.root, text="日志打印")
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.root.grid_rowconfigure(1, weight=0)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=8, wrap=tk.NONE)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.log_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)



    # --- BLE TAB
    def _build_ble_tab(self) -> None:
        btn_frame = ttk.Frame(self.tab_ble)
        btn_frame.pack(fill="x")

        self.scan_button = ttk.Button(btn_frame, text="扫描", command=self.on_scan)
        self.scan_button.pack(side="left", padx=(0, 6))
        self.connect_button = ttk.Button(btn_frame, text="监听", command=self.on_connect, state=tk.DISABLED)
        self.connect_button.pack(side="left", padx=6)
        self.disconnect_button = ttk.Button(btn_frame, text="断开", command=self.on_disconnect, state=tk.DISABLED)
        self.disconnect_button.pack(side="left", padx=6)

        ttk.Label(self.tab_ble, textvariable=self.status_var, foreground="#1d8348").pack(anchor="w", pady=(8, 4))
        ttk.Label(self.tab_ble, textvariable=self.card_var, foreground="#2874a6").pack(anchor="w", pady=(0, 8))

        list_frame = ttk.Frame(self.tab_ble)
        list_frame.pack(fill="both", expand=True)
        ttk.Label(list_frame, text="设备列表").pack(anchor="w")

        self.devices_list = tk.Listbox(list_frame, height=12, exportselection=False)
        self.devices_list.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.devices_list.yview)
        scroll.pack(side="right", fill="y")
        self.devices_list.configure(yscrollcommand=scroll.set)
        self.devices_list.bind("<<ListboxSelect>>", self.on_select)

    # --- OCR TAB
    def _build_ocr_tab(self) -> None:
        columns = ("enabled", "name", "param", "default", "recognized", "sample")
        self.ocr_tree = ttk.Treeview(self.tab_ocr, columns=columns, show="headings", height=10, selectmode="browse")
        self.ocr_tree.heading("enabled", text="启用")
        self.ocr_tree.heading("name", text="名称")
        self.ocr_tree.heading("param", text="参数名")
        self.ocr_tree.heading("default", text="默认")
        self.ocr_tree.heading("recognized", text="识图")
        self.ocr_tree.heading("sample", text="识别示例")
        self.ocr_tree.column("enabled", width=60, anchor="center")
        self.ocr_tree.column("name", width=120)
        self.ocr_tree.column("param", width=120)
        self.ocr_tree.column("default", width=150)
        self.ocr_tree.column("recognized", width=60)
        self.ocr_tree.column("sample", width=150)
        self.ocr_tree.pack(fill="both", expand=True)
        self.ocr_tree.bind("<Double-1>", self._on_ocr_tree_double_click)
        self.ocr_tree.bind("<<TreeviewSelect>>", self._on_ocr_tree_select)

        btn_frame = ttk.Frame(self.tab_ocr)
        btn_frame.pack(fill="x", pady=8)
        ttk.Button(btn_frame, text="新增", command=self.add_field).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="编辑", command=self.edit_field).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="启用/禁用", command=self.toggle_field).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="定位", command=self.set_field_rect).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="识别", command=self.recognize_field).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="删除", command=self.delete_field).pack(side="left", padx=4)

        tips = (
            "tips: 无法通过OCR识别获取的字段，可自定义默认值；多选项字段以 ';' 分隔，"
            "工具会在提交前允许手动切换。定位/识别流程会记录最后一次结果，便于信息绑定。"
        )
        ttk.Label(self.tab_ocr, text=tips, wraplength=900, foreground="#7b7d7d").pack(anchor="w", pady=(4, 0))
        
        # OCR引擎状态显示
        self.ocr_status_label = ttk.Label(self.tab_ocr, text="正在检测OCR引擎...", foreground="#007acc")
        self.ocr_status_label.pack(anchor="w", pady=(4, 0))
        
        # 延迟显示OCR引擎状态，避免初始化时阻塞
        self.root.after(1000, self._update_ocr_status)
        
        # 右侧预览区域 - 放大尺寸以更好显示截图和按钮
        preview_frame = ttk.LabelFrame(self.tab_ocr, text="截图预览", width=280, height=450)
        preview_frame.pack(side="right", fill="y", padx=(10, 0), pady=(0, 20))
        preview_frame.pack_propagate(False)
        
        # 预览标签
        self.screenshot_preview_label = ttk.Label(preview_frame, text="暂无截图", 
                                                 relief="solid", borderwidth=1,
                                                 anchor="center", justify="center")
        self.screenshot_preview_label.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 预览按钮
        preview_btn_frame = ttk.Frame(preview_frame)
        preview_btn_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        ttk.Button(preview_btn_frame, text="查看大图", 
                  command=self._show_current_screenshot_preview).pack(fill="x", pady=(0, 5))

    # --- SERVICE TAB
    def _build_service_tab(self) -> None:
        version_frame = ttk.LabelFrame(self.tab_service, text="1. 对接系统选择")
        version_frame.pack(fill="x", pady=6)

        self.service_version_var = tk.StringVar(value=self.config.service.selected_version)
        self.service_version_var.trace_add("write", lambda *_: self._on_service_version_change())

        for idx, (version, _) in enumerate(self.config.service.versions.items()):
            block = ttk.Frame(version_frame)
            block.pack(fill="x", pady=4)
            ttk.Radiobutton(
                block, text=version.upper(), value=version, variable=self.service_version_var
            ).grid(row=0, column=0, rowspan=2, sticky="nw", padx=4)

            verify_var = tk.StringVar(value=self.config.service.versions[version].verify_url)
            bind_var = tk.StringVar(value=self.config.service.versions[version].bind_url)

            # V0.0版本特殊处理：显示调试URL和调试按钮
            if version == "v0":
                debug_var = tk.StringVar(value=self.config.service.versions[version].debug_url)
                
                ttk.Label(block, text="调试URL:").grid(row=0, column=1, sticky="w", padx=6, pady=2)
                ttk.Entry(block, textvariable=debug_var, width=50).grid(row=0, column=2, sticky="ew", padx=6, pady=2)
                ttk.Button(block, text="保存", command=lambda v=version, var=debug_var: self._update_service_url(v, "debug", var)).grid(row=0, column=3, sticky="e", padx=2, pady=2)
                ttk.Button(block, text="调试", command=self._debug_v0_system).grid(row=0, column=4, sticky="e", padx=6, pady=2)
                block.columnconfigure(2, weight=1)
            else:
                ttk.Label(block, text="洗消验证接口:").grid(row=0, column=1, sticky="w", padx=6, pady=2)
                ttk.Entry(block, textvariable=verify_var, width=60).grid(row=0, column=2, sticky="ew", padx=6, pady=2)
                ttk.Button(block, text="保存", command=lambda v=version, var=verify_var: self._update_service_url(v, "verify", var)).grid(row=0, column=3, sticky="e", padx=6, pady=2)
                
                ttk.Label(block, text="信息绑定接口:").grid(row=1, column=1, sticky="w", padx=6, pady=2)
                ttk.Entry(block, textvariable=bind_var, width=60).grid(row=1, column=2, sticky="ew", padx=6, pady=2)
                ttk.Button(block, text="保存", command=lambda v=version, var=bind_var: self._update_service_url(v, "bind", var)).grid(row=1, column=3, sticky="e", padx=6, pady=2)
                block.columnconfigure(2, weight=1)

        verify_frame = ttk.LabelFrame(self.tab_service, text="2. 验证功能选择")
        verify_frame.pack(fill="x", pady=6)
        self.verify_enabled_var = tk.BooleanVar(value=self.config.service.enable_verification)
        self.verify_enabled_var.trace_add("write", lambda *_: self._save_service_config())
        ttk.Checkbutton(verify_frame, text="验证洗消结果", variable=self.verify_enabled_var).grid(row=0, column=0, sticky="w", padx=6, pady=6)

        self.popup_success_var = tk.BooleanVar(value=self.config.service.popup_success)
        ttk.Checkbutton(verify_frame, text="弹窗显示洗消成功结果", variable=self.popup_success_var,
                        command=self._save_service_config).grid(row=1, column=0, sticky="w", padx=20)
        self.popup_failure_var = tk.BooleanVar(value=self.config.service.popup_failure)
        ttk.Checkbutton(verify_frame, text="弹窗显示洗消失败结果", variable=self.popup_failure_var,
                        command=self._save_service_config).grid(row=1, column=1, sticky="w", padx=20)

        note = (
            "本工具需兼容新/老系统。刷卡后若启用验证，将调用选定版本的洗消验证接口，再依据结果决定是否提交绑定接口；"
            "可配置是否弹窗展示成功/失败提示。"
        )
        ttk.Label(self.tab_service, text=note, wraplength=900, foreground="#7b7d7d").pack(anchor="w", pady=(6, 0))

    # --- BACKEND TAB
    def _build_backend_tab(self) -> None:
        submit_frame = ttk.LabelFrame(self.tab_backend, text="信息绑定弹窗")
        submit_frame.pack(fill="x", pady=6)

        self.submission_mode_var = tk.StringVar(value=self.config.backend.submission_mode)
        self.submission_mode_var.trace_add("write", lambda *_: self._on_backend_change())
        ttk.Radiobutton(submit_frame, text="手动提交", value="manual", variable=self.submission_mode_var).grid(row=0, column=0, sticky="w", padx=6, pady=4)

        auto_frame = ttk.Frame(submit_frame)
        auto_frame.grid(row=0, column=1, sticky="w", padx=6)
        ttk.Radiobutton(auto_frame, text="自动提交", value="auto", variable=self.submission_mode_var).pack(side="left")
        ttk.Label(auto_frame, text="，").pack(side="left")
        self.auto_delay_var = tk.IntVar(value=self.config.backend.auto_delay_seconds)
        self.auto_delay_var.trace_add("write", lambda *_: self._on_backend_change())
        self.auto_delay_spin = ttk.Spinbox(auto_frame, from_=1, to=30, width=4, textvariable=self.auto_delay_var, command=self._on_backend_change)
        self.auto_delay_spin.pack(side="left")
        ttk.Label(auto_frame, text=" 秒内自动提交，并关闭弹窗").pack(side="left")

        option_frame = ttk.Frame(self.tab_backend)
        option_frame.pack(fill="x", pady=6)
        self.startup_var = tk.BooleanVar(value=self.config.backend.enable_startup)
        ttk.Checkbutton(option_frame, text="开机自启动，默认后台运行", variable=self.startup_var,
                        command=self._on_backend_change).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.float_var = tk.BooleanVar(value=self.config.backend.enable_float_input)
        ttk.Checkbutton(option_frame, text="开启浮球输入（硬件异常时手动输入卡号）", variable=self.float_var,
                        command=self._on_backend_change).grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.service_var = tk.BooleanVar(value=self.config.backend.enable_service)
        ttk.Checkbutton(option_frame, text="开启服务（自动串联扫描/验证/绑定）", variable=self.service_var,
                        command=self._on_backend_change).grid(row=2, column=0, sticky="w", padx=6, pady=4)

        hid_frame = ttk.LabelFrame(self.tab_backend, text="HID 监听配置（键盘模式刷卡器）")
        hid_frame.pack(fill="x", pady=6)
        self.hid_enabled_var = tk.BooleanVar(value=self.config.hid.enabled)
        self.hid_keywords_var = tk.StringVar(value=";".join(self.config.hid.device_keywords))
        self.hid_digits_var = tk.IntVar(value=self.config.hid.digit_length)
        self.hid_require_enter_var = tk.BooleanVar(value=self.config.hid.require_enter)

        ttk.Checkbutton(hid_frame, text="启用 HID 监听（无需 BLE 连接）", variable=self.hid_enabled_var).grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=4)
        ttk.Label(hid_frame, text="设备关键词（分号分隔）").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(hid_frame, textvariable=self.hid_keywords_var).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(hid_frame, text="数字长度").grid(row=1, column=2, sticky="e", padx=6, pady=4)
        ttk.Spinbox(hid_frame, from_=4, to=32, width=4, textvariable=self.hid_digits_var).grid(row=1, column=3, sticky="w", padx=6, pady=4)
        ttk.Checkbutton(hid_frame, text="需回车/Enter 结束一次刷卡", variable=self.hid_require_enter_var).grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        ttk.Button(hid_frame, text="保存 HID 配置", command=self._apply_hid_form).grid(row=2, column=3, sticky="e", padx=6, pady=4)
        hid_frame.columnconfigure(1, weight=1)

        desc = (
            "后台配置说明：字段齐备后可选择手动或自动提交。开机自启动便于医生电脑保持后台运行；启用浮球输入时，可在刷卡器异常时手动注入卡号；"
            "勾选开启服务后，系统会在检测到刷卡并完成验证后自动弹窗或提交。"
        )
        ttk.Label(self.tab_backend, text=desc, wraplength=900, foreground="#7b7d7d").pack(anchor="w", pady=(6, 0))

    # --- OCR operations
    def _refresh_ocr_tree(self) -> None:
        for item in self.ocr_tree.get_children():
            self.ocr_tree.delete(item)
        for field in self.config.ocr_fields:
            # 识图列显示图标：有截图显示相机图标，无截图显示空白
            screenshot_status = "📷" if field.recognition_area else ""
                
            self.ocr_tree.insert(
                "",
                tk.END,
                iid=field.field_id,
                values=(
                    "✔" if field.enabled else "✘",
                    field.name,
                    field.param_name,
                    field.default_value,
                    screenshot_status,
                    field.sample_value or field.recognized_value,  # 优先显示识别示例，如果没有则显示识别结果
                ),
            )

    def _update_ocr_status(self) -> None:
        """更新OCR引擎状态显示"""
        try:
            from app.ocr_engine import get_ocr_engine, get_available_engines
            
            # 获取当前引擎信息
            engine = get_ocr_engine()
            engine_info = engine.get_engine_info()
            
            if engine_info:
                engine_name = engine_info.get('engine', '未知')
                description = engine_info.get('description', '无描述')
                status_text = f"当前OCR引擎: {engine_name} - {description}"
                color = "#28a745"  # 绿色，表示正常
            else:
                status_text = "OCR引擎: 无可用引擎"
                color = "#dc3545"  # 红色，表示异常
            
            # 获取所有可用引擎
            available_engines = get_available_engines()
            available_count = sum(1 for info in available_engines.values() if info['available'])
            total_count = len(available_engines)
            
            if available_count > 0:
                status_text += f" (可用引擎: {available_count}/{total_count})"
            
            # 更新状态标签
            self.ocr_status_label.config(text=status_text, foreground=color)
            
        except Exception as e:
            self.ocr_status_label.config(text=f"OCR引擎检测失败: {e}", foreground="#dc3545")

    def _on_ocr_tree_select(self, event) -> None:
        """OCR树选择事件处理"""
        field = self._get_selected_field()
        if field and field.recognition_area:
            # 如果有选中字段且有截图，显示预览
            self._update_screenshot_preview(field)
        else:
            # 清空预览
            self._clear_screenshot_preview()

    def _on_ocr_tree_double_click(self, event) -> None:
        """双击OCR树的事件处理"""
        # 获取点击的列
        column = self.ocr_tree.identify_column(event.x)
        field = self._get_selected_field()
        if not field:
            return
            
        # 如果双击的是"识图"列，显示截图预览
        if column == "#5" and field.recognition_area:  # "#5"是"识图"列
            self._show_screenshot_preview(field)
        else:
            # 其他列双击，执行编辑功能
            self.edit_field()

    def _show_current_screenshot_preview(self) -> None:
        """显示当前选中字段的大图预览"""
        field = self._get_selected_field()
        if field:
            self._show_screenshot_preview(field)
        else:
            messagebox.showinfo("提示", "请先选择一个字段")
    
    def _update_screenshot_preview(self, field: OCRField) -> None:
        """更新截图预览（在主界面显示小预览图）"""
        try:
            import PIL.Image
            import PIL.ImageTk
            import glob
            import os
            
            # 查找该字段的最新截图
            screenshots_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
            pattern = os.path.join(screenshots_dir, f"{field.name}_*.png")
            screenshots = glob.glob(pattern)
            
            if not screenshots:
                self._clear_screenshot_preview()
                return
            
            # 获取最新截图
            latest_screenshot = max(screenshots, key=os.path.getmtime)
            
            # 加载图片并调整大小
            image = PIL.Image.open(latest_screenshot)
            # 调整图片大小以适应预览区域（小尺寸）
            image.thumbnail((120, 80), PIL.Image.Resampling.LANCZOS)
            
            photo = PIL.ImageTk.PhotoImage(image)
            
            # 更新预览标签
            if hasattr(self, 'screenshot_preview_label'):
                self.screenshot_preview_label.configure(image=photo, text="")
                self.screenshot_preview_label.image = photo  # 保持引用
                self.current_preview_image = photo
            else:
                # 如果预览标签不存在，创建它
                self.screenshot_preview_label = ttk.Label(self.tab_ocr, image=photo, relief="solid", borderwidth=1)
                self.screenshot_preview_label.image = photo
                self.screenshot_preview_label.pack(side="right", padx=10, pady=10)
                
        except Exception as e:
            self.append_log(f"[OCR] 截图预览更新失败：{e}")
            self._clear_screenshot_preview()

    def _clear_screenshot_preview(self) -> None:
        """清空截图预览"""
        if hasattr(self, 'screenshot_preview_label'):
            self.screenshot_preview_label.configure(image="", text="暂无截图")
            if hasattr(self, 'current_preview_image'):
                delattr(self, 'current_preview_image')

    def _show_screenshot_preview(self, field: OCRField) -> None:
        """显示截图预览窗口（大图）"""
        try:
            import tkinter as tk
            from tkinter import ttk
            import PIL.Image
            import PIL.ImageTk
            import glob
            import os
            
            # 查找该字段的最新截图
            screenshots_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
            pattern = os.path.join(screenshots_dir, f"{field.name}_*.png")
            screenshots = glob.glob(pattern)
            
            if not screenshots:
                messagebox.showinfo("提示", f"字段'{field.name}'暂无截图")
                return
            
            # 获取最新截图
            latest_screenshot = max(screenshots, key=os.path.getmtime)
            
            # 创建预览窗口（尺寸放大一倍）
            preview_window = tk.Toplevel(self.root)
            preview_window.title(f"截图预览 - {field.name}")
            preview_window.geometry("400x300")  # 原400x300放大到800x600
            preview_window.transient(self.root)
            preview_window.grab_set()
            
            # 加载图片
            image = PIL.Image.open(latest_screenshot)
            
            # 调整图片大小以适应窗口（尺寸放大一倍）
            max_width, max_height = 760, 500  # 原380x250放大到760x500
            image.thumbnail((max_width, max_height), PIL.Image.Resampling.LANCZOS)
            
            photo = PIL.ImageTk.PhotoImage(image)
            
            # 显示图片
            label = ttk.Label(preview_window, image=photo)
            label.image = photo  # 保持引用
            label.pack(pady=10)
            
            # 显示图片信息
            info_text = f"截图: {os.path.basename(latest_screenshot)}\n"
            info_text += f"区域: ({field.recognition_area.x},{field.recognition_area.y}) {field.recognition_area.width}x{field.recognition_area.height}"
            if field.recognized_value:
                info_text += f"\n识别结果: {field.recognized_value}"
                
            info_label = ttk.Label(preview_window, text=info_text, justify="center")
            info_label.pack(pady=5)
            
            # 关闭按钮
            ttk.Button(preview_window, text="关闭", command=preview_window.destroy).pack(pady=5)
            
            # 窗口居中
            preview_window.update_idletasks()
            x = (preview_window.winfo_screenwidth() - preview_window.winfo_width()) // 2
            y = (preview_window.winfo_screenheight() - preview_window.winfo_height()) // 2
            preview_window.geometry(f"+{x}+{y}")
            
        except Exception as e:
            self.append_log(f"[OCR] 截图预览失败：{e}")
            messagebox.showerror("错误", f"截图预览失败：{e}")

    def _get_selected_field(self) -> Optional[OCRField]:
        sel = self.ocr_tree.selection()
        if not sel:
            return None
        field_id = sel[0]
        for field in self.config.ocr_fields:
            if field.field_id == field_id:
                return field
        return None

    def add_field(self) -> None:
        dialog = FieldDialog(self.root, "新增字段")
        if not dialog.result:
            return
        field = OCRField(
            field_id=str(uuid.uuid4()),
            name=dialog.result["name"],
            param_name=dialog.result["param_name"],
            default_value=dialog.result["default_value"],
            sample_value=dialog.result["sample_value"],
        )
        self.config.ocr_fields.append(field)
        self._save_config()
        self._refresh_ocr_tree()

    def edit_field(self) -> None:
        field = self._get_selected_field()
        if not field:
            return
        dialog = FieldDialog(self.root, "编辑字段", field=field)
        if not dialog.result:
            return
        field.name = dialog.result["name"]
        field.param_name = dialog.result["param_name"]
        field.default_value = dialog.result["default_value"]
        field.sample_value = dialog.result["sample_value"]
        self._save_config()
        self._refresh_ocr_tree()

    def toggle_field(self) -> None:
        field = self._get_selected_field()
        if not field:
            return
        field.enabled = not field.enabled
        self._save_config()
        self._refresh_ocr_tree()

    def set_field_rect(self) -> None:
        field = self._get_selected_field()
        if not field:
            return
            
        # 使用屏幕截图选择器
        try:
            from app.screenshot_selector import ScreenshotSelector
            selector = ScreenshotSelector(self.root)
            area = selector.select_area()
            
            if area:
                x, y, w, h = area
                from app.config_manager import Rect
                
                field.recognition_area = Rect(x=x, y=y, width=w, height=h)
                self._save_config()
                self.append_log(f"[OCR] 已设置 {field.name} 区域：({x},{y},{w},{h})")
                
                # 自动进行OCR识别并保存截图
                self._auto_recognize_and_save(field, x, y, w, h)
                
                # messagebox.showinfo("成功", f"识别区域已设置：{w}x{h} 位于 ({x},{y})")
            else:
                self.append_log(f"[OCR] 取消设置 {field.name} 识别区域")
                
        except ImportError as e:
            # 如果截图选择器不可用，回退到原来的输入方式
            self._set_field_rect_manual(field)
        except Exception as e:
            messagebox.showerror("错误", f"屏幕截图选择器出错：{e}\n将使用手动输入方式")
            self._set_field_rect_manual(field)
    
    def _recognize_with_retry(self, x: int, y: int, w: int, h: int, max_retries: int = 2) -> str:
        """带重试机制的OCR识别"""
        from app.ocr_engine import recognize_screen_area
        import time
        
        for attempt in range(max_retries):
            try:
                # 第一次尝试直接识别
                if attempt == 0:
                    result = recognize_screen_area(x, y, w, h)
                    if result.strip():
                        return result
                
                # 第二次尝试稍微调整区域大小
                elif attempt == 1:
                    # 稍微扩大区域（增加5像素边距）
                    adjusted_x = max(0, x - 5)
                    adjusted_y = max(0, y - 5)
                    adjusted_w = w + 10
                    adjusted_h = h + 10
                    
                    result = recognize_screen_area(adjusted_x, adjusted_y, adjusted_w, adjusted_h)
                    if result.strip():
                        self.append_log(f"[OCR] 使用调整后的区域识别成功：({adjusted_x},{adjusted_y},{adjusted_w},{adjusted_h})")
                        return result
                
                # 如果还有重试次数，等待一小段时间
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # 短暂等待
                    
            except Exception as e:
                self.append_log(f"[OCR] 识别尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.1)
        
        return ""
    
    def _show_ocr_tooltip(self, message: str) -> None:
        """显示OCR相关的工具提示"""
        try:
            # 使用tkinter的messagebox显示简短提示
            # 使用after延迟显示，避免阻塞主线程
            self.root.after(100, lambda: messagebox.showinfo("OCR提示", message))
        except Exception:
            # 如果显示工具提示失败，只记录日志
            self.append_log(f"[OCR提示] {message}")
    
    def _show_ocr_success_tooltip(self, field_name: str, recognized_text: str) -> None:
        """显示OCR成功识别的工具提示"""
        # 截断过长的识别结果
        display_text = recognized_text[:50] + "..." if len(recognized_text) > 50 else recognized_text
        message = f"字段 '{field_name}' 识别成功:\n{display_text}"
        self._show_ocr_tooltip(message)
    
    def _show_ocr_result_dialog(self, field_name: str, x: int, y: int, w: int, h: int, recognized_text: str = None, is_success: bool = True) -> None:
        """显示OCR识别结果的综合对话框，包含坐标和识别结果信息"""
        try:
            # 构建综合提示信息
            coord_info = f"识别区域: ({x}, {y}, {w}, {h})"
            
            if is_success and recognized_text:
                # 截断过长的识别结果
                display_text = recognized_text[:100] + "..." if len(recognized_text) > 100 else recognized_text
                message = f"字段 '{field_name}' 识别成功！\n\n{coord_info}\n\n识别结果:\n{display_text}"
                title = "OCR识别成功"
                icon = "info"
            elif is_success and not recognized_text:
                message = f"字段 '{field_name}' 未识别到文字内容。\n\n{coord_info}\n\n请检查截图区域是否包含清晰的文字。"
                title = "OCR识别结果"
                icon = "warning"
            else:
                message = f"字段 '{field_name}' OCR识别失败。\n\n{coord_info}\n\n请检查截图区域或手动输入。"
                title = "OCR识别失败"
                icon = "error"
            
            # 使用after延迟显示，避免阻塞主线程
            self.root.after(100, lambda: messagebox.showinfo(title, message))
            
        except Exception as e:
            # 如果显示对话框失败，只记录日志
            self.append_log(f"[OCR结果提示] 显示失败: {e}")
            # 回退到简单的工具提示
            if is_success and recognized_text:
                self._show_ocr_success_tooltip(field_name, recognized_text)
            elif is_success and not recognized_text:
                self._show_ocr_tooltip(f"未识别到文字：{field_name}")
            else:
                self._show_ocr_tooltip(f"识别失败：{field_name}")

    def _auto_recognize_and_save(self, field, x: int, y: int, w: int, h: int) -> None:
        """自动进行OCR识别并保存截图"""
        try:
            from app.ocr_engine import recognize_screen_area, save_area_screenshot
            import os
            from datetime import datetime
            
            self.append_log(f"[OCR] 开始自动识别：{field.name}，区域：({x},{y},{w},{h})")
            
            # 进行OCR文字识别，带重试机制
            recognized_text = self._recognize_with_retry(x, y, w, h, max_retries=2)
            
            if recognized_text:
                field.recognized_value = recognized_text
                # 识别结果应该显示在"识别示例"列
                field.sample_value = recognized_text
                self.append_log(f"[OCR] 自动识别成功：{field.name} = {recognized_text}")
                
                # 使用新的合并提示功能显示识别结果和坐标信息
                self._show_ocr_result_dialog(field.name, x, y, w, h, recognized_text, is_success=True)
            else:
                self.append_log(f"[OCR] 未识别到文字：{field.name}")
                # 使用新的合并提示功能显示未识别到文字的信息和坐标
                self._show_ocr_result_dialog(field.name, x, y, w, h, recognized_text=None, is_success=True)
            
            # 保存截图到识图目录
            screenshots_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{field.name}_{timestamp}.png"
            screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
            
            if save_area_screenshot(x, y, w, h, screenshot_path):
                self.append_log(f"[OCR] 截图已保存：{screenshot_path}")
            else:
                self.append_log(f"[OCR] 截图保存失败")
            
            # 保存配置
            self._save_config()
            self._refresh_ocr_tree()
            
            # 重新选中之前操作的字段，保持选中状态
            self.ocr_tree.selection_set(field.field_id)
            self.ocr_tree.focus(field.field_id)
            
        except Exception as e:
            self.append_log(f"[OCR] 自动识别失败：{e}")
            # 使用新的合并提示功能显示识别失败的信息和坐标
            self._show_ocr_result_dialog(field.name, x, y, w, h, recognized_text=None, is_success=False)

    def _set_field_rect_manual(self, field) -> None:
        """手动输入坐标方式（备用方案）"""
        answer = simpledialog.askstring(
            "设置识别区域",
            "请输入屏幕区域 x,y,width,height：",
            initialvalue=(
                f"{field.recognition_area.x},{field.recognition_area.y},{field.recognition_area.width},{field.recognition_area.height}"
                if field.recognition_area
                else ""
            ),
        )
        if not answer:
            return
        try:
            x, y, w, h = [int(part.strip()) for part in answer.split(",")]
            from app.config_manager import Rect

            field.recognition_area = Rect(x=x, y=y, width=w, height=h)
            self._save_config()
            self.append_log(f"[OCR] 已设置 {field.name} 区域：({x},{y},{w},{h})")
            # 重新选中之前操作的字段，保持选中状态
            self.ocr_tree.selection_set(field.field_id)
            self.ocr_tree.focus(field.field_id)
        except Exception:
            messagebox.showerror("错误", "格式错误，应为 x,y,width,height")

    def recognize_field(self) -> None:
        field = self._get_selected_field()
        if not field:
            return
            
        # 检查是否有识图坐标
        if not field.recognition_area:
            messagebox.showinfo("提示", "该字段无有效识图坐标")
            return
            
        # 如果有识图坐标，自动进行OCR识别
        try:
            from app.ocr_engine import recognize_screen_area
            
            x = field.recognition_area.x
            y = field.recognition_area.y
            w = field.recognition_area.width
            h = field.recognition_area.height
            
            self.append_log(f"[OCR] 开始识别字段：{field.name}，区域：({x},{y},{w},{h})")
            
            # 进行OCR文字识别，带重试机制
            recognized_text = self._recognize_with_retry(x, y, w, h, max_retries=2)
            
            if recognized_text:
                # 特殊处理：年龄字段只保留数字
                if field.name == "年龄":
                    import re
                    # 提取所有数字，去掉汉字如"岁"、"月"等
                    numbers = re.findall(r'\d+', recognized_text)
                    if numbers:
                        cleaned_text = ''.join(numbers)
                        self.append_log(f"[OCR] 年龄字段清理：'{recognized_text}' → '{cleaned_text}'")
                        recognized_text = cleaned_text
                
                field.recognized_value = recognized_text
                # 识别结果应该显示在"识别示例"列
                field.sample_value = recognized_text
                self._save_config()
                self._refresh_ocr_tree()
                # 重新选中之前操作的字段，保持选中状态
                self.ocr_tree.selection_set(field.field_id)
                self.ocr_tree.focus(field.field_id)
                self.append_log(f"[OCR] 识别成功：{field.name} = {recognized_text}")
                # 使用新的合并提示功能显示识别结果和坐标信息
                self._show_ocr_result_dialog(field.name, x, y, w, h, recognized_text, is_success=True)
            else:
                self.append_log(f"[OCR] 未识别到文字：{field.name}")
                # 使用新的合并提示功能显示未识别到文字的信息和坐标
                self._show_ocr_result_dialog(field.name, x, y, w, h, recognized_text=None, is_success=True)
                
        except Exception as e:
            self.append_log(f"[OCR] 识别失败：{e}")
            # 如果OCR识别失败，回退到手动输入方式
            value = simpledialog.askstring(
                "识别结果",
                f"OCR识别失败，请手动录入字段“{field.name}”的识别值：",
                initialvalue=field.recognized_value or field.sample_value or field.default_value,
            )
            if value is not None:
                field.recognized_value = value.strip()
                self._save_config()
                self._refresh_ocr_tree()
                # 重新选中之前操作的字段，保持选中状态
                self.ocr_tree.selection_set(field.field_id)
                self.ocr_tree.focus(field.field_id)

    def delete_field(self) -> None:
        field = self._get_selected_field()
        if not field:
            return
        if field.builtin:
            messagebox.showinfo("提示", "内置字段不可删除")
            return
        self.config.ocr_fields = [f for f in self.config.ocr_fields if f.field_id != field.field_id]
        self._save_config()
        self._refresh_ocr_tree()

    # --- service config helper
    def _update_service_url(self, version: str, field_name: str, var: tk.StringVar) -> None:
        value = var.get().strip()
        version_cfg = self.config.service.versions.get(version)
        if not version_cfg:
            version_cfg = ServiceVersionConfig()
            self.config.service.versions[version] = version_cfg
        if field_name == "verify":
            version_cfg.verify_url = value
        elif field_name == "bind":
            version_cfg.bind_url = value
        elif field_name == "debug":
            version_cfg.debug_url = value
        self._save_service_config()

    def _on_service_version_change(self) -> None:
        self.config.service.selected_version = self.service_version_var.get()
        self._save_service_config()

    def _save_service_config(self) -> None:
        self.config.service.enable_verification = self.verify_enabled_var.get()
        self.config.service.popup_success = self.popup_success_var.get()
        self.config.service.popup_failure = self.popup_failure_var.get()
        self._save_config()

    def _refresh_service_form(self) -> None:
        self.service_version_var.set(self.config.service.selected_version)
        self.verify_enabled_var.set(self.config.service.enable_verification)
        self.popup_success_var.set(self.config.service.popup_success)
        self.popup_failure_var.set(self.config.service.popup_failure)

    # --- backend config helper
    def _refresh_backend_form(self) -> None:
        self.submission_mode_var.set(self.config.backend.submission_mode)
        self.auto_delay_var.set(self.config.backend.auto_delay_seconds)
        self.startup_var.set(self.config.backend.enable_startup)
        self.float_var.set(self.config.backend.enable_float_input)
        self.service_var.set(self.config.backend.enable_service)
        if hasattr(self, "hid_enabled_var"):
            self.hid_enabled_var.set(self.config.hid.enabled)
        if hasattr(self, "hid_keywords_var"):
            self.hid_keywords_var.set(";".join(self.config.hid.device_keywords))
        if hasattr(self, "hid_digits_var"):
            self.hid_digits_var.set(self.config.hid.digit_length)
        if hasattr(self, "hid_require_enter_var"):
            self.hid_require_enter_var.set(self.config.hid.require_enter)

    def _on_backend_change(self) -> None:
        self.config.backend.submission_mode = self.submission_mode_var.get()
        self.config.backend.auto_delay_seconds = int(self.auto_delay_var.get())
        self.config.backend.enable_startup = self.startup_var.get()
        self.config.backend.enable_float_input = self.float_var.get()
        self.config.backend.enable_service = self.service_var.get()
        self._save_config()
        set_startup(self.config.backend.enable_startup)
        if self.config.backend.enable_float_input:
            self._ensure_float_window(show=True)
        elif self.float_window:
            self.float_window._hide()

    def _apply_hid_form(self) -> None:
        keywords_raw = self.hid_keywords_var.get()
        keywords = [kw.strip() for kw in keywords_raw.split(";") if kw.strip()]
        try:
            digits = int(self.hid_digits_var.get())
        except Exception:
            digits = self.config.hid.digit_length
        digits = max(1, digits)
        self.hid_digits_var.set(digits)
        self.config.hid.enabled = self.hid_enabled_var.get()
        self.config.hid.device_keywords = keywords
        self.config.hid.digit_length = digits
        self.config.hid.require_enter = self.hid_require_enter_var.get()
        self._save_config()

        self.append_log("HID 配置已更新。")

    # --- BLE actions
    def append_log(self, line: str) -> None:
        def _append() -> None:
            self.log_text.insert(tk.END, f"[{_human_now()}] {line}\n")
            self.log_text.see(tk.END)
        self.root.after(0, _append)

    def on_devices_updated(self, devices: List[ConnectedDevice]) -> None:
        def _update() -> None:
            # 只显示已连接的设备，隐藏已配对但未连接的设备
            connected_devices = [d for d in devices if d.is_connected]
            self.scanned_devices = connected_devices
            self.devices_list.delete(0, tk.END)
            for d in connected_devices:
                self.devices_list.insert(tk.END, f"{d.name} | {d.address} | 已连接")
            
            # 更新状态信息
            if not connected_devices:
                self.append_log("未找到已连接的蓝牙设备，请确认设备已在系统中连接。")
            else:
                self.append_log(f"找到 {len(connected_devices)} 个已连接的蓝牙设备")
        self.root.after(0, _update)

    def on_device_event(self, event: str, device: Optional[BLEDevice]) -> None:
        if event == "connected":
            self.status_var.set(f"已连接：{device.name or '未知'} | {device.address}")
            self.root.after(0, lambda: self.disconnect_button.configure(state=tk.NORMAL))
            label = (device.name or device.address) if device else "BLE 设备"
            self._enable_hid_capture(label)
        elif event == "disconnected":
            self.status_var.set("已断开")
            self.root.after(0, lambda: self.connect_button.configure(state=tk.NORMAL))
            self._disable_hid_capture()

    def on_scan(self) -> None:
        self.connect_button.configure(state=tk.DISABLED)
        self.disconnect_button.configure(state=tk.DISABLED)
        self.devices_list.delete(0, tk.END)
        self.append_log("正在读取系统已配对/连接的蓝牙设备...")

        def _task() -> None:
            try:
                self.append_log("开始获取系统蓝牙设备列表...")
                print(f"[DEBUG] 开始调用 list_connected_bluetooth_devices")
                from app.system_devices import list_connected_bluetooth_devices
                devices = list_connected_bluetooth_devices()
                self.append_log(f"系统返回 {len(devices)} 个蓝牙设备")
                if not devices:
                    self.append_log("未获取到蓝牙设备，请确认已在系统中完成配对。")
            except Exception as exc:
                import traceback
                error_msg = f"获取系统蓝牙设备失败: {exc}"
                self.append_log(error_msg)
                print(f"[DEBUG] 扫描错误详情: {error_msg}")
                print(f"[DEBUG] 错误堆栈: {traceback.format_exc()}")
                devices = []
            self.on_devices_updated(devices)

        self.executor.submit(_task)

    def on_select(self, _evt: object) -> None:
        sel = self.devices_list.curselection()
        self.connect_button.configure(state=tk.NORMAL if sel else tk.DISABLED)

    def _get_selected_device(self) -> Optional[ConnectedDevice]:
        sel = self.devices_list.curselection()
        if not sel:
            return None
        index = sel[0]
        if index >= len(self.scanned_devices):
            return None
        return self.scanned_devices[index]

    def on_connect(self) -> None:
        device = self._get_selected_device()
        if not device:
            return
        self.current_device = device
        self.connect_button.configure(state=tk.DISABLED)
        self.disconnect_button.configure(state=tk.DISABLED)
        display_name = f"{device.name} | {device.address}"
        status = "已连接" if device.is_connected else ("已配对" if device.is_paired else "未连接")
        self.status_var.set(f"已选择：{display_name}（{status}）")
        self.append_log(f"已选择设备：{display_name}，开始通过BLE接收数据。")
        self.root.after(0, lambda: self.disconnect_button.configure(state=tk.NORMAL))

    def on_disconnect(self) -> None:
        self.current_device = None
        self.status_var.set("已断开")
        self.append_log("已断开与蓝牙设备的连接。")
        self.connect_button.configure(state=tk.NORMAL)
        self.disconnect_button.configure(state=tk.DISABLED)

    # --- Workflow
    def on_card_data(self, data: Dict[str, str]) -> None:
        # 记录接收到的数据
        self.append_log(f"[调试] on_card_data接收到数据: {data}")
        
        # 特别标记Bluetooth Keyboard设备的数据
        if "Bluetooth Keyboard" in data['source']:
            self.append_log(f"[调试] 处理Bluetooth Keyboard设备数据")
        
        self.latest_card = data
        self.append_log(f"[调试] 更新latest_card变量")
        
        # 更新UI显示
        self.card_var.set(f"监听到卡号：8H {data['hex']} / 10D {data['dec']} (来源 {data['source']})")
        self.append_log(f"[调试] 更新UI显示")
        
        # 记录标准日志
        self.append_log(f"捕获卡号 8H={data['hex']} 10D={data['dec']} 来源={data['source']}")
        
        # 避免循环调用：优化判断条件
        # 1. 检查数据来源，如果已经是BLE来源则不传递给HID监听器
        # 2. 对于Bluetooth Keyboard设备，避免不必要的数据传递
        is_ble_source = data['source'].startswith('BLE:')
        is_bluetooth_keyboard = "Bluetooth Keyboard" in data['source']
        
        self.append_log(f"[调试] 循环检测: is_ble_source={is_ble_source}, is_bluetooth_keyboard={is_bluetooth_keyboard}")
        
        if (self.hid_listener and 
            hasattr(self, 'current_device') and 
            self.current_device and 
            not is_ble_source and 
            not is_bluetooth_keyboard):  # 避免循环调用
            try:
                self.append_log(f"[调试] 将数据传递给HID监听器处理")
                self.hid_listener.process_bluetooth_data(data['dec'], self.current_device.name)
            except Exception as e:
                self.append_log(f"[错误] 传递数据给HID监听器失败: {e}")
        else:
            self.append_log(f"[调试] 跳过数据传递给HID监听器（避免循环或不适合处理）")
        
        # 根据配置启动服务
        self.append_log(f"[调试] 配置服务状态: enable_service={self.config.backend.enable_service}")
        if self.config.backend.enable_service:
            self.append_log(f"[调试] 服务版本: {self.config.service.selected_version}")
            if self.config.service.selected_version == "v0":
                self.append_log("检测到V0.0版本，自动执行调试功能...")
                self._debug_v0_system(auto_mode=True)
            else:
                self.append_log(f"[调试] 启动工作流处理")
                self._start_workflow(data)

    def _collect_field_values(self) -> Dict[str, str]:
        payload: Dict[str, str] = {}
        for field in self.config.ocr_fields:
            if not field.enabled:
                continue
            value = field.recognized_value or field.default_value
            payload[field.param_name] = value
        return payload

    def _debug_v0_system(self, auto_mode: bool = False) -> None:
        """V0.0 第三套系统调试接口 - 重新进行OCR识图
        
        Args:
            auto_mode: 是否为自动模式（刷卡触发），如果是则不显示消息框
        """
        try:
            # 获取v0版本的调试URL
            v0_config = self.config.service.versions.get("v0")
            if not v0_config or not v0_config.debug_url:
                if not auto_mode:
                    messagebox.showerror("错误", "请先配置V0.0版本的调试URL")
                self.append_log("错误：V0.0版本的调试URL未配置")
                return
            
            debug_url = v0_config.debug_url.strip()
            if not debug_url:
                if not auto_mode:
                    messagebox.showerror("错误", "调试URL不能为空")
                self.append_log("错误：V0.0版本的调试URL为空")
                return
            
            self.append_log("开始执行V0.0系统调试，重新进行OCR识图...")
            self.append_log(f"调试URL: {debug_url}")
            
            # 获取OCR引擎
            try:
                from app.ocr_engine import get_ocr_engine
                ocr_engine = get_ocr_engine()
                self.append_log(f"OCR引擎初始化成功: {type(ocr_engine).__name__}")
            except Exception as e:
                if not auto_mode:
                    messagebox.showerror("错误", f"OCR引擎初始化失败: {str(e)}")
                self.append_log(f"错误：OCR引擎初始化失败: {str(e)}")
                return
            
            # 收集OCR字段值（排除卡ID和诊疗时间）
            params = []
            excluded_fields = {"卡ID", "诊疗时间"}  # 排除的字段名称
            total_fields = 0
            processed_fields = 0
            valid_params = 0
            
            self.append_log(f"开始遍历OCR字段，总共 {len(self.config.ocr_fields)} 个字段")
            
            for field in self.config.ocr_fields:
                total_fields += 1
                self.append_log(f"处理字段 {total_fields}: '{field.name}' (enabled: {field.enabled}, param_name: {field.param_name})")
                
                if not field.enabled:
                    self.append_log(f"  字段 '{field.name}' 被禁用，跳过")
                    continue
                if field.name in excluded_fields:
                    self.append_log(f"  字段 '{field.name}' 在排除列表中，跳过")
                    continue
                
                processed_fields += 1
                value = ""
                
                if not field.recognition_area:
                    # 如果没有识别区域，使用默认值
                    value = field.default_value or ""
                    self.append_log(f"  字段 '{field.name}' 无识别区域，使用默认值: '{value}'")
                else:
                    # 重新进行OCR识图
                    try:
                        # 处理不同格式的坐标数据
                        if hasattr(field.recognition_area, 'x') and hasattr(field.recognition_area, 'y') and hasattr(field.recognition_area, 'width') and hasattr(field.recognition_area, 'height'):
                            # Rect对象格式（来自config_manager.py）
                            x = field.recognition_area.x
                            y = field.recognition_area.y
                            w = field.recognition_area.width
                            h = field.recognition_area.height
                        elif isinstance(field.recognition_area, dict):
                            # 字典格式
                            x = field.recognition_area.get('x', 0)
                            y = field.recognition_area.get('y', 0)
                            w = field.recognition_area.get('width', 0)
                            h = field.recognition_area.get('height', 0)
                        elif isinstance(field.recognition_area, (list, tuple)) and len(field.recognition_area) == 4:
                            # 列表/元组格式
                            x, y, w, h = field.recognition_area
                        else:
                            raise ValueError(f"不支持的坐标格式: {type(field.recognition_area)} - {field.recognition_area}")
                        
                        self.append_log(f"  正在识别字段 '{field.name}' 坐标: ({x}, {y}, {w}, {h})")
                        
                        # 从屏幕指定区域识别文字
                        recognized_text = ocr_engine.recognize_from_screen_area(x, y, w, h)
                        self.append_log(f"  原始识别结果: '{recognized_text}'")
                        
                        if recognized_text.strip():
                            value = recognized_text.strip()
                            
                            # 特殊处理：年龄字段只保留数字
                            if field.name == "年龄":
                                import re
                                # 提取所有数字，去掉汉字如"岁"、"月"等
                                numbers = re.findall(r'\d+', value)
                                if numbers:
                                    value = ''.join(numbers)
                                    self.append_log(f"  年龄字段清理后: '{value}' (原始: '{recognized_text.strip()}')")
                                else:
                                    self.append_log(f"  年龄字段未提取到数字，使用原始值: '{value}'")
                            
                            # 更新字段的识别结果
                            field.recognized_value = value
                            self.append_log(f"  字段 '{field.name}' 识别成功: '{value}'")
                        else:
                            # 识别失败，使用默认值
                            value = field.default_value or ""
                            field.recognized_value = ""
                            self.append_log(f"  字段 '{field.name}' 识别为空，使用默认值: '{value}'")
                            
                    except Exception as e:
                        # 识别过程出错，使用默认值
                        value = field.default_value or ""
                        self.append_log(f"  字段 '{field.name}' 识别出错: {str(e)}，使用默认值: '{value}'")
                
                # 检查参数名和值
                self.append_log(f"  字段 '{field.name}' 最终值: '{value}', param_name: '{field.param_name}'")
                if field.param_name and value:
                    param_entry = f"{field.param_name}={value}"
                    params.append(param_entry)
                    valid_params += 1
                    self.append_log(f"  ✓ 添加参数: {param_entry}")
                else:
                    reason = []
                    if not field.param_name:
                        reason.append("无参数名")
                    if not value:
                        reason.append("无值")
                    self.append_log(f"  ✗ 跳过参数: {'且'.join(reason)}")
            
            self.append_log(f"字段处理统计: 总共 {total_fields} 个, 处理 {processed_fields} 个, 有效参数 {valid_params} 个")
            self.append_log(f"生成的参数列表: {params}")
            
            # 保存配置更新（识别结果已更新到字段中）
            self._save_config()
            self._refresh_ocr_tree()  # 刷新显示
            
            # 构建参数字符串
            param_string = "&".join(params)
            self.append_log(f"参数字符串: '{param_string}'")
            
            # 构建完整的URL
            if "?" in debug_url:
                full_url = f"{debug_url}{param_string}"
            else:
                full_url = f"{debug_url}?{param_string}"
            
            self.append_log(f"最终调试URL: {full_url}")
            
            # 在默认浏览器中打开URL
            import webbrowser
            webbrowser.open(full_url)
            
            self.append_log("V0.0系统调试完成，已在浏览器中打开调试URL")
            if not auto_mode:
                messagebox.showinfo("成功", f"OCR重新识图完成，共识别 {valid_params} 个参数，调试URL已在浏览器中打开")
            
        except Exception as e:
            error_msg = f"V0.0系统调试失败: {str(e)}"
            self.append_log(error_msg)
            if not auto_mode:
                messagebox.showerror("错误", error_msg)

    def _start_workflow(self, card: Dict[str, str]) -> None:
        # V2版本特殊处理：先不执行OCR，直接将10D卡号拼接到URL后面发送GET请求
        if self.config.service.selected_version == "v2":
            self.append_log("[V2版本] 开始处理，先不执行OCR识别...")
            
            # 直接使用10D卡号，不执行OCR
            card_dec = card.get("dec")
            
            if self.config.service.enable_verification:
                self.append_log("[V2版本] 调用洗消验证接口...")
                selected_version = self.config.service.get_selected_version()
                
                # 构建简化的payload，只包含必要信息
                payload = {
                    "card_hex": card.get("hex"),
                    "card_dec": card_dec,
                    "timestamp": _human_now(),
                    "fields": {},  # 先不包含OCR字段
                }
                
                # V2版本使用GET请求
                self._get_request(
                    selected_version.verify_url,
                    payload,
                    on_success=lambda data: self._after_v2_verify(True, data, card),
                    on_error=lambda err: self._after_v2_verify(False, err, card),
                )
            else:
                # 如果未启用验证，直接执行OCR
                self.append_log("[V2版本] 未启用验证，直接执行OCR识别...")
                self._perform_ocr_and_continue(card)
        else:
            # 其他版本保持原有逻辑
            field_values = self._collect_field_values()
            missing = [f.name for f in self.config.ocr_fields if f.enabled and not (f.recognized_value or f.default_value)]
            if missing:
                messagebox.showwarning("字段缺失", f"以下字段缺失，已使用空值：{', '.join(missing)}")
            payload = {
                "card_hex": card.get("hex"),
                "card_dec": card.get("dec"),
                "timestamp": _human_now(),
                "fields": field_values,
            }
            if self.config.service.enable_verification:
                self.append_log("开始调用洗消验证接口...")
                selected_version = self.config.service.get_selected_version()
                # 其他版本使用POST请求
                self._post_request(
                    selected_version.verify_url,
                    payload,
                    on_success=lambda data: self._after_verify(True, data, payload),
                    on_error=lambda err: self._after_verify(False, err, payload),
                )
            else:
                self._open_binding_dialog(payload)

    def _after_v2_verify(self, ok: bool, response: Dict, card: Dict[str, str]) -> None:
        """V2版本验证后的处理"""
        # 记录完整响应内容以便调试
        self.append_log(f"[V2版本] 洗消验证响应内容: {response}")
        
        if ok:
            # 确保response是字典类型
            if isinstance(response, dict):
                # 获取状态码
                code = response.get("code")
                self.append_log(f"[V2版本] 洗消验证接口返回状态码: {code}")
                
                if code == 200:
                    self.append_log(f"[V2版本] 洗消验证接口返回成功 (code=200)")
                    
                    # 检查返回内容的 "data.status.first" 是否等于 "可用"
                    data = response.get("data", {})
                    if data and isinstance(data, dict):
                        status = data.get("status", {})
                        if status and isinstance(status, dict):
                            first_status = status.get("first")
                            if first_status == "可用":
                                self.append_log("[V2版本] 验证状态：可用，开始执行OCR识别...")
                                
                                # 验证合格后执行OCR识别
                                self._perform_ocr_and_continue(card)
                                return
                        
                    # 如果没有 "data.status.first" 或不等于 "可用"，检查是否有 "msg" 字段
                    if "msg" in response:
                        msg = response.get("msg", "验证失败")
                        self.append_log(f"[V2版本] 验证失败：{msg}")
                        if self.config.service.popup_failure:
                            messagebox.showerror("洗消验证", f"验证失败：{msg}")
                    else:
                        # 其他情况
                        self.append_log("[V2版本] 验证失败：返回内容格式不符合要求")
                        if self.config.service.popup_failure:
                            messagebox.showerror("洗消验证", "验证失败：返回内容格式不符合要求")
                else:
                    # 响应状态码不是200，检查是否有 "msg" 字段
                    if "msg" in response:
                        msg = response.get("msg", "验证失败")
                        self.append_log(f"[V2版本] 验证失败：{msg}")
                        if self.config.service.popup_failure:
                            messagebox.showerror("洗消验证", f"验证失败：{msg}")
                    else:
                        # 其他情况
                        text = response.get("message", "验证失败")
                        self.append_log(f"[V2版本] 验证失败: {text}")
                        if self.config.service.popup_failure:
                            messagebox.showerror("洗消验证", f"验证失败：{text}")
            else:
                # response不是字典类型
                text = str(response)
                self.append_log(f"[V2版本] 验证失败: {text}")
                if self.config.service.popup_failure:
                    messagebox.showerror("洗消验证", f"验证失败：{text}")
        else:
            # 请求失败的情况
            if isinstance(response, dict):
                # 检查是否有 "error" 或 "msg" 字段
                if "error" in response:
                    msg = response.get("error", "验证失败")
                elif "msg" in response:
                    msg = response.get("msg", "验证失败")
                else:
                    msg = "验证失败"
            else:
                msg = str(response)
                
            self.append_log(f"[V2版本] 洗消验证失败: {msg}")
            if self.config.service.popup_failure:
                messagebox.showerror("洗消验证", f"验证失败：{msg}")
    
    def _perform_ocr_and_continue(self, card: Dict[str, str]) -> None:
        """执行OCR识别并继续后续流程"""
        try:
            # 执行OCR识别所有字段
            for field in self.config.ocr_fields:
                if field.enabled and field.recognition_area:
                    x = field.recognition_area.x
                    y = field.recognition_area.y
                    w = field.recognition_area.width
                    h = field.recognition_area.height
                    
                    self.append_log(f"[OCR] 开始识别字段：{field.name}，区域：({x},{y},{w},{h})")
                    
                    # 进行OCR文字识别，带重试机制
                    recognized_text = self._recognize_with_retry(x, y, w, h, max_retries=2)
                    
                    if recognized_text:
                        # 特殊处理：年龄字段只保留数字
                        if field.name == "年龄":
                            import re
                            # 提取所有数字，去掉汉字如"岁"、"月"等
                            numbers = re.findall(r'\d+', recognized_text)
                            if numbers:
                                cleaned_text = ''.join(numbers)
                                self.append_log(f"[OCR] 年龄字段清理：'{recognized_text}' → '{cleaned_text}'")
                                recognized_text = cleaned_text
                        
                        field.recognized_value = recognized_text
                        self.append_log(f"[OCR] 识别成功：{field.name} = {recognized_text}")
                    else:
                        self.append_log(f"[OCR] 未识别到文字：{field.name}")
            
            # 保存OCR结果
            self._save_config()
            self._refresh_ocr_tree()
            
            # 收集OCR识别结果
            field_values = self._collect_field_values()
            missing = [f.name for f in self.config.ocr_fields if f.enabled and not (f.recognized_value or f.default_value)]
            if missing:
                self.append_log(f"[V2版本] 以下字段缺失，已使用空值：{', '.join(missing)}")
            
            # 构建完整payload
            payload = {
                "card_hex": card.get("hex"),
                "card_dec": card.get("dec"),
                "timestamp": _human_now(),
                "fields": field_values,
            }
            
            # 继续后续流程
            self.append_log("[V2版本] OCR识别完成，打开绑定对话框...")
            self._open_binding_dialog(payload)
            
        except Exception as e:
            self.append_log(f"[V2版本] OCR识别过程中出错: {e}")
            messagebox.showerror("OCR识别错误", f"OCR识别过程中发生错误：{e}")
    
    def _after_verify(self, ok: bool, response: Dict, payload: Dict) -> None:
        if ok:
            text = response.get("message") if isinstance(response, dict) else str(response)
            self.append_log(f"洗消验证成功: {text}")
            if self.config.service.popup_success:
                messagebox.showinfo("洗消验证", f"验证通过：{text}")
            self._open_binding_dialog(payload)
        else:
            msg = response.get("error") if isinstance(response, dict) else response
            self.append_log(f"洗消验证失败: {msg}")
            if self.config.service.popup_failure:
                messagebox.showerror("洗消验证", f"验证失败：{msg}")

    def _open_binding_dialog(self, payload: Dict) -> None:
        self.pending_binding_payload = payload
        if self.binding_dialog:
            self.binding_dialog.destroy()
        source = (self.latest_card or {}).get("source", "BLE")
        card_info = {"hex": payload.get("card_hex", ""), "dec": payload.get("card_dec", ""), "source": source}
        auto = self.config.backend.submission_mode == "auto"
        seconds = self.config.backend.auto_delay_seconds
        self.binding_dialog = BindingDialog(
            self.root,
            card_info=card_info,
            field_values=payload.get("fields", {}),
            auto_submit=auto,
            auto_seconds=seconds,
            on_submit=self._submit_binding_payload,
            on_cancel=self._cancel_binding_dialog,
        )

    def _cancel_binding_dialog(self) -> None:
        self.binding_dialog = None
        self.pending_binding_payload = None

    def _submit_binding_payload(self) -> None:
        if not self.pending_binding_payload:
            return
        if self.binding_dialog:
            self.binding_dialog.show_result("提交中...")
        version = self.config.service.get_selected_version()
        self.append_log("提交信息绑定接口...")
        self._post_request(
            version.bind_url,
            self.pending_binding_payload,
            on_success=self._on_binding_success,
            on_error=self._on_binding_error,
        )

    def _on_binding_success(self, data: Dict) -> None:
        msg = data.get("message") if isinstance(data, dict) else str(data)
        self.append_log(f"信息绑定成功：{msg}")
        if self.binding_dialog:
            self.binding_dialog.show_result("提交成功")
            self.binding_dialog.destroy()
            self.binding_dialog = None
        messagebox.showinfo("信息绑定", f"提交成功：{msg}")

    def _on_binding_error(self, data: Dict) -> None:
        msg = data.get("error") if isinstance(data, dict) else str(data)
        self.append_log(f"信息绑定失败：{msg}")
        if self.binding_dialog:
            self.binding_dialog.show_result(f"提交失败：{msg}")
            self.binding_dialog.submit_btn.configure(state=tk.NORMAL)
        messagebox.showerror("信息绑定", f"提交失败：{msg}")

    def _post_request(self, url: str, payload: Dict, on_success, on_error) -> None:
        if not url:
            on_error({"error": "未配置接口地址"})
            return

        def _request():
            try:
                resp = requests.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                try:
                    return True, resp.json()
                except json.JSONDecodeError:
                    return True, {"message": resp.text}
            except Exception as exc:
                return False, {"error": str(exc)}

        future = self.executor.submit(_request)

        def _callback(fut):
            ok, result = fut.result()
            self.root.after(0, lambda: (on_success(result) if ok else on_error(result)))

        future.add_done_callback(_callback)

    def _get_request(self, url: str, payload: Dict, on_success, on_error) -> None:
        if not url:
            on_error({"error": "未配置接口地址"})
            return

        def _request():
            try:
                # 构建GET请求URL
                import urllib.parse
                
                # V2版本特殊处理：将10位数卡号删除前面4个0，保留后6位，然后拼接到URL后面
                if self.config.service.selected_version == "v2":
                    card_dec = payload.get("card_dec", "")
                    
                    # 处理卡号：删除前面4个0，保留后6位
                    if len(card_dec) == 10 and card_dec.startswith("0000"):
                        processed_card = card_dec[4:]
                        self.append_log(f"[V2] 卡号处理：{card_dec} → {processed_card}")
                    else:
                        # 如果不是10位或不以前4个0开头，使用原始卡号
                        processed_card = card_dec
                        self.append_log(f"[V2] 卡号未处理：{processed_card}")
                    
                    # 确保URL和卡号之间没有多余的分隔符
                    if url.endswith("/"):
                        full_url = f"{url}{processed_card}"
                    else:
                        full_url = f"{url}{processed_card}"
                    
                    self.append_log(f"[V2] 发送GET请求: {full_url}")
                    
                    resp = requests.get(full_url, timeout=10)
                    resp.raise_for_status()
                    
                    self.append_log(f"[V2] 响应状态码: {resp.status_code}")
                    self.append_log(f"[V2] 响应内容: {resp.text}")
                    
                    try:
                        return True, resp.json()
                    except json.JSONDecodeError:
                        return True, {"message": resp.text}
                else:
                    # 其他版本使用标准GET参数
                    params = {}
                    
                    # 提取需要的参数
                    if payload.get("card_hex"):
                        params["card_hex"] = payload["card_hex"]
                    if payload.get("card_dec"):
                        params["card_dec"] = payload["card_dec"]
                    
                    # 添加fields中的参数
                    for field_name, field_value in payload.get("fields", {}).items():
                        params[field_name] = field_value
                    
                    # 构建完整URL
                    if "?" in url:
                        if url.endswith("?"):
                            full_url = url + urllib.parse.urlencode(params)
                        else:
                            full_url = url + "&" + urllib.parse.urlencode(params)
                    else:
                        full_url = url + "?" + urllib.parse.urlencode(params)
                    
                    self.append_log(f"[GET] 发送请求: {full_url}")
                    
                    resp = requests.get(full_url, timeout=10)
                    resp.raise_for_status()
                    
                    self.append_log(f"[GET] 响应状态码: {resp.status_code}")
                    self.append_log(f"[GET] 响应内容: {resp.text}")
                    
                    try:
                        return True, resp.json()
                    except json.JSONDecodeError:
                        return True, {"message": resp.text}
            except Exception as exc:
                error_msg = str(exc)
                self.append_log(f"[V2] 请求失败: {error_msg}")
                return False, {"error": error_msg}

        future = self.executor.submit(_request)

        def _callback(fut):
            ok, result = fut.result()
            self.root.after(0, lambda: (on_success(result) if ok else on_error(result)))

        future.add_done_callback(_callback)

    # --- other helpers
    def _save_config(self) -> None:
        self.config_manager.save(self.config)

    def _ensure_float_window(self, show: bool = False) -> None:
        if self.float_window is None or not self.float_window.winfo_exists():
            self.float_window = FloatInputWindow(self.root, self._on_manual_card_input)
        if show:
            self.float_window.deiconify()

    def _on_manual_card_input(self, value: str) -> None:
        clean = value.strip().replace(" ", "")
        hex_value = ""
        dec_value = ""
        if not clean:
            return
        if clean.isdigit():
            dec_value = clean
            try:
                hex_value = f"{int(clean):08X}"
            except Exception:
                hex_value = clean
        else:
            hex_candidate = clean.upper()
            try:
                dec_value = f"{int(hex_candidate, 16):010d}"
                hex_value = f"{int(hex_candidate, 16):08X}"
            except Exception:
                hex_value = hex_candidate
                dec_value = hex_candidate
        card = {"hex": hex_value, "dec": dec_value, "source": "浮球"}
        self.on_card_data(card)

    def _restart_hid_listener(self) -> None:
        """重启HID监听器 - 在HID功能启用时启动，无需BLE设备连接"""
        self.append_log(f"[调试] 开始重启HID监听器")
        
        if os.name != "nt":
            self.append_log("[调试] 非Windows系统，不支持HID监听")
            return
        
        # 停止之前的监听器
        if self.hid_listener:
            self.append_log("[调试] 停止之前的HID监听器")
            self.hid_listener.stop()
            self.hid_listener = None
            self.bound_hid_device = None
        
        # 只有当HID功能启用时才启动监听器
        self.append_log(f"[调试] HID配置状态: enabled={self.config.hid.enabled}")
        if not self.config.hid.enabled:
            self.append_log("HID监听：功能未启用，不启动监听器")
            return
            
        self.append_log(f"[调试] HID配置参数: digit_length={self.config.hid.digit_length}, require_enter={self.config.hid.require_enter}")
        self.append_log(f"[调试] 设备关键字: {self.config.hid.device_keywords}")
        
        try:
            self.hid_listener = HidListener(
                device_keywords=self.config.hid.device_keywords,
                digit_length=self.config.hid.digit_length,
                require_enter=self.config.hid.require_enter,
                callback=self._on_hid_card,
                logger=self.append_log,
            )
            self.append_log(f"[调试] HID监听器实例创建成功")
            start_result = self.hid_listener.start()
            self.append_log(f"[调试] HID监听器start()调用结果: {start_result}")
            self.append_log("HID监听：已启动蓝牙数据监听器，等待HID设备输入")
        except Exception as e:
            self.append_log(f"[错误] 启动HID监听器失败: {e}")
            import traceback
            self.append_log(f"[错误] 详细错误堆栈: {traceback.format_exc()}")

    def _stop_hid_listener(self) -> None:
        if self.hid_listener:
            self.hid_listener.stop()
            try:
                self.hid_listener.join(timeout=1.0)
            except Exception:
                pass
            self.hid_listener = None

    def _enable_hid_capture(self, label: str) -> None:
        """启用蓝牙设备HID捕获"""
        if not self.config.hid.enabled:
            return
            
        self.hid_accepting = True
        self.bound_hid_device = None
        self.hid_expected_label = label or "目标刷卡器"
        self.append_log(f"蓝牙数据监听：准备接收设备 {self.hid_expected_label} 的数据。")
        
        # 设备连接后启动监听器
        self._restart_hid_listener()

    def _disable_hid_capture(self) -> None:
        self.hid_accepting = False
        self.bound_hid_device = None
        self.hid_expected_label = ""

    def _on_hid_card(self, value: str, device_name: str) -> None:
        """处理蓝牙设备发送的卡号数据"""
        def _handle() -> None:
            # 添加详细调试日志
            self.append_log(f"[调试] HID监听器收到数据: 值={value}, 设备名={device_name}")
            
            # 特别记录"Bluetooth Keyboard"设备的数据
            if "Bluetooth Keyboard" in device_name:
                self.append_log(f"[调试] 检测到Bluetooth Keyboard设备数据: {value}")
            
            # 检查基本状态
            self.append_log(f"[调试] hid_accepting状态: {self.hid_accepting}")
            current_device_name = self.current_device.name if hasattr(self, 'current_device') and self.current_device else '无'
            self.append_log(f"[调试] 当前连接设备: {current_device_name}")
            
            # 检查设备名称匹配
            if hasattr(self, 'current_device') and self.current_device:
                if device_name.lower() != self.current_device.name.lower():
                    self.append_log(f"[调试] 设备名称不匹配: 监听器设备='{device_name}', 连接设备='{self.current_device.name}'")
                    # 尝试模糊匹配
                    if device_name.lower() in self.current_device.name.lower() or self.current_device.name.lower() in device_name.lower():
                        self.append_log("[调试] 设备名称部分匹配，继续处理")
                    else:
                        self.append_log("[调试] 设备名称完全不匹配，继续处理（允许其他设备数据）")
            
            if not self.hid_accepting:
                self.append_log("[调试] HID接收未启用，忽略数据")
                return
                
            # 确保只处理已连接蓝牙设备的数据
            if not hasattr(self, 'current_device') or not self.current_device:
                self.append_log("警告：没有连接的蓝牙设备，忽略数据")
                return
                
            # 详细记录原始值的长度和内容
            self.append_log(f"[调试] 原始值长度: {len(value)}, 内容: '{value}'")
            
            # 处理卡号数据
            self.append_log(f"[调试] 配置的数字长度: {self.config.hid.digit_length}")
            
            # 特殊处理Bluetooth Keyboard设备数据
            if "Bluetooth Keyboard" in device_name:
                self.append_log("[调试] 应用特殊处理规则到Bluetooth Keyboard数据")
                # 尝试从原始数据中提取数字部分
                numeric_part = ''.join(filter(str.isdigit, value))
                self.append_log(f"[调试] 提取的数字部分: '{numeric_part}'")
                if numeric_part:
                    dec_value = numeric_part[-self.config.hid.digit_length:].zfill(self.config.hid.digit_length)
                else:
                    self.append_log("[警告] 无法从数据中提取数字")
                    dec_value = value[-self.config.hid.digit_length:].zfill(self.config.hid.digit_length)
            else:
                # 常规处理
                dec_value = value[-self.config.hid.digit_length:].zfill(self.config.hid.digit_length)
            
            self.append_log(f"[调试] 处理后的值: '{dec_value}'")
            
            try:
                dec_int = int(dec_value)
                self.append_log(f"[调试] 转换为整数: {dec_int}")
                # 对于10位数卡号，使用10D格式，十六进制保持8位（限制为32位）
                hex_value = f"{dec_int & 0xFFFFFFFF:08X}"
                self.append_log(f"[调试] 转换为十六进制: {hex_value}")
                # 确保10D格式是10位数，不足补零
                dec_value = f"{dec_int:010d}"
                self.append_log(f"[调试] 格式化后10D值: {dec_value}")
            except Exception as e:
                self.append_log(f"[调试] 转换失败，保留原始值: {e}")
                hex_value = dec_value
                
            # 使用当前连接的蓝牙设备作为来源
            card = {"hex": hex_value, "dec": dec_value, "source": f"BLE:{device_name}"}
            self.append_log(f"蓝牙刷卡：10D={dec_value} 来自 {device_name}")
            
            # 调用on_card_data处理数据
            self.append_log(f"[调试] 准备调用on_card_data处理数据")
            self.on_card_data(card)

        # 使用after方法确保在UI线程中执行
        self.append_log(f"[调试] 调度UI线程处理")
        self.root.after(0, _handle)

    def _on_close(self) -> None:
        self._stop_hid_listener()
        if self.float_window and self.float_window.winfo_exists():
            self.float_window.destroy()
        try:
            asyncio.run_coroutine_threadsafe(self.manager.disconnect(), self.loop)
        except Exception:
            pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.executor.shutdown(wait=False)
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()


