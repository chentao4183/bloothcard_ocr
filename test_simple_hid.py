#!/usr/bin/env python3
"""
简化版HID监听测试
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
    sys.exit(1)

def main():
    print("=== 简化HID监听测试 ===")
    print("配置: 不需要回车键，监听所有设备")
    
    received_count = 0
    
    def on_card_data(value: str, device_name: str):
        """卡号数据回调函数"""
        nonlocal received_count
        received_count += 1
        
        print(f"\n🎯 接收到数据 #{received_count}")
        print(f"   原始值: '{value}'")
        print(f"   设备名: '{device_name}'")
        print(f"   长度: {len(value)}")
        
        # 尝试转换为16进制
        try:
            dec_int = int(value)
            hex_value = f"{dec_int:08X}"
            print(f"   16进制: {hex_value}")
        except:
            pass
        
        print(f"\n⏳ 继续等待...")
    
    def logger(msg: str):
        """日志函数"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {msg}")
    
    # 创建HID监听器 - 使用更宽松的配置
    try:
        listener = HidListener(
            device_keywords=[],  # 监听所有设备
            digit_length=10,
            require_enter=False,  # 不需要回车键
            callback=on_card_data,
            logger=logger
        )
    except Exception as e:
        print(f"创建HID监听器失败: {e}")
        return False
    
    try:
        listener.start()
        print("✅ HID监听器启动成功!")
        print("\n📋 测试步骤:")
        print("1. 在蓝牙刷卡器上刷卡")
        print("2. 观察是否有数据接收")
        print("3. 按 Ctrl+C 退出")
        print("\n⏳ 等待输入...")
        
        # 持续运行
        while True:
            time.sleep(1)
            print(f". 等待输入中 (已接收: {received_count})", end='\r')
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 用户中断，共接收 {received_count} 条数据")
    except Exception as e:
        print(f"运行错误: {e}")
        return False
    finally:
        print("\n停止HID监听器...")
        listener.stop()
        
    return received_count > 0

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}")
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")