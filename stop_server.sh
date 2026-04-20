#!/data/data/com.termux/files/usr/bin/bash
# stop_server.sh - 停止微信文章阅读器服务
# 用法: bash stop_server.sh

APP_DIR="$HOME/wechat-reader"
PID_FILE="$APP_DIR/server.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "服务未在运行"
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo ">>> 正在停止服务 (PID: $PID)..."
    kill "$PID"
    sleep 2
    # 如果还没停止，强制结束
    if kill -0 "$PID" 2>/dev/null; then
        kill -9 "$PID"
    fi
    rm -f "$PID_FILE"
    echo "服务已停止"
else
    rm -f "$PID_FILE"
    echo "服务未在运行（已清理旧记录）"
fi

# 释放 Termux 唤醒锁
if command -v termux-wake-unlock &>/dev/null; then
    termux-wake-unlock
    echo ">>> 已释放唤醒锁"
fi
