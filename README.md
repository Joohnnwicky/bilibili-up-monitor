# B站数据监控看板

赛博朋克2077风格的B站UP主数据监控Web应用，支持Docker部署。

## 功能特性

- **粉丝数据监控**：实时显示粉丝数、关注数，每60秒自动刷新
- **消息提醒**：自动获取评论回复通知，每120秒刷新
- **声音提醒**：
  - 新关注：蜂鸣1声
  - 新回复/留言：蜂鸣3声
  - 可通过按钮开关控制
- **用户自定义**：
  - 自定义显示名称
  - 本地上传头像图片
  - 设置头衔（如认证信息）
- **基线标记**：可标记当前粉丝数作为基准，显示涨粉变化
- **赛博朋克风格**：霓虹黄+青蓝配色，科技感UI

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户浏览器                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  粉丝卡片   │  │  消息列表   │  │  设置弹窗   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/JSON
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 Flask 后端 (web_app.py)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ /api/data   │  │/api/messages│  │  /api/user  │       │
│  │ 粉丝数据    │  │  消息列表   │  │  用户设置   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP请求 + Cookie
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   B站 API 接口                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ api.bilibili.com/x/relation/stat   粉丝数据     │    │
│  │ api.bilibili.com/x/msgfeed/reply   回复消息     │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    数据存储                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ bilibili_   │  │ bilibili_   │  │   avatars/  │       │
│  │ data.json   │  │ cookie.txt  │  │  头像文件   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
bilibili-up-monitor/
├── web_app.py           # Flask后端主程序
├── templates/
│   └── index.html       # 前端页面（赛博朋克风格）
├── data/                # 数据目录（Docker挂载）
│   ├── bilibili_cookie.txt      # B站Cookie
│   ├── bilibili_data.json       # 粉丝数据缓存
│   ├── bilibili_user_info.json  # 用户自定义设置
│   └── avatars/                 # 头像图片目录
├── Dockerfile.web       # Docker构建文件
├── requirements.txt     # Python依赖
├── deploy_to_nas.py     # NAS部署脚本
└── README.md            # 说明文档
```

## 快速部署

### 方式一：Docker部署（推荐）

**1. 构建镜像**
```bash
docker build -f Dockerfile.web -t bilibili-dashboard:latest .
```

**2. 运行容器**
```bash
docker run -d \
  --name bilibili-dashboard \
  -p 5000:5000 \
  -v ./data:/app/data \
  --restart unless-stopped \
  bilibili-dashboard:latest
```

**3. 访问页面**
打开浏览器访问 `http://localhost:5000`

### 方式二：NAS部署

**1. 导出镜像**
```bash
docker save -o bilibili-dashboard.tar bilibili-dashboard:latest
```

**2. 上传到NAS**
将tar文件上传到NAS，然后导入：
```bash
docker load -i bilibili-dashboard.tar
```

**3. 运行容器**
```bash
docker run -d \
  --name bilibili-dashboard \
  -p 5001:5000 \
  -v /volume1/docker/bilibili-dashboard/data:/app/data \
  --restart unless-stopped \
  bilibili-dashboard:latest
```

**4. SSH一键部署**
修改 `deploy_to_nas.py` 中的NAS连接信息后运行：
```bash
python deploy_to_nas.py
```

### 方式三：本地运行

**1. 安装依赖**
```bash
pip install flask requests
```

**2. 运行程序**
```bash
python web_app.py
```

## 配置说明

### 1. 设置B站Cookie（必需，用于获取消息）

**获取方法：**
1. 登录 bilibili.com
2. 按 F12 打开开发者工具
3. Application → Cookies → bilibili.com
4. 找到并复制 `SESSDATA` 的值

**设置方式：**
- 页面点击 `[KEY]` 按钮，粘贴SESSDATA值
- 或直接写入 `data/bilibili_cookie.txt` 文件

### 2. 自定义显示信息

点击页面 `[👤 设置]` 按钮：

| 设置项 | 说明 |
|--------|------|
| 名称 | 自定义显示的用户名 |
| 头像 | 选择本地jpg/png图片上传 |
| 头衔 | 如"知名UP主"、"个人认证"等 |

### 3. 标记粉丝基线

点击 `[⚡ MARK]` 按钮，将当前粉丝数标记为基准，
后续会显示涨粉变化（如 `▲ +10 NEW`）。

### 4. 声音提醒控制

声音默认开启。可在页面下方看到状态：
- `◈ 声音提醒: 开启` - 正常提醒
- 点击按钮可切换开关状态

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/data` | GET | 获取粉丝数据 |
| `/api/messages` | GET | 获取回复消息列表 |
| `/api/user` | GET | 获取用户设置 |
| `/api/user` | POST | 保存用户设置（支持图片上传） |
| `/api/cookie` | POST | 保存SESSDATA Cookie |
| `/api/mark` | GET | 标记当前粉丝数为基线 |

## 技术栈

- **后端**：Python 3.11 + Flask
- **前端**：原生HTML/CSS/JavaScript
- **风格**：赛博朋克2077配色
- **部署**：Docker容器化
- **API**：B站Web API接口

## 注意事项

1. **Cookie安全**：SESSDATA是敏感信息，请勿泄露
2. **请求频率**：数据刷新间隔60秒，避免触发B站限流
3. **充电数据**：B站充电人数无公开API，无法自动获取
4. **头像文件**：上传后存储在 `data/avatars/` 目录

## 常见问题

**Q: 粉丝数显示不准确？**
A: B站API可能限流，等待几分钟后自动恢复。

**Q: 消息列表为空？**
A: 需要正确设置SESSDATA Cookie，确保已登录状态。

**Q: 声音提醒不工作？**
A: 需要用户与页面交互后才能播放声音（浏览器安全策略）。

## 许可证

MIT License

## 作者

前线观察大队