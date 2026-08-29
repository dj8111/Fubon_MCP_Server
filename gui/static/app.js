let currentSymbol = "2881";
let currentDraft = null;
let currentChallenge = null;
let otpTimer = null;
let currentPortfolioData = null;
const chartInstances = {};

let lastSyncedMsgId = 0;

document.addEventListener("DOMContentLoaded", () => {
  initEvents();
  fetchPortfolio();
  startPolling();
});

function initEvents() {
  // 對話送出
  const btnSend = document.getElementById("btnSendChat");
  const chatInput = document.getElementById("chatInput");
  if (btnSend) btnSend.addEventListener("click", sendChat);
  if (chatInput) {
    chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendChat();
    });
  }

  // 對話快捷 Chip
  document.querySelectorAll(".chat-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      if (chatInput) {
        chatInput.value = chip.dataset.msg;
        sendChat();
      }
    });
  });

  // 清除對話
  const btnClear = document.getElementById("btnClearChat");
  if (btnClear) {
    btnClear.addEventListener("click", () => {
      const chat = document.getElementById("chatMessages");
      if (chat) {
        chat.innerHTML = `
          <div class="chat-bubble assistant">
            <div class="bubble-header">🤖 富邦證券 AI 投資助理</div>
            <div class="bubble-content">對話紀錄已清除。請問您想查詢帳務、個股報價、研報或進行交易？</div>
          </div>
        `;
      }
    });
  }

  // 熔斷開關
  const btnKill = document.getElementById("btnKillSwitch");
  if (btnKill) btnKill.addEventListener("click", toggleKillSwitch);

  // 重新整理
  const btnRefresh = document.getElementById("btnRefresh");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      fetchPortfolio();
      alert("✅ 帳務與連線狀態已重新同步！");
    });
  }

  // Modal 控制
  const btnModalClose = document.getElementById("btnModalClose");
  const btnCancelDraft = document.getElementById("btnCancelDraft");
  const btnApproveDraft = document.getElementById("btnApproveDraft");
  const btnConfirmSubmit = document.getElementById("btnConfirmSubmit");

  if (btnModalClose) btnModalClose.addEventListener("click", closeModal);
  if (btnCancelDraft) btnCancelDraft.addEventListener("click", closeModal);
  if (btnApproveDraft) btnApproveDraft.addEventListener("click", approveDraft);
  if (btnConfirmSubmit) btnConfirmSubmit.addEventListener("click", submitOrderWithOtp);
}

// HTML 跳脫防護 (防止 XSS 跨站腳本攻擊)
function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, function (m) {
    switch (m) {
      case '&': return '&amp;';
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '"': return '&quot;';
      case "'": return '&#39;';
      default: return m;
    }
  });
}

// 簡易 Markdown 轉換器 (具備 XSS 白名單防護，支援 Table、Header、Bold、Span 色彩、Quote)
function parseMarkdownToHtml(mdText) {
  if (!mdText) return "";

  // 1. 先處理特定的安全 span 色彩標籤 (富邦紅/綠損益標籤)
  let safeText = mdText.replace(/<span style='color:(red|green); font-weight:bold;'>(.*?)<\/span>/gi, '@@SPAN_$1@@$2@@ENDSPAN@@');
  
  // 2. 對其餘所有原始 HTML 字元進行安全跳脫
  safeText = escapeHtml(safeText);

  // 3. 還原安全色彩 span
  safeText = safeText.replace(/@@SPAN_(red|green)@@(.*?)@@ENDSPAN@@/gi, '<span class="pnl-color-$1" style="color: $1; font-weight: bold;">$2</span>');

  let html = safeText;

  // 4. 處理 Markdown Table
  const tableRegex = /((?:\|[^\n]+\|\r?\n)+)/g;
  html = html.replace(tableRegex, (match) => {
    const lines = match.trim().split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length < 2) return match;

    let headers = [];
    let rows = [];

    // Header
    const hLine = lines[0];
    if (hLine.startsWith("|") && hLine.endsWith("|")) {
      headers = hLine.slice(1, -1).split("|").map(h => h.trim());
    }

    // Body rows (skip separator line like |:---:|:---:|)
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      if (/^\|[-:\s|]+\|$/.test(line)) continue;
      if (line.startsWith("|") && line.endsWith("|")) {
        const cells = line.slice(1, -1).split("|").map(c => c.trim());
        rows.push(cells);
      }
    }

    if (headers.length === 0) return match;

    let tblHtml = `<div class="table-responsive"><table class="chat-md-table"><thead><tr>`;
    headers.forEach(h => {
      tblHtml += `<th>${parseInlineMarkdown(h)}</th>`;
    });
    tblHtml += `</tr></thead><tbody>`;

    rows.forEach(r => {
      tblHtml += `<tr>`;
      r.forEach(c => {
        tblHtml += `<td>${parseInlineMarkdown(c)}</td>`;
      });
      tblHtml += `</tr>`;
    });

    tblHtml += `</tbody></table></div>`;
    return tblHtml;
  });

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3 class="chat-h3">$1</h3>');
  html = html.replace(/^#### (.*$)/gim, '<h4 class="chat-h4">$1</h4>');

  // Blockquote
  html = html.replace(/^&gt; (.*$)/gim, '<blockquote class="chat-quote">$1</blockquote>');
  html = html.replace(/^> (.*$)/gim, '<blockquote class="chat-quote">$1</blockquote>');

  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Inline Code
  html = html.replace(/`([^`]+)`/g, '<code class="chat-code">$1</code>');

  // Line breaks
  html = html.replace(/\n/g, '<br>');

  return html;
}

function parseInlineMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

// 取得帳務與購買力
async function fetchPortfolio() {
  try {
    const res = await fetch("/api/portfolio");
    const json = await res.json();
    if (json.success) {
      const data = json.data;
      const s = data.summary;
      currentPortfolioData = s;
      
      const accRefEl = document.getElementById("accountRef");
      const greetingEl = document.getElementById("greetingText");
      if (accRefEl) accRefEl.innerText = s.account_ref;
      if (greetingEl) greetingEl.innerText = `${data.greeting} 歡迎使用富邦 AI 助理`;
    }
  } catch (err) {
    console.error("fetchPortfolio error:", err);
  }
}

// 繪製對話框內圓餅圖 (Donut Chart)
async function renderInlinePieChart(msgId, portfolio) {
  let targetPortfolio = portfolio || currentPortfolioData;
  if (!targetPortfolio || !targetPortfolio.positions) {
    try {
      const res = await fetch("/api/portfolio");
      const data = await res.json();
      if (data.success && data.data && data.data.summary) {
        targetPortfolio = data.data.summary;
        currentPortfolioData = targetPortfolio;
      }
    } catch (e) {
      console.error("Failed to fetch portfolio for pie chart", e);
    }
  }

  setTimeout(() => {
    const canvas = document.getElementById(`canvas_${msgId}`);
    if (!canvas || !targetPortfolio || !targetPortfolio.positions) return;

    const positions = targetPortfolio.positions;
    const labels = positions.slice(0, 8).map(p => `${p.symbol} ${p.display_name}`);
    const values = positions.slice(0, 8).map(p => parseFloat(p.market_value));
    
    const otherVal = positions.slice(8).reduce((acc, cur) => acc + parseFloat(cur.market_value), 0);
    if (otherVal > 0) {
      labels.push(`其他持股 (${positions.length - 8}檔)`);
      values.push(otherVal);
    }

    const colors = [
      "#005BAC", "#00F2FE", "#38ef7d", "#ff6b6b",
      "#fbbf24", "#f472b6", "#34d399", "#a78bfa", "#94a3b8"
    ];

    if (chartInstances[msgId]) {
      chartInstances[msgId].destroy();
    }

    if (window.Chart) {
      chartInstances[msgId] = new Chart(canvas, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: colors.slice(0, labels.length),
            borderWidth: 2,
            borderColor: "#0d192c",
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "right",
              labels: { color: "#e2e8f0", font: { size: 12, family: "Noto Sans TC" } }
            },
            title: {
              display: true,
              text: "📊 富邦持股部位資產分佈比重",
              color: "#00F2FE",
              font: { size: 14, weight: "bold" }
            }
          }
        }
      });
    }
  }, 100);
}

// 繪製對話框內 K 線走勢圖
async function renderInlineKlineChart(msgId, symbol) {
  try {
    const res = await fetch(`/api/kline?symbol=${symbol}`);
    const json = await res.json();
    if (!json.success || !json.data) return;

    setTimeout(() => {
      const canvas = document.getElementById(`canvas_${msgId}`);
      if (!canvas) return;

      const candles = json.data.slice(-20);
      const labels = candles.map(c => c.time ? c.time.slice(11, 16) : "");
      const prices = candles.map(c => parseFloat(c.close));

      if (chartInstances[msgId]) {
        chartInstances[msgId].destroy();
      }

      if (window.Chart) {
        chartInstances[msgId] = new Chart(canvas, {
          type: "line",
          data: {
            labels: labels,
            datasets: [{
              label: `${symbol} 即時分K收盤價`,
              data: prices,
              borderColor: "#00F2FE",
              backgroundColor: "rgba(0, 242, 254, 0.15)",
              fill: true,
              tension: 0.2,
              borderWidth: 2,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } },
              y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } }
            },
            plugins: {
              legend: { labels: { color: "#e2e8f0" } }
            }
          }
        });
      }
    }, 100);
  } catch (err) {
    console.error("renderInlineKlineChart error:", err);
  }
}

// 對話處理
async function sendChat() {
  const input = document.getElementById("chatInput");
  const msg = input ? input.value.trim() : "";
  if (!msg) return;

  const chatMessages = document.getElementById("chatMessages");
  const userMsgEl = document.createElement("div");
  userMsgEl.className = "chat-bubble user";
  userMsgEl.innerHTML = `<div class="bubble-content">${escapeHtml(msg)}</div>`;
  if (chatMessages) chatMessages.appendChild(userMsgEl);

  if (input) input.value = "";
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;

  // 辨識是否為下單指令 (如：買進 1 張富邦金、在 72.50 買進...)
  if (msg.includes("買進") || msg.includes("賣出")) {
    const side = msg.includes("買進") ? "BUY" : "SELL";
    const symMatch = msg.match(/(2881|2330|2454|0050|\d{4})/);
    const sym = symMatch ? symMatch[1] : "2881";
    currentSymbol = sym;
    openDraftModal(side);
    return;
  }

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    const json = await res.json();
    if (json.success && chatMessages) {
      const msgId = Date.now();
      const assistantMsgEl = document.createElement("div");
      assistantMsgEl.className = "chat-bubble assistant";

      let chartBox = "";
      if (json.action && json.action.type === "SHOW_PIE_CHART") {
        chartBox = `<div class="inline-chart-container"><canvas id="canvas_${msgId}"></canvas></div>`;
      } else if (json.action && json.action.type === "SHOW_KLINE_CHART") {
        chartBox = `<div class="inline-chart-container"><canvas id="canvas_${msgId}"></canvas></div>`;
      }

      assistantMsgEl.innerHTML = `
        <div class="bubble-header">🤖 富邦證券 AI 投資助理</div>
        <div class="bubble-content">${parseMarkdownToHtml(json.reply)}</div>
        ${chartBox}
      `;
      chatMessages.appendChild(assistantMsgEl);
      chatMessages.scrollTop = chatMessages.scrollHeight;

      if (json.action && json.action.type === "SHOW_PIE_CHART") {
        renderInlinePieChart(msgId, json.portfolio);
      } else if (json.action && json.action.type === "SHOW_KLINE_CHART") {
        renderInlineKlineChart(msgId, json.action.symbol || currentSymbol);
      }
    }
  } catch (err) {
    console.error("sendChat error:", err);
  }
}

// 開啟草稿 Modal
async function openDraftModal(side) {
  const price = prompt(`【富邦下單草稿】請確認 ${currentSymbol} 限價 (例: 72.50):`, "72.50");
  if (!price) return;
  const qty = prompt(`請輸入欲${side === 'BUY' ? '買進' : '賣出'} ${currentSymbol} 之股數 (需為 1,000 整數倍):`, "1000");
  if (!qty) return;

  try {
    const res = await fetch("/api/draft/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: currentSymbol,
        side: side,
        quantity: parseInt(qty),
        limit_price: price,
      }),
    });
    const json = await res.json();
    if (!json.success) {
      alert(`建立草稿失敗: ${json.error}`);
      return;
    }

    currentDraft = json.data;
    document.getElementById("draftDetailBox").innerHTML = `
      <p><strong>草稿編號:</strong> ${currentDraft.draft_id}</p>
      <p><strong>交易標的:</strong> ${currentDraft.symbol_name} (${currentDraft.symbol})</p>
      <p><strong>方向/股數:</strong> <span class="${side === 'BUY' ? 'price-up' : 'price-down'}">${currentDraft.side}</span> ${currentDraft.quantity_shares.toLocaleString()} 股</p>
      <p><strong>委託限價:</strong> NT$ ${currentDraft.limit_price} 元 (ROD 普通單)</p>
      <p><strong>預估金額:</strong> NT$ ${Number(currentDraft.estimated_amount).toLocaleString()} 元 (預估手續費 NT$ ${currentDraft.estimated_fee})</p>
      <p style="font-family: monospace; font-size: 0.75rem; color: #8b9bb4; margin-top: 6px;"><strong>Draft Hash:</strong> ${currentDraft.draft_hash.slice(0, 24)}...</p>
    `;

    const riskList = document.getElementById("riskChecksList");
    riskList.innerHTML = "";
    currentDraft.risk_checks.forEach(r => {
      riskList.innerHTML += `
        <div class="risk-check-item ${r.result === 'PASS' ? 'pass' : 'reject'}">
          ${r.result === 'PASS' ? '✅' : '❌'} [${r.check_code}] ${r.message}
        </div>
      `;
    });

    document.getElementById("otpAuthBox").style.display = "none";
    document.getElementById("btnApproveDraft").style.display = "inline-block";
    document.getElementById("draftModal").style.display = "flex";
  } catch (err) {
    alert(`系統異常: ${err.message}`);
  }
}

// 核准草稿並發行 OTP
async function approveDraft() {
  if (!currentDraft) return;
  try {
    const res = await fetch("/api/draft/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft_id: currentDraft.draft_id }),
    });
    const json = await res.json();
    if (!json.success) {
      alert(`核准失敗: ${json.error}`);
      return;
    }

    currentChallenge = json.data;
    document.getElementById("otpAuthBox").style.display = "block";
    document.getElementById("btnApproveDraft").style.display = "none";

    // 啟動 120 秒倒數計時
    let remain = 120;
    const cdEl = document.getElementById("otpCountdown");
    clearInterval(otpTimer);
    otpTimer = setInterval(() => {
      remain--;
      if (cdEl) cdEl.innerText = remain;
      if (remain <= 0) {
        clearInterval(otpTimer);
        alert("OTP 授權已逾期，請重新發行挑戰");
        closeModal();
      }
    }, 1000);

    // 如果後端有提供內部測試 OTP (展示模式)
    if (currentChallenge._test_otp) {
      document.getElementById("otpInput").value = currentChallenge._test_otp;
    }
  } catch (err) {
    alert(`核准異常: ${err.message}`);
  }
}

// 驗證 OTP 並送出委託
async function submitOrderWithOtp() {
  const otpVal = document.getElementById("otpInput").value.trim();
  if (!otpVal || otpVal.length !== 6) {
    alert("請輸入 6 碼數字 OTP 授權碼");
    return;
  }

  try {
    const res = await fetch("/api/draft/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        draft_id: currentDraft.draft_id,
        draft_hash: currentDraft.draft_hash,
        user_otp: otpVal,
      }),
    });
    const json = await res.json();
    if (!json.success) {
      alert(`委託送出失敗: ${json.error}`);
      return;
    }

    clearInterval(otpTimer);
    alert(`🎉 委託成功送出至富邦證券！\n委託單號: ${json.data.broker_order_no}\n狀態: ${json.data.status}`);
    closeModal();
    fetchPortfolio();
  } catch (err) {
    alert(`下單送單異常: ${err.message}`);
  }
}

function closeModal() {
  clearInterval(otpTimer);
  const modal = document.getElementById("draftModal");
  if (modal) modal.style.display = "none";
  currentDraft = null;
  currentChallenge = null;
}

// 切換緊急熔斷開關
async function toggleKillSwitch() {
  const btn = document.getElementById("btnKillSwitch");
  if (!btn) return;
  const isActive = btn.classList.contains("active");
  const action = isActive ? "reset" : "activate";
  const reason = isActive ? "" : prompt("請輸入啟動交易熔斷的原因:", "市場異常劇烈波動");
  if (!isActive && reason === null) return;

  try {
    const res = await fetch("/api/kill_switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action, reason: reason }),
    });
    const json = await res.json();
    if (json.success) {
      if (action === "activate") {
        btn.classList.add("active");
        btn.innerHTML = `<span class="icon">🔒</span> 熔斷鎖定 (唯讀)`;
        alert("⚠️ 富邦交易熔斷已啟動！系統目前鎖定為唯讀狀態，拒絕所有新委託單。");
      } else {
        btn.classList.remove("active");
        btn.innerHTML = `<span class="icon">🛑</span> 熔斷開關`;
        alert("交易熔斷已解除，恢復正常下單。");
      }
    }
  } catch (err) {
    console.error("toggleKillSwitch error:", err);
  }
}

// 定時拉取 IDE / 後端同步的對話消息 (自動同步對話)
function startPolling() {
  setInterval(pollFeed, 1500);
}

async function pollFeed() {
  try {
    const res = await fetch("/api/feed");
    const json = await res.json();
    if (json.success && Array.isArray(json.data)) {
      const chatMessages = document.getElementById("chatMessages");
      if (!chatMessages) return;
      let hasNew = false;

      json.data.forEach(item => {
        if (item.id > lastSyncedMsgId) {
          lastSyncedMsgId = item.id;
          hasNew = true;

          // 1. 如果有 user_msg 且不是本機剛剛輸入的
          if (item.user_msg && item.type !== "local_chat") {
            const userMsgEl = document.createElement("div");
            userMsgEl.className = "chat-bubble user";
            userMsgEl.innerHTML = `<div class="bubble-content">${escapeHtml(item.user_msg)}</div>`;
            chatMessages.appendChild(userMsgEl);
          }

          // 2. 助理訊息
          const text = item.ai_reply || item.text || "";
          if (text) {
            const msgId = item.id || Date.now();
            const assistantMsgEl = document.createElement("div");
            assistantMsgEl.className = "chat-bubble assistant";

            let chartBox = "";
            if (item.action && (item.action.type === "SHOW_PIE_CHART" || item.action.type === "SHOW_KLINE_CHART")) {
              chartBox = `<div class="inline-chart-container"><canvas id="canvas_${msgId}"></canvas></div>`;
            }

            assistantMsgEl.innerHTML = `
              <div class="bubble-header">🤖 富邦證券 AI 投資助理 <span style="font-size:0.75rem; color:#8b9bb4; font-weight:normal; margin-left:6px;">(${item.time || ''})</span></div>
              <div class="bubble-content">${parseMarkdownToHtml(text)}</div>
              ${chartBox}
            `;
            chatMessages.appendChild(assistantMsgEl);

            if (item.action && item.action.type === "SHOW_PIE_CHART") {
              renderInlinePieChart(msgId, item.portfolio);
            } else if (item.action && item.action.type === "SHOW_KLINE_CHART") {
              renderInlineKlineChart(msgId, item.action.symbol || "2881");
            }
          }
        }
      });

      if (hasNew) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }
    }
  } catch (e) {
    // silent
  }
}

