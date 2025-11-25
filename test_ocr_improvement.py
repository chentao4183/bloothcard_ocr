#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR识别改进测试脚本
用于验证OCR识别功能的改进效果
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ocr_engine import get_ocr_engine, recognize_screen_area
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def create_test_image():
    """创建测试图片"""
    # 创建一个白色背景的图片
    img = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(img)
    
    # 尝试使用系统字体
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = None
    
    # 绘制测试文字
    draw.text((10, 20), "测试文字123", fill='black', font=font)
    draw.text((10, 50), "ABC123XYZ", fill='darkblue', font=font)
    
    # 保存测试图片
    test_path = "test_ocr_improvement.png"
    img.save(test_path)
    return test_path

def test_ocr_engines():
    """测试不同OCR引擎的识别效果"""
    print("=== OCR识别改进测试 ===\n")
    
    try:
        # 获取OCR引擎
        engine = get_ocr_engine()
        engine_info = engine.get_engine_info()
        
        print(f"当前使用OCR引擎: {engine_info.get('engine', '未知')}")
        print(f"描述: {engine_info.get('description', '无描述')}")
        print()
        
        # 创建测试图片
        test_image = create_test_image()
        print(f"✓ 创建测试图片: {test_image}")
        
        # 测试图片识别
        print("\n--- 测试图片识别 ---")
        result = engine.recognize_from_image(test_image)
        print(f"识别结果: '{result}'")
        
        if result and result.strip():
            print("✓ 图片识别成功")
        else:
            print("✗ 图片识别失败")
        
        # 测试重试机制
        print("\n--- 测试重试机制 ---")
        print("测试小区域识别（模拟实际使用场景）...")
        
        # 模拟小区域识别（使用测试图片的一小部分）
        img = Image.open(test_image)
        small_area = img.crop((10, 20, 120, 70))  # 只包含第一行文字
        small_area_path = "test_small_area.png"
        small_area.save(small_area_path)
        
        # 测试预处理效果
        result_small = engine.recognize_from_image(small_area_path)
        print(f"小区域识别结果: '{result_small}'")
        
        if result_small and result_small.strip():
            print("✓ 小区域识别成功")
        else:
            print("✗ 小区域识别失败，可能需要调整预处理参数")
        
        # 清理测试文件
        if os.path.exists(test_image):
            os.remove(test_image)
        if os.path.exists(small_area_path):
            os.remove(small_area_path)
        
        print("\n=== 测试完成 ===")
        
        # 提供建议
        print("\n建议:")
        if not result or not result.strip():
            print("1. 检查OCR引擎是否正常工作")
            print("2. 调整图像预处理参数")
            print("3. 确保测试图片文字清晰")
        else:
            print("✓ OCR引擎工作正常")
            if not result_small or not result_small.strip():
                print("- 小区域识别可能需要优化预处理")
                print("- 考虑调整置信度阈值")
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_ocr_engines()
    sys.exit(0 if success else 1)