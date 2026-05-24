#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站数据监控看板 - 桌面小工具
作者: AI Assistant
功能: 实时显示B站粉丝数、获赞数、评论回复，每分钟自动刷新
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
from PIL import Image, ImageTk
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

# ============== API 地址 ==============
API_FAN = f"https://api.bilibili.com/x/relation/stat?vmid={UID}"
API_STAT = f"https://api.bilibili.com/x/space/upstat?mid={UID}"
API_INFO = f"https://api.bilibili.com/x/space/acc/info?mid={UID}"
API_REPLY = "https://api.bilibili.com/x/msgfeed/reply"  # 获取回复消息


class BilibiliDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title(TITLE)
        # 增加窗口高度，确保按钮可见
        self.root.geometry("650x550")
        self.root.resizable(True, True)
        self.root.minsize(600, 500)
        
        # 窗口置顶
        self.root.attributes('-topmost', True)
        
        # 数据存储
        self.data = {
            'follower': 0,
            'following': 0,
            'likes': 0,
            'views': 0,
            'name': TITLE,
            'face_url': ''
        }
        
        # 消息数据
        self.messages = []
        self.cookie = self.load_cookie()
        
        # 从文件加载上次的数据
        self.baseline_data = self.load_data()
        self.prev_data = self.baseline_data.copy() if self.baseline_data else {}
        
        # 创建UI
        self.create_ui()
        
        # 首次加载数据
        self.refresh_data()
        self.refresh_messages()
        
        # 启动自动刷新定时器
        self.schedule_refresh()
        self.schedule_msg_refresh()
    
    def create_ui(self):
        """创建用户界面 - 左右分栏布局"""
        # 主框架 - 水平分割
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ====== 左侧：数据面板 ======
        left_frame = tk.Frame(main_paned, width=340)
        main_paned.add(left_frame, minsize=320)
        
        # 使用Canvas + Scrollbar让左侧也能滚动
        left_canvas = tk.Canvas(left_frame, highlightthickness=0)
        left_scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 左侧内容框架
        left_content = tk.Frame(left_canvas, padx=15, pady=15)
        left_canvas_window = left_canvas.create_window((0, 0), window=left_content, anchor="nw", width=320)
        
        def configure_left_canvas(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
            left_canvas.itemconfig(left_canvas_window, width=event.width)
        
        left_content.bind("<Configure>", configure_left_canvas)
        left_canvas.bind("<Configure>", lambda e: left_canvas.itemconfig(left_canvas_window, width=e.width))
        
        # 头像区域
        self.avatar_label = tk.Label(left_content)
        self.avatar_label.pack(pady=(0, 5))
        
        # 标题
        title_label = tk.Label(
            left_content, 
            text=TITLE, 
            font=("Microsoft YaHei", 16, "bold"),
            fg="#FB7299"
        )
        title_label.pack(pady=(0, 5))
        
        # 用户名
        self.name_label = tk.Label(
            left_content,
            text="加载中...",
            font=("Microsoft YaHei", 10),
            fg="#666666"
        )
        self.name_label.pack(pady=(0, 5))
        
        # 说明标签
        self.info_label = tk.Label(
            left_content,
            text="📊 数据变化从本次启动开始计算",
            font=("Microsoft YaHei", 8),
            fg="#999999"
        )
        self.info_label.pack(pady=(0, 10))
        
        # 数据卡片框架
        cards_frame = tk.Frame(left_content)
        cards_frame.pack(fill=tk.X, pady=5)
        
        # 粉丝数卡片
        self.follower_card = self.create_card(cards_frame, "👥 粉丝数", "0", 0)
        self.follower_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 获赞数卡片
        self.likes_card = self.create_card(cards_frame, "❤️ 获赞数", "0", 1)
        self.likes_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 关注数（第二行）
        self.following_card = self.create_card(left_content, "🔔 关注数", "0", 2)
        self.following_card.pack(fill=tk.X, pady=5, padx=2)
        
        # 分隔线
        separator = tk.Frame(left_content, height=1, bg="#E0E0E0")
        separator.pack(fill=tk.X, pady=10)
        
        # 状态栏
        self.status_label = tk.Label(
            left_content,
            text="🔄 正在初始化...",
            font=("Microsoft YaHei", 9),
            fg="#999999"
        )
        self.status_label.pack(pady=3)
        
        # 按钮框架 - 使用Frame确保不会被挤压
        btn_frame_outer = tk.Frame(left_content)
        btn_frame_outer.pack(fill=tk.X, pady=10)
        
        btn_frame = tk.Frame(btn_frame_outer)
        btn_frame.pack(fill=tk.X)
        
        # 刷新按钮
        refresh_btn = tk.Button(
            btn_frame,
            text="🔄 刷新",
            command=self.manual_refresh,
            font=("Microsoft YaHei", 9),
            bg="#FB7299",
            fg="white",
            activebackground="#FF85A7",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        refresh_btn.pack(side=tk.LEFT, expand=True, padx=2)
        
        # 标记按钮
        reset_btn = tk.Button(
            btn_frame,
            text="📍 标记",
            command=self.reset_baseline,
            font=("Microsoft YaHei", 9),
            bg="#00AA00",
            fg="white",
            activebackground="#00CC00",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        reset_btn.pack(side=tk.LEFT, expand=True, padx=2)
        
        # 置顶切换按钮
        self.topmost_var = tk.BooleanVar(value=True)
        topmost_btn = tk.Checkbutton(
            btn_frame,
            text="置顶",
            variable=self.topmost_var,
            command=self.toggle_topmost,
            font=("Microsoft YaHei", 9),
            fg="#666666"
        )
        topmost_btn.pack(side=tk.LEFT, padx=5)
        
        # Cookie设置按钮
        cookie_btn = tk.Button(
            btn_frame,
            text="🔑",
            command=self.set_cookie_simple,
            font=("Microsoft YaHei", 9),
            bg="#666666",
            fg="white",
            bd=0,
            width=3,
            cursor="hand2"
        )
        cookie_btn.pack(side=tk.LEFT, padx=2)
        
        # ====== 右侧：消息通知面板 ======
        right_frame = tk.Frame(main_paned, bg="#FAFAFA", padx=10, pady=10)
        main_paned.add(right_frame, minsize=260)
        
        # 消息标题
        msg_title = tk.Label(
            right_frame,
            text="💬 最新回复",
            font=("Microsoft YaHei", 14, "bold"),
            bg="#FAFAFA",
            fg="#333333"
        )
        msg_title.pack(pady=(0, 10))
        
        # Cookie提示（如果没有设置）
        self.cookie_hint = tk.Label(
            right_frame,
            text="点击左侧🔑按钮\n设置Cookie后可查看消息",
            font=("Microsoft YaHei", 10),
            bg="#FAFAFA",
            fg="#FB7299",
            justify=tk.CENTER
        )
        if not self.cookie:
            self.cookie_hint.pack(pady=20)
        
        # 消息列表框架
        self.msg_list_frame = tk.Frame(right_frame, bg="#FAFAFA")
        self.msg_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = tk.Scrollbar(self.msg_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas用于滚动
        self.msg_canvas = tk.Canvas(self.msg_list_frame, bg="#FAFAFA", highlightthickness=0)
        self.msg_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.msg_canvas.yview)
        self.msg_canvas.config(yscrollcommand=scrollbar.set)
        
        # 消息容器
        self.msg_container = tk.Frame(self.msg_canvas, bg="#FAFAFA")
        self.msg_canvas_window = self.msg_canvas.create_window((0, 0), window=self.msg_container, anchor="nw", width=240)
        
        # 绑定事件
        self.msg_container.bind("<Configure>", self.on_frame_configure)
        self.msg_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 消息状态
        self.msg_status_label = tk.Label(
            right_frame,
            text="🔄 加载消息中..." if self.cookie else "🔑 请设置Cookie",
            font=("Microsoft YaHei", 9),
            bg="#FAFAFA",
            fg="#999999"
        )
        self.msg_status_label.pack(pady=5)
        
        # 刷新消息按钮
        refresh_msg_btn = tk.Button(
            right_frame,
            text="🔄 刷新消息",
            command=self.manual_refresh_messages,
            font=("Microsoft YaHei", 9),
            bg="#2196F3",
            fg="white",
            activebackground="#42A5F5",
            bd=0,
            padx=15,
            pady=5,
            cursor="hand2"
        )
        refresh_msg_btn.pack(pady=5)
    
    def create_card(self, parent, title, value, index):
        """创建数据卡片"""
        colors = ["#FFF0F5", "#FFF5F0", "#F0F8FF"]
        
        card = tk.Frame(parent, bg=colors[index % 3], padx=8, pady=10)
        
        title_label = tk.Label(
            card, 
            text=title, 
            font=("Microsoft YaHei", 10),
            bg=colors[index % 3],
            fg="#666666"
        )
        title_label.pack()
        
        value_label = tk.Label(
            card,
            text=value,
            font=("Microsoft YaHei", 16, "bold"),
            bg=colors[index % 3],
            fg="#333333"
        )
        value_label.pack()
        
        change_label = tk.Label(
            card,
            text="",
            font=("Microsoft YaHei", 9),
            bg=colors[index % 3],
            fg="#00AA00"
        )
        change_label.pack()
        
        card.value_label = value_label
        card.change_label = change_label
        
        return card
    
    def on_frame_configure(self, event=None):
        """重置Canvas的滚动区域"""
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """当Canvas大小改变时调整内部Frame宽度"""
        canvas_width = event.width
        self.msg_canvas.itemconfig(self.msg_canvas_window, width=canvas_width)
    
    def format_number(self, num, compact=False):
        """格式化数字"""
        if compact and num >= 1000:
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            return f"{num/1000:.1f}k"
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
        """设置Cookie - 使用简单对话框"""
        # 创建对话框窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("设置B站Cookie")
        dialog.geometry("500x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # 标题
        tk.Label(
            dialog,
            text="🔑 设置B站Cookie",
            font=("Microsoft YaHei", 14, "bold"),
            fg="#FB7299"
        ).pack(pady=10)
        
        # 说明
        tk.Label(
            dialog,
            text="请粘贴从浏览器获取的SESSDATA值：",
            font=("Microsoft YaHei", 10),
            fg="#666666"
        ).pack()
        
        # 输入框
        entry = tk.Entry(dialog, width=60, font=("Consolas", 10))
        entry.insert(0, self.cookie)
        entry.pack(pady=10, padx=20)
        entry.select_range(0, tk.END)
        entry.focus()
        
        # 提示
        tk.Label(
            dialog,
            text="获取方法：F12 → Application → Cookies → https://www.bilibili.com → 找SESSDATA",
            font=("Microsoft YaHei", 9),
            fg="#999999",
            wraplength=450
        ).pack(pady=5)
        
        def save():
            cookie = entry.get().strip()
            if not cookie:
                messagebox.showwarning("提示", "请输入Cookie！", parent=dialog)
                return
            
            if len(cookie) < 20:
                messagebox.showwarning("格式错误", "Cookie太短了，请检查是否复制完整！", parent=dialog)
                return
            
            try:
                with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                    f.write(cookie)
                self.cookie = cookie
                
                # 隐藏提示
                if hasattr(self, 'cookie_hint'):
                    self.cookie_hint.pack_forget()
                
                messagebox.showinfo("成功", "Cookie已保存！\n\n现在会自动刷新消息列表。", parent=dialog)
                dialog.destroy()
                
                # 立即刷新消息
                self.refresh_messages()
                
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：{e}", parent=dialog)
        
        def open_help():
            webbrowser.open("https://www.bilibili.com")
        
        # 按钮框架
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)
        
        tk.Button(
            btn_frame,
            text="💾 保存",
            command=save,
            font=("Microsoft YaHei", 10),
            bg="#00AA00",
            fg="white",
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            btn_frame,
            text="🌐 打开B站",
            command=open_help,
            font=("Microsoft YaHei", 10),
            bg="#FB7299",
            fg="white",
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            btn_frame,
            text="取消",
            command=dialog.destroy,
            font=("Microsoft YaHei", 10),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=10)
    
    def load_avatar(self, url):
        """加载头像图片"""
        try:
            if not url:
                return
            
            response = requests.get(url, headers=HEADERS, timeout=10)
            image = Image.open(io.BytesIO(response.content))
            image = image.resize((80, 80), Image.Resampling.LANCZOS)
            
            # 圆形裁剪
            mask = Image.new('L', (80, 80), 0)
            from PIL import ImageDraw
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 80, 80), fill=255)
            
            output = Image.new('RGBA', (80, 80), (0, 0, 0, 0))
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
                resp2 = requests.get(API_STAT, headers=HEADERS, timeout=10)
                stat_data = resp2.json()
            except:
                stat_data = {"code": -1}
            
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
            
            if stat_data.get("code") == 0:
                data = stat_data["data"]
                result["likes"] = data.get("likes", 0)
                result["views"] = data.get("archive", {}).get("view", 0)
            else:
                result["likes"] = 0
                result["views"] = 0
            
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
            
            # 获取回复消息
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
                
                for item in items[:10]:  # 只取前10条
                    user = item.get("user", {})
                    item_data = item.get("item", {})
                    
                    msg = {
                        "id": item.get("id"),
                        "type": item.get("type"),  # reply 或 at
                        "user_name": user.get("nickname", "未知用户"),
                        "user_avatar": user.get("avatar", ""),
                        "content": item_data.get("source_content", "")[:50],  # 源评论内容
                        "reply_content": item_data.get("target_reply_content", "")[:50],  # 回复内容
                        "title": item_data.get("title", ""),  # 视频标题
                        "uri": item_data.get("uri", ""),  # 跳转链接
                        "bvid": item.get("bvid", ""),  # BV号
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
        
        if not messages:
            # 显示空状态
            empty_label = tk.Label(
                self.msg_container,
                text="暂无新回复\n\n点击左侧🔑按钮设置Cookie\n以获取消息通知",
                font=("Microsoft YaHei", 10),
                bg="#FAFAFA",
                fg="#999999",
                justify=tk.CENTER
            )
            empty_label.pack(pady=50)
            return
        
        # 添加消息卡片
        for msg in messages:
            self.create_msg_card(msg)
        
        self.on_frame_configure()
    
    def create_msg_card(self, msg):
        """创建消息卡片"""
        card = tk.Frame(self.msg_container, bg="white", padx=10, pady=10)
        card.pack(fill=tk.X, pady=5, padx=5)
        
        # 类型标签
        type_text = "💬 回复了你" if msg["type"] == "reply" else "@ 提到了你"
        type_color = "#FB7299" if msg["type"] == "reply" else "#2196F3"
        
        type_label = tk.Label(
            card,
            text=type_text,
            font=("Microsoft YaHei", 8),
            bg="white",
            fg=type_color
        )
        type_label.pack(anchor="w")
        
        # 用户名
        name_label = tk.Label(
            card,
            text=f"👤 {msg['user_name']}",
            font=("Microsoft YaHei", 10, "bold"),
            bg="white",
            fg="#333333"
        )
        name_label.pack(anchor="w", pady=(5, 0))
        
        # 视频标题
        if msg["title"]:
            title_label = tk.Label(
                card,
                text=f"📺 {msg['title'][:30]}..." if len(msg['title']) > 30 else f"📺 {msg['title']}",
                font=("Microsoft YaHei", 9),
                bg="white",
                fg="#666666"
            )
            title_label.pack(anchor="w", pady=(5, 0))
        
        # 评论内容
        content_text = msg["reply_content"] or msg["content"]
        if content_text:
            content_label = tk.Label(
                card,
                text=f"💭 {content_text}",
                font=("Microsoft YaHei", 9),
                bg="#F5F5F5",
                fg="#333333",
                wraplength=200,
                justify=tk.LEFT,
                padx=5,
                pady=5
            )
            content_label.pack(fill=tk.X, pady=5)
        
        # 时间
        if msg["timestamp"]:
            time_str = datetime.fromtimestamp(msg["timestamp"]).strftime("%m-%d %H:%M")
            time_label = tk.Label(
                card,
                text=time_str,
                font=("Microsoft YaHei", 8),
                bg="white",
                fg="#999999"
            )
            time_label.pack(anchor="e")
        
        # 点击跳转
        def open_link(event, bvid=msg["bvid"]):
            if bvid:
                url = f"https://www.bilibili.com/video/{bvid}"
                webbrowser.open(url)
        
        card.bind("<Button-1>", open_link)
        card.bind("<Enter>", lambda e: card.config(bg="#FFF5F7", cursor="hand2"))
        card.bind("<Leave>", lambda e: card.config(bg="white", cursor=""))
    
    def update_ui(self, data):
        """更新数据UI"""
        if not data.get("success"):
            self.status_label.config(
                text=f"❌ 更新失败: {data.get('error', '未知错误')}",
                fg="#FF4444"
            )
            return
        
        if data.get('face_url') and not self.data.get('face_url'):
            self.load_avatar(data['face_url'])
        
        if self.data.get('follower'):
            self.prev_data = self.data.copy()
        
        self.data = data
        self.save_data()
        
        self.name_label.config(text=f"@{data['name']}")
        
        baseline_follower = self.baseline_data.get('follower', data['follower']) if self.baseline_data else data['follower']
        self.update_card(self.follower_card, data['follower'], baseline_follower, compact=False)
        
        baseline_likes = self.baseline_data.get('likes', data['likes']) if self.baseline_data else data['likes']
        self.update_card(self.likes_card, data['likes'], baseline_likes, compact=True)
        
        baseline_following = self.baseline_data.get('following', data['following']) if self.baseline_data else data['following']
        self.update_card(self.following_card, data['following'], baseline_following, compact=False)
        
        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(
            text=f"✅ 更新于 {now} | 每{REFRESH_INTERVAL}秒刷新",
            fg="#666666"
        )
    
    def update_card(self, card, new_val, baseline_val, compact=False):
        """更新卡片数值"""
        card.value_label.config(text=self.format_number(new_val, compact))
        
        change = new_val - baseline_val
        if change > 0:
            card.change_label.config(text=f"▲ +{change}", fg="#00AA00")
        elif change < 0:
            card.change_label.config(text=f"▼ {change}", fg="#FF4444")
        else:
            card.change_label.config(text="—", fg="#999999")
    
    def reset_baseline(self):
        """重置基线数据"""
        self.baseline_data = self.data.copy()
        self.prev_data = self.data.copy()
        self.update_ui(self.data)
        self.status_label.config(text="📍 已标记当前数据为起点", fg="#00AA00")
    
    def refresh_data(self):
        """刷新数据"""
        self.status_label.config(text="🔄 正在获取数据...", fg="#FB7299")
        
        def do_refresh():
            data = self.fetch_data()
            self.root.after(0, lambda: self.update_ui(data))
        
        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()
    
    def refresh_messages(self):
        """刷新消息"""
        if not self.cookie:
            self.msg_status_label.config(text="🔑 请设置Cookie以获取消息", fg="#FF9800")
            self.update_msg_list([])
            return
        
        self.msg_status_label.config(text="🔄 正在获取消息...", fg="#2196F3")
        
        def do_refresh():
            result = self.fetch_messages()
            self.root.after(0, lambda: self.update_msg_ui(result))
        
        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()
    
    def update_msg_ui(self, result):
        """更新消息UI"""
        if result["success"]:
            self.messages = result["messages"]
            self.update_msg_list(self.messages)
            self.msg_status_label.config(
                text=f"✅ 共{len(self.messages)}条消息 | 每{MSG_REFRESH_INTERVAL}秒刷新",
                fg="#666666"
            )
        else:
            self.msg_status_label.config(
                text=f"❌ {result.get('error', '获取失败')}",
                fg="#FF4444"
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
