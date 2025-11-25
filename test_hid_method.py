#!/usr/bin/env python3
"""
检查HID监听器使用的方法，并测试pynput方法
"""
import tkinter as tk
from app.main import App
import time
import threading
import sys
from app.hid_listener_simple import SimpleHidListener

def check_hid_method():
    """检查HID监听器使用的方法"""
    print("=== HID监听器方法检查 ===")
    
    # 创建监听器实例
    listener = SimpleHidListener(
        digit_length=10,
        require_enter=False,
        callback=lambda x, y: print(f"收到: {x} 来自: {y}"),
        logger_func=lambda x: print(f"[LOG] {x}")
    )
    
    print(f"监听器方法: {listener._method}")
    print(f"pynput可用: {listener._pynput_available}")
    print(f"msvcrt可用: {listener._msvcrt_available}")
    
    # 测试pynput监听
    if listener._pynput_available:
        print("\n--- 测试pynput监听 ---")
        
        def test_callback(value, device):
            print(f"🎯 测试收到: '{value}' 来自: '{device}'")
        
        test_listener = SimpleHidListener(
            digit_length=10,
            require_enter=False,
            callback=test_callback,
            logger_func=lambda x: print(f"[TEST] {x}")
        )
        
        # 启动监听器
        if test_listener.start():
            print("pynput监听器已启动")
            print("请在键盘上输入10位数字测试...")
            
            # 运行10秒测试
            time.sleep(10)
            
            test_listener.stop()
            print("测试结束")
        else:
            print("pynput监听器启动失败")
    else:
        print("pynput不可用，尝试安装: pip install pynput")

def test_bluetooth_hid():
    """测试蓝牙HID监听"""
    print("\n=== 蓝牙HID监听测试 ===")
    
    # 创建主应用
    root = tk.Tk()
    root.title("蓝牙HID测试")
    app = App(root)
    
    # 等待初始化
    time.sleep(2)
    
    print(f"HID监听器: {app.hid_listener}")
    print(f"HID方法: {app.hid_listener._method if app.hid_listener else '无监听器'}")
    
    # 启用HID捕获
    app._enable_hid_capture("蓝牙刷卡器测试")
    print(f"HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
    
    # 记录接收到的数据
    received_data = []
    
    def on_card_received(card_data):
        received_data.append(card_data)
        print(f"🎯 蓝牙刷卡收到: {card_data}")
    
    # 临时替换接收方法
    original_method = app.on_card_data
    app.on_card_data = on_card_received
    
    print("\n请使用蓝牙刷卡器刷卡测试...")
    print("30秒后自动结束")
    
    # 运行30秒
    start_time = time.time()
    while time.time() - start_time < 30:
        try:
            root.update()
            time.sleep(0.1)
        except:
            break
    
    # 恢复原始方法
    app.on_card_data = original_method
    
    # 清理
    try:
        app._on_close()
    except:
        pass
    
    print(f"\n蓝牙测试结果: 接收到 {len(received_data)} 条数据")
    for i, data in enumerate(received_data):
        print(f"  {i+1}. {data}")
    
    return len(received_data) > 0

if __name__ == "__main__":
    # 检查HID方法
    check_hid_method()
    
    # 测试蓝牙HID
    test_bluetooth_hid()