# 微信文章阅读器

当前微信公众号文章的阅读体验存在以下两个巨大的痛点：
1. 公众号文章不能严格按时间排序。我想看最新消息，结果排在前面的是一条三天前的新闻，而且还没有地方可以设置更改，岂有此理！
2. 看公众号文章看到一半有人发消息，切出去回复完，很难再无缝衔接到之前的进度。尽管有浮窗之类功能，但终究不太方便。

为了解决这两大痛点，我（让 Claude Code）做了这个免费、开源的微信公众号阅读器。你可以关注你喜欢的公众号，并在浏览器网页里按时间顺序阅读所有文章。

**完全免费** — 不需要购买服务器，不需要任何付费服务。部署方式如下：
- **安卓手机**：安装 Termux 应用，在手机上直接使用
- **iPhone/iPad**：在电脑上部署，手机通过 Wi-Fi 访问

## 效果预览

- 信息流：所有文章按时间倒序排列，分组查看

<img src='./img/feed.png'>

- 关注管理：搜索公众号名称一键关注，自定义分组

<img src='./img/accounts.png'>

- 阅读历史：自动记录已读文章

<img src='./img/history.png'>

## 部署指南

整个过程大约需要 15-20 分钟。根据你的设备选择对应的方式：

- **安卓手机用户**：参考下方「安卓用户指南」
- **iPhone/iPad 用户**：参考下方「iPhone 用户指南」

---

### 安卓用户指南

#### 第一步：注册微信公众号

你需要一个微信公众号账号来登录微信公众号后台，这是获取文章的唯一通道。**个人订阅号**即可，完全免费。

1. 在电脑浏览器打开 https://mp.weixin.qq.com
2. 点击右上角「立即注册」
3. 选择「订阅号」
4. 按提示填写邮箱、密码、身份信息，完成注册

> 如果你已经有微信公众号，跳过此步。

### 第二步：在手机上安装 Termux

Termux 是一个安卓手机上的终端应用，可以在手机上运行服务器程序。**完全免费，不需要 root 权限。**

#### 2.1 下载安装 Termux
  1. 在手机浏览器打开：https://github.com/termux/termux-app/releases
  2. 找到最新版本（带 `Latest` 标签），下载 `arm64-v8a` 版本的 apk（适用于绝大多数手机），例如：[termux-app_v0.118.3+github-debug_arm64-v8a.apk
](https://github.com/termux/termux-app/releases/download/v0.118.3/termux-app_v0.118.3+github-debug_arm64-v8a.apk)
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
> 执行过程中会出现一些提示需要你手动确认，直接一路按回车使用默认选项即可。这一步可能需要几分钟，请耐心等待。

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
   > 如果 zip 文件不在 downloads 目录，请根据实际下载位置修改上面命令中的路径。

### 第四步：开始使用
1. 由于大多数安卓手机会对后台应用进行省电限制，看到「服务启动成功」后，**必须先允许 Termux 后台活动**，否则会导致浏览器打不开网页。
  - **通用方法**：打开手机「设置」→「电池」→「应用耗电管理」或「后台管理」→ 找到 Termux → 设为「不限制后台」或「允许后台活动」
  - **华为/荣耀**：设置 → 电池 → 启动管理 → 找到 Termux → 关闭「自动管理」→ 开启「允许自启动」「允许后台活动」「允许关联启动」
  - **小米/红米**：设置 → 应用设置 → 应用管理 → 找到 Termux → 省电策略 → 选「无限制」
  - **OPPO/realme**：设置 → 电池 → 更多电池设置 → 优化电池使用 → 找到 Termux → 选「不优化」
  - **vivo**：设置 → 电池 → 后台高耗电 → 允许 Termux
  - **三星**：设置 → 电池 → 后台使用限制 → 将 Termux 从「深度休眠应用」中移除
3. 打开手机浏览器（如 Chrome、夸克、自带浏览器等）
4. 在地址栏输入 **http://127.0.0.1:5000** 并打开（注意：如果手机开着翻墙软件，必须关掉翻墙软件再打开这个网址，否则会打不开）。
5. 注册一个账号（这是你的阅读器账号，和微信公众号账号无关）
6. 注册后会跳转到微信登录页面，点击“获取登录二维码”。
7. 这个二维码**必须用你的手机微信摄像头扫码**，不能保存到相册扫码。请查看下面的“关于扫码”获取建议。扫码后在手机上确认登录即可。
8. 登录成功后，进入「关注」页面，搜索公众号名称来关注。新关注的公众号归入“默认”分组，你可以新建分组，并把关注的公众号归入新的分组。
9. 回到「信息流」页面，选择分组标签查看文章。
> **关于扫码**：微信公众号后台要求**摄像头扫码**登录。你可以用以下方法：
> - 用你的另一个手机或者平板拍下二维码，然后用你的手机微信扫码
> - 找身边的人拍下二维码让你扫
> - 或者在电脑浏览器打开 `http://手机IP:5000`（需要连同一个 WiFi），在电脑上显示二维码，手机微信扫码
>   - 查看手机 IP：在 Termux 中输入 `ifconfig` 查看 `wlan0` 下的 `inet` 地址
> - 扫码登录一次后约 30 天有效，不需要每次都扫

### 日常使用

#### 启动服务

每次重启手机或关闭了 Termux 后，需要重新启动服务：

1. 打开 Termux 应用
2. 输入以下命令并回车：
   ```
   bash ~/wechat-reader/start_server.sh
   ```
3. 看到「服务启动成功」后，在手机浏览器打开 `http://127.0.0.1:5000`

#### 停止服务
想要停止服务时，进入 Termux 执行以下命令：
```
bash ~/wechat-reader/stop_server.sh
```

#### 保持 Termux 后台运行（重要）

启动服务后，可以切换到浏览器使用，**不需要一直停留在 Termux 界面**。但如果 Termux 被系统杀掉，服务就会停止。请按以下步骤设置：

**1. 不要划掉 Termux 后台**

从「最近任务」中划掉 Termux 会导致服务立即停止。可以切走，但不要划掉。

**2. 锁定 Termux 后台（推荐）**

在手机的「最近任务」界面，找到 Termux，长按或下拉它的卡片，选择「锁定」（不同手机叫法不同，可能叫「加锁」「固定」「不允许关闭」等）。锁定后系统清理后台时不会杀掉 Termux。

**3. 关闭电池优化/允许后台行为**

上面第四步你应该已经给 Termux 关闭了电池优化，允许其后台行为。

**4. 允许 Termux 通知**

启动服务时，脚本会自动获取 Termux 唤醒锁（`termux-wake-lock`），此时 Termux 通知栏会显示一个常驻通知。**请不要关闭这个通知**，它是防止系统杀掉 Termux 的重要保护。

如果通知被禁用了：打开手机「设置」→「通知管理」→ 找到 Termux → 允许通知。

#### 添加到浏览器主屏幕（像 APP 一样使用）

- **Chrome**：打开 `http://127.0.0.1:5000` → 点右上角菜单 → 「添加到主屏幕」
- **其他浏览器**：类似操作，在菜单中找到「添加到桌面」

## iOS 用户指南

由于 iOS 系统对后台应用有严格限制，无法在 iPhone 上直接运行服务。**请在电脑上部署服务，然后用 iPhone 访问。**

### 前置要求

1. 一台电脑（Windows、Mac、Linux 均可）
2. 电脑和 iPhone 连接**同一个 Wi-Fi 网络**
3. 参考「电脑部署指南」完成部署

### 在 iPhone 上访问

1. 确保电脑上的服务已启动
2. 查看**电脑的 IP 地址**（参考下方说明）
3. 在 iPhone Safari 浏览器中输入：`http://电脑IP地址:5000`

**查看电脑 IP 的方法：**
- **Windows**：
  1. 按 `Win + R` 键，输入 `cmd` 按回车
  2. 在黑色窗口中输入 `ipconfig` 按回车
  3. 找到「无线局域网适配器 WLAN」下的「IPv4 地址」
- **Mac**：
  1. 打开「终端」应用
  2. 输入 `ifconfig` 按回车
  3. 找到 `en0` 下的 `inet` 地址
- **Linux**：
  1. 打开终端
  2. 输入 `ip addr` 按回车
  3. 找到 `wlp` 或 `wlan` 开头下的 `inet` 地址

**添加到主屏幕：**
1. 在 Safari 打开网页后，点击底部分享按钮
2. 选择「添加到主屏幕」
3. 点击「添加」
4. 之后就可以像 APP 一样直接打开使用了

---

## 电脑部署指南

如果你使用 iPhone，或者希望在电脑上使用，请按照以下步骤部署。整个过程不需要编程基础，只要会复制粘贴命令即可。

### 第一步：注册微信公众号

你需要一个微信公众号账号来登录微信公众号后台，这是获取文章的唯一通道。**个人订阅号**即可，完全免费。

1. 在电脑浏览器打开 https://mp.weixin.qq.com
2. 点击右上角「立即注册」
3. 选择「订阅号」
4. 按提示填写邮箱、密码、身份信息，完成注册

> 如果你已经有微信公众号，跳过此步。

---

### 第二步：检查并安装 Python

1. 打开命令行工具：
   - **Windows**：按 `Win + R`，输入 `cmd` 按回车
   - **Mac/Linux**：打开「终端」应用

2. 输入以下命令检查 Python 是否已安装：
   ```
   python --version
   ```
   或者：
   ```
   python3 --version
   ```

3. 如果显示版本号（如 `Python 3.x.x`），说明已安装，跳到第三步。

4. 如果提示命令不存在，需要安装 Python：
   - **Windows**：访问 https://www.python.org/downloads/ 下载最新版，安装时**务必勾选「Add Python to PATH」**
   - **Mac**：已内置 Python 3，输入 `python3 --version` 查看
   - **Linux (Ubuntu/Debian)**：运行 `sudo apt install python3`
   - **Linux (CentOS/Fedora)**：运行 `sudo dnf install python3`

---

### 第三步：安装 Git

Git 用于下载项目代码。

**Windows：**
1. 访问 https://git-scm.com/download/win 下载安装包
2. 运行安装程序，一路点击「Next」使用默认选项
3. 安装完成后，重新打开命令行窗口

**Mac：**
在终端输入：
```
git --version
```
如果已安装会显示版本号。如果没有，会提示安装 Xcode Command Line Tools，按提示安装即可。

**Linux：**
- Ubuntu/Debian：`sudo apt install git`
- CentOS/Fedora：`sudo dnf install git`

---

### 第四步：下载项目代码

**使用国内镜像加速下载（推荐）**

在命令行中执行以下命令：

```
git clone https://ghfast.top/https://github.com/JianXiao2021/wechat_article_feed.git wechat-reader
```

> 如果提示失败，尝试以下其他镜像：
> ```
> git clone https://github.moeyy.xyz/https://github.com/JianXiao2021/wechat_article_feed.git wechat-reader
> ```
> ```
> git clone https://mirror.ghproxy.com/https://github.com/JianXiao2021/wechat_article_feed.git wechat-reader
> ```

如果所有镜像都失败，可以尝试直接下载 zip 包：
1. 在浏览器打开：https://github.com/JianXiao2021/wechat_article_feed/archive/refs/heads/main.zip
2. 下载后解压到任意目录，重命名文件夹为 `wechat-reader`

---

### 第五步：配置国内镜像源

为了让下载速度更快，先配置 Python 的国内镜像源。

**Windows：**

在命令行执行：
```
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip config set install.trusted-host mirrors.aliyun.com
```

**Mac/Linux：**

在终端执行：
```
pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip3 config set install.trusted-host mirrors.aliyun.com
```

> 如果提示 `pip command not found`，尝试用 `pip3` 代替 `pip`

---

### 第六步：安装依赖

进入项目目录并安装所需库：

**Windows：**
```
cd wechat-reader
pip install -r requirements.txt
```

**Mac/Linux：**
```
cd wechat-reader
pip3 install -r requirements.txt
```

这一步可能需要几分钟，请耐心等待。

---

### 第七步：启动服务

在命令行执行：

**Windows：**
```
python app.py
```

**Mac/Linux：**
```
python3 app.py
```

看到以下提示说明启动成功：
```
 * Running on http://0.0.0.0:5000
```

---

### 第八步：在浏览器中打开

1. 打开浏览器（Chrome、Edge、Safari 等）
2. 在地址栏输入：`http://127.0.0.1:5000`
3. 按回车，即可开始使用

**用手机访问（电脑和手机连同一个 Wi-Fi）：**

1. 查看电脑 IP 地址（参考 iPhone 用户指南中的说明）
2. 在手机浏览器输入：`http://电脑IP:5000`

---

### 日常使用

**启动服务：**
每次重启电脑后，需要重新启动服务：
1. 打开命令行
2. 进入项目目录：`cd wechat-reader`
3. 运行：`python app.py`（Windows）或 `python3 app.py`（Mac/Linux）

**关闭服务：**
在命令行窗口按 `Ctrl + C` 即可停止服务。

---

## 电脑部署指南

查看电脑 IP 的方法：
- **Windows**：打开命令提示符，输入 `ipconfig`，找到「IPv4 地址」
- **Mac/Linux**：打开终端，输入 `ifconfig`，找到 `en0` 下的 `inet` 地址

---

## 注意事项

### 关于扫码登录

- 微信公众号后台要求**摄像头扫码**登录，不支持长按识别或截图扫码
- 首次扫码建议找另一部手机或在电脑上操作
- 扫码登录后会自动保持活跃状态：每次成功获取文章时，会话会自动延期
- 如果长时间不使用（超过4天），可能需要重新扫码登录

### 关于文章同步

- 建议每个分组内的公众号数量**不超过 15 个**，太多会导致同步时间较长
- 该项目获取文章的方式依赖微信公众号后台接口，请合理使用，过于频繁地获取文章可能导致账号被封禁
- 关注新公众号后，首次在”信息流”页面加载该公众号的文章可能需要几秒钟
- 同一公众号 30 分钟内不会重复同步（冷却机制），手动点「刷新文章」可跳过冷却期
- 文章同步是并发进行的，先获取到的文章会立即显示在页面上
- 如果所有公众号都在冷却期内，刷新时不会实际获取文章（仅检查缓存）

### 关于数据安全

- 所有数据存储在你手机本地，不会上传到任何服务器
- 关注的公众号和分组等数据可以随时在「我的」页面导出为 JSON 文件备份。当你换手机时，在「我的」页面点击“导入数据”并导入此文件即可恢复你的关注和分组数据
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
| `ARTICLE_CACHE_TTL` | 文章同步冷却时间，分钟 | `30` |
| `WX_SESSION_DAYS` | 微信登录会话有效期，天（会自动延期） | `4` |

### 使用 Supabase 数据库（推荐用于云部署）

Supabase 是一个开源的 Firebase 替代品，提供免费的 PostgreSQL 云数据库。适合云端部署时使用。

#### 1. 注册 Supabase 账号

1. 访问 https://supabase.com
2. 点击「Start your project」
3. 使用 GitHub 或邮箱注册账号

#### 2. 创建项目

1. 登录后点击「New Project」
2. 填写项目名称（如 `wechat-reader`）
3. 设置数据库密码（请妥善保存）
4. 选择区域（推荐选择「Southeast Asia (Singapore)」以获得更好的国内访问速度）
5. 点击「Create new project」，等待创建完成（通常需要 1-2 分钟）

#### 3. 获取数据库连接字符串

1. 进入项目 Dashboard
2. 左侧菜单选择「Settings」→「Database」
3. 找到「Connection string」部分
4. 选择「URI」标签页
5. 复制连接字符串，格式如下：
   ```
   postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
   ```
6. **重要**：将连接字符串中的 `YOUR_PASSWORD` 替换为你设置的实际数据库密码

> **注意**：请使用 **Direct Connection**（直连）模式的连接字符串，不要使用 Pooler 模式。Pooler 模式是为 WebSockets 等场景设计的，本项目使用普通的 PostgreSQL 连接。

#### 4. 配置项目

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下内容：

```bash
# 使用 Supabase 数据库
DB_TYPE=supabase

# 替换为你的实际连接字符串
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

# 可选：设置 Flask 会话密钥（建议在生产环境设置）
SECRET_KEY=your_random_secret_key_here

# 可选：自定义其他配置
ARTICLE_CACHE_TTL=30
WX_SESSION_DAYS=4
```

#### 5. 初始化数据库表

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用（会自动创建数据库表）
python3 app.py
```

首次运行时，应用会自动在 Supabase 中创建所需的数据表。

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
