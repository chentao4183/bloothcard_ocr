#!/usr/bin/env python3
"""
直接测试HID监听功能
"""

import sys
import time
import threading

# 添加到Python路径以便导入应用模块
sys.path.insert(0, 'app')

try:
    from hid_listener import HidListener
except ImportError as e:
    print(f"导入HID监听模块失败: {e}")
    print("请确保在Windows环境下运行此脚本")
    sys.exit(1)

def main():
    print("=== 直接HID监听测试 ===")
    print("启动HID监听器，等待刷卡输入...")
    
    # 记录接收到的数据
    received_count = 0
    listener_ready = threading.Event()
    
    def on_card_data(value: str, device_name: str):
        """卡号数据回调函数"""
        nonlocal received_count
        received_count += 1
        
        print(f"\n🎯 接收到卡号数据 #{received_count}")
        print(f"   原始值: '{value}'")
        print(f"   设备名: '{device_name}'")
        print(f"   长度: {len(value)}")
        
        # 转换为16进制
        try:
            dec_int = int(value)
            hex_value = f"{dec_int:08X}"
            print(f"   16进制: {hex_value}")
        except Exception as e:
            print(f"   转换错误: {e}")
        
        print(f"\n⏳ 继续等待输入...")
    
    def logger(msg: str):
        """日志函数"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {msg}")
        
        if "已启动" in msg:
            listener_ready.set()
    
    # 创建HID监听器 - 使用更宽松的配置
    try:
        listener = HidListener(
            device_keywords=["Bluetooth", "Keyboard", "BLE", "RFID", "Microsoft"],  # 扩大关键词范围
            digit_length=10,
            require_enter=False,  # 不需要回车键
            callback=on_card_data,
            logger=logger
        )
    except Exception as e:
        print(f"创建HID监听器失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        listener.start()
        
        # 等待监听器启动
        if listener_ready.wait(timeout=5):
            print("✅ HID监听器启动成功!")
            print("\n📋 测试说明:")
            print("1. 请在蓝牙刷卡器上刷卡")
            print("2. 观察是否有卡号数据接收")
            print("3. 按 Ctrl+C 退出测试")
            print("\n⏳ 等待刷卡输入...")
            
            # 持续运行，直到用户中断
            try:
                while True:
                    time.sleep(1)
                    print(f". 等待输入中 (已接收: {received_count})", end='\r')
            except KeyboardInterrupt:
                print(f"\n\n🛑 用户中断测试，共接收 {received_count} 条数据")
                
        else:
            print("❌ HID监听器启动超时")
            return False
            
    except Exception as e:
        print(f"HID监听器运行错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n停止HID监听器...")
        listener.stop()
        try:
            listener.join(timeout=2)
        except Exception:
            pass
    
    return received_count > 0

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}")
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()