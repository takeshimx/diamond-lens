import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getBackendUrl } from './advancedStatsConstants';

const METRIC_DEFS = [
  { id: 'ops',      label: 'OPS',       colFn: (p) => `ops_${p}days`,                 fmt: (v) => v?.toFixed(3) ?? '—' },
  { id: 'ba',       label: 'BA',        colFn: (p) => `ba_${p}days`,                  fmt: (v) => v?.toFixed(3) ?? '—' },
  { id: 'barrels',  label: 'Barrel%',   colFn: (p) => `barrels_percentage_${p}days`,  fmt: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
  { id: 'hard_hit', label: 'Hard Hit%', colFn: (p) => `hard_hit_percentage_${p}days`, fmt: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
];

const hotFlagsFn = (p) => [
  { key: `is_red_hot_ba_${p}days`,       label: 'BA' },
  { key: `is_red_hot_ops_${p}days`,      label: 'OPS' },
  { key: `is_red_hot_barrels_${p}days`,  label: 'Barrel' },
  { key: `is_red_hot_hard_hit_${p}days`, label: 'HH' },
];
const slumpFlagsFn = (p) => [
  { key: `is_slump_ba_${p}days`,       label: 'BA' },
  { key: `is_slump_ops_${p}days`,      label: 'OPS' },
  { key: `is_slump_barrels_${p}days`,  label: 'Barrel' },
  { key: `is_slump_hard_hit_${p}days`, label: 'HH' },
];

const HOT_BADGE  = { background: "oklch(0.80 0.165 80 / 0.20)", color: "oklch(0.80 0.165 80)", border: "1px solid oklch(0.80 0.165 80 / 0.40)" };
const SLUMP_BADGE = { background: "oklch(0.75 0.12 240 / 0.20)", color: "oklch(0.75 0.12 240)", border: "1px solid oklch(0.75 0.12 240 / 0.40)" };

const TH = ({ children, align = "left" }) => (
  <th style={{
    padding: "6px 10px", textAlign: align, fontSize: 10,
    color: "var(--ink-3)", fontFamily: "var(--ff-mono)",
    fontWeight: 600, letterSpacing: "0.08em",
    borderBottom: "1px solid var(--rule)",
    background: "var(--bg-2)",
    textTransform: "uppercase",
  }}>{children}</th>
);

const RankRow = ({ rank, player, metricDef, period, flagDefs, isHot }) => {
  const col = metricDef.colFn(period);
  const value = metricDef.fmt(player[col]);
  const activeBadges = flagDefs.filter((f) => player[f.key]);
  const accentColor = isHot ? 'oklch(0.80 0.165 80)' : 'oklch(0.75 0.12 240)';
  const badgeStyle = isHot ? HOT_BADGE : SLUMP_BADGE;

  return (
    <tr style={{ borderBottom: "1px solid var(--rule-dim)" }}>
      <td className="t-mono" style={{ padding: "7px 10px", color: "var(--ink-4)", fontSize: 11, width: 32 }}>
        {rank}
      </td>
      <td style={{ padding: "7px 10px" }}>
        <div style={{ color: "var(--ink-0)", fontSize: 12, fontWeight: 600 }}>{player.batter_name}</div>
        <div className="t-mono" style={{ color: "var(--ink-4)", fontSize: 10 }}>{player.team ?? '—'}</div>
      </td>
      <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: accentColor, fontWeight: 700, fontSize: 13 }}>
        {value}
      </td>
      <td style={{ padding: "7px 10px" }}>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {activeBadges.map((f) => (
            <span key={f.key} style={{
              ...badgeStyle,
              fontSize: 10, padding: "1px 5px",
              fontFamily: "var(--ff-mono)", fontWeight: 600,
            }}>
              {f.label}
            </span>
          ))}
        </div>
      </td>
    </tr>
  );
};

const RankTable = ({ title, emoji, players, metricDef, period, flagDefs, isHot, isLoading }) => (
  <div style={{ flex: 1, minWidth: 0 }}>
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
      <span>{emoji}</span>
      <span className="h-display" style={{ fontSize: 14 }}>{title}</span>
      {!isLoading && (
        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>({players.length}人)</span>
      )}
    </div>
    <div style={{ border: "1px solid var(--rule)", background: "var(--bg-1)" }}>
      {isLoading ? (
        <div style={{ padding: "24px 0", textAlign: "center", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
          <span className="think-dot"/>
          <span className="think-dot" style={{ animationDelay: ".2s" }}/>
          <span className="think-dot" style={{ animationDelay: ".4s" }}/>
        </div>
      ) : players.length === 0 ? (
        <div style={{ padding: "24px 0", textAlign: "center", color: "var(--ink-4)", fontSize: 12 }}>該当選手なし</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <TH>#</TH>
              <TH>選手</TH>
              <TH align="right">{metricDef.label}</TH>
              <TH align="right">指標</TH>
            </tr>
          </thead>
          <tbody>
            {players.map((p, i) => (
              <RankRow
                key={p.batter_id ?? i}
                rank={i + 1}
                player={p}
                metricDef={metricDef}
                period={period}
                flagDefs={flagDefs}
                isHot={isHot}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  </div>
);

const HotSlumpDashboard = () => {
  const { getIdToken } = useAuth();
  const BACKEND_URL = getBackendUrl();

  const [period, setPeriod] = useState(7);
  const [metric, setMetric] = useState('ops');
  const [selectedDate, setSelectedDate] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const getAuthHeaders = async () => {
    const idToken = await getIdToken();
    return {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(idToken ? { Authorization: `Bearer ${idToken}` } : {}),
    };
  };

  useEffect(() => {
    const fetchDates = async () => {
      setSelectedDate(null);
      setData(null);
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(
          `${BACKEND_URL}/api/v1/hot-slump/available-dates?period=${period}`,
          { headers }
        );
        if (!res.ok) return;
        const json = await res.json();
        const dates = json.dates ?? [];
        setAvailableDates(dates);
        if (dates.length > 0) setSelectedDate(dates[0]);
      } catch (e) {
        console.error('Failed to fetch available dates:', e);
      }
    };
    fetchDates();
  }, [period]);

  useEffect(() => {
    if (!selectedDate) return;
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const headers = await getAuthHeaders();
        const params = new URLSearchParams({ metric, period, game_date: selectedDate, top_n: 10 });
        const res = await fetch(`${BACKEND_URL}/api/v1/hot-slump/batters?${params}`, { headers });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        setError(e.message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [metric, period, selectedDate]);

  const metricDef = METRIC_DEFS.find((m) => m.id === metric);
  const hotFlags = hotFlagsFn(period);
  const slumpFlags = slumpFlagsFn(period);

  const tabBtn = (active) => ({
    padding: "5px 14px", fontSize: 11,
    fontFamily: "var(--ff-mono)", letterSpacing: "0.06em",
    background: active ? "var(--amber)" : "transparent",
    color: active ? "var(--bg-0)" : "var(--ink-3)",
    border: `1px solid ${active ? "var(--amber)" : "var(--rule)"}`,
    fontWeight: active ? 600 : 400,
    transition: "all .12s",
  });

  const metricBtn = (active) => ({
    padding: "5px 12px", fontSize: 11,
    fontFamily: "var(--ff-mono)", letterSpacing: "0.05em",
    background: active ? "var(--amber)" : "var(--bg-2)",
    color: active ? "var(--bg-0)" : "var(--ink-2)",
    border: `1px solid ${active ? "var(--amber)" : "var(--rule)"}`,
    fontWeight: active ? 600 : 400,
    transition: "all .12s",
  });

  return (
    <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        {/* Period toggle */}
        <div style={{ display: "flex", gap: 4 }}>
          {[7, 15].map((p) => (
            <button key={p} onClick={() => setPeriod(p)} style={tabBtn(period === p)}>
              {p}日
            </button>
          ))}
        </div>

        {/* Metric tabs */}
        <div style={{ display: "flex", gap: 4 }}>
          {METRIC_DEFS.map(({ id, label }) => (
            <button key={id} onClick={() => setMetric(id)} style={metricBtn(metric === id)}>
              {label}
            </button>
          ))}
        </div>

        {/* Date select */}
        <select
          value={selectedDate ?? ''}
          onChange={(e) => setSelectedDate(e.target.value)}
          style={{
            marginLeft: "auto",
            background: "var(--bg-1)", color: "var(--ink-1)",
            fontSize: 11, padding: "5px 10px",
            border: "1px solid var(--rule)", fontFamily: "var(--ff-mono)",
          }}
        >
          {availableDates.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* Description */}
      <p className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
        直近{period}日スタッツがシーズン平均比 +20% 以上 → 🔥 Red Hot　／　−20% 以下 → 📉 Slump
      </p>

      {error && (
        <div style={{
          color: "var(--neg)", fontSize: 12,
          border: "1px solid var(--neg-dim)",
          background: "oklch(0.26 0.10 28 / 0.12)",
          padding: "8px 12px",
        }}>
          {error}
        </div>
      )}

      {/* Hot / Slump tables side by side */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <RankTable
          title="Red Hot Top 10"
          emoji="🔥"
          players={data?.hot ?? []}
          metricDef={metricDef}
          period={period}
          flagDefs={hotFlags}
          isHot={true}
          isLoading={isLoading}
        />
        <RankTable
          title="Slump Top 10"
          emoji="📉"
          players={data?.slump ?? []}
          metricDef={metricDef}
          period={period}
          flagDefs={slumpFlags}
          isHot={false}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};

export default HotSlumpDashboard;
