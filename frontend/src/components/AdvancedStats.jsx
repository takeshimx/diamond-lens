import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter,
  LineChart, Line, Legend, Cell,
} from 'recharts';
import { BarChart3, User, GitCompare, TrendingUp, ChevronRight, ChevronLeft, Search, RefreshCw } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

// ============================================================
// Metric Definitions — 追加・削除はここだけ
// ============================================================
const PITCHING_METRICS = [
  { id: 'P1', name: 'Pitch Tunnel Score', nameJp: 'ピッチトンネルスコア', question: '最も球の見分けがつきにくい投手は？', apiReady: false },
  { id: 'P2', name: 'Pressure Dominance', nameJp: 'プレッシャー支配力', question: '最もプレッシャーに強い投手は？', apiReady: false },
  { id: 'P3', name: 'Stamina Score', nameJp: 'スタミナスコア', question: '最もスタミナのある投手は？', apiReady: false },
  { id: 'P4', name: 'Two-Strike Finisher', nameJp: '2ストライク仕留め力', question: '最も追い込んでから仕留める投手は？', apiReady: false },
  { id: 'P5', name: 'Command Precision', nameJp: 'コマンド精度', question: '最もコントロールの良い投手は？', apiReady: false },
  { id: 'P6', name: 'Arsenal Effectiveness', nameJp: '球種構成効果', question: '最も多彩で効果的な球種構成は？', apiReady: true },
  { id: 'P7', name: 'First-Pitch Strike', nameJp: '初球ストライク支配力', question: '初球の支配力が最も高い投手は？', apiReady: false },
];

const BATTING_METRICS = [
  { id: 'B1', name: 'Swing Efficiency', nameJp: 'スイング効率', question: '最も効率的なスイングをする打者は？', apiReady: false },
  { id: 'B2', name: 'Plate Discipline', nameJp: '選球眼スコア', question: '最も選球眼の良い打者は？', apiReady: false },
  { id: 'B3', name: 'Clutch Hitting', nameJp: 'クラッチ打撃', question: '最もチャンスに強い打者は？', apiReady: false },
  { id: 'B4', name: 'Contact Consistency', nameJp: 'コンタクト一貫性', question: '最もコンタクトの質が安定している打者は？', apiReady: false },
  { id: 'B5', name: 'Adjustment Ability', nameJp: '対応力', question: '同一投手への対応力が最も高い打者は？', apiReady: false },
  { id: 'B6', name: 'Spray Mastery', nameJp: '打球方向マスタリー', question: '最も広角に打ち分けられる打者は？', apiReady: false },
  { id: 'B7', name: 'Power Under Pressure', nameJp: 'プレッシャー下パワー', question: 'チャンスで最も長打力を発揮する打者は？', apiReady: false },
];

// ============================================================
// Dummy Data (API未接続の指標用)
// ============================================================
const DUMMY_PITCHERS = [
  { id: 1, name: 'Shohei Ohtani', team: 'LAD' },
  { id: 2, name: 'Gerrit Cole', team: 'NYY' },
  { id: 3, name: 'Corbin Burns', team: 'BAL' },
  { id: 4, name: 'Zack Wheeler', team: 'PHI' },
  { id: 5, name: 'Paul Skenes', team: 'PIT' },
  { id: 6, name: 'Chris Sale', team: 'ATL' },
  { id: 7, name: 'Spencer Strider', team: 'ATL' },
  { id: 8, name: 'Logan Webb', team: 'SF' },
  { id: 9, name: 'Tarik Skubal', team: 'DET' },
  { id: 10, name: 'Dylan Cease', team: 'SD' },
];

const DUMMY_BATTERS = [
  { id: 101, name: 'Shohei Ohtani', team: 'LAD' },
  { id: 102, name: 'Aaron Judge', team: 'NYY' },
  { id: 103, name: 'Mookie Betts', team: 'LAD' },
  { id: 104, name: 'Ronald Acuna Jr.', team: 'ATL' },
  { id: 105, name: 'Juan Soto', team: 'NYM' },
  { id: 106, name: 'Freddie Freeman', team: 'LAD' },
  { id: 107, name: 'Corey Seager', team: 'TEX' },
  { id: 108, name: 'Trea Turner', team: 'PHI' },
  { id: 109, name: 'Marcus Semien', team: 'TEX' },
  { id: 110, name: 'Bobby Witt Jr.', team: 'KC' },
];

const seededRandom = (seed) => {
  let s = seed;
  return () => { s = (s * 16807 + 0) % 2147483647; return (s - 1) / 2147483646; };
};

const generateDummyRankings = (metrics, players) => {
  const result = {};
  metrics.forEach((metric) => {
    if (metric.apiReady) return; // API接続済みはスキップ
    const rng = seededRandom(metric.id.charCodeAt(0) * 100 + metric.id.charCodeAt(1));
    const ranked = players
      .map((p) => ({ ...p, score: Math.round((60 + rng() * 35) * 10) / 10 }))
      .sort((a, b) => b.score - a.score);
    result[metric.id] = ranked;
  });
  return result;
};

const generateDummyProfile = (metrics, playerId) => {
  const rng = seededRandom(playerId * 7);
  return metrics.map((m) => ({
    metricId: m.id, metricName: m.name, metricNameJp: m.nameJp,
    score: Math.round((65 + rng() * 30) * 10) / 10,
    rank: Math.floor(rng() * 20) + 1, leagueAvg: 75,
  }));
};

const generateDummyTrends = (metrics, playerId) => {
  const rng = seededRandom(playerId * 13);
  return [2021, 2022, 2023, 2024].map((year) => {
    const row = { season: year };
    metrics.forEach((m) => { row[m.id] = Math.round((65 + rng() * 30) * 10) / 10; });
    return row;
  });
};

// ============================================================
// Color / Chart Helpers
// ============================================================
const PITCH_TYPE_COLORS = {
  '4-Seam Fastball': '#ef4444', 'Sinker': '#f97316', 'Cutter': '#eab308',
  'Slider': '#3b82f6', 'Sweeper': '#6366f1', 'Curveball': '#8b5cf6',
  'Changeup': '#22c55e', 'Split-Finger': '#14b8a6', 'Knuckle Curve': '#a855f7',
  'Slurve': '#ec4899', 'Screwball': '#f43f5e', 'Knuckleball': '#64748b',
};
const getPitchColor = (name) => PITCH_TYPE_COLORS[name] || '#6b7280';

const getScoreColor = (score) => {
  if (score >= 90) return 'text-green-400';
  if (score >= 80) return 'text-emerald-400';
  if (score >= 70) return 'text-yellow-400';
  return 'text-orange-400';
};
const getBarFill = (score) => {
  if (score >= 90) return '#22c55e';
  if (score >= 80) return '#10b981';
  if (score >= 70) return '#eab308';
  return '#f97316';
};

const RADAR_COLORS = ['#3b82f6', '#ef4444', '#6b7280'];
const LINE_COLORS = ['#3b82f6', '#8b5cf6', '#22c55e', '#ef4444', '#eab308', '#ec4899', '#06b6d4'];

// ============================================================
// Main Component
// ============================================================
const AdvancedStats = () => {
  const { getIdToken } = useAuth();

  // --- Backend URL ---
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

  // --- Shared state ---
  const [view, setView] = useState('rankings');
  const [category, setCategory] = useState('pitching');
  const [season, setSeason] = useState(2025);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- Rankings state ---
  const [expandedMetric, setExpandedMetric] = useState(null);
  const [arsenalRankings, setArsenalRankings] = useState(null); // P6 live data (includes pitch_mix)

  // --- Profile state ---
  const [profilePlayerId, setProfilePlayerId] = useState(null);
  const [profileSearch, setProfileSearch] = useState('');

  // --- Compare state ---
  const [comparePlayerA, setComparePlayerA] = useState(null);
  const [comparePlayerB, setComparePlayerB] = useState(null);
  const [compareSearchA, setCompareSearchA] = useState('');
  const [compareSearchB, setCompareSearchB] = useState('');

  // --- Trends state ---
  const [trendsPlayerId, setTrendsPlayerId] = useState(null);
  const [trendsSearch, setTrendsSearch] = useState('');
  const [trendsSelectedMetrics, setTrendsSelectedMetrics] = useState([]);

  // --- Derived ---
  const metrics = category === 'pitching' ? PITCHING_METRICS : BATTING_METRICS;
  const players = category === 'pitching' ? DUMMY_PITCHERS : DUMMY_BATTERS;
  const dummyRankingsData = useMemo(() => generateDummyRankings(metrics, players), [category, season]);

  const profileData = useMemo(
    () => (profilePlayerId ? generateDummyProfile(metrics, profilePlayerId) : null),
    [profilePlayerId, category]
  );
  const compareDataA = useMemo(
    () => (comparePlayerA ? generateDummyProfile(metrics, comparePlayerA) : null),
    [comparePlayerA, category]
  );
  const compareDataB = useMemo(
    () => (comparePlayerB ? generateDummyProfile(metrics, comparePlayerB) : null),
    [comparePlayerB, category]
  );
  const trendsData = useMemo(
    () => (trendsPlayerId ? generateDummyTrends(metrics, trendsPlayerId) : null),
    [trendsPlayerId, category]
  );

  // --- Helpers ---
  const getPlayer = (id) => players.find((p) => p.id === id);
  const filteredPlayers = (query) => {
    if (!query || query.length < 1) return [];
    return players.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()));
  };

  // ============================================================
  // API Calls — P6 Arsenal
  // ============================================================
  const fetchArsenalRankings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        season, min_pitches: 100, limit: 40, offset: 0,
      });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/pitching/arsenal/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setArsenalRankings(data);
    } catch (e) {
      console.error('Arsenal rankings fetch failed:', e);
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch P6 on mount and season change
  useEffect(() => {
    if (category === 'pitching') {
      fetchArsenalRankings();
    }
  }, [season, category]);

  // Build unified rankings data (mix real + dummy)
  const getRankingsForMetric = (metricId) => {
    if (metricId === 'P6' && arsenalRankings?.rankings) {
      return arsenalRankings.rankings.map((r) => ({
        id: r.pitcher_id,
        name: r.player_name,
        team: r.team || '',
        score: r.synthetic_score,
        diversity_score: r.diversity_score,
        effectiveness_score: r.effectiveness_score,
        pitch_mix: r.pitch_mix || [],
      }));
    }
    return dummyRankingsData[metricId] || [];
  };

  // ============================================================
  // Sub-components
  // ============================================================
  const ChartTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
        <p className="text-white font-medium text-sm">{d.name || d.metricName || d.season || d.player_name}</p>
        {payload.map((p, i) => (
          <p key={i} className="text-gray-300 text-xs">
            {p.name}: {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
          </p>
        ))}
      </div>
    );
  };

  const PlayerSearchDropdown = ({ query, setQuery, onSelect, placeholder }) => {
    const results = filteredPlayers(query);
    return (
      <div className="relative">
        <div className="flex items-center">
          <Search className="absolute left-2.5 w-3.5 h-3.5 text-gray-500" />
          <input
            type="text" value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder || 'Search player...'}
            className="bg-gray-700 text-white border border-gray-600 rounded-lg pl-8 pr-3 py-1.5 text-sm w-56"
          />
        </div>
        {results.length > 0 && query.length >= 1 && (
          <div className="absolute z-50 mt-1 w-72 bg-gray-800 border border-gray-600 rounded-lg shadow-xl max-h-48 overflow-y-auto">
            {results.map((p) => (
              <button key={p.id} onClick={() => { onSelect(p.id); setQuery(p.name); }}
                className="w-full text-left px-3 py-2 hover:bg-gray-700 transition-colors flex items-center justify-between">
                <span className="text-white text-sm font-medium">{p.name}</span>
                <span className="text-gray-500 text-xs">{p.team}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ============================================================
  // P6 Arsenal Expanded View — Metric Detail
  // ============================================================
  const ArsenalDetailView = () => {
    const data = getRankingsForMetric('P6');
    const metric = PITCHING_METRICS.find((m) => m.id === 'P6');

    // Scatter data — use scatter_all (all qualifying pitchers) from API
    const scatterData = arsenalRankings?.scatter_all || data.map((r) => ({
      player_name: r.name,
      diversity_score: r.diversity_score,
      effectiveness_score: r.effectiveness_score,
      synthetic_score: r.score,
    }));
    const topN = new Set(data.slice(0, 5).map((r) => r.name));

    return (
      <div className="space-y-4">
        <button onClick={() => setExpandedMetric(null)}
          className="flex items-center gap-1 text-gray-400 hover:text-white text-sm transition-colors">
          <ChevronLeft className="w-4 h-4" /> Back to Overview
        </button>

        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white">{metric.id}. {metric.name} ({metric.nameJp})</h3>
            <p className="text-sm text-gray-400 mt-0.5">
              Logic: 球種使用率のシャノンエントロピー（多様性）と各球種の得点抑止力（delta_pitcher_run_exp）の複合
            </p>
          </div>
          <button onClick={fetchArsenalRankings}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white text-xs transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Left: Rankings Table */}
          <div className="xl:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            {/* Pitch type legend — above column headers */}
            <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1">
              {Object.entries(PITCH_TYPE_COLORS).map(([name, color]) => (
                <div key={name} className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
                  <span className="text-gray-500 text-[10px]">{name}</span>
                </div>
              ))}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left text-gray-400 py-2 px-2 w-8">#</th>
                    <th className="text-left text-gray-400 py-2 px-2">Pitcher</th>
                    <th className="text-left text-gray-400 py-2 px-2">Team</th>
                    <th className="text-right text-gray-400 py-2 px-2">Diversity (H)</th>
                    <th className="text-right text-gray-400 py-2 px-2">Effectiveness</th>
                    <th className="text-right text-gray-400 py-2 px-2">Synthetic</th>
                    <th className="text-left text-gray-400 py-2 px-2 min-w-[200px]">Pitch Type Mix</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((r, i) => {
                    const mix = r.pitch_mix;
                    return (
                      <tr key={r.id} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                        <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                        <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                        <td className="py-2 px-2 text-gray-400">{r.team}</td>
                        <td className="py-2 px-2 text-right text-cyan-400 font-mono">{r.diversity_score?.toFixed(4)}</td>
                        <td className="py-2 px-2 text-right text-amber-400 font-mono">{r.effectiveness_score?.toFixed(4)}</td>
                        <td className={`py-2 px-2 text-right font-bold ${getScoreColor(r.score * 10)}`}>{r.score?.toFixed(4)}</td>
                        <td className="py-2 px-2">
                          {mix && mix.length > 0 ? (
                            <div className="relative">
                              {/* Visual bar (overflow-hidden for rounded corners) */}
                              <div className="flex h-3 rounded-full overflow-hidden">
                                {mix.map((p) => (
                                  <div key={p.pitch_name}
                                    style={{ width: `${p.usage_pct * 100}%`, backgroundColor: getPitchColor(p.pitch_name) }} />
                                ))}
                              </div>
                              {/* Hover overlay (no overflow-hidden — tooltip escapes) */}
                              <div className="absolute inset-0 flex h-3">
                                {mix.map((p) => (
                                  <div key={p.pitch_name} className="relative group/pitch h-full"
                                    style={{ width: `${p.usage_pct * 100}%` }}>
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1 bg-gray-900 border border-gray-600 rounded text-[10px] text-white whitespace-nowrap opacity-0 group-hover/pitch:opacity-100 pointer-events-none transition-opacity z-50 shadow-lg">
                                      <span style={{ color: getPitchColor(p.pitch_name) }}>{p.pitch_name}</span>: {(p.usage_pct * 100).toFixed(1)}%
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-600 text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

          </div>

          {/* Right: Scatter + Info */}
          <div className="space-y-4">
            {/* Diversity vs Effectiveness Scatter — ALL qualifying pitchers */}
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-300">Diversity vs Effectiveness</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} pitchers</span>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="diversity_score" name="Diversity (H)"
                    stroke="#9ca3af" tick={{ fontSize: 10 }} domain={[0, 2]}
                    label={{ value: 'Diversity (H)', position: 'insideBottom', offset: -3, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="effectiveness_score" name="Effectiveness"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Effectiveness', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData} fill="#8b5cf6" fillOpacity={0.6}>
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#8b5cf6'}
                        fillOpacity={topN.has(entry.player_name) ? 0.9 : 0.5}
                        r={topN.has(entry.player_name) ? 5 : 3} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-3 mt-1.5">
                <div className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span className="text-gray-500 text-[10px]">Top 5</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded-full bg-purple-500 opacity-50" />
                  <span className="text-gray-500 text-[10px]">Others</span>
                </div>
              </div>
            </div>

            {/* Calculation Details */}
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• Diversity: Shannon Entropy H = -Σ p(i) × ln(p(i))</li>
                <li className="ml-3">• Effectiveness: Σ delta_pitcher_run_exp</li>
                <li className="ml-3">• Synthetic: H × Effectiveness</li>
                <li className="mt-2">入力カラム</li>
                <li className="ml-3 font-mono text-gray-500">pitch_type, delta_pitcher_run_exp, woba_value</li>
                <li className="mt-2">フィルタ: 最低 100 球以上, effectiveness &gt; 0</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // RANKINGS VIEW
  // ============================================================
  const RankingsView = () => {
    // P6 expanded → dedicated detail view
    if (expandedMetric === 'P6' && category === 'pitching') {
      return <ArsenalDetailView />;
    }

    // Other metric expanded → generic table
    if (expandedMetric) {
      const metric = metrics.find((m) => m.id === expandedMetric);
      const data = getRankingsForMetric(expandedMetric);
      return (
        <div className="space-y-4">
          <button onClick={() => setExpandedMetric(null)}
            className="flex items-center gap-1 text-gray-400 hover:text-white text-sm transition-colors">
            <ChevronLeft className="w-4 h-4" /> Back to Overview
          </button>
          <div>
            <h3 className="text-lg font-bold text-white">{metric.id}. {metric.name}</h3>
            <p className="text-sm text-gray-400">{metric.question}</p>
            {!metric.apiReady && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-[10px] rounded">
                Dummy Data — API未接続
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-3 w-12">#</th>
                  <th className="text-left text-gray-400 py-2 px-3">Player</th>
                  <th className="text-left text-gray-400 py-2 px-3">Team</th>
                  <th className="text-right text-gray-400 py-2 px-3">Score</th>
                  <th className="text-left text-gray-400 py-2 px-3 w-48"></th>
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={r.id} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2.5 px-3 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2.5 px-3 text-white font-medium">{r.name}</td>
                    <td className="py-2.5 px-3 text-gray-400">{r.team}</td>
                    <td className={`py-2.5 px-3 text-right font-bold ${getScoreColor(r.score)}`}>{r.score}</td>
                    <td className="py-2.5 px-3">
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div className="h-2 rounded-full transition-all"
                          style={{ width: `${Math.min((r.score / 100) * 100, 100)}%`, backgroundColor: getBarFill(r.score) }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    // Overview — card grid
    return (
      <div className="space-y-4">
        {/* Loading / Error */}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500" />
            P6 Arsenal データ読み込み中...
          </div>
        )}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-2 text-sm">
            P6 API Error: {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {metrics.map((metric) => {
            const data = getRankingsForMetric(metric.id).slice(0, 5);
            const isLive = metric.apiReady && metric.id === 'P6' && arsenalRankings;
            return (
              <div key={metric.id} className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-white font-semibold text-sm">{metric.id}: {metric.name}</h4>
                      {isLive ? (
                        <span className="px-1.5 py-0.5 bg-green-500/10 border border-green-500/20 text-green-400 text-[9px] rounded">LIVE</span>
                      ) : !metric.apiReady ? (
                        <span className="px-1.5 py-0.5 bg-gray-500/10 border border-gray-500/20 text-gray-500 text-[9px] rounded">DUMMY</span>
                      ) : null}
                    </div>
                    <p className="text-gray-500 text-xs mt-0.5">{metric.question}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  {data.map((r, i) => (
                    <div key={r.id}
                      className="flex items-center gap-3 hover:bg-gray-700/30 rounded-lg px-2 py-1 cursor-pointer transition-colors"
                      onClick={() => {
                        if (metric.apiReady) {
                          setExpandedMetric(metric.id);
                        } else {
                          setProfilePlayerId(r.id);
                          setProfileSearch(r.name);
                          setView('profile');
                        }
                      }}>
                      <span className="text-gray-500 text-xs font-medium w-4">{i + 1}</span>
                      <span className="text-white text-sm font-medium flex-1 truncate">{r.name}</span>
                      <span className="text-gray-500 text-xs">{r.team}</span>
                      {metric.id === 'P6' ? (
                        <span className="text-sm font-bold w-16 text-right text-amber-400 font-mono">{r.score?.toFixed(3)}</span>
                      ) : (
                        <>
                          <span className={`text-sm font-bold w-12 text-right ${getScoreColor(r.score)}`}>{r.score}</span>
                          <div className="w-20 bg-gray-700 rounded-full h-1.5">
                            <div className="h-1.5 rounded-full"
                              style={{ width: `${Math.min((r.score / 100) * 100, 100)}%`, backgroundColor: getBarFill(r.score) }} />
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>

                <button onClick={() => setExpandedMetric(metric.id)}
                  className="mt-3 flex items-center gap-1 text-blue-400 hover:text-blue-300 text-xs font-medium transition-colors">
                  View Full Rankings <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // ============================================================
  // PROFILE VIEW (dummy for now)
  // ============================================================
  const ProfileView = () => {
    const player = getPlayer(profilePlayerId);
    const radarData = profileData
      ? profileData.map((d) => ({ metric: d.metricId, score: d.score, leagueAvg: d.leagueAvg, fullMark: 100 }))
      : [];
    const strengths = profileData ? [...profileData].sort((a, b) => a.rank - b.rank).slice(0, 2) : [];
    const weaknesses = profileData ? [...profileData].sort((a, b) => b.rank - a.rank).slice(0, 2) : [];

    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-400 mb-1">{category === 'pitching' ? '投手名' : '打者名'}</label>
            <PlayerSearchDropdown query={profileSearch} setQuery={setProfileSearch}
              onSelect={setProfilePlayerId} placeholder={category === 'pitching' ? 'e.g. Ohtani' : 'e.g. Judge'} />
          </div>
        </div>
        {!profileData && (
          <div className="text-center py-16 text-gray-500">
            <User className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">選手を検索してプロファイルを表示</p>
          </div>
        )}
        {profileData && player && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
                <h3 className="text-xl font-bold text-white">{player.name}</h3>
                <p className="text-gray-400 text-sm">{player.team}</p>
                <div className="mt-4 space-y-2">
                  {profileData.map((d) => (
                    <div key={d.metricId} className="flex items-center gap-2">
                      <span className="text-gray-400 text-xs w-6">{d.metricId}</span>
                      <span className="text-gray-300 text-xs flex-1 truncate">{d.metricNameJp}</span>
                      <span className={`text-sm font-bold w-12 text-right ${getScoreColor(d.score)}`}>{d.score}</span>
                      <span className="text-gray-500 text-xs w-8">#{d.rank}</span>
                      <div className="w-24 bg-gray-700 rounded-full h-1.5 relative">
                        <div className="h-1.5 rounded-full absolute top-0 left-0"
                          style={{ width: `${Math.min((d.score / 100) * 100, 100)}%`, backgroundColor: getBarFill(d.score) }} />
                        <div className="absolute top-[-2px] h-[calc(100%+4px)] w-[2px] bg-gray-400"
                          style={{ left: `${d.leagueAvg}%` }} title="League Avg" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Skill Radar</h4>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#374151" />
                    <PolarAngleAxis dataKey="metric" stroke="#9ca3af" tick={{ fontSize: 11 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#374151" tick={{ fontSize: 10, fill: '#6b7280' }} />
                    <Radar name={player.name} dataKey="score" stroke={RADAR_COLORS[0]} fill={RADAR_COLORS[0]} fillOpacity={0.25} strokeWidth={2} />
                    <Radar name="League Avg" dataKey="leagueAvg" stroke={RADAR_COLORS[2]} fill="none" strokeDasharray="4 4" strokeWidth={1} />
                    <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-4">
                <h4 className="text-green-400 font-semibold text-sm mb-2">Top Strengths</h4>
                {strengths.map((s) => (
                  <p key={s.metricId} className="text-gray-300 text-sm">
                    {s.metricId} {s.metricNameJp} — <span className="text-green-400 font-medium">#{s.rank}</span> ({s.score})
                  </p>
                ))}
              </div>
              <div className="bg-orange-500/5 border border-orange-500/20 rounded-xl p-4">
                <h4 className="text-orange-400 font-semibold text-sm mb-2">Areas to Watch</h4>
                {weaknesses.map((w) => (
                  <p key={w.metricId} className="text-gray-300 text-sm">
                    {w.metricId} {w.metricNameJp} — <span className="text-orange-400 font-medium">#{w.rank}</span> ({w.score})
                  </p>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  // ============================================================
  // COMPARE VIEW (dummy for now)
  // ============================================================
  const CompareView = () => {
    const playerA = getPlayer(comparePlayerA);
    const playerB = getPlayer(comparePlayerB);
    const radarData = compareDataA && compareDataB
      ? compareDataA.map((a, i) => ({ metric: a.metricId, playerA: a.score, playerB: compareDataB[i].score, fullMark: 100 }))
      : [];

    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Player A</label>
            <PlayerSearchDropdown query={compareSearchA} setQuery={setCompareSearchA} onSelect={setComparePlayerA} placeholder="Player A" />
          </div>
          <span className="text-gray-500 font-bold pb-1">vs</span>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Player B</label>
            <PlayerSearchDropdown query={compareSearchB} setQuery={setCompareSearchB} onSelect={setComparePlayerB} placeholder="Player B" />
          </div>
        </div>
        {(!compareDataA || !compareDataB) && (
          <div className="text-center py-16 text-gray-500">
            <GitCompare className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">2選手を選択して比較</p>
          </div>
        )}
        {compareDataA && compareDataB && playerA && playerB && (
          <>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Radar Comparison</h4>
              <ResponsiveContainer width="100%" height={350}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis dataKey="metric" stroke="#9ca3af" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#374151" tick={{ fontSize: 10, fill: '#6b7280' }} />
                  <Radar name={playerA.name} dataKey="playerA" stroke={RADAR_COLORS[0]} fill={RADAR_COLORS[0]} fillOpacity={0.2} strokeWidth={2} />
                  <Radar name={playerB.name} dataKey="playerB" stroke={RADAR_COLORS[1]} fill={RADAR_COLORS[1]} fillOpacity={0.2} strokeWidth={2} />
                  <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Metric Comparison</h4>
              <div className="space-y-2">
                {compareDataA.map((a, i) => {
                  const b = compareDataB[i];
                  const diff = a.score - b.score;
                  return (
                    <div key={a.metricId} className="flex items-center gap-2">
                      <span className={`text-xs font-bold w-12 text-right ${diff > 0 ? 'text-blue-400' : 'text-gray-400'}`}>{a.score}</span>
                      <div className="flex-1 flex items-center gap-1">
                        <div className="flex-1 flex justify-end">
                          <div className="h-3 rounded-l-full" style={{ width: `${a.score}%`, backgroundColor: RADAR_COLORS[0], opacity: 0.7 }} />
                        </div>
                        <span className="text-gray-400 text-xs font-medium w-8 text-center">{a.metricId}</span>
                        <div className="flex-1">
                          <div className="h-3 rounded-r-full" style={{ width: `${b.score}%`, backgroundColor: RADAR_COLORS[1], opacity: 0.7 }} />
                        </div>
                      </div>
                      <span className={`text-xs font-bold w-12 ${diff < 0 ? 'text-red-400' : 'text-gray-400'}`}>{b.score}</span>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-3 text-xs text-gray-500">
                <span className="text-blue-400">{playerA.name}</span>
                <span className="text-red-400">{playerB.name}</span>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Summary</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <p className="text-blue-400 text-xs font-semibold mb-1">{playerA.name} が優位</p>
                  {compareDataA.map((a, i) => ({ ...a, diff: a.score - compareDataB[i].score }))
                    .filter((x) => x.diff > 0).sort((a, b) => b.diff - a.diff).slice(0, 3)
                    .map((x) => (
                      <p key={x.metricId} className="text-gray-400 text-xs">{x.metricId} {x.metricNameJp} (+{x.diff.toFixed(1)})</p>
                    ))}
                </div>
                <div>
                  <p className="text-red-400 text-xs font-semibold mb-1">{playerB.name} が優位</p>
                  {compareDataA.map((a, i) => ({ ...a, diff: compareDataB[i].score - a.score }))
                    .filter((x) => x.diff > 0).sort((a, b) => b.diff - a.diff).slice(0, 3)
                    .map((x) => (
                      <p key={x.metricId} className="text-gray-400 text-xs">{x.metricId} {x.metricNameJp} (+{x.diff.toFixed(1)})</p>
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
  // TRENDS VIEW (dummy for now)
  // ============================================================
  const TrendsView = () => {
    const player = getPlayer(trendsPlayerId);
    const toggleMetric = (metricId) => {
      setTrendsSelectedMetrics((prev) =>
        prev.includes(metricId) ? prev.filter((m) => m !== metricId)
          : prev.length < 5 ? [...prev, metricId] : prev
      );
    };
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-400 mb-1">{category === 'pitching' ? '投手名' : '打者名'}</label>
            <PlayerSearchDropdown query={trendsSearch} setQuery={setTrendsSearch}
              onSelect={(id) => {
                setTrendsPlayerId(id);
                if (trendsSelectedMetrics.length === 0) setTrendsSelectedMetrics(metrics.slice(0, 3).map((m) => m.id));
              }} placeholder="Search player..." />
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {metrics.map((m, i) => (
            <button key={m.id} onClick={() => toggleMetric(m.id)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors border ${
                trendsSelectedMetrics.includes(m.id) ? 'border-blue-500/50 text-white' : 'border-gray-600 text-gray-500 hover:text-gray-300'
              }`}
              style={trendsSelectedMetrics.includes(m.id) ? { backgroundColor: LINE_COLORS[i % LINE_COLORS.length] + '20' } : {}}>
              {m.id}
            </button>
          ))}
          <span className="text-gray-600 text-xs self-center ml-1">(max 5)</span>
        </div>
        {!trendsData && (
          <div className="text-center py-16 text-gray-500">
            <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">選手を検索してトレンドを表示</p>
          </div>
        )}
        {trendsData && player && trendsSelectedMetrics.length > 0 && (
          <>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">{player.name} — Season Trends</h4>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={trendsData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="season" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} domain={[50, 100]} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
                  {trendsSelectedMetrics.map((metricId, i) => {
                    const m = metrics.find((x) => x.id === metricId);
                    return (
                      <Line key={metricId} type="monotone" dataKey={metricId}
                        name={`${metricId}: ${m?.nameJp || m?.name}`}
                        stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={2}
                        dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Year-over-Year</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left text-gray-400 py-2 px-3">Metric</th>
                      {trendsData.map((row) => (
                        <th key={row.season} className="text-right text-gray-400 py-2 px-3">{row.season}</th>
                      ))}
                      <th className="text-right text-gray-400 py-2 px-3">YoY</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trendsSelectedMetrics.map((metricId) => {
                      const m = metrics.find((x) => x.id === metricId);
                      const latest = trendsData[trendsData.length - 1]?.[metricId];
                      const prev = trendsData[trendsData.length - 2]?.[metricId];
                      const yoy = latest != null && prev != null ? latest - prev : null;
                      return (
                        <tr key={metricId} className="border-b border-gray-700/50">
                          <td className="py-2 px-3 text-gray-300">{metricId} {m?.nameJp}</td>
                          {trendsData.map((row) => (
                            <td key={row.season} className="py-2 px-3 text-right text-gray-300">{row[metricId]?.toFixed(1)}</td>
                          ))}
                          <td className={`py-2 px-3 text-right font-medium ${yoy > 0 ? 'text-green-400' : yoy < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                            {yoy != null ? `${yoy > 0 ? '+' : ''}${yoy.toFixed(1)}` : '—'}
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
    { key: 'rankings', label: 'Rankings', icon: BarChart3 },
    { key: 'profile', label: 'Profile', icon: User },
    { key: 'compare', label: 'Compare', icon: GitCompare },
    { key: 'trends', label: 'Trends', icon: TrendingUp },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-purple-600/20 rounded-lg">
          <BarChart3 className="w-6 h-6 text-purple-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Advanced Stats Rankings</h2>
          <p className="text-sm text-gray-400">Statcastベースの高度投手・打者技術プロファイル</p>
        </div>
      </div>

      {/* Controls Row */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1 border border-gray-700 w-fit">
          {SUB_TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.key} onClick={() => setView(tab.key)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${
                  view === tab.key ? 'bg-gray-600 text-white' : 'text-gray-400 hover:text-gray-200'
                }`}>
                <Icon className="w-3.5 h-3.5" /> {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex rounded-lg overflow-hidden border border-gray-600">
          <button onClick={() => { setCategory('pitching'); setExpandedMetric(null); }}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              category === 'pitching' ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(59,130,246,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}>Pitching</button>
          <button onClick={() => { setCategory('batting'); setExpandedMetric(null); }}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              category === 'batting' ? 'bg-purple-600 text-white shadow-[0_0_12px_rgba(147,51,234,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}>Batting</button>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Season</label>
          <select value={season} onChange={(e) => setSeason(Number(e.target.value))}
            className="bg-gray-700 text-white border border-gray-600 rounded-lg px-3 py-1.5 text-sm">
            {[2025, 2024, 2023, 2022, 2021].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Content */}
      {view === 'rankings' && RankingsView()}
      {view === 'profile' && ProfileView()}
      {view === 'compare' && CompareView()}
      {view === 'trends' && TrendsView()}
    </div>
  );
};

export default AdvancedStats;
