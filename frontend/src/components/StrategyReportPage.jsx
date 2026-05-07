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
import React, { useState, useEffect, useRef, Fragment } from 'react';
import Icon from './layout/Icon.jsx';

/* MLB 30球団のチームカラー（primary color, ダークテーマで視認可能なトーンを採用）。
   出典: Wikipedia 各球団ページ / Team Color Codes コミュニティ。
   未マッピング略号は accent (--pos / --info) にフォールバック。 */
const TEAM_COLORS = {
  // AL East
  BAL: "#DF4601", // Orioles オレンジ
  BOS: "#BD3039", // Red Sox レッド
  NYY: "#1D2D5C", // Yankees ネイビー（少し明るめに）
  TB:  "#8FBCE6", // Rays ライトブルー
  TOR: "#134A8E", // Blue Jays ブルー
  // AL Central
  CWS: "#C4CED4", // White Sox シルバー（黒は背景同化のためシルバー採用）
  CHW: "#C4CED4",
  CLE: "#E50022", // Guardians レッド
  DET: "#FA4616", // Tigers オレンジ寄り（ネイビーは Yankees と被るため）
  KC:  "#004687", // Royals ロイヤルブルー
  KCR: "#004687",
  MIN: "#D31145", // Twins レッド
  // AL West
  HOU: "#EB6E1F", // Astros オレンジ
  LAA: "#BA0021", // Angels レッド
  OAK: "#EFB21E", // Athletics ゴールド
  ATH: "#EFB21E",
  SEA: "#005C5C", // Mariners ティール
  TEX: "#C0111F", // Rangers レッド
  // NL East
  ATL: "#CE1141", // Braves レッド
  MIA: "#00A3E0", // Marlins ブルー
  NYM: "#FF5910", // Mets オレンジ
  PHI: "#E81828", // Phillies レッド
  WSH: "#AB0003", // Nationals レッド
  WAS: "#AB0003",
  // NL Central
  CHC: "#0E3386", // Cubs ブルー
  CIN: "#C6011F", // Reds レッド
  MIL: "#FFC52F", // Brewers ゴールド
  PIT: "#FDB827", // Pirates ゴールド
  STL: "#C41E3A", // Cardinals レッド
  // NL West
  ARI: "#A71930", // D-backs セドナレッド
  COL: "#9F69D6", // Rockies パープル（明るめ）
  LAD: "#3FA1FF", // Dodgers ライトブルー
  SD:  "#FFC425", // Padres ゴールド
  SDP: "#FFC425",
  SF:  "#FD5A1E", // Giants オレンジ
  SFG: "#FD5A1E",
};

const teamColor = (abbr, fallback) => {
  if (!abbr) return fallback;
  return TEAM_COLORS[String(abbr).toUpperCase()] || fallback;
};

const StrategyScreen = ({ getBackendURL, getAuthHeaders }) => {
  /* ============ STATE ============ */
  // Phase 1: 開発を簡素化するため batter/pitcher は固定
  const [batter, setBatter] = useState({ id: 660271, name: "Shohei Ohtani", team: "LAD", hand: "L", pos: "DH" });
  const [pitcher, setPitcher] = useState({ id: 673540, name: "Kodai Senga", team: "NYM", hand: "R", pos: "SP" });
  const [season, setSeason] = useState(2026);
  const [generated, setGenerated] = useState(false);
  const [view, setView] = useState("both"); // both | batter | pitcher

  // 選手選択時に PlayerBio を取得して team / hand / pos を埋める。
  // 検索結果には team しか含まれないため、選択直後に追加 fetch する。
  const enrichWithProfile = async (mlbid, role) => {
    try {
      const baseURL = getBackendURL ? getBackendURL() : "";
      const headers = getAuthHeaders ? await getAuthHeaders() : {};
      const url = `${baseURL}/api/v1/players/${mlbid}/profile?season=${season}`;
      const res = await fetch(url, { headers });
      if (!res.ok) return;
      const data = await res.json();
      const bio = data.bio || {};
      // シーズン別所属チームは mart 由来の KPI から取得する。
      // bio.team_abbreviation は dim_players_master = 最新シーズンのみのため、過去シーズンでは誤表示になる。
      const team = data.batting_kpi?.team || data.pitching_kpi?.team || "";
      const pos = bio.primary_position || (role === "batter" ? "" : "P");
      const hand = role === "batter" ? (bio.bat_side || "") : (bio.pitch_hand || "");
      const name = bio.full_name || "";
      const setter = role === "batter" ? setBatter : setPitcher;
      setter(prev => ({
        ...prev,
        ...(name ? { name } : {}),
        ...(team ? { team } : {}),
        ...(hand ? { hand } : {}),
        ...(pos ? { pos } : {}),
      }));
    } catch (e) {
      console.warn("profile enrich failed", e);
    }
  };

  const onSelectPlayer = (role, item) => {
    // PlayerSearchItem -> { mlbid, player_name, team, league }
    const setter = role === "batter" ? setBatter : setPitcher;
    setter({
      id: item.mlbid,
      name: item.player_name,
      team: item.team || "",
      hand: "",
      pos: role === "batter" ? "" : "P",
    });
    // hand/pos は profile から非同期で埋める
    if (item.mlbid) enrichWithProfile(item.mlbid, role);
  };

  // シーズン変更時にも team / hand / pos / name を再取得する。
  // dim_players_master は最新シーズンのみ、mart は season 別なので、
  // シーズン切替で正しい所属チームを表示するために再 enrich が必要。
  useEffect(() => {
    if (batter.id) enrichWithProfile(batter.id, "batter");
    if (pitcher.id) enrichWithProfile(pitcher.id, "pitcher");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [season]);

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
        const url = `${baseURL}/api/v1/strategy-report/kpi-band?batter_id=${batter.id}&pitcher_id=${pitcher.id}&season=${season}`;
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
  }, [batter.id, pitcher.id, season, getBackendURL, getAuthHeaders]);

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

  // Pitch arsenal — pitcher's pitches, batter's xwOBA against, recommendation (backend fetched)
  const [arsenalState, setArsenalState] = useState({ loading: true, arsenal: [], error: null });

  useEffect(() => {
    let cancelled = false;
    setArsenalState(prev => ({ ...prev, loading: true, error: null }));
    (async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/pitch-arsenal?pitcher_id=${pitcher.id}&season=${season}`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setArsenalState({
          loading: false,
          arsenal: Array.isArray(data.arsenal) ? data.arsenal : [],
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        console.error("pitch-arsenal fetch failed", e);
        setArsenalState({ loading: false, arsenal: [], error: e.message });
      }
    })();
    return () => { cancelled = true; };
  }, [pitcher.id, season, getBackendURL, getAuthHeaders]);

  const arsenal = arsenalState.arsenal;

  // Heat zone — 5x5 grid of xwOBA (batter's hot/cold) — backend fetched
  const [heatZoneState, setHeatZoneState] = useState({
    loading: true, zone: null, counts: null, totalPa: 0, error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setHeatZoneState(prev => ({ ...prev, loading: true, error: null }));
    (async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/heat-zone?batter_id=${batter.id}&season=${season}`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        // データが疎なセルは null のまま渡す（HeatZonePanel 側で表示処理）
        setHeatZoneState({
          loading: false,
          zone: Array.isArray(data.zone) ? data.zone : null,
          counts: data.counts || null,
          totalPa: data.total_pa || 0,
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        console.error("heat-zone fetch failed", e);
        setHeatZoneState({
          loading: false, zone: null, counts: null, totalPa: 0, error: e.message,
        });
      }
    })();
    return () => { cancelled = true; };
  }, [batter.id, season, getBackendURL, getAuthHeaders]);

  const heatZone = heatZoneState.zone;

  // Spray distribution by field third (backend fetched)
  const [sprayState, setSprayState] = useState({ loading: true, spray: [], totalBip: 0, error: null });

  useEffect(() => {
    let cancelled = false;
    setSprayState(prev => ({ ...prev, loading: true, error: null }));
    (async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/spray?batter_id=${batter.id}&season=${season}`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setSprayState({
          loading: false,
          spray: Array.isArray(data.spray) ? data.spray : [],
          totalBip: data.total_bip || 0,
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        console.error("spray fetch failed", e);
        setSprayState({ loading: false, spray: [], totalBip: 0, error: e.message });
      }
    })();
    return () => { cancelled = true; };
  }, [batter.id, season, getBackendURL, getAuthHeaders]);

  const spray = sprayState.spray;

  // Count-state matrix — 投手のカウント別最頻球種（view: both / pitcher のみ表示）
  // 打者は関与しない。打者ユーザが「対戦投手の傾向」を確認するための参考情報。
  const [countMatrixState, setCountMatrixState] = useState({
    loading: true, counts: [], error: null,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setCountMatrixState(prev => ({ ...prev, loading: true, error: null }));
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/count-matrix`
          + `?pitcher_id=${pitcher.id}&season=${season}`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setCountMatrixState({
          loading: false,
          counts: Array.isArray(data.counts) ? data.counts : [],
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        console.error("count-matrix fetch failed", e);
        setCountMatrixState({ loading: false, counts: [], error: e.message });
      }
    })();
    return () => { cancelled = true; };
  }, [pitcher.id, season, getBackendURL, getAuthHeaders]);

  const counts = countMatrixState.counts;

  // Last 10 PA timeline — 当該打者×投手の通算 直近10打席（バックエンド集計）
  const [recentPaState, setRecentPaState] = useState({
    loading: true, recent: [], error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setRecentPaState(prev => ({ ...prev, loading: true, error: null }));
    (async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/recent-pa`
          + `?batter_id=${batter.id}&pitcher_id=${pitcher.id}&limit=10`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setRecentPaState({
          loading: false,
          recent: Array.isArray(data.recent) ? data.recent : [],
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        console.error("recent-pa fetch failed", e);
        setRecentPaState({ loading: false, recent: [], error: e.message });
      }
    })();
    return () => { cancelled = true; };
  }, [batter.id, pitcher.id, getBackendURL, getAuthHeaders]);

  const recent = recentPaState.recent;

  // Tactics — split by side (BATTER / PITCHER)
  // Tactics — AI 生成（手動トリガー型）。
  // ランディング時は自動生成しない（コスト対策）。
  // batter/pitcher を並列で LLM 呼び出し。打者・投手の選択が変わったら結果をリセット。
  const [tacticsState, setTacticsState] = useState({
    generated: false,
    batter:  { loading: false, tactics: [], verified: null, error: null },
    pitcher: { loading: false, tactics: [], verified: null, error: null },
  });

  // 打者・投手・シーズンの組み合わせが変わったら戦術結果をクリア（古い結果が残らないように）
  useEffect(() => {
    setTacticsState({
      generated: false,
      batter:  { loading: false, tactics: [], verified: null, error: null },
      pitcher: { loading: false, tactics: [], verified: null, error: null },
    });
  }, [batter.id, pitcher.id, season]);

  const generateTactics = async () => {
    setTacticsState({
      generated: true,
      batter:  { loading: true, tactics: [], verified: null, error: null },
      pitcher: { loading: true, tactics: [], verified: null, error: null },
    });
    const fetchSide = async (side) => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        const url = `${baseURL}/api/v1/strategy-report/tactics`
          + `?batter_id=${batter.id}&pitcher_id=${pitcher.id}`
          + `&season=${season}&side=${side}`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        return {
          loading: false,
          tactics: Array.isArray(data.tactics) ? data.tactics : [],
          verified: data.verified === true,
          error: null,
        };
      } catch (e) {
        console.error(`tactics(${side}) fetch failed`, e);
        return { loading: false, tactics: [], verified: false, error: e.message };
      }
    };
    const [b, p] = await Promise.all([fetchSide("batter"), fetchSide("pitcher")]);
    setTacticsState({ generated: true, batter: b, pitcher: p });
  };

  const batterTactics = tacticsState.batter.tactics;
  const pitcherTactics = tacticsState.pitcher.tactics;
  const tacticsGenerated = tacticsState.generated;
  const tacticsAnyLoading = tacticsState.batter.loading || tacticsState.pitcher.loading;

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
    return (
      <StrategyEmptyState
        onGenerate={() => setGenerated(true)}
        batter={batter} pitcher={pitcher}
        season={season} setSeason={setSeason}
        onSelectPlayer={onSelectPlayer}
        getBackendURL={getBackendURL} getAuthHeaders={getAuthHeaders}
      />
    );
  }

  /* ============ RENDER ============ */
  return (
    <div data-screen-label="STRATEGY · MATCHUP REPORT" className="strategy-report-print-target" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--bg-0)", overflowY: "auto" }}>
      {/* 印刷用 CSS:
         - サイドバー/ヘッダなど外側 UI を強制的に隠す（visibility ベース）
         - 印刷対象だけを画面全体に展開し、自然にページ分割させる
         - ダーク背景を保持
      */}
      <style>{`
        @media print {
          /* 1-pager: レポート全体を1ページに収めるため縦長カスタムサイズ
             (A4 横の幅 297mm × 縦に長い 720mm)。コンテンツ次第で下部に空白が出るのは許容。 */
          @page { size: 297mm 720mm; margin: 6mm; }
          html, body {
            background: #0a0a0a !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            margin: 0 !important;
            padding: 0 !important;
          }
          /* 全要素を一旦不可視にしてから印刷対象だけ可視化 */
          body * { visibility: hidden !important; }
          .strategy-report-print-target,
          .strategy-report-print-target * { visibility: visible !important; }

          /* 印刷対象を画面左上から全幅で展開（外側レイアウトの flex 制約を無効化） */
          .strategy-report-print-target {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            height: auto !important;
            overflow: visible !important;
            display: block !important;
          }

          /* 操作系の非表示（強い優先度） */
          .no-print, .no-print * { display: none !important; visibility: hidden !important; }

          /* 1-pager: ページ送りを抑止（途中で切れるのを防ぐ。サイズが足りなければ
             画面プレビュー側で切れるが、それは page サイズで吸収） */
          .strategy-report-print-target,
          .strategy-report-print-target * {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
          }
          /* スクロール領域を flow に */
          .strategy-report-print-target [style*="overflow"] {
            overflow: visible !important;
            max-height: none !important;
          }
        }
      `}</style>
      {/* ============ SELECTOR BAR ============ */}
      <SelectorBar
        batter={batter} pitcher={pitcher} setBatter={setBatter} setPitcher={setPitcher}
        season={season} setSeason={setSeason}
        onSelectPlayer={onSelectPlayer}
        getBackendURL={getBackendURL} getAuthHeaders={getAuthHeaders}
        swap={swap}
        onRegenerate={() => { setGenerated(false); setTimeout(() => setGenerated(true), 220); }}
        view={view} setView={setView}
      />

      {/* ============ HERO MATCHUP ============ */}
      <MatchupHero batter={batter} pitcher={pitcher} season={season} headline={headline} view={view}/>

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
        <ViewWrap view={view} side="batter">
          <HeatZonePanel
            zone={heatZone} batter={batter} view={view}
            loading={heatZoneState.loading} error={heatZoneState.error}
          />
        </ViewWrap>
        <ViewWrap view={view} side="pitcher">
          <ArsenalPanel
            arsenal={arsenal} pitcher={pitcher} view={view}
            loading={arsenalState.loading} error={arsenalState.error}
          />
        </ViewWrap>
        <ViewWrap view={view} side="batter">
          <SprayPanel
            spray={spray} batter={batter}
            loading={sprayState.loading} error={sprayState.error}
          />
        </ViewWrap>
      </div>

      {/* ============ ROW 2: TACTICS DUAL + COUNT MATRIX ============ */}
      {/* COUNT MATRIX は投手の配球傾向を示すため、view が batter のときは列ごと非表示。 */}
      <div className="rule-b" style={{
        padding: "18px 28px",
        display: "grid",
        gridTemplateColumns: view === "batter" ? "1fr 1fr" : "1fr 1fr 360px",
        gap: 14,
      }}>
        <ViewWrap view={view} side="batter">
          <TacticsPanel
            tactics={batterTactics} side="BATTER" sideLabel="打者戦術" accent="var(--pos)"
            loading={tacticsState.batter.loading}
            error={tacticsState.batter.error}
            verified={tacticsState.batter.verified}
            generated={tacticsGenerated}
            anyLoading={tacticsAnyLoading}
            onGenerate={generateTactics}
          />
        </ViewWrap>
        <ViewWrap view={view} side="pitcher">
          <TacticsPanel
            tactics={pitcherTactics} side="PITCHER" sideLabel="投手戦術" accent="var(--info)"
            loading={tacticsState.pitcher.loading}
            error={tacticsState.pitcher.error}
            verified={tacticsState.pitcher.verified}
            generated={tacticsGenerated}
            anyLoading={tacticsAnyLoading}
            onGenerate={generateTactics}
          />
        </ViewWrap>
        {view !== "batter" && (
          <CountMatrixPanel
            counts={counts}
            view={view}
            loading={countMatrixState.loading}
            error={countMatrixState.error}
          />
        )}
      </div>

      {/* ============ ROW 2.5: COMPS ============ */}
      <div className="rule-b" style={{ padding: "18px 28px", display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
        <CompsPanel comps={comps} pitcher={pitcher}/>
      </div>

      {/* ============ ROW 3: RECENT TIMELINE + EXEC SUMMARY ============ */}
      <div style={{ padding: "18px 28px 24px", display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 14 }}>
        <RecentPAPanel
          recent={recent}
          loading={recentPaState.loading}
          error={recentPaState.error}
        />
        <ExecSummaryPanel batter={batter} pitcher={pitcher} headline={headline}/>
      </div>
    </div>
  );
};

/* ============================================================
   SELECTOR BAR (シーズン除外、選手 2 つだけ)
============================================================ */
const SelectorBar = ({
  batter, pitcher, season, setSeason,
  onSelectPlayer, getBackendURL, getAuthHeaders,
  swap, onRegenerate, view, setView,
}) => (
  <div className="rule-b no-print" style={{ padding: "14px 28px", display: "flex", alignItems: "center", gap: 14, background: "var(--bg-0)" }}>
    <div className="h-label" style={{ fontSize: 9.5, color: "var(--amber)", letterSpacing: "0.14em" }}>STRATEGY · 対戦戦略</div>
    <div style={{ width: 1, height: 22, background: "var(--rule)" }}/>

    <PlayerSearchPicker
      label="BATTER · 打者" data={batter} accent="var(--pos)" dim={view === "pitcher"}
      role="batter"
      onSelect={(item) => onSelectPlayer && onSelectPlayer("batter", item)}
      getBackendURL={getBackendURL} getAuthHeaders={getAuthHeaders}
    />
    <button onClick={swap} title="入れ替え" style={{ width: 28, height: 28, border: "1px solid var(--rule)", color: "var(--ink-3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 8h14l-3-3M21 16H7l3 3"/></svg>
    </button>
    <PlayerSearchPicker
      label="PITCHER · 投手" data={pitcher} accent="var(--info)" dim={view === "batter"}
      role="pitcher"
      onSelect={(item) => onSelectPlayer && onSelectPlayer("pitcher", item)}
      getBackendURL={getBackendURL} getAuthHeaders={getAuthHeaders}
    />

    {/* SEASON SELECT */}
    <div style={{ marginLeft: 4, display: "flex", flexDirection: "column", gap: 3 }}>
      <span className="h-label" style={{ fontSize: 8.5, color: "var(--ink-3)" }}>SEASON · 年度</span>
      <select
        value={season}
        onChange={(e) => setSeason && setSeason(Number(e.target.value))}
        style={{
          padding: "6px 10px", border: "1px solid var(--rule)", background: "var(--bg-1)",
          color: "var(--ink-0)", fontFamily: "var(--ff-mono)", fontSize: 12,
          letterSpacing: "0.06em", cursor: "pointer",
        }}
      >
        {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015].map(y => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>
    </div>

    {/* VIEW TOGGLE */}
    <div style={{ marginLeft: 14, display: "flex", alignItems: "center", gap: 8 }}>
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
    <button
      onClick={() => window.print()}
      title="印刷ダイアログを開いて PDF として保存"
      style={{
        padding: "8px 12px", border: "1px solid var(--rule)", color: "var(--ink-2)",
        fontFamily: "var(--ff-mono)", fontSize: 10.5, letterSpacing: "0.1em",
        background: "transparent", cursor: "pointer",
      }}
    >
      <Icon name="send" size={11} style={{ marginRight: 6, verticalAlign: "-1px" }}/>EXPORT
    </button>
  </div>
);

/* PlayerSearchPicker — クリックで開閉する検索可能ドロップダウン。
   入力に応じて /api/v1/players/search を debounce 呼び出し、選択で onSelect。 */
const PlayerSearchPicker = ({
  label, data, accent, dim, role,
  onSelect, getBackendURL, getAuthHeaders,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  // 外側クリックで閉じる
  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  // 開いたとき入力欄にフォーカス
  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current && inputRef.current.focus(), 0);
    }
  }, [open]);

  // debounce (250ms) 検索
  useEffect(() => {
    if (!open) return;
    const q = (query || "").trim();
    if (q.length < 2) { setResults([]); setError(null); return; }
    let cancelled = false;
    setSearching(true);
    const t = setTimeout(async () => {
      try {
        const baseURL = getBackendURL ? getBackendURL() : "";
        const headers = getAuthHeaders ? await getAuthHeaders() : {};
        // feature flag: VITE_USE_AUTOCOMPLETE_API=true で新統合エンドポイントへ切替
        const useAutocomplete =
          String(import.meta.env.VITE_USE_AUTOCOMPLETE_API).toLowerCase() === "true";
        const url = useAutocomplete
          ? `${baseURL}/api/v1/players/autocomplete?q=${encodeURIComponent(q)}&context=all&limit=20`
          : `${baseURL}/api/v1/players/search?q=${encodeURIComponent(q)}`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (cancelled) return;

        // 旧 API: { results: [{mlbid, player_name, team, league}] }
        // 新 API: { results: [{mlbid, full_name, team, ...}] }
        // 既存呼び出し側 (handleSelect) は player_name を読むので旧形式に揃える。
        const rawResults = Array.isArray(json.results) ? json.results : [];
        const normalized = useAutocomplete
          ? rawResults.map((it) => ({
              mlbid: it.mlbid,
              player_name: it.full_name,
              team: it.team || null,
              league: null,
            }))
          : rawResults;
        setResults(normalized.slice(0, 20));
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(e.message);
        setResults([]);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);
    return () => { cancelled = true; clearTimeout(t); };
  }, [query, open, getBackendURL, getAuthHeaders]);

  const handleSelect = (item) => {
    onSelect && onSelect(item);
    setOpen(false);
    setQuery("");
    setResults([]);
  };

  return (
    <div ref={containerRef} style={{
      display: "flex", flexDirection: "column", gap: 3,
      opacity: dim ? 0.42 : 1, transition: "opacity .2s",
      position: "relative",
    }}>
      <span className="h-label" style={{ fontSize: 8.5, color: "var(--ink-3)" }}>{label}</span>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: "flex", alignItems: "center", gap: 9, padding: "6px 12px",
          border: `1px solid ${open ? accent : "var(--rule)"}`,
          background: "var(--bg-1)", minWidth: 280, cursor: "pointer",
        }}
      >
        <span style={{ width: 6, height: 6, background: accent, transform: "rotate(45deg)" }}/>
        <span style={{ fontSize: 13, color: "var(--ink-0)", fontWeight: 600, fontFamily: "var(--ff-head)", letterSpacing: "0.02em", textTransform: "uppercase" }}>{data.name || "—"}</span>
        {data.team && (
          <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", padding: "1px 5px", border: "1px solid var(--rule-dim)" }}>{data.team}</span>
        )}
        {data.hand && (
          <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{data.hand}{role === "batter" ? "HB" : "HP"}</span>
        )}
        <div style={{ flex: 1 }}/>
        <Icon name="chevD" size={12} style={{ color: "var(--ink-3)" }}/>
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "100%", left: 0, marginTop: 4,
          width: "100%", minWidth: 320, zIndex: 50,
          border: `1px solid ${accent}`, background: "var(--bg-0)",
          boxShadow: "0 6px 20px oklch(0 0 0 / 0.5)",
        }}>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={role === "batter" ? "打者名を検索 (2文字以上)" : "投手名を検索 (2文字以上)"}
            style={{
              width: "100%", padding: "8px 10px", border: "none",
              borderBottom: "1px solid var(--rule)",
              background: "var(--bg-1)", color: "var(--ink-0)",
              fontFamily: "var(--ff-mono)", fontSize: 12, outline: "none",
            }}
          />
          <div style={{ maxHeight: 280, overflowY: "auto" }}>
            {searching && (
              <div className="t-mono" style={{ padding: "10px 12px", fontSize: 10, color: "var(--ink-3)" }}>SEARCHING…</div>
            )}
            {!searching && error && (
              <div className="t-mono" style={{ padding: "10px 12px", fontSize: 10, color: "var(--neg)" }}>ERROR: {error}</div>
            )}
            {!searching && !error && query.trim().length < 2 && (
              <div className="t-mono" style={{ padding: "10px 12px", fontSize: 10, color: "var(--ink-4)" }}>2 文字以上で検索開始</div>
            )}
            {!searching && !error && query.trim().length >= 2 && results.length === 0 && (
              <div className="t-mono" style={{ padding: "10px 12px", fontSize: 10, color: "var(--ink-4)" }}>該当なし</div>
            )}
            {!searching && results.map((it) => (
              <button
                key={it.mlbid}
                onClick={() => handleSelect(it)}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  width: "100%", padding: "8px 12px", textAlign: "left",
                  border: "none", background: "transparent",
                  borderBottom: "1px solid var(--rule-dim)", cursor: "pointer",
                  color: "var(--ink-1)",
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-1)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <span style={{ fontSize: 12.5, color: "var(--ink-0)", fontWeight: 600, fontFamily: "var(--ff-head)", letterSpacing: "0.02em", textTransform: "uppercase" }}>{it.player_name}</span>
                {it.team && (
                  <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", padding: "1px 5px", border: "1px solid var(--rule-dim)" }}>{it.team}</span>
                )}
                <div style={{ flex: 1 }}/>
                <span className="t-mono" style={{ fontSize: 9, color: "var(--ink-4)" }}>#{it.mlbid}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/* ============================================================
   HERO MATCHUP — vs ・ Edge bar ・ Headline
============================================================ */
const MatchupHero = ({ batter, pitcher, season, headline, view }) => {
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
          <div className="t-mono" style={{ fontSize: 10, color: "var(--amber)", letterSpacing: "0.2em", marginBottom: 8 }}>MATCHUP REPORT · {season}</div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, marginBottom: 14 }}>
            <span className="h-display" style={{ fontSize: 40, color: teamColor(batter.team, "var(--pos)") }}>{batter.team}</span>
            <span className="h-display" style={{ fontSize: 28, color: "var(--ink-3)" }}>VS</span>
            <span className="h-display" style={{ fontSize: 40, color: teamColor(pitcher.team, "var(--info)") }}>{pitcher.team}</span>
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

const PlayerCard = ({ data, role, accent, align }) => {
  // 打者は LHB/RHB/SHB（Batter）、投手は LHP/RHP（Pitcher）を表記する。
  const handSuffix = role === "BATTER" ? "HB" : "HP";
  const handLabel = data.hand ? `${data.hand}${handSuffix}` : "";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: align === "right" ? "flex-end" : "flex-start" }}>
      <div className="t-mono" style={{ fontSize: 10, color: accent, letterSpacing: "0.14em", marginBottom: 4 }}>{role} · {data.pos}</div>
      <div className="h-display" style={{ fontSize: 30, color: "var(--ink-0)", lineHeight: 1, letterSpacing: "0.01em" }}>{data.name.toUpperCase()}</div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        {data.team && (
          <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-1)", padding: "2px 8px", border: "1px solid var(--rule)", background: "var(--bg-1)" }}>{data.team}</span>
        )}
        {handLabel && (
          <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-2)", padding: "2px 8px", border: "1px solid var(--rule)", background: "var(--bg-1)" }}>{handLabel}</span>
        )}
        <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-2)", padding: "2px 8px", border: "1px solid var(--rule)", background: "var(--bg-1)" }}>#{data.id}</span>
      </div>
    </div>
  );
};

/* ============================================================
   PanelStatePlaceholder — loading / error / empty 共通表示
============================================================ */
const PanelStatePlaceholder = ({ loading, error, empty, minHeight = 280, label = "" }) => {
  let msg = label;
  let color = "var(--ink-3)";
  if (loading) msg = "LOADING…";
  else if (error) { msg = `ERROR: ${error}`; color = "var(--neg)"; }
  else if (empty) msg = "NO DATA";
  return (
    <div className="t-mono" style={{
      minHeight, padding: 14, display: "flex",
      alignItems: "center", justifyContent: "center",
      fontSize: 10.5, color, letterSpacing: "0.08em",
    }}>{msg}</div>
  );
};

/* ============================================================
   HEAT ZONE — 5x5 strike zone xwOBA
============================================================ */
const HeatZonePanel = ({ zone, view, loading = false, error = null }) => {
  const isEmpty = !Array.isArray(zone) || zone.length === 0;
  const title = view === "pitcher" ? "HEAT ZONE · 避けるゾーン" : "HEAT ZONE · 狙いゾーン";
  if (loading || error || isEmpty) {
    return (
      <div style={{ border: "1px solid var(--rule)" }}>
        <PanelHeader title={title} sub="xwOBA · 5×5"/>
        <PanelStatePlaceholder loading={loading} error={error} empty={isEmpty}/>
      </div>
    );
  }
  const colorFor = (v) => {
    if (v == null) return "var(--bg-2)";
    const t = Math.max(0, Math.min(1, (v - .150) / (.640 - .150)));
    const lightness = 0.32 + t * 0.45;
    const chroma = 0.04 + t * 0.18;
    const hue = 240 - t * 210;
    return `oklch(${lightness} ${chroma} ${hue})`;
  };
  return (
    <div style={{ border: "1px solid var(--rule)", display: "flex", flexDirection: "column" }}>
      <PanelHeader title={title} sub="xwOBA · 5×5"/>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
        {/* Strike zone */}
        <div style={{ position: "relative", aspectRatio: "1 / 1", background: "var(--bg-1)", border: "1px solid var(--rule)" }}>
          <div style={{ position: "absolute", inset: 0, display: "grid", gridTemplateColumns: "repeat(5,1fr)", gridTemplateRows: "repeat(5,1fr)" }}>
            {zone.flatMap((row, ri) => row.map((v, ci) => {
              const inZone = ri >= 1 && ri <= 3 && ci >= 1 && ci <= 3;
              const label = v == null ? "—" : ("." + String(Math.round(v*1000)).padStart(3,"0")).replace(/^0/, "");
              return (
                <div key={`${ri}-${ci}`} style={{
                  background: colorFor(v),
                  border: inZone ? "0.5px solid oklch(1 0 0 / 0.18)" : "0.5px dashed oklch(1 0 0 / 0.08)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: "var(--ff-mono)", fontSize: 9.5, fontWeight: 700,
                  color: v != null && v > .4 ? "var(--bg-0)" : "var(--ink-0)",
                }}>{label}</div>
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
const ArsenalPanel = ({ arsenal, pitcher, view, loading = false, error = null }) => {
  const recColor = { neg: "var(--neg)", amber: "var(--amber)", pos: "var(--pos)" };
  const title = view === "batter" ? "OPPONENT ARSENAL · 投手シーズン" : "PITCH ARSENAL · 投手シーズン";
  const sub = `${pitcher.name} · 2026 vs 全打者`;
  const isEmpty = !Array.isArray(arsenal) || arsenal.length === 0;
  if (loading || error || isEmpty) {
    return (
      <div style={{ border: "1px solid var(--rule)" }}>
        <PanelHeader title={title} sub={sub}/>
        <PanelStatePlaceholder loading={loading} error={error} empty={isEmpty} minHeight={420}/>
      </div>
    );
  }
  return (
    <div style={{ border: "1px solid var(--rule)" }}>
      <PanelHeader title={title} sub={sub}/>
      {/* SEASON 注釈バナー */}
      <div style={{
        padding: "8px 14px",
        display: "flex", alignItems: "center", gap: 10,
        background: "oklch(from var(--info) l c h / 0.06)",
        borderBottom: "1px solid var(--rule)",
      }}>
        <span className="t-mono" style={{
          fontSize: 9.5, fontWeight: 700, letterSpacing: "0.14em",
          padding: "2px 7px", border: "1px solid var(--info)",
          color: "var(--info)",
        }}>SEASON</span>
        <span style={{ fontSize: 11, color: "var(--ink-2)", lineHeight: 1.5 }}>
          投手の<strong style={{ color: "var(--ink-0)" }}>シーズン全体</strong>の球種成績（vs 全打者）。
          STRATEGY タグは<strong style={{ color: "var(--ink-0)" }}>投手のシーズン傾向のみ</strong>から算出（打者の弱点反映は今後）。
        </span>
      </div>
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
        {/* 結果分布 + 打球品質散布図 */}
        <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <OutcomeMixPlot arsenal={arsenal}/>
          <QualityScatterPlot arsenal={arsenal}/>
        </div>
      </div>
    </div>
  );
};

/* OUTCOME MIX — 球種別の打席結果分布（K / GB / LD / FB / BB+HBP の積み上げ）
   投手にとってのポジティブ→ネガティブ順に下から積む。母数は events IS NOT NULL の打席。 */
const OUTCOME_CATS = [
  { key: "k_pct",  label: "K",  color: "var(--pos)",   sub: "三振" },
  { key: "gb_pct", label: "GB", color: "oklch(from var(--pos) l c h / 0.45)", sub: "ゴロ" },
  { key: "ld_pct", label: "LD", color: "var(--amber)", sub: "ライナー" },
  { key: "fb_pct", label: "FB", color: "oklch(from var(--neg) l c h / 0.55)", sub: "フライ" },
  { key: "bb_pct", label: "BB", color: "var(--neg)",   sub: "四死球" },
];

const OutcomeMixPlot = ({ arsenal }) => {
  const items = (arsenal || []).filter(p => p.outcomes && p.outcomes.pa > 0);
  return (
    <div style={{ border: "1px solid var(--rule-dim)", padding: 14, background: "var(--bg-1)" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 10 }}>
        <span className="h-label" style={{ fontSize: 11, color: "var(--ink-2)" }}>OUTCOME MIX · 打席結果分布</span>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>母数 = PA</span>
      </div>
      {items.length === 0 ? (
        <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", padding: "30px 0", textAlign: "center" }}>NO DATA</div>
      ) : (
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", justifyContent: "space-around" }}>
          {items.map(p => {
            const oc = p.outcomes;
            const pa = oc.pa || 0;
            // 各カテゴリ % を下から K → GB → LD → FB → BB の順で積む。
            return (
              <div key={p.code} title={`${p.code} · PA=${pa} · K ${oc.k_pct ?? 0}% / GB ${oc.gb_pct ?? 0}% / LD ${oc.ld_pct ?? 0}% / FB ${oc.fb_pct ?? 0}% / BB ${oc.bb_pct ?? 0}%`}
                   style={{ flex: 1, minWidth: 48, maxWidth: 90, display: "flex", flexDirection: "column", alignItems: "center", gap: 5 }}>
                <div style={{ width: "100%", height: 200, display: "flex", flexDirection: "column-reverse", border: "1px solid var(--rule-dim)" }}>
                  {OUTCOME_CATS.map(cat => {
                    const v = oc[cat.key];
                    if (v == null || v <= 0) return null;
                    return (
                      <div key={cat.key} style={{
                        height: `${v}%`, background: cat.color,
                        display: "flex", alignItems: "center", justifyContent: "center",
                      }}>
                        {v >= 8 && (
                          <span className="t-mono" style={{ fontSize: 10.5, fontWeight: 700, color: "var(--bg-0)" }}>
                            {cat.label} {Math.round(v)}%
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
                <span className="t-mono" style={{ fontSize: 11, color: "var(--amber)", fontWeight: 700, letterSpacing: "0.04em" }}>{p.code}</span>
                <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>PA {pa}</span>
              </div>
            );
          })}
        </div>
      )}
      {/* 凡例 */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 12, fontSize: 10, fontFamily: "var(--ff-mono)" }}>
        {OUTCOME_CATS.map(cat => (
          <div key={cat.key} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 10, height: 10, background: cat.color }}/>
            <span style={{ color: "var(--ink-2)", fontWeight: 700 }}>{cat.label}</span>
            <span style={{ color: "var(--ink-4)" }}>{cat.sub}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* QUALITY SCATTER — 打球品質 vs 成果。X=HardHit% Y=xwOBA size=USE% color=Strategy */
const QualityScatterPlot = ({ arsenal }) => {
  const recColor = { neg: "var(--neg)", amber: "var(--amber)", pos: "var(--pos)" };
  // 軸範囲（固定）
  const xMin = 0,    xMax = 60;          // HardHit%
  const yMin = 0.150, yMax = 0.500;       // xwOBA
  // SVG ビューポート（縦を伸ばしてプロットエリアを拡大）
  const W = 360, H = 360, padL = 46, padB = 40, padT = 18, padR = 18;
  const items = (arsenal || []).filter(p =>
    p.quality && p.quality.hardHit != null && p.batXwoba != null
  );
  const toX = (hh) => padL + ((hh - xMin) / (xMax - xMin)) * (W - padL - padR);
  const toY = (xw) => padT + (1 - (xw - yMin) / (yMax - yMin)) * (H - padT - padB);
  // バブル半径: USE% の平方根に比例（半径 px ベース、最小 8 / 最大 32）
  const rOf = (use) => {
    if (use == null) return 10;
    return Math.max(8, Math.min(32, Math.sqrt(use) * 4.2));
  };
  return (
    <div style={{ border: "1px solid var(--rule-dim)", padding: 14, background: "var(--bg-1)" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 10 }}>
        <span className="h-label" style={{ fontSize: 11, color: "var(--ink-2)" }}>QUALITY · 打球品質 vs 成果</span>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>size = USE%</span>
      </div>
      {items.length === 0 ? (
        <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", padding: "30px 0", textAlign: "center" }}>NO DATA</div>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", aspectRatio: `${W}/${H}`, display: "block" }}>
          {/* グリッド */}
          {[0.200, 0.300, 0.400].map(yv => (
            <g key={`gy-${yv}`}>
              <line x1={padL} y1={toY(yv)} x2={W - padR} y2={toY(yv)} stroke="var(--rule-dim)" strokeWidth="0.6" strokeDasharray="2 2"/>
              <text x={padL - 6} y={toY(yv) + 4} fontSize="11" fontFamily="var(--ff-mono)" fill="var(--ink-3)" textAnchor="end">.{String(Math.round(yv*1000)).padStart(3,"0")}</text>
            </g>
          ))}
          {[20, 40].map(xv => (
            <g key={`gx-${xv}`}>
              <line x1={toX(xv)} y1={padT} x2={toX(xv)} y2={H - padB} stroke="var(--rule-dim)" strokeWidth="0.6" strokeDasharray="2 2"/>
              <text x={toX(xv)} y={H - padB + 14} fontSize="11" fontFamily="var(--ff-mono)" fill="var(--ink-3)" textAnchor="middle">{xv}</text>
            </g>
          ))}
          {/* 軸 */}
          <line x1={padL} y1={padT} x2={padL} y2={H - padB} stroke="var(--rule)" strokeWidth="0.8"/>
          <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke="var(--rule)" strokeWidth="0.8"/>
          {/* 軸ラベル */}
          <text x={(padL + W - padR) / 2} y={H - 6} fontSize="11" fontFamily="var(--ff-mono)" fill="var(--ink-2)" textAnchor="middle" letterSpacing="0.08em">HardHit %</text>
          <text x={12} y={(padT + H - padB) / 2} fontSize="11" fontFamily="var(--ff-mono)" fill="var(--ink-2)" textAnchor="middle" letterSpacing="0.08em" transform={`rotate(-90 12 ${(padT + H - padB) / 2})`}>xwOBA</text>
          {/* バブル */}
          {items.map(p => {
            const cx = toX(Math.min(xMax, Math.max(xMin, p.quality.hardHit)));
            const cy = toY(Math.min(yMax, Math.max(yMin, p.batXwoba)));
            const r  = rOf(p.use);
            const fill = recColor[p.recColor] || "var(--amber)";
            const xwobaStr = `.${String(Math.round(p.batXwoba * 1000)).padStart(3, "0")}`;
            return (
              <g key={p.code}>
                <title>{`${p.code} · HardHit ${p.quality.hardHit}% · xwOBA ${xwobaStr} · USE ${p.use}% · BBE ${p.quality.bbe}`}</title>
                <circle cx={cx} cy={cy} r={r} fill={fill} opacity="0.55" stroke={fill} strokeWidth="1.2"/>
                <text x={cx} y={cy + 4} fontSize="12" fontFamily="var(--ff-mono)" fontWeight="700" fill="var(--ink-0)" textAnchor="middle">{p.code}</text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
};

/* ============================================================
   SPRAY CHART — field with hit distribution
============================================================ */
const SprayPanel = ({ spray, loading = false, error = null }) => {
  const isEmpty = !Array.isArray(spray) || spray.length < 3;
  if (loading || error || isEmpty) {
    return (
      <div style={{ border: "1px solid var(--rule)" }}>
        <PanelHeader title="SPRAY · 打球方向" sub="プル / セ / 流し"/>
        <PanelStatePlaceholder loading={loading} error={error} empty={isEmpty}/>
      </div>
    );
  }
  return (
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
      <SprayVerdict spray={spray}/>
    </div>
  </div>
  );
};

/**
 * spray の PULL 値から動的に判定文を生成。
 *  - PULL >= 45%: プル偏重 → シフト強く推奨
 *  - PULL 35-45%: プル傾向あり → シフト推奨
 *  - その他: バランス型
 */
const SprayVerdict = ({ spray }) => {
  const pull = spray.find(s => s.zone === "PULL") || { pct: 0, slg: 0 };
  const slgStr = "." + String(Math.round((pull.slg || 0) * 1000)).padStart(3, "0").replace(/^0/, "");
  let label, advice;
  if (pull.pct >= 45) {
    label = "プル偏重";
    advice = "シフト強く推奨";
  } else if (pull.pct >= 35) {
    label = "プル傾向あり";
    advice = "シフト推奨";
  } else if (pull.pct >= 25) {
    label = "バランス型";
    advice = "通常守備";
  } else {
    label = "オポ寄り";
    advice = "逆方向警戒";
  }
  return (
    <div style={{ marginTop: 10, fontSize: 10.5, color: "var(--ink-2)", lineHeight: 1.5 }}>
      <span className="t-mono" style={{ color: "var(--amber)", fontSize: 10 }}>→ </span>
      {label} <strong style={{ color: "var(--ink-0)" }}>{pull.pct}% / SLG{slgStr}</strong>。{advice}。
    </div>
  );
};

/* ============================================================
   TACTICS — actionable recommendations
============================================================ */
const TacticsPanel = ({
  tactics, side, sideLabel, accent,
  loading = false, error = null, verified = null,
  generated = false, anyLoading = false, onGenerate = null,
}) => {
  const tierColor = (t) => ({
    SIT_ON: "var(--pos)", TAKE: "var(--neg)", PROTECT: "var(--amber)", COUNT: "var(--info)",
    OFFENSIVE: "var(--amber)", WEAPON: "var(--pos)", AVOID: "var(--neg)",
    DEFENSE: "var(--info)", SETUP: "var(--amber)",
    ALERT: "var(--neg)",
  })[t.replace(" ", "_")] || "var(--ink-2)";

  const itemsLabel = loading ? "LOADING…" :
                     error ? "ERROR" :
                     generated ? `${tactics.length} ITEMS` :
                     "READY";

  const buttonLabel = anyLoading ? "GENERATING…" :
                      generated ? "REGENERATE" :
                      "GENERATE";

  return (
    <div style={{ border: `1px solid ${accent}` }}>
      <div className="rule-b" style={{ padding: "9px 14px", background: `oklch(from ${accent} l c h / 0.08)`, display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ width: 8, height: 8, background: accent }}/>
        <span className="h-label" style={{ color: accent }}>{side} TACTICS</span>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>{sideLabel}</span>
        {/* AI バッジ + 検証ステータス */}
        <span className="t-mono" style={{
          fontSize: 8.5, padding: "1px 5px", border: "1px solid var(--info)",
          color: "var(--info)", letterSpacing: "0.12em", fontWeight: 700,
        }}>AI</span>
        {verified === true && (
          <span className="t-mono" title="数値が画面上のデータと一致" style={{
            fontSize: 8.5, padding: "1px 5px", border: "1px solid var(--pos)",
            color: "var(--pos)", letterSpacing: "0.08em",
          }}>VERIFIED</span>
        )}
        {verified === false && tactics.length > 0 && !loading && !error && (
          <span className="t-mono" title="一部の数値が画面データに見当たらない可能性あり" style={{
            fontSize: 8.5, padding: "1px 5px", border: "1px solid var(--amber)",
            color: "var(--amber)", letterSpacing: "0.08em",
          }}>UNVERIFIED</span>
        )}
        <div style={{ flex: 1 }}/>
        <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{itemsLabel}</span>
      </div>
      <div>
        {/* 未生成: GENERATE ボタンを目立つ位置に表示（ヘッダ直下、両パネル共通の動線） */}
        {!generated && !loading && !error && (
          <div className="no-print" style={{
            padding: "28px 14px", display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 10,
            background: `oklch(from ${accent} l c h / 0.03)`,
          }}>
            <div className="t-mono" style={{
              fontSize: 10, color: "var(--ink-3)", letterSpacing: "0.08em", textAlign: "center",
            }}>AI戦術は手動生成です（コスト管理）</div>
            <button
              onClick={onGenerate}
              disabled={anyLoading || !onGenerate}
              style={{
                padding: "8px 18px", border: `1px solid ${accent}`,
                background: `oklch(from ${accent} l c h / 0.12)`,
                color: accent, fontWeight: 700,
                fontFamily: "var(--ff-mono)", fontSize: 11, letterSpacing: "0.14em",
                cursor: anyLoading ? "wait" : "pointer",
                opacity: anyLoading ? 0.6 : 1,
              }}
            >▶ {buttonLabel}</button>
            <div className="t-mono" style={{
              fontSize: 9, color: "var(--ink-4)", letterSpacing: "0.06em", textAlign: "center",
            }}>BATTER / PITCHER 同時に生成されます</div>
          </div>
        )}
        {loading && (
          <div className="t-mono" style={{
            padding: "40px 14px", textAlign: "center",
            fontSize: 10.5, color: "var(--ink-3)", letterSpacing: "0.08em",
          }}>AI 戦術を生成中…</div>
        )}
        {!loading && error && tactics.length === 0 && (
          <div className="t-mono" style={{
            padding: "40px 14px", textAlign: "center",
            fontSize: 10.5, color: "var(--neg)", letterSpacing: "0.06em",
          }}>ERROR: {error}</div>
        )}
        {!loading && generated && tactics.map((t, i) => (
          <div key={`${t.tier}-${t.title}-${i}`} style={{
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
        {/* 生成済み + 戦術カード描画後: 下部に REGENERATE ボタン */}
        {generated && !loading && tactics.length > 0 && (
          <div className="no-print" style={{
            padding: "10px 14px", borderTop: "1px solid var(--rule-dim)",
            display: "flex", justifyContent: "flex-end",
            background: "var(--bg-1)",
          }}>
            <button
              onClick={onGenerate}
              disabled={anyLoading || !onGenerate}
              style={{
                padding: "5px 12px", border: `1px solid ${accent}`,
                background: "transparent", color: accent,
                fontFamily: "var(--ff-mono)", fontSize: 9.5, letterSpacing: "0.12em", fontWeight: 700,
                cursor: anyLoading ? "wait" : "pointer",
                opacity: anyLoading ? 0.5 : 1,
              }}
            >↻ {buttonLabel}</button>
          </div>
        )}
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
const CountMatrixPanel = ({ counts, view, loading = false, error = null }) => {
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
      <PanelHeader
        title={view === "pitcher" ? "COUNT · 配球コール" : "COUNT-STATE CALL MATRIX"}
        sub="投手のカウント別最頻球種"
      />
      <div style={{ padding: 14, position: "relative" }}>
        {loading && (
          <div className="t-mono" style={{
            position: "absolute", inset: 0, display: "flex",
            alignItems: "center", justifyContent: "center",
            background: "var(--bg-0)", opacity: 0.7, zIndex: 1,
            fontSize: 10, color: "var(--ink-3)", letterSpacing: "0.08em",
          }}>LOADING…</div>
        )}
        {error && !loading && (
          <div className="t-mono" style={{
            fontSize: 10, color: "var(--neg)", marginBottom: 8, letterSpacing: "0.06em",
          }}>ERROR: {error}</div>
        )}
        <div style={{ display: "grid", gridTemplateColumns: "30px repeat(3, 1fr)", gap: 4 }}>
          <div></div>
          {[0,1,2].map(s => <div key={s} className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", textAlign: "center", letterSpacing: "0.08em" }}>{s} STR</div>)}
          {[0,1,2,3].map(b => (
            <Fragment key={b}>
              <div className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-3)", display: "flex", alignItems: "center", letterSpacing: "0.08em" }}>{b}B</div>
              {[0,1,2].map(s => {
                const cell = grid.find(g => g.b === b && g.s === s);
                if (!cell || !cell.call) return <div key={s} style={{ aspectRatio: "1.6/1", background: "var(--bg-2)", opacity: 0.4 }}/>;
                const usePct = cell.pitchPct != null ? ` · USE ${cell.pitchPct}%` : "";
                const tooltip = `${b}-${s} · ${cell.call}${usePct}`
                  + (cell.pitches ? ` · N=${cell.pitches}` : "");
                return (
                  <div key={s} title={tooltip} style={{
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
        <div style={{
          marginTop: 8, fontSize: 9.5, color: "var(--ink-4)",
          fontFamily: "var(--ff-mono)", letterSpacing: "0.04em", lineHeight: 1.5,
        }}>
          CONF. = 最頻球種の使用率（USE%）　HIGH ≥ 50% / MED ≥ 35% / LOW &lt; 35%
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   COMPS — similar pitcher matchups
============================================================ */
/* COMPARABLE MATCHUPS — 未実装（後回し）。
   類似投手との対戦実績を出すには pitcher similarity モデルとサンプル確保が必要なため、
   現時点では TBD バッジを表示するのみ。 */
const CompsPanel = () => (
  <div style={{ border: "1px dashed var(--amber)", position: "relative", overflow: "hidden" }}>
    <PanelHeader title="COMPARABLE MATCHUPS" sub="類似投手との対戦実績"/>
    <div style={{
      padding: "32px 14px",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10,
      background: "oklch(from var(--amber) l c h / 0.05)",
      minHeight: 220,
    }}>
      <span className="t-mono" style={{
        fontSize: 22, fontWeight: 800, letterSpacing: "0.18em",
        color: "var(--amber)",
        padding: "8px 18px", border: "2px solid var(--amber)",
        background: "var(--bg-0)",
      }}>TBD</span>
      <div style={{
        fontSize: 11, color: "var(--ink-2)", textAlign: "center", lineHeight: 1.6, maxWidth: 280,
      }}>
        類似投手検索ロジック（pitcher similarity）の実装後に有効化予定です。
      </div>
      <div className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)", letterSpacing: "0.08em" }}>
        STATUS · DEPRIORITIZED
      </div>
    </div>
  </div>
);

/* ============================================================
   RECENT PA — last 10 plate appearances
============================================================ */
const RecentPAPanel = ({ recent, loading = false, error = null }) => {
  const outcomeColor = (pa) => {
    if (pa === "HR") return "var(--amber)";
    if (["1B","2B","3B"].includes(pa)) return "var(--pos)";
    if (pa === "BB" || pa === "HBP") return "var(--info)";
    if (pa === "K") return "var(--neg)";
    return "var(--ink-2)";
  };
  const isEmpty = !Array.isArray(recent) || recent.length === 0;
  if (loading || error || isEmpty) {
    return (
      <div style={{ border: "1px solid var(--rule)" }}>
        <PanelHeader title="LAST 10 PA · 直近対戦"/>
        <PanelStatePlaceholder
          loading={loading} error={error} empty={isEmpty}
          minHeight={180}
          label={isEmpty ? "対戦履歴なし" : ""}
        />
      </div>
    );
  }
  // 件数が10未満の場合も grid を実件数に合わせて自動調整
  const cellCount = recent.length;
  return (
    <div style={{ border: "1px solid var(--rule)" }}>
      <PanelHeader title={`LAST ${cellCount} PA · 直近対戦`} sub="通算"/>
      <div style={{ padding: "8px 14px 14px" }}>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(cellCount, 10)}, 1fr)`, gap: 6 }}>
          {recent.map((r, i) => (
            <div key={i} title={`${r.d}${r.note ? " · " + r.note : ""}`} style={{
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
const StrategyEmptyState = ({
  onGenerate, batter, pitcher,
  season, setSeason,
  onSelectPlayer, getBackendURL, getAuthHeaders,
}) => (
  <div style={{ flex: 1, display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "60px 40px 40px", background: "var(--bg-0)" }}>
    <div style={{ width: 620, border: "1px solid var(--rule)", background: "var(--bg-1)" }}>
      <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--rule)" }}>
        <div className="t-mono" style={{ fontSize: 10, color: "var(--amber)", letterSpacing: "0.16em", marginBottom: 6 }}>STRATEGY · 対戦戦略</div>
        <div className="h-display" style={{ fontSize: 22, color: "var(--ink-0)" }}>MATCHUP REPORT</div>
        <div style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 4 }}>
          打者・投手・シーズンを選択して GENERATE を押してください。
        </div>
      </div>
      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 18 }}>
        <PlayerSearchPicker
          label="BATTER · 打者" data={batter} accent="var(--pos)"
          role="batter"
          onSelect={(item) => onSelectPlayer && onSelectPlayer("batter", item)}
          getBackendURL={getBackendURL} getAuthHeaders={getAuthHeaders}
        />
        <PlayerSearchPicker
          label="PITCHER · 投手" data={pitcher} accent="var(--info)"
          role="pitcher"
          onSelect={(item) => onSelectPlayer && onSelectPlayer("pitcher", item)}
          getBackendURL={getBackendURL} getAuthHeaders={getAuthHeaders}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span className="h-label" style={{ fontSize: 8.5, color: "var(--ink-3)" }}>SEASON · 年度</span>
          <select
            value={season}
            onChange={(e) => setSeason && setSeason(Number(e.target.value))}
            style={{
              padding: "8px 12px", border: "1px solid var(--rule)", background: "var(--bg-1)",
              color: "var(--ink-0)", fontFamily: "var(--ff-mono)", fontSize: 13,
              letterSpacing: "0.06em", cursor: "pointer",
            }}
          >
            {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <button
          onClick={onGenerate}
          style={{
            marginTop: 4, padding: "12px",
            background: "var(--amber)", color: "var(--bg-0)",
            fontFamily: "var(--ff-mono)", fontSize: 12, fontWeight: 700, letterSpacing: "0.14em",
            cursor: "pointer", border: "none",
          }}
        >
          ▶ GENERATE REPORT
        </button>
      </div>
    </div>
  </div>
);

export default StrategyScreen;
