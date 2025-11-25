#!/usr/bin/env python3
"""
HID监听功能诊断脚本
用于测试RFID卡号读取功能
"""

import sys
import time
import threading
from typing import Dict, Optional

# 添加到Python路径以便导入应用模块
sys.path.insert(0, 'app')

try:
    from hid_listener import HidListener
except ImportError as e:
    print(f"导入HID监听模块失败: {e}")
    print("请确保在Windows环境下运行此脚本")
    sys.exit(1)

def test_hid_listener():
    """测试HID监听功能"""
    print("=== HID监听功能诊断测试 ===")
    
    # 配置参数
    device_keywords = ["Bluetooth", "Keyboard", "BLE", "RFID"]
    digit_length = 10
    require_enter = True
    
    print(f"设备关键词: {device_keywords}")
    print(f"数字长度: {digit_length}")
    print(f"需要回车: {require_enter}")
    
    # 记录接收到的数据
    received_data = []
    listener_ready = threading.Event()
    
    def on_card_data(value: str, device_name: str):
        """卡号数据回调函数"""
        print(f"\n🎯 接收到卡号数据!")
        print(f"   原始值: {value}")
        print(f"   设备名: {device_name}")
        print(f"   长度: {len(value)}")
        
        # 转换为16进制
        try:
            dec_int = int(value)
            hex_value = f"{dec_int:08X}"
            print(f"   16进制: {hex_value}")
        except Exception as e:
            print(f"   转换错误: {e}")
            hex_value = value
        
        received_data.append({
            'value': value,
            'device_name': device_name,
            'hex_value': hex_value,
            'timestamp': time.strftime('%H:%M:%S')
        })
        
        print(f"\n💡 提示: 请继续刷卡测试，或按 Ctrl+C 退出测试")
    
    def logger(msg: str):
        """日志函数"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {msg}")
        
        if "已启动" in msg:
            listener_ready.set()
    
    # 创建HID监听器
    try:
        listener = HidListener(
            device_keywords=device_keywords,
            digit_length=digit_length,
            require_enter=require_enter,
            callback=on_card_data,
            logger=logger
        )
    except Exception as e:
        print(f"创建HID监听器失败: {e}")
        return False
    
    print("\n启动HID监听器...")
    try:
        listener.start()
        
        # 等待监听器启动
        if listener_ready.wait(timeout=5):
            print("✅ HID监听器启动成功!")
            print("\n📋 测试说明:")
            print("1. 确保蓝牙刷卡器已连接并配对")
            print("2. 在刷卡器上刷卡")
            print("3. 观察是否有卡号数据接收")
            print("4. 如果require_enter=True，刷卡后需要按回车键")
            print("5. 按 Ctrl+C 退出测试")
            print("\n⏳ 等待刷卡输入...")
            
            # 持续运行，直到用户中断
            try:
                while True:
                    time.sleep(1)
                    if received_data:
                        print(f". 已接收 {len(received_data)} 条数据", end='\r')
                    else:
                        print(". 等待输入中", end='\r')
            except KeyboardInterrupt:
                print("\n\n🛑 用户中断测试")
        else:
            print("❌ HID监听器启动超时")
            return False
            
    except Exception as e:
        print(f"HID监听器运行错误: {e}")
        return False
    finally:
        print("\n停止HID监听器...")
        listener.stop()
        try:
            listener.join(timeout=2)
        except Exception:
            pass
    
    # 测试结果总结
    print("\n=== 测试结果总结 ===")
    if received_data:
        print(f"✅ 成功接收 {len(received_data)} 条卡号数据")
        for i, data in enumerate(received_data, 1):
            print(f"  数据{i}: {data['value']} (设备: {data['device_name']}, 时间: {data['timestamp']})")
        return True
    else:
        print("❌ 未接收到任何卡号数据")
        print("\n可能的原因:")
        print("1. 刷卡器未正确连接或配对")
        print("2. 设备关键词不匹配")
        print("3. 刷卡器发送的数据格式不符合预期")
        print("4. 需要按回车键才能发送数据")
        return False

def test_device_detection():
    """测试设备检测功能"""
    print("\n=== 设备检测测试 ===")
    
    try:
        from system_devices import list_connected_bluetooth_devices
        
        print("正在扫描蓝牙设备...")
        devices = list_connected_bluetooth_devices()
        
        if not devices:
            print("未找到任何蓝牙设备")
            return False
        
        print(f"找到 {len(devices)} 个蓝牙设备:")
        keyboard_devices = []
        
        for i, device in enumerate(devices, 1):
            print(f"{i}. {device.name} ({device.address})")
            print(f"   连接状态: {'已连接' if device.is_connected else '未连接'}")
            print(f"   配对状态: {'已配对' if device.is_paired else '未配对'}")
            
            # 检查是否为键盘设备
            device_name_lower = device.name.lower() if device.name else ""
            if any(keyword in device_name_lower for keyword in ["keyboard", "键盘", "rfid", "ble", "bluetooth"]):
                keyboard_devices.append(device)
                print(f"   🎯 可能是刷卡器设备")
            print()
        
        if keyboard_devices:
            print(f"✅ 找到 {len(keyboard_devices)} 个可能的刷卡器设备")
            return True
        else:
            print("⚠️  未找到明显的刷卡器设备")
            print("建议检查设备名称是否包含: keyboard, 键盘, rfid, ble, bluetooth")
            return False
            
    except Exception as e:
        print(f"设备检测失败: {e}")
        return False

def main():
    """主测试函数"""
    print("蓝牙刷卡器RFID读取功能诊断")
    print("=" * 50)
    
    # 检查操作系统
    import os
    if os.name != 'nt':
        print("❌ 此脚本只能在Windows系统下运行")
        return
    
    # 测试1: 设备检测
    device_test_passed = test_device_detection()
    
    print("\n" + "=" * 50)
    
    # 测试2: HID监听
    print("\n准备测试HID监听功能...")
    input("请确保蓝牙刷卡器已连接，然后按回车键开始测试...")
    
    hid_test_passed = test_hid_listener()
    
    # 最终总结
    print("\n" + "=" * 50)
    print("=== 最终测试结果 ===")
    print(f"设备检测: {'✅ 通过' if device_test_passed else '❌ 失败'}")
    print(f"HID监听: {'✅ 通过' if hid_test_passed else '❌ 失败'}")
    
    if device_test_passed and hid_test_passed:
        print("\n🎉 所有测试通过！刷卡器应该可以正常工作")
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息")
        print("建议:")
        if not device_test_passed:
            print("- 检查蓝牙刷卡器是否正确连接和配对")
            print("- 确认设备名称包含关键词: keyboard, rfid, ble 等")
        if not hid_test_passed:
            print("- 检查刷卡器是否需要特殊的驱动程序")
            print("- 尝试调整设备关键词配置")
            print("- 确认刷卡数据格式和长度设置")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()