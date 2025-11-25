#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新后的HID监听器（使用SimpleHidListener）
"""

import sys
import os
import time
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_hid.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def on_card_data(value, device_name="未知设备"):
    """测试用的卡号数据回调函数"""
    logger.info(f"[回调] 收到卡号数据: {value} (来自设备: {device_name})")
    print(f"\n=== 检测到卡号 ===")
    print(f"卡号: {value}")
    print(f"设备: {device_name}")
    print("==================")

def main():
    """主测试函数"""
    logger.info("启动HID监听器测试...")
    print("HID监听器测试 (使用SimpleHidListener)")
    print("按 Ctrl+C 停止测试")
    print("=" * 50)
    
    try:
        # 导入更新后的HidListener
        from app.hid_listener_simple import SimpleHidListener
        
        # 创建监听器实例
        listener = SimpleHidListener(
            device_keywords=['Bluetooth', 'Keyboard'],
            digit_length=10,
            require_enter=False,
            callback=on_card_data,
            logger=lambda msg: logger.debug(f"[HID] {msg}")
        )
        
        logger.info("创建HidListener实例成功")
        
        # 启动监听器
        start_result = listener.start()
        logger.info(f"启动监听器结果: {start_result}")
        
        if not start_result:
            logger.error("启动监听器失败")
            print("错误: 启动监听器失败")
            return 1
        
        print("监听器已启动，正在等待蓝牙刷卡器输入...")
        print("(如果有蓝牙键盘连接，尝试输入一些数字)")
        
        # 定期检查监听器状态
        count = 0
        while True:
            time.sleep(5)
            count += 1
            logger.info(f"监听器运行状态检查 #{count}: 线程活跃={listener.is_alive()}")
            print(f"\r状态: 运行中 ({count} × 5秒) 线程={listener.is_alive()}", end="", flush=True)
            
    except KeyboardInterrupt:
        logger.info("用户中断测试")
        print("\n\n用户中断，停止测试")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保监听器被正确停止
        if 'listener' in locals() and listener:
            logger.info("停止监听器")
            listener.stop()
            try:
                listener.join(timeout=1.0)
            except Exception:
                pass
    
    logger.info("测试结束")
    return 0

if __name__ == "__main__":
    sys.exit(main())
