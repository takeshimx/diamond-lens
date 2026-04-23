import { useState, useMemo } from 'react';
import Icon from './layout/Icon.jsx';

const BATTING_METRICS = {
  'avg': 'BA', 'hr': 'HR', 'rbi': 'RBI', 'r': 'Run', 'h': 'H',
  'ops': 'OPS', 'obp': 'OBP', 'slg': 'SLG', 'woba': 'wOBA', 'war': 'WAR',
  'wrcplus': 'wRC+', 'bb': 'BB', 'so': 'SO', 'babip': 'BABIP', 'iso': 'ISO',
  'hardhitpct': 'HH%', 'barrelspct': 'Barrel%', 'pa': 'PA', 'ab': 'AB', 'g': 'G',
  'batting_average_at_risp': 'RISP打率',
  'slugging_percentage_at_risp': 'RISP長打率',
  'home_runs_at_risp': 'RISP HR',
};

const PITCHING_METRICS = {
  'era': '防御率', 'whip': 'WHIP', 'so': '奪三振', 'w': '勝', 'l': '敗',
  'sv': 'S', 'fip': 'FIP', 'war': 'WAR', 'k_9': 'K/9', 'bb_9': 'BB/9',
  'k_bb': 'K/BB', 'lobpct': 'LOB%', 'gbpct': 'GB%', 'barrelspct': 'Barrel%',
  'hardhitpct': 'HH%', 'avg': '被打率', 'ip': 'IP', 'gs': '先発',
  'bb': '与四球', 'h': '被安打', 'hr': '被HR',
};

const getMetricDisplayName = (metric, isPitching = false) => {
  if (isPitching) return PITCHING_METRICS[metric] || BATTING_METRICS[metric] || metric.toUpperCase();
  return BATTING_METRICS[metric] || metric.toUpperCase();
};

const getRankBadge = (rank) => {
  if (rank === 1) return <span className="t-mono" style={{ color: "var(--amber)", fontWeight: 700, fontSize: 13 }}>①</span>;
  if (rank === 2) return <span className="t-mono" style={{ color: "var(--ink-2)", fontWeight: 700, fontSize: 12 }}>②</span>;
  if (rank === 3) return <span className="t-mono" style={{ color: "var(--amber-dim)", fontWeight: 700, fontSize: 12 }}>③</span>;
  return <span className="t-mono" style={{ color: "var(--ink-4)", fontSize: 11 }}>{rank}</span>;
};

const formatValue = (value, metric) => {
  if (value === null || value === undefined) return '-';
  if (metric.includes('rate') || metric.includes('percentage') || metric === 'avg' ||
      metric === 'obp' || metric === 'slg' || metric === 'ops' || metric === 'woba' ||
      metric === 'babip' || metric === 'iso' || metric === 'batting_average_at_risp' ||
      metric === 'slugging_percentage_at_risp') {
    return Number(value).toFixed(3);
  }
  if (metric === 'era' || metric === 'whip' || metric === 'fip') {
    return Number(value).toFixed(2);
  }
  if (metric === 'hr' || metric === 'rbi' || metric === 'r' || metric === 'h' ||
      metric === 'bb' || metric === 'so' || metric === 'w' || metric === 'l' ||
      metric === 'sv' || metric === 'g' || metric === 'pa' || metric === 'ab' ||
      metric === 'gs' || metric === 'home_runs_at_risp') {
    return Math.round(Number(value));
  }
  return Number(value).toFixed(1);
};

const LeaderboardTable = ({ data, category, metricOrder, isLoading, error }) => {
  const isPitching = category?.id === 'pitching_leaderboard';
  const keyColumns = isPitching
    ? ['ip', 'era', 'whip', 'so', 'w', 'l', 'fip', 'k_9', 'k_bb', 'war']
    : ['avg', 'hr', 'rbi', 'r', 'obp', 'slg', 'ops', 'war', 'wrcplus', 'batting_average_at_risp', 'slugging_percentage_at_risp', 'home_runs_at_risp'];

  const [sortKey, setSortKey] = useState(metricOrder);
  const [sortDir, setSortDir] = useState('desc');

  const sortedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return [...data].sort((a, b) => {
      const av = a[sortKey] ?? (sortDir === 'desc' ? -Infinity : Infinity);
      const bv = b[sortKey] ?? (sortDir === 'desc' ? -Infinity : Infinity);
      return sortDir === 'desc' ? bv - av : av - bv;
    });
  }, [data, sortKey, sortDir]);

  const handleSort = (column) => {
    if (sortKey === column) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(column);
      setSortDir('desc');
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: 8 }}>
        <span className="think-dot"/>
        <span className="think-dot" style={{ animationDelay: ".2s" }}/>
        <span className="think-dot" style={{ animationDelay: ".4s" }}/>
        <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>リーダーボードを読み込み中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: "48px 0" }}>
        <div style={{ color: "var(--neg)", marginBottom: 6, fontSize: 13 }}>エラーが発生しました</div>
        <div className="t-mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>{error}</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "48px 0", color: "var(--ink-4)", fontSize: 13 }}>
        データが見つかりませんでした
      </div>
    );
  }

  const SortIcon = ({ column }) => {
    if (sortKey !== column) return <Icon name="chevD" size={10} style={{ opacity: 0.3 }}/>;
    return sortDir === 'desc'
      ? <Icon name="chevD" size={10} style={{ color: "var(--amber)" }}/>
      : <Icon name="chevD" size={10} style={{ color: "var(--amber)", transform: "rotate(180deg)" }}/>;
  };

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
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Header */}
      <div style={{ textAlign: "center", paddingBottom: 8, borderBottom: "1px solid var(--rule)" }}>
        <span className="h-display" style={{ fontSize: 15 }}>
          {isPitching ? '投手' : '打者'}リーダーボード
        </span>
        <span className="t-mono" style={{ display: "block", fontSize: 10, color: "var(--ink-4)", marginTop: 4 }}>
          {getMetricDisplayName(sortKey, isPitching)} でソート済み
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "var(--bg-2)" }}>
              <th style={{ ...thBase, textAlign: "left", color: "var(--ink-3)" }}>順位</th>
              <th style={{ ...thBase, textAlign: "left", color: "var(--ink-3)" }}>選手名</th>
              <th style={{ ...thBase, textAlign: "left", color: "var(--ink-3)" }}>チーム</th>
              {keyColumns.map((column) => (
                <th
                  key={column}
                  onClick={() => handleSort(column)}
                  style={{
                    ...thBase,
                    textAlign: "center",
                    cursor: "pointer",
                    color: sortKey === column ? "var(--amber)" : "var(--ink-3)",
                    background: sortKey === column ? "oklch(0.80 0.165 80 / 0.08)" : "var(--bg-2)",
                    userSelect: "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 3 }}>
                    {getMetricDisplayName(column, isPitching)}
                    <SortIcon column={column}/>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.slice(0, 30).map((player, index) => (
              <tr
                key={`${player.player_name || player.name}-${index}`}
                style={{ borderBottom: "1px solid var(--rule-dim)" }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <td style={{ padding: "8px 10px", whiteSpace: "nowrap" }}>
                  {getRankBadge(index + 1)}
                </td>
                <td style={{ padding: "8px 10px", whiteSpace: "nowrap", color: "var(--ink-0)", fontWeight: 600 }}>
                  {player.player_name || player.name}
                </td>
                <td className="t-mono" style={{ padding: "8px 10px", whiteSpace: "nowrap", color: "var(--ink-3)", fontSize: 10 }}>
                  {player.team}
                </td>
                {keyColumns.map((column) => (
                  <td
                    key={column}
                    className="t-mono"
                    style={{
                      padding: "8px 10px",
                      whiteSpace: "nowrap",
                      textAlign: "center",
                      fontSize: 12,
                      color: "var(--ink-1)",
                      fontWeight: sortKey === column ? 700 : 400,
                      color: sortKey === column ? "var(--amber)" : "var(--ink-1)",
                      background: sortKey === column ? "oklch(0.80 0.165 80 / 0.05)" : "transparent",
                    }}
                  >
                    {formatValue(player[column], column)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="t-mono" style={{ textAlign: "center", fontSize: 10, color: "var(--ink-4)" }}>
        トップ{Math.min(30, sortedData.length)}人を表示 ({sortedData.length}人中)
      </div>
    </div>
  );
};

export default LeaderboardTable;
