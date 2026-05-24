#!/usr/bin/env python3
"""
生成B站风格图标
使用方法: python generate_icon.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size=256):
    """创建B站粉色风格图标"""
    # B站粉色
    bili_pink = (251, 114, 153)  # #FB7299
    
    # 创建图像
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制圆角矩形背景
    padding = size // 10
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=size // 5,
        fill=bili_pink
    )
    
    # 绘制文字
    try:
        # 尝试使用系统字体
        font_size = size // 2
        try:
            font = ImageFont.truetype("msyh.ttc", font_size)  # 微软雅黑
        except:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        text = "B"
        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 居中绘制
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - text_height // 4
        
        draw.text((x, y), text, font=font, fill="white")
    except Exception as e:
        # 如果字体失败，绘制简单的图形
        center = size // 2
        radius = size // 4
        draw.ellipse(
            [center - radius, center - radius, center + radius, center + radius],
            fill="white"
        )
    
    return img

def main():
    # 创建不同尺寸的图标
    sizes = [256, 128, 64, 48, 32, 16]
    
    # 创建.ico文件（包含多个尺寸）
    images = [create_icon(size) for size in sizes]
    
    # 保存为ico
    output_path = "icon.ico"
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    
    # 同时保存一张PNG作为预览
    images[0].save("icon.png", format='PNG')
    
    print(f"✅ 图标已生成: {output_path}")
    print(f"✅ 预览图已生成: icon.png")

if __name__ == "__main__":
    main()
