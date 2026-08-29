import json
import urllib.request

SYNC_URL = "http://127.0.0.1:9600/api/sync_from_ide"


def push_to_gui(title: str, text: str, data_type: str = "assistant_reply"):
    """將 Antigravity / AI 產出的推論、研報或訂單草稿即時同步至富邦 GUI 工作台"""
    payload = {
        "title": title,
        "text": text,
        "type": data_type,
    }
    try:
        req = urllib.request.Request(
            SYNC_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            pass
    except Exception:
        pass
