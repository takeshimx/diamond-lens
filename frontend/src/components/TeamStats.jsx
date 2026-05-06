import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useAuth } from '../hooks/useAuth';
import Icon from './layout/Icon.jsx';

const getBackendUrl = () => {
  if (window.location.hostname.includes('run.app')) {
    return 'https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app';
  }
  const currentUrl = window.location.href;
  if (currentUrl.includes('app.github.dev')) {
    return currentUrl.replace('-5173.app.github.dev', '-8000.app.github.dev').split('?')[0];
  }
  return 'http://localhost:8000';
};

const BACKEND_URL = getBackendUrl();

const STICKY_RANK_W = 44;

const HITTING_COLS = [
  { key: 'g',         label: 'G',         fmt: 'int' },
  { key: 'avg',       label: 'AVG',       fmt: 'avg' },
  { key: 'obp',       label: 'OBP',       fmt: 'avg' },
  { key: 'slg',       label: 'SLG',       fmt: 'avg' },
  { key: 'ops',       label: 'OPS',       fmt: 'avg' },
  { key: 'r',         label: 'R',         fmt: 'int' },
  { key: 'h',         label: 'H',         fmt: 'int' },
  { key: 'hr',        label: 'HR',        fmt: 'int' },
  { key: 'rbi',       label: 'RBI',       fmt: 'int' },
  { key: 'bb',        label: 'BB',        fmt: 'int' },
  { key: 'so',        label: 'SO',        fmt: 'int' },
  { key: 'sb',        label: 'SB',        fmt: 'int' },
  { key: 'babip',     label: 'BABIP',     fmt: 'avg' },
  { key: 'risp_avg',    label: 'RISP打率',  fmt: 'avg' },
  { key: 'risp_ops',    label: 'RISP OPS',  fmt: 'avg' },
  { key: 'risp_rbi',    label: 'RISP RBI',  fmt: 'int' },
  { key: 'bl_avg',      label: '満塁打率',  fmt: 'avg' },
  { key: 'bl_ops',      label: '満塁OPS',   fmt: 'avg' },
  { key: 'bl_rbi',      label: '満塁RBI',   fmt: 'int' },
  { key: 'grand_slam',  label: 'GS',        fmt: 'int' },
];

const PITCHING_COLS = [
  { key: 'w',     label: 'W',     fmt: 'int' },
  { key: 'l',     label: 'L',     fmt: 'int' },
  { key: 'era',   label: 'ERA',   fmt: 'two' },
  { key: 'whip',  label: 'WHIP',  fmt: 'two' },
  { key: 'ip',    label: 'IP',    fmt: 'str' },
  { key: 'so',    label: 'SO',    fmt: 'int' },
  { key: 'bb',    label: 'BB',    fmt: 'int' },
  { key: 'hr',    label: '被HR',  fmt: 'int' },
  { key: 'sv',    label: 'SV',    fmt: 'int' },
  { key: 'k_9',   label: 'K/9',   fmt: 'two' },
  { key: 'bb_9',  label: 'BB/9',  fmt: 'two' },
  { key: 'k_bb',  label: 'K/BB',  fmt: 'two' },
  { key: 'sho',   label: 'SHO',   fmt: 'int' },
  { key: 'cg',    label: 'CG',    fmt: 'int' },
];

const formatVal = (val, fmt) => {
  if (val === null || val === undefined || val === '-' || val === '') return '-';
  const n = Number(val);
  if (fmt === 'avg') {
    if (Number.isNaN(n)) return '-';
    const s = n.toFixed(3);
    return n < 1 && n >= 0 ? s.replace(/^0\./, '.') : s;
  }
  if (fmt === 'two') {
    if (Number.isNaN(n)) return val;
    return n.toFixed(2);
  }
  if (fmt === 'int') {
    if (Number.isNaN(n)) return val;
    return Math.round(n);
  }
  return val;
};

const compareNumeric = (a, b, dir) => {
  const av = a === null || a === undefined || a === '-' || a === '' ? null : Number(a);
  const bv = b === null || b === undefined || b === '-' || b === '' ? null : Number(b);
  const aN = av === null || Number.isNaN(av);
  const bN = bv === null || Number.isNaN(bv);
  if (aN && bN) return 0;
  if (aN) return 1;
  if (bN) return -1;
  return dir === 'desc' ? bv - av : av - bv;
};

const getRankBadge = (rank) => {
  if (rank === 1) return <span className="t-mono" style={{ color: "var(--amber)", fontWeight: 700, fontSize: 13 }}>①</span>;
  if (rank === 2) return <span className="t-mono" style={{ color: "var(--ink-2)", fontWeight: 700, fontSize: 12 }}>②</span>;
  if (rank === 3) return <span className="t-mono" style={{ color: "var(--amber-dim)", fontWeight: 700, fontSize: 12 }}>③</span>;
  return <span className="t-mono" style={{ color: "var(--ink-4)", fontSize: 11 }}>{rank}</span>;
};

export default function TeamStats() {
  const { getIdToken } = useAuth();
  const getIdTokenRef = useRef(getIdToken);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState('hitting');
  const [sortKey, setSortKey] = useState('ops');
  const [sortDir, setSortDir] = useState('desc');
  const [updatedAt, setUpdatedAt] = useState(null);

  const fetchTeamStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const idToken = await getIdTokenRef.current();
      const headers = {
        'Accept': 'application/json',
        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
      };
      const res = await fetch(`${BACKEND_URL}/api/v1/live/team-stats`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setUpdatedAt(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTeamStats(); }, [fetchTeamStats]);

  useEffect(() => {
    if (mode === 'hitting') {
      setSortKey('ops');
      setSortDir('desc');
    } else {
      setSortKey('era');
      setSortDir('asc');
    }
  }, [mode]);

  const cols = mode === 'hitting' ? HITTING_COLS : PITCHING_COLS;

  const sorted = useMemo(() => {
    if (!data?.teams) return [];
    return [...data.teams].sort((a, b) =>
      compareNumeric(a[mode]?.[sortKey], b[mode]?.[sortKey], sortDir)
    );
  }, [data, mode, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(key);
      setSortDir(mode === 'pitching' && (key === 'era' || key === 'whip' || key === 'bb_9') ? 'asc' : 'desc');
    }
  };

  const SortIcon = ({ column }) => {
    if (sortKey !== column) return <Icon name="chevD" size={10} style={{ opacity: 0.3 }}/>;
    return sortDir === 'desc'
      ? <Icon name="chevD" size={10} style={{ color: "var(--amber)" }}/>
      : <Icon name="chevD" size={10} style={{ color: "var(--amber)", transform: "rotate(180deg)" }}/>;
  };

  const tabBtn = (active) => ({
    padding: "5px 16px",
    fontSize: 11,
    fontFamily: "var(--ff-mono)",
    letterSpacing: "0.06em",
    fontWeight: active ? 600 : 400,
    background: active ? "var(--amber)" : "transparent",
    color: active ? "var(--bg-0)" : "var(--ink-3)",
    border: `1px solid ${active ? "var(--amber)" : "var(--rule)"}`,
    transition: "all .12s",
    cursor: "pointer",
  });

  const thBase = {
    padding: "7px 10px",
    fontSize: 10,
    fontFamily: "var(--ff-mono)",
    fontWeight: 600,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    borderBottom: "1px solid var(--rule)",
    whiteSpace: "nowrap",
  };

  return (
    <div style={{ width: "100%", maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <div className="rule-b" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 12, marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon name="grid" size={16} style={{ color: "var(--amber)" }}/>
          <span className="h-display" style={{ fontSize: 16 }}>
            Team Stats
          </span>
          {data?.season && (
            <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
              {data.season}
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {updatedAt && (
            <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
              更新: {updatedAt.toLocaleDateString('ja-JP', { month: 'numeric', day: 'numeric' })}{' '}
              {updatedAt.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
          <button
            onClick={fetchTeamStats}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", fontSize: 11,
              border: "1px solid var(--rule)", color: "var(--ink-2)",
              opacity: loading ? 0.5 : 1,
              fontFamily: "var(--ff-mono)",
              cursor: loading ? "default" : "pointer",
            }}
          >
            <Icon name="refresh" size={12} className={loading ? "dl-spin" : ""}/>
            更新
          </button>
        </div>
      </div>

      {/* Mode toggle */}
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
        {[
          { id: 'hitting',  label: '打撃 HITTING'  },
          { id: 'pitching', label: '投手 PITCHING' },
        ].map((m) => (
          <button key={m.id} onClick={() => setMode(m.id)} style={tabBtn(mode === m.id)}>
            {m.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "80px 0", gap: 8 }}>
          <span className="think-dot"/>
          <span className="think-dot" style={{ animationDelay: ".2s" }}/>
          <span className="think-dot" style={{ animationDelay: ".4s" }}/>
          <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>取得中...</span>
        </div>
      ) : error ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px 0", gap: 10 }}>
          <span style={{ color: "var(--neg)", fontSize: 13 }}>データを取得できませんでした</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{error}</span>
          <button
            onClick={fetchTeamStats}
            style={{ marginTop: 8, padding: "6px 16px", fontSize: 12, border: "1px solid var(--rule)", color: "var(--ink-2)", cursor: "pointer" }}
          >
            再試行
          </button>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <style>{`
            .ts-row .ts-sticky { background: var(--bg-0); }
            .ts-row:hover { background: var(--bg-2); }
            .ts-row:hover .ts-sticky { background: var(--bg-2); }
          `}</style>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: 0, fontSize: 12 }}>
            <thead>
              <tr style={{ background: "var(--bg-2)" }}>
                <th style={{
                  ...thBase, textAlign: "left", color: "var(--ink-3)",
                  position: "sticky", left: 0, zIndex: 3, background: "var(--bg-2)",
                  width: STICKY_RANK_W, minWidth: STICKY_RANK_W,
                }}>順位</th>
                <th style={{
                  ...thBase, textAlign: "left", color: "var(--ink-3)",
                  position: "sticky", left: STICKY_RANK_W, zIndex: 3, background: "var(--bg-2)",
                  borderRight: "1px solid var(--rule)",
                }}>チーム</th>
                {cols.map((c) => (
                  <th
                    key={c.key}
                    onClick={() => handleSort(c.key)}
                    style={{
                      ...thBase,
                      textAlign: "center",
                      cursor: "pointer",
                      color: sortKey === c.key ? "var(--amber)" : "var(--ink-3)",
                      background: sortKey === c.key ? "oklch(0.80 0.165 80 / 0.08)" : "var(--bg-2)",
                      userSelect: "none",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 3 }}>
                      {c.label}
                      <SortIcon column={c.key}/>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((team, idx) => {
                const stats = team[mode] || {};
                return (
                  <tr
                    key={team.team_id}
                    className="ts-row"
                  >
                    <td className="ts-sticky" style={{
                      padding: "8px 10px", whiteSpace: "nowrap",
                      borderBottom: "1px solid var(--rule-dim)",
                      position: "sticky", left: 0, zIndex: 1,
                      width: STICKY_RANK_W, minWidth: STICKY_RANK_W,
                    }}>
                      {getRankBadge(idx + 1)}
                    </td>
                    <td className="ts-sticky" style={{
                      padding: "8px 10px", whiteSpace: "nowrap",
                      color: "var(--ink-0)", fontWeight: 600,
                      borderBottom: "1px solid var(--rule-dim)",
                      borderRight: "1px solid var(--rule)",
                      position: "sticky", left: STICKY_RANK_W, zIndex: 1,
                    }}>
                      {team.team_abbrev || team.team_name}
                    </td>
                    {cols.map((c) => (
                      <td
                        key={c.key}
                        className="t-mono"
                        style={{
                          padding: "8px 10px",
                          whiteSpace: "nowrap",
                          textAlign: "center",
                          fontSize: 12,
                          fontWeight: sortKey === c.key ? 700 : 400,
                          color: sortKey === c.key ? "var(--amber)" : "var(--ink-1)",
                          background: sortKey === c.key ? "oklch(0.80 0.165 80 / 0.05)" : "transparent",
                          borderBottom: "1px solid var(--rule-dim)",
                        }}
                      >
                        {formatVal(stats[c.key], c.fmt)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Legend */}
      {!loading && !error && (
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 12 }}>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>列ヘッダクリックでソート</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>RISP = Runners In Scoring Position</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>満塁 = Bases Loaded / GS = Grand Slam</span>
        </div>
      )}
    </div>
  );
}
