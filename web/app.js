/**
 * Jev AI Terminal Dashboard - Client Logic & WebSocket Handler
 */

let ws = null;
let isBotActive = true;

// Initialize TradingView Widget
function initTradingView() {
  if (typeof TradingView !== "undefined") {
    new TradingView.widget({
      "autosize": true,
      "symbol": "BINANCE:ARBUSDT",
      "interval": "5",
      "timezone": "Asia/Ho_Chi_Minh",
      "theme": "dark",
      "style": "1",
      "locale": "vi_VN",
      "toolbar_bg": "#0a0e17",
      "enable_publishing": false,
      "allow_symbol_change": false,
      "container_id": "tradingview_chart"
    });
  }
}

// WebSocket Setup
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("[Jev Terminal] Connected to bot WebSocket stream.");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateDashboard(data);
    } catch (e) {
      console.error("Error parsing WebSocket message:", e);
    }
  };

  ws.onclose = () => {
    console.warn("[Jev Terminal] WebSocket disconnected. Reconnecting in 3s...");
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error("[Jev Terminal] WebSocket error:", err);
    ws.close();
  };
}

// Update UI Elements with Live Telemetry
function updateDashboard(data) {
  if (!data) return;

  // 1. Ticker & Header
  if (data.ticker) {
    const t = data.ticker;
    const priceEl = document.getElementById("current-price");
    const changeEl = document.getElementById("price-change");

    if (t.price) priceEl.innerText = t.price.toFixed(4);
    if (t.percentage_24h !== undefined) {
      const isPos = t.percentage_24h >= 0;
      changeEl.innerText = `${isPos ? "+" : ""}${t.percentage_24h.toFixed(2)}%`;
      changeEl.style.color = isPos ? "var(--color-buy)" : "var(--color-sell)";
    }
  }

  // 2. Balance & Metrics
  if (data.balance) {
    const b = data.balance;
    document.getElementById("total-equity").innerText = `$${b.total_equity?.toLocaleString() || "1,000.00"}`;
    document.getElementById("usdt-free").innerText = `$${b.usdt_free?.toLocaleString() || "1,000.00"}`;
    document.getElementById("arb-holding").innerText = `${b.arb_free?.toFixed(2) || "0.00"} ARB`;
    document.getElementById("arb-value").innerText = `Trị giá: $${b.arb_value_usdt?.toFixed(2) || "0.00"} USDT`;

    const pnl = b.total_pnl || 0.0;
    const pnlPct = b.total_pnl_pct || 0.0;
    const pnlEl = document.getElementById("total-pnl");
    const isPnlPos = pnl >= 0;
    pnlEl.innerText = `PnL: ${isPnlPos ? "+" : ""}$${pnl.toFixed(2)} (${isPnlPos ? "+" : ""}${pnlPct.toFixed(2)}%)`;
    pnlEl.style.color = isPnlPos ? "var(--color-buy)" : "var(--color-sell)";

    // Mode Pill
    const modeBadge = document.getElementById("mode-badge");
    const modeText = document.getElementById("mode-text");
    modeText.innerText = b.mode === "LIVE" ? "LIVE BINANCE" : "PAPER TRADING";
    modeBadge.style.borderColor = b.mode === "LIVE" ? "rgba(244,63,94,0.4)" : "rgba(16,185,129,0.3)";
  }

  // 3. Jev AI Decision Core
  if (data.latest_decision) {
    const d = data.latest_decision;
    const actionEl = document.getElementById("jev-action");
    actionEl.innerText = d.action || "HOLD";
    actionEl.className = "decision-action " + (
      d.action === "BUY" ? "action-buy" : (d.action === "SELL" ? "action-sell" : "action-hold")
    );

    document.getElementById("jev-confidence").innerText = `${d.confidence || 0}%`;
    document.getElementById("jev-conf-fill").style.width = `${d.confidence || 0}%`;

    document.getElementById("jev-prob").innerText = d.action_prob !== undefined ? `p=${d.action_prob.toFixed(2)}` : "--";
    document.getElementById("jev-regime").innerText = d.regime || "RANGING";
    document.getElementById("jev-risk").innerText = d.risk_level || "MEDIUM";
    document.getElementById("jev-latency").innerText = `${d.latency_ms || 70} ms`;

    document.getElementById("jev-reasoning").innerText = d.reasoning || "Đang phân tích...";
    document.getElementById("brain-source").innerText = d.source || "jevai.org (System One)";
  }

  // 4. Indicators Grid
  if (data.indicators) {
    const ind = data.indicators;
    document.getElementById("ind-rsi").innerText = ind.rsi !== undefined ? ind.rsi : "--";
    document.getElementById("ind-macd").innerText = ind.macd_hist !== undefined ? ind.macd_hist.toFixed(5) : "--";
    document.getElementById("ind-atr").innerText = ind.atr !== undefined ? ind.atr.toFixed(4) : "--";
    document.getElementById("ind-ema").innerText = ind.trend || "NEUTRAL";
    document.getElementById("ind-vol").innerText = ind.volume_ratio ? `${ind.volume_ratio.toFixed(2)}x` : "1.0x";
  }

  if (data.order_book) {
    const ob = data.order_book;
    document.getElementById("ind-book").innerText = ob.bid_ask_ratio ? `${ob.bid_ask_ratio.toFixed(2)} (B/A)` : "--";
  }

  // 5. Active Position Card
  const posDetails = document.getElementById("pos-details");
  const posBadge = document.getElementById("pos-badge");
  if (data.open_position) {
    const p = data.open_position;
    const curP = data.ticker?.price || p.price;
    const pnlCash = (curP - p.price) * p.amount_arb;
    const pnlPercent = ((curP - p.price) / p.price) * 100;
    const isWin = pnlCash >= 0;

    posBadge.innerText = "LONG ĐANG MỞ";
    posBadge.style.background = "rgba(16, 185, 129, 0.2)";
    posBadge.style.color = "var(--color-buy)";

    posDetails.innerHTML = `
      <div class="pos-grid">
        <div>
          <div class="pos-item-title">GIÁ VÀO LỆNH</div>
          <div class="pos-item-val">${p.price.toFixed(4)} USDT</div>
        </div>
        <div>
          <div class="pos-item-title">KHỐI LƯỢNG ARB</div>
          <div class="pos-item-val">${p.amount_arb.toFixed(2)} ARB</div>
        </div>
        <div>
          <div class="pos-item-title">STOP LOSS (ĐỘNG)</div>
          <div class="pos-item-val" style="color: var(--color-sell)">${p.stop_loss.toFixed(4)}</div>
        </div>
        <div>
          <div class="pos-item-title">TAKE PROFIT</div>
          <div class="pos-item-val" style="color: var(--color-buy)">${p.take_profit.toFixed(4)}</div>
        </div>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
        <span style="font-size:12px; color:var(--text-dim)">LỢI NHUẬN CHƯA ĐÓNG:</span>
        <span style="font-size:16px; font-weight:800; font-family:var(--font-mono); color:${isWin ? 'var(--color-buy)' : 'var(--color-sell)'}">
          ${isWin ? '+' : ''}$${pnlCash.toFixed(2)} (${isWin ? '+' : ''}${pnlPercent.toFixed(2)}%)
        </span>
      </div>
    `;
  } else {
    posBadge.innerText = "CHƯA CÓ LỆNH";
    posBadge.style.background = "rgba(255, 255, 255, 0.06)";
    posBadge.style.color = "var(--text-muted)";
    posDetails.innerHTML = `<div class="empty-pos-hint">Hiện đang ở trạng thái trống vị thế. Jev AI đang quét tìm điểm vào lệnh tối ưu.</div>`;
  }

  // 6. AI Experience Memory & Lessons
  if (data.memory) {
    const mem = data.memory;
    const lessonsList = document.getElementById("lessons-list");
    const streakEl = document.getElementById("memory-streak");
    const shieldBadge = document.getElementById("adaptive-shield-badge");

    const losses = mem.stats?.consecutive_losses || 0;
    const wins = mem.stats?.consecutive_wins || 0;
    if (streakEl) {
      streakEl.innerText = losses > 0 ? `Chuỗi thua: ${losses}` : `Chuỗi thắng: ${wins}`;
    }

    if (data.adaptive_risk && shieldBadge) {
      const ar = data.adaptive_risk;
      shieldBadge.innerText = `PHÒNG THỦ: ${ar.status || 'BÌNH THƯỜNG'} (${ar.effective_risk_pct}%, Conf: ${ar.effective_min_confidence}%)`;
      if (ar.status && ar.status.includes("MAX")) {
        shieldBadge.className = "adaptive-shield-badge shield-danger";
      } else if (ar.status && ar.status.includes("MID")) {
        shieldBadge.className = "adaptive-shield-badge shield-warning";
      } else {
        shieldBadge.className = "adaptive-shield-badge";
      }
    }

    if (lessonsList) {
      if (mem.recent_lessons && mem.recent_lessons.length > 0) {
        lessonsList.innerHTML = mem.recent_lessons.map(l => {
          const isWin = l.is_win;
          const cardClass = isWin ? "lesson-card win-card" : "lesson-card loss-card";
          const pnlClass = isWin ? "win" : "loss";
          return `
            <div class="${cardClass}">
              <div class="lesson-top">
                <span class="lesson-cat">${l.category || (isWin ? 'THẮNG' : 'THUA')}</span>
                <span class="lesson-pnl ${pnlClass}">${isWin ? '+' : ''}${l.pnl_pct.toFixed(2)}%</span>
              </div>
              <div class="lesson-text">${l.lesson}</div>
              <div class="lesson-time">${l.date_str || ''}</div>
            </div>
          `;
        }).join("");
      } else {
        lessonsList.innerHTML = `<div class="lesson-empty">Chưa có bài học nào được ghi nhận. Jev AI sẽ tự động đúc kết kinh nghiệm sau mỗi lệnh đóng.</div>`;
      }
    }
  }

  // 7. Logs Console
  if (data.logs && data.logs.length > 0) {
    const logsBox = document.getElementById("logs-container");
    logsBox.innerHTML = data.logs.map(line => `<div class="log-row">${line}</div>`).join("");
  }

  // 7. Trade History Table
  if (data.trades) {
    const tbody = document.getElementById("trades-tbody");
    const trades = data.trades;
    document.getElementById("total-trades").innerText = `${trades.length} Lệnh`;

    // Calculate win rate
    const closedTrades = trades.filter(t => t.side === "SELL" && t.pnl !== undefined);
    const winningTrades = closedTrades.filter(t => t.pnl > 0);
    const winRate = closedTrades.length > 0 ? (winningTrades.length / closedTrades.length * 100).toFixed(1) : "0.0";
    document.getElementById("win-rate").innerText = `Tỷ lệ thắng: ${winRate}% (${winningTrades.length}/${closedTrades.length})`;

    if (trades.length > 0) {
      tbody.innerHTML = trades.slice().reverse().map(t => {
        const timeStr = new Date(t.timestamp).toLocaleTimeString();
        const sideColor = t.side === "BUY" ? "var(--color-buy)" : "var(--color-sell)";
        const pnlStr = t.pnl !== undefined ? `${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)} (${t.pnl_pct >= 0 ? '+' : ''}${t.pnl_pct.toFixed(2)}%)` : "--";
        const pnlColor = t.pnl !== undefined && t.pnl >= 0 ? "var(--color-buy)" : (t.pnl < 0 ? "var(--color-sell)" : "var(--text-muted)");

        return `
          <tr>
            <td>${timeStr}</td>
            <td>${t.symbol}</td>
            <td style="color:${sideColor}; font-weight:700;">${t.side}</td>
            <td>${t.price.toFixed(4)}</td>
            <td>${t.amount_arb.toFixed(2)}</td>
            <td>$${t.amount_usdt.toFixed(2)}</td>
            <td style="color:${pnlColor}; font-weight:700;">${pnlStr}</td>
            <td style="color:var(--text-dim); max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${t.reason || ''}">${t.reason || '--'}</td>
          </tr>
        `;
      }).join("");
    }
  }

  // 8. Bot State Button
  const btnToggle = document.getElementById("btn-toggle-bot");
  if (data.status === "ACTIVE") {
    isBotActive = true;
    btnToggle.innerHTML = `<span class="btn-icon">⏸</span><span class="btn-label">TẠM DỪNG</span>`;
    btnToggle.className = "btn btn-ghost";
  } else {
    isBotActive = false;
    btnToggle.innerHTML = `<span class="btn-icon">▶</span><span class="btn-label">BẬT BOT</span>`;
    btnToggle.className = "btn btn-primary";
  }
}

// Button Events
document.addEventListener("DOMContentLoaded", () => {
  initTradingView();
  connectWebSocket();

  // Toggle Bot
  document.getElementById("btn-toggle-bot").addEventListener("click", async () => {
    const url = isBotActive ? "/api/bot/stop" : "/api/bot/start";
    await fetch(url, { method: "POST" });
  });

  // Emergency Close All
  document.getElementById("btn-emergency-close").addEventListener("click", async () => {
    if (confirm("⚠️ BẠN CÓ CHẮC CHẮN MUỐN ĐÓNG TẤT CẢ VỊ THẾ ARB/USDT NGAY LẬP TỨC?")) {
      await fetch("/api/bot/emergency_close", { method: "POST" });
    }
  });

  // Settings Modal
  const modal = document.getElementById("settings-modal");
  document.getElementById("btn-open-settings").addEventListener("click", () => {
    modal.classList.add("show");
  });
  document.getElementById("btn-close-settings").addEventListener("click", () => {
    modal.classList.remove("show");
  });
  document.getElementById("btn-cancel-settings").addEventListener("click", () => {
    modal.classList.remove("show");
  });

  // Save Settings
  document.getElementById("btn-save-settings").addEventListener("click", async () => {
    const payload = {
      risk_per_trade_percent: parseFloat(document.getElementById("cfg-risk").value),
      min_jev_confidence: parseInt(document.getElementById("cfg-conf").value),
      atr_sl_multiplier: parseFloat(document.getElementById("cfg-sl").value),
      atr_tp_multiplier: parseFloat(document.getElementById("cfg-tp").value),
      trailing_stop_enabled: document.getElementById("cfg-trailing").checked
    };

    await fetch("/api/bot/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    modal.classList.remove("show");
    alert("Đã lưu cài đặt thành công!");
  });
});
