#!/usr/bin/env python3
"""
测试键盘输入 - 模拟蓝牙刷卡器输入
"""

import time
import threading
import msvcrt

def test_keyboard_input():
    """测试键盘输入"""
    print("=== 键盘输入测试 ===")
    print("这个测试将直接监听键盘输入，模拟刷卡器行为")
    print("请刷卡或按任意键...")
    print("按 ESC 键退出测试")
    
    buffer = ""
    start_time = time.time()
    
    while True:
        try:
            # 检查是否有按键
            if msvcrt.kbhit():
                key = msvcrt.getch()
                
                # 检查是否是ESC键
                if key == b'\x1b':  # ESC键
                    print("\n🛑 用户中断测试")
                    break
                
                # 尝试解码按键
                try:
                    char = key.decode('utf-8', errors='replace')
                    
                    # 如果是可打印字符
                    if char.isprintable():
                        buffer += char
                        print(f"\n🔤 接收到字符: '{char}' (ASCII: {ord(char)})")
                        print(f"   当前缓冲区: '{buffer}'")
                        
                        # 如果收到回车键
                        if char in ['\r', '\n']:
                            print(f"🎯 完整输入: '{buffer.strip()}'")
                            buffer = ""
                            
                    else:
                        print(f"\n🔢 特殊字符: {key} (ASCII: {ord(char) if len(char) == 1 else 'N/A'})")
                        
                except Exception as e:
                    print(f"\n❌ 解码错误: {e}, 原始数据: {key}")
            
            # 每秒显示状态
            if time.time() - start_time > 1:
                print(f". 等待输入中 (缓冲区: '{buffer}')", end='\r')
                start_time = time.time()
                
            time.sleep(0.01)  # 小延迟避免CPU占用过高
            
        except KeyboardInterrupt:
            print("\n🛑 测试被用户中断")
            break
    
    return True

def test_pynput():
    """使用pynput库测试键盘输入"""
    print("\n=== 使用pynput库测试 ===")
    
    try:
        from pynput import keyboard
        
        def on_press(key):
            try:
                print(f"按下: {key.char}")
            except AttributeError:
                print(f"按下: {key}")
        
        def on_release(key):
            if key == keyboard.Key.esc:
                # 停止监听
                return False
        
        print("启动键盘监听器...")
        with keyboard.Listener(
                on_press=on_press,
                on_release=on_release) as listener:
            print("按 ESC 键退出")
            listener.join()
            
    except ImportError:
        print("pynput库未安装，跳过此测试")
        return False
    except Exception as e:
        print(f"pynput测试失败: {e}")
        return False
    
    return True

def main():
    print("=== 蓝牙刷卡器输入测试 ===")
    print("\n这个测试将帮助你确定蓝牙刷卡器的工作原理:")
    print("1. 刷卡器可能模拟键盘输入")
    print("2. 刷卡器可能发送特定的按键序列")
    print("3. 刷卡器可能需要特定的驱动或配置")
    
    # 测试1: 基本键盘输入
    test_keyboard_input()
    
    # 测试2: pynput库测试
    test_pynput()
    
    print("\n=== 测试完成 ===")
    print("建议:")
    print("1. 如果刷卡器模拟键盘，应该能在测试中捕获输入")
    print("2. 检查刷卡器是否需要特定驱动或软件")
    print("3. 确认刷卡器是否已正确配对和连接")

if __name__ == "__main__":
    main()