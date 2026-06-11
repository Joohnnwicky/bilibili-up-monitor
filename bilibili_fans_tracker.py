#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站粉丝追踪器 - 每小时爬取粉丝列表，持续累计取关者，计算关注天数

用法:
  python bilibili_fans_tracker.py              # 获取当前小时快照并对比
  python bilibili_fans_tracker.py --scan       # 扫描历史快照重建取关列表
"""

import requests
import json
import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============ 配置（与 web_app.py 路径一致） ============
UID = "662899682"
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
COOKIE_FILE = DATA_DIR / "bilibili_cookie.txt" if (DATA_DIR / "bilibili_cookie.txt").exists() else BASE_DIR / "bilibili_cookie.txt"
FANS_DIR = DATA_DIR / "fans"                     # 粉丝快照: YYYY-MM-DD_HH.json
UNFOLLOWERS_FILE = DATA_DIR / "unfollowers.json" # 累计取关名单
PAGE_SIZE = 50
REQUEST_DELAY = 1.0
MAX_RETRIES = 3
RETRY_WAIT = 10
# ============================================


def load_cookie():
    """从 bilibili_cookie.txt 读取 SESSDATA"""
    if COOKIE_FILE.exists():
        try:
            return COOKIE_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    print("❌ Cookie 未设置")
    sys.exit(1)


def make_headers(sessdata):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Referer": "https://member.bilibili.com/platform/fans/manage",
        "Cookie": f"SESSDATA={sessdata}",
    }


def get_fans_page(sessdata, page):
    url = "https://api.bilibili.com/x/relation/followers"
    params = {"vmid": UID, "pn": page, "ps": PAGE_SIZE, "order": "desc"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=make_headers(sessdata), timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 0:
                return data["data"]

            code = data.get("code", 0)
            msg = data.get("message", "")
            print(f"\n  ⚠️ API错误 code={code}: {msg}")

            if code == -352:
                print(f"  触发风控，等待 {RETRY_WAIT}s 后重试...")
                time.sleep(RETRY_WAIT)
                continue
            if code == -101:
                print("  ❌ 登录已过期，请更新 Cookie")
                sys.exit(1)
            return None

        except requests.RequestException as e:
            print(f"\n  ⚠️ 请求失败 (第{attempt + 1}次): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(3)

    return None


def get_all_fans(sessdata):
    fans = []
    page = 1
    total = None

    print("📥 开始获取粉丝列表...")

    while True:
        print(f"  第 {page} 页...", end="", flush=True)
        data = get_fans_page(sessdata, page)

        if data is None:
            print(" ❌")
            break

        followers = data.get("list") or []

        raw_total = data.get("total", 0)
        total = raw_total.get("total", 0) if isinstance(raw_total, dict) else raw_total

        if not followers:
            # B站API偶尔跳页返回空，如果还没拿够total就继续翻
            if total and len(fans) < total and page < (total // PAGE_SIZE + 3):
                print(f" 空页(跳过), 已获取 {len(fans)}/{total}")
                page += 1
                time.sleep(REQUEST_DELAY)
                continue
            print(" ✅ (无更多数据)")
            break

        fans.extend(followers)

        print(f" 已获取 {len(fans)}/{total}")

        if total and len(fans) >= total:
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    print(f"✅ 共获取 {len(fans)} 个粉丝\n")
    return fans


# ============ 快照管理 ============

def get_snapshot_key():
    """当前小时的快照标识，如 2026-06-11_09"""
    return datetime.now().strftime("%Y-%m-%d_%H")


def save_snapshot(fans, key):
    FANS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = FANS_DIR / f"{key}.json"
    snapshot = {
        "key": key,
        "uid": UID,
        "count": len(fans),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fans": [{"mid": fan["mid"], "uname": fan.get("uname", "")} for fan in fans],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"💾 快照已保存: {filepath}")
    return filepath


def load_snapshot(key):
    filepath = FANS_DIR / f"{key}.json"
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_snapshots():
    """返回所有快照key，按时间排序"""
    if not FANS_DIR.exists():
        return []
    return sorted(f.stem for f in FANS_DIR.glob("*.json"))


def get_previous_snapshot_key(before_key):
    """获取 before_key 之前最近的快照key"""
    snapshots = list_snapshots()
    earlier = [s for s in snapshots if s < before_key]
    return earlier[-1] if earlier else None


# ============ 累计取关名单 ============

def load_unfollowers():
    """加载累计取关名单"""
    if UNFOLLOWERS_FILE.exists():
        try:
            with open(UNFOLLOWERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"updated": "", "list": []}


def save_unfollowers(data):
    """保存累计取关名单"""
    UNFOLLOWERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(UNFOLLOWERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"📄 取关名单已更新: {UNFOLLOWERS_FILE}")


def find_first_seen(mid):
    """在历史快照中查找某用户最早出现的时间"""
    snapshots = list_snapshots()
    for key in snapshots:
        snap = load_snapshot(key)
        if snap is None:
            continue
        for fan in snap["fans"]:
            if fan["mid"] == mid:
                return snap["time"]
    return None


def calc_follow_days(first_seen_str, unfollowed_str):
    """计算关注天数，不到1天按1天算"""
    try:
        first = datetime.strptime(first_seen_str, "%Y-%m-%d %H:%M:%S")
        unfollow = datetime.strptime(unfollowed_str, "%Y-%m-%d %H:%M:%S")
        delta = unfollow - first
        days = delta.days + (1 if delta.seconds > 0 else 0)
        return max(days, 1)
    except Exception:
        return 1


def update_unfollowers(prev_key, curr_key):
    """对比两个快照，更新累计取关名单"""
    prev_data = load_snapshot(prev_key)
    curr_data = load_snapshot(curr_key)

    if not prev_data or not curr_data:
        print("❌ 快照数据不完整，无法对比")
        return

    prev_mids = {fan["mid"]: fan["uname"] for fan in prev_data["fans"]}
    curr_mids = {fan["mid"]: fan["uname"] for fan in curr_data["fans"]}

    unfollowed_mids = set(prev_mids.keys()) - set(curr_mids.keys())
    new_followed_mids = set(curr_mids.keys()) - set(prev_mids.keys())

    unfollowers_db = load_unfollowers()
    existing_mids = {u["mid"] for u in unfollowers_db["list"]}

    # 新增取关者
    new_unfollowers = []
    for mid in sorted(unfollowed_mids):
        if mid in existing_mids:
            continue  # 已记录过，跳过
        uname = prev_mids[mid]
        first_seen = find_first_seen(mid)
        unfollowed_at = curr_data["time"]
        follow_days = calc_follow_days(first_seen, unfollowed_at) if first_seen else 1

        entry = {
            "mid": mid,
            "uname": uname,
            "first_seen": first_seen or prev_data["time"],
            "unfollowed_at": unfollowed_at,
            "follow_days": follow_days,
        }
        new_unfollowers.append(entry)
        print(f"  👎 {uname:20s}  UID: {mid}  关注了 {follow_days} 天后取关")

    # 检查是否有已记录的取关者重新关注了（从取关名单移除）
    rejoined = []
    for entry in unfollowers_db["list"]:
        if entry["mid"] in new_followed_mids:
            rejoined.append(entry["mid"])
            print(f"  👋 {entry['uname']:20s}  UID: {entry['mid']}  重新关注了，从取关名单移除")

    # 更新名单
    if new_unfollowers:
        unfollowers_db["list"].extend(new_unfollowers)
        # 按取关时间排序
        unfollowers_db["list"].sort(key=lambda x: x["unfollowed_at"], reverse=True)

    if rejoined:
        unfollowers_db["list"] = [u for u in unfollowers_db["list"] if u["mid"] not in rejoined]

    if new_unfollowers or rejoined:
        save_unfollowers(unfollowers_db)
    else:
        print("✅ 本次对比无变化")

    return new_unfollowers, new_followed_mids, rejoined


# ============ 历史重建 ============

def scan_history():
    """扫描所有历史快照，重建累计取关名单"""
    snapshots = list_snapshots()
    if len(snapshots) < 2:
        print("快照不足2个，无法扫描")
        return

    print(f"📂 发现 {len(snapshots)} 个快照，开始逐对对比...\n")

    all_unfollowers = {}  # mid -> entry

    for i in range(1, len(snapshots)):
        prev_key = snapshots[i - 1]
        curr_key = snapshots[i]
        prev_data = load_snapshot(prev_key)
        curr_data = load_snapshot(curr_key)

        if not prev_data or not curr_data:
            continue

        prev_mids = {fan["mid"]: fan["uname"] for fan in prev_data["fans"]}
        curr_mids = {fan["mid"]: fan["uname"] for fan in curr_data["fans"]}

        unfollowed = set(prev_mids.keys()) - set(curr_mids.keys())
        rejoined = set(curr_mids.keys()) - set(prev_mids.keys())

        # 处理取关
        for mid in unfollowed:
            if mid in all_unfollowers:
                continue
            uname = prev_mids[mid]
            first_seen = None
            # 在更早的快照中找首次出现
            for j in range(i):
                snap = load_snapshot(snapshots[j])
                if snap:
                    for fan in snap["fans"]:
                        if fan["mid"] == mid:
                            first_seen = snap["time"]
                            break
                if first_seen:
                    break

            unfollowed_at = curr_data["time"]
            follow_days = calc_follow_days(first_seen, unfollowed_at) if first_seen else 1

            all_unfollowers[mid] = {
                "mid": mid,
                "uname": uname,
                "first_seen": first_seen or prev_data["time"],
                "unfollowed_at": unfollowed_at,
                "follow_days": follow_days,
            }

        # 处理重新关注：从取关名单移除
        for mid in rejoined:
            if mid in all_unfollowers:
                del all_unfollowers[mid]

    # 保存
    result = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "list": sorted(all_unfollowers.values(), key=lambda x: x["unfollowed_at"], reverse=True),
    }
    save_unfollowers(result)
    print(f"\n📊 累计发现 {len(result['list'])} 个取关者")


# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description="B站粉丝追踪器")
    parser.add_argument("--scan", action="store_true", help="扫描历史快照重建取关列表")
    args = parser.parse_args()

    if args.scan:
        scan_history()
        return

    sessdata = load_cookie()
    curr_key = get_snapshot_key()

    # 检查当前小时是否已有快照
    if load_snapshot(curr_key):
        print(f"⚠️ 本小时快照已存在 ({curr_key}.json)，跳过获取")
    else:
        fans = get_all_fans(sessdata)
        if not fans:
            print("❌ 未能获取粉丝列表")
            sys.exit(1)
        save_snapshot(fans, curr_key)

    # 对比上一小时
    prev_key = get_previous_snapshot_key(curr_key)
    if not prev_key:
        print("📝 这是第一次运行，已保存基准快照。")
        print("   下一小时再运行即可看到对比结果。")
        return

    print(f"🔍 对比快照: {prev_key} → {curr_key}")
    result = update_unfollowers(prev_key, curr_key)

    if result:
        new_unfollowers, new_followed, rejoined = result
        print(f"\n{'='*50}")
        print(f"📊 本次对比:")
        print(f"  新取关: {len(new_unfollowers)} 人")
        print(f"  新关注: {len(new_followed)} 人")
        print(f"  重新关注: {len(rejoined)} 人")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()
