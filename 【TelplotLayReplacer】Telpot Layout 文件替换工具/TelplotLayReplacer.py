import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os


class LayGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TecplotLayReplacer")
        self.root.geometry("1100x650")
        self.root.configure(bg='#f5f6fa')
        
        self.colors = {
            'bg': '#f5f6fa',
            'card': '#ffffff',
            'primary': '#4CAF50',
            'primary_hover': '#43a047',
            'text': '#2c3e50',
            'text_secondary': '#7f8c8d',
            'border': '#e1e8ed'
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        # 顶部标题
        header = tk.Frame(self.root, bg=self.colors['bg'], padx=20, pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="TecplotLayReplacer", font=('Segoe UI', 18, 'bold'), 
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w')
        tk.Label(header, text="批量替换.lay文件中的数据路径", font=('Segoe UI', 10), 
                bg=self.colors['bg'], fg=self.colors['text_secondary']).pack(anchor='w')
        
        # 主区域 - 左右分栏
        main = tk.Frame(self.root, bg=self.colors['bg'], padx=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # 左侧面板
        left_panel = tk.Frame(main, bg=self.colors['bg'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 文件配置（紧凑）
        file_card = tk.Frame(left_panel, bg=self.colors['card'], padx=15, pady=12,
                            highlightbackground=self.colors['border'], highlightthickness=1)
        file_card.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(file_card, text="📁 文件配置", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(anchor='w', pady=(0, 10))
        
        # 模板文件行
        f1 = tk.Frame(file_card, bg=self.colors['card'])
        f1.pack(fill=tk.X, pady=2)
        tk.Label(f1, text="模板:", bg=self.colors['card'], width=6, anchor='w').pack(side=tk.LEFT)
        self.template_var = tk.StringVar()
        tk.Entry(f1, textvariable=self.template_var, relief='solid', bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(f1, text="浏览", command=self.browse_template, relief='solid', bd=1, cursor='hand2').pack(side=tk.RIGHT)
        
        # 输出行
        f2 = tk.Frame(file_card, bg=self.colors['card'])
        f2.pack(fill=tk.X, pady=2)
        tk.Label(f2, text="输出:", bg=self.colors['card'], width=6, anchor='w').pack(side=tk.LEFT)
        self.output_var = tk.StringVar()
        tk.Entry(f2, textvariable=self.output_var, relief='solid', bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(f2, text="浏览", command=self.browse_output, relief='solid', bd=1, cursor='hand2').pack(side=tk.RIGHT)
        
        # 替换规则（左侧窄右侧宽）
        rule_card = tk.Frame(left_panel, bg=self.colors['card'], padx=15, pady=12,
                            highlightbackground=self.colors['border'], highlightthickness=1)
        rule_card.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(rule_card, text="📝 替换规则", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(anchor='w', pady=(0, 10))
        
        # 替换内容左右分栏（1:3比例）
        content_frame = tk.Frame(rule_card, bg=self.colors['card'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：原文件名（窄，固定180px）
        left_frame = tk.Frame(content_frame, bg=self.colors['card'], width=180)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)  # 固定宽度不随内容变化
        
        tk.Label(left_frame, text="原文件名", bg=self.colors['card'], 
                fg=self.colors['text_secondary'], font=('Segoe UI', 9)).pack(anchor='w')
        self.old_text = tk.Text(left_frame, wrap=tk.WORD, font=('Consolas', 9),
                               relief='solid', bd=1, bg='#fafafa', height=8)
        self.old_text.pack(fill=tk.BOTH, expand=True, pady=2)
        self.old_text.insert("1.0", "A0.cas.gz\nA0.dat.gz\ndefault.xml")
        
        # 右侧：映射表（宽，自适应）
        right_frame = tk.Frame(content_frame, bg=self.colors['card'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        right_header = tk.Frame(right_frame, bg=self.colors['card'])
        right_header.pack(fill=tk.X)
        tk.Label(right_header, text="映射表", bg=self.colors['card'],
                fg=self.colors['text_secondary'], font=('Segoe UI', 9)).pack(side=tk.LEFT)
        tk.Label(right_header, text="格式: 基础名,新文件1,新文件2...", bg=self.colors['card'],
                fg='#bbb', font=('Segoe UI', 9)).pack(side=tk.RIGHT)
        
        self.map_text = tk.Text(right_frame, wrap=tk.WORD, font=('Consolas', 9),
                               relief='solid', bd=1, bg='#fafafa', height=8)
        self.map_text.pack(fill=tk.BOTH, expand=True, pady=2)
        self.map_text.insert("1.0", "A1,A1.cas.gz,A1.dat.gz,A1.xml\nA2,A2.cas.gz,A2.dat.gz,A2.xml")
        
        # 右侧面板：日志区域（与左侧文件配置同行）
        right_panel = tk.Frame(main, bg=self.colors['card'], padx=15, pady=12,
                              highlightbackground=self.colors['border'], highlightthickness=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        log_header = tk.Frame(right_panel, bg=self.colors['card'])
        log_header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(log_header, text="📋 执行日志", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        self.status_label = tk.Label(log_header, text="就绪", font=('Segoe UI', 9),
                                    bg=self.colors['card'], fg=self.colors['text_secondary'])
        self.status_label.pack(side=tk.RIGHT)
        
        self.log_text = scrolledtext.ScrolledText(right_panel, wrap=tk.WORD, font=('Consolas', 9),
                                                  relief='flat', bg='#fafafa', state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部按钮
        btn_frame = tk.Frame(self.root, bg=self.colors['bg'], pady=15)
        btn_frame.pack(fill=tk.X)
        
        self.generate_btn = tk.Button(btn_frame, text="🚀 开始生成", command=self.generate,
                                     bg=self.colors['primary'], fg='white',
                                     font=('Segoe UI', 11, 'bold'), relief='flat',
                                     padx=30, pady=8, cursor='hand2')
        self.generate_btn.pack()
        
        self.generate_btn.bind('<Enter>', lambda e: self.generate_btn.config(bg=self.colors['primary_hover']))
        self.generate_btn.bind('<Leave>', lambda e: self.generate_btn.config(bg=self.colors['primary']))
        
        self.log("就绪。请选择模板文件并配置映射规则。")
        
    def browse_template(self):
        filename = filedialog.askopenfilename(filetypes=[("LAY files", "*.lay"), ("All files", "*.*")])
        if filename:
            self.template_var.set(filename)
            if not self.output_var.get():
                self.output_var.set(os.path.dirname(filename))
            self.log(f"已选择模板: {os.path.basename(filename)}")
    
    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_var.set(folder)
            self.log(f"输出目录: {folder}")
    
    def log(self, msg):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"> {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
    
    def generate(self):
        template_path = self.template_var.get().strip()
        output_dir = self.output_var.get().strip()
        
        if not template_path or not os.path.exists(template_path):
            messagebox.showerror("错误", "请选择有效的模板文件")
            return
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return
        
        old_strings = [s.strip() for s in self.old_text.get("1.0", tk.END).strip().split("\n") if s.strip()]
        if not old_strings:
            messagebox.showerror("错误", "请输入原文件名")
            return
        
        maps = []
        lines = self.map_text.get("1.0", tk.END).strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                maps.append((parts[0], parts[1:]))
        
        if not maps:
            messagebox.showerror("错误", "映射表为空")
            return
        
        for base_name, new_files in maps:
            if len(new_files) != len(old_strings):
                messagebox.showerror("错误", f"{base_name}: 数量不匹配")
                return
        
        try:
            with open(template_path, 'r', encoding='utf-8', errors='ignore') as f:
                template = f.read()
        except Exception as e:
            messagebox.showerror("错误", f"读取模板失败: {e}")
            return
        
        self.status_label.config(text="生成中...", fg=self.colors['primary'])
        self.generate_btn.config(state='disabled', text='生成中...')
        self.root.update()
        
        success = 0
        for base_name, new_files in maps:
            try:
                content = template
                for old, new in zip(old_strings, new_files):
                    content = content.replace(old, new)
                output_path = os.path.join(output_dir, f"{base_name}.lay")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"✓ {base_name}.lay")
                success += 1
            except Exception as e:
                self.log(f"✗ {base_name}: {str(e)}")
        
        self.status_label.config(text=f"完成 {success}/{len(maps)}", fg=self.colors['text_secondary'])
        self.generate_btn.config(state='normal', text='🚀 开始生成')
        
        if success == len(maps):
            messagebox.showinfo("完成", f"成功生成 {success} 个文件")


if __name__ == "__main__":
    root = tk.Tk()
    app = LayGeneratorGUI(root)
    root.mainloop()
