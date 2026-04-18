# 微信文章阅读器

免费、开源的微信公众号 RSS 阅读器。关注你喜欢的公众号，在一个页面里按时间顺序阅读所有文章。

**完全免费** — 不需要购买服务器，不需要任何付费服务。部署到 Vercel 后，手机浏览器打开网址即可使用。

## 效果预览

- 信息流：所有文章按时间倒序排列，分组查看
- 关注管理：搜索公众号名称一键关注，自定义分组
- 阅读历史：自动记录已读文章

## 部署指南（面向普通用户）

整个过程大约需要 20 分钟，需要完成三件事：

1. 注册微信公众号（用于获取文章的通道）
2. 创建 Supabase 数据库（免费云端数据库）
3. 部署到 Vercel（免费网站托管）

### 第一步：注册微信公众号

你需要一个微信公众号账号来登录微信公众号后台，这是获取文章的唯一通道。**个人订阅号**即可，完全免费。

1. 在电脑浏览器打开 https://mp.weixin.qq.com
2. 点击右上角「立即注册」
3. 选择「订阅号」
4. 按提示填写邮箱、密码、身份信息，完成注册

> 如果你已经有微信公众号，跳过此步。

### 第二步：创建 Supabase 数据库

Supabase 提供免费的云端数据库，用来存储你的订阅和文章数据。

1. 打开 https://supabase.com ，点击「Start your project」，用 GitHub 账号登录（没有 GitHub 账号需要先注册一个）
2. 点击「New Project」
3. 填写项目名称（随意，如 `wechat-reader`），设置数据库密码（**请记住这个密码**），Region 选择 `Southeast Asia (Singapore)` 或任意一个
4. 点击「Create new project」，等待 1-2 分钟创建完成
5. 创建完成后，进入项目页面，点击左侧菜单的 **Settings**（齿轮图标）
6. 点击左侧的 **Database**
7. 找到 **Connection string** 区域，确保上方选择的是 **Transaction** 模式（不是 Session 也不是 Direct）
8. 你会看到一个类似这样的连接串：

```
postgresql://postgres.xxxxxx:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

9. 复制这个连接串，把其中的 `[YOUR-PASSWORD]` 替换为你第 3 步设置的数据库密码
10. 保存好这个完整的连接串，下一步要用

### 第三步：部署到 Vercel

Vercel 是一个免费的网站托管平台，可以直接从 GitHub 部署。

#### 3.1 Fork 本项目

1. 打开本项目的 GitHub 页面：https://github.com/JianXiao2021/wechat_article_feed
2. 点击右上角的「Fork」按钮，将项目复制到你自己的 GitHub 账号下

#### 3.2 在 Vercel 上部署

1. 打开 https://vercel.com ，点击「Start Deploying」，用 GitHub 账号登录
2. 登录后点击「Add New...」→「Project」
3. 在列表中找到你刚 Fork 的 `wechat_article_feed` 仓库，点击「Import」
4. 在配置页面，展开「Environment Variables」，添加以下三个环境变量：

| Name | Value |
|------|-------|
| `DATABASE_URL` | 第二步保存的 Supabase 连接串（完整的，包含 `postgresql://` 开头） |
| `SECRET_KEY` | 随便输入一串字符，如 `my-secret-key-123abc`（用于加密会话，越长越安全） |
| `DB_TYPE` | `supabase` |

5. 点击「Deploy」，等待 1-2 分钟
6. 部署成功后，Vercel 会给你一个网址，形如 `https://wechat-article-feed-xxx.vercel.app`

**恭喜，部署完成！**

### 第四步：开始使用

1. 在手机或电脑浏览器打开 Vercel 给你的网址
2. 注册一个账号（这是你的阅读器账号，和微信公众号账号无关）
3. 注册后会跳转到微信登录页面，页面上会显示一个二维码
4. 用**微信**扫描这个二维码（需要使用手机摄像头对准屏幕），在手机上确认登录
5. 登录成功后，进入「关注」页面，搜索公众号名称来关注
6. 回到「信息流」页面，选择分组标签查看文章

> **提示**：扫码登录后约 30 天有效。到期前会在「我的」页面提醒，可点击「延长会话」手动续期。

### 手机添加到主屏幕（像 APP 一样使用）

- **iPhone Safari**：打开网址 → 点底部分享按钮 → 「添加到主屏幕」
- **Android Chrome**：打开网址 → 点右上角菜单 → 「添加到主屏幕」

## 注意事项

### 关于扫码登录

- 微信公众号后台要求**摄像头扫码**登录，不支持长按识别或截图扫码
- 如果你在手机上使用，第一次扫码建议在电脑上打开网站扫码登录，之后手机可以直接用
- 如果你只有手机，需要用另一台设备显示二维码，然后用手机微信扫码

### 关于文章同步

- 建议每个分组内的公众号数量**不超过 15 个**，太多会导致同步时间较长
- 关注新公众号后，首次加载该公众号的文章可能需要几秒钟。如果一个分组下公众号较多，加载时间可能较长
- 同一公众号 30 分钟内不会重复同步（冷却机制），手动点「刷新文章」可跳过冷却期
- 文章同步是并发进行的，先获取到的文章会立即显示在页面上

### 关于网络

- 访问 Vercel 网站在部分地区可能需要**科学上网**
- 如果你有自己的域名，可以在 Vercel 项目设置中绑定自定义域名来解决此问题
- 阅读文章时点击标题会跳转到微信原文页面，该页面不受 Vercel 网络限制

### 其他

- 微信登录会话约 30 天过期，到期前会在「我的」页面提醒，可点击「延长会话」手动续期
- 关注的公众号和分组等数据可以随时在「我的」页面导出为 JSON 文件备份
- 该项目获取文章的方式依赖微信公众号后台接口，请合理使用，避免过于频繁的请求导致账号被封禁

## 进阶：本地开发与自建服务器

以下内容面向有开发经验的用户。

### 本地运行（SQLite 零配置）

```bash
git clone https://github.com/JianXiao2021/wechat_article_feed.git
cd wechat_article_feed

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python3 app.py
```

浏览器打开 http://localhost:5000 。数据存储在本地 `data/app.db`。

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_TYPE` | `local`（SQLite）/ `supabase`（PostgreSQL）/ `auto`（自动检测） | `auto` |
| `DATABASE_URL` | PostgreSQL 连接串（`local` 模式不需要） | — |
| `SECRET_KEY` | Flask 会话密钥（不设置会自动生成） | 自动生成 |
| `ARTICLE_CACHE_TTL` | 同步冷却时间，分钟 | `30` |
| `MAX_ARTICLE_PAGES` | 每个公众号最大拉取页数（每页 10 篇） | `3` |
| `WX_SESSION_DAYS` | 微信登录会话有效天数 | `30` |

### 部署到自建服务器

```bash
# 在服务器上
git clone https://github.com/JianXiao2021/wechat_article_feed.git
cd wechat_article_feed

cp .env.example .env
# 编辑 .env 按需配置

bash deploy.sh
```

生产环境使用 Gunicorn 运行：

```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
```

可配合 systemd + Nginx + Let's Encrypt 实现后台运行和 HTTPS。

### 数据迁移

在「我的」页面支持数据导出/导入（JSON 格式），可用于：
- SQLite 与 Supabase 之间切换
- 更换设备或服务器迁移

### 技术栈

- 后端：Python Flask + SQLAlchemy
- 数据库：SQLite / PostgreSQL（Supabase）
- 前端：原生 HTML/CSS/JS（移动端优先）
- 部署：Vercel Serverless / Gunicorn

## License

MIT
