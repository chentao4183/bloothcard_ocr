#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试HidListener的轮询方式 - 测试脚本
"""

import sys
import time
import threading

# 添加项目根目录到Python路径
sys.path.append('.')

from app.hid_listener import HidListener

# 测试回调函数
received_cards = []

def on_card_data(card_number, device_name):
    print(f"✅ 收到卡号: {card_number}, 设备: {device_name}")
    received_cards.append((card_number, device_name))

# 日志函数
def logger(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# 主测试函数
def main():
    print("\n" + "="*50)
    print("HidListener 轮询方式测试")
    print("="*50)
    
    # 创建监听器
    listener = HidListener(
        device_keywords=['Bluetooth', 'Keyboard'],  # 监听蓝牙键盘类型设备
        digit_length=10,  # 卡号长度
        require_enter=False,  # 不需要回车
        callback=on_card_data,
        logger=logger
    )
    
    print("\n1. 启动HID监听器...")
    listener.start()  # 启动监听器线程
    time.sleep(1)  # 等待监听器初始化
    
    if listener.is_alive():
        print("✅ HID监听器已启动并运行")
    else:
        print("❌ HID监听器启动失败")
        return
    
    print("\n" + "="*50)
    print("🔍 开始监听刷卡器输入")
    print("请使用蓝牙刷卡器进行刷卡操作")
    print("按 Ctrl+C 停止测试")
    print("="*50)
    
    try:
        # 持续运行，每10秒打印状态
        while True:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 监听器运行中...")
            print(f"   收到的卡号: {received_cards}")
            print(f"   监听器线程状态: {'活跃' if listener.is_alive() else '已停止'}")
            
            # 等待10秒
            for _ in range(10):
                time.sleep(1)
                if not listener.is_alive():
                    print("❌ 监听器线程意外停止")
                    break
                    
    except KeyboardInterrupt:
        print("\n\n💡 用户中断测试")
    finally:
        # 停止监听器
        print("\n3. 停止HID监听器...")
        listener.stop()
        listener.join(timeout=5)  # 等待线程结束
        
        if not listener.is_alive():
            print("✅ HID监听器已成功停止")
        else:
            print("⚠️  HID监听器可能未完全停止")
    
    print("\n" + "="*50)
    print("测试完成")
    print(f"总共收到 {len(received_cards)} 个卡号")
    for i, (card, device) in enumerate(received_cards):
        print(f"   {i+1}. {card} ({device})")
    print("="*50)

if __name__ == "__main__":
    main()