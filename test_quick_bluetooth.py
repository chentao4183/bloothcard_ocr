#!/usr/bin/env python3
"""
快速蓝牙刷卡器测试 - 快速验证功能
"""
import tkinter as tk
import time
from app.main import App

def test_quick_bluetooth():
    """快速测试蓝牙刷卡器功能"""
    print("=== 快速蓝牙刷卡器功能测试 ===")
    
    # 创建主应用
    root = tk.Tk()
    root.withdraw()
    
    app = App(root)
    time.sleep(2)
    
    if not app.hid_listener:
        print("❌ HID监听器未启动")
        return False
    
    print(f"✅ HID监听器已启动")
    
    # 设置接收器
    received = []
    
    def test_receiver(card_data):
        received.append(card_data)
        print(f"📡 接收: {card_data}")
    
    # 替换方法
    original = app.on_card_data
    app.on_card_data = test_receiver
    
    # 启用捕获
    app._enable_hid_capture("test")
    time.sleep(1)
    
    # 测试3个卡号
    test_cards = ["1234567890", "9876543210", "5555666677"]
    
    for card in test_cards:
        print(f"测试卡号: {card}")
        app._on_hid_card(card, "TestDevice")
        root.update()
        time.sleep(2)
    
    # 恢复方法
    app.on_card_data = original
    app._disable_hid_capture()
    
    # 结果
    print(f"\n结果: 接收到 {len(received)} 条数据")
    for i, card in enumerate(received, 1):
        print(f"  {i}. 卡号: {card.get('dec', 'N/A')}")
    
    # 清理
    try:
        app._on_close()
    except:
        pass
    root.quit()
    root.destroy()
    
    return len(received) > 0

if __name__ == "__main__":
    success = test_quick_bluetooth()
    print(f"\n测试{'成功' if success else '失败'}")