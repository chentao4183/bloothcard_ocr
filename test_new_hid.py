#!/usr/bin/env python3
"""
测试新的简化版HID监听器
"""

import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_hid_listener():
    """测试HID监听器"""
    print("=== 测试新的简化版HID监听器 ===")
    
    try:
        from app.hid_listener_simple import SimpleHidListener
        
        received_cards = []
        
        def on_card_data(value: str, device_name: str):
            """接收到卡号数据时的回调"""
            print(f"🎯 接收到卡号: '{value}' 来自设备: '{device_name}'")
            received_cards.append((value, device_name))
        
        def logger_func(msg: str):
            """日志函数"""
            print(f"[{time.strftime('%H:%M:%S')}] {msg}")
        
        # 创建监听器
        listener = SimpleHidListener(
            digit_length=10,
            require_enter=False,
            callback=on_card_data,
            logger_func=logger_func
        )
        
        print("正在启动HID监听器...")
        if listener.start():
            print("✅ HID监听器启动成功!")
            print("\n测试说明:")
            print("1. 监听器正在运行，等待键盘输入")
            print("2. 请输入10位数字来模拟刷卡")
            print("3. 或者等待模拟刷卡器发送数据")
            print("4. 按 Ctrl+C 退出测试")
            print("\n监听器配置:")
            print(f"   - 数字长度: {listener.digit_length}")
            print(f"   - 需要回车: {listener.require_enter}")
            print(f"   - 监听方法: {listener._method}")
            
            # 启动模拟刷卡器
            from app.hid_listener_simple import CardReaderSimulator
            simulator = CardReaderSimulator(callback=on_card_data)
            simulator.start_simulation(card_number="9876543210", interval=10)
            
            print("\n模拟刷卡器已启动，每10秒发送一次测试卡号...")
            
            # 运行测试
            test_duration = 30  # 30秒
            for i in range(test_duration):
                time.sleep(1)
                print(f"\r测试中... {test_duration-i}秒 已接收: {len(received_cards)} 条数据", end='', flush=True)
            
            print(f"\n\n测试完成!")
            print(f"总共接收到 {len(received_cards)} 条卡号数据:")
            for i, (value, device) in enumerate(received_cards, 1):
                print(f"  {i}. 卡号: {value} 设备: {device}")
            
            # 停止监听器
            listener.stop()
            simulator.stop_simulation()
            
            return len(received_cards) > 0
            
        else:
            print("❌ HID监听器启动失败!")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")
        return False
    except Exception as e:
        print(f"测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hid_listener()
    print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}")
    sys.exit(0 if success else 1)