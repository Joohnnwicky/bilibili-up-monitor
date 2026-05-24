#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站Cookie一键获取工具
使用方法：
1. 先用浏览器登录B站
2. 运行这个程序
3. 复制输出的内容，粘贴到看板程序中
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
import os

def show_instructions():
    """显示获取步骤"""
    steps = """
📋 最简单的获取Cookie方法：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
方法1：控制台命令（推荐）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 用浏览器（Chrome/Edge）打开 B站并登录
2. 按键盘 F12 打开开发者工具
3. 找到顶部的 "Console" 或 "控制台" 标签，点击它
4. 粘贴下面的代码，按回车：

   document.cookie.match(/SESSDATA=([^;]+)/)[1]

5. 复制输出的结果（不含引号）
6. 点击看板程序的 🔑 按钮，粘贴进去

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
方法2：手动查找
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 按F12打开开发者工具
2. 点击 "Application" 或 "应用程序" 标签
3. 左侧展开：Storage → Cookies
4. 点击 "https://www.bilibili.com"
5. 在右侧列表中找到 "SESSDATA"
6. 双击对应的 Value 值，复制

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 常见问题
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: Console在哪里？
A: 开发者工具顶部有一排标签：Elements, Console, Network...
   中文浏览器显示：元素、控制台、网络

Q: 提示 null 或 undefined？
A: 说明你没有登录B站，请先登录

Q: 复制的内容很长？
A: 没关系，全部复制粘贴即可，格式类似：
   abc123%2Cdef456%2C789xxx*xxxxxxxx

Q: Cookie有效期多久？
A: 一般1-2个月，失效后需要重新获取
"""
    
    # 创建窗口
    window = tk.Tk()
    window.title("获取B站Cookie - 前线观察大队")
    window.geometry("600x500")
    window.resizable(False, False)
    
    # 标题
    tk.Label(
        window,
        text="🔑 获取B站Cookie",
        font=("Microsoft YaHei", 16, "bold"),
        fg="#FB7299"
    ).pack(pady=10)
    
    # 文本区域
    text_area = scrolledtext.ScrolledText(
        window,
        wrap=tk.WORD,
        font=("Microsoft YaHei", 10),
        padx=10,
        pady=10
    )
    text_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    text_area.insert(tk.END, steps)
    text_area.config(state=tk.DISABLED)
    
    # 底部按钮
    btn_frame = tk.Frame(window)
    btn_frame.pack(pady=15)
    
    def open_bilibili():
        import webbrowser
        webbrowser.open("https://www.bilibili.com")
    
    tk.Button(
        btn_frame,
        text="🌐 打开B站登录",
        command=open_bilibili,
        font=("Microsoft YaHei", 10),
        bg="#FB7299",
        fg="white",
        padx=20,
        pady=5
    ).pack(side=tk.LEFT, padx=10)
    
    tk.Button(
        btn_frame,
        text="📋 复制获取命令",
        command=lambda: [
            window.clipboard_clear(),
            window.clipboard_append("document.cookie.match(/SESSDATA=([^;]+)/)[1]"),
            messagebox.showinfo("已复制", "命令已复制到剪贴板！\n去Console控制台粘贴执行即可。")
        ],
        font=("Microsoft YaHei", 10),
        bg="#2196F3",
        fg="white",
        padx=20,
        pady=5
    ).pack(side=tk.LEFT, padx=10)
    
    tk.Button(
        btn_frame,
        text="❌ 关闭",
        command=window.destroy,
        font=("Microsoft YaHei", 10),
        padx=20,
        pady=5
    ).pack(side=tk.LEFT, padx=10)
    
    window.mainloop()

if __name__ == "__main__":
    show_instructions()
