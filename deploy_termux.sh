#!/data/data/com.termux/files/usr/bin/bash
# deploy_termux.sh - Termux 一键部署脚本（国内网络优化版）
# 用法: bash deploy_termux.sh

set -e

echo "=== 微信文章阅读器 - Termux 一键部署 ==="
echo ""

APP_DIR="$HOME/wechat-reader"

# ---- 1. 更换 Termux 国内镜像源 & 更新系统 ----
echo ">>> [1/6] 配置国内镜像源并更新系统..."
# 使用清华镜像源，避免默认源在国内访问慢或失败
TERMUX_MIRROR="https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main"
mkdir -p "$PREFIX/etc/apt"
echo "deb ${TERMUX_MIRROR} stable main" > "$PREFIX/etc/apt/sources.list"
apt update -y && apt upgrade -y

# ---- 2. 安装系统依赖 ----
echo ">>> [2/6] 安装系统依赖（python、git）..."
apt install -y python git

# ---- 3. 下载项目代码 ----
if [ -d "$APP_DIR" ]; then
    echo ">>> 检测到已有项目目录，尝试更新..."
    cd "$APP_DIR"
    git pull || echo "更新失败，将使用现有代码继续"
else
    echo ">>> [3/6] 下载项目代码..."
    echo ""

    CLONE_SUCCESS=0

    # 依次尝试多个镜像源
    MIRRORS=(
        "https://ghfast.top/https://github.com/JianXiao2021/wechat_article_feed.git"
        "https://github.moeyy.xyz/https://github.com/JianXiao2021/wechat_article_feed.git"
        "https://ghproxy.cc/https://github.com/JianXiao2021/wechat_article_feed.git"
        "https://github.com/JianXiao2021/wechat_article_feed.git"
    )

    for mirror in "${MIRRORS[@]}"; do
        echo "正在尝试: $mirror ..."
        if git clone --depth 1 "$mirror" "$APP_DIR" 2>/dev/null; then
            CLONE_SUCCESS=1
            echo "下载成功！"
            break
        fi
        echo "该地址不可用，尝试下一个..."
        rm -rf "$APP_DIR" 2>/dev/null
    done

    if [ "$CLONE_SUCCESS" = "0" ]; then
        echo ""
        echo "所有自动下载地址均失败。"
        echo ""
        echo "请手动输入一个可用的 git 地址（例如 Gitee 镜像地址）："
        echo "（直接回车可退出，稍后手动下载后重试）"
        read -p "> " custom_url
        if [ -z "$custom_url" ]; then
            echo ""
            echo "你可以通过以下方式手动下载项目后重试："
            echo "  1. 在手机浏览器下载 zip 包并解压到 $APP_DIR"
            echo "  2. 或找到一个可用的 git 地址后执行："
            echo "     git clone <地址> $APP_DIR"
            echo "  然后重新运行: bash deploy_termux.sh"
            exit 1
        fi
        git clone "$custom_url" "$APP_DIR"
    fi

    cd "$APP_DIR"
fi

# ---- 4. 创建虚拟环境 ----
echo ">>> [4/6] 创建 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python -m venv venv
fi
source venv/bin/activate

# ---- 5. 安装 Python 依赖（使用国内 pip 镜像）----
echo ">>> [5/6] 安装 Python 依赖..."
PIP_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"
pip install --upgrade pip -i "$PIP_MIRROR" --quiet
pip install -r requirements.txt -i "$PIP_MIRROR" --quiet

# 持久化 pip 镜像配置，后续 pip install 也走国内源
mkdir -p "$HOME/.config/pip"
cat > "$HOME/.config/pip/pip.conf" <<PIPEOF
[global]
index-url = $PIP_MIRROR
trusted-host = pypi.tuna.tsinghua.edu.cn
PIPEOF

# ---- 6. 配置环境 ----
echo ">>> [6/6] 配置环境..."
if [ ! -f ".env" ]; then
    echo "DB_TYPE=local" > .env
    echo ">>> 已配置为本地 SQLite 数据库"
fi

# 生成 SECRET_KEY
export $(grep -v '^#' .env | grep -v '^\s*$' | xargs 2>/dev/null) 2>/dev/null || true
if [ -z "$SECRET_KEY" ]; then
    echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
    echo ">>> 已自动生成 SECRET_KEY"
fi

# ---- 7. 初始化数据库 ----
echo ">>> 初始化数据库..."
python -c "from app import app, db; app.app_context().__enter__(); db.create_all(); print('数据库初始化完成')"

echo ""
echo "========================================"
echo "  部署完成！"
echo "========================================"
echo ""
echo "启动方式："
echo "  bash ~/wechat-reader/start_server.sh"
echo ""
echo "启动后在手机浏览器打开："
echo "  http://127.0.0.1:5000"
echo ""
echo "首次使用请先注册账号，然后扫码登录微信公众号后台。"
echo ""

# 询问是否立即启动
read -p "是否现在启动服务？[Y/n] " start_now
start_now=${start_now:-Y}

if [ "$start_now" = "Y" ] || [ "$start_now" = "y" ]; then
    echo ""
    echo ">>> 启动服务..."
    bash start_server.sh
fi
