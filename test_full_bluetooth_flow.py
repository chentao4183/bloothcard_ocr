#!/usr/bin/env python3
"""
完整测试：验证蓝牙刷卡器数据流
"""
import tkinter as tk
from app.main import App
import time
import threading

def full_bluetooth_test():
    """完整的蓝牙刷卡测试"""
    print("=== 完整蓝牙刷卡器数据流测试 ===")
    
    # 创建主应用
    root = tk.Tk()
    root.title("完整蓝牙刷卡测试")
    app = App(root)
    
    # 等待初始化
    time.sleep(2)
    
    print(f"1. HID监听器状态:")
    print(f"   - 监听方法: {app.hid_listener._method}")
    print(f"   - 运行状态: {'运行中' if app.hid_listener._running else '停止'}")
    
    # 启用HID捕获
    app._enable_hid_capture("蓝牙刷卡器")
    print(f"\n2. HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
    
    # 记录接收到的数据
    received_data = []
    log_messages = []
    
    def on_card_received(card_data):
        received_data.append(card_data)
        print(f"🎯 接收到卡号: {card_data}")
    
    def custom_append_log(line):
        log_messages.append(line)
        print(f"📋 日志: {line}")
    
    # 临时替换方法
    original_method = app.on_card_data
    app.on_card_data = on_card_received
    original_append_log = app.append_log
    app.append_log = custom_append_log
    
    print("\n3. 请使用蓝牙刷卡器刷卡...")
    print("   测试将在60秒后结束")
    
    # 运行60秒
    start_time = time.time()
    test_running = True
    
    def check_timeout():
        nonlocal test_running
        if time.time() - start_time > 60:
            test_running = False
            print("\n⏰ 测试时间到")
        elif test_running:
            root.after(1000, check_timeout)
    
    # 开始超时检查
    root.after(1000, check_timeout)
    
    # 主循环
    while test_running and root.winfo_exists():
        try:
            root.update()
            time.sleep(0.1)
        except:
            break
    
    # 恢复原始方法
    app.on_card_data = original_method
    app.append_log = original_append_log
    
    # 清理
    try:
        app._on_close()
    except:
        pass
    
    print(f"\n=== 测试结果 ===")
    print(f"接收到 {len(received_data)} 条卡号数据:")
    for i, data in enumerate(received_data):
        print(f"  {i+1}. {data}")
    
    print(f"\n日志消息 ({len(log_messages)} 条):")
    for i, msg in enumerate(log_messages):
        print(f"  {i+1}. {msg}")
    
    success = len(received_data) > 0
    print(f"\n整体测试结果: {'✅ 成功' if success else '❌ 失败'}")
    
    return success

if __name__ == "__main__":
    full_bluetooth_test()