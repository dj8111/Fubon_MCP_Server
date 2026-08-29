# 富邦證券 AI 投資助理 (Fubon Neo AI Investment Assistant)

[![Python Version](https://img.shields.io/badge/Python-3.10%2B%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Standard%20v1.0-purple.svg)](https://modelcontextprotocol.io/)
[![Fubon Neo API](https://img.shields.io/badge/Fubon%20API-Neo%20v2.2.9-005BAC.svg)](https://www.fubon.com/securities/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

本專案為專為**富邦證券 (Fubon Securities)** 打造之企業級 **Model Context Protocol (MCP) Server** 體系與視覺化 AI 投資助理工作台。依據**富邦新一代行情與交易 API (Fubon Neo API v2.2.9)** 規格與金融高資安治理架構設計，深度整合 **Claude Desktop**、**Cursor IDE** 與 **Google Antigravity**，提供智慧庫存損益分析、實質即時購買力防呆計算、Fugle 行情五檔監控、公開資訊觀測站 (MOPS) 研報及嚴格雙向 6 碼本機 OTP 人工核准下單機制。

---

## 🌟 核心特色與架構優勢

1. **🏛️ 雙軌環境無縫切換 (Dual-Mode Architecture)**：
   * **正式環境 (Production)**：直連富邦新一代 SDK (`fubon_neo`) 與憑證簽章，取得 100% 真實持股、交割款與行情。
   * **模擬/展示環境 (Simulation)**：在無憑證或非開盤時段提供高擬真全功能演繹，供策略回測與展示。
2. **⚡ 實質即時可用購買力防呆試算 (Anti-Default Settlement Engine)**：
   * 嚴格執行 `台北富邦銀行可用餘額 - 尚未交割之應付交割款項 (T+2) - 圈存預扣`，徹底杜絕違約交割風險。
3. **🛡️ 金融級硬性風控與 6 碼本機 OTP 挑戰 (Zero-Trust Security)**：
   * AI 助理僅能產生「交易草稿 (Order Draft)」，無法直接扣款下單。
   * 內建臺股六級 Tick Size 價格合法性、±10% 漲跌停限制與單筆/每日累計委託限額檢核。
   * 必須由使用者親自在本機輸入 CSPRNG 密碼學安全亂數產生的 6 碼 OTP 挑戰碼才可正式送單。
4. **📊 視覺化 Web 互動工作台 (Port 9600)**：
   * 富邦專屬深藍/霓虹青科技風格 (`#005BAC` + `#00F2FE`)。
   * 支援持股資產分佈圓餅圖 (Donut Chart)、即時五檔委託簿、分 K 走勢圖、智慧價格條件監測與緊急熔斷開關。

---

## 🚀 新手從 0 開始安裝與設定指南 (Step-by-Step)

### 步驟 1：確認 Python 環境 (建議 Python 3.10 ~ 3.12)
確認電腦已安裝 Python 3.10 或更高版本：
```bash
python --version
```

### 步驟 2：建立並啟用虛擬環境 (Virtual Environment)

在 Windows PowerShell 下執行：
```powershell
# 1. 建立虛擬環境
python -m venv venv

# 2. 啟用虛擬環境 (若遇腳本執行限制請先執行 Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
.\venv\Scripts\Activate.ps1
```

### 步驟 3：安裝專案核心依賴與 5 大 MCP 套件

```bash
# 1. 升級 pip 與安裝核心基礎依賴
python -m pip install --upgrade pip
pip install -r requirements.txt

# 2. 以 Editable 模式安裝 5 大 Monorepo 子模組
pip install -e packages/fubon-common-contracts
pip install -e packages/fubon-account-mcp
pip install -e packages/fubon-marketdata-mcp
pip install -e packages/fubon-trading-mcp
pip install -e packages/fubon-research-mcp
```

---

### 步驟 4：富邦 Neo API 憑證與 INI 設定檔教學 (正式環境連線必備)

若您要連線至富邦證券正式主機進行真實帳務查詢與交易下單，請依序完成以下憑證與設定檔配置：

#### 1. 取得與匯出軟體憑證 (`.pfx` / `.p12`)
* **申請憑證**：至富邦證券官網登入「電子下單憑證專區」或使用富邦 e 點通電腦版申請憑證。
* **匯出憑證**：
  1. 開啟 Windows「管理使用者憑證」(`certmgr.msc`) 或瀏覽器憑證管理員。
  2. 在「個人 > 憑證」中找到富邦證券憑證，按右鍵選擇「所有工作 > 匯出」。
  3. 選擇「**是，匯出私密金鑰**」，格式選擇 **PKCS #12 (`.PFX`)**，設定憑證保護密碼。
  4. 將匯出的檔案妥善放置於專屬目錄（例如：`C:\Dev\certs\fubon_cert.pfx`）。

#### 2. 配置 INI 設定檔 (`fubon_config.ini`) 或 `.env`
本專案支援使用 INI 設定檔或環境變數進行自動認證：

建立 **`fubon_config.ini`**（建議存放在專案根目錄）：
```ini
[FUBON]
# 富邦證券身分證字號 / 登入帳號
user_id = A123456789

# 富邦證券登入密碼
password = YourPasswordHere

# 軟體憑證絕對路徑 (.pfx 或 .p12)
cert_path = C:\Dev\certs\fubon_cert.pfx

# 憑證匯出時設定的保護密碼
cert_password = YourCertPasswordHere

# 運行環境 (production 代表正式環境, simulation 代表模擬展示)
env = production
```

或者使用 PowerShell 環境變數：
```powershell
$env:FUBON_ENV = "production"
$env:FUBON_USER_ID = "A123456789"
$env:FUBON_PASSWORD = "YourPasswordHere"
$env:FUBON_CERT_PATH = "C:\Dev\certs\fubon_cert.pfx"
$env:FUBON_CERT_PASSWORD = "YourCertPasswordHere"
```

---

> 💡 **【貼心提示：遇到任何設定問題？直接問 AI 助理！】**
> 
> 如果您在憑證匯出、路徑設定、INI 檔案配置或 API 開通上有任何不清楚的地方，**您完全不需要煩惱！請直接在對話框中向 AI 助理發問**，例如：
> * 🙋 *「請告訴我如何在 Windows 11 中匯出富邦證券 PFX 憑證？」*
> * 🙋 *「我的 fubon_config.ini 檔案應該放在哪裡？可以幫我生成範本嗎？」*
> * 🙋 *「請幫我測試富邦 SDK 登入與憑證是否有效」*
>
> AI 投資助理會一步一步耐心地引導您完成所有配置！

---

### 步驟 5：執行系統整合預檢 (Pre-Flight Check)

在啟動前，可透過預檢工具一秒確認全系統 5 大模組與本機 SQLite 資料庫狀態：

```bash
python scripts/preflight_check.py
```

或執行全套單元與端到端驗收測試：
```bash
pytest tests/ -v
```
*(看到 `passed` 代表所有模組功能 100% 準備就緒！)*

---

## 🎯 系統使用方式 (三大使用情境)

### 情境 1：視覺化 Web 互動工作台 (最推薦)

專為投資人打造的高質感儀表板，支援即時 K 線圖、庫存損益總表、資產配置圓餅圖、即時對話下單、風控審查與 OTP 彈窗驗證。

* **Windows 一鍵啟動**：直接雙擊 **`開啟富邦AI投資助理.bat`**
* **命令列啟動**：
  ```bash
  python run_gui.py
  ```
* 瀏覽器將自動開啟：`http://127.0.0.1:9600`
* 您可以直接在對話框輸入：
  * `查詢我的帳戶持股與損益`
  * `查看資產配置圓餅圖`
  * `查看 2881 富邦金即時五檔與 K 線圖`
  * `幫我監控 2881 價格 >= 75.00 元`
  * `我想在 72.50 元買進 1 張富邦金` ➜ 系統將啟動風控審核並彈出確認與 OTP 挑戰！

---

### 情境 2：串接至 Claude Desktop / Cursor / Antigravity (AI MCP Client)

若您想在 **Claude Desktop**、**Cursor IDE** 或 **Google Antigravity** 中讓 AI 具有富邦證券操作能力：

將專案根目錄的 `mcp_config.json` 內容加入至您的 Claude / Cursor 設定檔中（例如 `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "fubon-account": {
      "command": "python",
      "args": ["-m", "fubon_account_mcp.cli", "serve"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "FUBON_ENV": "production"
      }
    },
    "fubon-marketdata": {
      "command": "python",
      "args": ["-m", "fubon_marketdata_mcp.cli", "serve"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "FUBON_ENV": "production"
      }
    },
    "fubon-trading": {
      "command": "python",
      "args": ["-m", "fubon_trading_mcp.cli", "serve"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "FUBON_ENV": "production"
      }
    },
    "fubon-research": {
      "command": "python",
      "args": ["-m", "fubon_research_mcp.cli", "serve"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

重新啟動 Claude Desktop 後，您即可直接向 Claude 下達指令：
> *「請幫我查詢富邦金 (2881) 今日即時行情與委託五檔簿」*  
> *「請為我的持股部位做情境壓力測試，若台股大盤下跌 300 點損益會如何？」*

---

### 情境 3：CLI 命令列日常操作

每個子模組均提供獨立的 Command Line 指令工具：

```bash
# 1. 查詢個股即時行情
fubon-marketdata quote 2881

# 2. 查詢個股即時五檔委託簿
fubon-marketdata book 2881

# 3. 建立股價條件監控 (富邦金 >= 75.00 元)
fubon-marketdata monitor create --symbol 2881 --op GREATER_THAN_OR_EQUAL --price 75.00

# 4. 查詢帳務總覽與實質購買力
fubon-account summary

# 5. 查詢 T+0/1/2 待交割款明細
fubon-account settlement

# 6. 建立本機 SQLite 帳務快照
fubon-account snapshot create --note "今日盤後快照"

# 7. 產生個股 AI 研究與風險評估報告
fubon-research report 2881

# 8. 查詢交易風控狀態
fubon-trading status
```

---

## 🏛️ 專案目錄結構 (Monorepo)

```text
Fubon_MCP_Server/
├── packages/
│   ├── fubon-common-contracts/     # 共用資料契約、Pydantic v2 模型、SQLite DDL 與系統健檢
│   ├── fubon-account-mcp/          # 帳務持股、T+2 交割款試算、維持率與快照管理
│   ├── fubon-marketdata-mcp/       # Fugle REST 行情、即時五檔委託簿與條件監測引擎
│   ├── fubon-trading-mcp/          # 硬性風控、下單草稿審查、本機 6 碼 OTP 挑戰與 Kill-Switch
│   └── fubon-research-mcp/         # 公開資訊觀測站 (MOPS) 重大訊息、除權息與風險情境分析
├── gui/                            # 富邦科技風視覺化 Web 互動工作台前端與後端
│   ├── static/                     # HTML / CSS / JS 前端資源
│   └── server.py                   # 工作台 HTTP 服務與即時對話分派
├── scripts/                        # 系統整合預檢 (preflight_check) 與 IDE 同步腳本
├── tests/                          # 完整單元測試與端到端閉環測試 (E2E Test Suite)
├── data/                           # 本機 SQLite 帳務快照與事件儲存庫 (fubon_assistant.db)
├── run_gui.py                      # 一鍵啟動 Web 互動工作台
├── 開啟富邦AI投資助理.bat            # Windows 桌面一鍵啟動腳本
└── mcp_config.json                 # MCP Client (Claude / Cursor / IDE) 標準設定檔
```

---

## 🛡️ 安全合規與風控機制

本系統嚴格遵循金融級安全防護規範：
1. **多模組權限隔離**：研究分析與真實下單通道完全隔離，杜絕 Prompt Injection 觸發交易。
2. **三道防線硬性風控 (Hard Limits)**：
   * 單筆下單金額上限（預設 50 萬元）
   * 每日累計委託上限（預設 200 萬元）
   * 臺股六級 Tick Size 價格合法性與 ±10% 漲跌停價格檢核
   * 反向自成交與同向重複下單防呆機制
3. **本機 6 碼 OTP 挑戰**：任何正式交易必須由使用者親自在本機介面確認並輸入由 CSPRNG 生成的一次性驗證碼。
4. **一鍵緊急熔斷機制 (Kill-Switch)**：異常時隨時終止委託通道，守護資產安全。

---

## ❓ 常見問題排解 (FAQ)

### Q1: 啟動時出現 `ModuleNotFoundError: No module named 'fubon_common_contracts'`？
**解答**：請確認您已在啟用虛擬環境後，依照「步驟 3」執行 `pip install -e packages/fubon-common-contracts` 等指令將套件以 Editable 模式安裝至環境中。

### Q2: 在 Windows PowerShell 執行啟用指令出現「因為這個系統上已停用指令碼執行」？
**解答**：這是 Windows PowerShell 預設的安全限制。請在 PowerShell 執行：
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
然後重新執行 `.\venv\Scripts\Activate.ps1` 即可。

### Q3: Web 介面顯示「伺服器連接埠被佔用 (Port 9600 in use)」？
**解答**：表示您已有背景行程正在執行，您可以關閉舊的終端視窗，或在 `run_gui.py` 中修改 `PORT = 9600` 為其他連接埠。

---

## 📚 富邦證券官方 API 參考資源

* **富邦新一代行情與交易 API 技術文件**：[https://www.fubon.com/securities/](https://www.fubon.com/securities/)
* **富邦證券 Neo API SDK 開發者專區**：[https://www.fubon.com/securities/api/](https://www.fubon.com/securities/api/)
* **公開資訊觀測站 (MOPS)**：[https://mops.twse.com.tw/](https://mops.twse.com.tw/)

---

## 📄 License & Disclaimer

本專案依據 MIT License 開源發布。本系統所提供之分析、報價與下單建議僅供輔助決策與研究參考，使用者在進行實際金融交易時應自行審慎評估市場風險。
