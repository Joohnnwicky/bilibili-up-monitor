#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站数据监控看板 - 赛博朋克2077风格
作者: AI Assistant
功能: 实时显示B站粉丝数、评论回复，每分钟自动刷新
风格: Cyberpunk 2077 - 霓虹黄 + 青蓝色 + 黑色科技风
新增: 字号调节器、蜂鸣提醒
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import requests
import json
import threading
import time
import os
import webbrowser
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import io

# ============== 配置 ==============
UID = "662899682"  # 你的B站UID
REFRESH_INTERVAL = 60  # 数据刷新间隔（秒）
MSG_REFRESH_INTERVAL = 120  # 消息刷新间隔（秒）
TITLE = "前线观察大队"  # 面板标题
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bilibili_data.json")
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bilibili_cookie.txt")

# 请求头（模拟浏览器）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://space.bilibili.com/{UID}",
}

# ============== 赛博朋克2077配色方案 ==============
CYBER_COLORS = {
    "bg_main": "#0a0a0f",
    "bg_secondary": "#12121a",
    "bg_card": "#1a1a24",
    "neon_yellow": "#ffff00",
    "neon_yellow_dim": "#cccc00",
    "neon_cyan": "#00ffff",
    "neon_pink": "#ff00ff",
    "neon_green": "#00ff41",
    "neon_red": "#ff0040",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b0",
    "border_glow": "#ffff00",
    "grid_line": "#2a2a3a",
}

# ============== API 地址 ==============
API_FAN = f"https://api.bilibili.com/x/relation/stat?vmid={UID}"
API_STAT = f"https://api.bilibili.com/x/space/upstat?mid={UID}"
API_INFO = f"https://api.bilibili.com/x/space/acc/info?mid={UID}"
API_REPLY = "https://api.bilibili.com/x/msgfeed/reply"


def beep(count=1, frequency=800, duration=150):
    """蜂鸣提醒"""
    try:
        import winsound
        for i in range(count):
            winsound.Beep(frequency, duration)
            if i < count - 1:
                time.sleep(0.1)
    except Exception:
        # 如果 winsound 不可用，尝试其他方式
        pass


class BilibiliDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{TITLE} // CYBERPUNK")
        self.root.geometry("800x750")
        self.root.resizable(True, True)
        self.root.minsize(700, 500)

        # 窗口置顶
        self.root.attributes('-topmost', True)

        # 设置背景色
        self.root.configure(bg=CYBER_COLORS["bg_main"])

        # 字号设置（基准值已放大，150%为基准的50%）
        self.font_scale = 1.0
        self.base_sizes = {
            'title': 21,      # 原14 * 1.5
            'subtitle': 12,   # 原8 * 1.5
            'name': 15,       # 原10 * 1.5
            'follower_title': 18,  # 原12 * 1.5
            'follower_value': 42,  # 原28 * 1.5
            'follower_change': 15, # 原10 * 1.5
            'btn': 14,        # 原9 * 1.5
            'status': 14,     # 原9 * 1.5
            'msg_title': 17,  # 原11 * 1.5
            'msg_type': 14,   # 原9 * 1.5
            'msg_name': 15,   # 原10 * 1.5
            'msg_time': 14,   # 原9 * 1.5
            'msg_content': 14, # 原9 * 1.5
            'slider_label': 12, # 原8 * 1.5
        }

        # 存储需要动态调整字号的组件
        self.font_widgets = []

        # 数据存储
        self.data = {
            'follower': 0,
            'following': 0,
            'name': TITLE,
            'face_url': ''
        }

        # 消息数据
        self.messages = []
        self.prev_msg_ids = set()  # 用于检测新消息
        self.cookie = self.load_cookie()

        # 从文件加载上次的数据
        self.baseline_data = self.load_data()
        self.prev_data = self.baseline_data.copy() if self.baseline_data else {}

        # 首次加载标记（首次不加蜂鸣）
        self.first_data_load = True
        self.first_msg_load = True

        # 创建UI
        self.create_ui()

        # 首次加载数据
        self.refresh_data()
        self.refresh_messages()

        # 启动自动刷新定时器
        self.schedule_refresh()
        self.schedule_msg_refresh()

    def get_font_size(self, key):
        """获取当前字号"""
        base = self.base_sizes.get(key, 10)
        return int(base * self.font_scale)

    def update_all_fonts(self):
        """更新所有组件的字号"""
        for widget, key in self.font_widgets:
            try:
                new_size = self.get_font_size(key)
                current_font = widget.cget('font')
                if isinstance(current_font, tuple):
                    new_font = (current_font[0], new_size, current_font[2] if len(current_font) > 2 else None)
                else:
                    # 字体字符串格式 "Consolas 9 bold"
                    parts = current_font.split()
                    if len(parts) >= 2:
                        new_font = f"{parts[0]} {new_size} {' '.join(parts[2:])}"
                    else:
                        new_font = f"{parts[0]} {new_size}"
                widget.config(font=new_font)
            except Exception:
                pass

        # 更新消息卡片字号
        self.refresh_msg_cards_font()

    def refresh_msg_cards_font(self):
        """刷新消息卡片的字号"""
        # 重新创建消息卡片以应用新字号
        if hasattr(self, 'messages') and self.messages:
            self.update_msg_list(self.messages)

    def register_font_widget(self, widget, key):
        """注册需要动态调整字号的组件"""
        self.font_widgets.append((widget, key))

    def create_ui(self):
        """创建赛博朋克风格界面 - 上下布局"""
        # 主框架 - 上下分割（上：数据面板，下：消息面板）
        main_paned = tk.PanedWindow(
            self.root,
            orient=tk.VERTICAL,
            bg=CYBER_COLORS["bg_main"],
            sashwidth=4,
            sashrelief=tk.FLAT
        )
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ====== 上侧：数据面板 ======
        top_frame = tk.Frame(main_paned, bg=CYBER_COLORS["bg_main"])
        main_paned.add(top_frame, minsize=200, height=260)

        # 上侧内容框架
        top_content = tk.Frame(top_frame, bg=CYBER_COLORS["bg_main"], padx=15, pady=10)
        top_content.pack(fill=tk.BOTH, expand=True)

        # ===== 标题区域 =====
        header_row = tk.Frame(top_content, bg=CYBER_COLORS["bg_main"])
        header_row.pack(fill=tk.X, pady=(0, 8))

        # 左侧：标题
        title_frame = tk.Frame(header_row, bg=CYBER_COLORS["bg_main"])
        title_frame.pack(side=tk.LEFT)

        # 装饰线条
        deco_line = tk.Frame(title_frame, bg=CYBER_COLORS["neon_yellow"], height=2, width=120)
        deco_line.pack(fill=tk.X)

        # 标题文字
        title_label = tk.Label(
            title_frame,
            text=TITLE.upper(),
            font=("Consolas", self.get_font_size('title'), "bold"),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["neon_yellow"]
        )
        title_label.pack(anchor="w")
        self.register_font_widget(title_label, 'title')

        # 副标题
        subtitle_label = tk.Label(
            title_frame,
            text="CYBERPUNK 2077",
            font=("Consolas", self.get_font_size('subtitle')),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["neon_cyan"]
        )
        subtitle_label.pack(anchor="w")
        self.register_font_widget(subtitle_label, 'subtitle')

        # ===== 右侧：字号调节器 =====
        font_control_frame = tk.Frame(header_row, bg=CYBER_COLORS["bg_secondary"], padx=8, pady=4)
        font_control_frame.pack(side=tk.RIGHT, padx=(10, 0))

        # 调节器标签
        slider_label = tk.Label(
            font_control_frame,
            text="FONT",
            font=("Consolas", self.get_font_size('slider_label'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_cyan"]
        )
        slider_label.pack(side=tk.LEFT)
        self.register_font_widget(slider_label, 'slider_label')

        # 字号滑块
        self.font_slider = tk.Scale(
            font_control_frame,
            from_=0.5,
            to=1.5,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            length=80,
            width=14,
            sliderlength=18,
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"],
            troughcolor=CYBER_COLORS["bg_main"],
            highlightthickness=0,
            bd=0,
            showvalue=False,
            command=self.on_font_scale_change
        )
        self.font_slider.set(1.0)
        self.font_slider.pack(side=tk.LEFT, padx=5)

        # 字号显示
        self.font_value_label = tk.Label(
            font_control_frame,
            text="100%",
            font=("Consolas", self.get_font_size('slider_label')),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"],
            width=4
        )
        self.font_value_label.pack(side=tk.LEFT)
        self.register_font_widget(self.font_value_label, 'slider_label')

        # 头像（放在字号调节器左边）
        avatar_frame = tk.Frame(header_row, bg=CYBER_COLORS["neon_yellow"], padx=2, pady=2)
        avatar_frame.pack(side=tk.RIGHT, padx=5)

        self.avatar_label = tk.Label(avatar_frame, bg=CYBER_COLORS["bg_secondary"])
        self.avatar_label.pack()

        # 用户名
        self.name_label = tk.Label(
            top_content,
            text=">> 系统初始化中...",
            font=("Consolas", self.get_font_size('name')),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["neon_cyan"]
        )
        self.name_label.pack(pady=(2, 5))
        self.register_font_widget(self.name_label, 'name')

        # ===== 粉丝数大卡片 =====
        follower_outer_frame = tk.Frame(
            top_content,
            bg=CYBER_COLORS["neon_yellow"],
            padx=2,
            pady=2
        )
        follower_outer_frame.pack(fill=tk.X, pady=8)

        # 内部卡片
        follower_inner_frame = tk.Frame(
            follower_outer_frame,
            bg=CYBER_COLORS["bg_secondary"],
            padx=15,
            pady=10
        )
        follower_inner_frame.pack(fill=tk.X)

        # 卡片行布局
        follower_row = tk.Frame(follower_inner_frame, bg=CYBER_COLORS["bg_secondary"])
        follower_row.pack(fill=tk.X)

        # 标题
        follower_title = tk.Label(
            follower_row,
            text="[FOLLOWERS]",
            font=("Consolas", self.get_font_size('follower_title'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"]
        )
        follower_title.pack(side=tk.LEFT)
        self.register_font_widget(follower_title, 'follower_title')

        # 粉丝数大数字
        self.follower_value_label = tk.Label(
            follower_row,
            text="0",
            font=("Consolas", self.get_font_size('follower_value'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"]
        )
        self.follower_value_label.pack(side=tk.LEFT, padx=15)
        self.register_font_widget(self.follower_value_label, 'follower_value')

        # 变化指示器
        self.follower_change_label = tk.Label(
            follower_row,
            text="◆ 等待数据同步 ◆",
            font=("Consolas", self.get_font_size('follower_change')),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_cyan"]
        )
        self.follower_change_label.pack(side=tk.LEFT, padx=10)
        self.register_font_widget(self.follower_change_label, 'follower_change')

        # ===== 按钮区域 =====
        btn_frame = tk.Frame(top_content, bg=CYBER_COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, pady=8)

        # 刷新按钮
        refresh_btn = tk.Button(
            btn_frame,
            text="⟳ SYNC",
            command=self.manual_refresh,
            font=("Consolas", self.get_font_size('btn'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_cyan"],
            activebackground=CYBER_COLORS["neon_cyan"],
            activeforeground=CYBER_COLORS["bg_main"],
            bd=1,
            padx=12,
            pady=5,
            cursor="hand2"
        )
        refresh_btn.pack(side=tk.LEFT, padx=3)
        self.register_font_widget(refresh_btn, 'btn')

        # 标记按钮
        reset_btn = tk.Button(
            btn_frame,
            text="⚡ MARK",
            command=self.reset_baseline,
            font=("Consolas", self.get_font_size('btn'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_green"],
            activebackground=CYBER_COLORS["neon_green"],
            activeforeground=CYBER_COLORS["bg_main"],
            bd=1,
            padx=12,
            pady=5,
            cursor="hand2"
        )
        reset_btn.pack(side=tk.LEFT, padx=3)
        self.register_font_widget(reset_btn, 'btn')

        # 置顶切换按钮
        self.topmost_var = tk.BooleanVar(value=True)
        topmost_btn = tk.Checkbutton(
            btn_frame,
            text="TOP",
            variable=self.topmost_var,
            command=self.toggle_topmost,
            font=("Consolas", self.get_font_size('btn'), "bold"),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["neon_pink"],
            selectcolor=CYBER_COLORS["bg_secondary"],
            activebackground=CYBER_COLORS["bg_main"],
            activeforeground=CYBER_COLORS["neon_pink"]
        )
        topmost_btn.pack(side=tk.LEFT, padx=8)

        # Cookie设置按钮
        cookie_btn = tk.Button(
            btn_frame,
            text="KEY",
            command=self.set_cookie_simple,
            font=("Consolas", self.get_font_size('btn'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["text_secondary"],
            bd=1,
            width=5,
            cursor="hand2"
        )
        cookie_btn.pack(side=tk.LEFT, padx=3)
        self.register_font_widget(cookie_btn, 'btn')

        # 刷新消息按钮
        refresh_msg_btn = tk.Button(
            btn_frame,
            text="⟳ MSG",
            command=self.manual_refresh_messages,
            font=("Consolas", self.get_font_size('btn'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"],
            activebackground=CYBER_COLORS["neon_yellow"],
            activeforeground=CYBER_COLORS["bg_main"],
            bd=1,
            padx=12,
            pady=5,
            cursor="hand2"
        )
        refresh_msg_btn.pack(side=tk.LEFT, padx=3)
        self.register_font_widget(refresh_msg_btn, 'btn')

        # 状态栏
        self.status_label = tk.Label(
            top_content,
            text="◈ 正在初始化系统...",
            font=("Consolas", self.get_font_size('status')),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["neon_pink"]
        )
        self.status_label.pack(pady=3)
        self.register_font_widget(self.status_label, 'status')

        # ====== 下侧：消息面板 ======
        bottom_frame = tk.Frame(main_paned, bg=CYBER_COLORS["bg_secondary"])
        main_paned.add(bottom_frame, minsize=200, height=450)

        # 底部标题
        bottom_title_frame = tk.Frame(bottom_frame, bg=CYBER_COLORS["bg_secondary"])
        bottom_title_frame.pack(fill=tk.X, padx=10, pady=(10, 8))

        # 标题装饰
        tk.Label(
            bottom_title_frame,
            text="▶",
            font=("Consolas", 12),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"]
        ).pack(side=tk.LEFT)

        msg_title = tk.Label(
            bottom_title_frame,
            text="INCOMING_TRANSMISSIONS",
            font=("Consolas", self.get_font_size('msg_title'), "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"]
        )
        msg_title.pack(side=tk.LEFT, padx=5)
        self.register_font_widget(msg_title, 'msg_title')

        tk.Label(
            bottom_title_frame,
            text="◀",
            font=("Consolas", 12),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"]
        ).pack(side=tk.RIGHT)

        # 分隔线
        tk.Frame(bottom_frame, height=1, bg=CYBER_COLORS["neon_cyan"]).pack(fill=tk.X, padx=10)

        # Cookie提示
        self.cookie_hint = tk.Label(
            bottom_frame,
            text="[警告] 访问密钥未配置 - 点击上方 [KEY] 按钮",
            font=("Consolas", self.get_font_size('status')),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_pink"]
        )
        if not self.cookie:
            self.cookie_hint.pack(pady=15)
        self.register_font_widget(self.cookie_hint, 'status')

        # 消息状态
        self.msg_status_label = tk.Label(
            bottom_frame,
            text="◈ 系统等待中..." if self.cookie else "[警告] 需要访问密钥",
            font=("Consolas", self.get_font_size('status')),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_cyan"] if self.cookie else CYBER_COLORS["neon_pink"]
        )
        self.msg_status_label.pack(pady=5)
        self.register_font_widget(self.msg_status_label, 'status')

        # 消息列表框架
        self.msg_list_frame = tk.Frame(bottom_frame, bg=CYBER_COLORS["bg_secondary"])
        self.msg_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 滚动条
        scrollbar = tk.Scrollbar(
            self.msg_list_frame,
            bg=CYBER_COLORS["bg_main"],
            troughcolor=CYBER_COLORS["bg_secondary"]
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas用于滚动
        self.msg_canvas = tk.Canvas(
            self.msg_list_frame,
            bg=CYBER_COLORS["bg_secondary"],
            highlightthickness=0
        )
        self.msg_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.msg_canvas.yview)
        self.msg_canvas.config(yscrollcommand=scrollbar.set)

        # 消息容器
        self.msg_container = tk.Frame(self.msg_canvas, bg=CYBER_COLORS["bg_secondary"])
        self.msg_canvas_window = self.msg_canvas.create_window((0, 0), window=self.msg_container, anchor="nw")

        # 绑定事件
        self.msg_container.bind("<Configure>", self.on_frame_configure)
        self.msg_canvas.bind("<Configure>", self.on_canvas_configure)

        # 绑定鼠标滚轮事件
        def on_mousewheel(event):
            self.msg_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        self._mousewheel_handler = on_mousewheel

        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)

        bind_mousewheel_recursive(bottom_frame)

    def on_font_scale_change(self, value):
        """字号滑块变化回调"""
        self.font_scale = float(value)
        self.font_value_label.config(text=f"{int(self.font_scale * 100)}%")
        self.update_all_fonts()

    def on_frame_configure(self, event=None):
        """重置Canvas的滚动区域"""
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """当Canvas大小改变时调整内部Frame宽度"""
        self.msg_canvas.itemconfig(self.msg_canvas_window, width=event.width)

    def format_number(self, num):
        """格式化数字"""
        return str(num)

    def load_data(self):
        """从文件加载上次的数据"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None

    def save_data(self):
        """保存当前数据到文件"""
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False)
        except Exception as e:
            print(f"保存数据失败: {e}")

    def load_cookie(self):
        """从文件加载Cookie"""
        if os.path.exists(COOKIE_FILE):
            try:
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except:
                pass
        return ""

    def set_cookie_simple(self):
        """设置Cookie"""
        dialog = tk.Toplevel(self.root)
        dialog.title("[安全协议] 访问密钥配置")
        dialog.geometry("520x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=CYBER_COLORS["bg_main"])

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (520 // 2)
        y = (dialog.winfo_screenheight() // 2) - (280 // 2)
        dialog.geometry(f"+{x}+{y}")

        # 标题
        title_frame = tk.Frame(dialog, bg=CYBER_COLORS["bg_main"])
        title_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            title_frame,
            text="[ 访问密钥配置 ]",
            font=("Consolas", 16, "bold"),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["neon_yellow"]
        ).pack()

        # 说明
        tk.Label(
            dialog,
            text=">>> 请输入从浏览器获取的SESSDATA值 <<<",
            font=("Consolas", 10),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["neon_cyan"]
        ).pack(pady=5)

        # 输入框
        entry_frame = tk.Frame(dialog, bg=CYBER_COLORS["neon_cyan"], padx=1, pady=1)
        entry_frame.pack(pady=10, padx=20)

        entry = tk.Entry(
            entry_frame,
            width=55,
            font=("Consolas", 10),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"],
            insertbackground=CYBER_COLORS["neon_cyan"],
            bd=0,
            highlightthickness=0
        )
        entry.insert(0, self.cookie)
        entry.pack(padx=8, pady=8)
        entry.select_range(0, tk.END)
        entry.focus()

        # 提示
        tk.Label(
            dialog,
            text="[获取方法] F12 → Application → Cookies → bilibili.com → SESSDATA",
            font=("Consolas", 9),
            bg=CYBER_COLORS["bg_main"],
            fg=CYBER_COLORS["text_secondary"],
            wraplength=480
        ).pack(pady=8)

        def save():
            cookie = entry.get().strip()
            if not cookie:
                messagebox.showwarning("[错误]", "请输入访问密钥！", parent=dialog)
                return

            if len(cookie) < 20:
                messagebox.showwarning("[错误]", "密钥格式不正确，请检查完整性！", parent=dialog)
                return

            try:
                with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                    f.write(cookie)
                self.cookie = cookie

                if hasattr(self, 'cookie_hint'):
                    self.cookie_hint.pack_forget()

                messagebox.showinfo("[成功]", "访问密钥已写入系统\n消息接收功能已激活", parent=dialog)
                dialog.destroy()
                self.refresh_messages()

            except Exception as e:
                messagebox.showerror("[错误]", f"写入失败: {e}", parent=dialog)

        def open_help():
            webbrowser.open("https://www.bilibili.com")

        # 按钮框架
        btn_frame = tk.Frame(dialog, bg=CYBER_COLORS["bg_main"])
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame,
            text="[ 写入系统 ]",
            command=save,
            font=("Consolas", 10, "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_green"],
            activebackground=CYBER_COLORS["neon_green"],
            activeforeground=CYBER_COLORS["bg_main"],
            bd=1,
            padx=20,
            pady=6
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            btn_frame,
            text="[ 打开B站 ]",
            command=open_help,
            font=("Consolas", 10, "bold"),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["neon_yellow"],
            activebackground=CYBER_COLORS["neon_yellow"],
            activeforeground=CYBER_COLORS["bg_main"],
            bd=1,
            padx=20,
            pady=6
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            btn_frame,
            text="[ 取消 ]",
            command=dialog.destroy,
            font=("Consolas", 10),
            bg=CYBER_COLORS["bg_secondary"],
            fg=CYBER_COLORS["text_secondary"],
            activebackground=CYBER_COLORS["text_secondary"],
            activeforeground=CYBER_COLORS["bg_main"],
            bd=1,
            padx=20,
            pady=6
        ).pack(side=tk.LEFT, padx=8)

    def load_avatar(self, url):
        """加载头像图片"""
        try:
            if not url:
                return

            response = requests.get(url, headers=HEADERS, timeout=10)
            image = Image.open(io.BytesIO(response.content))

            # 根据字号调整头像大小（基准90）
            avatar_size = int(90 * self.font_scale)
            avatar_size = max(60, min(120, avatar_size))

            image = image.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)

            # 圆形裁剪
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

            output = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
            output.paste(image, (0, 0))
            output.putalpha(mask)

            photo = ImageTk.PhotoImage(output)
            self.avatar_label.config(image=photo)
            self.avatar_label.image = photo
        except Exception as e:
            print(f"加载头像失败: {e}")

    def fetch_data(self):
        """获取B站数据"""
        try:
            resp1 = requests.get(API_FAN, headers=HEADERS, timeout=10)
            fan_data = resp1.json()

            try:
                resp3 = requests.get(API_INFO, headers=HEADERS, timeout=10)
                info_data = resp3.json()
            except:
                info_data = {"code": -1}

            result = {"success": False}

            if fan_data.get("code") == 0:
                data = fan_data["data"]
                result.update({
                    "success": True,
                    "follower": data.get("follower", 0),
                    "following": data.get("following", 0),
                })

            if info_data.get("code") == 0:
                data = info_data["data"]
                result["name"] = data.get("name", TITLE)
                result["face_url"] = data.get("face", "")
            else:
                result["name"] = TITLE
                result["face_url"] = ""

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_messages(self):
        """获取评论回复消息"""
        if not self.cookie:
            return {"success": False, "error": "未设置Cookie", "messages": []}

        try:
            headers = HEADERS.copy()
            headers["Cookie"] = f"SESSDATA={self.cookie}"

            resp = requests.get(
                API_REPLY,
                headers=headers,
                params={"platform": "web", "build": "0", "mobi_app": "web"},
                timeout=10
            )
            data = resp.json()

            if data.get("code") == 0:
                items = data.get("data", {}).get("items", [])
                messages = []

                for item in items[:10]:
                    user = item.get("user", {})
                    item_data = item.get("item", {})

                    # 从多个可能的位置获取uri和bvid
                    uri = item.get("uri") or item_data.get("uri") or ""
                    bvid = item.get("bvid") or item_data.get("bvid") or ""

                    # 尝试从nested结构获取
                    nested = item_data.get("nested", {})
                    if not uri and nested.get("uri"):
                        uri = nested.get("uri")
                    if not bvid and nested.get("bvid"):
                        bvid = nested.get("bvid")

                    msg = {
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "user_name": user.get("nickname", "未知用户"),
                        "user_avatar": user.get("avatar", ""),
                        "content": item_data.get("source_content", "")[:80],
                        "reply_content": item_data.get("target_reply_content", "")[:80],
                        "title": item_data.get("title", ""),
                        "uri": uri,
                        "bvid": bvid,
                        "timestamp": item.get("reply_time"),
                    }
                    messages.append(msg)

                return {"success": True, "messages": messages}
            else:
                return {"success": False, "error": data.get("message", "获取失败"), "messages": []}

        except Exception as e:
            return {"success": False, "error": str(e), "messages": []}

    def update_msg_list(self, messages):
        """更新消息列表UI"""
        # 清空现有消息
        for widget in self.msg_container.winfo_children():
            widget.destroy()

        def bind_wheel_recursive(widget):
            if hasattr(self, '_mousewheel_handler'):
                widget.bind("<MouseWheel>", self._mousewheel_handler)
            for child in widget.winfo_children():
                bind_wheel_recursive(child)

        if not messages:
            empty_frame = tk.Frame(self.msg_container, bg=CYBER_COLORS["bg_secondary"])
            empty_frame.pack(pady=30)

            empty_label = tk.Label(
                empty_frame,
                text="[ 信号静默 ]\n暂无传入传输",
                font=("Consolas", self.get_font_size('msg_title')),
                bg=CYBER_COLORS["bg_secondary"],
                fg=CYBER_COLORS["text_secondary"],
                justify=tk.CENTER
            )
            empty_label.pack()
            self.register_font_widget(empty_label, 'msg_title')

            bind_wheel_recursive(empty_frame)
            return

        # 添加消息卡片
        for msg in messages:
            self.create_msg_card(msg)

        self.on_frame_configure()

    def create_msg_card(self, msg):
        """创建消息卡片"""
        def bind_wheel_recursive(widget):
            if hasattr(self, '_mousewheel_handler'):
                widget.bind("<MouseWheel>", self._mousewheel_handler)
            for child in widget.winfo_children():
                bind_wheel_recursive(child)

        # 卡片外框
        card_outer = tk.Frame(
            self.msg_container,
            bg=CYBER_COLORS["neon_cyan"],
            padx=1,
            pady=1
        )
        card_outer.pack(fill=tk.X, pady=4, padx=2)

        # 卡片内容
        card = tk.Frame(card_outer, bg=CYBER_COLORS["bg_card"], padx=10, pady=8)
        card.pack(fill=tk.X)

        # 行布局：类型 + 用户名 + 时间
        header_row = tk.Frame(card, bg=CYBER_COLORS["bg_card"])
        header_row.pack(fill=tk.X)

        # 类型标签
        type_text = "◆ REPLY" if msg["type"] == "reply" else "◆ MENTION"
        type_color = CYBER_COLORS["neon_yellow"] if msg["type"] == "reply" else CYBER_COLORS["neon_cyan"]

        type_label = tk.Label(
            header_row,
            text=type_text,
            font=("Consolas", self.get_font_size('msg_type'), "bold"),
            bg=CYBER_COLORS["bg_card"],
            fg=type_color
        )
        type_label.pack(side=tk.LEFT)

        # 用户名
        name_label = tk.Label(
            header_row,
            text=f"> {msg['user_name']}",
            font=("Consolas", self.get_font_size('msg_name'), "bold"),
            bg=CYBER_COLORS["bg_card"],
            fg=CYBER_COLORS["neon_green"]
        )
        name_label.pack(side=tk.LEFT, padx=10)

        # 时间
        if msg["timestamp"]:
            time_str = datetime.fromtimestamp(msg["timestamp"]).strftime("%m-%d %H:%M")
            time_label = tk.Label(
                header_row,
                text=f"[{time_str}]",
                font=("Consolas", self.get_font_size('msg_time')),
                bg=CYBER_COLORS["bg_card"],
                fg=CYBER_COLORS["neon_pink"]
            )
            time_label.pack(side=tk.RIGHT)

        # 视频标题
        if msg["title"]:
            title_text = msg["title"][:50] + "..." if len(msg['title']) > 50 else msg['title']
            title_label = tk.Label(
                card,
                text=f"@ {title_text}",
                font=("Consolas", self.get_font_size('msg_time')),
                bg=CYBER_COLORS["bg_card"],
                fg=CYBER_COLORS["text_secondary"],
                anchor="w"
            )
            title_label.pack(fill=tk.X, pady=(3, 0))

        # 评论内容
        content_text = msg["reply_content"] or msg["content"]
        if content_text:
            content_frame = tk.Frame(card, bg=CYBER_COLORS["bg_secondary"], padx=6, pady=4)
            content_frame.pack(fill=tk.X, pady=4)

            content_label = tk.Label(
                content_frame,
                text=f">>> {content_text}",
                font=("Consolas", self.get_font_size('msg_content')),
                bg=CYBER_COLORS["bg_secondary"],
                fg=CYBER_COLORS["text_primary"],
                wraplength=int(1000 * self.font_scale),
                justify=tk.LEFT,
                anchor="w"
            )
            content_label.pack(fill=tk.X)

        # 点击跳转到B站回复消息页面
        def open_link(event, msg_data=msg):
            opened = False

            # 方法1: 使用API返回的uri
            if msg_data.get("uri"):
                url = msg_data["uri"]
                if url.startswith("//"):
                    url = "https:" + url
                elif not url.startswith("http"):
                    url = "https:" + url
                try:
                    webbrowser.open(url)
                    opened = True
                except Exception:
                    pass

            # 方法2: 使用bvid跳转到视频
            if not opened and msg_data.get("bvid"):
                url = f"https://www.bilibili.com/video/{msg_data['bvid']}"
                try:
                    webbrowser.open(url)
                    opened = True
                except Exception:
                    pass

            # 方法3: 跳转到消息中心回复页面
            if not opened:
                try:
                    webbrowser.open("https://message.bilibili.com/#/reply")
                except Exception:
                    pass

        card.bind("<Button-1>", open_link)
        card_outer.bind("<Button-1>", open_link)

        # 为卡片内所有子组件绑定点击事件
        def bind_click_recursive(widget):
            try:
                widget.bind("<Button-1>", open_link)
            except:
                pass
            for child in widget.winfo_children():
                bind_click_recursive(child)

        bind_click_recursive(card)

        # 悬停效果
        def on_enter(e):
            card_outer.config(bg=CYBER_COLORS["neon_yellow"])
            card.config(cursor="hand2")

        def on_leave(e):
            card_outer.config(bg=CYBER_COLORS["neon_cyan"])

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        card_outer.bind("<Enter>", on_enter)
        card_outer.bind("<Leave>", on_leave)

        bind_wheel_recursive(card_outer)

    def update_ui(self, data):
        """更新数据UI"""
        if not data.get("success"):
            self.status_label.config(
                text=f"[错误] 数据同步失败: {data.get('error', '未知错误')}",
                fg=CYBER_COLORS["neon_red"]
            )
            return

        # 检测粉丝数变化（蜂鸣提醒）
        if not self.first_data_load and self.data.get('follower'):
            old_follower = self.data.get('follower', 0)
            new_follower = data.get('follower', 0)
            if new_follower > old_follower:
                # 新关注 - 蜂鸣一声
                threading.Thread(target=beep, args=(1,), daemon=True).start()

        self.first_data_load = False

        if data.get('face_url') and not self.data.get('face_url'):
            self.load_avatar(data['face_url'])

        if self.data.get('follower'):
            self.prev_data = self.data.copy()

        self.data = data
        self.save_data()

        self.name_label.config(text=f">> @{data['name']}")

        baseline_follower = self.baseline_data.get('follower', data['follower']) if self.baseline_data else data['follower']
        self.update_follower_card(data['follower'], baseline_follower)

        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(
            text=f"◈ 同步完成 [{now}] | 间隔: {REFRESH_INTERVAL}s",
            fg=CYBER_COLORS["neon_cyan"]
        )

    def update_follower_card(self, new_val, baseline_val):
        """更新粉丝数卡片"""
        self.follower_value_label.config(text=self.format_number(new_val))

        change = new_val - baseline_val
        if change > 0:
            self.follower_change_label.config(
                text=f"▲ +{change} NEW",
                fg=CYBER_COLORS["neon_green"]
            )
        elif change < 0:
            self.follower_change_label.config(
                text=f"▼ {change}",
                fg=CYBER_COLORS["neon_red"]
            )
        else:
            self.follower_change_label.config(
                text="◆ 稳定 ◆",
                fg=CYBER_COLORS["neon_cyan"]
            )

    def reset_baseline(self):
        """重置基线数据"""
        self.baseline_data = self.data.copy()
        self.prev_data = self.data.copy()
        self.update_ui(self.data)
        self.status_label.config(text="◈ 基线数据已标记", fg=CYBER_COLORS["neon_green"])

    def refresh_data(self):
        """刷新数据"""
        self.status_label.config(text="◈ 正在同步数据...", fg=CYBER_COLORS["neon_yellow"])

        def do_refresh():
            data = self.fetch_data()
            self.root.after(0, lambda: self.update_ui(data))

        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()

    def refresh_messages(self):
        """刷新消息"""
        if not self.cookie:
            self.msg_status_label.config(text="[警告] 需要访问密钥", fg=CYBER_COLORS["neon_pink"])
            self.update_msg_list([])
            return

        self.msg_status_label.config(text="◈ 正在接收传输...", fg=CYBER_COLORS["neon_yellow"])

        def do_refresh():
            result = self.fetch_messages()
            self.root.after(0, lambda: self.update_msg_ui(result))

        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()

    def update_msg_ui(self, result):
        """更新消息UI"""
        if result["success"]:
            new_messages = result["messages"]

            # 检测新消息（蜂鸣提醒）
            if not self.first_msg_load:
                new_msg_ids = set(msg['id'] for msg in new_messages if msg['id'])
                # 找出新增的消息ID
                new_ids = new_msg_ids - self.prev_msg_ids
                if len(new_ids) > 0:
                    # 有新回复/留言 - 蜂鸣三声
                    threading.Thread(target=beep, args=(3,), daemon=True).start()

            self.first_msg_load = False
            self.prev_msg_ids = set(msg['id'] for msg in new_messages if msg['id'])

            self.messages = new_messages
            self.update_msg_list(self.messages)
            self.msg_status_label.config(
                text=f"◈ 共接收到 {len(self.messages)} 条传输 | 间隔: {MSG_REFRESH_INTERVAL}s",
                fg=CYBER_COLORS["neon_cyan"]
            )
        else:
            self.msg_status_label.config(
                text=f"[错误] {result.get('error', '传输失败')}",
                fg=CYBER_COLORS["neon_red"]
            )

    def manual_refresh(self):
        """手动刷新数据"""
        self.refresh_data()

    def manual_refresh_messages(self):
        """手动刷新消息"""
        self.refresh_messages()

    def schedule_refresh(self):
        """定时自动刷新数据"""
        self.refresh_data()
        self.root.after(REFRESH_INTERVAL * 1000, self.schedule_refresh)

    def schedule_msg_refresh(self):
        """定时自动刷新消息"""
        self.refresh_messages()
        self.root.after(MSG_REFRESH_INTERVAL * 1000, self.schedule_msg_refresh)

    def toggle_topmost(self):
        """切换窗口置顶"""
        self.root.attributes('-topmost', self.topmost_var.get())


def main():
    root = tk.Tk()

    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = BilibiliDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()