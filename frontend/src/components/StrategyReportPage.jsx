/* 対戦戦略 — Matchup Strategy Report
   Audience: 選手 / 監督 / コーチ / データ分析官
   Design philosophy:
   - 選手だけ選べば即生成（シーズンは隠す）
   - テキストとビジュアルを 50/50 でバランス
   - 縦長を排除し、グリッドで横方向の空白を活用
   - 既存スタッツに加え、Sprayチャート / Heat Zone / 球種マトリクス / Whiff%/CSW% などを追加

   ※ design/components/strategy.jsx を React 標準形式に移植したもの。
   ダミーデータのままで動作する（バックエンドは未結線）。
*/
import React, { useState, useEffect, Fragment } from 'react';
import Icon from './layout/Icon.jsx';

const StrategyScreen = ({ getBackendURL, getAuthHeaders }) => {
  /* ============ STATE ============ */
  // Phase 1: 開発を簡素化するため batter/pitcher は固定
  const [batter, setBatter] = useState({ id: 660271, name: "Shohei Ohtani", team: "LAD", hand: "L", pos: "DH" });
  const [pitcher, setPitcher] = useState({ id: 673540, name: "Kodai Senga", team: "NYM", hand: "R", pos: "SP" });
  const [generated, setGenerated] = useState(true);
  const [view, setView] = useState("both"); // both | batter | pitcher

  /* ============ CORE MATCHUP DATA ============ */
  // sample/historical_ops/confidence のみバックエンドから取得（LLM 不使用）。
  // edge / keyword は後続フェーズで本物に差し替え。
  const [headline, setHeadline] = useState({
    sample: { pa: 0, ab: 0, h: 0, hr: 0, bb: 0, k: 0 },
    historicalOps: ".000",
    edge: 62,
    confidence: "—",
    keyword: "速球は引っ張れ、変化球は見送れ",
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/sample-size?batter_id=${batter.id}&pitcher_id=${pitcher.id}`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        // OPS は 0〜4 程度の範囲を取りうるため、1 未満なら .XXX、1 以上は X.XXX で表示
        const ops = typeof data.historical_ops === "number" ? data.historical_ops : 0;
        const opsStr = ops > 0
          ? (ops < 1
              ? ops.toFixed(3).replace(/^-?0\./, ".")
              : ops.toFixed(3))
          : ".000";
        setHeadline(prev => ({
          ...prev,
          sample: data.sample || prev.sample,
          historicalOps: opsStr,
          confidence: data.confidence || "—",
          loading: false,
          error: null,
        }));
      } catch (e) {
        if (cancelled) return;
        console.error("sample-size fetch failed", e);
        setHeadline(prev => ({ ...prev, loading: false, error: e.message }));
      }
    })();
    return () => { cancelled = true; };
  }, [batter.id, pitcher.id, getBackendURL, getAuthHeaders]);

  // ============ KPI BAND（バックエンド集計） ============
  const [kpiBand, setKpiBand] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/kpi-band?batter_id=${batter.id}&pitcher_id=${pitcher.id}&season=2026`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setKpiBand({ loading: false, data, error: null });
      } catch (e) {
        if (cancelled) return;
        console.error("kpi-band fetch failed", e);
        setKpiBand({ loading: false, data: null, error: e.message });
      }
    })();
    return () => { cancelled = true; };
  }, [batter.id, pitcher.id, getBackendURL, getAuthHeaders]);

  // 表示用フォーマッタ
  // .790 のように常に小数3桁を保証（toFixed で末尾0も保持）
  const fmt3 = (v) => {
    if (v == null || Number.isNaN(v)) return "—";
    return Number(v).toFixed(3).replace(/^-?0\./, ".");
  };
  const fmtPct = (v) => v == null || isNaN(v) ? "—" : (v * 100).toFixed(1);

  // 比較ロジック（season vs league_avg）
  const compareTone = (val, lg, lowerIsBetter = false) => {
    if (val == null || lg == null) return { arrow: "flat", tone: "ink" };
    const diff = val - lg;
    if (Math.abs(diff) < 1e-6) return { arrow: "flat", tone: "ink" };
    const better = lowerIsBetter ? diff < 0 : diff > 0;
    return { arrow: better ? "up" : "down", tone: better ? "pos" : "neg" };
  };

  const buildKpis = () => {
    const d = kpiBand.data;
    if (!d) {
      // ロード中・エラー時のプレースホルダ
      return [
        { k: "xwOBA",     v: "…", d: "—",       arrow: "flat", tone: "ink" },
        { k: "xBA",       v: "…", d: "—",       arrow: "flat", tone: "ink" },
        { k: "K%",        v: "…", suffix: "%", d: "—", arrow: "flat", tone: "ink" },
        { k: "BB%",       v: "…", suffix: "%", d: "—", arrow: "flat", tone: "ink" },
        { k: "HARD HIT%", v: "…", suffix: "%", d: "—", arrow: "flat", tone: "ink" },
        { k: "SwStr%",    v: "…", suffix: "%", d: "—", arrow: "flat", tone: "ink" },
      ];
    }
    const k = d.season_kpi || {};
    const lg = d.league_avg || {};
    const matchupXba = d.matchup_xba;
    const matchupBbe = d.matchup_bbe || 0;
    const lgLabel = lg.p_throws ? `vs ${lg.p_throws}HP` : "リーグ";

    const xwoba = compareTone(k.xwoba, lg.xwoba);
    const kp    = compareTone(k.k_pct, lg.k_pct, /*lowerIsBetter*/ true);

    return [
      {
        k: "xwOBA", v: fmt3(k.xwoba),
        d: lg.xwoba != null ? `${lgLabel} avg ${fmt3(lg.xwoba)}` : "リーグ平均なし",
        arrow: xwoba.arrow, tone: xwoba.tone,
      },
      {
        k: "xBA", v: fmt3(matchupXba),
        d: matchupXba != null ? `対戦予測 (BBE ${matchupBbe})` : "対戦データなし",
        arrow: "flat", tone: "ink",
      },
      {
        k: "K%", v: fmtPct(k.k_pct), suffix: "%",
        d: lg.k_pct != null ? `${lgLabel}平均 ${fmtPct(lg.k_pct)}%` : "リーグ平均なし",
        arrow: kp.arrow, tone: kp.tone === "pos" ? "pos" : "neg",
      },
      {
        k: "BB%", v: fmtPct(k.bb_pct), suffix: "%",
        d: "選球眼指標",
        arrow: "flat", tone: "pos",
      },
      {
        k: "HARD HIT%", v: fmtPct(k.hardhit), suffix: "%",
        d: "EV ≥ 95mph 比率",
        arrow: "flat", tone: "pos",
      },
      {
        k: "SwStr%", v: fmtPct(k.swstr), suffix: "%",
        d: "空振り率",
        arrow: "flat", tone: "amber",
      },
    ];
  };
  const kpis = buildKpis();

  // Pitch arsenal — pitcher's pitches, batter's xwOBA against, recommendation
  const arsenal = [
    { code: "FF", name: "4-Seam",  vel: 95.8, use: 34, spin: 2410, mov: { h: 4.2, v: 14.1 }, batXwoba: .412, batRun: -3.1, swStr: 11.2, csw: 28.4, rec: "AVOID", recColor: "neg" },
    { code: "FS", name: "Forkball",vel: 84.2, use: 31, spin: 1620, mov: { h: 1.8, v: -4.4 }, batXwoba: .184, batRun: +5.2, swStr: 41.7, csw: 38.2, rec: "PRIMARY", recColor: "amber" },
    { code: "SL", name: "Slider",  vel: 87.3, use: 18, spin: 2480, mov: { h: -8.2, v: 1.1 }, batXwoba: .298, batRun: +1.8, swStr: 22.4, csw: 31.5, rec: "MIX",     recColor: "pos" },
    { code: "CT", name: "Cutter",  vel: 91.4, use: 11, spin: 2310, mov: { h: -2.4, v: 6.8 }, batXwoba: .264, batRun: +0.9, swStr: 18.5, csw: 30.1, rec: "MIX",     recColor: "pos" },
    { code: "CB", name: "Curve",   vel: 78.6, use: 6,  spin: 2580, mov: { h: -5.1, v: -8.2 },batXwoba: .211, batRun: +0.6, swStr: 26.0, csw: 33.8, rec: "STEAL",   recColor: "amber" },
  ];

  // Heat zone — 5x5 grid of xwOBA (batter's hot/cold) — backend fetched
  const FALLBACK_HEAT = [
    [.180, .220, .280, .240, .190],
    [.260, .380, .520, .410, .290],
    [.310, .550, .640, .520, .340],
    [.290, .420, .480, .380, .250],
    [.150, .210, .240, .200, .170],
  ];
  const [heatZoneState, setHeatZoneState] = useState({
    loading: true, zone: FALLBACK_HEAT, counts: null, totalPa: 0, error: null,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/heat-zone?batter_id=${batter.id}&season=2026`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        // null を持つセルは見栄えが悪いので fallback で穴埋め（極端値表示防止）
        const filled = (data.zone || FALLBACK_HEAT).map((row, ri) =>
          row.map((v, ci) => (v == null ? FALLBACK_HEAT[ri][ci] : v))
        );
        setHeatZoneState({
          loading: false,
          zone: filled,
          counts: data.counts || null,
          totalPa: data.total_pa || 0,
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        console.error("heat-zone fetch failed", e);
        setHeatZoneState(prev => ({ ...prev, loading: false, error: e.message }));
      }
    })();
    return () => { cancelled = true; };
  }, [batter.id, getBackendURL, getAuthHeaders]);

  const heatZone = heatZoneState.zone;

  // Spray distribution by field third
  const spray = [
    { zone: "PULL",   pct: 48, slg: .612, label: "RIGHT" },
    { zone: "CENTER", pct: 32, slg: .455, label: "MID"   },
    { zone: "OPPO",   pct: 20, slg: .288, label: "LEFT"  },
  ];

  // Count-state matrix — what to throw in each count
  const counts = [
    { c: "0-0", call: "FF",  conf: "HIGH" },
    { c: "0-1", call: "FS",  conf: "HIGH" },
    { c: "0-2", call: "FS",  conf: "HIGH" },
    { c: "1-0", call: "SL",  conf: "MED"  },
    { c: "1-1", call: "FS",  conf: "HIGH" },
    { c: "1-2", call: "FS",  conf: "HIGH" },
    { c: "2-0", call: "CT",  conf: "MED"  },
    { c: "2-1", call: "FS",  conf: "MED"  },
    { c: "2-2", call: "FS",  conf: "HIGH" },
    { c: "3-0", call: "FF",  conf: "LOW"  },
    { c: "3-1", call: "CT",  conf: "MED"  },
    { c: "3-2", call: "FS",  conf: "HIGH" },
  ];

  // Last 10 PA timeline
  const recent = [
    { d: "8/02", pa: "K", note: "FS見送り三振" },
    { d: "7/28", pa: "1B", note: "FF引っ張り" },
    { d: "7/22", pa: "BB", note: "FS見極め" },
    { d: "7/15", pa: "K", note: "FS空振り" },
    { d: "6/30", pa: "HR", note: "FF真ん中→右翼" },
    { d: "6/24", pa: "F8", note: "SLセンター" },
    { d: "6/12", pa: "K", note: "FSスイング" },
    { d: "5/28", pa: "2B", note: "FF引っ張り" },
    { d: "5/14", pa: "BB", note: "選球眼" },
    { d: "5/01", pa: "K", note: "FS低め" },
  ];

  // Tactics — split by side (BATTER / PITCHER)
  const batterTactics = [
    { tier: "SIT ON",     title: "初球速球を狙え",       detail: "0-0 では FF を 78% で投げてくる。真ん中〜内角の速球を強振、xwOBA .412 のゾーン狙い。", icon: "target" },
    { tier: "TAKE",       title: "2ストライクのフォーク見送り", detail: "低めへ落ちる Forkball は被xwOBA .184。スイング率を抑え、ボール球に手を出さない選球が鍵。", icon: "alert" },
    { tier: "PROTECT",    title: "カウント追い込まれ後の対応", detail: "1-2/2-2 で Forkball 連投が予想される。短く持って広く構え、当てに行く対応も視野に。", icon: "users" },
    { tier: "COUNT",      title: "3-1 / 2-0 で勝負",      detail: "バッター有利カウントでは Cutter or FF。失投を逃さず引っ張り SLG .612 を活かす。", icon: "bolt" },
  ];
  const pitcherTactics = [
    { tier: "WEAPON",     title: "フォーク決め球化",     detail: "Whiff率 41.7% は今季全打者中4位。2ストライク後はフォーク連投、空振り三振狙い。", icon: "bolt" },
    { tier: "AVOID",      title: "速球真ん中回避",       detail: "ゾーン中央へのFF被xwOBA .640。低め外角または内角ボール球で見せ球に。", icon: "alert" },
    { tier: "SETUP",      title: "1ストライク先行",      detail: "初球FF外角でストライク先行 → 2球目以降フォーク主体。0-1 からのフォーク被打率 .118。", icon: "target" },
    { tier: "DEFENSE",    title: "シフト・引っ張り守備", detail: "プル率48%、SLG .612。一二塁間/右翼線を厚く、二塁手深め配置を推奨。", icon: "users" },
  ];

  // Comparable matchups (calibration)
  const comps = [
    { vs: "M.Buehler",   sim: 92, paOPS: ".524", k: 6, pa: 15 },
    { vs: "Y.Yamamoto",  sim: 88, paOPS: ".618", k: 5, pa: 12 },
    { vs: "S.Manaea",    sim: 81, paOPS: ".712", k: 4, pa: 11 },
    { vs: "C.Burnes",    sim: 76, paOPS: ".891", k: 3, pa: 9  },
  ];

  /* ============ HANDLERS ============ */
  const swap = () => {
    setBatter(pitcher); setPitcher(batter);
  };

  if (!generated) {
    return <StrategyEmptyState onGenerate={() => setGenerated(true)} batter={batter} pitcher={pitcher} setBatter={setBatter} setPitcher={setPitcher}/>;
  }

  /* ============ RENDER ============ */
  return (
    <div data-screen-label="STRATEGY · MATCHUP REPORT" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--bg-0)", overflowY: "auto" }}>
      {/* ============ SELECTOR BAR ============ */}
      <SelectorBar batter={batter} pitcher={pitcher} setBatter={setBatter} setPitcher={setPitcher} swap={swap} onRegenerate={() => { setGenerated(false); setTimeout(() => setGenerated(true), 220); }} view={view} setView={setView}/>

      {/* ============ HERO MATCHUP ============ */}
      <MatchupHero batter={batter} pitcher={pitcher} headline={headline} view={view}/>

      {/* ============ KPI BAND ============ */}
      <div className="rule-b" style={{ padding: "16px 28px", display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
        {kpis.map(k => (
          <div key={k.k} style={{ border: "1px solid var(--rule)", padding: "10px 12px", background: "var(--bg-1)" }}>
            <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 4 }}>{k.k}</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
              <span style={{ fontSize: 22, fontFamily: "var(--ff-head)", fontWeight: 700,
                color: k.tone === "amber" ? "var(--amber)" : k.tone === "pos" ? "var(--pos)" : k.tone === "neg" ? "var(--neg)" : "var(--ink-0)",
                lineHeight: 1 }}>{k.v}</span>
              {k.suffix && <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>{k.suffix}</span>}
              <div style={{ flex: 1 }}/>
              <ArrowChip dir={k.arrow}/>
            </div>
            <div className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", marginTop: 6 }}>{k.d}</div>
          </div>
        ))}
      </div>

      {/* ============ ROW 1: HEAT + ARSENAL + SPRAY ============ */}
      <div className="rule-b" style={{ padding: "18px 28px", display: "grid", gridTemplateColumns: "320px 1fr 280px", gap: 14 }}>
        <ViewWrap view={view} side="batter"><HeatZonePanel zone={heatZone} batter={batter} view={view}/></ViewWrap>
        <ViewWrap view={view} side="pitcher"><ArsenalPanel arsenal={arsenal} pitcher={pitcher} view={view}/></ViewWrap>
        <ViewWrap view={view} side="batter"><SprayPanel spray={spray} batter={batter}/></ViewWrap>
      </div>

      {/* ============ ROW 2: TACTICS DUAL + COUNT MATRIX ============ */}
      <div className="rule-b" style={{ padding: "18px 28px", display: "grid", gridTemplateColumns: "1fr 1fr 360px", gap: 14 }}>
        <ViewWrap view={view} side="batter"><TacticsPanel tactics={batterTactics} side="BATTER" sideLabel="打者戦術" accent="var(--pos)"/></ViewWrap>
        <ViewWrap view={view} side="pitcher"><TacticsPanel tactics={pitcherTactics} side="PITCHER" sideLabel="投手戦術" accent="var(--info)"/></ViewWrap>
        <CountMatrixPanel counts={counts} view={view}/>
      </div>

      {/* ============ ROW 2.5: COMPS ============ */}
      <div className="rule-b" style={{ padding: "18px 28px", display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
        <CompsPanel comps={comps} pitcher={pitcher}/>
      </div>

      {/* ============ ROW 3: RECENT TIMELINE + EXEC SUMMARY ============ */}
      <div style={{ padding: "18px 28px 24px", display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 14 }}>
        <RecentPAPanel recent={recent}/>
        <ExecSummaryPanel batter={batter} pitcher={pitcher} headline={headline}/>
      </div>
    </div>
  );
};

/* ============================================================
   SELECTOR BAR (シーズン除外、選手 2 つだけ)
============================================================ */
const SelectorBar = ({ batter, pitcher, setBatter, setPitcher, swap, onRegenerate, view, setView }) => (
  <div className="rule-b" style={{ padding: "14px 28px", display: "flex", alignItems: "center", gap: 14, background: "var(--bg-0)" }}>
    <div className="h-label" style={{ fontSize: 9.5, color: "var(--amber)", letterSpacing: "0.14em" }}>STRATEGY · 対戦戦略</div>
    <div style={{ width: 1, height: 22, background: "var(--rule)" }}/>

    <PlayerPicker label="BATTER · 打者" data={batter} accent="var(--pos)" dim={view === "pitcher"}/>
    <button onClick={swap} title="入れ替え" style={{ width: 28, height: 28, border: "1px solid var(--rule)", color: "var(--ink-3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 8h14l-3-3M21 16H7l3 3"/></svg>
    </button>
    <PlayerPicker label="PITCHER · 投手" data={pitcher} accent="var(--info)" dim={view === "batter"}/>

    {/* VIEW TOGGLE */}
    <div style={{ marginLeft: 18, display: "flex", alignItems: "center", gap: 8 }}>
      <span className="h-label" style={{ fontSize: 8.5, color: "var(--ink-3)" }}>VIEW · 視点</span>
      <div style={{ display: "flex", border: "1px solid var(--rule)" }}>
        {[
          { id: "both",    label: "BOTH",    sub: "両方",  c: "var(--amber)" },
          { id: "batter",  label: "BATTER",  sub: "打者",  c: "var(--pos)" },
          { id: "pitcher", label: "PITCHER", sub: "投手",  c: "var(--info)" },
        ].map(o => {
          const a = view === o.id;
          return (
            <button key={o.id} onClick={() => setView(o.id)} style={{
              padding: "6px 12px", display: "flex", flexDirection: "column", alignItems: "center", gap: 1,
              background: a ? o.c : "transparent",
              color: a ? "var(--bg-0)" : "var(--ink-2)",
              borderRight: o.id !== "pitcher" ? "1px solid var(--rule)" : "none",
            }}>
              <span className="t-mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: "0.1em" }}>{o.label}</span>
              <span style={{ fontSize: 8.5, opacity: 0.85 }}>{o.sub}</span>
            </button>
          );
        })}
      </div>
    </div>

    <div style={{ flex: 1 }}/>

    <button onClick={onRegenerate} style={{
      padding: "8px 16px", background: "var(--amber)", color: "var(--bg-0)",
      fontFamily: "var(--ff-mono)", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em",
      display: "inline-flex", alignItems: "center", gap: 6,
    }}>
      <Icon name="bolt" size={12}/> REGENERATE REPORT
    </button>
    <button style={{ padding: "8px 12px", border: "1px solid var(--rule)", color: "var(--ink-2)", fontFamily: "var(--ff-mono)", fontSize: 10.5, letterSpacing: "0.1em" }}>
      <Icon name="send" size={11} style={{ marginRight: 6, verticalAlign: "-1px" }}/>EXPORT
    </button>
  </div>
);

const PlayerPicker = ({ label, data, accent, dim }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 3, opacity: dim ? 0.42 : 1, transition: "opacity .2s" }}>
    <span className="h-label" style={{ fontSize: 8.5, color: "var(--ink-3)" }}>{label}</span>
    <button style={{
      display: "flex", alignItems: "center", gap: 9, padding: "6px 12px",
      border: "1px solid var(--rule)", background: "var(--bg-1)", minWidth: 240,
    }}>
      <span style={{ width: 6, height: 6, background: accent, transform: "rotate(45deg)" }}/>
      <span style={{ fontSize: 13, color: "var(--ink-0)", fontWeight: 600, fontFamily: "var(--ff-head)", letterSpacing: "0.02em", textTransform: "uppercase" }}>{data.name}</span>
      <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", padding: "1px 5px", border: "1px solid var(--rule-dim)" }}>{data.team}</span>
      <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{data.hand}H</span>
      <div style={{ flex: 1 }}/>
      <Icon name="chevD" size={12} style={{ color: "var(--ink-3)" }}/>
    </button>
  </div>
);

/* ============================================================
   HERO MATCHUP — vs ・ Edge bar ・ Headline
============================================================ */
const MatchupHero = ({ batter, pitcher, headline, view }) => {
  const edgePct = headline.edge;
  const dimB = view === "pitcher";
  const dimP = view === "batter";
  return (
    <div className="rule-b" style={{
      padding: "26px 28px 22px",
      background: "linear-gradient(180deg, oklch(from var(--amber) l c h / 0.06) 0%, transparent 100%)",
    }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px 1fr", gap: 24, alignItems: "center" }}>
        {/* Batter */}
        <div style={{ opacity: dimB ? 0.4 : 1, transition: "opacity .2s" }}>
          <PlayerCard data={batter} role="BATTER" accent="var(--pos)" align="right"/>
        </div>

        {/* Center — VS, edge, headline */}
        <div style={{ textAlign: "center" }}>
          <div className="t-mono" style={{ fontSize: 10, color: "var(--amber)", letterSpacing: "0.2em", marginBottom: 8 }}>MATCHUP REPORT · 2026</div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, marginBottom: 14 }}>
            <span className="h-display" style={{ fontSize: 40, color: "var(--pos)" }}>{batter.team}</span>
            <span className="h-display" style={{ fontSize: 28, color: "var(--ink-3)" }}>VS</span>
            <span className="h-display" style={{ fontSize: 40, color: "var(--info)" }}>{pitcher.team}</span>
          </div>
          {/* Edge bar */}
          <div style={{ position: "relative", height: 8, background: "var(--bg-2)", border: "1px solid var(--rule)", marginBottom: 6 }}>
            <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${100 - edgePct}%`, background: "var(--info)", opacity: 0.6 }}/>
            <div style={{ position: "absolute", right: 0, top: 0, height: "100%", width: `${edgePct}%`, background: "var(--pos)", opacity: 0.6 }}/>
            <div style={{ position: "absolute", top: -3, left: `${edgePct}%`, width: 2, height: 14, background: "var(--amber)" }}/>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, fontFamily: "var(--ff-mono)", color: "var(--ink-3)", letterSpacing: "0.06em" }}>
            <span>PITCHER 38%</span>
            <span style={{ color: "var(--amber)" }}>EDGE: BATTER {edgePct}%</span>
            <span>BATTER 62%</span>
          </div>
          <div style={{ marginTop: 14, padding: "8px 14px", border: "1px solid var(--amber)", background: "oklch(from var(--amber) l c h / 0.08)", display: "inline-block" }}>
            <span className="h-label" style={{ fontSize: 9, color: "var(--amber)", marginRight: 8 }}>KEY INSIGHT</span>
            <span style={{ fontSize: 12.5, color: "var(--ink-0)", fontWeight: 500 }}>{headline.keyword}</span>
          </div>
        </div>

        {/* Pitcher */}
        <div style={{ opacity: dimP ? 0.4 : 1, transition: "opacity .2s" }}>
          <PlayerCard data={pitcher} role="PITCHER" accent="var(--info)" align="left"/>
        </div>
      </div>

      {/* Sample size strip */}
      <div style={{ marginTop: 22, paddingTop: 14, borderTop: "1px solid var(--rule)", display: "flex", justifyContent: "center", gap: 26 }}>
        {[
          { k: "PA", v: headline.sample.pa },
          { k: "AB", v: headline.sample.ab },
          { k: "H",  v: headline.sample.h  },
          { k: "HR", v: headline.sample.hr, tone: "amber" },
          { k: "BB", v: headline.sample.bb, tone: "pos" },
          { k: "K",  v: headline.sample.k,  tone: "neg" },
        ].map(s => (
          <div key={s.k} style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span className="h-label" style={{ fontSize: 9, color: "var(--ink-3)" }}>{s.k}</span>
            <span className="t-digit" style={{ fontSize: 16, color: s.tone === "amber" ? "var(--amber)" : s.tone === "pos" ? "var(--pos)" : s.tone === "neg" ? "var(--neg)" : "var(--ink-0)", fontWeight: 700 }}>{s.v}</span>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
          <span className="h-label" style={{ fontSize: 9, color: "var(--ink-3)" }}>HISTORICAL OPS</span>
          <span className="t-digit" style={{ fontSize: 16, color: "var(--ink-0)", fontWeight: 700 }}>
            {headline.loading ? "…" : (headline.historicalOps || ".000")}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
          <span className="h-label" style={{ fontSize: 9, color: "var(--ink-3)" }}>CONFIDENCE</span>
          <span className="t-mono" style={{ fontSize: 11, color: "var(--amber)", fontWeight: 700, padding: "1px 6px", border: "1px solid var(--amber)" }}>
            {headline.loading ? "…" : headline.confidence}
          </span>
        </div>
      </div>
    </div>
  );
};

const PlayerCard = ({ data, role, accent, align }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: align === "right" ? "flex-end" : "flex-start" }}>
    <div className="t-mono" style={{ fontSize: 10, color: accent, letterSpacing: "0.14em", marginBottom: 4 }}>{role} · {data.pos}</div>
    <div className="h-display" style={{ fontSize: 30, color: "var(--ink-0)", lineHeight: 1, letterSpacing: "0.01em" }}>{data.name.toUpperCase()}</div>
    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
      <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-1)", padding: "2px 8px", border: "1px solid var(--rule)", background: "var(--bg-1)" }}>{data.team}</span>
      <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-2)", padding: "2px 8px", border: "1px solid var(--rule)", background: "var(--bg-1)" }}>{data.hand}HP</span>
      <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-2)", padding: "2px 8px", border: "1px solid var(--rule)", background: "var(--bg-1)" }}>#{data.id}</span>
    </div>
  </div>
);

/* ============================================================
   HEAT ZONE — 5x5 strike zone xwOBA
============================================================ */
const HeatZonePanel = ({ zone, batter, view }) => {
  const colorFor = (v) => {
    // .150 (cold) → .640 (hot)
    const t = Math.max(0, Math.min(1, (v - .150) / (.640 - .150)));
    const lightness = 0.32 + t * 0.45;
    const chroma = 0.04 + t * 0.18;
    const hue = 240 - t * 210; // blue → amber → red
    return `oklch(${lightness} ${chroma} ${hue})`;
  };
  return (
    <div style={{ border: "1px solid var(--rule)", display: "flex", flexDirection: "column" }}>
      <PanelHeader title={view === "pitcher" ? "HEAT ZONE · 避けるゾーン" : "HEAT ZONE · 狙いゾーン"} sub="xwOBA · 5×5"/>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
        {/* Strike zone */}
        <div style={{ position: "relative", aspectRatio: "1 / 1", background: "var(--bg-1)", border: "1px solid var(--rule)" }}>
          <div style={{ position: "absolute", inset: 0, display: "grid", gridTemplateColumns: "repeat(5,1fr)", gridTemplateRows: "repeat(5,1fr)" }}>
            {zone.flatMap((row, ri) => row.map((v, ci) => {
              const inZone = ri >= 1 && ri <= 3 && ci >= 1 && ci <= 3;
              return (
                <div key={`${ri}-${ci}`} style={{
                  background: colorFor(v),
                  border: inZone ? "0.5px solid oklch(1 0 0 / 0.18)" : "0.5px dashed oklch(1 0 0 / 0.08)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: "var(--ff-mono)", fontSize: 9.5, fontWeight: 700,
                  color: v > .4 ? "var(--bg-0)" : "var(--ink-0)",
                }}>{("." + String(Math.round(v*1000)).padStart(3,"0")).replace(/^0/, "")}</div>
              );
            }))}
          </div>
          {/* Strike zone outline */}
          <div style={{ position: "absolute", left: "20%", top: "20%", width: "60%", height: "60%", border: "1.5px solid var(--ink-0)", pointerEvents: "none" }}/>
          <div style={{ position: "absolute", bottom: -2, left: "50%", transform: "translateX(-50%)", color: "var(--ink-3)", fontSize: 8.5, fontFamily: "var(--ff-mono)", background: "var(--bg-0)", padding: "0 4px" }}>HOME PLATE</div>
        </div>
        {/* Legend */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 9, fontFamily: "var(--ff-mono)" }}>
          <span style={{ color: "var(--ink-3)" }}>COLD</span>
          <div style={{ flex: 1, height: 8, background: "linear-gradient(90deg, oklch(0.32 0.04 240), oklch(0.55 0.13 80), oklch(0.65 0.20 30))" }}/>
          <span style={{ color: "var(--ink-3)" }}>HOT</span>
        </div>
        <div style={{ fontSize: 10.5, color: "var(--ink-2)", lineHeight: 1.5 }}>
          <span className="t-mono" style={{ color: "var(--amber)", fontSize: 10 }}>→ </span>
          中央〜内角中段に最も強い。<strong style={{ color: "var(--ink-0)" }}>低め外</strong>と<strong style={{ color: "var(--ink-0)" }}>高め内</strong>のボール球で対処。
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   ARSENAL — pitcher's pitches and how batter hits them
============================================================ */
const ArsenalPanel = ({ arsenal, pitcher, view }) => {
  const recColor = { neg: "var(--neg)", amber: "var(--amber)", pos: "var(--pos)" };
  return (
    <div style={{ border: "1px solid var(--rule)" }}>
      <PanelHeader title={view === "batter" ? "OPPONENT ARSENAL · 投手の武器" : "PITCH ARSENAL × MATCHUP"} sub={`${pitcher.name} の球種 / 打者対策`}/>
      <div style={{ padding: "10px 14px 14px" }}>
        {/* Header */}
        <div style={{
          display: "grid", gridTemplateColumns: "44px 1fr 56px 56px 60px 56px 56px 80px",
          padding: "6px 0", fontSize: 9, color: "var(--ink-3)", letterSpacing: "0.1em", fontWeight: 600,
          borderBottom: "1px solid var(--rule)",
        }}>
          <div>PITCH</div><div></div>
          <div style={{textAlign:"right"}}>VEL</div>
          <div style={{textAlign:"right"}}>USE%</div>
          <div style={{textAlign:"right", color: "var(--pos)"}}>xwOBA</div>
          <div style={{textAlign:"right"}}>SwStr%</div>
          <div style={{textAlign:"right"}}>CSW%</div>
          <div style={{textAlign:"right"}}>STRATEGY</div>
        </div>
        {arsenal.map((p, i) => (
          <div key={p.code} style={{
            display: "grid", gridTemplateColumns: "44px 1fr 56px 56px 60px 56px 56px 80px",
            padding: "10px 0", fontFamily: "var(--ff-mono)", fontSize: 11.5, alignItems: "center",
            borderBottom: i < arsenal.length-1 ? "1px solid var(--rule-dim)" : "none",
          }}>
            <div><span style={{ display: "inline-block", padding: "2px 7px", background: "var(--bg-2)", color: "var(--amber)", fontWeight: 700, letterSpacing: "0.04em" }}>{p.code}</span></div>
            <div style={{ fontFamily: "var(--ff-text)", fontSize: 12, color: "var(--ink-1)" }}>
              {p.name}
              <div style={{ display: "flex", gap: 2, marginTop: 4 }}>
                <div style={{ width: `${p.use*1.6}px`, maxWidth: 80, height: 4, background: "var(--amber-dim)" }}/>
              </div>
            </div>
            <div style={{ textAlign: "right", color: "var(--ink-0)" }}>{p.vel.toFixed(1)}</div>
            <div style={{ textAlign: "right", color: "var(--ink-2)" }}>{p.use}</div>
            <div style={{ textAlign: "right", color: p.batXwoba > .35 ? "var(--neg)" : p.batXwoba < .25 ? "var(--pos)" : "var(--ink-0)", fontWeight: 700 }}>
              .{String(Math.round(p.batXwoba*1000)).padStart(3,"0")}
            </div>
            <div style={{ textAlign: "right", color: p.swStr > 30 ? "var(--amber)" : "var(--ink-1)" }}>{p.swStr.toFixed(1)}</div>
            <div style={{ textAlign: "right", color: "var(--ink-2)" }}>{p.csw.toFixed(1)}</div>
            <div style={{ textAlign: "right" }}>
              <span style={{
                fontSize: 9.5, padding: "2px 7px", border: `1px solid ${recColor[p.recColor]}`, color: recColor[p.recColor],
                fontWeight: 700, letterSpacing: "0.08em",
              }}>{p.rec}</span>
            </div>
          </div>
        ))}
        {/* Mini movement plot */}
        <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <MovementPlot arsenal={arsenal}/>
          <VelocityPlot arsenal={arsenal}/>
        </div>
      </div>
    </div>
  );
};

const MovementPlot = ({ arsenal }) => (
  <div style={{ border: "1px solid var(--rule-dim)", padding: 10, background: "var(--bg-1)" }}>
    <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 6 }}>MOVEMENT · INCHES</div>
    <svg viewBox="-15 -15 30 30" style={{ width: "100%", aspectRatio: "1/1", display: "block" }}>
      <line x1="-15" y1="0" x2="15" y2="0" stroke="var(--rule)" strokeWidth="0.2"/>
      <line x1="0" y1="-15" x2="0" y2="15" stroke="var(--rule)" strokeWidth="0.2"/>
      {[5, 10].map(r => <circle key={r} cx="0" cy="0" r={r} fill="none" stroke="var(--rule-dim)" strokeWidth="0.15" strokeDasharray="0.5 0.5"/>)}
      {arsenal.map(p => (
        <g key={p.code}>
          <circle cx={p.mov.h} cy={-p.mov.v} r={p.use/8 + 1} fill="var(--amber)" opacity="0.7"/>
          <text x={p.mov.h} y={-p.mov.v + 0.5} fontSize="2" fontFamily="var(--ff-mono)" fontWeight="700" fill="var(--bg-0)" textAnchor="middle">{p.code}</text>
        </g>
      ))}
    </svg>
  </div>
);

const VelocityPlot = ({ arsenal }) => {
  const max = 100, min = 70;
  return (
    <div style={{ border: "1px solid var(--rule-dim)", padding: 10, background: "var(--bg-1)" }}>
      <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 6 }}>VELOCITY MIX · MPH</div>
      <div style={{ position: "relative", height: 80 }}>
        {arsenal.map(p => {
          const x = ((p.vel - min) / (max - min)) * 100;
          return (
            <div key={p.code} style={{ position: "absolute", left: `${x}%`, bottom: 0, transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span className="t-mono" style={{ fontSize: 9, color: "var(--ink-0)" }}>{p.vel.toFixed(1)}</span>
              <div style={{ width: 2, height: p.use*1.4, background: "var(--amber)" }}/>
              <span className="t-mono" style={{ fontSize: 8.5, color: "var(--amber)", fontWeight: 700 }}>{p.code}</span>
            </div>
          );
        })}
        <div style={{ position: "absolute", left: 0, right: 0, bottom: -1, height: 1, background: "var(--rule)" }}/>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 8.5, fontFamily: "var(--ff-mono)", color: "var(--ink-4)" }}>
        <span>70</span><span>85</span><span>100</span>
      </div>
    </div>
  );
};

/* ============================================================
   SPRAY CHART — field with hit distribution
============================================================ */
const SprayPanel = ({ spray, batter }) => (
  <div style={{ border: "1px solid var(--rule)" }}>
    <PanelHeader title="SPRAY · 打球方向" sub="プル / セ / 流し"/>
    <div style={{ padding: 14 }}>
      {/* Field SVG */}
      <svg viewBox="0 0 200 180" style={{ width: "100%", display: "block" }}>
        {/* Outfield arc fill */}
        <path d="M 30 160 A 100 100 0 0 1 170 160 L 100 160 Z" fill="var(--bg-1)" stroke="var(--rule)" strokeWidth="0.5"/>
        {/* Pull (right field for L) */}
        <path d="M 100 160 L 170 160 A 100 100 0 0 0 147 92 Z" fill={`oklch(0.55 ${spray[0].pct/200 + 0.08} 80 / 0.7)`}/>
        {/* Center */}
        <path d="M 100 160 L 147 92 A 100 100 0 0 0 53 92 Z" fill={`oklch(0.55 ${spray[1].pct/200 + 0.08} 80 / 0.5)`}/>
        {/* Oppo */}
        <path d="M 100 160 L 53 92 A 100 100 0 0 0 30 160 Z" fill={`oklch(0.55 ${spray[2].pct/200 + 0.08} 80 / 0.35)`}/>
        {/* Infield diamond */}
        <path d="M 100 160 L 130 130 L 100 100 L 70 130 Z" fill="var(--bg-2)" stroke="var(--ink-3)" strokeWidth="0.6"/>
        {/* Bases */}
        {[[100,160],[130,130],[100,100],[70,130]].map((b,i) => <rect key={i} x={b[0]-2.5} y={b[1]-2.5} width="5" height="5" fill="var(--ink-1)" transform={`rotate(45 ${b[0]} ${b[1]})`}/>)}
        {/* Foul lines */}
        <line x1="100" y1="160" x2="30" y2="160" stroke="var(--ink-3)" strokeWidth="0.4"/>
        <line x1="100" y1="160" x2="170" y2="160" stroke="var(--ink-3)" strokeWidth="0.4"/>
        {/* % labels */}
        <text x="148" y="125" fill="var(--amber)" fontSize="9" fontFamily="var(--ff-mono)" fontWeight="700" textAnchor="middle">{spray[0].pct}%</text>
        <text x="100" y="100" fill="var(--ink-0)" fontSize="9" fontFamily="var(--ff-mono)" fontWeight="700" textAnchor="middle">{spray[1].pct}%</text>
        <text x="52" y="125" fill="var(--ink-1)" fontSize="9" fontFamily="var(--ff-mono)" fontWeight="700" textAnchor="middle">{spray[2].pct}%</text>
        {/* Zone labels */}
        <text x="155" y="172" fill="var(--ink-3)" fontSize="6.5" fontFamily="var(--ff-mono)" textAnchor="middle">PULL</text>
        <text x="100" y="172" fill="var(--ink-3)" fontSize="6.5" fontFamily="var(--ff-mono)" textAnchor="middle">CEN</text>
        <text x="45"  y="172" fill="var(--ink-3)" fontSize="6.5" fontFamily="var(--ff-mono)" textAnchor="middle">OPPO</text>
      </svg>

      {/* SLG breakdown */}
      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
        {spray.map(s => (
          <div key={s.zone} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5, fontFamily: "var(--ff-mono)" }}>
            <span style={{ width: 50, color: "var(--ink-3)", fontSize: 9, letterSpacing: "0.06em" }}>{s.zone}</span>
            <div style={{ flex: 1, height: 4, background: "var(--bg-2)" }}>
              <div style={{ width: `${s.slg*100}%`, height: "100%", background: s.zone === "PULL" ? "var(--amber)" : "var(--ink-2)" }}/>
            </div>
            <span style={{ color: "var(--ink-0)", width: 38, textAlign: "right" }}>.{String(Math.round(s.slg*1000)).padStart(3,"0")}</span>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 10, fontSize: 10.5, color: "var(--ink-2)", lineHeight: 1.5 }}>
        <span className="t-mono" style={{ color: "var(--amber)", fontSize: 10 }}>→ </span>
        プル偏重 <strong style={{ color: "var(--ink-0)" }}>48% / SLG.612</strong>。シフト推奨。
      </div>
    </div>
  </div>
);

/* ============================================================
   TACTICS — actionable recommendations
============================================================ */
const TacticsPanel = ({ tactics, side, sideLabel, accent }) => {
  const tierColor = (t) => ({
    SIT_ON: "var(--pos)", TAKE: "var(--neg)", PROTECT: "var(--amber)", COUNT: "var(--info)",
    OFFENSIVE: "var(--amber)", WEAPON: "var(--pos)", AVOID: "var(--neg)", DEFENSE: "var(--info)", SETUP: "var(--amber)",
  })[t.replace(" ", "_")] || "var(--ink-2)";
  return (
    <div style={{ border: `1px solid ${accent}` }}>
      <div className="rule-b" style={{ padding: "9px 14px", background: `oklch(from ${accent} l c h / 0.08)`, display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ width: 8, height: 8, background: accent }}/>
        <span className="h-label" style={{ color: accent }}>{side} TACTICS</span>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>{sideLabel}</span>
        <div style={{ flex: 1 }}/>
        <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{tactics.length} ITEMS</span>
      </div>
      <div>
        {tactics.map((t, i) => (
          <div key={t.title} style={{
            padding: "12px 14px",
            borderBottom: i < tactics.length - 1 ? "1px solid var(--rule-dim)" : "none",
            display: "flex", gap: 11, alignItems: "flex-start",
          }}>
            <div style={{
              width: 28, height: 28, border: `1px solid ${tierColor(t.tier)}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: tierColor(t.tier), flexShrink: 0,
            }}>
              <Icon name={t.icon} size={13}/>
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 3 }}>
                <span className="t-mono" style={{ fontSize: 9, color: tierColor(t.tier), fontWeight: 700, letterSpacing: "0.12em" }}>{t.tier}</span>
                <span className="h-display" style={{ fontSize: 12.5, color: "var(--ink-0)" }}>{t.title}</span>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--ink-2)", lineHeight: 1.55 }}>{t.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ViewWrap — dim/hide panels by side based on view toggle */
const ViewWrap = ({ view, side, children }) => {
  if (view === "both" || side === "neutral") return children;
  const isMatch = view === side;
  return (
    <div style={{
      opacity: isMatch ? 1 : 0.32,
      transition: "opacity .25s, filter .25s",
      filter: isMatch ? "none" : "saturate(0.5)",
      position: "relative",
    }}>
      {!isMatch && (
        <div style={{
          position: "absolute", top: 8, right: 8, zIndex: 2,
          fontSize: 8.5, fontFamily: "var(--ff-mono)", color: "var(--ink-3)",
          padding: "2px 6px", border: "1px solid var(--rule)", background: "var(--bg-0)", letterSpacing: "0.08em",
        }}>{side === "batter" ? "打者視点" : "投手視点"}</div>
      )}
      {children}
    </div>
  );
};

/* ============================================================
   COUNT MATRIX — 12 counts, recommended pitch
============================================================ */
const CountMatrixPanel = ({ counts, view }) => {
  const confColor = { HIGH: "var(--pos)", MED: "var(--amber)", LOW: "var(--neg)" };
  const grid = [];
  for (let b = 0; b <= 3; b++) {
    for (let s = 0; s <= 2; s++) {
      const c = counts.find(x => x.c === `${b}-${s}`);
      grid.push({ b, s, ...c });
    }
  }
  return (
    <div style={{ border: "1px solid var(--rule)" }}>
      <PanelHeader title={view === "batter" ? "COUNT · 打者の狙い球" : view === "pitcher" ? "COUNT · 配球コール" : "COUNT-STATE CALL MATRIX"} sub={view === "batter" ? "予測される投球" : "カウント別推奨球種"}/>
      <div style={{ padding: 14 }}>
        <div style={{ display: "grid", gridTemplateColumns: "30px repeat(3, 1fr)", gap: 4 }}>
          <div></div>
          {[0,1,2].map(s => <div key={s} className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", textAlign: "center", letterSpacing: "0.08em" }}>{s} STR</div>)}
          {[0,1,2,3].map(b => (
            <Fragment key={b}>
              <div className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", display: "flex", alignItems: "center", letterSpacing: "0.08em" }}>{b}B</div>
              {[0,1,2].map(s => {
                const cell = grid.find(g => g.b === b && g.s === s);
                if (!cell || !cell.call) return <div key={s} style={{ aspectRatio: "1.6/1", background: "var(--bg-2)", opacity: 0.4 }}/>;
                return (
                  <div key={s} style={{
                    aspectRatio: "1.6/1", background: "var(--bg-1)",
                    border: `1px solid ${confColor[cell.conf]}`,
                    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 1,
                  }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: confColor[cell.conf], fontFamily: "var(--ff-mono)" }}>{cell.call}</span>
                    <span className="t-mono" style={{ fontSize: 8, color: "var(--ink-3)", letterSpacing: "0.05em" }}>{cell.conf}</span>
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>
        <div style={{ display: "flex", gap: 14, marginTop: 12, fontSize: 9.5, fontFamily: "var(--ff-mono)" }}>
          {[
            { k: "HIGH", c: "var(--pos)" },
            { k: "MED",  c: "var(--amber)" },
            { k: "LOW",  c: "var(--neg)" },
          ].map(l => (
            <div key={l.k} style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 9, height: 9, border: `1px solid ${l.c}` }}/>
              <span style={{ color: "var(--ink-3)", letterSpacing: "0.08em" }}>{l.k} CONF.</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   COMPS — similar pitcher matchups
============================================================ */
const CompsPanel = ({ comps, pitcher }) => (
  <div style={{ border: "1px solid var(--rule)" }}>
    <PanelHeader title="COMPARABLE MATCHUPS" sub="類似投手との対戦実績"/>
    <div style={{ padding: 12 }}>
      {comps.map((c, i) => (
        <div key={c.vs} style={{
          padding: "10px 4px", borderBottom: i < comps.length-1 ? "1px solid var(--rule-dim)" : "none",
        }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 5 }}>
            <span style={{ fontSize: 12, color: "var(--ink-0)", fontWeight: 600 }}>{c.vs}</span>
            <div style={{ flex: 1 }}/>
            <span className="t-mono" style={{ fontSize: 10, color: "var(--amber)" }}>SIM {c.sim}%</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <div style={{ flex: 1, height: 4, background: "var(--bg-2)" }}>
              <div style={{ width: `${c.sim}%`, height: "100%", background: "var(--amber)" }}/>
            </div>
          </div>
          <div style={{ display: "flex", gap: 12, fontSize: 10, fontFamily: "var(--ff-mono)", color: "var(--ink-2)" }}>
            <span>OPS <strong style={{ color: "var(--ink-0)" }}>{c.paOPS}</strong></span>
            <span>K {c.k}</span>
            <span>PA {c.pa}</span>
          </div>
        </div>
      ))}
    </div>
  </div>
);

/* ============================================================
   RECENT PA — last 10 plate appearances
============================================================ */
const RecentPAPanel = ({ recent }) => {
  const outcomeColor = (pa) => {
    if (pa === "HR") return "var(--amber)";
    if (pa === "BB") return "var(--pos)";
    if (pa === "K") return "var(--neg)";
    if (["1B","2B","3B"].includes(pa)) return "var(--pos)";
    return "var(--ink-2)";
  };
  return (
    <div style={{ border: "1px solid var(--rule)" }}>
      <PanelHeader title="LAST 10 PA · 直近対戦"/>
      <div style={{ padding: "8px 14px 14px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(10, 1fr)", gap: 6 }}>
          {recent.map((r, i) => (
            <div key={i} style={{
              border: `1px solid ${outcomeColor(r.pa)}`,
              padding: "8px 6px",
              display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
              background: r.pa === "HR" ? "oklch(from var(--amber) l c h / 0.1)" : "var(--bg-1)",
            }}>
              <span className="t-mono" style={{ fontSize: 8.5, color: "var(--ink-4)", letterSpacing: "0.06em" }}>{r.d}</span>
              <span style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--ff-head)", color: outcomeColor(r.pa) }}>{r.pa}</span>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 6 }}>
          {recent.slice(0, 4).map((r, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10.5 }}>
              <span className="t-mono" style={{ width: 30, color: outcomeColor(r.pa), fontWeight: 700 }}>{r.pa}</span>
              <span style={{ color: "var(--ink-3)", fontSize: 9 }}>{r.d}</span>
              <span style={{ color: "var(--ink-2)" }}>{r.note}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   EXEC SUMMARY — short narrative
============================================================ */
const ExecSummaryPanel = ({ batter, pitcher, headline }) => (
  <div style={{ border: "1px solid var(--amber)", background: "oklch(from var(--amber) l c h / 0.05)" }}>
    <div style={{ padding: "10px 14px", background: "oklch(from var(--amber) l c h / 0.12)", borderBottom: "1px solid var(--amber-dim)", display: "flex", alignItems: "center", gap: 8 }}>
      <Icon name="sparkle" size={13} style={{ color: "var(--amber)" }}/>
      <span className="h-label" style={{ color: "var(--amber)" }}>EXECUTIVE SUMMARY</span>
      <div style={{ flex: 1 }}/>
      <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>AI · 3 INSIGHTS</span>
    </div>
    <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
      <SummaryRow num="01" tone="amber" title="BATTER の強み" body={`${batter.name}は速球真ん中に対し xwOBA .640、HardHit% 52%。中央ゾーンの4-Seam は被弾リスク高。`}/>
      <SummaryRow num="02" tone="pos"   title="PITCHER の武器" body={`${pitcher.name}のフォークボール（被xwOBA .184、Whiff 41.7%）は今カードの決め球。0-1, 1-2, 2-2 で連投推奨。`}/>
      <SummaryRow num="03" tone="info"  title="戦術ポイント"   body="プル48%・SLG.612 のため一二塁間シフト。BB% 14.3 と選球眼があり、ボール先行は厳禁。" />
    </div>
    <div style={{ padding: "10px 14px", borderTop: "1px solid var(--amber-dim)", display: "flex", gap: 8 }}>
      <button style={{ flex: 1, padding: "7px", background: "var(--amber)", color: "var(--bg-0)", fontFamily: "var(--ff-mono)", fontSize: 10.5, fontWeight: 700, letterSpacing: "0.1em" }}>
        ASK AI · 詳細を深掘る
      </button>
      <button style={{ padding: "7px 12px", border: "1px solid var(--rule)", color: "var(--ink-2)", fontFamily: "var(--ff-mono)", fontSize: 10.5, letterSpacing: "0.08em" }}>
        フル長文版
      </button>
    </div>
  </div>
);

const SummaryRow = ({ num, tone, title, body }) => {
  const c = { amber: "var(--amber)", pos: "var(--pos)", info: "var(--info)", neg: "var(--neg)" }[tone];
  return (
    <div style={{ display: "flex", gap: 10 }}>
      <div style={{ width: 3, background: c, flexShrink: 0 }}/>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 3 }}>
          <span className="t-mono" style={{ fontSize: 10, color: c, fontWeight: 700 }}>{num}</span>
          <span className="h-display" style={{ fontSize: 12, color: "var(--ink-0)" }}>{title}</span>
        </div>
        <div style={{ fontSize: 11.5, color: "var(--ink-1)", lineHeight: 1.55 }}>{body}</div>
      </div>
    </div>
  );
};

/* ============================================================
   SHARED — Panel header, arrow chip
============================================================ */
const PanelHeader = ({ title, sub }) => (
  <div className="rule-b" style={{ padding: "9px 14px", background: "var(--bg-1)", display: "flex", alignItems: "center", gap: 10 }}>
    <span className="h-label" style={{ color: "var(--ink-0)" }}>{title}</span>
    {sub && <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>{sub}</span>}
  </div>
);

const ArrowChip = ({ dir }) => {
  const map = {
    up:   { c: "var(--pos)", p: "M3 9l4-4 4 4" },
    down: { c: "var(--neg)", p: "M3 5l4 4 4-4" },
    flat: { c: "var(--ink-3)", p: "M3 7h8" },
  };
  const x = map[dir] || map.flat;
  return <svg width="11" height="11" viewBox="0 0 14 14" fill="none" stroke={x.c} strokeWidth="1.6" strokeLinecap="round"><path d={x.p}/></svg>;
};

/* ============================================================
   EMPTY STATE — only batter+pitcher pickers (no season)
============================================================ */
const StrategyEmptyState = ({ onGenerate, batter, pitcher }) => (
  <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 40 }}>
    <div style={{ width: 560, border: "1px solid var(--rule)", background: "var(--bg-1)" }}>
      <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--rule)" }}>
        <div className="t-mono" style={{ fontSize: 10, color: "var(--amber)", letterSpacing: "0.16em", marginBottom: 6 }}>STRATEGY · 対戦戦略</div>
        <div className="h-display" style={{ fontSize: 22, color: "var(--ink-0)" }}>MATCHUP REPORT</div>
        <div style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 4 }}>打者と投手を選択してレポートを生成します。</div>
      </div>
      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
        <PlayerPicker label="BATTER · 打者" data={batter} accent="var(--pos)"/>
        <PlayerPicker label="PITCHER · 投手" data={pitcher} accent="var(--info)"/>
        <button onClick={onGenerate} style={{ marginTop: 8, padding: "12px", background: "var(--amber)", color: "var(--bg-0)", fontFamily: "var(--ff-mono)", fontSize: 12, fontWeight: 700, letterSpacing: "0.14em" }}>
          GENERATE REPORT
        </button>
      </div>
    </div>
  </div>
);

export default StrategyScreen;
