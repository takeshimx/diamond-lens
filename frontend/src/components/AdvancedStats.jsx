import { useState, useMemo } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { BarChart3, User, GitCompare, TrendingUp, Search } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

import AdvancedStatsPitching from './AdvancedStatsPitching';
import AdvancedStatsBatting  from './AdvancedStatsBatting';
import {
  PITCHING_METRICS, BATTING_METRICS,
  DUMMY_PITCHERS, DUMMY_BATTERS,
  generateDummyProfile, generateDummyTrends,
  getScoreColor, getBarFill,
  RADAR_COLORS, LINE_COLORS,
  getBackendUrl,
} from './advancedStatsConstants';

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
  const [season, setSeason]     = useState(2025);

  // --- Profile state ---
  const [profilePlayerId, setProfilePlayerId] = useState(null);
  const [profileSearch, setProfileSearch]     = useState('');

  // --- Compare state ---
  const [comparePlayerA, setComparePlayerA]   = useState(null);
  const [comparePlayerB, setComparePlayerB]   = useState(null);
  const [compareSearchA, setCompareSearchA]   = useState('');
  const [compareSearchB, setCompareSearchB]   = useState('');

  // --- Trends state ---
  const [trendsPlayerId, setTrendsPlayerId]             = useState(null);
  const [trendsSearch, setTrendsSearch]                 = useState('');
  const [trendsSelectedMetrics, setTrendsSelectedMetrics] = useState([]);

  // --- Derived ---
  const metrics = category === 'pitching' ? PITCHING_METRICS : BATTING_METRICS;
  const players = category === 'pitching' ? DUMMY_PITCHERS  : DUMMY_BATTERS;
  const profileData  = useMemo(() => (profilePlayerId  ? generateDummyProfile(metrics, profilePlayerId)  : null), [profilePlayerId,  category]);
  const compareDataA = useMemo(() => (comparePlayerA   ? generateDummyProfile(metrics, comparePlayerA)   : null), [comparePlayerA,   category]);
  const compareDataB = useMemo(() => (comparePlayerB   ? generateDummyProfile(metrics, comparePlayerB)   : null), [comparePlayerB,   category]);
  const trendsData   = useMemo(() => (trendsPlayerId   ? generateDummyTrends(metrics, trendsPlayerId)    : null), [trendsPlayerId,   category]);

  const getPlayer = (id) => players.find((p) => p.id === id);
  const filteredPlayers = (query) => {
    if (!query || query.length < 1) return [];
    return players.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()));
  };

  // ============================================================
  // Shared sub-components
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
  // PROFILE VIEW (dummy for now)
  // ============================================================
  const ProfileView = () => {
    const player   = getPlayer(profilePlayerId);
    const radarData = profileData
      ? profileData.map((d) => ({ metric: d.metricId, score: d.score, leagueAvg: d.leagueAvg, fullMark: 100 }))
      : [];
    const strengths  = profileData ? [...profileData].sort((a, b) => a.rank - b.rank).slice(0, 2)  : [];
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
                  const b    = compareDataB[i];
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
                      const m      = metrics.find((x) => x.id === metricId);
                      const latest = trendsData[trendsData.length - 1]?.[metricId];
                      const prev   = trendsData[trendsData.length - 2]?.[metricId];
                      const yoy    = latest != null && prev != null ? latest - prev : null;
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
    { key: 'rankings', label: 'Rankings',  icon: BarChart3   },
    { key: 'profile',  label: 'Profile',   icon: User        },
    { key: 'compare',  label: 'Compare',   icon: GitCompare  },
    { key: 'trends',   label: 'Trends',    icon: TrendingUp  },
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
          <button onClick={() => setCategory('pitching')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              category === 'pitching'
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(59,130,246,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}>Pitching</button>
          <button onClick={() => setCategory('batting')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              category === 'batting'
                ? 'bg-purple-600 text-white shadow-[0_0_12px_rgba(147,51,234,0.5)]'
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
      {view === 'rankings' && category === 'pitching' && (
        <AdvancedStatsPitching season={season} getAuthHeaders={getAuthHeaders} BACKEND_URL={BACKEND_URL} />
      )}
      {view === 'rankings' && category === 'batting' && (
        <AdvancedStatsBatting season={season} getAuthHeaders={getAuthHeaders} BACKEND_URL={BACKEND_URL} />
      )}
      {view === 'profile'  && <ProfileView />}
      {view === 'compare'  && <CompareView />}
      {view === 'trends'   && <TrendsView />}
    </div>
  );
};

export default AdvancedStats;
