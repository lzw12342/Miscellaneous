#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import threading
import time
import logging
from pathlib import Path
import os  # 新增：用于获取程序路径

from core import (AutoConnectMachine, ConfigManager, UserConfig, 
                 SettingConfig, set_logger, SystemUtils)

# 新增托盘相关
import pystray
from PIL import Image, ImageDraw

class AutoConnectGUI:
    """校园网自动连接工具GUI（完整版）"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("校园网自动连接工具 v3.0")
        self.root.geometry("680x720")
        self.root.resizable(False, False)
        
        # 创建并设置 logger
        self.logger = logging.getLogger("campus_wifi")
        self.logger.setLevel(logging.DEBUG)
        
        # 关键修复：使用程序所在目录作为日志路径
        # 获取当前脚本所在目录的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, 'auto_connect.log')
        
        # 文件处理器 - 使用绝对路径
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        
        self.logger.info("="*50)
        self.logger.info("程序启动 - 日志系统初始化成功")
        self.logger.info(f"日志文件路径: {log_path}")
        self.logger.info("="*50)
        
        # UI 处理器
        self.ui_handler = self._create_ui_handler()
        self.logger.addHandler(self.ui_handler)
        
        # 将 logger 传递给 core
        set_logger(self.logger)
        
        # 核心组件
        self.app = None
        self.config_manager = ConfigManager()
        self.is_running = False
        self.monitor_thread = None
        
        # 系统工具（提前定义）
        self.system_utils = SystemUtils()
        self.autostart_var = tk.BooleanVar(value=False)
        
        # 配置变量
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.provider_var = tk.StringVar(value="telecom")
        self.show_password_var = tk.BooleanVar(value=False)
        self.remember_var = tk.BooleanVar(value=False)
        self.interval_var = tk.StringVar(value="30")
        self.host_var = tk.StringVar(value="www.qq.com")
        self.minimize_to_tray_var = tk.BooleanVar(value=True)
        
        # 系统托盘图标
        self.tray_icon = None
        self.tray_thread = None
        
        # 现在可以安全调用这些方法了
        self._setup_ui()
        self._setup_tray_icon()
        
        # 绑定窗口事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind("<Unmap>", self._on_window_minimize)
        
        # 加载配置
        self._load_existing_config()
        
    def _create_ui_handler(self):
        """创建UI日志处理器"""
        class UIHandler(logging.Handler):
            def __init__(self, gui_instance):
                super().__init__()
                self.gui = gui_instance
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    level = record.levelname
                    self.gui.root.after(0, self.gui._log_message, level, msg)
                except:
                    pass
        
        handler = UIHandler(self)
        handler.setFormatter(logging.Formatter('%(message)s'))
        return handler
        
    def _setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title = ttk.Label(main_frame, text="校园网自动连接工具", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="连接状态", padding="8")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_icon = ttk.Label(status_frame, text="●", font=("Segoe UI", 20))
        self.status_icon.grid(row=0, column=0, rowspan=2, padx=10)
        
        self.status_label = ttk.Label(status_frame, text="未启动", font=("Segoe UI", 12))
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        self.status_detail = ttk.Label(status_frame, text="", foreground="gray")
        self.status_detail.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # 配置区域容器 - 两栏布局
        config_container = ttk.Frame(main_frame)
        config_container.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 用户配置（左栏）
        user_config_frame = ttk.LabelFrame(config_container, text="用户配置", padding="10")
        user_config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5))
        
        # 用户名
        ttk.Label(user_config_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.username_entry = ttk.Entry(user_config_frame, textvariable=self.username_var, 
                                       width=28, font=("Consolas", 10))
        self.username_entry.grid(row=0, column=1, sticky=tk.W, pady=6, padx=(8, 0))
        
        # 密码（带显示/隐藏）
        ttk.Label(user_config_frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=6)
        
        password_frame = ttk.Frame(user_config_frame)
        password_frame.grid(row=1, column=1, sticky=tk.W, pady=6, padx=(8, 0))
        
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password_var, 
                                       show="*", width=18, font=("Consolas", 10))
        self.password_entry.pack(side=tk.LEFT, padx=(0, 4))
        
        self.show_password_cb = ttk.Checkbutton(
            password_frame, 
            text="显示", 
            variable=self.show_password_var,
            command=self._toggle_password_visibility
        )
        self.show_password_cb.pack(side=tk.LEFT)
        
        # 运营商
        ttk.Label(user_config_frame, text="运营商:").grid(row=2, column=0, sticky=tk.W, pady=6)
        
        provider_frame = ttk.Frame(user_config_frame)
        provider_frame.grid(row=2, column=1, sticky=tk.W, padx=(8, 0))
        
        providers = {
            "telecom": "电信",
            "cmcc": "移动",
            "unicom": "联通"
        }
        
        for idx, (value, name) in enumerate(providers.items()):
            rb = ttk.Radiobutton(provider_frame, text=name, variable=self.provider_var, value=value)
            rb.pack(side=tk.LEFT, padx=(0, 8) if idx < len(providers)-1 else 0)
        
        # 记住配置
        self.remember_cb = ttk.Checkbutton(user_config_frame, text="记住用户配置", 
                                          variable=self.remember_var)
        self.remember_cb.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        
        # 高级设置（右栏）
        setting_frame = ttk.LabelFrame(config_container, text="高级设置", padding="10")
        setting_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), padx=(5, 0))
        
        # 检查间隔
        ttk.Label(setting_frame, text="检查间隔:").grid(row=0, column=0, sticky=tk.W, pady=6)
        
        interval_frame = ttk.Frame(setting_frame)
        interval_frame.grid(row=0, column=1, sticky=tk.W, pady=6, padx=(8, 0))
        
        self.interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, 
                                       width=8, font=("Consolas", 10))
        self.interval_entry.pack(side=tk.LEFT, padx=(0, 4))
        
        ttk.Label(interval_frame, text="秒", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        # 检测主机
        ttk.Label(setting_frame, text="检测主机:").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.host_entry = ttk.Entry(setting_frame, textvariable=self.host_var, 
                                   width=28, font=("Consolas", 10))
        self.host_entry.grid(row=1, column=1, sticky=tk.W, pady=6, padx=(8, 0))
        
        # 新增：最小化到托盘选项
        minimize_frame = ttk.Frame(config_container)
        minimize_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        
        self.minimize_to_tray_cb = ttk.Checkbutton(
            minimize_frame, 
            text="最小化窗口时隐藏到系统托盘", 
            variable=self.minimize_to_tray_var
        )
        self.minimize_to_tray_cb.grid(row=0, column=0, sticky=tk.W)

        # 开机自启动选项
        autostart_frame = ttk.Frame(config_container)
        autostart_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

        self.autostart_cb = ttk.Checkbutton(
            autostart_frame,
            text="开机自动启动", 
            variable=self.autostart_var,
            command=self._on_autostart_toggle
        )
        self.autostart_cb.pack(side=tk.LEFT)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            width=70, 
            height=12,
            state='disabled', 
            font=("Consolas", 9),
            foreground="#00FF00",
            background="#000000"
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(0, 5))
        
        self.start_button = ttk.Button(button_frame, text="启动监控", 
                                      command=self._start_monitoring, width=11)
        self.start_button.pack(side=tk.LEFT, padx=4)
        
        self.stop_button = ttk.Button(button_frame, text="停止监控", 
                                     command=self._stop_monitoring, width=11, 
                                     state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=4)
        
        self.save_button = ttk.Button(button_frame, text="保存配置", 
                                     command=self._save_config, width=11)
        self.save_button.pack(side=tk.LEFT, padx=4)
        
        self.exit_button = ttk.Button(button_frame, text="退出", 
                                     command=self._exit, width=11)
        self.exit_button.pack(side=tk.LEFT, padx=4)
        
        # 配置列权重
        self.root.columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        config_container.columnconfigure(0, weight=1)
        config_container.columnconfigure(1, weight=1)
        
    def _setup_tray_icon(self):
        """创建系统托盘图标"""
        # 生成一个简单的图标
        image = Image.new('RGB', (32, 32), color='#2c3e50')
        draw = ImageDraw.Draw(image)
        draw.rectangle([8, 8, 24, 24], fill='#27ae60', outline='#ffffff', width=2)
        
        # 创建托盘菜单
        menu = pystray.Menu(
            pystray.MenuItem("显示主窗口", self._show_window),
            pystray.MenuItem("退出程序", self._exit_from_tray)
        )
        
        self.tray_icon = pystray.Icon(
            "campus_wifi", 
            image, 
            "校园网自动连接工具", 
            menu
        )
        
        # 启动托盘图标在后台线程
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()
        # 初始时隐藏托盘图标
        self.tray_icon.visible = False
        
    def _toggle_password_visibility(self):
        """切换密码显示/隐藏"""
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
        
    def _load_existing_config(self):
        """加载已存在的配置"""
        user_config, setting_config, missing = self.config_manager.load()
        
        if user_config:
            self.username_var.set(user_config.username)
            self.password_var.set(user_config.password)
            self.provider_var.set(user_config.provider)
            self.remember_var.set(True)
        else:
            self._log_message("INFO", "未找到用户配置")
        
        if setting_config:
            self.interval_var.set(str(setting_config.interval))
            self.host_var.set(setting_config.host)
            self.autostart_var.set(setting_config.autostart)  # 从配置加载
        else:
            self._log_message("INFO", "未找到高级设置配置，使用默认值")
        
        # 加载当前自启动状态
        current_autostart = self.system_utils.is_autostart_enabled()
        self.autostart_var.set(current_autostart)
        
        # 更新状态
        if user_config and not missing[self.config_manager.USER_SECTION]:
            self._update_status("就绪", "配置已加载，点击启动开始连接")
        else:
            self._update_status("未配置", "请填写配置信息")
        
    def _update_status(self, main_status: str, detail: str = ""):
        """更新状态显示"""
        color_map = {
            "未启动": "gray",
            "就绪": "#FFA500",
            "运行中": "#00FF00",
            "已停止": "gray",
            "错误": "#FF0000"
        }
        
        icon = "●"
        color = color_map.get(main_status, "gray")
        
        self.status_icon.config(text=icon, foreground=color)
        self.status_label.config(text=main_status, foreground=color)
        self.status_detail.config(text=detail)
        
    def _log_message(self, level: str, message: str):
        """向日志框添加消息"""
        try:
            self.log_text.config(state='normal')
            timestamp = time.strftime('%H:%M:%S')
            
            # 限制日志长度
            max_lines = 500
            current_lines = int(self.log_text.index('end-1c').split('.')[0])
            
            if current_lines > max_lines:
                self.log_text.delete('1.0', f'{current_lines - max_lines}.0')
            
            # 设置颜色
            color_map = {
                "DEBUG": "#808080",
                "INFO": "#00FF00",
                "WARNING": "#FFA500",
                "ERROR": "#FF0000"
            }
            color = color_map.get(level, "#FFFFFF")
            
            tag_name = f"tag_{color}"
            self.log_text.insert(tk.END, f"{timestamp} [{level}] ", ("timestamp",))
            self.log_text.insert(tk.END, f"{message}\n", tag_name)
            
            self.log_text.tag_config("timestamp", foreground="#808080")
            self.log_text.tag_config(tag_name, foreground=color)
            
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        except:
            pass
        
    def _validate_inputs(self) -> bool:
        """验证输入有效性"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        interval = self.interval_var.get().strip()
        host = self.host_var.get().strip()
        
        if not username:
            messagebox.showerror("错误", "请输入用户名！")
            self.username_entry.focus()
            return False
        
        if not password:
            messagebox.showerror("错误", "请输入密码！")
            self.password_entry.focus()
            return False
        
        if not interval.isdigit() or not (5 <= int(interval) <= 3600):
            messagebox.showerror("错误", "检查间隔必须是5-3600之间的整数！")
            self.interval_entry.focus()
            return False
        
        if not host:
            messagebox.showerror("错误", "请输入检测主机！")
            self.host_entry.focus()
            return False
        
        return True
        
    def _save_config(self):
        """保存配置到文件"""
        if not self._validate_inputs():
            return
        
        user_config = UserConfig(
            username=self.username_var.get().strip(),
            password=self.password_var.get(),
            provider=self.provider_var.get()
        )
        
        setting_config = SettingConfig(
            interval=int(self.interval_var.get()),
            host=self.host_var.get().strip(),
            wifi_ssid="JXUST-WLAN",
            autostart=self.autostart_var.get()
        )
        
        success = self.config_manager.save(user_config, setting_config)
        if success:
            messagebox.showinfo("成功", "配置保存成功！")
            self.remember_var.set(True)
        else:
            messagebox.showerror("错误", "配置保存失败！")
            
    def _start_monitoring(self):
        """启动监控"""
        if self.is_running:
            messagebox.showwarning("警告", "监控已经在运行中！")
            return
        
        if not self._validate_inputs():
            return
        
        # 更新UI状态
        self.is_running = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.save_button.config(state='disabled')
        self._set_inputs_state('disabled')
        self._update_status("运行中", "正在监控网络状态...")
        
        # 启动后台线程
        def run_app():
            try:
                user_config = UserConfig(
                    username=self.username_var.get().strip(),
                    password=self.password_var.get(),
                    provider=self.provider_var.get()
                )
                
                setting_config = SettingConfig(
                    interval=int(self.interval_var.get()),
                    host=self.host_var.get().strip(),
                    wifi_ssid="JXUST-WLAN"
                )
                
                self.app = AutoConnectMachine(user_config, setting_config)
                self.app.run()
                
            except Exception as e:
                self.logger.error(f"应用运行异常: {e}", exc_info=True)
                if hasattr(self, 'root'):
                    self.root.after(0, lambda: messagebox.showerror("错误", 
                                                                f"应用运行失败: {e}"))
            finally:
                # 确保UI状态恢复
                if hasattr(self, 'root'):
                    self.root.after(0, self._stop_monitoring)
        
        self.monitor_thread = threading.Thread(target=run_app, daemon=True)
        self.monitor_thread.start()
        
    def _stop_monitoring(self):
        """停止监控"""
        if not self.is_running:
            return
        
        self._log_message("INFO", "用户请求停止监控...")
        
        # 停止应用
        if self.app:
            self.app.stop()
        
        # 恢复UI状态
        self.is_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.save_button.config(state='normal')
        self._set_inputs_state('normal')
        self._update_status("已停止", "监控已停止")
        self._log_message("INFO", "监控已完全停止")
        
    def _set_inputs_state(self, state: str):
        """设置输入区域状态"""
        try:
            self.username_entry.config(state=state)
            self.password_entry.config(state=state)
            self.show_password_cb.config(state=state)
            
            # 设置单选按钮状态
            for rb in self._get_radio_buttons():
                rb.config(state=state)
                
            self.remember_cb.config(state=state)
            self.interval_entry.config(state=state)
            self.host_entry.config(state=state)
            self.autostart_cb.config(state=state)
            
            # 托盘勾选框状态
            if state == 'disabled' and self.is_running:
                self.minimize_to_tray_cb.config(state='disabled')
            else:
                self.minimize_to_tray_cb.config(state='normal')
        except:
            pass
    
    def _get_radio_buttons(self):
        """获取所有单选按钮"""
        radio_buttons = []
        for child in self.root.winfo_children():
            self._find_radio_buttons(child, radio_buttons)
        return radio_buttons
    
    def _find_radio_buttons(self, widget, radio_buttons):
        """递归查找单选按钮"""
        for child in widget.winfo_children():
            if isinstance(child, ttk.Radiobutton):
                radio_buttons.append(child)
            self._find_radio_buttons(child, radio_buttons)
    
    def _on_window_minimize(self, event):
        """窗口最小化时隐藏到托盘"""
        if event.widget == self.root and self.minimize_to_tray_var.get():
            self.logger.debug("检测到窗口最小化事件")
            self.root.after(100, self._hide_window_to_tray)
    
    def _hide_window_to_tray(self):
        """实际执行隐藏到托盘的操作"""
        try:
            self.root.withdraw()
            if self.tray_icon:
                self.tray_icon.visible = True
                self.logger.info("窗口已最小化到托盘")
        except Exception as e:
            self.logger.error(f"最小化到托盘失败: {e}")
        
    def _show_window(self):
        """从托盘恢复窗口"""
        try:
            if self.tray_icon:
                self.tray_icon.visible = False
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.logger.info("窗口已从托盘恢复")
        except Exception as e:
            self.logger.error(f"从托盘恢复窗口失败: {e}")
    
    def _exit_from_tray(self):
        """从托盘退出程序"""
        if self.is_running:
            self._stop_monitoring()
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self._exit()
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.is_running:
            if not messagebox.askyesno("确认退出", "监控正在运行，确定要退出吗？"):
                return
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self._exit()
    
    def _exit(self):
        """退出程序"""
        if self.tray_icon:
            self.tray_icon.stop()
        
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        sys.exit(0)

    def _on_autostart_toggle(self):
        """处理开机自启动开关"""
        enable = self.autostart_var.get()
        
        # 检查权限
        if enable and not SystemUtils.is_admin():
            success = self.system_utils.set_autostart(enable)
            if not success:
                if messagebox.askyesno("需要管理员权限", 
                                     "设置开机自启动需要管理员权限。\n\n"
                                     "是否以管理员身份重新启动程序？"):
                    self.system_utils.run_as_admin()
                    self._exit()
                else:
                    self.autostart_var.set(False)
                    return
        else:
            success = self.system_utils.set_autostart(enable)
            if not success:
                messagebox.showerror("设置失败", "无法设置开机自启动，请检查权限")
                self.autostart_var.set(not enable)

def main():
    """GUI入口函数"""
    root = tk.Tk()
    app = AutoConnectGUI(root)
    
    # 窗口居中显示
    root.update_idletasks()
    width = 680
    height = 650
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    if "--minimized" in sys.argv:
        root.withdraw()
    
    root.mainloop()

if __name__ == '__main__':
    main()