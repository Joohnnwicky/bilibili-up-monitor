# B站数据监控看板 - CYBERPUNK 2077 Edition

赛博朋克2077风格的B站UP主数据监控应用，支持**桌面版(Tkinter)**和**Web版(Docker)**两种部署方式。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Style](https://img.shields.io/badge/Style-Cyberpunk-yellow.svg)

---

## 版本选择

| 版本 | 适用场景 | 特点 |
|------|----------|------|
| **桌面版** | 本地Windows使用 | Tkinter GUI，原生体验 |
| **Web版** | NAS/服务器部署 | Docker容器，浏览器访问 |

---

## Web版（推荐用于NAS部署）

### 功能特性

- **粉丝数据监控**：实时显示粉丝数、关注数，每60秒自动刷新
- **消息提醒**：自动获取评论回复通知，每120秒刷新
- **声音提醒**：新关注蜂鸣1声，新回复蜂鸣3声
- **用户自定义**：名称、头像、头衔
- **基线标记**：显示涨粉变化

### 快速部署

**Docker一键部署：**
```bash
docker build -f Dockerfile.web -t bilibili-dashboard:latest .
docker run -d -p 5000:5000 -v ./data:/app/data bilibili-dashboard:latest
```

访问：`http://localhost:5000`

### 配置Cookie

1. 登录 bilibili.com
2. F12 → Application → Cookies → SESSDATA
3. 页面点击 `[KEY]` 按钮，粘贴保存

---

## 桌面版（Windows本地使用）

### 功能特点

- 实时数据监控（每分钟自动刷新）
- 消息通知显示
- 蜂鸣提醒
- 字号调节（50%-150%）
- 窗口置顶
- 赛博朋克UI

### 快速开始

**方式一：运行exe**
- 从 Releases 下载 `B站数据看板.exe`

**方式二：Python源码**
```bash
pip install pillow requests
python bilibili_dashboard.py
```

---

## 项目结构

```
bilibili-up-monitor/
├── web_app.py           # Web版Flask后端
├── templates/index.html # Web版前端
├── Dockerfile.web       # Docker构建文件
├── bilibili_dashboard.py # 桌面版Tkinter程序
├── requirements.txt     # Python依赖
└── README.md
```

---

## API接口（Web版）

| 接口 | 说明 |
|------|------|
| `/api/data` | 粉丝数据 |
| `/api/messages` | 回复消息 |
| `/api/user` | 用户设置 |

---

## 常见问题

**Q: 粉丝数不准确？**  
A: B站API限流，等待几分钟恢复。

**Q: 消息列表为空？**  
A: 需正确设置SESSDATA Cookie。

---

## 技术栈

- Python 3.11 + Flask (Web版)
- Python 3.8 + Tkinter (桌面版)
- Docker容器化部署

---

## 许可证

MIT License

---

Made with neon lights by 前线观察大队