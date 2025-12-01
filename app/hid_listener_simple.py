#!/usr/bin/env python3
"""
简化版HID监听 - 使用pynput库监听键盘输入
专门处理蓝牙键盘设备的输入
"""

import threading
import time
import logging
from typing import Callable, Optional, List

# 尝试导入pynput库
HAS_PYNPUT = False
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    logging.warning("pynput库未安装，将使用模拟模式")

logger = logging.getLogger(__name__)

class SimpleHidListener:
    """简化版HID监听器 - 使用pynput库监听键盘输入"""
    
    def __init__(
        self,
        device_keywords: List[str] = None,
        digit_length: int = 10,
        require_enter: bool = False,
        callback: Optional[Callable[[str, str], None]] = None,
        logger: Optional[Callable[[str], None]] = None,
        simplified: bool = False  # 兼容性参数，忽略
    ):
        self.device_keywords = device_keywords or []
        self.digit_length = digit_length
        self.require_enter = require_enter
        self.callback = callback
        self.logger_func = logger or self._default_logger
        
        self._running = False
        self._thread = None
        self._buffer = ""
        self._last_key_time = 0
        self._key_timeout = 2.0  # 2秒内没有输入则清空缓冲区
        
        # 新增属性
        self._listener = None
        self._buffer_thread = None
        
        self._log("蓝牙刷卡器监听器初始化完成")
        self._log(f"配置: 数字长度={digit_length}, 需要回车={require_enter}")
        self._log(f"设备过滤关键词: {self.device_keywords}")
    
    def _default_logger(self, msg: str):
        """默认日志记录方法"""
        logging.info(msg)
    
    def _log(self, msg: str):
        """记录日志"""
        if self.logger_func:
            self.logger_func(f"[SimpleHID] {msg}")
    
    def start(self):
        """启动监听"""
        if self._running:
            self._log("监听器已在运行")
            return True
        
        self._running = True
        
        if HAS_PYNPUT:
            # 使用pynput库监听键盘输入
            self._log("使用pynput库监听键盘输入")
            self._listener = keyboard.Listener(on_press=self._on_key_press)
            self._listener.start()
            self._log("键盘监听器已启动")
        else:
            # 模拟模式
            self._log("pynput库未安装，使用模拟模式")
            self._thread = threading.Thread(target=self._simulate_listen_loop, daemon=True)
            self._thread.start()
        
        # 启动缓冲区超时检查线程
        self._buffer_thread = threading.Thread(target=self._buffer_check_loop, daemon=True)
        self._buffer_thread.start()
        
        self._log("监听器已启动")
        return True
    
    def stop(self):
        """停止监听"""
        self._running = False
        
        if HAS_PYNPUT and hasattr(self, '_listener'):
            self._listener.stop()
            self._listener.join(timeout=1)
        
        if hasattr(self, '_thread') and self._thread:
            self._thread.join(timeout=1)
        
        if hasattr(self, '_buffer_thread') and self._buffer_thread:
            self._buffer_thread.join(timeout=1)
        
        self._log("监听器已停止")
    
    def _on_key_press(self, key):
        """处理键盘按键事件"""
        if not self._running:
            return
        
        try:
            # 获取按键字符
            char = None
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
            elif hasattr(key, 'name'):
                # 处理特殊按键
                if key.name == 'enter' and self.require_enter:
                    self._handle_enter()
                return
            
            if char:
                self._log(f"检测到按键: {char}")
                self._handle_key(char)
        except Exception as e:
            self._log(f"处理按键事件错误: {e}")
    
    def _simulate_listen_loop(self):
        """模拟监听循环 - 用于测试"""
        self._log("运行在模拟模式，不会实际监听键盘输入")
        while self._running:
            time.sleep(1)
    
    def _buffer_check_loop(self):
        """缓冲区超时检查循环"""
        while self._running:
            time.sleep(0.1)
            self._check_buffer_timeout()
    
    def _handle_key(self, char: str):
        """处理单个按键输入"""
        if not char.isdigit():
            return
            
        current_time = time.time()
        
        # 如果超过超时时间，清空缓冲区
        if current_time - self._last_key_time > self._key_timeout:
            self._buffer = ""
            self._log("缓冲区超时，已清空")
        
        # 添加到缓冲区
        self._buffer += char
        self._last_key_time = current_time
        
        self._log(f"添加字符 '{char}' 到缓冲区，当前缓冲区: '{self._buffer}'")
        
        # 如果达到指定长度，触发回调
        if len(self._buffer) >= self.digit_length:
            # 取最后N位
            card_number = self._buffer[-self.digit_length:]
            # 使用设备关键字列表构建设备名称描述
            device_name = f"{' '.join(self.device_keywords)}" if self.device_keywords else "Bluetooth Keyboard"
            self._trigger_callback(device_name)
            
            # 如果不需要回车，则清空缓冲区
            if not self.require_enter:
                self._buffer = ""
    
    def _handle_enter(self):
        """处理回车键"""
        if self._buffer and len(self._buffer) >= self.digit_length:
            card_number = self._buffer[-self.digit_length:]
            # 使用设备关键字列表构建设备名称描述
            device_name = f"{' '.join(self.device_keywords)}" if self.device_keywords else "Bluetooth Keyboard"
            self._trigger_callback(device_name)
            self._buffer = ""
    
    def _check_buffer_timeout(self):
        """检查缓冲区超时"""
        if self._buffer and time.time() - self._last_key_time > self._key_timeout:
            self._log(f"缓冲区超时，清空内容: '{self._buffer}'")
            self._buffer = ""
    
    def _trigger_callback(self, device_name: str):
        """触发回调函数"""
        if self._buffer and len(self._buffer) >= self.digit_length:
            card_number = self._buffer[-self.digit_length:]
            self._log(f"触发回调，卡号: {card_number}，设备: {device_name}")
            
            if self.callback:
                try:
                    self.callback(card_number, device_name)
                except Exception as e:
                    self._log(f"回调函数执行错误: {e}")
    
    def process_bluetooth_data(self, data: str, device_name: str) -> None:
        """
        处理从蓝牙接收的数据
        :param data: 接收到的数据
        :param device_name: 设备名称
        """
        self._log(f"收到蓝牙数据: '{data}' 来自 {device_name}")
        
        # 验证数据格式
        if not data:
            return
            
        # 对Bluetooth Keyboard设备的特殊处理
        is_bluetooth_keyboard = "Bluetooth Keyboard" in device_name
        if is_bluetooth_keyboard:
            self._log(f"检测到Bluetooth Keyboard设备，应用特殊处理")
            
            # 提取纯数字部分
            numeric_part = ''.join(filter(str.isdigit, str(data)))
            
            if not numeric_part:
                self._log(f"警告: Bluetooth Keyboard设备数据中未找到数字: {data}")
                return
            
            self._log(f"Bluetooth Keyboard提取数字: {numeric_part}")
            
            # 添加到缓冲区
            for char in numeric_part:
                self._handle_key(char)
        else:
            # 其他蓝牙设备
            self._log(f"处理其他蓝牙设备数据: {data}")
            for char in data:
                if char.isdigit():
                    self._handle_key(char)
    
    def is_alive(self):
        """检查监听器是否活跃"""
        if HAS_PYNPUT:
            return self._running and hasattr(self, '_listener') and self._listener.is_alive
        else:
            return self._running and hasattr(self, '_thread') and self._thread.is_alive()
