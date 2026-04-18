#!/bin/bash
# deploy.sh - One-command deployment script for WeChat Article Reader
# Usage: bash deploy.sh

set -e

echo "=== 微信文章阅读器 - 部署脚本 ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo ">>> 创建虚拟环境..."
    python3 -m venv venv
fi

echo ">>> 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# Load .env file or create one
if [ ! -f ".env" ]; then
    echo ""
    echo "未找到 .env 文件，请选择数据库存储方式："
    echo "  1) 本地 SQLite（无需外部数据库，推荐新手使用）"
    echo "  2) Supabase PostgreSQL（云端数据库，需要注册 Supabase）"
    echo ""
    read -p "请选择 [1/2] (默认: 1): " choice
    choice=${choice:-1}

    if [ "$choice" = "2" ]; then
        cp .env.example .env
        echo ""
        echo "请编辑 .env 文件，填入 DATABASE_URL（Supabase 连接字符串）"
        echo "  nano .env"
        echo ""
        echo "填写完成后重新运行: bash deploy.sh"
        exit 0
    else
        echo "DB_TYPE=local" > .env
        echo ">>> 已选择本地 SQLite 存储"
    fi
fi
export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)

# Generate a persistent secret key if not set
if [ -z "$SECRET_KEY" ]; then
    echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
    echo ">>> 已自动生成 SECRET_KEY 并追加到 .env"
fi

echo ">>> 初始化数据库..."
python3 -c "from app import app, db; app.app_context().__enter__(); db.create_all(); print('数据库初始化完成')"

# Get the port (default 5000)
PORT=${PORT:-5000}

echo ""
echo "=== 启动服务 ==="
echo "数据库模式: ${DB_TYPE:-auto}"
echo "访问地址: http://0.0.0.0:${PORT}"
echo "如在服务器上部署，请用 http://你的服务器IP:${PORT} 访问"
echo "按 Ctrl+C 停止服务"
echo ""

# Run with gunicorn for production
exec gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app
