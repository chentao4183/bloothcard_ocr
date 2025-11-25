#!/usr/bin/env python3
"""
直接运行主应用，查看详细日志
"""

import sys
import os
import time
import logging

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app_debug.log', encoding='utf-8')
    ]
)

# 添加到Python路径
sys.path.insert(0, 'app')

try:
    from main import main
    
    print("=== 直接运行主应用 ===")
    print("日志将同时输出到控制台和 app_debug.log 文件")
    
    # 运行主应用
    try:
        main()
    except Exception as e:
        logging.error(f"主应用运行错误: {e}", exc_info=True)
        print(f"主应用运行错误: {e}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"运行主应用失败: {e}")
    import traceback
    traceback.print_exc()
    
    # 检查是否有日志文件
    if os.path.exists('app_debug.log'):
        print("\n=== 日志文件内容 ===")
        with open('app_debug.log', 'r', encoding='utf-8') as f:
            print(f.read()[-2000:])  # 显示最后2000字符