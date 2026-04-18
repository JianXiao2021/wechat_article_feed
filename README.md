# 微信文章阅读器

关注微信公众号，聚合阅读最新文章。类似 RSS 阅读器的信息流体验。

## 功能

- **信息流**：所有已关注公众号的文章按时间倒序排列，按分组查看
- **公众号分组**：自定义分组名称，将关注的公众号分类管理。每个公众号必须属于一个分组，新关注公众号自动归入「默认」分组
- **关注管理**：搜索公众号名称关注，支持分组分配
- **自动同步**：进入信息流页面自动从微信拉取最新文章（增量同步，遇到已缓存文章即停止）。30 分钟冷却期内不重复请求同一公众号，降低封号风险。手动点击「刷新文章」可跳过冷却期强制刷新
- **按需回填**：首次同步每个公众号仅拉取 1 页（10 篇），当用户滚动加载更多时，自动回填更多文章
- **阅读历史**：自动记录已打开的文章，方便回顾
- **微信登录**：扫码登录微信公众号后台获取文章，一次登录约 30 天有效，支持手动延长会话，到期前提醒
- **双数据库支持**：本地 SQLite（零配置）或 Supabase 云端 PostgreSQL，可一键切换和数据迁移
- **数据导出/导入**：在「我的」页面一键导出/导入 JSON 数据，方便更换设备或迁移数据库

## 快速开始（本地 SQLite，零配置）

```bash
# 克隆项目
git clone https://github.com/你的用户名/read_wechat_article.git
cd read_wechat_article

# 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 直接启动（自动使用本地 SQLite，无需配置数据库）
python3 app.py
```

浏览器打开 http://localhost:5000

> 数据存储在 `data/app.db`，无需注册任何外部服务。

## 使用 Supabase 云端数据库

如果你需要云端存储（多设备同步、数据持久化），可以使用 Supabase：

1. 注册 [Supabase](https://supabase.com/) 账号并创建一个项目
2. 在项目 Dashboard 顶部点击 **Connect** 按钮
3. 选择连接方式（推荐 Direct Connection），复制连接字符串
4. 创建 `.env` 文件：

```bash
cp .env.example .env
# 编辑 .env，填入以下内容：
```

```
DB_TYPE=supabase
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

> 如果你的网络不支持 IPv6，请在 Connect 页面选择 **Session Pooler** 方式。

## 数据库切换与数据迁移

### 从 SQLite 迁移到 Supabase

1. 在「我的」页面点击「导出数据」，下载 JSON 备份文件
2. 修改 `.env` 中的 `DB_TYPE=supabase` 并填入 `DATABASE_URL`
3. 重启应用，注册/登录账号
4. 在「我的」页面点击「导入数据」，选择备份文件导入

### 从 Supabase 迁移到 SQLite

操作同上，反向切换 `DB_TYPE=local` 即可。

### 更换设备迁移

1. 在旧设备上的「我的」页面点击「导出数据」
2. 在新设备上部署应用，注册/登录
3. 在「我的」页面点击「导入数据」

也可直接使用 API：
- 导出：`GET /api/data/export`（返回 JSON）
- 导入：`POST /api/data/import`（发送 JSON body）

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_TYPE` | 数据库类型：`local`(SQLite) / `supabase`(PostgreSQL) / `auto`(自动检测) | `auto` |
| `DATABASE_URL` | Supabase PostgreSQL 连接字符串 | 无（local 模式不需要） |
| `SECRET_KEY` | Flask 会话密钥（不设置会自动生成并持久化到 `.secret_key` 文件） | 自动生成 |
| `ARTICLE_CACHE_TTL` | 文章同步冷却时间（分钟），同一公众号在此时间内不会重复请求 | `30` |
| `MAX_ARTICLE_PAGES` | 每个公众号最大拉取页数（每页10篇） | `3` |
| `WX_SESSION_DAYS` | 微信登录会话有效天数 | `30` |
| `PORT` | 服务端口 | `5000` |

## 部署到服务器

### 第一步：购买服务器

推荐以下几个云服务商（选最便宜的轻量级即可）：

| 服务商 | 推荐产品 | 参考价格 |
|--------|---------|---------|
| 阿里云 | 轻量应用服务器 | ~34元/月起 |
| 腾讯云 | 轻量应用服务器 | ~32元/月起 |
| 华为云 | 弹性云服务器 ECS | ~39元/月起 |

**配置建议**：
- 系统：Ubuntu 22.04 或 Debian 12
- 配置：1核 1G 内存即可
- 带宽：3-5Mbps
- 存储：20GB+

购买后你会获得一个**公网 IP 地址**（例如 `123.45.67.89`）和 root 密码。

### 第二步：连接服务器

在电脑终端中：

```bash
ssh root@你的服务器IP
# 输入密码后即可登录
```

### 第三步：安装环境

登录服务器后执行：

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Python 和 Git
apt install -y python3 python3-venv python3-pip git

# 开放 5000 端口（如果有防火墙）
ufw allow 5000
```

### 第四步：部署项目

```bash
# 克隆项目
git clone https://github.com/你的用户名/read_wechat_article.git
cd read_wechat_article

# 一键部署（会引导选择 SQLite 或 Supabase）
bash deploy.sh
```

如需手动配置：

```bash
cp .env.example .env
nano .env  # 填入配置（或不配置，直接使用 SQLite）
bash deploy.sh
```

### 第五步：访问网站

在手机或电脑浏览器中打开：

```
http://你的服务器IP:5000
```

### 第六步：后台持续运行（可选但推荐）

使用 systemd 让服务开机自启：

```bash
cat > /etc/systemd/system/wechat-reader.service << 'EOF'
[Unit]
Description=WeChat Article Reader
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/read_wechat_article
Environment=PORT=5000
ExecStart=/root/read_wechat_article/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
EnvironmentFile=/root/read_wechat_article/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wechat-reader
systemctl start wechat-reader
```

查看运行状态：
```bash
systemctl status wechat-reader
```

查看日志：
```bash
journalctl -u wechat-reader -f
```

### 使用域名访问（可选）

如果你有域名，可以配置 Nginx 反向代理：

```bash
apt install -y nginx

cat > /etc/nginx/sites-available/wechat-reader << 'EOF'
server {
    listen 80;
    server_name 你的域名;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

ln -s /etc/nginx/sites-available/wechat-reader /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

配置 HTTPS（推荐，免费）：
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名
```

## 使用流程

1. 打开网站，注册一个账号
2. 进入「我的」页面，扫码登录你的微信公众号（建议在电脑上扫码，登录约 30 天有效）
3. 进入「关注」页面，搜索公众号名称来关注（新关注的公众号自动归入「默认」分组）
4. （可选）创建分组，将公众号分类管理
5. 回到「信息流」页面，选择分组标签查看文章。进入页面时自动同步最新文章
6. 点击文章即可阅读，阅读记录会自动保存到「历史」页面
7. 点击「刷新文章」按钮可强制刷新（跳过 30 分钟冷却期）

## 注意事项

- 需要有一个**微信公众号**（个人订阅号免费注册即可），用于登录微信公众号后台
- 微信登录会话约 30 天过期，到期前 3 天会在「我的」页面提醒，可点击「延长会话」手动延期
- 进入信息流页面自动同步最新文章（增量同步），30 分钟冷却期内不重复请求。手动「刷新文章」可跳过冷却期
- 每个公众号必须属于一个分组，新关注自动归入「默认」分组，删除分组时其下公众号移入默认分组
- **手机扫码建议**：微信公众平台要求使用摄像头扫码登录，建议在电脑上打开网站扫码，之后手机直接使用
- `.env` 文件包含敏感凭证，请勿提交到 Git（已在 `.gitignore` 中排除）

## 技术栈

- 后端：Python Flask
- 数据库：SQLite（本地）或 PostgreSQL（Supabase 云端）
- 前端：原生 HTML/CSS/JS（移动端优先设计）
- 部署：Gunicorn
