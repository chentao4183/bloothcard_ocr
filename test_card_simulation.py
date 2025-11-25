#!/usr/bin/env python3
"""
模拟刷卡器输入测试
"""

import sys
import time
import threading

# 添加到Python路径
sys.path.insert(0, 'app')

def simulate_card_input():
    """模拟刷卡器输入"""
    print("=== 模拟刷卡器输入测试 ===")
    print("这个测试将模拟刷卡器可能产生的各种输入格式")
    
    # 常见的RFID卡号格式
    test_cards = [
        "1234567890",           # 纯数字
        "0001234567",           # 带前导零
        "12345678",             # 较短卡号
        "123456789012",         # 较长卡号
        "\r1234567890\r",      # 带回车
        "\n1234567890\n",      # 带换行
        "1234567890\r\n",      # 回车+换行
        "\x021234567890\x03",  # 带起始和结束符
        "1234567890\x0D",      # 十六进制回车
        "1234567890\x0A",      # 十六进制换行
    ]
    
    print("\n测试各种卡号格式:")
    for i, card_data in enumerate(test_cards, 1):
        print(f"\n--- 测试格式 {i} ---")
        print(f"原始数据: {repr(card_data)}")
        print(f"可见字符: {card_data}")
        print(f"长度: {len(card_data)}")
        
        # 提取数字
        digits = ''.join(c for c in card_data if c.isdigit())
        print(f"提取数字: {digits}")
        
        # 转换为16进制
        if digits:
            try:
                dec_int = int(digits)
                hex_value = f"{dec_int:08X}"
                print(f"16进制: {hex_value}")
            except Exception as e:
                print(f"转换错误: {e}")
        
        time.sleep(0.5)
    
    return True

def test_hid_listener_simple():
    """简化版HID监听测试"""
    print("\n=== 简化HID监听测试 ===")
    
    try:
        from hid_listener import HidListener
        
        received_data = []
        
        def on_card_data(value: str, device_name: str):
            print(f"🎯 接收到数据: '{value}' 来自设备: '{device_name}'")
            received_data.append((value, device_name))
        
        def logger(msg: str):
            print(f"[HID] {msg}")
        
        print("创建HID监听器...")
        listener = HidListener(
            device_keywords=["Bluetooth", "Keyboard"],
            digit_length=10,
            require_enter=False,
            callback=on_card_data,
            logger=logger
        )
        
        print("启动HID监听器...")
        listener.start()
        
        print("HID监听器已启动，等待输入...")
        print("请在刷卡器上刷卡，或按任意键盘按键测试")
        
        # 运行10秒
        for i in range(10):
            time.sleep(1)
            print(f". 等待输入中 ({10-i}秒)", end='\r')
        
        print(f"\n测试完成，共接收 {len(received_data)} 条数据")
        
        listener.stop()
        return len(received_data) > 0
        
    except Exception as e:
        print(f"HID监听测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_keyboard_listener():
    """测试键盘监听"""
    print("\n=== 键盘监听测试 ===")
    
    try:
        import msvcrt
        
        print("这个测试将监听键盘输入")
        print("请刷卡或按任意键，按 ESC 退出")
        
        start_time = time.time()
        
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                
                if key == b'\x1b':  # ESC键
                    print("\n🛑 用户中断")
                    break
                
                print(f"\n按键: {repr(key)}")
                
                # 尝试解码
                try:
                    char = key.decode('utf-8', errors='replace')
                    print(f"字符: '{char}' (ASCII: {ord(char) if len(char) == 1 else 'N/A'})")
                except:
                    print(f"原始数据: {key}")
            
            # 超时检查
            if time.time() - start_time > 30:  # 30秒超时
                print("\n⏰ 测试超时")
                break
                
            time.sleep(0.01)
        
        return True
        
    except Exception as e:
        print(f"键盘监听测试失败: {e}")
        return False

def main():
    print("=== 蓝牙刷卡器问题诊断 ===")
    print("\n问题分析:")
    print("1. HID监听器窗口创建失败")
    print("2. 可能需要管理员权限")
    print("3. 刷卡器可能使用不同的输入方式")
    
    # 运行各种测试
    simulate_card_input()
    
    print("\n" + "="*50)
    print("建议下一步操作:")
    print("1. 以管理员身份运行此脚本")
    print("2. 检查刷卡器驱动是否正确安装")
    print("3. 确认刷卡器是否模拟键盘输入")
    print("4. 尝试使用不同的监听方法")
    
    # 尝试键盘监听
    test_keyboard_listener()
    
    # 如果HID监听可用，也测试一下
    try:
        test_hid_listener_simple()
    except:
        print("HID监听测试跳过")

if __name__ == "__main__":
    main()