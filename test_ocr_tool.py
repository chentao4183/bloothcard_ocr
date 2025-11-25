#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR工具测试程序
用于测试OCR功能是否正常工作
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from app.ocr_engine import OCREngine, recognize_screen_area, get_available_engines
from app.screenshot_selector import ScreenshotSelector

class OCRToolTester:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OCR工具测试")
        self.root.geometry("600x400")
        
        # OCR引擎
        self.ocr_engine = None
        self.init_ocr_engine()
        
        self.setup_ui()
        
    def init_ocr_engine(self):
        """初始化OCR引擎"""
        try:
            self.ocr_engine = OCREngine()
            print("✓ OCR引擎初始化成功")
        except Exception as e:
            print(f"✗ OCR引擎初始化失败: {e}")
            messagebox.showerror("错误", f"OCR引擎初始化失败: {e}")
            
    def setup_ui(self):
        """设置界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # OCR状态信息
        status_frame = ttk.LabelFrame(main_frame, text="OCR状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 可用引擎信息
        engines = get_available_engines()
        engine_info = "可用引擎:\n"
        for name, info in engines.items():
            status = "✓" if info.get('available', False) else "✗"
            engine_info += f"  {status} {info.get('engine', name)}: {info.get('description', '无描述')}\n"
        
        ttk.Label(status_frame, text=engine_info, justify=tk.LEFT).pack(anchor=tk.W)
        
        # 当前引擎信息
        if self.ocr_engine:
            current_info = self.ocr_engine.get_engine_info()
            current_text = f"当前引擎: {current_info.get('engine', '未知')} - {current_info.get('description', '无描述')}"
            ttk.Label(status_frame, text=current_text, font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5, 0))
        
        # 测试功能区域
        test_frame = ttk.LabelFrame(main_frame, text="测试功能", padding="10")
        test_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 按钮区域
        button_frame = ttk.Frame(test_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="测试屏幕区域识别", command=self.test_screen_area).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="选择屏幕区域并识别", command=self.select_and_recognize).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="测试OCR引擎", command=self.test_ocr_engine).pack(side=tk.LEFT, padx=5)
        
        # 结果显示
        result_frame = ttk.LabelFrame(test_frame, text="识别结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 滚动文本框显示结果
        self.result_text = tk.Text(result_frame, height=10, width=60)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
    def log_result(self, message):
        """记录结果到文本框"""
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)
        self.root.update()
        
    def set_status(self, message):
        """设置状态栏信息"""
        self.status_var.set(message)
        self.root.update()
        
    def test_ocr_engine(self):
        """测试OCR引擎基本功能"""
        if not self.ocr_engine:
            messagebox.showerror("错误", "OCR引擎未初始化")
            return
            
        self.set_status("正在测试OCR引擎...")
        self.log_result("=== 开始OCR引擎测试 ===")
        
        try:
            # 获取引擎信息
            engine_info = self.ocr_engine.get_engine_info()
            self.log_result(f"引擎信息: {engine_info}")
            
            # 创建一个简单的测试图片（白色背景，黑色文字）
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建测试图片
            img = Image.new('RGB', (200, 50), color='white')
            draw = ImageDraw.Draw(img)
            
            # 尝试使用系统字体，如果失败则使用默认字体
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
                
            # 绘制测试文字
            draw.text((10, 10), "测试文字123", fill='black', font=font)
            
            # 保存测试图片
            test_img_path = "test_ocr_image.png"
            img.save(test_img_path)
            self.log_result(f"测试图片已保存: {test_img_path}")
            
            # 进行OCR识别
            self.log_result("正在进行OCR识别...")
            result = self.ocr_engine.recognize_from_image(img)
            
            if result:
                self.log_result(f"✓ 识别成功: '{result}'")
            else:
                self.log_result("! 未识别到文字")
                
            self.log_result("=== OCR引擎测试完成 ===")
            
        except Exception as e:
            self.log_result(f"✗ 测试失败: {e}")
            messagebox.showerror("错误", f"OCR引擎测试失败: {e}")
            
        self.set_status("就绪")
        
    def test_screen_area(self):
        """测试屏幕区域识别"""
        self.set_status("正在测试屏幕区域识别...")
        self.log_result("=== 开始屏幕区域识别测试 ===")
        
        try:
            # 获取屏幕中心区域进行测试
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 测试屏幕左上角区域 (100x100)
            x, y, w, h = 0, 0, 200, 100
            self.log_result(f"测试区域: ({x}, {y}, {w}, {h})")
            
            result = recognize_screen_area(x, y, w, h)
            
            if result:
                self.log_result(f"✓ 识别结果: '{result}'")
            else:
                self.log_result("! 未识别到文字")
                
            self.log_result("=== 屏幕区域识别测试完成 ===")
            
        except Exception as e:
            self.log_result(f"✗ 测试失败: {e}")
            messagebox.showerror("错误", f"屏幕区域识别测试失败: {e}")
            
        self.set_status("就绪")
        
    def select_and_recognize(self):
        """选择屏幕区域并进行识别"""
        self.set_status("等待用户选择屏幕区域...")
        self.log_result("=== 开始选择屏幕区域识别 ===")
        
        try:
            # 最小化窗口以便选择
            self.root.withdraw()
            time.sleep(0.5)
            
            # 创建选择器
            selector = ScreenshotSelector()
            result = selector.get_screen_area()
            
            if result:
                x, y, w, h = result
                self.log_result(f"选择区域: ({x}, {y}, {w}, {h})")
                
                # 进行OCR识别
                self.set_status("正在进行OCR识别...")
                recognized_text = recognize_screen_area(x, y, w, h)
                
                # 恢复窗口
                self.root.deiconify()
                
                if recognized_text:
                    self.log_result(f"✓ 识别结果: '{recognized_text}'")
                    messagebox.showinfo("识别成功", f"识别结果:\n{recognized_text}")
                else:
                    self.log_result("! 未识别到文字")
                    messagebox.showinfo("识别结果", "未识别到文字内容")
                    
            else:
                self.log_result("用户取消了选择")
                self.root.deiconify()
                
            self.log_result("=== 选择屏幕区域识别完成 ===")
            
        except Exception as e:
            self.root.deiconify()
            self.log_result(f"✗ 识别失败: {e}")
            messagebox.showerror("错误", f"OCR识别失败: {e}")
            
        self.set_status("就绪")
        
    def run(self):
        """运行应用"""
        self.log_result("OCR工具测试程序已启动")
        self.log_result("请使用上方按钮测试OCR功能")
        self.log_result("-" * 50)
        
        self.root.mainloop()

if __name__ == "__main__":
    app = OCRToolTester()
    app.run()