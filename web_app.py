#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站数据监控看板 - Web版本
赛博朋克2077风格 - Flask后端
用户信息完全解耦，由用户自定义设置
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)

# 配置
UID = "662899682"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bilibili_data.json")
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bilibili_cookie.txt")
USER_INFO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bilibili_user_info.json")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://space.bilibili.com/{UID}",
}

API_FAN = f"https://api.bilibili.com/x/relation/stat?vmid={UID}"
API_REPLY = "https://api.bilibili.com/x/msgfeed/reply"


# 静态文件路由（头像）
@app.route('/avatars/<filename>')
def serve_avatar(filename):
    avatar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "avatars")
    return send_from_directory(avatar_dir, filename)


def load_cookie():
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            pass
    return ""


def save_cookie(cookie):
    os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        f.write(cookie)


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"follower": 0, "baseline": 0}


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def load_user_info():
    """从文件加载用户设置"""
    if os.path.exists(USER_INFO_FILE):
        try:
            with open(USER_INFO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"name": "前观日志", "face": "", "title": ""}


def save_user_info(info):
    """保存用户设置到文件"""
    os.makedirs(os.path.dirname(USER_INFO_FILE), exist_ok=True)
    with open(USER_INFO_FILE, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/user', methods=['GET', 'POST'])
def user_settings():
    if request.method == 'GET':
        return jsonify(load_user_info())
    else:
        name = request.form.get("name", "").strip()
        title = request.form.get("title", "").strip()
        face = load_user_info().get("face", "")
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                avatar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "avatars")
                os.makedirs(avatar_dir, exist_ok=True)
                file.save(os.path.join(avatar_dir, "avatar.jpg"))
                face = "/avatars/avatar.jpg"
        save_user_info({"name": name, "face": face, "title": title})
        return jsonify({"success": True, "face": face})


@app.route('/api/data')
def get_data():
    """只获取粉丝数据，用户信息通过/api/user获取"""
    try:
        cookie = load_cookie()
        headers = HEADERS.copy()
        if cookie:
            headers["Cookie"] = f"SESSDATA={cookie}"

        resp_fan = requests.get(API_FAN, headers=headers, timeout=10)
        fan_data = resp_fan.json()

        result = {"success": False}

        if fan_data.get("code") == 0:
            data = fan_data["data"]
            result.update({
                "success": True,
                "follower": data.get("follower", 0),
                "following": data.get("following", 0),
            })

        # 计算粉丝变化
        saved = load_data()
        baseline = saved.get("baseline", result.get("follower", 0))
        change = result.get("follower", 0) - baseline

        result["baseline"] = baseline
        result["change"] = change
        result["cookie_set"] = bool(cookie)

        save_data({
            "follower": result.get("follower", 0),
            "baseline": baseline
        })

        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/messages')
def get_messages():
    cookie = load_cookie()
    if not cookie:
        return jsonify({"success": False, "error": "未设置Cookie", "messages": []})

    try:
        headers = HEADERS.copy()
        headers["Cookie"] = f"SESSDATA={cookie}"

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

                uri = item.get("uri") or item_data.get("uri") or ""
                bvid = item.get("bvid") or item_data.get("bvid") or ""

                nested = item_data.get("nested", {})
                if not uri and nested.get("uri"):
                    uri = nested.get("uri")
                if not bvid and nested.get("bvid"):
                    bvid = nested.get("bvid")

                msg = {
                    "id": item.get("id"),
                    "type": item.get("type"),
                    "user_name": user.get("nickname", "未知"),
                    "user_avatar": user.get("avatar", ""),
                    "content": item_data.get("source_content", "")[:80],
                    "reply_content": item_data.get("target_reply_content", "")[:80],
                    "title": item_data.get("title", ""),
                    "uri": uri,
                    "bvid": bvid,
                    "timestamp": item.get("reply_time"),
                }
                messages.append(msg)

            return jsonify({"success": True, "messages": messages})
        else:
            return jsonify({"success": False, "error": data.get("message", "获取失败")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/cookie', methods=['POST'])
def set_cookie():
    cookie = request.json.get("cookie", "").strip()
    if not cookie or len(cookie) < 20:
        return jsonify({"success": False, "error": "Cookie格式不正确"})
    save_cookie(cookie)
    return jsonify({"success": True})


@app.route('/api/mark')
def mark_baseline():
    data = load_data()
    data["baseline"] = data.get("follower", 0)
    save_data(data)
    return jsonify({"success": True, "baseline": data["baseline"]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)