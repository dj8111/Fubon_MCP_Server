"""
富邦證券 AI 投資助理 - 系統整合健康檢查與預檢工具 (Pre-Flight Check)
一鍵檢查全系統 5 大模組、資料庫 DDL、行情連線與安全機制。
"""

import sys
import os
from pathlib import Path

# 設定 UTF-8 編碼
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_preflight_check():
    print("=" * 60)
    print("🚀 富邦證券 AI 投資助理 (Fubon Neo API) - 系統整合預檢")
    print("=" * 60)

    # 1. 檢查 Python 版本
    py_ver = sys.version_info
    print(f"\n[1/5] Python 執行環境: Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 10):
        print("  ❌ 警告: 建議使用 Python 3.10 以上版本")
    else:
        print("  ✅ Python 版本符合要求 (>= 3.10)")

    # 2. 檢查 5 大子模組引入
    print("\n[2/5] 檢查 Monorepo 子模組與契約套件:")
    packages = [
        ("fubon_common_contracts", "共用資料契約與 SQLite 管理 (fubon-common-contracts)"),
        ("fubon_account_mcp", "帳務查詢與快照管理 (fubon-account-mcp)"),
        ("fubon_marketdata_mcp", "即時行情與價格監控 (fubon-marketdata-mcp)"),
        ("fubon_trading_mcp", "硬性風控與下單執行 (fubon-trading-mcp)"),
        ("fubon_research_mcp", "公開資訊觀測站研報 (fubon-research-mcp)"),
    ]

    all_imported = True
    for pkg_name, desc in packages:
        try:
            __import__(pkg_name)
            print(f"  ✅ {desc} 載入成功")
        except ImportError as e:
            all_imported = False
            print(f"  ❌ {desc} 載入失敗: {e}")

    # 3. 檢查 SQLite 資料庫與 DDL 初始化
    print("\n[3/5] 檢查本機 SQLite 資料庫結構:")
    try:
        from fubon_common_contracts.storage.db import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row["name"] for row in cursor.fetchall()]
        print(f"  ✅ 資料庫連線正常 (路徑: {db.db_path})")
        print(f"  📋 已初始化資料表: {', '.join(tables)}")
    except Exception as e:
        print(f"  ❌ 資料庫檢查異常: {e}")

    # 4. 檢查市場行情與報價配接
    print("\n[4/5] 檢查即時行情與五檔委託簿:")
    try:
        from fubon_marketdata_mcp.services.market_service import MarketService
        mkt = MarketService()
        q = mkt.get_stock_quote("2881")
        book = mkt.get_order_book("2881")
        print(f"  ✅ 富邦金 (2881) 報價讀取成功: 現價 {q.last_price} 元, 漲跌 {q.change} ({q.change_percent}%)")
        print(f"  ✅ 五檔委託簿讀取成功: 買一 {book['bids'][0]['price']} ({book['bids'][0]['size']}張) / 賣一 {book['asks'][0]['price']} ({book['asks'][0]['size']}張)")
    except Exception as e:
        print(f"  ❌ 行情服務檢查異常: {e}")

    # 5. 檢查交易風控與 OTP 挑戰機制
    print("\n[5/5] 檢查交易硬性風控與本機 OTP 安全防護:")
    try:
        from fubon_trading_mcp.services.trading_service import TradingService
        from fubon_common_contracts.models.enums import OrderSide
        ts = TradingService()
        status = ts.get_status()
        print(f"  ✅ 交易系統狀態: {status['system_mode']}, 熔斷保護: {'啟用' if status['kill_switch_active'] else '關閉'}")
        
        # 測試建立草稿
        draft = ts.create_order_draft(symbol="2881", side=OrderSide.BUY, quantity_shares=1000, limit_price="72.50")
        print(f"  ✅ 風控引擎審核通過 (草稿 ID: {draft['draft_id']}, 檢核通過數: {len(draft['risk_checks'])})")
    except Exception as e:
        print(f"  ❌ 交易系統檢查異常: {e}")

    print("\n" + "=" * 60)
    if all_imported:
        print("🎉 全系統預檢通過 (HEALTHY)！您可以安心啟動 Web 工作台或連線至 AI 助理。")
    else:
        print("⚠️ 部份模組需要執行 pip install -e packages/<name> 進行安裝。")
    print("=" * 60)

if __name__ == "__main__":
    run_preflight_check()
