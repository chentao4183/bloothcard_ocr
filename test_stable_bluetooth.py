#!/usr/bin/env python3
"""
稳定版蓝牙刷卡器测试 - 确保完整执行
"""
import tkinter as tk
import time
from app.main import App

def test_stable_bluetooth():
    """稳定测试蓝牙刷卡器功能"""
    print("=== 稳定版蓝牙刷卡器功能测试 ===")
    
    try:
        # 创建主应用
        print("正在创建主应用...")
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        app = App(root)
        
        # 等待应用初始化
        time.sleep(2)
        
        # 检查HID监听器状态
        if not app.hid_listener:
            print("❌ HID监听器未启动")
            return
            
        print(f"✅ HID监听器已启动: {type(app.hid_listener).__name__}")
        print(f"   - 数字长度: {app.config.hid.digit_length}")
        print(f"   - 需要回车: {app.config.hid.require_enter}")
        
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
        time.sleep(1)
        
        # 测试卡号
        test_cards = [
            ("1234567890", "BLE Card Reader"),
            ("9876543210", "RFID Scanner"),
            ("5555666677", "Bluetooth Keyboard")
        ]
        
        print("\n开始稳定测试...")
        for i, (card_number, device_name) in enumerate(test_cards, 1):
            print(f"\n第 {i}/3 轮: {card_number} ({device_name})")
            
            # 直接调用HID回调
            app._on_hid_card(card_number, device_name)
            
            # 处理GUI事件
            root.update()
            time.sleep(3)  # 稳定等待时间
            root.update()
            
            print(f"  当前已接收: {len(received_cards)} 条")
        
        # 最终等待
        print("\n等待最终处理...")
        time.sleep(2)
        root.update()
        
        # 显示结果
        print(f"\n=== 测试结果 ===")
        print(f"总共接收到 {len(received_cards)} 条数据:")
        
        success_count = 0
        for i, card in enumerate(received_cards, 1):
            print(f"  {i}. 卡号: {card.get('dec', 'N/A')}")
            print(f"     来源: {card.get('source', 'N/A')}")
            success_count += 1
        
        if success_count == len(test_cards):
            print("✅ 完美！所有测试卡号都已接收")
        elif success_count > 0:
            print(f"⚠️  部分成功：{success_count}/{len(test_cards)} 个卡号被接收")
        else:
            print("❌ 测试失败：未接收到任何卡号")
        
        # 清理
        app.on_card_data = original_on_card_data
        app._disable_hid_capture()
        
        # 关闭应用
        try:
            app._on_close()
        except:
            pass
            
        root.quit()
        root.destroy()
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stable_bluetooth()