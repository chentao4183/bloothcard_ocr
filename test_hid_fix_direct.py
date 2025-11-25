#!/usr/bin/env python3
"""
直接测试HID监听器修复的脚本
"""
import time
import sys
from app.hid_listener_simple import SimpleHidListener as HidListener

# 收到的数据计数
received_count = 0
# 监听器准备就绪标志
listener_ready = False

def on_card_data(data: str, device_name: str):
    """处理接收到的卡号数据"""
    global received_count
    received_count += 1
    print(f"\n🎉 收到卡号数据!")
    print(f"   卡号: {data}")
    print(f"   设备: {device_name}")
    print(f"   接收计数: {received_count}")

def logger(msg: str):
    """日志函数"""
    global listener_ready
    timestamp = time.strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}")
    
    if "已启动" in msg:
        listener_ready = True

def main():
    """主测试函数"""
    print("=== HID监听器修复测试 ===")
    print("测试目的: 验证device_keywords参数修复是否有效")
    print("\n配置信息:")
    print(f"- Python版本: {sys.version}")
    print(f"- 操作系统: {sys.platform}")
    
    # 创建HID监听器 - 配置为监听Bluetooth Keyboard设备
    try:
        print("\n正在创建HID监听器...")
        print("配置参数:")
        print(f"- device_keywords: ['Bluetooth', 'Keyboard']")
        print(f"- digit_length: 10")
        print(f"- require_enter: False")
        
        listener = HidListener(
            device_keywords=['Bluetooth', 'Keyboard'],  # 明确指定设备关键词
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
        print("\n启动HID监听器...")
        listener.start()
        
        # 等待监听器启动
        start_time = time.time()
        timeout = 5
        while not listener_ready and time.time() - start_time < timeout:
            time.sleep(0.1)
            
        if listener_ready:
            print("✅ HID监听器启动成功!")
            print("\n📋 测试说明:")
            print("1. 请确保您的蓝牙刷卡器已连接")
            print("2. 在蓝牙刷卡器上刷卡")
            print("3. 观察是否能接收到卡号数据")
            print("4. 按 Ctrl+C 退出测试")
            print("\n⏳ 等待刷卡输入...")
            
            # 持续运行，直到用户中断
            try:
                while True:
                    time.sleep(1)
                    print(f". 等待输入中 (已接收: {received_count})")
            except KeyboardInterrupt:
                print(f"\n\n🛑 用户中断测试，共接收 {received_count} 条数据")
                return received_count > 0
            
        else:
            print("❌ HID监听器启动超时")
            return False
            
    except Exception as e:
        print(f"❌ HID监听器运行错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n停止HID监听器...")
        try:
            listener.stop()
        except Exception as e:
            print(f"停止监听器时出错: {e}")
    
    return received_count > 0

if __name__ == "__main__":
    print("开始测试HID监听器修复...")
    success = main()
    print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}")
    print("\n📋 修复说明:")
    print("- 问题: HidListener初始化时缺少device_keywords参数")
    print("- 修复: 在main.py的_restart_hid_listener方法中添加了该参数")
    print("- 目的: 让监听器能够正确识别并监听蓝牙刷卡器设备")
    
    sys.exit(0 if success else 1)
