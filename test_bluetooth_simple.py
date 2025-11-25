#!/usr/bin/env python3
"""
简化测试：检查蓝牙刷卡器数据流
"""
import tkinter as tk
from app.main import App
import time

def simple_bluetooth_test():
    """简单的蓝牙刷卡测试"""
    print("=== 蓝牙刷卡器数据流测试 ===")
    
    # 创建主应用
    root = tk.Tk()
    root.title("蓝牙刷卡器测试")
    app = App(root)
    
    # 等待初始化
    time.sleep(2)
    
    print(f"1. HID监听器状态:")
    print(f"   - 监听器存在: {'是' if app.hid_listener else '否'}")
    print(f"   - 监听方法: {app.hid_listener._method if app.hid_listener else '无'}")
    print(f"   - 运行状态: {'运行中' if app.hid_listener and app.hid_listener._running else '停止'}")
    
    # 启用HID捕获
    app._enable_hid_capture("蓝牙刷卡器")
    print(f"\n2. HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
    
    # 检查日志区域
    print(f"\n3. 日志区域状态:")
    print(f"   - 日志文本框存在: {'是' if hasattr(app, 'log_text') else '否'}")
    
    # 模拟刷卡数据
    print(f"\n4. 模拟刷卡测试:")
    test_card = "1234567890"
    
    # 直接调用_on_hid_card方法
    print(f"   - 测试卡号: {test_card}")
    app._on_hid_card(test_card, "模拟蓝牙刷卡器")
    
    # 检查日志输出
    time.sleep(1)
    
    # 获取日志内容
    try:
        log_content = app.log_text.get("1.0", tk.END)
        print(f"\n5. 日志内容预览:")
        print(f"   - 日志长度: {len(log_content)}")
        if "1234567890" in log_content:
            print(f"   - ✅ 卡号出现在日志中")
        else:
            print(f"   - ❌ 卡号未出现在日志中")
            print(f"   - 最后100字符:\n{log_content[-100:]}")
    except Exception as e:
        print(f"   - 获取日志错误: {e}")
    
    # 清理
    try:
        app._on_close()
    except:
        pass
    
    return True

if __name__ == "__main__":
    simple_bluetooth_test()