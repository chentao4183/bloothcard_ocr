#!/usr/bin/env python3
"""
诊断HID监听状态和配置
"""
import tkinter as tk
from app.main import App
import time

def diagnose_hid_status():
    """诊断HID监听状态"""
    print("=== HID监听状态诊断 ===")
    
    # 创建主应用
    root = tk.Tk()
    root.withdraw()  # 隐藏窗口
    app = App(root)
    
    # 等待初始化
    time.sleep(2)
    
    # 检查HID配置
    print("\n1. HID配置检查:")
    print(f"   - HID启用状态: {app.config.hid.enabled}")
    print(f"   - 设备关键词: {app.config.hid.device_keywords}")
    print(f"   - 数字长度: {app.config.hid.digit_length}")
    print(f"   - 需要回车: {app.config.hid.require_enter}")
    
    # 检查HID监听器状态
    print("\n2. HID监听器状态:")
    if app.hid_listener:
        print(f"   - HID监听器已创建: {type(app.hid_listener).__name__}")
        print(f"   - HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
        print(f"   - 绑定设备: {app.bound_hid_device}")
        print(f"   - 期望标签: {app.hid_expected_label}")
    else:
        print("   ❌ HID监听器未创建")
    
    # 检查当前设备
    print("\n3. 当前设备状态:")
    if hasattr(app, 'current_device') and app.current_device:
        device = app.current_device
        print(f"   - 设备名称: {device.name}")
        print(f"   - 设备地址: {device.address}")
        print(f"   - 连接状态: {'已连接' if device.is_connected else '未连接'}")
    else:
        print("   ❌ 无当前设备")
    
    # 检查日志
    print("\n4. 最近日志:")
    try:
        log_content = app.log_text.get('1.0', tk.END)
        log_lines = log_content.strip().split('\n')
        recent_logs = log_lines[-10:] if len(log_lines) > 10 else log_lines
        for log in recent_logs:
            if log.strip():
                print(f"   {log}")
    except:
        print("   无法获取日志内容")
    
    # 测试直接刷卡
    print("\n5. 测试直接刷卡:")
    test_received = []
    
    def test_receiver(data):
        test_received.append(data)
        print(f"   📡 接收到: {data}")
    
    # 临时替换接收方法
    original_method = app.on_card_data
    app.on_card_data = test_receiver
    
    # 模拟刷卡
    if app.hid_listener:
        print("   模拟刷卡测试...")
        app._on_hid_card("1234567890", "TestDevice")
        time.sleep(1)
        
        if test_received:
            print(f"   ✅ 模拟刷卡成功，接收到 {len(test_received)} 条数据")
        else:
            print("   ❌ 模拟刷卡失败，未接收到数据")
    else:
        print("   ❌ 无法模拟刷卡，HID监听器未启动")
    
    # 恢复原始方法
    app.on_card_data = original_method
    
    # 清理
    try:
        app._on_close()
    except:
        pass
    root.quit()
    root.destroy()
    
    print("\n=== 诊断完成 ===")
    return app.hid_listener is not None

if __name__ == "__main__":
    diagnose_hid_status()