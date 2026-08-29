"""
富邦證券 AI 投資助理 - IDE 與 Web 工作台即時同步腳本 (Sync Draft / Events)
提供 IDE 插件或外部腳本向 Web 工作台推送通知、交易草稿與對話更新。
"""

import sys
import json
import urllib.request

def sync_to_gui(title: str, text: str, msg_type: str = "assistant_reply", port: int = 9600):
    url = f"http://127.0.0.1:{port}/api/sync_from_ide"
    payload = {
        "title": title,
        "text": text,
        "type": msg_type
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("success"):
                print(f"✅ 成功同步至富邦 Web 工作台 (ID: {res.get('id', 'ok')})")
            else:
                print(f"⚠️ 同步回應: {res}")
    except Exception as e:
        print(f"❌ 無法連線到富邦 Web 工作台 (Port {port}): {e}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        t = sys.argv[1]
        c = sys.argv[2]
        sync_to_gui(t, c)
    elif len(sys.argv) > 1:
        sync_to_gui("AI 投資助理通知", sys.argv[1])
    else:
        print("用法: python scripts/sync_draft.py <標題> <內容>")
