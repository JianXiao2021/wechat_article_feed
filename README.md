# 微信文章阅读器

免费、开源的微信公众号 RSS 阅读器。关注你喜欢的公众号，在一个页面里按时间顺序阅读所有文章。

**完全免费** — 不需要购买服务器，不需要任何付费服务。只需要一部安卓手机，安装 Termux 应用后一键部署，在手机浏览器打开即可使用。

## 效果预览

- 信息流：所有文章按时间倒序排列，分组查看
- 关注管理：搜索公众号名称一键关注，自定义分组
- 阅读历史：自动记录已读文章

## 部署指南（面向普通用户，无需编程经验）

整个过程大约需要 15 分钟，只需要完成两件事：

1. 注册微信公众号（用于获取文章的通道）
2. 在手机上安装 Termux 并一键部署

### 第一步：注册微信公众号

你需要一个微信公众号账号来登录微信公众号后台，这是获取文章的唯一通道。**个人订阅号**即可，完全免费。

1. 在电脑浏览器打开 https://mp.weixin.qq.com
2. 点击右上角「立即注册」
3. 选择「订阅号」
4. 按提示填写邮箱、密码、身份信息，完成注册

> 如果你已经有微信公众号，跳过此步。

### 第二步：在手机上安装 Termux

Termux 是一个安卓手机上的终端应用，可以在手机上运行服务器程序。**完全免费，不需要 root 权限。**

#### 2.1 下载安装 Termux

> **重要**：请勿从 Google Play 商店安装 Termux，那里的版本已过时。请从以下渠道下载：

- **推荐**：从 F-Droid 下载
  1. 在手机浏览器打开：https://f-droid.org/packages/com.termux/
  2. 点击页面中的「Download APK」按钮下载
  3. 下载完成后点击安装（如果提示「不允许安装未知来源应用」，按提示到设置中允许即可）

- **备选**：从 GitHub 下载
  1. 在手机浏览器打开：https://github.com/termux/termux-app/releases
  2. 找到最新版本（带 `Latest` 标签），下载 `arm64-v8a` 版本的 apk（适用于绝大多数手机）
  3. 下载完成后点击安装

#### 2.2 初次打开 Termux

1. 安装完成后，打开 Termux 应用
2. 你会看到一个黑色的命令行界面，像电脑上的终端
3. Termux 会自动进行初始化，等待出现 `$` 符号表示已经准备好了

### 第三步：一键部署

> **粘贴方法**：先复制下方命令，然后在 Termux 界面**长按屏幕**，选择「Paste」(粘贴)，再按回车执行。

在 Termux 中**逐条复制粘贴**以下命令。每条命令复制后粘贴到 Termux 中按回车，等待执行完成后再粘贴下一条。

**第 1 条：更换国内镜像源并更新系统**

```
sed -i 's@^\(deb.*stable main\)$@#\1\ndeb https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main stable main@' $PREFIX/etc/apt/sources.list && apt update -y && apt upgrade -y
```

> 执行过程中如果出现提示问你要不要更新配置文件（类似 `Configuration file ... What do you want to do about it?`），直接按回车选默认即可。这一步可能需要几分钟，请耐心等待。

**第 2 条：安装 Python 和 Git**

```
apt install -y python git
```

**第 3 条：下载项目代码**

```
git clone https://ghfast.top/https://github.com/JianXiao2021/wechat_article_feed.git ~/wechat-reader
```

> 如果提示失败，换下面这条试试：
> ```
> git clone https://github.moeyy.xyz/https://github.com/JianXiao2021/wechat_article_feed.git ~/wechat-reader
> ```
> 如果还是失败，参考下方「网络问题解决方案」。

**第 4 条：运行部署脚本**

```
cd ~/wechat-reader && bash deploy_termux.sh
```

部署脚本会自动完成剩余工作（安装依赖、配置数据库等），大约需要 3-5 分钟。

完成后会提示「是否现在启动服务」，输入 `Y` 按回车。

#### 网络问题解决方案

如果第 3 条命令（下载项目代码）多个镜像都失败，可以用手机浏览器下载 zip 包：

1. 手机浏览器打开以下任一地址下载 zip 包：
   - https://ghfast.top/https://github.com/JianXiao2021/wechat_article_feed/archive/refs/heads/main.zip
   - https://github.moeyy.xyz/https://github.com/JianXiao2021/wechat_article_feed/archive/refs/heads/main.zip
   - https://github.com/JianXiao2021/wechat_article_feed/archive/refs/heads/main.zip
2. 在 Termux 中执行以下命令授权访问手机存储：
   ```
   termux-setup-storage
   ```
   弹出权限请求时点击「允许」
3. 然后执行以下命令：
   ```
   apt install -y unzip && cp ~/storage/downloads/wechat_article_feed-main.zip ~/ && cd ~ && unzip wechat_article_feed-main.zip && mv wechat_article_feed-main wechat-reader && cd wechat-reader && bash deploy_termux.sh
   ```
   > 如果 zip 文件不在 downloads 目录，请根据实际下载位置调整路径。

### 第四步：开始使用

1. 看到「服务启动成功」后，打开手机浏览器（如 Chrome、夸克、自带浏览器等）
2. 在地址栏输入 **http://127.0.0.1:5000** 并打开
3. 注册一个账号（这是你的阅读器账号，和微信公众号账号无关）
4. 注册后会跳转到微信登录页面，页面上会显示一个二维码
5. **用另一部手机的微信**扫描这个二维码（需要用摄像头扫码），在手机上确认登录
6. 登录成功后，进入「关注」页面，搜索公众号名称来关注
7. 回到「信息流」页面，选择分组标签查看文章

> **关于扫码**：微信公众号后台要求**摄像头扫码**登录。如果你只有一部手机，可以用以下方法：
> - 让朋友用微信帮你扫一次码
> - 或者在电脑浏览器打开 `http://手机IP:5000`（需要连同一个 WiFi），在电脑上显示二维码，手机微信扫码
>   - 查看手机 IP：在 Termux 中输入 `ifconfig` 查看 `wlan0` 下的 `inet` 地址
> - 扫码登录一次后约 30 天有效，不需要每次都扫

### 日常使用

#### 启动服务

每次重启手机或关闭了 Termux 后，需要重新启动服务：

1. 打开 Termux 应用
2. 输入以下命令：
   ```
   bash ~/wechat-reader/start_server.sh
   ```
3. 看到「服务启动成功」后，在手机浏览器打开 `http://127.0.0.1:5000`

#### 停止服务

```
bash ~/wechat-reader/stop_server.sh
```

#### 保持 Termux 后台运行（重要）

启动服务后，可以切换到浏览器使用，**不需要一直停留在 Termux 界面**。但如果 Termux 被系统杀掉，服务就会停止。请按以下步骤设置：

**1. 不要划掉 Termux 后台**

从「最近任务」中划掉 Termux 会导致服务立即停止。可以切走，但不要划掉。

**2. 锁定 Termux 后台（推荐）**

在手机的「最近任务」界面，找到 Termux，长按或下拉它的卡片，选择「锁定」（不同手机叫法不同，可能叫「加锁」「固定」「不允许关闭」等）。锁定后系统清理后台时不会杀掉 Termux。

**3. 关闭电池优化**

大多数安卓手机会对后台应用进行省电限制，需要给 Termux 关闭电池优化：

- **通用方法**：打开手机「设置」→「电池」→「应用耗电管理」或「后台管理」→ 找到 Termux → 设为「不限制后台」或「允许后台活动」
- **华为/荣耀**：设置 → 电池 → 启动管理 → 找到 Termux → 关闭「自动管理」→ 开启「允许自启动」「允许后台活动」「允许关联启动」
- **小米/红米**：设置 → 应用设置 → 应用管理 → 找到 Termux → 省电策略 → 选「无限制」
- **OPPO/realme**：设置 → 电池 → 更多电池设置 → 优化电池使用 → 找到 Termux → 选「不优化」
- **vivo**：设置 → 电池 → 后台高耗电 → 允许 Termux
- **三星**：设置 → 电池 → 后台使用限制 → 将 Termux 从「深度休眠应用」中移除

**4. 允许 Termux 通知**

启动服务时，脚本会自动获取 Termux 唤醒锁（`termux-wake-lock`），此时 Termux 通知栏会显示一个常驻通知。**请不要关闭这个通知**，它是防止系统杀掉 Termux 的重要保护。

如果通知被禁用了：打开手机「设置」→「通知管理」→ 找到 Termux → 允许通知。

#### 添加到浏览器主屏幕（像 APP 一样使用）

- **Chrome**：打开 `http://127.0.0.1:5000` → 点右上角菜单 → 「添加到主屏幕」
- **其他浏览器**：类似操作，在菜单中找到「添加到桌面」

## 注意事项

### 关于扫码登录

- 微信公众号后台要求**摄像头扫码**登录，不支持长按识别或截图扫码
- 首次扫码建议找另一部手机或在电脑上操作
- 扫码登录后约 30 天有效，到期前会在「我的」页面提醒，可点击「延长会话」手动续期

### 关于文章同步

- 建议每个分组内的公众号数量**不超过 15 个**，太多会导致同步时间较长
- 关注新公众号后，首次加载该公众号的文章可能需要几秒钟
- 同一公众号 30 分钟内不会重复同步（冷却机制），手动点「刷新文章」可跳过冷却期
- 文章同步是并发进行的，先获取到的文章会立即显示在页面上

### 关于数据安全

- 所有数据存储在你手机本地，不会上传到任何服务器
- 关注的公众号和分组等数据可以随时在「我的」页面导出为 JSON 文件备份

### 其他

- 微信登录会话约 30 天过期，到期前会在「我的」页面提醒
- 该项目获取文章的方式依赖微信公众号后台接口，请合理使用，避免过于频繁的请求导致账号被封禁

## 进阶：自建服务器部署

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
- 更换设备或服务器迁移

### 技术栈

- 后端：Python Flask + SQLAlchemy
- 数据库：SQLite / PostgreSQL
- 前端：原生 HTML/CSS/JS（移动端优先）
- 部署：Termux / Gunicorn

## License

MIT
