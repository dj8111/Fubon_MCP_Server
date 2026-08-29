import os
import subprocess
import sys
import threading
import time
import webbrowser

# 設定環境變數
os.environ["PYTHONIOENCODING"] = "utf-8"

# Windows 控制台編碼
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def open_browser():
    time.sleep(1.0)
    url = "http://127.0.0.1:9600"
    print(f"🌐 自動開啟瀏覽器工作台: {url}")
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer.exe", url])
        else:
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)


def main():
    threading.Thread(target=open_browser, daemon=True).start()
    from gui.server import run_server
    run_server(port=9600)


if __name__ == "__main__":
    main()
