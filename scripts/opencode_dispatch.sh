#!/bin/bash
# opencode派发带重试+backoff
# 用法: ./opencode_dispatch.sh "任务提示词" "日志文件名" [最大重试次数]

TASK="$1"
LOGFILE="$2"
MAX_RETRIES="${3:-5}"
PORT=4096
URL="http://127.0.0.1:$PORT"
OPENCODE_BIN="$HOME/.opencode/bin/opencode"

# 检查serve是否在跑
if ! curl -s "$URL/api/health" >/dev/null 2>&1; then
    echo "[$(date)] serve未启动，正在启动..." >> "$LOGFILE"
    opencode serve --port $PORT >> /tmp/opencode_serve.log 2>&1 &
    sleep 5
fi

for i in $(seq 1 $MAX_RETRIES); do
    echo "[$(date)] 第${i}次尝试" >> "$LOGFILE"
    $OPENCODE_BIN run --attach "$URL" -m opencode/step-5-preview-free "$TASK" >> "$LOGFILE" 2>&1
    EXIT=$?
    if [ $EXIT -eq 0 ]; then
        echo "[$(date)] 成功" >> "$LOGFILE"
        exit 0
    fi
    BACKOFF=$((i * 30))
    echo "[$(date)] 失败(exit=$EXIT)，${BACKOFF}s后重试" >> "$LOGFILE"
    sleep $BACKOFF
done
echo "[$(date)] 全部重试失败" >> "$LOGFILE"
exit 1
