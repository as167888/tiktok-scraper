#!/bin/bash
# TikTok 数据抓取 + 飞书通知
# 使用前请重命名为 send_report.sh 并填入你的飞书应用凭证
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 飞书应用凭证（从飞书开放平台获取）
FEISHU_APP_ID="your_app_id"
FEISHU_APP_SECRET="your_app_secret"
FEISHU_OPEN_ID="your_open_id"
MSG_FILE=$(mktemp)

cleanup() { rm -f "$MSG_FILE"; }
trap cleanup EXIT

# 运行 main.py，过滤噪声，只保留摘要部分（从 ═══ 开始）
python3 main.py 2>&1 | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    sed -n '/═══════/,$p' | \
    grep -v '^$' > "$MSG_FILE"

# 添加报告头
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
{
    echo "[TikTok 数据报告 + AI 趋势分析] ${TIMESTAMP}"
    echo "----------------------------------------"
    cat "$MSG_FILE"
} > "${MSG_FILE}.tmp" && mv "${MSG_FILE}.tmp" "$MSG_FILE"

# 截断超长消息（飞书限制 ~20KB）
MAX_LEN=20000
ACTUAL_LEN=$(wc -c < "$MSG_FILE")
if [ "$ACTUAL_LEN" -gt "$MAX_LEN" ]; then
    head -c "$MAX_LEN" "$MSG_FILE" > "${MSG_FILE}.tmp"
    echo "" >> "${MSG_FILE}.tmp"
    echo "[消息过长已截断，完整日志: ${SCRIPT_DIR}/tracking_data.csv]" >> "${MSG_FILE}.tmp"
    mv "${MSG_FILE}.tmp" "$MSG_FILE"
fi

# 获取 access token
TOKEN=$(curl -s -X POST \
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
    -H 'Content-Type: application/json' \
    -d "{\"app_id\":\"${FEISHU_APP_ID}\",\"app_secret\":\"${FEISHU_APP_SECRET}\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

# 构建消息 JSON body
python3 -c "
import sys, json
msg_file = '$MSG_FILE'
open_id = '${FEISHU_OPEN_ID}'
with open(msg_file, 'r') as f:
    text = f.read()
body = {
    'receive_id': open_id,
    'msg_type': 'text',
    'content': json.dumps({'text': text}, ensure_ascii=False)
}
print(json.dumps(body, ensure_ascii=False))
" > "${MSG_FILE}.json"

# 发送到飞书
RESPONSE=$(curl -s -X POST \
    'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id' \
    -H "Authorization: Bearer ${TOKEN}" \
    -H 'Content-Type: application/json' \
    -d "@${MSG_FILE}.json")

echo "飞书发送结果: $(echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
code = d.get('code', -1)
msg_id = d.get('data', {}).get('message_id', 'N/A')
print(f'code={code}, msg_id={msg_id}')
")"
