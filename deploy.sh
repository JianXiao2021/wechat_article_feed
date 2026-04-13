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

# Generate a persistent secret key if not set
if [ -z "$SECRET_KEY" ]; then
    if [ ! -f ".env" ]; then
        echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env
        echo ">>> 已生成 .env 文件（包含 SECRET_KEY）"
    fi
    export $(cat .env | xargs)
fi

echo ">>> 初始化数据库..."
python3 -c "from app import app, db; app.app_context().__enter__(); db.create_all(); print('数据库初始化完成')"

# Get the port (default 5000)
PORT=${PORT:-5000}

echo ""
echo "=== 启动服务 ==="
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
