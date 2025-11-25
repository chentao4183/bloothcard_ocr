#!/usr/bin/env python3
"""
测试pynput键盘监听是否正常工作
"""
import tkinter as tk
import time
import threading
from app.main import App

def test_pynput_keyboard():
    """测试pynput键盘监听"""
    print("=== pynput键盘监听测试 ===")
    
    # 创建主应用
    root = tk.Tk()
    root.title("pynput键盘测试")
    app = App(root)
    
    # 等待初始化
    time.sleep(2)
    
    print(f"HID监听器方法: {app.hid_listener._method}")
    print(f"HID监听器运行状态: {'运行中' if app.hid_listener._running else '停止'}")
    
    # 启用HID捕获
    app._enable_hid_capture("pynput测试")
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
    print("1. 请在任何窗口中输入10位数字")
    print("2. pynput应该监听全局键盘事件")
    print("3. 输入1234567890进行测试")
    print("4. 测试将在30秒后结束")
    
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

def test_direct_pynput():
    """直接测试pynput监听"""
    print("\n=== 直接pynput测试 ===")
    
    try:
        from pynput import keyboard
        
        received_keys = []
        
        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char and key.char.isdigit():
                    received_keys.append(key.char)
                    print(f"🎯 收到数字: '{key.char}'")
                    
                    if len(received_keys) >= 10:
                        card_number = ''.join(received_keys)
                        print(f"🎯 完整卡号: {card_number}")
                        received_keys.clear()
                        
            except Exception as e:
                print(f"按键处理错误: {e}")
        
        def on_release(key):
            if key == keyboard.Key.esc:
                return False
        
        print("直接pynput监听已启动...")
        print("请在任何窗口输入10位数字，按ESC结束")
        
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
            
        return True
        
    except ImportError as e:
        print(f"pynput导入错误: {e}")
        return False

if __name__ == "__main__":
    # 先直接测试pynput
    direct_success = test_direct_pynput()
    
    # 再测试应用中的pynput
    app_success = test_pynput_keyboard()
    
    print(f"\n=== 最终测试结果 ===")
    print(f"直接pynput测试: {'✅ 成功' if direct_success else '❌ 失败'}")
    print(f"应用pynput测试: {'✅ 成功' if app_success else '❌ 失败'}")
    
    if direct_success and not app_success:
        print("\n💡 建议: pynput工作正常，但应用中可能有其他问题")
    elif not direct_success:
        print("\n💡 建议: pynput本身有问题，需要检查安装或权限")