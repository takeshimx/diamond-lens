import React, { useState, useEffect, useRef } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { useAuth } from '../hooks/useAuth';
import Icon from './layout/Icon.jsx';

// Recharts SVG hardcoded colors (CSS vars don't work reliably in SVG attributes)
const C_GRID   = '#3a3520';
const C_AXIS   = '#7a6a45';
const C_TICK   = '#9a8a6a';
const C_AMBER  = 'oklch(0.80 0.165 80)';
const C_POS    = 'oklch(0.78 0.165 148)';
const C_NEG    = 'oklch(0.70 0.180 28)';
const C_INFO   = 'oklch(0.75 0.120 240)';
const C_PURP   = 'oklch(0.72 0.150 310)';

const PITCH_COLORS = [C_AMBER, C_NEG, C_POS, C_INFO, C_PURP,
  'oklch(0.82 0.15 340)', 'oklch(0.78 0.14 200)', 'oklch(0.75 0.16 55)'];

const StuffPlus = () => {
  const { getIdToken } = useAuth();
  const [view, setView] = useState('rankings');

  // Rankings state
  const [rankings, setRankings] = useState([]);
  const [rankingsTotal, setRankingsTotal] = useState(0);
  const [rankingsModelType, setRankingsModelType] = useState('stuff_plus');
  const [rankingsSeason, setRankingsSeason] = useState(2025);
  const [rankingsSortOrder, setRankingsSortOrder] = useState('desc');
  const [rankingsOffset, setRankingsOffset] = useState(0);
  const [rankingsLimit] = useState(25);
  const [rankingsMinPitches, setRankingsMinPitches] = useState(100);

  // Detail state
  const [detailPitcherId, setDetailPitcherId] = useState('');
  const [detailSearchQuery, setDetailSearchQuery] = useState('');
  const [detailSuggestions, setDetailSuggestions] = useState([]);
  const [detailShowSuggestions, setDetailShowSuggestions] = useState(false);
  const [detailModelType, setDetailModelType] = useState('stuff_plus');
  const [detailSeason, setDetailSeason] = useState(2025);
  const [detailResult, setDetailResult] = useState(null);
  const detailSearchRef = useRef(null);

  // Compare state
  const [comparePitcherId, setComparePitcherId] = useState('');
  const [compareSearchQuery, setCompareSearchQuery] = useState('');
  const [compareSuggestions, setCompareSuggestions] = useState([]);
  const [compareShowSuggestions, setCompareShowSuggestions] = useState(false);
  const [compareSeason, setCompareSeason] = useState(2025);
  const [compareResult, setCompareResult] = useState(null);
  const compareSearchRef = useRef(null);

  // Trend state
  const [trendPitcherId, setTrendPitcherId] = useState('');
  const [trendSearchQuery, setTrendSearchQuery] = useState('');
  const [trendSuggestions, setTrendSuggestions] = useState([]);
  const [trendShowSuggestions, setTrendShowSuggestions] = useState(false);
  const [trendModelType, setTrendModelType] = useState('stuff_plus');
  const [trendSeason, setTrendSeason] = useState(2025);
  const [trendResult, setTrendResult] = useState(null);
  const trendSearchRef = useRef(null);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

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

  const getAuthHeaders = async () => {
    const idToken = await getIdToken();
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
    };
  };

  // ----------------------------------------------------------
  // スコア色 (CSS var文字列を返す)
  // ----------------------------------------------------------
  const getScoreColor = (score) => {
    if (score >= 120) return C_POS;
    if (score >= 110) return 'oklch(0.73 0.145 148)';
    if (score >= 90)  return C_AMBER;
    if (score >= 80)  return 'oklch(0.78 0.16 50)';
    return C_NEG;
  };

  const getBarColor = (score) => {
    if (score >= 120) return C_POS;
    if (score >= 110) return 'oklch(0.73 0.145 148)';
    if (score >= 90)  return C_AMBER;
    if (score >= 80)  return 'oklch(0.78 0.16 50)';
    return C_NEG;
  };

  const getProfileStyle = (profile) => {
    switch (profile) {
      case 'stuff_dominant':   return { background: "oklch(0.75 0.12 240 / 0.15)", color: C_INFO, border: "1px solid oklch(0.75 0.12 240 / 0.3)" };
      case 'command_dominant': return { background: "oklch(0.72 0.15 310 / 0.15)", color: C_PURP, border: "1px solid oklch(0.72 0.15 310 / 0.3)" };
      default:                 return { background: "oklch(0.78 0.165 148 / 0.15)", color: C_POS,  border: "1px solid oklch(0.78 0.165 148 / 0.3)" };
    }
  };

  // ----------------------------------------------------------
  // 選手名検索
  // ----------------------------------------------------------
  const searchPitchers = async (query, season) => {
    if (!query || query.length < 2) return [];
    try {
      const params = new URLSearchParams({ name: query, season, limit: 10 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/search?${params}`, { headers });
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  };

  useEffect(() => {
    if (detailSearchQuery.length < 2) { setDetailSuggestions([]); return; }
    const timer = setTimeout(async () => {
      const results = await searchPitchers(detailSearchQuery, detailSeason);
      setDetailSuggestions(results);
      setDetailShowSuggestions(results.length > 0);
    }, 300);
    return () => clearTimeout(timer);
  }, [detailSearchQuery, detailSeason]);

  useEffect(() => {
    if (compareSearchQuery.length < 2) { setCompareSuggestions([]); return; }
    const timer = setTimeout(async () => {
      const results = await searchPitchers(compareSearchQuery, compareSeason);
      setCompareSuggestions(results);
      setCompareShowSuggestions(results.length > 0);
    }, 300);
    return () => clearTimeout(timer);
  }, [compareSearchQuery, compareSeason]);

  useEffect(() => {
    if (trendSearchQuery.length < 2) { setTrendSuggestions([]); return; }
    const timer = setTimeout(async () => {
      const results = await searchPitchers(trendSearchQuery, trendSeason);
      setTrendSuggestions(results);
      setTrendShowSuggestions(results.length > 0);
    }, 300);
    return () => clearTimeout(timer);
  }, [trendSearchQuery, trendSeason]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (detailSearchRef.current && !detailSearchRef.current.contains(e.target)) setDetailShowSuggestions(false);
      if (compareSearchRef.current && !compareSearchRef.current.contains(e.target)) setCompareShowSuggestions(false);
      if (trendSearchRef.current && !trendSearchRef.current.contains(e.target)) setTrendShowSuggestions(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ----------------------------------------------------------
  // API fetchers
  // ----------------------------------------------------------
  const fetchRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({
        model_type: rankingsModelType, season: rankingsSeason,
        limit: rankingsLimit, offset: rankingsOffset,
        sort_order: rankingsSortOrder, min_pitches: rankingsMinPitches,
      });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setRankings((data.rankings || []).filter(r => r.pitch_name !== 'Pitch Out'));
      setRankingsTotal(data.total || 0);
    } catch (e) { setError(e.message); } finally { setIsLoading(false); }
  };

  useEffect(() => {
    if (view === 'rankings') fetchRankings();
  }, [view, rankingsModelType, rankingsSeason, rankingsSortOrder, rankingsOffset, rankingsMinPitches]);

  const fetchPitcherDetail = async () => {
    if (!detailPitcherId) return;
    setIsLoading(true); setError(null); setDetailResult(null);
    try {
      const params = new URLSearchParams({ model_type: detailModelType, season: detailSeason });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/pitcher/${detailPitcherId}?${params}`, { headers });
      if (!res.ok) {
        if (res.status === 404) throw new Error('投手が見つかりませんでした');
        if (res.status === 503) throw new Error('モデルが利用できません');
        throw new Error(`API error: ${res.status}`);
      }
      const data = await res.json();
      if (data.pitches) data.pitches = data.pitches.filter(p => p.pitch_name !== 'Pitch Out');
      setDetailResult(data);
    } catch (e) { setError(e.message); } finally { setIsLoading(false); }
  };

  useEffect(() => {
    if (view === 'detail' && detailPitcherId) fetchPitcherDetail();
  }, [detailModelType]);

  const fetchCompare = async () => {
    if (!comparePitcherId) return;
    setIsLoading(true); setError(null); setCompareResult(null);
    try {
      const params = new URLSearchParams({ season: compareSeason });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/pitcher/${comparePitcherId}/compare?${params}`, { headers });
      if (!res.ok) {
        if (res.status === 404) throw new Error('投手が見つかりませんでした');
        if (res.status === 503) throw new Error('モデルが利用できません');
        throw new Error(`API error: ${res.status}`);
      }
      const data = await res.json();
      if (data.comparison) data.comparison = data.comparison.filter(c => c.pitch_name !== 'Pitch Out');
      setCompareResult(data);
    } catch (e) { setError(e.message); } finally { setIsLoading(false); }
  };

  const fetchTrend = async () => {
    if (!trendPitcherId) return;
    setIsLoading(true); setError(null); setTrendResult(null);
    try {
      const params = new URLSearchParams({ model_type: trendModelType, season: trendSeason });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/pitcher/${trendPitcherId}/trend?${params}`, { headers });
      if (!res.ok) {
        if (res.status === 404) throw new Error('投手が見つかりませんでした');
        if (res.status === 503) throw new Error('モデルが利用できません');
        throw new Error(`API error: ${res.status}`);
      }
      setTrendResult(await res.json());
    } catch (e) { setError(e.message); } finally { setIsLoading(false); }
  };

  useEffect(() => {
    if (view === 'trend' && trendPitcherId) fetchTrend();
  }, [trendModelType]);

  const goToDetail = (pitcherId, playerName) => {
    setDetailPitcherId(String(pitcherId));
    setDetailSearchQuery(playerName || '');
    setDetailShowSuggestions(false);
    setView('detail');
  };

  // ----------------------------------------------------------
  // Shared style helpers
  // ----------------------------------------------------------
  const inputStyle = {
    border: "1px solid var(--rule)", background: "var(--bg-1)",
    color: "var(--ink-0)", padding: "6px 10px", fontSize: 12,
    fontFamily: "var(--ff-mono)",
  };

  const selectStyle = {
    ...inputStyle, padding: "6px 10px",
  };

  const tabBtn = (active) => ({
    padding: "5px 14px", fontSize: 11,
    fontFamily: "var(--ff-mono)", letterSpacing: "0.06em",
    background: active ? "var(--amber)" : "transparent",
    color: active ? "var(--bg-0)" : "var(--ink-3)",
    border: `1px solid ${active ? "var(--amber)" : "var(--rule)"}`,
    fontWeight: active ? 600 : 400,
    transition: "all .12s",
  });

  const MODEL_CFG = {
    stuff_plus:        { label: "Stuff+",     color: C_INFO },
    pitching_plus:     { label: "Pitching+",  color: C_PURP },
    pitching_plus_plus:{ label: "Pitching++", color: C_POS  },
  };

  const modelBtn = (active, model) => {
    const cfg = MODEL_CFG[model];
    return {
      padding: "5px 12px", fontSize: 11, fontFamily: "var(--ff-mono)", fontWeight: active ? 600 : 400,
      background: active ? cfg.color : "var(--bg-2)",
      color: active ? "var(--bg-0)" : "var(--ink-3)",
      border: `1px solid ${active ? cfg.color : "var(--rule)"}`,
      transition: "all .12s",
    };
  };

  const actionBtn = (disabled) => ({
    display: "inline-flex", alignItems: "center", gap: 6,
    padding: "6px 16px", fontSize: 11,
    fontFamily: "var(--ff-mono)", fontWeight: 600, letterSpacing: "0.06em",
    background: disabled ? "var(--bg-3)" : "var(--amber)",
    color: disabled ? "var(--ink-4)" : "var(--bg-0)",
    border: "none", opacity: disabled ? 0.5 : 1,
    cursor: disabled ? "not-allowed" : "pointer",
    transition: "all .12s",
  });

  const SearchInput = ({ value, onChange, placeholder, inputRef, suggestions, showSuggestions, onSelect, season }) => (
    <div style={{ position: "relative" }} ref={inputRef}>
      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <Icon name="search" size={13} style={{ position: "absolute", left: 8, color: "var(--ink-4)", pointerEvents: "none" }}/>
        <input
          type="text"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          style={{ ...inputStyle, paddingLeft: 28, width: 200 }}
        />
      </div>
      {showSuggestions && suggestions.length > 0 && (
        <div style={{ position: "absolute", zIndex: 50, top: "100%", marginTop: 2, width: 280, background: "var(--bg-1)", border: "1px solid var(--rule-hi)", maxHeight: 240, overflowY: "auto" }}>
          {suggestions.map((s) => (
            <button
              key={s.pitcher_id}
              onClick={() => onSelect(s)}
              style={{ width: "100%", textAlign: "left", padding: "8px 12px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--rule-dim)" }}
              onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
              onMouseLeave={e => e.currentTarget.style.background = "transparent"}
            >
              <span style={{ color: "var(--ink-0)", fontSize: 12, fontWeight: 600 }}>{s.player_name}</span>
              <span className="t-mono" style={{ color: "var(--ink-4)", fontSize: 10 }}>{s.team} / {s.hand === 'R' ? 'RHP' : s.hand === 'L' ? 'LHP' : s.hand}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );

  const chartContainer = { border: "1px solid var(--rule)", background: "var(--bg-1)", padding: 16, marginTop: 12 };

  const DetailChartTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div style={{ background: "var(--bg-1)", border: "1px solid var(--rule-hi)", padding: "10px 12px", fontSize: 12 }}>
        <p style={{ color: "var(--ink-0)", fontWeight: 600, marginBottom: 4 }}>{d.pitch_name}</p>
        <p style={{ color: getScoreColor(d.score) }}>Score: {d.score}</p>
        <p style={{ color: "var(--ink-2)" }}>投球数: {d.pitch_count}</p>
        <p style={{ color: "var(--ink-2)" }}>平均球速: {d.avg_velo} mph</p>
        <p style={{ color: "var(--ink-2)" }}>平均回転数: {d.avg_spin} rpm</p>
      </div>
    );
  };

  const CompareChartTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div style={{ background: "var(--bg-1)", border: "1px solid var(--rule-hi)", padding: "10px 12px", fontSize: 12 }}>
        <p style={{ color: "var(--ink-0)", fontWeight: 600, marginBottom: 4 }}>{d.pitch_name}</p>
        {d.stuff_plus != null && <p style={{ color: C_INFO }}>Stuff+: {d.stuff_plus}</p>}
        {d.pitching_plus != null && <p style={{ color: C_PURP }}>Pitching+: {d.pitching_plus}</p>}
        {d.pitching_plus_plus != null && <p style={{ color: C_POS }}>Pitching++: {d.pitching_plus_plus}</p>}
        {d.gap != null && <p style={{ color: "var(--ink-2)" }}>Gap: {d.gap > 0 ? '+' : ''}{d.gap}</p>}
        <p style={{ color: "var(--ink-2)" }}>投球数: {d.pitch_count}</p>
      </div>
    );
  };

  const MONTH_LABELS = { 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov' };

  const TrendChartTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const monthEntry = trendResult?.monthly?.find(m => m.month === label);
    return (
      <div style={{ background: "var(--bg-1)", border: "1px solid var(--rule-hi)", padding: "10px 12px", fontSize: 12 }}>
        <p style={{ color: "var(--ink-0)", fontWeight: 600, marginBottom: 4 }}>{MONTH_LABELS[label] || `Month ${label}`}</p>
        {payload.map((p, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
            <span style={{ width: 8, height: 8, background: p.color, display: "inline-block", flexShrink: 0 }}/>
            <span style={{ color: "var(--ink-2)" }}>{p.name}:</span>
            <span style={{ fontWeight: 600, color: getScoreColor(p.value) }}>{p.value}</span>
            {monthEntry && monthEntry[`${p.name}_count`] != null && (
              <span className="t-mono" style={{ color: "var(--ink-4)", fontSize: 10 }}>({monthEntry[`${p.name}_count`]}球)</span>
            )}
          </div>
        ))}
      </div>
    );
  };

  const tableThStyle = (align = "left") => ({
    padding: "6px 10px", fontSize: 10, textAlign: align,
    color: "var(--ink-3)", fontFamily: "var(--ff-mono)",
    fontWeight: 600, letterSpacing: "0.08em",
    borderBottom: "1px solid var(--rule)",
    background: "var(--bg-2)", textTransform: "uppercase",
  });

  // ==========================================================
  // RankingsView
  // ==========================================================
  const RankingsView = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Controls */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
        <div style={{ display: "flex", gap: 2 }}>
          {Object.keys(MODEL_CFG).map(m => (
            <button key={m} onClick={() => { setRankingsModelType(m); setRankingsOffset(0); }} style={modelBtn(rankingsModelType === m, m)}>
              {MODEL_CFG[m].label}
            </button>
          ))}
        </div>

        <select value={rankingsSeason} onChange={(e) => { setRankingsSeason(Number(e.target.value)); setRankingsOffset(0); }} style={selectStyle}>
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => <option key={y} value={y}>{y}</option>)}
        </select>

        <button
          onClick={() => { setRankingsSortOrder(prev => prev === 'desc' ? 'asc' : 'desc'); setRankingsOffset(0); }}
          style={{ ...inputStyle, display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer" }}
        >
          <Icon name="chevD" size={12} style={{ transform: rankingsSortOrder === 'asc' ? 'rotate(180deg)' : 'none' }}/>
          {rankingsSortOrder === 'desc' ? 'High → Low' : 'Low → High'}
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <label className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)", whiteSpace: "nowrap" }}>MIN投球数</label>
          <input
            type="number"
            value={rankingsMinPitches}
            onChange={(e) => { setRankingsMinPitches(Number(e.target.value)); setRankingsOffset(0); }}
            min={0} max={5000} step={50}
            style={{ ...inputStyle, width: 70 }}
          />
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>
              {['#','Player','Team','Hand','Pitch','Score','Count','Velo (mph)','Spin (rpm)'].map((h, i) => (
                <th key={h} style={tableThStyle(i >= 5 ? "right" : "left")}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rankings.map((r, i) => (
              <tr
                key={`${r.pitcher_id}-${r.pitch_name}-${i}`}
                style={{ borderBottom: "1px solid var(--rule-dim)", cursor: "pointer" }}
                onClick={() => goToDetail(r.pitcher_id, r.player_name)}
                onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <td className="t-mono" style={{ padding: "7px 10px", color: "var(--ink-4)" }}>{rankingsOffset + i + 1}</td>
                <td style={{ padding: "7px 10px", color: "var(--ink-0)", fontWeight: 600 }}>{r.player_name}</td>
                <td className="t-mono" style={{ padding: "7px 10px", color: "var(--ink-3)", fontSize: 10 }}>{r.team}</td>
                <td className="t-mono" style={{ padding: "7px 10px", color: "var(--ink-3)", fontSize: 10 }}>{r.hand === 'R' ? 'RHP' : r.hand === 'L' ? 'LHP' : r.hand}</td>
                <td style={{ padding: "7px 10px", color: "var(--ink-1)" }}>{r.pitch_name}</td>
                <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: getScoreColor(r.score), fontWeight: 700 }}>{r.score}</td>
                <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{r.pitch_count}</td>
                <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{r.avg_velo}</td>
                <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{r.avg_spin}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {rankingsTotal > 0 && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 4 }}>
          <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
            {rankingsOffset + 1} - {Math.min(rankingsOffset + rankingsLimit, rankingsTotal)} / {rankingsTotal}
          </span>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              disabled={rankingsOffset === 0}
              onClick={() => setRankingsOffset(Math.max(0, rankingsOffset - rankingsLimit))}
              style={{ padding: 6, border: "1px solid var(--rule)", color: "var(--ink-2)", opacity: rankingsOffset === 0 ? 0.4 : 1 }}
            >
              <Icon name="chevL" size={14}/>
            </button>
            <button
              disabled={rankingsOffset + rankingsLimit >= rankingsTotal}
              onClick={() => setRankingsOffset(rankingsOffset + rankingsLimit)}
              style={{ padding: 6, border: "1px solid var(--rule)", color: "var(--ink-2)", opacity: rankingsOffset + rankingsLimit >= rankingsTotal ? 0.4 : 1 }}
            >
              <Icon name="chevR" size={14}/>
            </button>
          </div>
        </div>
      )}
    </div>
  );

  // ==========================================================
  // DetailView
  // ==========================================================
  const DetailView = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
        <div>
          <div className="h-label" style={{ fontSize: 9, marginBottom: 4 }}>投手名</div>
          <SearchInput
            value={detailSearchQuery}
            onChange={(e) => { setDetailSearchQuery(e.target.value); setDetailPitcherId(''); setDetailShowSuggestions(true); }}
            placeholder="e.g. Yamamoto"
            inputRef={detailSearchRef}
            suggestions={detailSuggestions}
            showSuggestions={detailShowSuggestions}
            onSelect={(s) => { setDetailPitcherId(String(s.pitcher_id)); setDetailSearchQuery(s.player_name); setDetailShowSuggestions(false); }}
          />
        </div>

        <div style={{ display: "flex", gap: 2 }}>
          {Object.keys(MODEL_CFG).map(m => (
            <button key={m} onClick={() => setDetailModelType(m)} style={modelBtn(detailModelType === m, m)}>
              {MODEL_CFG[m].label}
            </button>
          ))}
        </div>

        <select value={detailSeason} onChange={(e) => setDetailSeason(Number(e.target.value))} style={selectStyle}>
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => <option key={y} value={y}>{y}</option>)}
        </select>

        <button onClick={fetchPitcherDetail} disabled={!detailPitcherId || isLoading} style={actionBtn(!detailPitcherId || isLoading)}>
          <Icon name="search" size={12}/>検索
        </button>
      </div>

      {detailResult && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="h-display" style={{ fontSize: 16 }}>{detailResult.player_name}</span>
            <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
              {MODEL_CFG[detailResult.model_type]?.label ?? detailResult.model_type} / {detailResult.season}
            </span>
          </div>

          <div style={chartContainer}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={detailResult.pitches} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={C_GRID}/>
                <XAxis dataKey="pitch_name" stroke={C_AXIS} tick={{ fontSize: 11, fill: C_TICK }}/>
                <YAxis stroke={C_AXIS} tick={{ fontSize: 11, fill: C_TICK }} domain={[60, 160]}/>
                <Tooltip content={<DetailChartTooltip/>}/>
                <ReferenceLine y={100} stroke={C_AXIS} strokeDasharray="4 4" label={{ value: 'Avg (100)', fill: C_TICK, fontSize: 10 }}/>
                <Bar dataKey="score" radius={[2, 2, 0, 0]} label={{ position: 'top', fill: C_TICK, fontSize: 10 }}>
                  {detailResult.pitches.map((entry, index) => (
                    <rect key={index} fill={getBarColor(entry.score)}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr>
                  {['Pitch','Score','Count','Velo (mph)','Spin (rpm)','Pred RE','Actual RE','Sample'].map((h, i) => (
                    <th key={h} style={tableThStyle(i === 0 ? "left" : i === 7 ? "center" : "right")}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {detailResult.pitches.map((p, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--rule-dim)" }}>
                    <td style={{ padding: "7px 10px", color: "var(--ink-0)", fontWeight: 600 }}>{p.pitch_name}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: getScoreColor(p.score), fontWeight: 700 }}>{p.score}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{p.pitch_count}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{p.avg_velo}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{p.avg_spin}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{p.mean_pred_run_exp.toFixed(4)}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{p.actual_run_exp.toFixed(4)}</td>
                    <td style={{ padding: "7px 10px", textAlign: "center" }}>
                      {p.sufficient_sample
                        ? <span className="t-mono" style={{ color: C_POS, fontSize: 10 }}>OK</span>
                        : <span className="t-mono" style={{ color: C_AMBER, fontSize: 10 }}>Low</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", marginTop: 8, paddingLeft: 10 }}>
              RE = Run Expectancy（得点期待値の変化量）。負値ほど投手有利。Pred RE はモデル予測値、Actual RE は実際の結果。Sample は最低投球数を満たしているかの判定。
            </p>
          </div>
        </div>
      )}
    </div>
  );

  // ==========================================================
  // CompareView
  // ==========================================================
  const CompareView = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
        <div>
          <div className="h-label" style={{ fontSize: 9, marginBottom: 4 }}>投手名</div>
          <SearchInput
            value={compareSearchQuery}
            onChange={(e) => { setCompareSearchQuery(e.target.value); setComparePitcherId(''); setCompareShowSuggestions(true); }}
            placeholder="e.g. Yamamoto"
            inputRef={compareSearchRef}
            suggestions={compareSuggestions}
            showSuggestions={compareShowSuggestions}
            onSelect={(s) => { setComparePitcherId(String(s.pitcher_id)); setCompareSearchQuery(s.player_name); setCompareShowSuggestions(false); }}
          />
        </div>

        <select value={compareSeason} onChange={(e) => setCompareSeason(Number(e.target.value))} style={selectStyle}>
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => <option key={y} value={y}>{y}</option>)}
        </select>

        <button onClick={fetchCompare} disabled={!comparePitcherId || isLoading} style={actionBtn(!comparePitcherId || isLoading)}>
          <Icon name="search" size={12}/>比較
        </button>
      </div>

      {compareResult && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
            <span className="h-display" style={{ fontSize: 16 }}>{compareResult.player_name}</span>
            <span style={{ ...getProfileStyle(compareResult.profile), padding: "3px 10px", fontSize: 11, fontFamily: "var(--ff-mono)" }}>
              {compareResult.profile_desc}
            </span>
            <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
              Avg Gap: <span style={{ color: compareResult.avg_gap > 0 ? C_INFO : compareResult.avg_gap < 0 ? C_PURP : "var(--ink-1)", fontWeight: 600 }}>
                {compareResult.avg_gap > 0 ? '+' : ''}{compareResult.avg_gap}
              </span>
            </span>
          </div>

          <div style={chartContainer}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={compareResult.comparison} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={C_GRID}/>
                <XAxis dataKey="pitch_name" stroke={C_AXIS} tick={{ fontSize: 11, fill: C_TICK }}/>
                <YAxis stroke={C_AXIS} tick={{ fontSize: 11, fill: C_TICK }} domain={[60, 160]}/>
                <Tooltip content={<CompareChartTooltip/>}/>
                <Legend wrapperStyle={{ fontSize: 11, color: C_TICK }}/>
                <ReferenceLine y={100} stroke={C_AXIS} strokeDasharray="4 4"/>
                <Bar dataKey="stuff_plus" name="Stuff+" fill={C_INFO} radius={[2, 2, 0, 0]}/>
                <Bar dataKey="pitching_plus" name="Pitching+" fill={C_PURP} radius={[2, 2, 0, 0]}/>
                <Bar dataKey="pitching_plus_plus" name="Pitching++" fill={C_POS} radius={[2, 2, 0, 0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={tableThStyle("left")}>Pitch</th>
                  <th style={{ ...tableThStyle("right"), color: C_INFO }}>Stuff+</th>
                  <th style={{ ...tableThStyle("right"), color: C_PURP }}>Pitching+</th>
                  <th style={{ ...tableThStyle("right"), color: C_POS }}>Pitching++</th>
                  <th style={tableThStyle("right")}>Gap</th>
                  <th style={tableThStyle("right")}>Count</th>
                  <th style={tableThStyle("right")}>Velo (mph)</th>
                </tr>
              </thead>
              <tbody>
                {compareResult.comparison.map((c, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--rule-dim)" }}>
                    <td style={{ padding: "7px 10px", color: "var(--ink-0)", fontWeight: 600 }}>{c.pitch_name}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right" }}>
                      {c.stuff_plus != null ? <span style={{ color: getScoreColor(c.stuff_plus), fontWeight: 700 }}>{c.stuff_plus}</span> : <span style={{ color: "var(--ink-4)" }}>-</span>}
                    </td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right" }}>
                      {c.pitching_plus != null ? <span style={{ color: getScoreColor(c.pitching_plus), fontWeight: 700 }}>{c.pitching_plus}</span> : <span style={{ color: "var(--ink-4)" }}>-</span>}
                    </td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right" }}>
                      {c.pitching_plus_plus != null ? <span style={{ color: getScoreColor(c.pitching_plus_plus), fontWeight: 700 }}>{c.pitching_plus_plus}</span> : <span style={{ color: "var(--ink-4)" }}>-</span>}
                    </td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right" }}>
                      {c.gap != null ? <span style={{ color: c.gap > 0 ? C_INFO : c.gap < 0 ? C_PURP : "var(--ink-2)", fontWeight: 600 }}>{c.gap > 0 ? '+' : ''}{c.gap}</span> : <span style={{ color: "var(--ink-4)" }}>-</span>}
                    </td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{c.pitch_count}</td>
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{c.avg_velo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  // ==========================================================
  // TrendView
  // ==========================================================
  const TrendView = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
        <div>
          <div className="h-label" style={{ fontSize: 9, marginBottom: 4 }}>投手名</div>
          <SearchInput
            value={trendSearchQuery}
            onChange={(e) => { setTrendSearchQuery(e.target.value); setTrendPitcherId(''); setTrendShowSuggestions(true); }}
            placeholder="e.g. Ohtani"
            inputRef={trendSearchRef}
            suggestions={trendSuggestions}
            showSuggestions={trendShowSuggestions}
            onSelect={(s) => { setTrendPitcherId(String(s.pitcher_id)); setTrendSearchQuery(s.player_name); setTrendShowSuggestions(false); }}
          />
        </div>

        <div style={{ display: "flex", gap: 2 }}>
          {Object.keys(MODEL_CFG).map(m => (
            <button key={m} onClick={() => setTrendModelType(m)} style={modelBtn(trendModelType === m, m)}>
              {MODEL_CFG[m].label}
            </button>
          ))}
        </div>

        <select value={trendSeason} onChange={(e) => setTrendSeason(Number(e.target.value))} style={selectStyle}>
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => <option key={y} value={y}>{y}</option>)}
        </select>

        <button onClick={fetchTrend} disabled={!trendPitcherId || isLoading} style={actionBtn(!trendPitcherId || isLoading)}>
          <Icon name="chart" size={12}/>推移表示
        </button>
      </div>

      {trendResult && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="h-display" style={{ fontSize: 16 }}>{trendResult.player_name}</span>
            <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
              {MODEL_CFG[trendModelType]?.label} / {trendResult.season} 月別推移
            </span>
          </div>

          <div style={chartContainer}>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={trendResult.monthly} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={C_GRID}/>
                <XAxis dataKey="month" stroke={C_AXIS} tick={{ fontSize: 11, fill: C_TICK }} tickFormatter={(m) => MONTH_LABELS[m] || m}/>
                <YAxis stroke={C_AXIS} tick={{ fontSize: 11, fill: C_TICK }} domain={[60, 160]}/>
                <Tooltip content={<TrendChartTooltip/>}/>
                <Legend wrapperStyle={{ fontSize: 11, color: C_TICK }}/>
                <ReferenceLine y={100} stroke={C_AXIS} strokeDasharray="4 4" label={{ value: 'Avg (100)', fill: C_TICK, fontSize: 10 }}/>
                {trendResult.pitch_names.map((pn, i) => (
                  <Line key={pn} type="monotone" dataKey={pn} name={pn}
                    stroke={PITCH_COLORS[i % PITCH_COLORS.length]}
                    strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls/>
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={tableThStyle("left")}>Month</th>
                  {trendResult.pitch_names.map((pn, i) => (
                    <th key={pn} style={{ ...tableThStyle("right"), color: PITCH_COLORS[i % PITCH_COLORS.length] }}>{pn}</th>
                  ))}
                  <th style={tableThStyle("right")}>Total</th>
                </tr>
              </thead>
              <tbody>
                {trendResult.monthly.map((m) => (
                  <tr key={m.month} style={{ borderBottom: "1px solid var(--rule-dim)" }}>
                    <td style={{ padding: "7px 10px", color: "var(--ink-0)", fontWeight: 600 }}>{MONTH_LABELS[m.month] || m.month}</td>
                    {trendResult.pitch_names.map((pn) => (
                      <td key={pn} className="t-mono" style={{ padding: "7px 10px", textAlign: "right" }}>
                        {m[pn] != null
                          ? <span style={{ color: getScoreColor(m[pn]), fontWeight: 700 }}>{m[pn]}</span>
                          : <span style={{ color: "var(--ink-4)" }}>-</span>
                        }
                        {m[`${pn}_count`] != null && (
                          <span style={{ color: "var(--ink-4)", fontSize: 10, marginLeft: 3 }}>({m[`${pn}_count`]})</span>
                        )}
                      </td>
                    ))}
                    <td className="t-mono" style={{ padding: "7px 10px", textAlign: "right", color: "var(--ink-2)" }}>{m.total_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", marginTop: 8, paddingLeft: 10 }}>
              括弧内はその月の投球数。サンプルが少ない月はスコアの信頼度が低い点に注意。
            </p>
          </div>
        </div>
      )}
    </div>
  );

  // ==========================================================
  // Main render
  // ==========================================================
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div className="rule-b" style={{ display: "flex", alignItems: "center", gap: 12, paddingBottom: 12 }}>
        <Icon name="target" size={20} style={{ color: "var(--amber)", flexShrink: 0 }}/>
        <div>
          <span className="h-display" style={{ fontSize: 17, display: "block" }}>Stuff+ / Pitching+ / Pitching++</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>XGBoostベースの球質・投球評価モデル</span>
        </div>
      </div>

      {/* Model definitions */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 8 }}>
        {[
          { key: 'stuff_plus',         color: C_INFO, label: "Stuff+",     desc: "球速・回転・変化量・リリースなど物理的な球質のみで評価。100 = MLB平均、15pt = 1SD。" },
          { key: 'pitching_plus',      color: C_PURP, label: "Pitching+",  desc: "Stuff+ に投球コースを追加。「良い球を、良い場所に投げられるか」を評価。コーナーワークに優れた投手が高スコア。" },
          { key: 'pitching_plus_plus', color: C_POS,  label: "Pitching++", desc: "Pitching+ に前球との球速差・リリース差・カウント状況を追加。「配球の組み立てで打者を翻弄できるか」を評価。" },
        ].map(({ key, color, label, desc }) => (
          <div key={key} style={{ border: `1px solid ${color}30`, background: `${color}0a`, padding: "10px 14px" }}>
            <span style={{ color, fontWeight: 600, fontSize: 12, fontFamily: "var(--ff-mono)" }}>{label}</span>
            <p style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 4, lineHeight: 1.5 }}>{desc}</p>
          </div>
        ))}
      </div>

      {/* Sub-view tabs */}
      <div style={{ display: "flex", gap: 4 }}>
        {[
          { key: 'rankings', label: 'ランキング' },
          { key: 'detail',   label: '投手詳細' },
          { key: 'trend',    label: '月別推移' },
          { key: 'compare',  label: 'モデル比較' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => { setView(tab.key); setError(null); }}
            style={tabBtn(view === tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 0", gap: 8 }}>
          <span className="think-dot"/>
          <span className="think-dot" style={{ animationDelay: ".2s" }}/>
          <span className="think-dot" style={{ animationDelay: ".4s" }}/>
          <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>読み込み中...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ color: "var(--neg)", fontSize: 12, border: "1px solid var(--neg-dim)", background: "oklch(0.26 0.10 28 / 0.12)", padding: "10px 14px" }}>
          {error}
        </div>
      )}

      {/* Content */}
      {!isLoading && !error && (
        <>
          {view === 'rankings' && RankingsView()}
          {view === 'detail'   && DetailView()}
          {view === 'trend'    && TrendView()}
          {view === 'compare'  && CompareView()}
        </>
      )}
    </div>
  );
};

export default StuffPlus;
