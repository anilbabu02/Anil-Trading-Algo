(() => {
  'use strict';
  const LWC = window.LightweightCharts;

  // ==========================================================================
  // 1. CHART
  // ==========================================================================
  const root   = document.getElementById('abtChart');
  const canvas = document.getElementById('abtCanvas');
  const css    = (name) => getComputedStyle(root).getPropertyValue(name).trim();

  const C = {
    bg: css('--bg'), text: css('--text'), muted: css('--muted'),
    border: css('--border'), grid: css('--grid'),
    up: css('--up'), down: css('--down'), accent: css('--accent'),
  };

  const chart = LWC.createChart(canvas, {
    layout: {
      background: { type: LWC.ColorType.Solid, color: C.bg },
      textColor: C.muted,
      fontFamily: 'ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif',
      attributionLogo: false,          // set true if you want TradingView's link shown
    },
    grid: {
      vertLines: { color: C.grid },
      horzLines: { color: C.grid },
    },
    crosshair: {
      mode: LWC.CrosshairMode.Normal,  // .Magnet snaps to OHLC values instead
      vertLine: { color: C.muted, width: 1, style: LWC.LineStyle.Dashed, labelBackgroundColor: C.accent },
      horzLine: { color: C.muted, width: 1, style: LWC.LineStyle.Dashed, labelBackgroundColor: C.accent },
    },
    rightPriceScale: { borderColor: C.border, scaleMargins: { top: 0.10, bottom: 0.25 } },
    timeScale: {
      borderColor: C.border,
      timeVisible: true,               // intraday: show HH:MM on the axis
      secondsVisible: false,
      rightOffset: 10,                 // breathing room so marker labels aren't clipped
      barSpacing: 8,
    },
    localization: {
      locale: 'en-IN',
      priceFormatter: (p) => p.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    },
    autoSize: false,                   // we drive sizing with a ResizeObserver below
  });

  // ---- series (v5 unified API: chart.addSeries(SeriesDefinition, options)) ----
  const candles = chart.addSeries(LWC.CandlestickSeries, {
    upColor: C.up,       downColor: C.down,
    borderUpColor: C.up, borderDownColor: C.down,
    wickUpColor: C.up,   wickDownColor: C.down,
    priceLineVisible: true,
    priceLineColor: C.accent,
    priceLineStyle: LWC.LineStyle.Dotted,
  });

  const volume = chart.addSeries(LWC.HistogramSeries, {
    priceFormat: { type: 'volume' },
    priceScaleId: '',                  // '' = overlay on its own invisible scale
    lastValueVisible: false,
    priceLineVisible: false,
  });
  volume.priceScale().applyOptions({ scaleMargins: { top: 0.80, bottom: 0 } });

  const ema20 = chart.addSeries(LWC.LineSeries, {
    color: '#f0b90b', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
    crosshairMarkerVisible: false,
  });
  const ema50 = chart.addSeries(LWC.LineSeries, {
    color: '#a78bfa', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
    crosshairMarkerVisible: false,
  });

  // keep the chart sized to its container (works inside flex/grid dashboards)
  new ResizeObserver(([e]) => {
    const { width, height } = e.contentRect;
    if (width && height) chart.resize(width, height);
  }).observe(canvas);

  // ==========================================================================
  // 2. INDICATORS
  // ==========================================================================
  function ema(bars, period) {
    const k = 2 / (period + 1);
    const out = [];
    let prev = null;
    bars.forEach((b, i) => {
      prev = i === 0 ? b.close : b.close * k + prev * (1 - k);
      if (i >= period - 1) out.push({ time: b.time, value: prev });
    });
    return out;
  }

  // ==========================================================================
  // 3. TRADE LEVELS + SIGNAL MARKERS
  //    Feed this from your Option Recommendation Desk.
  // ==========================================================================
  let priceLines   = [];
  let markerApi    = null;
  let activeSignal = null;

  // Price lines don't affect autoscale on their own, so a far target can sit
  // off-screen. Widen the visible price range to always include the levels.
  candles.applyOptions({
    autoscaleInfoProvider: (original) => {
      const res = original();
      if (!res || !res.priceRange || !activeSignal) return res;
      const lv = [activeSignal.entry, activeSignal.stop, activeSignal.target1, activeSignal.target2]
        .filter((x) => typeof x === 'number');
      if (!lv.length) return res;
      res.priceRange.minValue = Math.min(res.priceRange.minValue, ...lv);
      res.priceRange.maxValue = Math.max(res.priceRange.maxValue, ...lv);
      return res;
    },
  });

  function clearLevels() {
    priceLines.forEach((l) => candles.removePriceLine(l));
    priceLines = [];
    activeSignal = null;
    if (markerApi) { markerApi.setMarkers([]); }
  }

  function drawLevels(signal) {
    clearLevels();
    if (!signal || !document.getElementById('abtLvls').checked) return;
    activeSignal = signal;

    const line = (price, color, title, style) => priceLines.push(
      candles.createPriceLine({
        price, color, lineWidth: 1, lineStyle: style ?? LWC.LineStyle.Dashed,
        axisLabelVisible: true, title,
      })
    );

    line(signal.entry,  C.accent, 'ENTRY', LWC.LineStyle.Solid);
    line(signal.stop,   C.down,   'SL');
    line(signal.target1, C.up,    'T1');
    if (signal.target2) line(signal.target2, C.up, 'T2', LWC.LineStyle.Dotted);

    // entry marker on the bar the signal fired
    const marks = [{
      time: signal.time,
      position: signal.side === 'SHORT' ? 'aboveBar' : 'belowBar',
      color: signal.side === 'SHORT' ? C.down : C.up,
      shape: signal.side === 'SHORT' ? 'arrowDown' : 'arrowUp',
      text: `${signal.side} ${signal.label ?? ''}`.trim(),
    }];
    markerApi = markerApi ? (markerApi.setMarkers(marks), markerApi)
                          : LWC.createSeriesMarkers(candles, marks);
  }

  const inr = (n) => Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function renderSignalStrip(signal) {
    const el = document.getElementById('abtSignal');
    if (!signal) { el.innerHTML = '<span class="abt-status">No active signal</span>'; return; }
    const rr = ((signal.target1 - signal.entry) / (signal.entry - signal.stop));
    el.innerHTML = `
      <span><span class="k">SIDE</span><span class="v" style="color:${signal.side === 'SHORT' ? C.down : C.up}">${signal.side}</span></span>
      <span><span class="k">ENTRY</span><span class="v">${inr(signal.entry)}</span></span>
      <span><span class="k">SL</span><span class="v" style="color:${C.down}">${inr(signal.stop)}</span></span>
      <span><span class="k">T1</span><span class="v" style="color:${C.up}">${inr(signal.target1)}</span></span>
      ${signal.target2 ? `<span><span class="k">T2</span><span class="v" style="color:${C.up}">${inr(signal.target2)}</span></span>` : ''}
      <span><span class="k">R:R</span><span class="v">1 : ${Math.abs(rr).toFixed(2)}</span></span>
      ${signal.note ? `<span class="abt-status">${signal.note}</span>` : ''}`;
  }

  // ==========================================================================
  // 4. CROSSHAIR LEGEND
  // ==========================================================================
  const legend = document.getElementById('abtLegend');
  let state = { symbol: 'NIFTY', bars: [] };

  function paintLegend(bar, e20, e50) {
    if (!bar) { legend.innerHTML = `<div class="sym">${state.symbol}</div>`; return; }
    const col = bar.close >= bar.open ? C.up : C.down;
    const chg = bar.close - bar.open;
    const pct = (chg / bar.open) * 100;
    legend.innerHTML = `
      <div class="sym">${state.symbol} · ${state.resLabel}</div>
      <div class="ohlc">
        O <b style="color:${col}">${inr(bar.open)}</b>
        H <b style="color:${col}">${inr(bar.high)}</b>
        L <b style="color:${col}">${inr(bar.low)}</b>
        C <b style="color:${col}">${inr(bar.close)}</b>
        <span class="v" style="color:${col}">${chg >= 0 ? '+' : ''}${inr(chg)} (${pct.toFixed(2)}%)</span>
      </div>
      <div class="ema">
        <span style="color:#f0b90b">EMA20 ${e20 ? inr(e20) : '—'}</span>
        &nbsp;<span style="color:#a78bfa">EMA50 ${e50 ? inr(e50) : '—'}</span>
      </div>`;
  }

  chart.subscribeCrosshairMove((param) => {
    if (!param.time) { paintLegend(state.bars.at(-1), lastEma(ema20Data), lastEma(ema50Data)); return; }
    paintLegend(
      param.seriesData.get(candles),
      param.seriesData.get(ema20)?.value,
      param.seriesData.get(ema50)?.value
    );
  });
  const lastEma = (arr) => arr.length ? arr.at(-1).value : null;

  // ==========================================================================
  // 5. DATA ADAPTER  ◀── THIS IS THE PART YOU REPLACE
  // ==========================================================================
  //
  //  Call YOUR backend, not Fyers, from the browser:
  //    - Fyers does not send CORS headers for browser origins
  //    - your access token would be readable by anyone opening devtools
  //
  //  Backend route (Node/Python) proxies to Fyers History and returns:
  //    { candles: [[epochSeconds, open, high, low, close, volume], ...] }
  //  which is exactly Fyers' own shape, so the mapping below stays trivial.
  //
  async function fetchCandles(symbol, resolution) {
    try {
      const res = await fetch(`/api/chart-history?symbol=${encodeURIComponent(symbol)}&resolution=${encodeURIComponent(resolution)}`);
      const data = await res.json();
      if (data.status === "SUCCESS" && data.candles && data.candles.length > 0) {
        return data.candles.map(c => ({
          time: c.timestamp || Math.floor(Date.now() / 1000),
          open: c.o,
          high: c.h,
          low: c.l,
          close: c.c,
          value: c.v || Math.round(Math.random() * 5000 + 1000),
        }));
      }
    } catch (e) {
      console.warn("fetchCandles history error:", e);
    }
    return demoCandles(symbol, resolution);
  }

  // Live tick from your Fyers websocket -> update the forming candle in place.
  // window.abtChart.onTick({ time: 1756450800, price: 24812.4, volume: 1200 })
  function onTick({ time, price, volume: vol }) {
    const last = state.bars.at(-1);
    if (!last) return;
    if (time > last.time) {                       // new bucket
      state.bars.push({ time, open: price, high: price, low: price, close: price, value: vol || 0 });
    } else {
      last.high = Math.max(last.high, price);
      last.low  = Math.min(last.low,  price);
      last.close = price;
      if (vol) last.value += vol;
    }
    const b = state.bars.at(-1);
    candles.update({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
    volume.update({ time: b.time, value: b.value, color: b.close >= b.open ? C.up + '66' : C.down + '66' });
  }

  // ==========================================================================
  // 6. RENDER PIPELINE
  // ==========================================================================
  let ema20Data = [], ema50Data = [];

  // `signal` is optional — pass one from your recommendation desk, or leave it
  // out and currentSignal() supplies whatever the last fetch produced.
  async function load(symbol, resolution, resLabel, signal) {
    state.symbol = ({
      'NSE:NIFTY50-INDEX': 'NIFTY 50',
      'NSE:NIFTYBANK-INDEX': 'BANK NIFTY',
      'BSE:SENSEX-INDEX': 'SENSEX',
    })[symbol] || symbol;
    state.resLabel = resLabel;

    const bars = await fetchCandles(symbol, resolution);
    state.bars = bars;

    candles.setData(bars.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })));
    volume.setData(bars.map((b) => ({
      time: b.time, value: b.value,
      color: (b.close >= b.open ? C.up : C.down) + '66',   // 40% alpha
    })));

    ema20Data = ema(bars, 20);
    ema50Data = ema(bars, 50);
    ema20.setData(ema20Data);
    ema50.setData(ema50Data);

    const sig = signal ?? currentSignal();   // resolved AFTER the fetch
    drawLevels(sig);
    renderSignalStrip(sig);
    paintLegend(bars.at(-1), lastEma(ema20Data), lastEma(ema50Data));
    chart.timeScale().fitContent();
  }

  // ==========================================================================
  // 7. CONTROLS
  // ==========================================================================
  let cur = { symbol: 'NSE:NIFTY50-INDEX', res: '5', label: '5m' };

  function wireGroup(role, onPick) {
    const g = root.querySelector(`[data-role="${role}"]`);
    g.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      g.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      onPick(b);
    });
  }
  wireGroup('symbols',     (b) => { cur.symbol = b.dataset.symbol; refresh(); });
  wireGroup('resolutions', (b) => { cur.res = b.dataset.res; cur.label = b.textContent; refresh(); });

  document.getElementById('abtVol').addEventListener('change', (e) =>
    volume.applyOptions({ visible: e.target.checked }));
  document.getElementById('abtEma').addEventListener('change', (e) => {
    ema20.applyOptions({ visible: e.target.checked });
    ema50.applyOptions({ visible: e.target.checked });
  });
  document.getElementById('abtLvls').addEventListener('change', () => refresh());

  function refresh() { load(cur.symbol, cur.res, cur.label); }

  // ==========================================================================
  // 8. DEMO DATA — delete this whole block once fetchCandles() is live
  // ==========================================================================
  let demoSignal = null;

  function demoCandles(symbol, res) {
    const base  = symbol.includes('NIFTYBANK') ? 55200 : symbol.includes('SENSEX') ? 81400 : 24800;
    const stepS = ({ '1': 60, '5': 300, '15': 900, '60': 3600, 'D': 86400 })[res];
    const n     = res === 'D' ? 180 : 240;
    const vol   = base * (res === 'D' ? 0.006 : 0.0009);

    // deterministic PRNG so the demo looks the same on every reload
    let seed = base + stepS;
    const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);

    let t = Math.floor(Date.now() / 1000 / stepS) * stepS - n * stepS;
    let px = base;
    const bars = [];
    for (let i = 0; i < n; i++) {
      const drift = (rnd() - 0.48) * vol;
      const open = px;
      const close = open + drift;
      const wick = vol * (0.3 + rnd() * 0.9);
      bars.push({
        time: t,
        open: +open.toFixed(2),
        high: +(Math.max(open, close) + wick * rnd()).toFixed(2),
        low:  +(Math.min(open, close) - wick * rnd()).toFixed(2),
        close: +close.toFixed(2),
        value: Math.round(80000 + rnd() * 260000),
      });
      px = close;
      t += stepS;
    }

    // a plausible signal on the last bar, mirroring your desk's +25% / -15% framing
    const last = bars.at(-1);
    const long = last.close >= bars.at(-20).close;
    demoSignal = {
      time: last.time,
      side: long ? 'LONG' : 'SHORT',
      label: long ? 'CE' : 'PE',
      entry: last.close,
      stop:  +(last.close + (long ? -1 : 1) * vol * 3).toFixed(2),
      target1: +(last.close + (long ? 1 : -1) * vol * 4).toFixed(2),
      target2: +(last.close + (long ? 1 : -1) * vol * 7).toFixed(2),
      note: 'demo data — wire fetchCandles() to your backend',
    };
    return bars;
  }

  function currentSignal() { return demoSignal; }

  // ==========================================================================
  // 9. PUBLIC HANDLE
  // ==========================================================================
  window.abtChart = {
    chart, candles, volume, ema20, ema50,
    load,                       // load(symbol, resolution, label, signalObject)
    onTick,                     // feed websocket ticks
    setSignal: (s) => { drawLevels(s); renderSignalStrip(s); },
    destroy: () => chart.remove(),
  };

  refresh();
})();