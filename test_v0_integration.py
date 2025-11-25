#!/usr/bin/env python3
"""测试V0.0版本集成功能"""

import json
import sys
import os
from pathlib import Path

# 添加app目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config_manager import ConfigManager

def test_v0_config():
    """测试V0.0版本配置"""
    config_path = Path('app_settings.json')
    config_manager = ConfigManager(config_path)
    config = config_manager.load()
    
    print("=== V0.0版本配置测试 ===")
    print(f"当前选择的版本: {config.service.selected_version}")
    print(f"可用版本: {list(config.service.versions.keys())}")
    
    v0_config = config.service.versions.get("v0")
    if v0_config:
        print(f"V0.0调试URL: {v0_config.debug_url}")
        print("✓ V0.0版本配置正常")
    else:
        print("✗ V0.0版本配置缺失")
        return False
    
    # 测试切换到V0.0版本
    config.service.selected_version = "v0"
    config_manager.save(config)
    print("✓ 已切换到V0.0版本")
    
    return True

def test_ocr_fields():
    """测试OCR字段配置"""
    config_path = Path('app_settings.json')
    config_manager = ConfigManager(config_path)
    config = config_manager.load()
    
    print("\n=== OCR字段测试 ===")
    print(f"OCR字段数量: {len(config.ocr_fields)}")
    
    for field in config.ocr_fields:
        if field.enabled:
            print(f"✓ {field.name}: param={field.param_name}, default={field.default_value}")
        else:
            print(f"✗ {field.name}: 已禁用")
    
    return True

if __name__ == "__main__":
    print("开始测试V0.0版本集成...")
    
    success = True
    success &= test_v0_config()
    success &= test_ocr_fields()
    
    if success:
        print("\n✓ 所有测试通过！V0.0版本集成正常")
    else:
        print("\n✗ 部分测试失败")
        sys.exit(1)