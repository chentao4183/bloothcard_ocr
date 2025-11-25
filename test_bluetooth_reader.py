#!/usr/bin/env python3
"""
测试蓝牙刷卡器功能 - 完整流程测试
"""

import time
import sys
import os
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_bluetooth_reader():
    """测试蓝牙刷卡器完整流程"""
    print("=== 蓝牙刷卡器功能测试 ===")
    
    try:
        # 导入主应用模块
        from app.main import App
        import tkinter as tk
        
        print("正在创建主应用...")
        
        # 创建主窗口（隐藏）
        root = tk.Tk()
        root.withdraw()  # 隐藏窗口
        
        print("正在初始化应用...")
        
        # 创建应用实例
        app = App(root)
        
        print("✅ 主应用初始化成功!")
        
        # 检查HID监听器状态
        if hasattr(app, 'hid_listener') and app.hid_listener:
            print(f"✅ HID监听器已启动: {type(app.hid_listener).__name__}")
            print(f"   - 数字长度: {app.config.hid.digit_length}")
            print(f"   - 需要回车: {app.config.hid.require_enter}")
            print(f"   - 设备关键词: {app.config.hid.device_keywords}")
        else:
            print("⚠️  HID监听器未启动")
        
        # 模拟刷卡数据
        test_cards = [
            {"card": "1234567890", "source": "Bluetooth Keyboard"},
            {"card": "9876543210", "source": "BLE Card Reader"},
            {"card": "5555666677", "source": "RFID Scanner"},
        ]
        
        print(f"\n准备测试 {len(test_cards)} 个卡号...")
        
        received_cards = []
        
        # 重写on_card_data方法来捕获数据
        original_on_card_data = app.on_card_data
        
        def test_on_card_data(card_data):
            """测试用的卡号数据处理函数"""
            print(f"🎯 接收到卡号数据:")
            print(f"   - 卡号(十进制): {card_data.get('dec', 'N/A')}")
            print(f"   - 卡号(十六进制): {card_data.get('hex', 'N/A')}")
            print(f"   - 来源: {card_data.get('source', 'N/A')}")
            received_cards.append(card_data)
            # 调用原始方法
            original_on_card_data(card_data)
        
        app.on_card_data = test_on_card_data
        
        # 直接调用HID回调，绕过捕获逻辑
        print("\n直接调用HID回调...")
        
        for i, test_data in enumerate(test_cards, 1):
            card_number = test_data["card"]
            device_name = test_data["source"]
            
            print(f"\n[{i}/3] 准备模拟刷卡: {card_number}")
            print(">>> 请在此时间内进行刷卡操作...")
            
            # 直接调用HID回调函数
            app._on_hid_card(card_number, device_name)
            print(f"已发送卡号: {card_number}")
            
            if i < len(test_cards):
                print(f"等待 {8} 秒后进行下一次刷卡...")
                time.sleep(8)  # 增加等待时间，方便观察
            else:
                print("所有刷卡测试完成，等待结果...")
                time.sleep(3)
        
        # 检查结果
        print(f"\n测试完成!")
        print(f"总共接收到 {len(received_cards)} 条卡号数据:")
        
        for i, card in enumerate(received_cards, 1):
            print(f"  {i}. 卡号: {card.get('dec', 'N/A')} 来源: {card.get('source', 'N/A')}")
        
        # 禁用HID监听捕获
        app._disable_hid_capture()
        
        # 关闭应用
        root.quit()
        root.destroy()
        
        success = len(received_cards) == len(test_cards)
        print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}")
        
        return success
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")
        return False
    except Exception as e:
        print(f"测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bluetooth_reader()
    sys.exit(0 if success else 1)