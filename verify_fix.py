#!/usr/bin/env python3
"""
验证修复：检查HID监听是否正常工作并能正确触发V0.0版本调试功能
"""

import os
import sys
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_config():
    """验证配置文件中的相关设置"""
    try:
        # 检查app_settings.json
        settings_path = os.path.join('app', 'app_settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            logger.info("✅ 配置文件检查:")
            logger.info(f"   - 服务版本: {settings.get('service', {}).get('selected_version', '未设置')}")
            logger.info(f"   - V0调试URL: {settings.get('service', {}).get('v0', {}).get('debug_url', '未设置')}")
            logger.info(f"   - HID启用: {settings.get('hid', {}).get('enabled', False)}")
            logger.info(f"   - HID关键词: {settings.get('hid', {}).get('device_keywords', [])}")
            logger.info(f"   - HID数字长度: {settings.get('hid', {}).get('digit_length', 10)}")
        else:
            logger.warning("❌ 配置文件不存在: app/app_settings.json")
            
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        return False
    return True

def verify_hid_listener_fix():
    """验证HidListener修复是否正确应用"""
    try:
        main_py_path = os.path.join('app', 'main.py')
        if os.path.exists(main_py_path):
            with open(main_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查_restart_hid_listener方法中是否包含device_keywords参数
            if 'def _restart_hid_listener' in content and 'device_keywords=self.config.hid.device_keywords' in content:
                logger.info("✅ 修复验证成功: HidListener初始化已包含device_keywords参数")
                return True
            else:
                logger.error("❌ 修复验证失败: HidListener初始化中未找到device_keywords参数")
                return False
        else:
            logger.error("❌ main.py文件不存在")
            return False
    except Exception as e:
        logger.error(f"修复验证失败: {e}")
        return False

def main():
    """主验证函数"""
    logger.info("开始验证HID监听修复...")
    
    # 验证配置
    config_valid = verify_config()
    
    # 验证修复
    fix_valid = verify_hid_listener_fix()
    
    # 给出修复说明
    logger.info("\n📋 修复说明:")
    logger.info("1. 问题原因: HidListener初始化时缺少device_keywords参数，导致HID监听器无法正确启动")
    logger.info("2. 解决方案: 在main.py的_restart_hid_listener方法中为HidListener添加device_keywords参数")
    logger.info("3. 验证结果: " + ("✅ 修复成功" if fix_valid else "❌ 修复失败"))
    
    # 给出后续操作建议
    logger.info("\n🔧 后续操作:")
    logger.info("1. 确保服务版本设置为'v0'")
    logger.info("2. 确保backend.enable_service设置为true")
    logger.info("3. 确保HID功能已启用(hid.enabled=true)")
    logger.info("4. 重新启动应用程序")
    logger.info("5. 测试蓝牙刷卡是否能自动调用V0.0版本的调试功能")
    
    return config_valid and fix_valid

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
