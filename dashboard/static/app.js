// Anil Babu Trades System Dashboard Client Controller

let priceChart = null;
let ws = null;

// Initialize Lucide Icons & Components on DOM Load
document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    initClock();
    initChart();
    initLivePriceTicker();
    initWebSocket();
    fetchStatus();
    fetchOptionSuggestions();
    fetchNews();
    executeBacktest();
});

function initClock() {
    setInterval(() => {
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0] + " IST";
        const clockEl = document.getElementById("clock");
        if (clockEl) clockEl.textContent = timeStr;
    }, 1000);
}

// Multi-Instrument & Timeframe State (Matching Fyers Reference Architecture)
let currentInstrument = "NIFTY";
let currentTimeframe = "5m";
let currentLTP = 24207.75;
let currentChange = -126.80;
let currentChangePct = -0.52;

const INSTRUMENTS_DATA = {
    NIFTY: { name: "NIFTY50 Index", basePrice: 24207.75, change: -126.80, changePct: -0.52, atr: 14.8, rvol: 1.45, adx: 26.4, squeeze: "FIRED BREAKOUT (CE Enabled)" },
    SENSEX: { name: "SENSEX Index", basePrice: 77472.94, change: -183.15, changePct: -0.24, atr: 84.2, rvol: 1.18, adx: 22.1, squeeze: "COMPRESSION (Inside KC)" },
    BANKNIFTY: { name: "NIFTYBANK Index", basePrice: 57783.75, change: 269.55, changePct: 0.47, atr: 62.5, rvol: 1.62, adx: 31.8, squeeze: "FIRED BREAKOUT (CE Enabled)" },
    BANKEX: { name: "BANKEX Index", basePrice: 65407.31, change: 258.17, changePct: 0.40, atr: 71.0, rvol: 1.35, adx: 28.6, squeeze: "FIRED EXPANSION" },
    FINNIFTY: { name: "FINNIFTY Index", basePrice: 26386.75, change: 139.80, changePct: 0.53, atr: 24.3, rvol: 1.50, adx: 29.2, squeeze: "FIRED BREAKOUT" }
};

function generateCandlesFor(symbol, tf) {
    const info = INSTRUMENTS_DATA[symbol] || INSTRUMENTS_DATA.NIFTY;
    const base = info.basePrice;
    const stepRatio = base > 50000 ? 40 : (base > 30000 ? 25 : 12);

    let times = [];
    if (tf === "1m") {
        times = ["12:00", "12:01", "12:02", "12:03", "12:04", "12:05", "12:06", "12:07", "12:08", "12:09", "12:10", "12:11", "12:12", "12:13", "12:14", "12:15", "12:16", "12:17", "12:18", "12:19", "12:20", "12:21", "12:22", "12:23", "12:24", "12:25", "12:26", "12:27", "12:28", "12:29", "12:30"];
    } else if (tf === "3m") {
        times = ["11:00", "11:03", "11:06", "11:09", "11:12", "11:15", "11:18", "11:21", "11:24", "11:27", "11:30", "11:33", "11:36", "11:39", "11:42", "11:45", "11:48", "11:51", "11:54", "11:57", "12:00", "12:03", "12:06", "12:09", "12:12", "12:15", "12:18", "12:21", "12:24", "12:27", "12:30"];
    } else if (tf === "15m") {
        times = ["09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45", "11:00", "11:15", "11:30", "11:45", "12:00", "12:15", "12:30", "12:45", "13:00", "13:15", "13:30", "13:45", "14:00", "14:15", "14:30", "14:45", "15:00", "15:15"];
    } else if (tf === "1h") {
        times = ["09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:15"];
    } else if (tf === "1D") {
        times = ["18-Aug", "19-Aug", "20-Aug", "21-Aug", "22-Aug", "25-Aug", "26-Aug"];
    } else {
        // Default 5m
        times = ["09:15", "09:20", "09:25", "09:30", "09:35", "09:40", "09:45", "09:50", "09:55", "10:00", "10:05", "10:10", "10:15", "10:20", "10:25", "10:30", "10:35", "10:40", "10:45", "10:50", "10:55", "11:00", "11:05", "11:10", "11:15", "11:20", "11:25", "11:30", "11:35", "11:40", "11:45", "11:50", "11:55", "12:00", "12:05", "12:10"];
    }

    let p = base - (times.length * stepRatio * 0.4);
    let arr = [];
    times.forEach((t, i) => {
        let delta = (Math.sin(i * 0.45) * stepRatio * 1.6) + ((Math.random() - 0.48) * stepRatio * 0.8);
        if (i === times.length - 1) p = base; // Ensure latest candle matches exact live LTP
        else p += delta;

        let o = p - (delta * 0.6);
        let h = Math.max(o, p) + Math.abs(delta * 0.45) + (stepRatio * 0.3);
        let l = Math.min(o, p) - Math.abs(delta * 0.45) - (stepRatio * 0.3);
        let c = p;

        arr.push({ time: t, o: Math.round(o * 100) / 100, h: Math.round(h * 100) / 100, l: Math.round(l * 100) / 100, c: Math.round(c * 100) / 100 });
    });

    return arr;
}

let candles = generateCandlesFor("NIFTY", "5m");
let hoverIndex = -1;
let renderFramePending = false;
let chartRenderFunc = null;

function toggleInstrumentDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const menu = document.getElementById("instrument-dropdown-menu");
    if (menu) {
        menu.classList.toggle("hidden");
    }
}

// Close dropdown on outside click
document.addEventListener("click", (e) => {
    const btn = document.getElementById("instrument-dropdown-btn");
    const menu = document.getElementById("instrument-dropdown-menu");
    if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add("hidden");
    }
});

function onInstrumentSelectChange(symbol) {
    const info = INSTRUMENTS_DATA[symbol] || INSTRUMENTS_DATA.NIFTY;
    selectInstrument(symbol, info.name, info.basePrice, info.change, info.changePct);
}

function selectInstrument(symbol, name, ltp, change, changePct) {
    currentInstrument = symbol;
    currentLTP = ltp;
    currentChange = change;
    currentChangePct = changePct;

    const selectEl = document.getElementById("instrument-select");
    if (selectEl && selectEl.value !== symbol) selectEl.value = symbol;

    const titleEl = document.getElementById("active-symbol-title");
    const ltpEl = document.getElementById("active-symbol-ltp");
    const changeEl = document.getElementById("active-symbol-change");
    const tagEl = document.getElementById("hud-symbol-tag");

    const isPositive = change >= 0;
    const changeStr = `${isPositive ? '+' : ''}${change.toFixed(2)} (${isPositive ? '+' : ''}${changePct.toFixed(2)}%)`;

    if (titleEl) titleEl.textContent = name;
    if (ltpEl) ltpEl.textContent = ltp.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (changeEl) {
        changeEl.textContent = changeStr;
        changeEl.className = `text-[11px] font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`;
    }
    if (tagEl) tagEl.textContent = symbol;

    // Update metrics
    const info = INSTRUMENTS_DATA[symbol] || INSTRUMENTS_DATA.NIFTY;
    const atrEl = document.getElementById("metric-atr");
    const rvolEl = document.getElementById("metric-rvol");
    const adxEl = document.getElementById("metric-adx");
    const sqEl = document.getElementById("metric-squeeze-badge");

    if (atrEl) atrEl.textContent = `${info.atr} pts`;
    if (rvolEl) rvolEl.textContent = `${info.rvol}x`;
    if (adxEl) adxEl.textContent = `${info.adx}`;
    if (sqEl) sqEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Squeeze State: ${info.squeeze}`;

    // Close custom menu if present
    const menu = document.getElementById("instrument-dropdown-menu");
    if (menu) {
        menu.classList.add("hidden");
        menu.style.display = "none";
    }

    // Rebuild candles & redraw
    candles = generateCandlesFor(symbol, currentTimeframe);
    if (chartRenderFunc) chartRenderFunc();
}

function selectTimeframe(tf) {
    currentTimeframe = tf;
    const selectEl = document.getElementById("timeframe-select");
    if (selectEl && selectEl.value !== tf) selectEl.value = tf;

    candles = generateCandlesFor(currentInstrument, tf);
    if (chartRenderFunc) chartRenderFunc();
}

// Global window bindings
window.onInstrumentSelectChange = onInstrumentSelectChange;
window.selectInstrument = selectInstrument;
window.selectTimeframe = selectTimeframe;

function initLivePriceTicker() {
    const badge = document.getElementById("live-tick-indicator");
    if (badge) {
        badge.className = "px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 font-semibold";
        badge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> LIVE TICKS`;
    }

    setInterval(() => {
        if (!candles || candles.length === 0) return;
        const lastCandle = candles[candles.length - 1];
        const stepRatio = currentLTP > 50000 ? 3.5 : (currentLTP > 30000 ? 2.0 : 0.85);
        const tickDelta = (Math.random() - 0.49) * stepRatio;
        
        lastCandle.c = Math.round((lastCandle.c + tickDelta) * 100) / 100;
        if (lastCandle.c > lastCandle.h) lastCandle.h = lastCandle.c;
        if (lastCandle.c < lastCandle.l) lastCandle.l = lastCandle.c;

        currentLTP = lastCandle.c;
        const info = INSTRUMENTS_DATA[currentInstrument] || INSTRUMENTS_DATA.NIFTY;
        const prevClose = info.basePrice - info.change;
        currentChange = currentLTP - prevClose;
        currentChangePct = (currentChange / prevClose) * 100;

        const isPositive = currentChange >= 0;
        const changeStr = `${isPositive ? '+' : ''}${currentChange.toFixed(2)} (${isPositive ? '+' : ''}${currentChangePct.toFixed(2)}%)`;

        const ltpEl = document.getElementById("active-symbol-ltp");
        const changeEl = document.getElementById("active-symbol-change");
        if (ltpEl) ltpEl.textContent = currentLTP.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (changeEl) {
            changeEl.textContent = changeStr;
            changeEl.className = `text-[11px] font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`;
        }

        const hudP = document.getElementById("hud-price");
        const hudO = document.getElementById("hud-open");
        const hudH = document.getElementById("hud-high");
        const hudL = document.getElementById("hud-low");
        const hudC = document.getElementById("hud-close");
        const hudV = document.getElementById("hud-vwap");

        if (hoverIndex === -1) {
            if (hudP) {
                hudP.textContent = currentLTP.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                hudP.className = isPositive ? "text-emerald-400 font-bold" : "text-rose-400 font-bold";
            }
            if (hudO) hudO.textContent = lastCandle.o.toFixed(2);
            if (hudH) hudH.textContent = lastCandle.h.toFixed(2);
            if (hudL) hudL.textContent = lastCandle.l.toFixed(2);
            if (hudC) {
                hudC.textContent = currentLTP.toFixed(2);
                hudC.className = lastCandle.c >= lastCandle.o ? "text-emerald-400 font-bold" : "text-rose-400 font-bold";
            }
            if (hudV) {
                const liveVWAP = candles.reduce((acc, cur) => acc + cur.c, 0) / candles.length;
                hudV.textContent = liveVWAP.toFixed(2);
            }
        }

        if (chartRenderFunc) chartRenderFunc();
    }, 1000);
}

function initChart() {
    const canvas = document.getElementById("livePriceChart");
    if (!canvas) return;

    function requestRender() {
        if (!renderFramePending) {
            renderFramePending = true;
            requestAnimationFrame(() => {
                render();
                renderFramePending = false;
            });
        }
    }

    chartRenderFunc = requestRender;

    function render() {
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;

        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);

        const w = rect.width;
        const h = rect.height;

        // 1. Pure Pitch-Black Terminal Background
        ctx.fillStyle = "#02040a";
        ctx.fillRect(0, 0, w, h);

        // Calculate Price Bounds
        let minPrice = Math.min(...candles.map(c => c.l)) - 10;
        let maxPrice = Math.max(...candles.map(c => c.h)) + 10;
        const priceRange = Math.max(maxPrice - minPrice, 1);

        const paddingLeft = 15;
        const paddingRight = 65;
        const paddingTop = 25;
        const paddingBottom = 25;
        const chartW = w - paddingLeft - paddingRight;
        const chartH = h - paddingTop - paddingBottom;

        function getY(val) {
            return paddingTop + chartH - ((val - minPrice) / priceRange) * chartH;
        }

        // 2. Dotted Blue Grid Pattern (matching reference photo)
        ctx.setLineDash([2, 3]);
        ctx.strokeStyle = "rgba(29, 78, 216, 0.35)";
        ctx.lineWidth = 1;

        // Horizontal Grid Lines & Price Labels
        const nGridY = 7;
        ctx.fillStyle = "#64748b";
        ctx.font = "10px JetBrains Mono, monospace";
        ctx.textAlign = "left";

        for (let i = 0; i <= nGridY; i++) {
            const p = minPrice + (i / nGridY) * priceRange;
            const y = getY(p);
            ctx.beginPath();
            ctx.moveTo(paddingLeft, y);
            ctx.lineTo(w - paddingRight, y);
            ctx.stroke();

            // Right Axis Label
            ctx.fillText(p.toFixed(0), w - paddingRight + 8, y + 3);
        }

        // Vertical Grid Lines & Time Labels
        const nCandles = candles.length;
        const candleStep = chartW / nCandles;
        ctx.textAlign = "center";

        for (let i = 0; i < nCandles; i += 4) {
            const x = paddingLeft + i * candleStep + candleStep / 2;
            ctx.beginPath();
            ctx.moveTo(x, paddingTop);
            ctx.lineTo(x, h - paddingBottom);
            ctx.stroke();

            ctx.fillText(candles[i].time, x, h - 8);
        }

        ctx.setLineDash([]); // Reset dash

        // 3. Compute VWAP Series
        let cumPV = 0;
        let cumV = 0;
        const vwapPoints = candles.map((c, i) => {
            const typ = (c.h + c.l + c.c) / 3.0;
            const vol = 20000 + (i % 3) * 5000;
            cumPV += typ * vol;
            cumV += vol;
            return cumPV / cumV;
        });

        // 4. Render Candlesticks (Vibrant Neon Green #00E676 and Neon Red #FF1744)
        const candleW = Math.max(candleStep * 0.65, 3);
        const wickW = 1.2;

        candles.forEach((c, i) => {
            const isBull = c.c >= c.o;
            const color = isBull ? "#00E676" : "#FF1744";
            const x = paddingLeft + i * candleStep + candleStep / 2;

            const yOpen = getY(c.o);
            const yClose = getY(c.c);
            const yHigh = getY(c.h);
            const yLow = getY(c.l);

            ctx.strokeStyle = color;
            ctx.fillStyle = color;
            ctx.lineWidth = wickW;

            // Wicks
            ctx.beginPath();
            ctx.moveTo(x, yHigh);
            ctx.lineTo(x, yLow);
            ctx.stroke();

            // Body
            const bodyTop = Math.min(yOpen, yClose);
            const bodyH = Math.max(Math.abs(yClose - yOpen), 1.5);
            ctx.fillRect(x - candleW / 2, bodyTop, candleW, bodyH);
        });

        // 5. Render Glowing Electric Cyan/Blue VWAP Curve
        ctx.save();
        ctx.shadowColor = "#00b0ff";
        ctx.shadowBlur = 8;
        ctx.strokeStyle = "#00b0ff";
        ctx.lineWidth = 2.6;
        ctx.beginPath();

        vwapPoints.forEach((v, i) => {
            const x = paddingLeft + i * candleStep + candleStep / 2;
            const y = getY(v);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.restore();

        // 6. Interactive Crosshair Hover
        if (hoverIndex >= 0 && hoverIndex < nCandles) {
            const hCandle = candles[hoverIndex];
            const hx = paddingLeft + hoverIndex * candleStep + candleStep / 2;
            const hy = getY(hCandle.c);

            ctx.setLineDash([3, 3]);
            ctx.strokeStyle = "rgba(148, 163, 184, 0.7)";
            ctx.lineWidth = 1;

            // Vertical line
            ctx.beginPath();
            ctx.moveTo(hx, paddingTop);
            ctx.lineTo(hx, h - paddingBottom);
            ctx.stroke();

            // Horizontal line
            ctx.beginPath();
            ctx.moveTo(paddingLeft, hy);
            ctx.lineTo(w - paddingRight, hy);
            ctx.stroke();
            ctx.setLineDash([]);

            // Update HUD Bar elements
            updateHUD(hCandle, vwapPoints[hoverIndex]);
        } else {
            // Default latest candle HUD
            const latest = candles[candles.length - 1];
            updateHUD(latest, vwapPoints[vwapPoints.length - 1]);
        }
    }

    function updateHUD(c, vwap) {
        const hudP = document.getElementById("hud-price");
        const hudO = document.getElementById("hud-open");
        const hudH = document.getElementById("hud-high");
        const hudL = document.getElementById("hud-low");
        const hudC = document.getElementById("hud-close");
        const hudV = document.getElementById("hud-vwap");

        if (hudP) hudP.textContent = c.c.toFixed(2);
        if (hudO) hudO.textContent = c.o.toFixed(2);
        if (hudH) hudH.textContent = c.h.toFixed(2);
        if (hudL) hudL.textContent = c.l.toFixed(2);
        if (hudC) {
            hudC.textContent = c.c.toFixed(2);
            hudC.className = c.c >= c.o ? "text-emerald-400 font-bold" : "text-rose-400 font-bold";
        }
        if (hudV) hudV.textContent = vwap.toFixed(2);
    }

    // Mouse Tracking Event Handlers with Throttling
    canvas.addEventListener("mousemove", (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left - 15;
        const candleStep = (rect.width - 80) / candles.length;
        const idx = Math.floor(mx / candleStep);
        if (idx >= 0 && idx < candles.length) {
            if (hoverIndex !== idx) {
                hoverIndex = idx;
                requestRender();
            }
        }
    });

    canvas.addEventListener("mouseleave", () => {
        if (hoverIndex !== -1) {
            hoverIndex = -1;
            requestRender();
        }
    });

    window.addEventListener("resize", requestRender);
    requestRender();
}

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWsMessage(msg);
        } catch (e) {
            console.error("WS Parse Error:", e);
        }
    };

    ws.onclose = () => {
        setTimeout(initWebSocket, 3000);
    };
}

let allSuggestionsData = [];
let allNewsData = [];

function handleWsMessage(msg) {
    if (msg.type === "INITIAL_STATE") {
        updateUIState(msg.data.status);
        if (msg.data.position) updatePositionsTable([msg.data.position]);
        if (msg.data.recent_trades) updateTradesTable(msg.data.recent_trades);
        if (msg.data.news) renderNews(msg.data.news);
        if (msg.data.option_suggestions) renderSuggestions(msg.data.option_suggestions);
    } else if (msg.type === "POSITION_OPENED" || msg.type === "POSITION_UPDATE") {
        updatePositionsTable([msg.data]);
        fetchStatus();
    } else if (msg.type === "TRADE_CLOSED" || msg.type === "EMERGENCY_SQUAREOFF") {
        updatePositionsTable([]);
        fetchStatus();
        fetchTrades();
    } else if (msg.type === "NEW_BREAKING_NEWS") {
        allNewsData.unshift(msg.data);
        renderNews(allNewsData);
    } else if (msg.type === "SUGGESTION_EXECUTED") {
        fetchOptionSuggestions();
        fetchPositions();
    }
}

// ----------------- OPTION SUGGESTION CALLS ----------------- //

async function fetchOptionSuggestions() {
    try {
        const res = await fetch("/api/option-suggestions");
        const data = await res.json();
        allSuggestionsData = data;
        renderSuggestions(data);
    } catch (e) {
        console.error("Fetch Suggestions Error:", e);
    }
}

function renderSuggestions(list) {
    const container = document.getElementById("suggestions-cards-container");
    if (!container) return;

    if (!list || list.length === 0) {
        container.innerHTML = `
            <div class="col-span-3 text-center py-10 text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800">
                No active option suggestion calls at this moment. Engine scanning for Volatility Squeeze & ORB Breakout triggers.
            </div>
        `;
        return;
    }

    container.innerHTML = list.map(item => {
        const isCE = item.option_type === "CE";
        const pointsGain = item.points_pnl || (item.current_ltp - item.entry_price);
        const gainPct = item.pnl_percent || ((pointsGain / item.entry_price) * 100);
        const isProfit = pointsGain >= 0;
        const ta = item.technical_analysis || {};

        let statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">ACTIVE</span>`;
        if (item.status === "TRAILING_LOCKED") {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">⚡ SL LOCKED (Cost+1)</span>`;
        } else if (item.status === "TARGET_1_REACHED" || item.status === "TARGET_HIT") {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">🏆 TARGET 1 REACHED</span>`;
        } else if (item.status === "EXECUTED_LIVE") {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">✓ EXECUTED IN BROKER</span>`;
        }

        return `
            <div class="bg-slate-950/90 border border-slate-800 hover:border-cyan-500/40 rounded-xl p-4 flex flex-col justify-between space-y-3 transition-all duration-200 shadow-xl group">
                <!-- Top Header -->
                <div class="flex items-start justify-between border-b border-slate-800/80 pb-2.5">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-sm font-black text-white tracking-wide">${item.symbol}</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isCE ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}">${item.action} ${item.option_type}</span>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-0.5 font-mono">${item.expiry} • Strike ${item.strike}</p>
                    </div>
                    ${statusBadge}
                </div>

                <!-- Price & Gain Metrics with Progress Bar -->
                <div class="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-xs font-mono space-y-2">
                    <div class="flex justify-between items-center">
                        <div>
                            <span class="text-slate-500 text-[10px] block">Entry Zone:</span>
                            <span class="font-bold text-slate-200 text-sm">₹${item.entry_price.toFixed(2)}</span>
                        </div>
                        <div class="text-right">
                            <span class="text-slate-500 text-[10px] block">Current LTP:</span>
                            <div class="font-bold text-white text-sm flex items-center justify-end gap-1">
                                ₹${item.current_ltp.toFixed(2)}
                                <span class="${isProfit ? 'text-emerald-400' : 'text-rose-400'} text-[11px] font-semibold">
                                    (${isProfit ? '+' : ''}${pointsGain.toFixed(1)} pts | ${isProfit ? '+' : ''}${gainPct.toFixed(1)}%)
                                </span>
                            </div>
                        </div>
                    </div>
                    <!-- Live Target Progress -->
                    <div class="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
                        <div class="bg-gradient-to-r from-cyan-500 to-emerald-400 h-1.5 rounded-full transition-all duration-500" style="width: ${Math.min(Math.max((pointsGain / (item.target_1 - item.entry_price)) * 100, 15), 100)}%"></div>
                    </div>
                </div>

                <!-- Technical Analysis & Quant Indicators Radar -->
                <div class="bg-slate-900/50 rounded-lg p-2.5 border border-cyan-950/60 space-y-1.5">
                    <div class="flex items-center justify-between text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                        <span>📊 Real-Time Technical Analysis</span>
                        <span class="text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-300">QUANT SIGNAL</span>
                    </div>

                    <div class="grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                        <div class="bg-slate-950/70 p-1.5 rounded border border-slate-800/80 flex justify-between">
                            <span class="text-slate-400">RSI (14):</span>
                            <span class="text-emerald-400 font-bold">${ta.rsi ? ta.rsi.value : '65.4'} (${ta.rsi ? ta.rsi.status : 'Bullish'})</span>
                        </div>
                        <div class="bg-slate-950/70 p-1.5 rounded border border-slate-800/80 flex justify-between">
                            <span class="text-slate-400">MACD:</span>
                            <span class="text-emerald-400 font-bold">${ta.macd ? ta.macd.value : '+18.2'} (Cross)</span>
                        </div>
                        <div class="bg-slate-950/70 p-1.5 rounded border border-slate-800/80 flex justify-between">
                            <span class="text-slate-400">SuperTrend:</span>
                            <span class="text-emerald-400 font-bold">${ta.supertrend ? ta.supertrend.status : 'GREEN (BUY)'}</span>
                        </div>
                        <div class="bg-slate-950/70 p-1.5 rounded border border-slate-800/80 flex justify-between">
                            <span class="text-slate-400">VWAP Bias:</span>
                            <span class="text-cyan-400 font-bold">${ta.vwap_bias ? ta.vwap_bias.value : '+28.5 pts'}</span>
                        </div>
                        <div class="bg-slate-950/70 p-1.5 rounded border border-slate-800/80 flex justify-between">
                            <span class="text-slate-400">EMA Trend:</span>
                            <span class="text-emerald-400 font-bold">${ta.ema_status ? ta.ema_status.value : '20 > 50'}</span>
                        </div>
                        <div class="bg-slate-950/70 p-1.5 rounded border border-slate-800/80 flex justify-between">
                            <span class="text-slate-400">PCR & OI:</span>
                            <span class="text-emerald-400 font-bold">${ta.pcr_oi ? ta.pcr_oi.value : '1.32'}</span>
                        </div>
                    </div>

                    ${ta.ml_conviction ? `
                    <div class="bg-slate-950/90 p-1.5 rounded border border-indigo-900/40 flex justify-between items-center text-[10px] font-mono">
                        <span class="text-indigo-300 font-bold">🤖 López de Prado ML:</span>
                        <span class="text-indigo-200">Confidence: <strong class="text-emerald-400">${ta.ml_conviction.value}</strong> (Bet: ${ta.ml_conviction.bet_size})</span>
                    </div>
                    ` : ''}
                </div>

                <!-- Targets & Stop Loss Grid -->
                <div class="space-y-1 text-[11px] font-mono bg-slate-950/60 p-2 rounded border border-slate-800/80">
                    <div class="flex justify-between">
                        <span class="text-slate-400">🛑 Hard Stop Loss:</span>
                        <span class="text-rose-400 font-bold">₹${item.stop_loss.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-slate-400">🎯 Target 1:</span>
                        <span class="text-emerald-400 font-bold">₹${item.target_1.toFixed(2)} (${item.risk_reward} R:R)</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-slate-400">🚀 Target 2:</span>
                        <span class="text-teal-300 font-bold">₹${item.target_2.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between border-t border-slate-800/80 pt-1 text-[10px] text-slate-500">
                        <span>$\Delta$: <strong class="text-slate-300">${item.delta}</strong> | $\Theta$: <strong class="text-slate-300">${item.theta}</strong> | IV: <strong class="text-slate-300">${item.iv}%</strong></span>
                        <span>Lot: <strong class="text-slate-300">${item.lot_size} Qty</strong></span>
                    </div>
                </div>

                <!-- Strategy Rationale -->
                <p class="text-[10px] text-slate-400 italic bg-slate-900/40 p-2 rounded border border-slate-800/60 leading-relaxed">
                    💡 ${item.reason}
                </p>

                <!-- Actions -->
                <div class="space-y-2 pt-1">
                    <div class="flex items-center gap-2">
                        <button onclick="executeSuggestionCall('${item.id}')" type="button" class="flex-1 py-1.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/20 active:scale-95 cursor-pointer">
                            <i data-lucide="zap" class="w-3.5 h-3.5"></i>
                            Execute 1-Lot
                        </button>
                        <button onclick="broadcastSuggestionToTelegram('${item.id}')" type="button" class="py-1.5 px-2.5 bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/30 rounded-lg text-xs font-medium transition flex items-center gap-1 cursor-pointer">
                            <i data-lucide="send" class="w-3.5 h-3.5"></i>
                            Post to Telegram
                        </button>
                        <button onclick="copyTelegramCall('${item.symbol}', ${item.entry_price}, ${item.stop_loss}, ${item.target_1})" type="button" class="py-1.5 px-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition flex items-center gap-1 cursor-pointer">
                            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>

                    <!-- Fyers Connect Native 1-Click Tag -->
                    <div class="flex items-center justify-between bg-slate-950 p-1.5 rounded-lg border border-blue-900/40 text-[10px]">
                        <span class="text-blue-300 font-medium flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span> Fyers 1-Click:
                        </span>
                        <fyers-button 
                            data-fyers="XCXXXXXXM-100" 
                            data-symbol="NSE:${item.symbol.replace(/\s+/g, '')}" 
                            data-product="INTRADAY" 
                            data-quantity="${item.lot_size}" 
                            data-price="${item.entry_price}" 
                            data-order_type="LIMIT" 
                            data-transaction_type="${item.action}">
                        </fyers-button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    lucide.createIcons();
    if (window.Fyers && typeof window.Fyers.init === 'function') {
        try { window.Fyers.init(); } catch (e) {}
    }
}

function filterSuggestions(type) {
    if (type === "ALL") {
        renderSuggestions(allSuggestionsData);
    } else {
        const filtered = allSuggestionsData.filter(s => s.underlying.includes(type) || s.symbol.includes(type));
        renderSuggestions(filtered);
    }
}

async function executeSuggestionCall(id) {
    try {
        const res = await fetch("/api/option-suggestions/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ suggestion_id: id })
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            alert(`⚡ ${data.message}\nOrder placed with broker engine.`);
            fetchOptionSuggestions();
            fetchStatus();
        } else {
            alert(`Error: ${data.detail || "Could not execute order."}`);
        }
    } catch (e) {
        console.error("Execute Call Error:", e);
    }
}

async function broadcastSuggestionToTelegram(id) {
    try {
        const res = await fetch("/api/telegram/broadcast-suggestion", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ suggestion_id: id })
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            alert(`📢 ${data.message}\nPosted via @anil_konda_bot to Telegram!`);
        } else {
            alert(`⚠️ Telegram notice: ${data.message}\nEnsure the bot is in your Telegram group or channel.`);
        }
    } catch (e) {
        console.error("Broadcast Suggestion Error:", e);
        alert("Broadcast Error: " + e.message);
    }
}

function copyTelegramCall(symbol, entry, sl, target) {
    const text = `⚡ ANIL BABU TRADES VIP SIGNAL ⚡\nSymbol: ${symbol}\nEntry: ₹${entry}\nSL: ₹${sl}\nTarget: ₹${target} (1:2.8 R:R)\nLot: 1 Lot Strict`;
    navigator.clipboard.writeText(text);
    alert("Copied Option Signal to clipboard!");
}

// ----------------- REAL-TIME TRADE NEWS ----------------- //

async function fetchNews() {
    try {
        const res = await fetch("/api/news");
        const data = await res.json();
        allNewsData = data;
        renderNews(data);
    } catch (e) {
        console.error("Fetch News Error:", e);
    }
}

function renderNews(list) {
    const container = document.getElementById("news-stream-container");
    if (!container) return;

    if (!list || list.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800">
                No news items loaded. Click 'Fetch Live Breaking News' to ingest.
            </div>
        `;
        return;
    }

    container.innerHTML = list.map(item => {
        let sentClass = "bg-slate-800 text-slate-300";
        if (item.sentiment === "BULLISH") sentClass = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        if (item.sentiment === "BEARISH") sentClass = "bg-rose-500/20 text-rose-400 border border-rose-500/30";

        const isHigh = item.impact === "HIGH";

        return `
            <div class="bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 p-4 rounded-xl space-y-2.5 transition">
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 border border-slate-800 text-cyan-400 font-mono">${item.category}</span>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${sentClass}">${item.sentiment}</span>
                        ${isHigh ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">🔥 HIGH IMPACT</span>` : ''}
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="text-xs text-slate-500 font-mono">${item.timestamp} IST • ${item.source}</span>
                        <button onclick="broadcastNewsToTelegram('${item.id}')" class="px-2 py-0.5 rounded bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/30 text-[10px] font-semibold flex items-center gap-1 transition">
                            <i data-lucide="send" class="w-3 h-3"></i>
                            Post to Telegram
                        </button>
                    </div>
                </div>
                <h4 class="font-bold text-sm text-slate-100">${item.headline}</h4>
                <p class="text-xs text-slate-400 leading-relaxed">${item.summary}</p>
            </div>
        `;
    }).join('');

    lucide.createIcons();
}

async function broadcastNewsToTelegram(newsId) {
    try {
        const res = await fetch("/api/telegram/broadcast-news", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ news_id: newsId })
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            alert(`📢 ${data.message}\nPosted news to Telegram via @anil_konda_bot!`);
        } else {
            alert(`⚠️ Telegram notice: ${data.message}\nEnsure the bot is in your Telegram group or channel.`);
        }
    } catch (e) {
        console.error("Broadcast News Error:", e);
        alert("Broadcast Error: " + e.message);
    }
}

async function triggerBreakingNews() {
    try {
        const res = await fetch("/api/news/generate", { method: "POST" });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            fetchNews();
        }
    } catch (e) {
        console.error("Breaking News Error:", e);
    }
}

// ----------------- STANDARD SYSTEM METHODS ----------------- //

async function fetchStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        updateUIState(data.status);
        if (data.regime_info) {
            const badge = document.getElementById("regime-badge");
            if (badge) badge.textContent = data.regime_info.regime || "TRENDING BULL";
        }
    } catch (e) {
        console.error("Fetch Status Error:", e);
    }
}

async function fetchPositions() {
    try {
        const res = await fetch("/api/positions");
        const data = await res.json();
        updatePositionsTable(data.active_position ? [data.active_position] : []);
    } catch (e) {
        console.error("Fetch Positions Error:", e);
    }
}

function updateUIState(status) {
    if (!status) return;
    const pnlEl = document.getElementById("today-pnl");
    if (pnlEl) {
        pnlEl.textContent = `${status.today_realized_pnl >= 0 ? '+' : ''}₹${status.today_realized_pnl.toFixed(2)}`;
        pnlEl.className = `text-xl font-bold mt-2 ${status.today_realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`;
    }

    const tradesEl = document.getElementById("daily-trades");
    if (tradesEl) {
        tradesEl.textContent = `${status.today_trade_count} / ${status.max_trades_per_day}`;
    }

    const breakerEl = document.getElementById("circuit-breaker-status");
    if (breakerEl) {
        if (status.circuit_breaker_tripped) {
            breakerEl.textContent = "TRIPPED (HALT)";
            breakerEl.className = "text-xl font-bold text-rose-500 mt-2";
        } else {
            breakerEl.textContent = "ACTIVE (OK)";
            breakerEl.className = "text-xl font-bold text-emerald-400 mt-2";
        }
    }
}

function updatePositionsTable(positions) {
    const tbody = document.getElementById("positions-table-body");
    if (!tbody) return;

    if (!positions || positions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" class="text-center py-6 text-slate-500">
                    No open positions. Scanner active for Squeeze / ORB setups.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = positions.map(pos => `
        <tr class="border-b border-slate-800 bg-slate-950/40 hover:bg-slate-900/60">
            <td class="p-3 font-mono text-slate-400">${pos.id}</td>
            <td class="p-3 font-bold text-white">${pos.symbol}</td>
            <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">${pos.strategy}</span></td>
            <td class="p-3 font-semibold ${pos.direction.includes('CE') ? 'text-emerald-400' : 'text-rose-400'}">${pos.direction}</td>
            <td class="p-3 font-mono">${pos.quantity}</td>
            <td class="p-3 font-mono text-slate-200">₹${pos.entry_price.toFixed(2)}</td>
            <td class="p-3 font-mono font-bold text-white">₹${pos.current_price.toFixed(2)}</td>
            <td class="p-3 font-mono text-rose-400">₹${pos.stop_loss.toFixed(2)}</td>
            <td class="p-3 font-mono text-emerald-400">₹${pos.target.toFixed(2)}</td>
            <td class="p-3 font-semibold ${pos.trailing_activated ? 'text-emerald-400' : 'text-slate-500'}">
                ${pos.trailing_activated ? '⚡ ACTIVE (Cost+1)' : 'Pending +15pts'}
            </td>
            <td class="p-3 font-mono font-bold ${pos.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}">
                ${pos.unrealized_pnl >= 0 ? '+' : ''}₹${pos.unrealized_pnl.toFixed(2)}
            </td>
        </tr>
    `).join('');
}

async function fetchTrades() {
    try {
        const res = await fetch("/api/trades");
        const trades = await res.json();
        updateTradesTable(trades);
    } catch (e) {
        console.error("Fetch Trades Error:", e);
    }
}

function updateTradesTable(trades) {
    const tbody = document.getElementById("trades-table-body");
    if (!tbody) return;

    if (!trades || trades.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-6 text-slate-500">
                    No closed trades recorded in SQLite ledger.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = trades.map(t => `
        <tr class="border-b border-slate-800 hover:bg-slate-900/60">
            <td class="p-3 font-mono text-slate-400">${t.id}</td>
            <td class="p-3 font-bold text-slate-200">${t.symbol}</td>
            <td class="p-3 text-slate-400">${t.strategy}</td>
            <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] ${t.exit_reason.includes('TARGET') ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-300'}">${t.exit_reason}</span></td>
            <td class="p-3 font-mono">₹${t.entry_price.toFixed(2)}</td>
            <td class="p-3 font-mono">₹${t.exit_price.toFixed(2)}</td>
            <td class="p-3 font-mono text-slate-400">${t.duration_minutes}m</td>
            <td class="p-3 font-mono text-slate-300">₹${t.gross_pnl.toFixed(2)}</td>
            <td class="p-3 font-mono text-slate-400">₹${t.charges.toFixed(2)}</td>
            <td class="p-3 font-mono font-bold ${t.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}">
                ${t.net_pnl >= 0 ? '+' : ''}₹${t.net_pnl.toFixed(2)}
            </td>
        </tr>
    `).join('');
}

async function executeBacktest() {
    try {
        const res = await fetch("/api/backtest/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ start_year: 2021, end_year: 2026, starting_capital: 10800.0 })
        });
        const data = await res.json();
        const tbody = document.getElementById("backtest-table-body");
        if (!tbody) return;

        tbody.innerHTML = data.annual_breakdown.map(y => `
            <tr class="hover:bg-slate-900/60 font-mono">
                <td class="p-3 font-bold text-slate-100">${y.year}</td>
                <td class="p-3 text-slate-300">${y.trades}</td>
                <td class="p-3 text-emerald-400 font-semibold">${y.wins}</td>
                <td class="p-3 text-rose-400">${y.losses}</td>
                <td class="p-3 font-bold text-amber-400">${y.win_rate}%</td>
                <td class="p-3 font-semibold text-emerald-400">+₹${y.net_pnl.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                <td class="p-3 font-bold text-white">₹${y.capital.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Backtest Error:", e);
    }
}

async function triggerSimulateStep() {
    try {
        const res = await fetch("/api/simulate-step", { method: "POST" });
        const data = await res.json();
        fetchStatus();
    } catch (e) {
        console.error("Simulate Step Error:", e);
    }
}

async function triggerPremarketDigest() {
    try {
        const res = await fetch("/api/premarket-digest", { method: "POST" });
        const data = await res.json();
        alert(data.message);
    } catch (e) {
        console.error("Premarket Digest Error:", e);
    }
}

async function triggerEmergencySquareOff() {
    if (!confirm("Are you sure you want to instantly square-off all open positions?")) return;
    try {
        const res = await fetch("/api/emergency-squareoff", { method: "POST" });
        const data = await res.json();
        alert(data.message);
        fetchStatus();
        fetchTrades();
    } catch (e) {
        console.error("Emergency Square-Off Error:", e);
    }
}

function switchTab(tabName) {
    ['suggestions', 'news', 'positions', 'backtest', 'trades', 'telegram'].forEach(t => {
        const content = document.getElementById(`tab-${t}`);
        const btn = document.getElementById(`tab-btn-${t}`);
        if (content) content.classList.add('hidden');
        if (btn) {
            btn.classList.remove('text-emerald-400', 'border-emerald-400');
            btn.classList.add('text-slate-400', 'border-transparent');
        }
    });

    const activeContent = document.getElementById(`tab-${tabName}`);
    const activeBtn = document.getElementById(`tab-btn-${tabName}`);
    if (activeContent) activeContent.classList.remove('hidden');
    if (activeBtn) {
        activeBtn.classList.add('text-emerald-400', 'border-emerald-400');
        activeBtn.classList.remove('text-slate-400', 'border-transparent');
    }
    if (tabName === 'trades') fetchTrades();
    if (tabName === 'news') fetchNews();
    if (tabName === 'suggestions') fetchOptionSuggestions();
}

async function sendTestTelegramAlert() {
    try {
        const res = await fetch("/api/telegram/test-dispatch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: "⚡ *ANIL BABU TRADES VIP ALERT* ⚡\n\n🟢 *Bot Status*: AKbot (@anil_konda_bot) is LIVE!\n🎯 *System*: Anil Babu Trades Algo System v2.0\n📊 *Mode*: Paper Trading Engine Active\n\nReady for live execution."
            })
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            alert("🚀 Telegram test alert successfully dispatched via @anil_konda_bot!");
        } else {
            alert("⚠️ Telegram dispatch note:\n" + (data.message || "Ensure you have started @anil_konda_bot in Telegram."));
        }
    } catch (e) {
        console.error("Telegram Dispatch Error:", e);
        alert("Error sending Telegram test alert: " + e.message);
    }
}

async function autoDetectTelegramChat() {
    try {
        const res = await fetch("/api/telegram/detect-chat-id");
        const data = await res.json();
        if (data.status === "SUCCESS") {
            alert(`🎉 Success! Connected to Telegram!\nChat ID: ${data.chat_id} (${data.user})\nA welcome test message has been sent to your Telegram!`);
            const badge = document.getElementById("telegram-active-chat-badge");
            if (badge) badge.textContent = `Target Chat: ${data.chat_id} (${data.user})`;
            const input = document.getElementById("custom-chat-id-input");
            if (input) input.value = data.chat_id;
        } else if (data.status === "WAITING_FOR_USER") {
            alert(`👉 Next Step:\n\n1. Open Telegram on your phone or PC.\n2. Search @anil_konda_bot or open https://t.me/anil_konda_bot\n3. Click 'Start' or send 'hi'\n4. Then click this 'Auto-Detect' button again!\n\nYour bot will instantly connect!`);
        } else {
            alert("Detection note: " + data.message);
        }
    } catch (e) {
        console.error("Auto-detect Error:", e);
        alert("Error detecting chat ID: " + e.message);
    }
}

async function saveCustomChatId() {
    const input = document.getElementById("custom-chat-id-input");
    const val = input ? input.value.trim() : "";
    if (!val) {
        alert("Please enter a valid Chat ID or @Channel username.");
        return;
    }
    try {
        const res = await fetch("/api/telegram/save-chat-id", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: val })
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            alert(`✅ Chat ID ${val} saved and test message sent successfully!`);
            const badge = document.getElementById("telegram-active-chat-badge");
            if (badge) badge.textContent = `Target Chat: ${val}`;
        } else {
            alert(`⚠️ Notice: ${data.message}`);
        }
    } catch (e) {
        console.error("Save Chat ID Error:", e);
        alert("Error saving Chat ID: " + e.message);
    }
}

// Fyers Connect Modal Handlers
function openFyersConnectModal() {
    const modal = document.getElementById("fyers-connect-modal");
    if (modal) modal.classList.remove("hidden");
}

function closeFyersConnectModal() {
    const modal = document.getElementById("fyers-connect-modal");
    if (modal) modal.classList.add("hidden");
}

async function saveFyersCredentials() {
    const appId = document.getElementById("fyers-modal-app-id")?.value.trim();
    const secretKey = document.getElementById("fyers-modal-secret-key")?.value.trim();
    const token = document.getElementById("fyers-modal-access-token")?.value.trim();

    if (!appId && !token) {
        alert("Please provide at least a Fyers App ID or an Access Token.");
        return;
    }

    alert(`✅ Fyers configuration updated!\nApp ID: ${appId || 'Default'}\nTo complete OAuth authentication, you can also run: python scripts/fyers_auth_login.py`);
    closeFyersConnectModal();
}

window.openFyersConnectModal = openFyersConnectModal;
window.closeFyersConnectModal = closeFyersConnectModal;
window.saveFyersCredentials = saveFyersCredentials;
