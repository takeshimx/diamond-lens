import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../hooks/useAuth';

const POLL_INTERVAL_MS = 60000;

const getBackendUrl = () => {
  if (window.location.hostname.includes('run.app')) {
    return 'https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app';
  }
  if (window.location.href.includes('app.github.dev')) {
    return window.location.href.replace('-5173.app.github.dev', '-8000.app.github.dev').split('?')[0];
  }
  return 'http://localhost:8000';
};

const BACKEND_URL = getBackendUrl();

const gameToChip = (game, isLive) => ({
  type: "score",
  away:   game.away_team,
  home:   game.home_team,
  aScore: game.away_score ?? 0,
  hScore: game.home_score ?? 0,
  status: isLive
    ? `${game.inning_half === 'Top' ? 'TOP' : 'BOT'} ${game.inning}`
    : (game.innings ? `F/${game.innings}` : 'F'),
});

const TickerChip = ({ item }) => {
  if (item.type === "score") {
    const homeWin = item.hScore > item.aScore;
    const awayWin = item.aScore > item.hScore;
    return (
      <span className="t-mono" style={{
        display: "inline-flex", alignItems: "center", gap: 8, padding: "0 14px",
        borderRight: "1px solid var(--rule-dim)", fontSize: 11, letterSpacing: "0.04em",
      }}>
        <span style={{ color: awayWin ? "var(--amber)" : "var(--ink-2)", fontWeight: 600 }}>{item.away}</span>
        <span style={{ color: awayWin ? "var(--amber)" : "var(--ink-1)" }}>{item.aScore}</span>
        <span style={{ color: "var(--ink-4)" }}>–</span>
        <span style={{ color: homeWin ? "var(--amber)" : "var(--ink-1)" }}>{item.hScore}</span>
        <span style={{ color: homeWin ? "var(--amber)" : "var(--ink-2)", fontWeight: 600 }}>{item.home}</span>
        <span style={{
          fontSize: 9, marginLeft: 4, letterSpacing: "0.1em",
          color: item.status.startsWith("F") ? "var(--ink-4)" : "var(--pos)",
        }}>{item.status}</span>
      </span>
    );
  }
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 8, padding: "0 14px",
      borderRight: "1px solid var(--rule-dim)", fontSize: 11,
    }}>
      <span className="h-label" style={{ fontSize: 9, color: "var(--ink-3)" }}>{item.label}</span>
      <span className="t-mono" style={{ color: "var(--ink-0)", fontWeight: 600 }}>{item.value}</span>
      <span className="t-mono" style={{
        fontSize: 10,
        color: item.delta.startsWith("+") ? "var(--pos)"
             : item.delta.startsWith("-") ? "var(--neg)"
             : "var(--amber)",
      }}>{item.delta}</span>
    </span>
  );
};

const Ticker = () => {
  const { getIdToken } = useAuth();
  const getIdTokenRef = useRef(getIdToken);
  const [chips, setChips] = useState([]);

  useEffect(() => {
    const fetchScores = async () => {
      try {
        const idToken = await getIdTokenRef.current();
        const headers = {
          Accept: 'application/json',
          ...(idToken ? { Authorization: `Bearer ${idToken}` } : {}),
        };
        const res = await fetch(`${BACKEND_URL}/api/v1/live/games/today`, { headers });
        if (!res.ok) return;
        const data = await res.json();
        const liveChips  = (data.live  ?? []).map(g => gameToChip(g, true));
        const finalChips = (data.final ?? []).map(g => gameToChip(g, false));
        const all = [...liveChips, ...finalChips];
        if (all.length > 0) setChips(all);
      } catch {
        // ネットワークエラー時は現在の表示を維持
      }
    };

    fetchScores();
    const timer = setInterval(fetchScores, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  const items = chips.length > 0 ? [...chips, ...chips] : [];

  return (
    <div className="rule-b" style={{
      height: 28, background: "var(--bg-0)", overflow: "hidden", position: "relative", flexShrink: 0,
    }}>
      {/* LIVE label overlay */}
      <div style={{
        position: "absolute", left: 0, top: 0, height: "100%",
        display: "flex", alignItems: "center", gap: 0, padding: "0 12px",
        zIndex: 2, background: "linear-gradient(90deg, var(--bg-0) 60%, transparent)",
      }}>
        <span className="live-dot" style={{ marginRight: 6 }}/>
        <span className="h-label" style={{ fontSize: 9, color: "var(--pos)" }}>LIVE</span>
      </div>

      {/* Scrolling content */}
      <div className="ticker-track" style={{
        display: "inline-flex", whiteSpace: "nowrap", height: "100%",
        alignItems: "center", paddingLeft: 90,
      }}>
        {items.map((item, i) => <TickerChip key={i} item={item}/>)}
      </div>
    </div>
  );
};

export default Ticker;
