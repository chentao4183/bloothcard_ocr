#!/usr/bin/env python3
"""
调试脚本：测试V0.0版本自动调试功能
用于排查为什么刷卡后没有自动调用调试功能
"""

import json
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 1. 测试配置加载
print("=== 1. 测试配置加载 ===")
try:
    from app.config_manager import ConfigManager, AppConfig
    config_path = Path("app_settings.json")
    if config_path.exists():
        config_manager = ConfigManager(config_path)
        config = config_manager.load()
        print(f"配置加载成功")
        print(f"selected_version: {config.service.selected_version}")
        print(f"enable_service: {config.backend.enable_service}")
        print(f"v0 debug_url: {config.service.versions.get('v0', {}).debug_url if hasattr(config.service.versions.get('v0', {}), 'debug_url') else 'N/A'}")
    else:
        print(f"配置文件不存在: {config_path}")
        # 使用默认配置测试
        config = AppConfig.default()
        print(f"使用默认配置: selected_version={config.service.selected_version}, enable_service={config.backend.enable_service}")
except Exception as e:
    print(f"配置加载失败: {e}")

# 2. 测试OCR引擎初始化
print("\n=== 2. 测试OCR引擎初始化 ===")
try:
    from app.ocr_engine import get_ocr_engine, get_available_engines
    
    # 显示可用的OCR引擎
    available_engines = get_available_engines()
    print(f"可用OCR引擎: {[k for k, v in available_engines.items() if v['available']]}")
    
    # 尝试初始化OCR引擎
    ocr_engine = get_ocr_engine()
    print(f"OCR引擎初始化成功: {ocr_engine.get_engine_info()}")
except Exception as e:
    print(f"OCR引擎初始化失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 模拟_app实例和_debug_v0_system调用
print("\n=== 3. 模拟_debug_v0_system调用 ===")
try:
    # 创建一个最小化的App模拟对象
    class MockApp:
        def __init__(self, config):
            self.config = config
            self.logs = []
        
        def append_log(self, line):
            self.logs.append(line)
            print(f"[LOG] {line}")
        
        def _save_config(self):
            self.append_log("配置已保存")
        
        def _refresh_ocr_tree(self):
            self.append_log("OCR树已刷新")
        
        def _debug_v0_system(self, auto_mode=False):
            """简化版的_debug_v0_system，主要用于测试流程"""
            try:
                # 获取v0版本的调试URL
                v0_config = self.config.service.versions.get("v0")
                if not v0_config or not v0_config.debug_url:
                    self.append_log("错误：V0.0版本的调试URL未配置")
                    return
                
                debug_url = v0_config.debug_url.strip()
                if not debug_url:
                    self.append_log("错误：V0.0版本的调试URL为空")
                    return
                
                self.append_log(f"调试URL: {debug_url}")
                self.append_log("OCR引擎初始化测试...")
                
                # 模拟OCR识别和URL构建
                self.append_log("模拟OCR识别成功")
                self.append_log("构建参数字符串")
                self.append_log("构建完整URL")
                self.append_log("在默认浏览器中打开URL (模拟)")
                self.append_log("V0.0系统调试完成")
                return True
            except Exception as e:
                self.append_log(f"V0.0系统调试失败: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    # 创建模拟App实例并测试
    mock_app = MockApp(config)
    success = mock_app._debug_v0_system(auto_mode=True)
    print(f"_debug_v0_system调用{'成功' if success else '失败'}")
    
    # 检查日志中是否有错误
    errors = [log for log in mock_app.logs if "错误" in log or "失败" in log]
    if errors:
        print(f"发现错误日志: {errors}")
    else:
        print("没有发现错误日志")
        
except Exception as e:
    print(f"模拟调用失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 分析可能的问题
print("\n=== 4. 可能的问题分析 ===")
print("1. 检查配置文件中selected_version是否为'v0'")
print("2. 检查配置文件中enable_service是否为true")
print("3. 检查OCR引擎是否正常工作")
print("4. 检查调试URL是否正确配置")
print("5. 检查是否有异常在执行过程中被捕获但没有显示")
