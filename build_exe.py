#!/usr/bin/env python3
"""
打包脚本：将 Python 程序打包成 exe
需要先安装: pip install pyinstaller
"""

import subprocess
import sys
import os
import shutil

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "bilibili_dashboard.py")

    if not os.path.exists(main_script):
        print(f"[错误] 主脚本不存在: {main_script}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",        # 打包成单个文件
        "--windowed",       # 不显示命令行窗口
        "--name", "B站数据看板",
        "--clean",
        "--noconfirm",
        main_script
    ]

    print("=" * 50)
    print("  B站数据看板 - 打包工具")
    print("=" * 50)
    print("\n开始打包...")

    try:
        result = subprocess.run(cmd, cwd=script_dir)

        if result.returncode == 0:
            exe_path = os.path.join(script_dir, "dist", "B站数据看板.exe")
            if os.path.exists(exe_path):
                print("\n" + "=" * 50)
                print("打包成功！")
                print(f"exe 位置: {exe_path}")
                print("=" * 50)

                # 清理临时文件
                build_dir = os.path.join(script_dir, "build")
                spec_file = os.path.join(script_dir, "B站数据看板.spec")
                if os.path.exists(build_dir):
                    shutil.rmtree(build_dir)
                    print("[清理] 已删除 build 目录")
                if os.path.exists(spec_file):
                    os.remove(spec_file)
                    print("[清理] 已删除 spec 文件")
            else:
                print("\n[错误] exe 未生成")
        else:
            print("\n[错误] 打包失败")

    except FileNotFoundError:
        print("\n[错误] 未找到 PyInstaller，请先安装:")
        print("   pip install pyinstaller")
        sys.exit(1)

if __name__ == "__main__":
    main()