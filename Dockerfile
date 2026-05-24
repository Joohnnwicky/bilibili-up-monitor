# B站数据看板 - Docker镜像
# 基于VNC的GUI应用，可通过浏览器访问

FROM python:3.11-slim

LABEL maintainer="前线观察大队"
LABEL description="B站数据监控看板 - Cyberpunk风格"

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    libgtk-3-0 \
    libnotify4 \
    libnss3 \
    libxss1 \
    libxtst6 \
    x11-xkb-utils \
    xfonts-75dpi \
    xfonts-100dpi \
    xfonts-scalable \
    xfonts-cyrillic \
    fonts-liberation \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
RUN pip install --no-cache-dir pillow requests

# 创建工作目录
WORKDIR /app

# 复制应用文件
COPY bilibili_dashboard.py .
COPY bilibili_cookie.txt .
COPY bilibili_data.json .

# 创建启动脚本
RUN echo '#!/bin/bash\n\
Xvfb :99 -screen 0 1024x768x24 &\n\
export DISPLAY=:99\n\
x11vnc -forever -nopw -display :99 -bg\n\
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &\n\
python /app/bilibili_dashboard.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# 暴露端口（noVNC Web界面）
EXPOSE 6080

# 启动命令
CMD ["/app/start.sh"]