import http.server
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# 設定環境
os.environ["FUBON_ENV"] = "production"

# Windows 終端編碼保護
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fubon_account_mcp.services.portfolio_service import PortfolioService
from fubon_account_mcp.services.snapshot_service import SnapshotService
from fubon_marketdata_mcp.services.market_service import MarketService
from fubon_research_mcp.services.research_service import ResearchService
from fubon_trading_mcp.services.trading_service import TradingService
from fubon_common_contracts.models.enums import OrderSide, OrderType, MarketSession

STATIC_DIR = Path(__file__).parent / "static"
SYNCED_MESSAGES = []
MESSAGES_LOCK = threading.Lock()
GLOBAL_MSG_COUNTER = 0

GLOBAL_LOGGED_IN = True
GLOBAL_ADAPTER = None

STOCK_NAMES = {
    "00403A": "主動統一升級50",
    "0050": "元大台灣50",
    "0052": "富邦科技",
    "0056": "元大高股息",
    "006208": "富邦台50",
    "00692": "富邦公司治理",
    "00713": "元大台灣高息低波",
    "00730": "富邦臺灣優質高息",
    "00878": "國泰永續高股息",
    "00900": "富邦特選高股息30",
    "00981A": "主動統一台灣高息",
    "2881": "富邦金",
    "2881C": "富邦金特別股丙",
    "2882": "國泰金",
    "2884": "玉山金",
    "2886": "兆豐金",
    "2887": "台新新光金控",
    "2891": "中信金",
    "8349A": "恒耀特別股甲",
    "2330": "台積電",
    "2454": "聯發科",
    "2317": "鴻海",
}


def get_time_greeting() -> str:
    """依當前時段產生繁體中文親切問候語"""
    now_hour = datetime.now().hour
    if 5 <= now_hour < 12:
        return "早安 ☀️"
    elif 12 <= now_hour < 14:
        return "午安 🍱"
    elif 14 <= now_hour < 18:
        return "下午好 ☕"
    elif 18 <= now_hour < 24:
        return "晚上好 🌙"
    else:
        return "夜深了 🌌"


portfolio_service = PortfolioService()
snapshot_service = SnapshotService(portfolio_service=portfolio_service)
market_service = MarketService()
research_service = ResearchService()
trading_service = TradingService(portfolio_service=portfolio_service, market_service=market_service)


class FubonDashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def _send_json(self, data: dict, status: int = 200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "SAMEORIGIN")

            # 安全防護：僅允許本機 127.0.0.1 與 localhost 來源，杜絕外部惡意網頁 CSRF 跨站讀取
            origin = self.headers.get("Origin", "")
            if origin and any(origin.startswith(h) for h in ["http://127.0.0.1", "http://localhost"]):
                self.send_header("Access-Control-Allow-Origin", origin)
            else:
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:9600")

            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def do_OPTIONS(self):
        self.send_response(200)
        origin = self.headers.get("Origin", "")
        if origin and any(origin.startswith(h) for h in ["http://127.0.0.1", "http://localhost"]):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:9600")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/portfolio":
            try:
                summary = portfolio_service.get_portfolio_summary()
                settle = portfolio_service.get_settlements()
                bank = portfolio_service.get_bank_balance()
                maint = portfolio_service.get_maintenance_ratio()
                greeting = get_time_greeting()

                res_data = {
                    "success": True,
                    "data": {
                        "summary": summary.model_dump(),
                        "settlement": settle.model_dump(),
                        "bank": bank.model_dump(),
                        "maintenance": maint.model_dump(),
                        "greeting": greeting,
                    }
                }
            except Exception as e:
                res_data = {"success": False, "error": str(e)}

            self._send_json(res_data)

        elif parsed.path.startswith("/api/quote"):
            params = urllib.parse.parse_qs(parsed.query)
            symbol = params.get("symbol", ["2881"])[0]
            try:
                quote = market_service.get_stock_quote(symbol)
                book = market_service.get_order_book(symbol)
                res_data = {"success": True, "data": {"quote": quote.model_dump(), "order_book": book}}
            except Exception as e:
                res_data = {"success": False, "error": str(e)}

            self._send_json(res_data)

        elif parsed.path.startswith("/api/kline"):
            params = urllib.parse.parse_qs(parsed.query)
            symbol = params.get("symbol", ["2881"])[0]
            candles = market_service.get_intraday_candles(symbol)
            self._send_json({"success": True, "data": candles})

        elif parsed.path == "/api/feed":
            with MESSAGES_LOCK:
                feed = list(SYNCED_MESSAGES[-30:])
            self._send_json({"success": True, "data": feed})

        elif parsed.path == "/api/status":
            stat = trading_service.get_status()
            self._send_json({"success": True, "data": stat})

        elif parsed.path == "/api/monitors":
            mons = market_service.list_all_monitors()
            self._send_json({"success": True, "data": mons})

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        global GLOBAL_MSG_COUNTER, GLOBAL_LOGGED_IN

        if parsed.path == "/api/sync_from_ide":
            with MESSAGES_LOCK:
                GLOBAL_MSG_COUNTER += 1
                msg_id = GLOBAL_MSG_COUNTER
                user_m = req_data.get("user_msg", "")
                port_d = req_data.get("portfolio")

                if (user_m and any(k in user_m.lower() for k in ["登入", "login", "連線富邦"])) or (port_d and port_d.get("account_ref")):
                    GLOBAL_LOGGED_IN = True
                elif user_m and any(k in user_m.lower() for k in ["登出", "logout", "中斷連線"]):
                    GLOBAL_LOGGED_IN = False

                entry = {
                    "id": msg_id,
                    "title": req_data.get("title", "AI 即時同步"),
                    "text": req_data.get("text", "") or req_data.get("ai_reply", ""),
                    "type": req_data.get("type", "assistant_reply"),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "user_msg": user_m,
                    "ai_reply": req_data.get("ai_reply"),
                    "action": req_data.get("action"),
                    "portfolio": port_d,
                }
                SYNCED_MESSAGES.append(entry)
                if len(SYNCED_MESSAGES) > 100:
                    SYNCED_MESSAGES.pop(0)

            self._send_json({"success": True, "id": msg_id})

        elif parsed.path == "/api/chat":
            msg = req_data.get("message", "").strip()
            reply, portfolio_data, action_intent = self._handle_chat_command(msg)

            with MESSAGES_LOCK:
                GLOBAL_MSG_COUNTER += 1
                entry = {
                    "id": GLOBAL_MSG_COUNTER,
                    "title": "對話紀錄",
                    "text": f"🙋 您: {msg}\n🤖 富邦AI: {reply}",
                    "type": "chat",
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "user_msg": msg,
                    "ai_reply": reply,
                    "action": action_intent,
                    "portfolio": portfolio_data,
                }
                SYNCED_MESSAGES.append(entry)
                if len(SYNCED_MESSAGES) > 100:
                    SYNCED_MESSAGES.pop(0)

            self._send_json({
                "success": True,
                "reply": reply,
                "portfolio": portfolio_data,
                "action": action_intent,
            })

        elif parsed.path == "/api/draft/create":
            try:
                draft = trading_service.create_order_draft(
                    symbol=req_data["symbol"],
                    side=OrderSide(req_data["side"]),
                    quantity_shares=int(req_data["quantity"]),
                    price_type=OrderType(req_data.get("price_type", "LIMIT")),
                    limit_price=req_data.get("limit_price"),
                )
                res = {"success": True, "data": draft}
            except Exception as e:
                res = {"success": False, "error": str(e)}

            self._send_json(res)

        elif parsed.path == "/api/draft/approve":
            try:
                challenge = trading_service.approve_order_draft(req_data["draft_id"])
                res = {"success": True, "data": challenge}
            except Exception as e:
                res = {"success": False, "error": str(e)}

            self._send_json(res)

        elif parsed.path == "/api/draft/submit":
            try:
                order_res = trading_service.submit_confirmed_order(
                    draft_id=req_data["draft_id"],
                    draft_hash=req_data["draft_hash"],
                    user_otp=req_data["user_otp"],
                )
                res = {"success": True, "data": order_res}
            except Exception as e:
                res = {"success": False, "error": str(e)}

            self._send_json(res)

        elif parsed.path == "/api/kill_switch":
            action = req_data.get("action", "activate")
            if action == "activate":
                res_data = trading_service.activate_kill_switch(reason=req_data.get("reason", "GUI 手動觸發"))
            else:
                trading_service.kill_switch.reset()
                res_data = {"status": "RESET", "message": "熔斷開關已重置"}

            self._send_json({"success": True, "data": res_data})

        else:
            self._send_json({"error": "Not Found"}, status=404)

    def _handle_chat_command(self, msg: str):
        """處理對話意圖，回傳 (文字回覆, 投資組合資料, 動作意圖)"""
        if not msg:
            return "您好！我是富邦證券 AI 投資助理，請告訴我您想查詢帳務、個股報價、研報分析或進行智慧委託監控。", None, None

        # 庫存 / 部位 / 帳務 / 損益
        if any(k in msg for k in ["庫存", "部位", "帳務", "損益", "持股", "圓餅圖", "資產配置", "分佈"]):
            try:
                summary = portfolio_service.get_portfolio_summary()
                rows_tbl = []
                for idx, p in enumerate(summary.positions, 1):
                    d_name = STOCK_NAMES.get(p.symbol, p.display_name or p.symbol)
                    pnl_color = "red" if not p.unrealized_pnl.startswith("-") else "green"
                    m_val = f"{Decimal(p.market_value):,.0f}"
                    rows_tbl.append(
                        f"| {idx} | **{p.symbol}** | {d_name} | {p.quantity_shares:,} 股 | NT$ {p.average_price} | **NT$ {p.current_price}** | NT$ {m_val} | <span style='color:{pnl_color}; font-weight:bold;'>{p.unrealized_pnl} ({p.unrealized_pnl_percent})</span> | {p.weight_percent} |"
                    )
                table_content = "\n".join(rows_tbl)

                pnl_tot_color = "red" if not summary.total_unrealized_pnl.startswith("-") else "green"
                reply = f"""### 📊 富邦證券正式環境 - 個人真實持股部位資產總表

* **帳戶代號**：`{summary.account_ref}`
* **股票總市值**：**NT$ {Decimal(summary.total_market_value):,.2f} 元**
* **投資總成本**：**NT$ {Decimal(summary.total_cost):,.2f} 元**
* **未實現總損益**：**<span style='color:{pnl_tot_color}; font-weight:bold;'>{summary.total_unrealized_pnl} ({summary.total_unrealized_pnl_percent})</span>**
* **持股總檔數**：{summary.position_count} 檔

| # | 代號 | 標的名稱 | 持有股數 | 平均成本 | 現價 | 部位市值 | 未實現損益 | 佔比 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
{table_content}
"""
                action_intent = {"type": "SHOW_PIE_CHART"} if any(k in msg for k in ["圓餅圖", "圖表", "比例", "分佈", "配置"]) else None
                return reply, summary.model_dump(), action_intent
            except Exception as e:
                return f"⚠️ **【未連線到富邦證券正式環境】** 帳務資料讀取失敗: {e}", None, None

        if "購買力" in msg or "交割" in msg or "餘額" in msg:
            power = trading_service.get_buying_power()
            reply = f"""### 🏛️ 富邦即時購買力防呆試算

* **台北富邦銀行可用餘額**：**NT$ {Decimal(power['available_bank_balance']):,.2f} 元**
* **尚未交割之應付扣款 (T+2)**：**-NT$ {Decimal(power['pending_settlement_payable']):,.2f} 元**
* ⚡ **實質即時可用購買力**：**NT$ {Decimal(power['net_buying_power']):,.2f} 元**

> 依富邦安全規範已完整預扣 T+2 待扣款，確保絕不發生違約交割。
"""
            return reply, None, None

        # 檢查是否含有代碼查詢報價或研報
        sym_match = re.search(r"\b(00\d{2,4}[A-Z]?|2881[A-Z]?|\d{4}[A-Z]?)\b", msg)
        if sym_match:
            sym = sym_match.group(1).upper()
            if any(k in msg for k in ["研報", "研究", "新聞", "公告", "財報"]):
                rep = research_service.generate_research_report(sym)
                anns = "\n".join([f"• [{a['date']}] {a['title']}" for a in rep.get("announcements", [])[:3]])
                fin_str = f"EPS: {rep['financials']['eps']} 元, 毛利率: {rep['financials']['gross_margin']}" if rep.get("financials") else "暫無財報指標"
                reply = f"""### 📑 【{rep.get('target_name', sym)} ({sym}) 富邦綜合研究分析】

* **最新財報指標**：{fin_str}

#### 📢 最新重大訊息 (公開資訊觀測站 MOPS)：
{anns}

> ⚠️ {rep.get('disclaimer', '本報告僅供投資研究參考，投資人應獨立判斷並自負投資風險。')}
"""
                return reply, None, None
            elif any(k in msg for k in ["K線", "走勢", "圖表", "技術圖", "k線"]):
                quote = market_service.get_stock_quote(sym)
                reply = f"""### 📈 【{quote.name} ({quote.symbol}) 富邦即時 K 線圖】

* **成交價**：**{quote.last_price} 元** ({quote.change}, {quote.change_percent}%)
* **開盤 / 最高 / 最低**：{quote.open} / {quote.high} / {quote.low}
* **成交量**：{quote.volume:,} 張
"""
                return reply, None, {"type": "SHOW_KLINE_CHART", "symbol": sym}
            else:
                quote = market_service.get_stock_quote(sym)
                reply = f"""### 📈 【{quote.name} ({quote.symbol}) 富邦即時行情】

* **成交價**：**{quote.last_price} 元** ({quote.change}, {quote.change_percent}%)
* **開盤**：{quote.open} | **最高**：{quote.high} | **最低**：{quote.low}
* **成交量**：{quote.volume:,} 張
* **買一 / 賣一**：{quote.bid_price_1} ({quote.bid_size_1}張) / {quote.ask_price_1} ({quote.ask_size_1}張)
"""
                return reply, None, None

        reply = f"""收到您的指令：「{msg}」。您可以嘗試：
1. 輸入「**查詢庫存損益**」或「**資產配置圓餅圖**」查看富邦帳戶部位與市值。
2. 輸入「**查詢實質購買力**」查看銀行可用餘額與 T+2 預扣試算。
3. 輸入「**2881 行情**」或「**2881 K線**」查看富邦金即時五檔與技術圖。
4. 輸入「**2881 研報**」查看公開資訊觀測站重大公告與財報評估。
5. 點擊右上方「**新增監控**」設定價格穿越條件自動預警。
"""
        return reply, None, None


def run_server(port: int = 9600):
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), FubonDashboardHandler)
    print(f"🚀 富邦證券 AI 投資助理工作台已在 http://127.0.0.1:{port} 啟動")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已停止")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9600
    run_server(port)
