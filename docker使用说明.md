# B站数据看板 - Docker部署指南（Web版）

## Web版本优势

- 纯Web界面，无需VNC/X11转发
- 镜像更小（~50MB vs VNC版300MB）
- NAS/服务器通用，浏览器直接访问
- 赏心悦目的赛博朋克2077风格

---

## 构建 Docker 镜像

```powershell
cd "J:\B站数据看板"
docker build -f Dockerfile.web -t bilibili-dashboard:latest .
```

## 导出为 tar 文件

```powershell
docker save -o bilibili-dashboard.tar bilibili-dashboard:latest
```

---

## NAS Docker 运行

```bash
# 导入镜像
docker load -i bilibili-dashboard.tar

# 运行容器
docker run -d \
  --name bilibili-dashboard \
  -p 5000:5000 \
  -v /path/to/data:/app/data \
  --restart unless-stopped \
  bilibili-dashboard:latest
```

## 访问看板

浏览器打开：`http://NAS_IP:5000`

---

## 配置说明

### Cookie配置

访问界面后点击 `[KEY]` 按钮，输入从浏览器获取的SESSDATA值。

获取方法：
1. 登录 bilibili.com
2. F12 → Application → Cookies → bilibili.com
3. 复制 SESSDATA 的值

### 数据持久化

挂载 `/app/data` 目录可持久化：
- `bilibili_cookie.txt` - Cookie配置
- `bilibili_data.json` - 粉丝基线数据

---

## 文件结构

```
B站数据看板/
├── web_app.py           # Flask后端
├── templates/
│   └── index.html       # Web前端（赛博朋克风格）
├── Dockerfile.web       # Docker构建文件
├── requirements.txt     # Python依赖
└── data/                # 数据目录（挂载点）
    ├── bilibili_cookie.txt
    └── bilibili_data.json
```