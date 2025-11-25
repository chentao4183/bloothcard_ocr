#!/usr/bin/env python3
"""
完整版蓝牙刷卡器测试 - 增加等待时间和调试
"""
import tkinter as tk
import time
import threading
from app.main import App

def test_full_bluetooth():
    """完整测试蓝牙刷卡器功能"""
    print("=== 完整版蓝牙刷卡器功能测试 ===")
    
    # 创建主应用
    print("正在创建主应用...")
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    app = App(root)
    
    # 等待应用初始化
    time.sleep(3)
    
    # 检查HID监听器状态
    if app.hid_listener:
        print(f"✅ HID监听器已启动: {type(app.hid_listener).__name__}")
        print(f"   - 数字长度: {app.config.hid.digit_length}")
        print(f"   - 需要回车: {app.config.hid.require_enter}")
    else:
        print("❌ HID监听器未启动")
        return
    
    # 设置测试数据接收器
    received_cards = []
    
    def test_on_card_data(card_data):
        """测试用的卡片数据接收函数"""
        print(f"📡 接收到卡片数据: {card_data}")
        received_cards.append(card_data)
    
    # 替换原有的on_card_data方法
    original_on_card_data = app.on_card_data
    app.on_card_data = test_on_card_data
    
    # 启用HID监听捕获
    print("\n启用HID监听捕获...")
    app._enable_hid_capture("测试刷卡器")
    time.sleep(2)
    
    # 检查状态
    print(f"HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
    print(f"期望设备: {app.hid_expected_label}")
    
    # 测试卡号
    test_cards = [
        {"card": "1234567890", "source": "BLE Card Reader"},
        {"card": "9876543210", "source": "RFID Scanner"},
        {"card": "5555666677", "source": "Bluetooth Keyboard"}
    ]
    
    print("\n开始逐个测试卡号...")
    for i, test_data in enumerate(test_cards, 1):
        card_number = test_data["card"]
        device_name = test_data["source"]
        
        print(f"\n{'='*50}")
        print(f"第 {i} 轮测试: {card_number}")
        print(f"设备: {device_name}")
        print(f"当前绑定设备: {app.bound_hid_device}")
        print(f"HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
        
        # 直接调用_on_hid_card方法
        print(f"调用HID回调函数...")
        app._on_hid_card(card_number, device_name)
        
        # 等待GUI事件循环处理
        print("等待GUI事件处理...")
        root.update()
        time.sleep(2)
        root.update()
        time.sleep(1)
        
        print(f"当前已接收: {len(received_cards)} 条数据")
        
        if i < len(test_cards):
            print(f"等待 {5} 秒后进行下一轮...")
            time.sleep(5)
    
    # 等待最终处理
    print(f"\n{'='*50}")
    print("所有测试完成，等待最终处理...")
    time.sleep(3)
    root.update()
    
    # 检查结果
    print(f"\n{'='*50}")
    print("=== 最终测试结果 ===")
    print(f"总共接收到 {len(received_cards)} 条卡号数据:")
    
    if received_cards:
        for i, card in enumerate(received_cards, 1):
            print(f"  {i}. 卡号: {card.get('dec', 'N/A')}")
            print(f"     十六进制: {card.get('hex', 'N/A')}")
            print(f"     来源: {card.get('source', 'N/A')}")
        print("✅ 测试成功 - HID回调正常工作")
    else:
        print("❌ 测试失败 - 未接收到任何卡号数据")
        print("\n调试信息:")
        print(f"- HID监听器状态: {'运行中' if app.hid_listener else '未运行'}")
        print(f"- HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
        print(f"- 绑定设备: {app.bound_hid_device}")
        print(f"- 期望设备: {app.hid_expected_label}")
    
    # 恢复原始方法
    app.on_card_data = original_on_card_data
    
    # 清理
    app._disable_hid_capture()
    
    # 关闭应用
    try:
        app._on_close()
    except:
        pass
    
    root.quit()
    root.destroy()
    
    print(f"\n{'='*50}")
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_full_bluetooth()