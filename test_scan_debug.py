#!/usr/bin/env python3
"""测试扫描功能的诊断脚本"""

import sys
import traceback

def test_system_devices():
    """测试系统设备模块"""
    print("=== 测试系统设备模块 ===")
    try:
        from app.system_devices import list_connected_bluetooth_devices
        print("✓ 成功导入 list_connected_bluetooth_devices")
        
        print("开始获取蓝牙设备列表...")
        devices = list_connected_bluetooth_devices()
        print(f"✓ 成功获取 {len(devices)} 个设备")
        
        for i, device in enumerate(devices):
            print(f"  设备 {i+1}: {device.name} ({device.address}) - 连接: {device.is_connected}, 配对: {device.is_paired}")
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        print("详细错误信息:")
        traceback.print_exc()
        return False
    
    return True

def test_powershell_directly():
    """直接测试 PowerShell 命令"""
    print("\n=== 直接测试 PowerShell ===")
    try:
        import subprocess
        import json
        
        # 测试基本的 PowerShell 命令
        cmd = ["powershell", "-NoProfile", "-Command", "Get-Command Get-PnpDevice"]
        print(f"执行命令: {cmd}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        
        print(f"返回码: {result.returncode}")
        print(f"stdout: {result.stdout[:200]}")
        print(f"stderr: {result.stderr[:200]}")
        
        if result.returncode == 0:
            print("✓ PowerShell 可用")
            
            # 测试蓝牙设备命令
            bluetooth_cmd = ["powershell", "-NoProfile", "-Command", "Get-PnpDevice -Class Bluetooth | Select-Object InstanceId, FriendlyName, Status | ConvertTo-Json"]
            print(f"\n执行蓝牙设备命令...")
            bt_result = subprocess.run(bluetooth_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            
            print(f"返回码: {bt_result.returncode}")
            print(f"stdout: {bt_result.stdout[:300]}")
            print(f"stderr: {bt_result.stderr[:200]}")
            
            if bt_result.returncode == 0 and bt_result.stdout.strip():
                try:
                    data = json.loads(bt_result.stdout.strip())
                    print(f"✓ 成功解析 JSON，设备数量: {len(data) if isinstance(data, list) else 1}")
                except json.JSONDecodeError as e:
                    print(f"✗ JSON 解析失败: {e}")
                    return False
            else:
                print("✗ 蓝牙设备命令失败")
                return False
        else:
            print("✗ PowerShell 不可用")
            return False
            
    except Exception as e:
        print(f"✗ PowerShell 测试失败: {e}")
        traceback.print_exc()
        return False
    
    return True

def main():
    """主测试函数"""
    print("开始扫描功能诊断测试...")
    
    # 测试 PowerShell
    ps_ok = test_powershell_directly()
    
    # 测试系统设备模块
    devices_ok = test_system_devices()
    
    print(f"\n=== 测试结果总结 ===")
    print(f"PowerShell 测试: {'✓ 通过' if ps_ok else '✗ 失败'}")
    print(f"系统设备测试: {'✓ 通过' if devices_ok else '✗ 失败'}")
    
    if ps_ok and devices_ok:
        print("✓ 所有测试通过！扫描功能应该正常工作。")
        return 0
    else:
        print("✗ 测试失败，请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())