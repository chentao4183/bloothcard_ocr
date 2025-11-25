#!/usr/bin/env python3
"""
OCR识别问题诊断脚本
用于测试和诊断OCR识别功能的问题
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ocr_engines():
    """测试所有可用的OCR引擎"""
    print("=== OCR引擎测试开始 ===")
    
    try:
        from app.ocr_engine import get_available_engines, get_ocr_engine, OCREngine
        
        # 检查可用引擎
        available_engines = get_available_engines()
        print(f"可用OCR引擎: {len(available_engines)}")
        
        for engine_name, info in available_engines.items():
            status = "可用" if info['available'] else "不可用"
            print(f"  - {engine_name}: {status} - {info['description']}")
        
        # 测试当前引擎
        print("\n--- 初始化OCR引擎 ---")
        try:
            engine = get_ocr_engine()
            engine_info = engine.get_engine_info()
            print(f"当前引擎: {engine_info.get('engine', '未知')}")
            print(f"描述: {engine_info.get('description', '无描述')}")
        except Exception as e:
            print(f"OCR引擎初始化失败: {e}")
            return
            
        # 测试屏幕截图功能
        print("\n--- 测试屏幕截图功能 ---")
        try:
            # 测试小区域截图（100x100像素）
            test_area = (100, 100, 100, 100)  # x, y, width, height
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_image = f"test_screenshot_{timestamp}.png"
            
            success = engine.save_area_screenshot(*test_area, test_image)
            if success and os.path.exists(test_image):
                print(f"✓ 截图测试成功: {test_image}")
                
                # 测试OCR识别
                print("\n--- 测试OCR识别 ---")
                try:
                    from PIL import Image
                    with Image.open(test_image) as img:
                        recognized_text = engine.recognize_from_image(img)
                        print(f"识别结果: '{recognized_text}'")
                        
                        if recognized_text.strip():
                            print("✓ OCR识别功能正常")
                        else:
                            print("⚠ OCR未识别到文字（可能是截图区域无文字内容）")
                            
                except Exception as e:
                    print(f"✗ OCR识别失败: {e}")
                
                # 清理测试文件
                try:
                    os.remove(test_image)
                    print(f"已清理测试文件: {test_image}")
                except:
                    pass
                    
            else:
                print(f"✗ 截图测试失败")
                
        except Exception as e:
            print(f"✗ 截图功能测试失败: {e}")
            
        # 测试直接屏幕区域识别
        print("\n--- 测试直接屏幕区域识别 ---")
        try:
            # 测试屏幕左上角区域（通常会有窗口标题等文字）
            test_text = engine.recognize_from_screen_area(0, 0, 200, 50)
            print(f"屏幕区域识别结果: '{test_text}'")
            
            if test_text.strip():
                print("✓ 直接屏幕识别功能正常")
            else:
                print("⚠ 未识别到文字（可能是屏幕区域无文字或识别敏感度问题）")
                
        except Exception as e:
            print(f"✗ 直接屏幕识别测试失败: {e}")
            
    except ImportError as e:
        print(f"✗ 导入模块失败: {e}")
        print("请确保在项目根目录下运行此脚本")
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

def test_image_preprocessing():
    """测试图像预处理效果"""
    print("\n=== 图像预处理测试 ===")
    
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        import numpy as np
        
        # 创建测试图像（包含文字）
        test_image_path = "test_ocr_image.png"
        
        # 如果存在测试图像，使用它进行测试
        if os.path.exists(test_image_path):
            print(f"使用现有测试图像: {test_image_path}")
            with Image.open(test_image_path) as img:
                test_ocr_with_preprocessing(img)
        else:
            print("创建测试图像...")
            # 创建一个简单的测试图像
            img = Image.new('RGB', (200, 50), color='white')
            
            # 这里可以添加文字绘制，但需要PIL的ImageDraw
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                
                # 尝试使用系统字体
                font_size = 20
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.load_default()
                    except:
                        font = None
                
                if font:
                    draw.text((10, 10), "测试文字123", fill='black', font=font)
                    print("✓ 测试图像创建成功")
                    test_ocr_with_preprocessing(img)
                else:
                    print("⚠ 无法创建字体，跳过图像预处理测试")
                    
            except ImportError:
                print("⚠ 缺少ImageDraw模块，跳过图像预处理测试")
                
    except Exception as e:
        print(f"✗ 图像预处理测试失败: {e}")

def test_ocr_with_preprocessing(image):
    """使用不同预处理方法测试OCR"""
    try:
        from app.ocr_engine import get_ocr_engine
        engine = get_ocr_engine()
        
        print("\n--- 原始图像识别 ---")
        original_text = engine.recognize_from_image(image)
        print(f"原始识别结果: '{original_text}'")
        
        # 测试不同的预处理方法
        preprocessing_methods = [
            ("增强对比度", lambda img: ImageEnhance.Contrast(img).enhance(2.0)),
            ("锐化", lambda img: img.filter(ImageFilter.SHARPEN)),
            ("灰度化", lambda img: img.convert('L')),
            ("二值化", lambda img: img.convert('L').point(lambda x: 0 if x < 128 else 255, '1')),
            ("增强亮度", lambda img: ImageEnhance.Brightness(img).enhance(1.2)),
        ]
        
        for method_name, preprocessor in preprocessing_methods:
            try:
                processed_img = preprocessor(image)
                recognized_text = engine.recognize_from_image(processed_img)
                print(f"{method_name}识别结果: '{recognized_text}'")
            except Exception as e:
                print(f"{method_name}处理失败: {e}")
                
    except Exception as e:
        print(f"✗ 预处理测试失败: {e}")

def test_common_issues():
    """测试常见OCR问题"""
    print("\n=== 常见问题诊断 ===")
    
    # 检查依赖库
    print("\n--- 依赖库检查 ---")
    dependencies = [
        ("PIL/Pillow", "from PIL import Image"),
        ("numpy", "import numpy"),
        ("paddleocr", "from paddleocr import PaddleOCR"),
        ("easyocr", "import easyocr"),
        ("pytesseract", "import pytesseract"),
    ]
    
    for lib_name, import_statement in dependencies:
        try:
            exec(import_statement)
            print(f"✓ {lib_name} 可用")
        except ImportError as e:
            print(f"✗ {lib_name} 不可用: {e}")
    
    # 检查Tesseract安装
    print("\n--- Tesseract安装检查 ---")
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract版本: {version}")
    except Exception as e:
        print(f"✗ Tesseract检查失败: {e}")
    
    # 检查屏幕截图权限（Windows）
    print("\n--- 屏幕截图权限检查 ---")
    try:
        from PIL import ImageGrab
        # 尝试截图一个小区域
        screenshot = ImageGrab.grab(bbox=(0, 0, 10, 10))
        print("✓ 屏幕截图权限正常")
    except Exception as e:
        print(f"✗ 屏幕截图权限问题: {e}")
        print("  可能需要以管理员身份运行，或检查屏幕录制权限")

if __name__ == "__main__":
    print("OCR识别问题诊断工具")
    print("=" * 50)
    
    # 运行基础测试
    test_ocr_engines()
    
    # 运行图像预处理测试
    test_image_preprocessing()
    
    # 运行常见问题诊断
    test_common_issues()
    
    print("\n" + "=" * 50)
    print("诊断完成！")
    print("\n建议:")
    print("1. 如果OCR引擎不可用，请安装相应的OCR库:")
    print("   - PaddleOCR: pip install paddleocr")
    print("   - EasyOCR: pip install easyocr")
    print("   - Tesseract: pip install pytesseract 并安装Tesseract-OCR软件")
    print("2. 如果截图功能异常，请检查屏幕录制权限或以管理员身份运行")
    print("3. 如果识别率低，可以尝试调整截图区域或图像预处理方法")
    print("4. 确保截图区域有足够清晰的文字内容")