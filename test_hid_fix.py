#!/usr/bin/env python3
"""
修复HID监听问题的测试脚本
"""
import tkinter as tk
from app.main import App
import time

def test_hid_fix():
    """测试HID监听修复"""
    print("=== HID监听修复测试 ===")
    
    # 创建主应用
    root = tk.Tk()
    root.withdraw()  # 隐藏窗口
    app = App(root)
    
    # 等待初始化
    time.sleep(2)
    
    print("\n1. 检查HID配置:")
    print(f"   - HID启用状态: {app.config.hid.enabled}")
    print(f"   - 数字长度: {app.config.hid.digit_length}")
    print(f"   - 需要回车: {app.config.hid.require_enter}")
    
    print("\n2. 检查HID监听器状态:")
    if app.hid_listener:
        print(f"   - HID监听器已创建: {type(app.hid_listener).__name__}")
        print(f"   - HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
        print(f"   - 绑定设备: {app.bound_hid_device}")
        print(f"   - 期望标签: {app.hid_expected_label}")
        
        # 检查监听器内部状态
        if hasattr(app.hid_listener, '_running'):
            print(f"   - 监听器运行状态: {'运行中' if app.hid_listener._running else '已停止'}")
        else:
            print("   - 无法获取监听器运行状态")
            
        # 检查监听方法
        if hasattr(app.hid_listener, '_method'):
            print(f"   - 监听方法: {app.hid_listener._method}")
        else:
            print("   - 监听方法: 未知")
    else:
        print("   ❌ HID监听器未创建")
    
    print("\n3. 启用HID捕获:")
    # 模拟点击监听按钮
    app._enable_hid_capture("测试刷卡器")
    print(f"   - HID捕获状态: {'启用' if app.hid_accepting else '禁用'}")
    print(f"   - 期望标签: {app.hid_expected_label}")
    
    print("\n4. 测试模拟刷卡:")
    test_received = []
    
    def test_receiver(data):
        test_received.append(data)
        print(f"   📡 接收到: {data}")
    
    # 临时替换接收方法
    original_method = app.on_card_data
    app.on_card_data = test_receiver
    
    # 模拟刷卡
    if app.hid_listener and app.hid_accepting:
        print("   模拟刷卡测试...")
        app._on_hid_card("1234567890", "TestDevice")
        time.sleep(1)
        
        if test_received:
            print(f"   ✅ 模拟刷卡成功，接收到 {len(test_received)} 条数据")
        else:
            print("   ❌ 模拟刷卡失败，未接收到数据")
    else:
        print("   ❌ 无法模拟刷卡，HID监听器未启动或捕获未启用")
    
    # 恢复原始方法
    app.on_card_data = original_method
    
    # 清理
    try:
        app._on_close()
    except:
        pass
    root.quit()
    
    print("\n=== 测试完成 ===")
    return len(test_received) > 0

if __name__ == "__main__":
    success = test_hid_fix()
    print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}")