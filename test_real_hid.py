#!/usr/bin/env python3
"""
测试HID监听器是否能接收实际的键盘输入
"""
import tkinter as tk
from app.main import App
import time
import threading

def test_real_hid_input():
    """测试真实HID输入"""
    print("=== 真实HID输入测试 ===")
    print("请在此窗口中输入数字测试刷卡功能")
    
    # 创建主应用
    root = tk.Tk()
    root.title("HID输入测试")
    app = App(root)
    
    # 等待初始化
    time.sleep(2)
    
    # 启用HID捕获
    app._enable_hid_capture("测试刷卡器")
    print(f"HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
    
    # 记录接收到的数据
    received_data = []
    
    def on_card_received(card_data):
        received_data.append(card_data)
        print(f"🎯 接收到卡号: {card_data}")
    
    # 临时替换接收方法
    original_method = app.on_card_data
    app.on_card_data = on_card_received
    
    print("\n测试说明:")
    print("1. 请在此窗口中输入10位数字")
    print("2. 或者输入1234567890测试")
    print("3. 输入完成后按回车键")
    print("4. 30秒后自动结束测试")
    print("5. 按ESC键可提前结束")
    
    # 运行30秒
    start_time = time.time()
    test_running = True
    
    def check_timeout():
        nonlocal test_running
        if time.time() - start_time > 30:
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
    
    # 清理
    try:
        app._on_close()
    except:
        pass
    
    print(f"\n测试结果: 接收到 {len(received_data)} 条数据")
    for i, data in enumerate(received_data):
        print(f"  {i+1}. {data}")
    
    return len(received_data) > 0

if __name__ == "__main__":
    success = test_real_hid_input()
    print(f"\n整体测试结果: {'✅ 成功' if success else '❌ 失败'}")