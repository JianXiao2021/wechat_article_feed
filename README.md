# 微信文章阅读器

关注微信公众号，聚合阅读最新文章。类似 RSS 阅读器的信息流体验。

## 功能

- **信息流**：所有已关注公众号的文章按时间倒序排列，无限滚动加载
- **关注管理**：粘贴任意文章链接即可关注该公众号，也支持按名称搜索
- **阅读历史**：记录所有已打开的文章，方便回顾
- **微信登录**：通过扫码登录微信公众号后台获取文章，一次登录约4天有效

## 本地运行

```bash
# 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置数据库连接（首次运行必须）
cp .env.example .env
# 编辑 .env，填入你的 DATABASE_URL（获取方式见下方说明）

# 启动开发服务器
python3 app.py
```

浏览器打开 http://localhost:5000

### 获取 DATABASE_URL

本项目使用 [Supabase](https://supabase.com/) 提供的云端 PostgreSQL 数据库。你需要：

1. 注册 [Supabase](https://supabase.com/) 账号并创建一个项目
2. 在项目 Dashboard 顶部点击 **Connect** 按钮
3. 选择连接方式（推荐 Direct Connection），复制连接字符串
4. 将连接字符串填入 `.env` 文件的 `DATABASE_URL` 字段

连接字符串格式如下：

```
postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

> 如果你的网络不支持 IPv6，请在 Connect 页面选择 **Session Pooler** 方式。

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
# 克隆或上传项目到服务器
# 方式1：如果项目在 GitHub
git clone https://github.com/你的用户名/read_wechat_article.git
cd read_wechat_article

# 方式2：从本地上传（在本地电脑执行）
scp -r /path/to/read_wechat_article root@你的服务器IP:/root/

# 在服务器上进入项目目录
cd /root/read_wechat_article

# 配置数据库连接
cp .env.example .env
nano .env  # 填入 DATABASE_URL（获取方式见「获取 DATABASE_URL」章节）

# 一键部署
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
2. 进入「微信」页面，扫码登录你的微信公众号
3. 进入「关注」页面，粘贴文章链接或搜索公众号名称来关注
4. 回到「信息流」页面，点击「刷新文章」获取最新文章
5. 点击文章即可阅读，阅读记录会自动保存到「历史」页面

## 注意事项

- 需要有一个**微信公众号**（个人订阅号免费注册即可），用于登录微信公众号后台
- 微信登录会话约 4 天过期，过期后需要重新扫码
- 获取文章有频率限制，建议不要频繁刷新
- 数据存储在 Supabase 云端 PostgreSQL 数据库中，需配置 `DATABASE_URL`（参见「获取 DATABASE_URL」章节）
- `.env` 文件包含敏感凭证，请勿提交到 Git（已在 `.gitignore` 中排除）

## 技术栈

- 后端：Python Flask
- 数据库：PostgreSQL（Supabase 云端托管）
- 前端：原生 HTML/CSS/JS（移动端优先设计）
- 部署：Gunicorn
