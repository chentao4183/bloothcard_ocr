#!/usr/bin/env python3
"""
蓝牙刷卡器监听器测试脚本 - 改进版
用于测试修复后的HidListener类能否正常接收蓝牙刷卡器输入
"""

import sys
import time
import threading
from app.hid_listener import HidListener


def main():
    """主测试函数"""
    print("=" * 50)
    print("蓝牙刷卡器监听器测试 - 改进版")
    print("=" * 50)
    print("Python版本:", sys.version)
    print("操作系统:", sys.platform)
    print("=" * 50)
    
    # 接收到的卡号记录
    received_cards = []
    
    def on_card_received(card_number: str, device_name: str):
        """刷卡回调函数"""
        nonlocal received_cards
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 🎯 收到卡号: '{card_number}' 来自设备: '{device_name}'")
        
        # 记录收到的数据
        received_cards.append({
            "timestamp": timestamp,
            "card_number": card_number,
            "device_name": device_name
        })
    
    def logger(message: str):
        """日志记录函数"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    try:
        # 1. 创建HID监听器
        print("\n1. 创建HID监听器...")
        try:
            hid_listener = HidListener(
                device_keywords=['Bluetooth', 'Keyboard'],
                digit_length=10,
                require_enter=False,
                callback=on_card_received,
                logger=logger,
            )
            print("✅ HID监听器创建成功")
        except Exception as e:
            print(f"❌ HID监听器创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 2. 启动HID监听器
        print("\n2. 启动HID监听器...")
        try:
            # 使用单独的线程启动监听器，避免阻塞主线程
            listener_thread = threading.Thread(
                target=hid_listener.run,
                daemon=False
            )
            listener_thread.start()
            print("✅ HID监听器启动成功")
            print(f"   监听器线程状态: {listener_thread.name} - {listener_thread.is_alive()}")
        except Exception as e:
            print(f"❌ HID监听器启动失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 3. 等待监听器完全启动
        print("\n3. 等待监听器初始化完成...")
        time.sleep(2)
        print("✅ 监听器初始化完成，开始监听刷卡器输入")
        
        # 4. 长时间运行以等待实际刷卡
        print("\n" + "=" * 50)
        print("🔍 现在开始监听实际刷卡器输入")
        print("请使用蓝牙刷卡器进行刷卡操作")
        print("按 Ctrl+C 停止测试")
        print("=" * 50)
        
        # 打印初始状态
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 监听器运行状态: 正常")
        print(f"[{timestamp}] 监听设备类型: Bluetooth Keyboard")
        print(f"[{timestamp}] 卡号格式: 10位数字")
        print(f"[{timestamp}] 等待输入...")
        
        try:
            # 持续运行，等待用户按键终止
            while True:
                time.sleep(1)
                # 每10秒打印一次状态
                if int(time.time()) % 10 == 0:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] 监听器运行正常... (已收到 {len(received_cards)} 条记录)")
                    print(f"[{timestamp}] 按 Ctrl+C 停止测试")
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 50)
            print("⏹️  收到中断信号，正在停止监听器...")
        
        # 5. 停止HID监听器
        print("\n5. 停止HID监听器...")
        try:
            hid_listener.stop()
            print("✅ HID监听器停止命令已发送")
        except Exception as e:
            print(f"❌ HID监听器停止失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 6. 等待监听器线程结束
        print("\n6. 等待监听器线程结束...")
        time.sleep(2)
        
        # 7. 打印测试结果
        print("\n" + "=" * 50)
        print("📊 测试结果总结")
        print("=" * 50)
        
        if received_cards:
            print(f"✅ 成功接收 {len(received_cards)} 条卡号数据:")
            for i, record in enumerate(received_cards, 1):
                print(f"  {i}. [{record['timestamp']}] 卡号: {record['card_number']} 设备: {record['device_name']}")
        else:
            print("⚠️  未收到任何卡号数据")
            print("请确保:")
            print("1. 蓝牙刷卡器已正确连接到电脑")
            print("2. 刷卡器处于工作状态")
            print("3. 刷卡时使用了正确的刷卡方式")
        
        print("\n" + "=" * 50)
        print("测试已完成")
        print("=" * 50)
        return True
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生未预期错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("启动测试脚本...")
    success = main()
    print("测试脚本结束")
    sys.exit(0 if success else 1)
