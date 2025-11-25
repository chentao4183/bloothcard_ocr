"""
OCR文字识别引擎模块 - 智能选择版本
根据可用库自动选择最佳的OCR引擎
优先级: PaddleOCR > EasyOCR > Tesseract
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Union
import warnings

# 尝试导入各种OCR库，按优先级排序
OCR_ENGINES = {}
CURRENT_ENGINE = None

# 尝试PaddleOCR
try:
    from paddleocr import PaddleOCR
    OCR_ENGINES['paddle'] = {
        'available': True,
        'engine': 'PaddleOCR',
        'description': '百度PaddleOCR - 中文优化，轻量级'
    }
except ImportError:
    pass

# 尝试EasyOCR
try:
    import easyocr
    OCR_ENGINES['easyocr'] = {
        'available': True,
        'engine': 'EasyOCR',
        'description': '基于PyTorch的OCR库 - 支持多语言'
    }
    print("✓ EasyOCR 可用")
except Exception as e:
    print(f"✗ EasyOCR 不可用: {e}")
    OCR_ENGINES['easyocr'] = {
        'available': False,
        'engine': 'EasyOCR',
        'description': f'不可用: {e}'
    }

# 尝试Tesseract
try:
    import pytesseract
    OCR_ENGINES['tesseract'] = {
        'available': True,
        'engine': 'Tesseract',
        'description': 'Google Tesseract - 传统OCR引擎'
    }
except ImportError:
    pass

# 检查Pillow是否可用
try:
    import PIL.Image
    import PIL.ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class BaseOCREngine:
    """OCR引擎基类"""
    
    def recognize_from_image(self, image) -> str:
        """从图片中识别文字"""
        raise NotImplementedError
    
    def recognize_from_screen_area(self, x: int, y: int, width: int, height: int) -> str:
        """从屏幕指定区域识别文字"""
        raise NotImplementedError
    
    def save_area_screenshot(self, x: int, y: int, width: int, height: int, save_path: str) -> bool:
        """保存屏幕指定区域的截图"""
        raise NotImplementedError


class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR引擎"""
    
    def __init__(self):
        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
        except Exception as e:
            raise RuntimeError(f"PaddleOCR初始化失败: {e}")
    
    def recognize_from_image(self, image: Union[PIL.Image.Image, str]) -> str:
        """从图片中识别文字，包含图像预处理"""
        # 如果传入的是文件路径，先加载图片
        if isinstance(image, str):
            image = PIL.Image.open(image)
        
        # 图像预处理以提高识别准确率
        processed_image = self._preprocess_image(image)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            processed_image.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            results = self.ocr.ocr(tmp_path, cls=True)
            text_parts = []
            if results and results[0]:
                for line in results[0]:
                    text = line[1][0]
                    confidence = line[1][1]
                    if confidence > 0.3:  # 降低置信度阈值以提高识别率
                        text_parts.append(text.strip())
            
            # 合并文本，移除多余的空白
            result_text = ' '.join(text_parts).strip()
            return result_text
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def _preprocess_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
        """图像预处理以提高OCR识别率"""
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # 转换为RGB模式（如果不是）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 1. 增强对比度
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # 适度增强对比度
            
            # 2. 增强锐度
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)  # 适度锐化
            
            # 3. 如果图像太小，稍微放大
            if image.width < 100 or image.height < 30:
                new_width = max(image.width * 2, 100)
                new_height = max(image.height * 2, 30)
                image = image.resize((new_width, new_height), PIL.Image.LANCZOS)
            
            return image
            
        except Exception as e:
            print(f"图像预处理失败: {e}，使用原图")
            return image
    
    def recognize_from_screen_area(self, x: int, y: int, width: int, height: int) -> str:
        screenshot = PIL.ImageGrab.grab(bbox=(x, y, x + width, y + height))
        return self.recognize_from_image(screenshot)
    
    def save_area_screenshot(self, x: int, y: int, width: int, height: int, save_path: str) -> bool:
        try:
            screenshot = PIL.ImageGrab.grab(bbox=(x, y, x + width, y + height))
            screenshot.save(save_path)
            return True
        except Exception as e:
            print(f"保存截图失败: {e}")
            return False


class EasyOCREngine(BaseOCREngine):
    """EasyOCR引擎"""
    
    def __init__(self):
        try:
            self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        except Exception as e:
            raise RuntimeError(f"EasyOCR初始化失败: {e}")
    
    def recognize_from_image(self, image: Union[PIL.Image.Image, str]) -> str:
        """从图片中识别文字，包含图像预处理"""
        # 如果传入的是文件路径，先加载图片
        if isinstance(image, str):
            image = PIL.Image.open(image)
        
        # 图像预处理以提高识别准确率
        processed_image = self._preprocess_image(image)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            processed_image.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            results = self.reader.readtext(tmp_path)
            text_parts = []
            for (bbox, text, confidence) in results:
                # 过滤低置信度的结果
                if confidence > 0.3:  # 降低置信度阈值
                    text_parts.append(text.strip())
            
            # 合并文本，移除多余的空白
            result_text = ' '.join(text_parts).strip()
            return result_text
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def _preprocess_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
        """图像预处理以提高OCR识别率"""
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # 转换为RGB模式（如果不是）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 1. 增强对比度
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # 适度增强对比度
            
            # 2. 增强锐度
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)  # 适度锐化
            
            # 3. 如果图像太小，稍微放大
            if image.width < 100 or image.height < 30:
                new_width = max(image.width * 2, 100)
                new_height = max(image.height * 2, 30)
                image = image.resize((new_width, new_height), PIL.Image.LANCZOS)
            
            return image
            
        except Exception as e:
            print(f"图像预处理失败: {e}，使用原图")
            return image
    
    def recognize_from_screen_area(self, x: int, y: int, width: int, height: int) -> str:
        screenshot = PIL.ImageGrab.grab(bbox=(x, y, x + width, y + height))
        return self.recognize_from_image(screenshot)
    
    def save_area_screenshot(self, x: int, y: int, width: int, height: int, save_path: str) -> bool:
        try:
            screenshot = PIL.ImageGrab.grab(bbox=(x, y, x + width, y + height))
            screenshot.save(save_path)
            return True
        except Exception as e:
            print(f"保存截图失败: {e}")
            return False


class TesseractEngine(BaseOCREngine):
    """Tesseract引擎"""
    
    def __init__(self):
        try:
            pytesseract.get_tesseract_version()
        except:
            raise RuntimeError("Tesseract-OCR引擎未安装或未配置")
    
    def recognize_from_image(self, image: PIL.Image.Image) -> str:
        try:
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            return text.strip()
        except Exception as e:
            raise RuntimeError(f"OCR识别失败: {e}")
    
    def recognize_from_screen_area(self, x: int, y: int, width: int, height: int) -> str:
        screenshot = PIL.ImageGrab.grab(bbox=(x, y, x + width, y + height))
        return self.recognize_from_image(screenshot)
    
    def save_area_screenshot(self, x: int, y: int, width: int, height: int, save_path: str) -> bool:
        try:
            screenshot = PIL.ImageGrab.grab(bbox=(x, y, x + width, y + height))
            screenshot.save(save_path)
            return True
        except Exception as e:
            print(f"保存截图失败: {e}")
            return False


class OCREngine:
    """智能OCR引擎 - 自动选择最佳引擎"""
    
    def __init__(self, preferred_engine: str = None):
        """
        初始化OCR引擎
        
        Args:
            preferred_engine: 优先使用的引擎类型，如果为None则自动选择
        """
        self.engine = None
        self.engine_name = None
        
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow库不可用，OCR功能无法使用")
        
        # 如果指定了优先引擎，尝试使用它
        if preferred_engine and preferred_engine in OCR_ENGINES:
            try:
                if preferred_engine == 'paddle':
                    self.engine = PaddleOCREngine()
                elif preferred_engine == 'easyocr':
                    self.engine = EasyOCREngine()
                elif preferred_engine == 'tesseract':
                    self.engine = TesseractEngine()
                
                self.engine_name = preferred_engine
                print(f"使用OCR引擎: {OCR_ENGINES[preferred_engine]['description']}")
                return
            except Exception as e:
                warnings.warn(f"{OCR_ENGINES[preferred_engine]['engine']}初始化失败: {e}")
        
        # 按优先级尝试各个引擎
        for engine_type in ['paddle', 'easyocr', 'tesseract']:
            if engine_type in OCR_ENGINES:
                try:
                    if engine_type == 'paddle':
                        self.engine = PaddleOCREngine()
                    elif engine_type == 'easyocr':
                        self.engine = EasyOCREngine()
                    elif engine_type == 'tesseract':
                        self.engine = TesseractEngine()
                    
                    self.engine_name = engine_type
                    print(f"使用OCR引擎: {OCR_ENGINES[engine_type]['description']}")
                    break
                    
                except Exception as e:
                    warnings.warn(f"{OCR_ENGINES[engine_type]['engine']}初始化失败: {e}")
                    continue
        
        if self.engine is None:
            warnings.warn("没有可用的OCR引擎，将使用空引擎（所有识别返回空字符串）")
            self.engine_name = "none"
    
    def recognize_from_image(self, image: PIL.Image.Image) -> str:
        """从图片中识别文字"""
        if self.engine is None:
            return ""
        return self.engine.recognize_from_image(image)
    
    def recognize_from_screen_area(self, x: int, y: int, width: int, height: int) -> str:
        """从屏幕指定区域识别文字"""
        if self.engine is None:
            return ""
        return self.engine.recognize_from_screen_area(x, y, width, height)
    
    def save_area_screenshot(self, x: int, y: int, width: int, height: int, save_path: str) -> bool:
        """保存屏幕指定区域的截图"""
        if self.engine is None:
            # 即使没有OCR引擎，也可以保存截图
            try:
                screenshot = PIL.ImageGrab.grab(bbox=(x, y, x + width, y + height))
                screenshot.save(save_path)
                return True
            except Exception:
                return False
        return self.engine.save_area_screenshot(x, y, width, height, save_path)
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取当前引擎信息"""
        if self.engine is None:
            return {}
        if self.engine_name and self.engine_name in OCR_ENGINES:
            return OCR_ENGINES[self.engine_name].copy()
        return {}
    
    @staticmethod
    def is_available() -> bool:
        """检查OCR功能是否可用"""
        return PIL_AVAILABLE and len(OCR_ENGINES) > 0
    
    @staticmethod
    def get_available_engines() -> Dict[str, Dict[str, Any]]:
        """获取所有可用引擎信息"""
        return OCR_ENGINES.copy()
    
    @staticmethod
    def is_available() -> bool:
        """检查OCR功能是否可用"""
        return PIL_AVAILABLE and len(OCR_ENGINES) > 0


# 全局OCR引擎实例
_ocr_engine: Optional[OCREngine] = None


def get_ocr_engine() -> OCREngine:
    """
    获取全局OCR引擎实例
    
    Returns:
        OCREngine实例
    """
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine


def get_available_engines() -> Dict[str, Dict[str, Any]]:
    """获取所有可用引擎信息"""
    return OCR_ENGINES.copy()

def recognize_screen_area(x: int, y: int, width: int, height: int) -> str:
    """
    便捷的屏幕区域文字识别函数
    
    Args:
        x: 区域左上角x坐标
        y: 区域左上角y坐标
        width: 区域宽度
        height: 区域高度
        
    Returns:
        识别出的文字内容，失败时返回空字符串
    """
    try:
        engine = get_ocr_engine()
        return engine.recognize_from_screen_area(x, y, width, height)
    except Exception as e:
        print(f"OCR识别失败: {e}")
        return ""


def save_area_screenshot(x: int, y: int, width: int, height: int, save_path: str) -> bool:
    """
    便捷的屏幕区域截图保存函数
    
    Args:
        x: 区域左上角x坐标
        y: 区域左上角y坐标
        width: 区域宽度
        height: 区域高度
        save_path: 保存路径
        
    Returns:
        是否保存成功
    """
    try:
        engine = get_ocr_engine()
        return engine.save_area_screenshot(x, y, width, height, save_path)
    except Exception as e:
        print(f"保存截图失败: {e}")
        return False