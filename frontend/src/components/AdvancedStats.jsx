import { useState, useMemo, useEffect, useRef } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useAuth } from '../hooks/useAuth';

import AdvancedStatsPitching from './AdvancedStatsPitching';
import AdvancedStatsBatting  from './AdvancedStatsBatting';
import {
  PITCHING_METRICS, BATTING_METRICS,
  DUMMY_PITCHERS, DUMMY_BATTERS,
  generateDummyProfile,
  getScoreColor, getBarFill,
  RADAR_COLORS, LINE_COLORS,
  getBackendUrl,
} from './advancedStatsConstants';

// Design-system color constants for recharts (CSS vars not supported in SVG attrs)
const C_AMBER  = "oklch(0.80 0.165 80)";
const C_POS    = "oklch(0.78 0.165 148)";
const C_NEG    = "oklch(0.70 0.180 28)";
const C_PURP   = "oklch(0.72 0.150 310)";
const C_INFO   = "oklch(0.75 0.120 240)";
const C_RULE   = "oklch(0.28 0.008 60)";
const C_INK3   = "oklch(0.52 0.010 75)";
const C_INK4   = "oklch(0.40 0.010 70)";
const CHART_COLORS = [C_AMBER, C_INFO, C_POS, C_PURP, C_NEG];

// Shared input style
const inputStyle = {
  background: "var(--bg-2)", color: "var(--ink-0)",
  border: "1px solid var(--rule)", padding: "5px 10px",
  fontSize: 12.5, fontFamily: "var(--ff-text)", width: "100%",
};

// ============================================================
// PlayerSearchDropdown
// ============================================================
const PlayerSearchDropdown = ({ query, setQuery, onSelect, placeholder, players }) => {
  const [isOpen, setIsOpen] = useState(false);
  const results = !query || query.length < 1
    ? []
    : players.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div style={{ position: "relative" }}>
      <input
        type="text" value={query}
        onChange={(e) => { setQuery(e.target.value); setIsOpen(true); }}
        placeholder={placeholder || 'Search player...'}
        style={{ ...inputStyle, width: 220 }}
      />
      {isOpen && results.length > 0 && (
        <div style={{
          position: "absolute", zIndex: 50, marginTop: 2, width: 280,
          background: "var(--bg-1)", border: "1px solid var(--rule)",
          maxHeight: 192, overflowY: "auto",
          boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
        }}>
          {results.map((p) => (
            <button key={p.id}
              onClick={() => { onSelect(p.id); setQuery(p.name); setIsOpen(false); }}
              style={{
                width: "100%", textAlign: "left",
                padding: "8px 12px", display: "flex",
                justifyContent: "space-between", alignItems: "center",
                fontSize: 12.5, color: "var(--ink-0)",
                borderBottom: "1px solid var(--rule-dim)",
              }}
              onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
              onMouseLeave={e => e.currentTarget.style.background = "transparent"}
            >
              <span style={{ fontWeight: 500 }}>{p.name}</span>
              <span style={{ fontSize: 11, color: "var(--ink-3)" }}>{p.team}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================================
// Main Component
// ============================================================
const AdvancedStats = () => {
  const { getIdToken } = useAuth();
  const BACKEND_URL = getBackendUrl();

  const getAuthHeaders = async () => {
    const idToken = await getIdToken();
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
    };
  };

  // --- Shared state ---
  const [view, setView]         = useState('rankings');
  const [category, setCategory] = useState('pitching');
  const [season, setSeason]     = useState(2026);

  // --- Profile state ---
  const [profilePlayerId, setProfilePlayerId] = useState(null);
  const [profileSearch, setProfileSearch]     = useState('');

  // --- Compare state ---
  const [comparePlayerA, setComparePlayerA]   = useState(null);
  const [comparePlayerB, setComparePlayerB]   = useState(null);
  const [compareSearchA, setCompareSearchA]   = useState('');
  const [compareSearchB, setCompareSearchB]   = useState('');

  // --- Trends state ---
  const trendsQueryRef = useRef('');
  const [trendsSearch, setTrendsSearch]                   = useState('');
  const [trendsSearchResults, setTrendsSearchResults]     = useState([]);
  const [trendsPlayerName, setTrendsPlayerName]           = useState('');
  const [trendsData, setTrendsData]                       = useState(null);
  const [trendsLoading, setTrendsLoading]                 = useState(false);
  const [trendsSelectedMetrics, setTrendsSelectedMetrics] = useState([]);

  useEffect(() => {
    setTrendsSearch('');
    setTrendsSearchResults([]);
    setTrendsPlayerName('');
    setTrendsData(null);
    setTrendsSelectedMetrics([]);
  }, [category]);

  // --- Derived ---
  const metrics = category === 'pitching' ? PITCHING_METRICS : BATTING_METRICS;
  const players = category === 'pitching' ? DUMMY_PITCHERS  : DUMMY_BATTERS;
  const profileData  = useMemo(() => (profilePlayerId  ? generateDummyProfile(metrics, profilePlayerId)  : null), [profilePlayerId,  category]);
  const compareDataA = useMemo(() => (comparePlayerA   ? generateDummyProfile(metrics, comparePlayerA)   : null), [comparePlayerA,   category]);
  const compareDataB = useMemo(() => (comparePlayerB   ? generateDummyProfile(metrics, comparePlayerB)   : null), [comparePlayerB,   category]);

  const getPlayer = (id) => players.find((p) => p.id === id);

  // ============================================================
  // Shared Tooltip
  // ============================================================
  const ChartTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const d = payload[0].payload;
    return (
      <div style={{
        background: "var(--bg-1)", border: "1px solid var(--rule)",
        padding: "8px 12px", fontSize: 11.5,
      }}>
        <p style={{ color: "var(--ink-0)", fontWeight: 600, marginBottom: 4 }}>
          {d.name || d.metricName || d.season || d.player_name}
        </p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: "var(--ink-2)" }}>
            {p.name}: {typeof p.value === 'number' ? (p.value < 10 ? p.value.toFixed(2) : Math.round(p.value)) : p.value}
          </p>
        ))}
      </div>
    );
  };

  // Card wrapper style
  const card = {
    border: "1px solid var(--rule)", background: "var(--bg-1)", padding: 16, marginBottom: 12,
  };

  // ============================================================
  // PROFILE VIEW
  // ============================================================
  const ProfileView = () => {
    const player   = getPlayer(profilePlayerId);
    const radarData = profileData
      ? profileData.map((d) => ({ metric: d.metricId, score: d.score, leagueAvg: d.leagueAvg, fullMark: 100 }))
      : [];
    const strengths  = profileData ? [...profileData].sort((a, b) => a.rank - b.rank).slice(0, 2)  : [];
    const weaknesses = profileData ? [...profileData].sort((a, b) => b.rank - a.rank).slice(0, 2) : [];

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
          <div>
            <div className="h-label" style={{ fontSize: 9, marginBottom: 6 }}>
              {category === 'pitching' ? '投手名' : '打者名'}
            </div>
            <PlayerSearchDropdown query={profileSearch} setQuery={setProfileSearch}
              onSelect={setProfilePlayerId}
              placeholder={category === 'pitching' ? 'e.g. Ohtani' : 'e.g. Judge'}
              players={players} />
          </div>
        </div>

        {!profileData && (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--ink-4)" }}>
            <div className="h-label" style={{ fontSize: 10 }}>選手を検索してプロファイルを表示</div>
          </div>
        )}

        {profileData && player && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={card}>
                <div style={{ fontSize: 16, fontFamily: "var(--ff-head)", fontWeight: 700, color: "var(--ink-0)", letterSpacing: "0.04em" }}>
                  {player.name}
                </div>
                <div style={{ fontSize: 11, color: "var(--ink-3)", marginBottom: 12 }}>{player.team}</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {profileData.map((d) => (
                    <div key={d.metricId} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="t-mono" style={{ fontSize: 10, color: "var(--amber)", width: 28 }}>{d.metricId}</span>
                      <span style={{ fontSize: 11.5, color: "var(--ink-2)", flex: 1 }}>{d.metricNameJp}</span>
                      <span className="t-digit" style={{ fontSize: 12, width: 40, textAlign: "right", color: d.score >= 70 ? "var(--pos)" : d.score >= 40 ? "var(--ink-1)" : "var(--neg)" }}>
                        {d.score}
                      </span>
                      <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", width: 32 }}>#{d.rank}</span>
                      <div style={{ width: 80, height: 4, background: "var(--bg-3)", position: "relative" }}>
                        <div style={{
                          height: "100%", background: d.score >= 70 ? "var(--pos)" : d.score >= 40 ? "var(--amber)" : "var(--neg)",
                          width: `${Math.min((d.score / 100) * 100, 100)}%`,
                        }}/>
                        <div style={{
                          position: "absolute", top: -2, height: "calc(100% + 4px)", width: 1,
                          background: "var(--ink-3)", left: `${d.leagueAvg}%`,
                        }}/>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={card}>
                <div className="h-label" style={{ fontSize: 9, marginBottom: 10 }}>SKILL RADAR</div>
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke={C_RULE}/>
                    <PolarAngleAxis dataKey="metric" stroke={C_INK3} tick={{ fontSize: 10, fill: C_INK3 }}/>
                    <PolarRadiusAxis angle={90} domain={[0, 100]} stroke={C_RULE} tick={{ fontSize: 9, fill: C_INK4 }}/>
                    <Radar name={player.name} dataKey="score" stroke={C_AMBER} fill={C_AMBER} fillOpacity={0.2} strokeWidth={2}/>
                    <Radar name="League Avg" dataKey="leagueAvg" stroke={C_INK3} fill="none" strokeDasharray="4 4" strokeWidth={1}/>
                    <Legend wrapperStyle={{ fontSize: 11, color: C_INK3 }}/>
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ ...card, borderColor: "var(--pos-dim)" }}>
                <div className="h-label" style={{ fontSize: 9, color: "var(--pos)", marginBottom: 8 }}>TOP STRENGTHS</div>
                {strengths.map((s) => (
                  <div key={s.metricId} style={{ fontSize: 12, color: "var(--ink-1)", marginBottom: 4 }}>
                    <span className="t-mono" style={{ color: "var(--amber)" }}>{s.metricId}</span>
                    {' '}{s.metricNameJp} — <span style={{ color: "var(--pos)", fontWeight: 600 }}>#{s.rank}</span>
                    <span style={{ color: "var(--ink-3)" }}> ({s.score})</span>
                  </div>
                ))}
              </div>
              <div style={{ ...card, borderColor: "var(--neg-dim)" }}>
                <div className="h-label" style={{ fontSize: 9, color: "var(--neg)", marginBottom: 8 }}>AREAS TO WATCH</div>
                {weaknesses.map((w) => (
                  <div key={w.metricId} style={{ fontSize: 12, color: "var(--ink-1)", marginBottom: 4 }}>
                    <span className="t-mono" style={{ color: "var(--amber)" }}>{w.metricId}</span>
                    {' '}{w.metricNameJp} — <span style={{ color: "var(--neg)", fontWeight: 600 }}>#{w.rank}</span>
                    <span style={{ color: "var(--ink-3)" }}> ({w.score})</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  // ============================================================
  // COMPARE VIEW
  // ============================================================
  const CompareView = () => {
    const playerA = getPlayer(comparePlayerA);
    const playerB = getPlayer(comparePlayerB);
    const radarData = compareDataA && compareDataB
      ? compareDataA.map((a, i) => ({ metric: a.metricId, playerA: a.score, playerB: compareDataB[i].score, fullMark: 100 }))
      : [];

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-end" }}>
          <div>
            <div className="h-label" style={{ fontSize: 9, marginBottom: 6 }}>PLAYER A</div>
            <PlayerSearchDropdown query={compareSearchA} setQuery={setCompareSearchA} onSelect={setComparePlayerA} placeholder="Player A" players={players}/>
          </div>
          <span className="t-mono" style={{ fontSize: 12, color: "var(--ink-4)", paddingBottom: 4 }}>vs</span>
          <div>
            <div className="h-label" style={{ fontSize: 9, marginBottom: 6 }}>PLAYER B</div>
            <PlayerSearchDropdown query={compareSearchB} setQuery={setCompareSearchB} onSelect={setComparePlayerB} placeholder="Player B" players={players}/>
          </div>
        </div>

        {(!compareDataA || !compareDataB) && (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--ink-4)" }}>
            <div className="h-label" style={{ fontSize: 10 }}>2選手を選択して比較</div>
          </div>
        )}

        {compareDataA && compareDataB && playerA && playerB && (
          <>
            <div style={card}>
              <div className="h-label" style={{ fontSize: 9, marginBottom: 10 }}>RADAR COMPARISON</div>
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke={C_RULE}/>
                  <PolarAngleAxis dataKey="metric" stroke={C_INK3} tick={{ fontSize: 10, fill: C_INK3 }}/>
                  <PolarRadiusAxis angle={90} domain={[0, 100]} stroke={C_RULE} tick={{ fontSize: 9, fill: C_INK4 }}/>
                  <Radar name={playerA.name} dataKey="playerA" stroke={C_AMBER} fill={C_AMBER} fillOpacity={0.18} strokeWidth={2}/>
                  <Radar name={playerB.name} dataKey="playerB" stroke={C_INFO}  fill={C_INFO}  fillOpacity={0.18} strokeWidth={2}/>
                  <Legend wrapperStyle={{ fontSize: 11, color: C_INK3 }}/>
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div style={card}>
              <div className="h-label" style={{ fontSize: 9, marginBottom: 10 }}>METRIC COMPARISON</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {compareDataA.map((a, i) => {
                  const b    = compareDataB[i];
                  const diff = a.score - b.score;
                  return (
                    <div key={a.metricId} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="t-digit" style={{ fontSize: 11, width: 40, textAlign: "right", color: diff > 0 ? C_AMBER : "var(--ink-4)" }}>{a.score}</span>
                      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 4 }}>
                        <div style={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
                          <div style={{ height: 10, width: `${a.score}%`, background: C_AMBER, opacity: 0.7 }}/>
                        </div>
                        <span className="t-mono" style={{ fontSize: 9.5, color: "var(--amber)", width: 36, textAlign: "center" }}>{a.metricId}</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ height: 10, width: `${b.score}%`, background: C_INFO, opacity: 0.7 }}/>
                        </div>
                      </div>
                      <span className="t-digit" style={{ fontSize: 11, width: 40, color: diff < 0 ? C_INFO : "var(--ink-4)" }}>{b.score}</span>
                    </div>
                  );
                })}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
                <span style={{ fontSize: 11, color: C_AMBER, fontWeight: 600 }}>{playerA.name}</span>
                <span style={{ fontSize: 11, color: C_INFO,  fontWeight: 600 }}>{playerB.name}</span>
              </div>
            </div>

            <div style={card}>
              <div className="h-label" style={{ fontSize: 9, marginBottom: 10 }}>SUMMARY</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 11, color: C_AMBER, fontWeight: 600, marginBottom: 6 }}>{playerA.name} が優位</div>
                  {compareDataA.map((a, i) => ({ ...a, diff: a.score - compareDataB[i].score }))
                    .filter((x) => x.diff > 0).sort((a, b) => b.diff - a.diff).slice(0, 3)
                    .map((x) => (
                      <div key={x.metricId} style={{ fontSize: 11.5, color: "var(--ink-2)", marginBottom: 3 }}>
                        <span className="t-mono" style={{ color: "var(--amber)" }}>{x.metricId}</span> {x.metricNameJp}
                        <span style={{ color: "var(--pos)" }}> (+{x.diff.toFixed(1)})</span>
                      </div>
                    ))}
                </div>
                <div>
                  <div style={{ fontSize: 11, color: C_INFO, fontWeight: 600, marginBottom: 6 }}>{playerB.name} が優位</div>
                  {compareDataA.map((a, i) => ({ ...a, diff: compareDataB[i].score - a.score }))
                    .filter((x) => x.diff > 0).sort((a, b) => b.diff - a.diff).slice(0, 3)
                    .map((x) => (
                      <div key={x.metricId} style={{ fontSize: 11.5, color: "var(--ink-2)", marginBottom: 3 }}>
                        <span className="t-mono" style={{ color: "var(--amber)" }}>{x.metricId}</span> {x.metricNameJp}
                        <span style={{ color: "var(--pos)" }}> (+{x.diff.toFixed(1)})</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  // ============================================================
  // TRENDS VIEW
  // ============================================================
  const TrendsView = () => {
    const toggleMetric = (metricId) => {
      setTrendsSelectedMetrics((prev) =>
        prev.includes(metricId) ? prev.filter((m) => m !== metricId) : [...prev, metricId]
      );
    };

    const handleSearchChange = async (val) => {
      trendsQueryRef.current = val;
      setTrendsSearch(val);
      setTrendsSearchResults([]);
      if (val.length < 2) return;
      try {
        const endpoint = category === 'pitching'
          ? `/api/v1/advanced-stats/pitching/search?name=${encodeURIComponent(val)}&season=2025&limit=10`
          : `/api/v1/advanced-stats/batting/search?name=${encodeURIComponent(val)}&season=2025&limit=10`;
        const headers = await getAuthHeaders();
        const res = await fetch(`${BACKEND_URL}${endpoint}`, { headers });
        const data = await res.json();
        if (trendsQueryRef.current !== val) return;
        setTrendsSearchResults(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error('Search error:', e);
      }
    };

    const handleSelectPlayer = async (playerId, playerName) => {
      trendsQueryRef.current = playerName;
      setTrendsPlayerName(playerName);
      setTrendsSearch(playerName);
      setTrendsSearchResults([]);
      setTrendsData(null);
      setTrendsLoading(true);
      try {
        const endpoint = category === 'pitching'
          ? `/api/v1/advanced-stats/pitching/trends/${playerId}`
          : `/api/v1/advanced-stats/batting/trends/${playerId}`;
        const headers = await getAuthHeaders();
        const res = await fetch(`${BACKEND_URL}${endpoint}`, { headers });
        const data = await res.json();
        setTrendsData(data.trends || []);
      } catch (e) {
        console.error('Trends error:', e);
      } finally {
        setTrendsLoading(false);
      }
    };

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
          <div>
            <div className="h-label" style={{ fontSize: 9, marginBottom: 6 }}>
              {category === 'pitching' ? '投手名' : '打者名'}
            </div>
            <div style={{ position: "relative" }}>
              <input
                type="text" value={trendsSearch}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder="Search player..."
                style={{ ...inputStyle, width: 220 }}
              />
              {trendsSearchResults.length > 0 && (
                <div style={{
                  position: "absolute", zIndex: 50, marginTop: 2, width: 280,
                  background: "var(--bg-1)", border: "1px solid var(--rule)",
                  maxHeight: 192, overflowY: "auto",
                }}>
                  {trendsSearchResults.map((p) => {
                    const id = p.pitcher_id ?? p.batter_id;
                    return (
                      <button key={id} onClick={() => handleSelectPlayer(id, p.player_name)}
                        style={{
                          width: "100%", textAlign: "left", padding: "8px 12px",
                          display: "flex", justifyContent: "space-between",
                          fontSize: 12.5, color: "var(--ink-0)",
                          borderBottom: "1px solid var(--rule-dim)",
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
                        onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                      >
                        <span style={{ fontWeight: 500 }}>{p.player_name}</span>
                        <span style={{ fontSize: 11, color: "var(--ink-3)" }}>{p.team}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Metric toggles */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {metrics.map((m, i) => {
            const active = trendsSelectedMetrics.includes(m.id);
            return (
              <button key={m.id} onClick={() => toggleMetric(m.id)} style={{
                padding: "3px 8px", fontSize: 10.5,
                border: `1px solid ${active ? CHART_COLORS[i % CHART_COLORS.length] : "var(--rule)"}`,
                color: active ? "var(--ink-0)" : "var(--ink-3)",
                background: active ? `${CHART_COLORS[i % CHART_COLORS.length]}20` : "transparent",
                fontFamily: "var(--ff-mono)",
                transition: "all .1s",
              }}>
                {m.id}: {m.name}
              </button>
            );
          })}
        </div>

        {trendsLoading && (
          <div style={{ textAlign: "center", padding: "48px 0" }}>
            <span className="think-dot"/><span className="think-dot" style={{ animationDelay: ".2s" }}/><span className="think-dot" style={{ animationDelay: ".4s" }}/>
          </div>
        )}
        {!trendsLoading && !trendsData && (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--ink-4)" }}>
            <div className="h-label" style={{ fontSize: 10 }}>選手を検索してトレンドを表示</div>
          </div>
        )}
        {!trendsLoading && trendsData && trendsPlayerName && trendsSelectedMetrics.length > 0 && (
          <>
            <div style={card}>
              <div className="h-label" style={{ fontSize: 9, marginBottom: 10 }}>
                {trendsPlayerName} — SEASON TRENDS
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={trendsData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C_RULE}/>
                  <XAxis dataKey="season" stroke={C_INK3} tick={{ fontSize: 11, fill: C_INK3 }}/>
                  <YAxis stroke={C_INK3} tick={{ fontSize: 11, fill: C_INK3 }} domain={['auto', 'auto']}/>
                  <Tooltip content={<ChartTooltip/>}/>
                  <Legend wrapperStyle={{ fontSize: 11, color: C_INK3 }}/>
                  {trendsSelectedMetrics.map((metricId, i) => {
                    const m = metrics.find((x) => x.id === metricId);
                    return (
                      <Line key={metricId} type="monotone" dataKey={metricId}
                        name={`${metricId}: ${m?.nameJp || m?.name}`}
                        stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2}
                        dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls/>
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div style={card}>
              <div className="h-label" style={{ fontSize: 9, marginBottom: 10 }}>YEAR-OVER-YEAR</div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                  <thead>
                    <tr className="rule-b">
                      <th style={{ textAlign: "left", padding: "6px 10px", color: "var(--ink-3)", fontWeight: 600, letterSpacing: "0.1em", fontSize: 9.5 }}>METRIC</th>
                      {trendsData.map((row) => (
                        <th key={row.season} style={{ textAlign: "right", padding: "6px 10px", color: "var(--ink-3)", fontWeight: 600, fontSize: 9.5 }}>{row.season}</th>
                      ))}
                      <th style={{ textAlign: "right", padding: "6px 10px", color: "var(--ink-3)", fontWeight: 600, fontSize: 9.5 }}>YoY</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trendsSelectedMetrics.map((metricId) => {
                      const m      = metrics.find((x) => x.id === metricId);
                      const dec    = m?.decimals ?? 0;
                      const fmt    = (v) => v != null ? v.toFixed(dec) : '—';
                      const latest = trendsData[trendsData.length - 1]?.[metricId];
                      const prev   = trendsData[trendsData.length - 2]?.[metricId];
                      const yoy    = latest != null && prev != null ? latest - prev : null;
                      return (
                        <tr key={metricId} style={{ borderBottom: "1px solid var(--rule-dim)" }}>
                          <td style={{ padding: "7px 10px", color: "var(--ink-1)" }}>
                            <span className="t-mono" style={{ color: "var(--amber)", marginRight: 6 }}>{metricId}</span>
                            {m?.nameJp}
                          </td>
                          {trendsData.map((row) => (
                            <td key={row.season} style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-1)", fontFamily: "var(--ff-mono)" }}>
                              {fmt(row[metricId])}
                            </td>
                          ))}
                          <td style={{ padding: "7px 10px", textAlign: "right", fontFamily: "var(--ff-mono)", fontWeight: 600, color: yoy > 0 ? "var(--pos)" : yoy < 0 ? "var(--neg)" : "var(--ink-4)" }}>
                            {yoy != null ? `${yoy > 0 ? '+' : ''}${yoy.toFixed(dec)}` : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  // ============================================================
  // Main Render
  // ============================================================
  const SUB_TABS = [
    { key: 'rankings', label: 'RANKINGS' },
    { key: 'profile',  label: 'PROFILE'  },
    { key: 'compare',  label: 'COMPARE'  },
    { key: 'trends',   label: 'TRENDS'   },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0, height: "100%" }}>
      {/* Filter bar */}
      <div className="rule-b" style={{ padding: "10px 0 10px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, flexShrink: 0 }}>
        {/* Sub-tabs */}
        <div style={{ display: "flex" }}>
          {SUB_TABS.map((tab) => (
            <button key={tab.key} onClick={() => setView(tab.key)} style={{
              padding: "5px 12px", fontSize: 10.5,
              fontFamily: "var(--ff-mono)", letterSpacing: "0.08em", fontWeight: 600,
              border: "1px solid var(--rule)",
              marginRight: -1,
              color: view === tab.key ? "var(--bg-0)" : "var(--ink-2)",
              background: view === tab.key ? "var(--amber)" : "transparent",
              transition: "all .1s",
            }}>{tab.label}</button>
          ))}
        </div>

        <div style={{ width: 1, height: 20, background: "var(--rule)" }}/>

        {/* Category */}
        <div style={{ display: "flex" }}>
          <button onClick={() => setCategory('pitching')} style={{
            padding: "5px 12px", fontSize: 10.5,
            fontFamily: "var(--ff-mono)", letterSpacing: "0.06em", fontWeight: 600,
            border: "1px solid var(--rule)", marginRight: -1,
            color: category === 'pitching' ? "var(--bg-0)" : "var(--ink-2)",
            background: category === 'pitching' ? "var(--amber)" : "transparent",
            transition: "all .1s",
          }}>PITCHING</button>
          <button onClick={() => setCategory('batting')} style={{
            padding: "5px 12px", fontSize: 10.5,
            fontFamily: "var(--ff-mono)", letterSpacing: "0.06em", fontWeight: 600,
            border: "1px solid var(--rule)",
            color: category === 'batting' ? "var(--bg-0)" : "var(--ink-2)",
            background: category === 'batting' ? "var(--amber)" : "transparent",
            transition: "all .1s",
          }}>BATTING</button>
        </div>

        <div style={{ width: 1, height: 20, background: "var(--rule)" }}/>

        {/* Season */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="h-label" style={{ fontSize: 9 }}>SEASON</span>
          <select value={season} onChange={(e) => setSeason(Number(e.target.value))} style={{
            background: "var(--bg-2)", color: "var(--ink-0)",
            border: "1px solid var(--rule)", padding: "4px 8px",
            fontSize: 12, fontFamily: "var(--ff-mono)",
          }}>
            {[2026, 2025, 2024, 2023, 2022, 2021].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", paddingTop: 16 }}>
        {view === 'rankings' && category === 'pitching' && (
          <AdvancedStatsPitching season={season} getAuthHeaders={getAuthHeaders} BACKEND_URL={BACKEND_URL}/>
        )}
        {view === 'rankings' && category === 'batting' && (
          <AdvancedStatsBatting season={season} getAuthHeaders={getAuthHeaders} BACKEND_URL={BACKEND_URL}/>
        )}
        {view === 'profile'  && ProfileView()}
        {view === 'compare'  && CompareView()}
        {view === 'trends'   && TrendsView()}
      </div>
    </div>
  );
};

export default AdvancedStats;
