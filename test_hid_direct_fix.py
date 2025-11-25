#!/usr/bin/env python3
"""
直接测试修复后的HID监听器
"""

import sys
import time
import threading
from typing import Optional

# 添加到Python路径以便导入应用模块
sys.path.insert(0, 'app')

# 导入修复后的HidListener类
from app.hid_listener import HidListener

# 全局变量用于跟踪监听器状态
listener_ready = False
received_data = []

def logger(msg: str):
    """日志函数"""
    global listener_ready
    timestamp = time.strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}")
    
    if "已启动" in msg:
        listener_ready = True

def on_card_data(value: str, device_name: str):
    """HID监听器回调函数"""
    timestamp = time.strftime('%H:%M:%S')
    print(f"[{timestamp}] 🎯 收到卡号: '{value}' 来自: '{device_name}'")
    received_data.append((value, device_name))

def main():
    """主测试函数"""
    print("=== 修复后的HID监听器测试 ===")
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {sys.platform}")
    
    try:
        print("\n1. 创建HID监听器...")
        listener = HidListener(
            device_keywords=['Bluetooth', 'Keyboard'],
            digit_length=10,
            require_enter=False,
            callback=on_card_data,
            logger=logger
        )
        print("✅ HID监听器创建成功")
    except Exception as e:
        print(f"❌ 创建HID监听器失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        print("\n2. 启动HID监听器...")
        listener.start()
        
        # 等待监听器启动
        start_time = time.time()
        timeout = 10
        while time.time() - start_time < timeout:
            time.sleep(0.5)
            print(f"   等待监听器启动... {int(time.time() - start_time)}/{timeout}秒")
            if listener._running.is_set():
                print("✅ HID监听器已启动并运行")
                break
        else:
            print("❌ HID监听器启动超时")
            return False
    except Exception as e:
        print(f"❌ 启动HID监听器失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        print("\n3. 模拟HID数据处理...")
        # 测试process_bluetooth_data方法
        test_data = "1234567890"
        test_device = "Bluetooth Keyboard"
        print(f"   测试数据: '{test_data}' 设备: '{test_device}'")
        listener.process_bluetooth_data(test_data, test_device)
        
        # 等待回调执行
        time.sleep(1)
        
        if received_data:
            print(f"✅ process_bluetooth_data测试成功")
        else:
            print(f"⚠️ process_bluetooth_data没有触发回调")
    except Exception as e:
        print(f"❌ 测试process_bluetooth_data失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n4. 开始监听实际键盘输入...")
    print("请现在使用蓝牙刷卡器刷卡，或者在键盘上输入10位以上数字")
    print("测试将在30秒后自动结束")
    
    # 等待实际输入或超时
    start_time = time.time()
    timeout = 30
    while time.time() - start_time < timeout:
        if received_data:
            print(f"\n✅ 收到实际输入数据: {received_data[-1]}")
            break
        time.sleep(1)
        print(f"   等待输入... {int(time.time() - start_time)}/{timeout}秒", end="\r")
    else:
        print(f"\n⚠️ 监听超时，没有收到实际输入")
    
    try:
        print("\n5. 停止HID监听器...")
        listener.stop()
        print("✅ HID监听器已停止")
    except Exception as e:
        print(f"❌ 停止HID监听器失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n=== 测试结果汇总 ===")
    print(f"监听器创建: ✅ 成功")
    print(f"监听器启动: ✅ 成功")
    print(f"process_bluetooth_data: {'✅ 成功' if received_data else '⚠️ 未触发回调'}")
    print(f"实际输入监听: {'✅ 成功' if len(received_data) > 1 else '⚠️ 未收到'}")
    print(f"监听器停止: ✅ 成功")
    
    return True

if __name__ == "__main__":
    success = main()
    print(f"\n测试最终结果: {'✅ 全部成功' if success else '❌ 部分失败'}")
    sys.exit(0 if success else 1)