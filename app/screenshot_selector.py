import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Optional, Tuple
import traceback

try:
    import pyautogui
    import PIL.Image
    import PIL.ImageTk
    import PIL.ImageDraw
    SCREENSHOT_AVAILABLE = True
except ImportError as e:
    SCREENSHOT_AVAILABLE = False
    print(f"截图依赖导入失败: {e}")
    print(f"详细错误: {traceback.format_exc()}")


class ScreenshotSelector:
    """屏幕截图区域选择器，支持鼠标拖拽框选"""
    
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.result = None  # 返回 (x, y, width, height) 或 None
        self.screenshot_thread = None
        
    def select_area(self) -> Optional[Tuple[int, int, int, int]]:
        """打开屏幕截图选择窗口，返回选择的区域坐标"""
        # 检查依赖是否可用
        if not SCREENSHOT_AVAILABLE:
            messagebox.showwarning(
                "依赖缺失",
                "屏幕截图功能需要安装 pyautogui 和 pillow\n"
                "请运行: pip install pyautogui pillow\n"
                "将使用手动输入方式"
            )
            return self._manual_input_area()
            
        # 隐藏父窗口（如果存在）
        if self.parent_window:
            # 使用更激进的隐藏方法
            self.parent_window.withdraw()  # 隐藏窗口
            self.parent_window.attributes('-alpha', 0.0)  # 设置完全透明
            # 确保窗口不在任务栏显示
            self.parent_window.overrideredirect(True)
            
            # 增加等待时间，确保窗口完全隐藏
            # Windows系统窗口隐藏动画通常需要0.5-1秒
            time.sleep(1.0)
            # 额外等待一小段时间，确保系统完成所有UI更新
            self.parent_window.update_idletasks()
            # 强制刷新系统显示
            import ctypes
            ctypes.windll.user32.UpdateWindow(self.parent_window.winfo_id())
            
        try:
            # 执行截图选择
            self.result = None
            self._capture_and_select()
            
            # 恢复父窗口
            if self.parent_window:
                # 添加短暂延迟，确保截图完成后再显示窗口
                time.sleep(0.2)
                # 恢复窗口状态
                self.parent_window.overrideredirect(False)  # 恢复窗口边框
                self.parent_window.attributes('-alpha', 1.0)  # 恢复透明度
                self.parent_window.deiconify()
                # 确保窗口置顶显示
                self.parent_window.attributes('-topmost', True)
                self.parent_window.after(100, lambda: self.parent_window.attributes('-topmost', False))
                
            return self.result
        
        except Exception as e:
            # 恢复父窗口
            if self.parent_window:
                # 恢复窗口状态
                self.parent_window.overrideredirect(False)  # 恢复窗口边框
                self.parent_window.attributes('-alpha', 1.0)  # 恢复透明度
                self.parent_window.deiconify()
                self.parent_window.attributes('-topmost', True)
                self.parent_window.after(100, lambda: self.parent_window.attributes('-topmost', False))
            
            # 显示错误信息
            error_msg = f"截图选择失败：{str(e)}\n\n是否切换到手动输入模式？"
            if messagebox.askyesno("截图错误", error_msg):
                return self._manual_input_area()
            else:
                return None
    
    def _manual_input_area(self) -> Optional[Tuple[int, int, int, int]]:
        """手动输入区域坐标"""
        dialog = tk.Toplevel(self.parent_window)
        dialog.title("设置识别区域")
        dialog.geometry("400x300+100+100")
        dialog.attributes('-topmost', True)
        dialog.transient(self.parent_window)
        
        # 创建提示信息
        tk.Label(dialog, text="手动输入识别区域坐标", font=('Arial', 14, 'bold')).pack(pady=10)
        
        info_text = """
使用说明：
1. 使用系统截图工具获取坐标
2. 输入起始点坐标 (X, Y)
3. 输入区域尺寸 (宽度, 高度)
4. 坐标格式：正整数
        """
        
        tk.Label(dialog, text=info_text, justify=tk.LEFT, wraplength=350).pack(pady=10)
        
        # 坐标输入框
        input_frame = tk.Frame(dialog)
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text="X坐标:").grid(row=0, column=0, padx=5)
        x_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=x_var, width=10).grid(row=0, column=1, padx=5)
        
        tk.Label(input_frame, text="Y坐标:").grid(row=0, column=2, padx=5)
        y_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=y_var, width=10).grid(row=0, column=3, padx=5)
        
        tk.Label(input_frame, text="宽度:").grid(row=1, column=0, padx=5, pady=5)
        w_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=w_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(input_frame, text="高度:").grid(row=1, column=2, padx=5, pady=5)
        h_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=h_var, width=10).grid(row=1, column=3, padx=5, pady=5)
        
        result = None
        
        def on_confirm():
            nonlocal result
            try:
                x = int(x_var.get())
                y = int(y_var.get())
                w = int(w_var.get())
                h = int(h_var.get())
                
                if w > 0 and h > 0 and x >= 0 and y >= 0:
                    result = (x, y, w, h)
                    dialog.destroy()
                else:
                    messagebox.showerror("错误", "请输入有效的正数坐标值")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        def on_cancel():
            dialog.destroy()
        
        # 按钮
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="确定", command=on_confirm, width=10).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="取消", command=on_cancel, width=10).pack(side=tk.LEFT, padx=10)
        
        # 绑定ESC键
        dialog.bind('<Escape>', lambda e: on_cancel())
        dialog.bind('<Return>', lambda e: on_confirm())
        
        # 等待对话框关闭
        dialog.wait_window()
        
        return result
    
    def _capture_and_select(self):
        """执行截图和区域选择"""
        try:
            print("开始执行截图选择...")
            
            # 检查依赖
            if not SCREENSHOT_AVAILABLE:
                raise ImportError("截图依赖库不可用")
                
            # 截取全屏
            print("正在截取屏幕...")
            screenshot = pyautogui.screenshot()
            print(f"截图成功，尺寸: {screenshot.size}")
            
            # 创建选择窗口
            print("创建选择窗口...")
            selector_window = tk.Toplevel()
            selector_window.title("选择OCR识别区域")
            selector_window.configure(bg='black')
            
            # 获取屏幕尺寸
            screen_width = screenshot.width
            screen_height = screenshot.height
            print(f"屏幕尺寸: {screen_width}x{screen_height}")
            
            # 设置窗口为全屏
            selector_window.geometry(f"{screen_width}x{screen_height}+0+0")
            selector_window.overrideredirect(True)  # 无边框
            selector_window.attributes('-topmost', True)  # 置顶
            selector_window.attributes('-alpha', 0.95)  # 半透明
            
            # 转换截图格式
            print("转换截图格式...")
            photo = PIL.ImageTk.PhotoImage(screenshot)
            
            # 创建画布
            canvas = tk.Canvas(
                selector_window,
                width=screen_width,
                height=screen_height,
                highlightthickness=0,
                bg='black'
            )
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # 显示截图
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            
            # 选择状态
            self.start_x = None
            self.start_y = None
            self.rect_id = None
            self.selection_made = False
            
            def on_mouse_down(event):
                """鼠标按下开始选择"""
                print(f"鼠标按下: ({event.x}, {event.y})")
                self.start_x = event.x
                self.start_y = event.y
                self.selection_made = True
                
            def on_mouse_move(event):
                """鼠标移动更新选择框"""
                if self.start_x is not None and self.start_y is not None:
                    # 删除旧的选择框
                    if self.rect_id:
                        canvas.delete(self.rect_id)
                    
                    # 绘制新的选择框
                    self.rect_id = canvas.create_rectangle(
                        self.start_x, self.start_y, event.x, event.y,
                        outline='red', width=2, fill=''
                    )
                    
                    # 显示坐标信息
                    width = abs(event.x - self.start_x)
                    height = abs(event.y - self.start_y)
                    x1 = min(self.start_x, event.x)
                    y1 = min(self.start_y, event.y)
                    
                    # 删除旧的坐标文本
                    old_text = canvas.find_withtag("coords")
                    for item in old_text:
                        canvas.delete(item)
                    
                    # 显示新坐标
                    canvas.create_text(
                        x1, y1 - 10,
                        text=f"({x1}, {y1}) {width}x{height}",
                        fill='red', font=('Arial', 10, 'bold'),
                        tags="coords"
                    )
                    
            def on_mouse_up(event):
                """鼠标释放完成选择"""
                print(f"鼠标释放: ({event.x}, {event.y})")
                if self.start_x is not None and self.start_y is not None and self.selection_made:
                    # 计算最终坐标
                    x1 = min(self.start_x, event.x)
                    y1 = min(self.start_y, event.y)
                    x2 = max(self.start_x, event.x)
                    y2 = max(self.start_y, event.y)
                    
                    width = x2 - x1
                    height = y2 - y1
                    
                    print(f"选择区域: ({x1}, {y1}) {width}x{height}")
                    
                    # 确保选择区域有效
                    if width > 5 and height > 5:  # 最小选择区域
                        self.result = (x1, y1, width, height)
                        selector_window.destroy()
                    else:
                        # 选择区域太小，显示提示
                        canvas.create_text(
                            screen_width // 2, screen_height // 2,
                            text="选择区域太小，请重新选择",
                            fill='red', font=('Arial', 16, 'bold'),
                            tags="warning"
                        )
                        selector_window.after(1500, lambda: canvas.delete("warning"))
                        
                    self.start_x = None
                    self.start_y = None
                    self.selection_made = False
            
            def on_key_press(event):
                """键盘事件处理"""
                print(f"按键按下: {event.keysym}")
                if event.keysym == 'Escape':
                    # ESC键取消选择
                    self.result = None
                    selector_window.destroy()
                elif event.keysym == 'Return':
                    # Enter键确认选择（如果已选择）
                    if self.result:
                        selector_window.destroy()
            
            def on_right_click(event):
                """右键取消选择"""
                print("右键点击，取消选择")
                self.result = None
                selector_window.destroy()
            
            # 绑定事件
            canvas.bind("<Button-1>", on_mouse_down)
            canvas.bind("<B1-Motion>", on_mouse_move)
            canvas.bind("<ButtonRelease-1>", on_mouse_up)
            canvas.bind("<KeyPress>", on_key_press)
            canvas.bind("<Button-3>", on_right_click)
            
            # 设置焦点到画布
            canvas.focus_set()
            
            # 添加提示文字
            canvas.create_text(
                screen_width // 2, 50,
                text="按住鼠标左键拖拽选择区域，右键或ESC取消",
                fill='red', font=('Arial', 20, 'bold')
            )
            
            # 保持图片引用
            canvas.image = photo
            
            print("等待用户选择...")
            # 模态等待
            selector_window.wait_window()
            print(f"选择结果: {self.result}")
            
        except Exception as e:
            print(f"截图选择器错误: {e}")
            print(f"详细错误: {traceback.format_exc()}")
            self.result = None
            
        finally:
            # 确保窗口被销毁
            try:
                selector_window.destroy()
            except:
                pass


class SimpleScreenshotSelector:
    """简化版截图选择器，使用tkinter内置功能"""
    
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.result = None
        
    def select_area(self) -> Optional[Tuple[int, int, int, int]]:
        """简单的屏幕区域选择"""
        if self.parent_window:
            # 使用更激进的隐藏方法
            self.parent_window.withdraw()  # 隐藏窗口
            self.parent_window.attributes('-alpha', 0.0)  # 设置完全透明
            # 确保窗口不在任务栏显示
            self.parent_window.overrideredirect(True)
            
            # 增加等待时间，确保窗口完全隐藏
            time.sleep(0.5)
            # 额外等待一小段时间，确保系统完成所有UI更新
            self.parent_window.update_idletasks()
            # 强制刷新系统显示
            import ctypes
            ctypes.windll.user32.UpdateWindow(self.parent_window.winfo_id())
            
        # 创建简单的输入对话框
        dialog = tk.Toplevel()
        dialog.title("设置识别区域")
        dialog.geometry("400x300+100+100")
        dialog.attributes('-topmost', True)
        
        # 创建提示信息
        tk.Label(dialog, text="屏幕截图区域选择", font=('Arial', 14, 'bold')).pack(pady=10)
        
        info_text = """
使用说明：
1. 请手动最小化此窗口
2. 使用系统截图工具（如QQ截图、微信截图等）
3. 截图时记住起始和结束坐标
4. 返回此窗口输入坐标值

或者使用传统方式直接输入坐标值
        """
        
        tk.Label(dialog, text=info_text, justify=tk.LEFT, wraplength=350).pack(pady=10)
        
        # 坐标输入框
        input_frame = tk.Frame(dialog)
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text="X坐标:").grid(row=0, column=0, padx=5)
        x_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=x_var, width=10).grid(row=0, column=1, padx=5)
        
        tk.Label(input_frame, text="Y坐标:").grid(row=0, column=2, padx=5)
        y_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=y_var, width=10).grid(row=0, column=3, padx=5)
        
        tk.Label(input_frame, text="宽度:").grid(row=1, column=0, padx=5, pady=5)
        w_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=w_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(input_frame, text="高度:").grid(row=1, column=2, padx=5, pady=5)
        h_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=h_var, width=10).grid(row=1, column=3, padx=5, pady=5)
        
        def on_confirm():
            try:
                x = int(x_var.get())
                y = int(y_var.get())
                w = int(w_var.get())
                h = int(h_var.get())
                
                if w > 0 and h > 0:
                    self.result = (x, y, w, h)
                    dialog.destroy()
                else:
                    tk.messagebox.showerror("错误", "宽度和高度必须大于0")
            except ValueError:
                tk.messagebox.showerror("错误", "请输入有效的数字")
        
        def on_cancel():
            self.result = None
            dialog.destroy()
        
        # 按钮
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="确定", command=on_confirm, width=10).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="取消", command=on_cancel, width=10).pack(side=tk.LEFT, padx=10)
        
        # 绑定ESC键
        dialog.bind('<Escape>', lambda e: on_cancel())
        dialog.bind('<Return>', lambda e: on_confirm())
        
        # 等待对话框关闭
        dialog.wait_window()
        
        if self.parent_window:
            # 添加短暂延迟，确保对话框完全关闭
            time.sleep(0.1)
            # 恢复窗口状态
            self.parent_window.overrideredirect(False)  # 恢复窗口边框
            self.parent_window.attributes('-alpha', 1.0)  # 恢复透明度
            self.parent_window.deiconify()
            # 确保窗口置顶显示
            self.parent_window.attributes('-topmost', True)
            self.parent_window.after(100, lambda: self.parent_window.attributes('-topmost', False))
            
        return self.result