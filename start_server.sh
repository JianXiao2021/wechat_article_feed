#!/data/data/com.termux/files/usr/bin/bash
# start_server.sh - 启动微信文章阅读器并后台运行
# 用法: bash start_server.sh
#
# 启动后可以关闭 Termux 界面（不要划掉 Termux 后台），服务会持续运行。
# 在手机浏览器打开 http://127.0.0.1:5000 即可使用。

APP_DIR="$HOME/wechat-reader"
LOG_FILE="$APP_DIR/server.log"
PID_FILE="$APP_DIR/server.pid"

# 检查是否已有服务在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "服务已在运行中 (PID: $OLD_PID)"
        echo "浏览器打开: http://127.0.0.1:5000"
        echo ""
        echo "如需重启，请先运行: bash ~/wechat-reader/stop_server.sh"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

cd "$APP_DIR" || { echo "错误: 项目目录不存在，请先运行 deploy_termux.sh"; exit 1; }

# 激活虚拟环境
source venv/bin/activate

# 加载环境变量
export $(grep -v '^#' .env | grep -v '^\s*$' | xargs 2>/dev/null) 2>/dev/null || true

# 获取 Termux 唤醒锁，防止 Android 系统休眠时杀掉进程
if command -v termux-wake-lock &>/dev/null; then
    termux-wake-lock
    echo ">>> 已获取唤醒锁（防止系统休眠杀进程）"
fi

echo ">>> 正在启动微信文章阅读器..."

# 使用 gunicorn 后台启动，日志写入文件
nohup gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile "$LOG_FILE" \
    --error-logfile "$LOG_FILE" \
    app:app > "$LOG_FILE" 2>&1 &

# 记录 PID
echo $! > "$PID_FILE"

# 等待启动
sleep 2

if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
    echo ""
    echo "========================================"
    echo "  服务启动成功！"
    echo "========================================"
    echo ""
    echo "在手机浏览器打开: http://127.0.0.1:5000"
    echo ""
    echo "提示："
    echo "  - 可以退出 Termux 界面，服务会在后台持续运行"
    echo "  - 但不要从最近任务中划掉 Termux，否则服务会停止"
    echo "  - 查看日志: cat $LOG_FILE"
    echo "  - 停止服务: bash ~/wechat-reader/stop_server.sh"
    echo ""
else
    echo "启动失败，请查看日志: cat $LOG_FILE"
    exit 1
fi
