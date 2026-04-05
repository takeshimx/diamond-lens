import React, { useState, useEffect, useMemo } from 'react';
import {
  CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, XAxis, YAxis, Cell,
} from 'recharts';
import { ChevronLeft, RefreshCw } from 'lucide-react';
import {
  BATTING_METRICS, DUMMY_BATTERS, generateDummyRankings,
  getScoreColor, getBarFill,
} from './advancedStatsConstants';

// ============================================================
// AdvancedStatsBatting
// Props: season, getAuthHeaders, BACKEND_URL
// ============================================================
const AdvancedStatsBatting = ({ season, getAuthHeaders, BACKEND_URL }) => {
  const [expandedMetric, setExpandedMetric]                     = useState(null);
  const [isLoading, setIsLoading]                               = useState(false);
  const [error, setError]                                       = useState(null);
  const [plateDisciplineRankings, setPlateDisciplineRankings]   = useState(null); // B2
  const [clutchRankings, setClutchRankings]                     = useState(null); // B3
  const [contactConsistencyRankings, setContactConsistencyRankings] = useState(null); // B4

  const dummyRankingsData = useMemo(
    () => generateDummyRankings(BATTING_METRICS, DUMMY_BATTERS),
    []
  );

  // ----------------------------------------------------------
  // API Calls — B4 Contact Consistency
  // ----------------------------------------------------------
  const fetchContactConsistencyRankings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/batting/contact-consistency/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setContactConsistencyRankings(await res.json());
    } catch (e) {
      console.error('Contact consistency rankings fetch failed:', e);
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // ----------------------------------------------------------
  // API Calls — B3 Clutch Hitting
  // ----------------------------------------------------------
  const fetchClutchRankings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/batting/clutch/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setClutchRankings(await res.json());
    } catch (e) {
      console.error('Clutch rankings fetch failed:', e);
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // ----------------------------------------------------------
  // API Calls — B2 Plate Discipline
  // ----------------------------------------------------------
  const fetchPlateDisciplineRankings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/batting/plate-discipline/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setPlateDisciplineRankings(data);
    } catch (e) {
      console.error('Plate discipline rankings fetch failed:', e);
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPlateDisciplineRankings();
    fetchClutchRankings();
    fetchContactConsistencyRankings();
  }, [season]);

  // ----------------------------------------------------------
  // getRankingsForMetric
  // ----------------------------------------------------------
  const getRankingsForMetric = (metricId) => {
    if (metricId === 'B3' && clutchRankings?.rankings) {
      return clutchRankings.rankings.map((r) => ({
        id: r.batter_id,
        name: r.player_name,
        team: r.team || '',
        score: r.clutch_hitting_score,
        total_pa: r.total_pa,
        high_li_pa: r.high_li_pa,
        woba_overall: r.woba_overall,
        woba_high_li: r.woba_high_li,
        ba_overall: r.ba_overall,
        ba_high_li: r.ba_high_li,
        clutch_index: r.clutch_index,
      }));
    }
    if (metricId === 'B4' && contactConsistencyRankings?.rankings) {
      return contactConsistencyRankings.rankings.map((r) => ({
        id: r.batter_id, name: r.player_name, team: r.team || '',
        score: r.contact_consistency_score,
        bbip: r.bbip,
        avg_xwoba: r.avg_xwoba,
        stddev_xwoba: r.stddev_xwoba,
        cv_xwoba: r.cv_xwoba,
        hard_hit_pct: r.hard_hit_pct,
        sweet_spot_pct: r.sweet_spot_pct,
      }));
    }
    if (metricId === 'B2' && plateDisciplineRankings?.rankings) {
      return plateDisciplineRankings.rankings.map((r) => ({
        id: r.batter_id,
        name: r.player_name,
        team: r.team || '',
        score: r.plate_discipline_score,
        total_pitches: r.total_pitches,
        o_swing_pct: r.o_swing_pct,
        z_swing_pct: r.z_swing_pct,
        o_take_pct: r.o_take_pct,
        z_take_pct: r.z_take_pct,
        avg_decision_value: r.avg_decision_value,
      }));
    }
    return dummyRankingsData[metricId] || [];
  };

  // ----------------------------------------------------------
  // Shared sub-components
  // ----------------------------------------------------------
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

  // ============================================================
  // B4 Contact Consistency — Metric Detail
  // ============================================================
  const ContactConsistencyDetailView = () => {
    const rawData    = getRankingsForMetric('B4');
    const metric     = BATTING_METRICS.find((m) => m.id === 'B4');
    const scatterData = contactConsistencyRankings?.scatter_all || [];
    const topN = new Set(rawData.slice(0, 5).map((r) => r.name));

    const [sortKey, setSortKey] = React.useState('score');
    const [sortDir, setSortDir] = React.useState('desc');

    const handleSort = (key) => {
      if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      else { setSortKey(key); setSortDir('desc'); }
    };
    const data = [...rawData].sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      return sortDir === 'desc' ? bv - av : av - bv;
    });
    const SortIcon = ({ col }) => {
      if (sortKey !== col) return <span className="text-gray-600 ml-0.5">⇅</span>;
      return <span className="text-indigo-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getConsistencyScoreColor = (score) => {
      if (score >= 115) return 'text-green-400';
      if (score >= 107) return 'text-emerald-400';
      if (score >= 100) return 'text-indigo-400';
      return 'text-orange-400';
    };

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
              xwOBAの変動係数(CV)逆転(35%) + 平均xwOBA(35%) + ハードヒット率(20%) + スウィートスポット率(10%)
            </p>
            <span className="inline-flex items-center mt-1.5 px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[11px] rounded">
              100 = リーグ平均（OPS+ スタイル / ±1σ = 85〜115）
            </span>
          </div>
          <button onClick={fetchContactConsistencyRankings}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white text-xs transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Left: Rankings Table */}
          <div className="xl:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-2 w-8">#</th>
                  <SortTh col="name"          label="Batter"       right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="bbip"          label="BBIP" />
                  <SortTh col="avg_xwoba"     label="avg xwOBA" />
                  <SortTh col="stddev_xwoba"  label="SD xwOBA" />
                  <SortTh col="cv_xwoba"      label="CV↓" />
                  <SortTh col="hard_hit_pct"  label="HH%" />
                  <SortTh col="sweet_spot_pct" label="SS%" />
                  <SortTh col="score"         label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.bbip?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-indigo-300 font-mono text-xs">{r.avg_xwoba?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.stddev_xwoba?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.cv_xwoba?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-amber-400 font-mono text-xs">{r.hard_hit_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-sky-400 font-mono text-xs">{r.sweet_spot_pct?.toFixed(1)}%</td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getConsistencyScoreColor(r.score)}`}>
                      {Math.round(r.score)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right: Scatter + Info */}
          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">avg xwOBA vs CV (変動係数)</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} batters</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                理想は <span className="text-indigo-400">右下</span>（xwOBA高 × CV低 = 質が高く安定）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="avg_xwoba" name="avg xwOBA"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'avg xwOBA (higher = better)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="cv_xwoba" name="CV"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'CV (lower = consistent)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData}>
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#6366f1'}
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
                  <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 opacity-50" />
                  <span className="text-gray-500 text-[10px]">Others</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• 対象: 打球(type=X) × xwOBA付き、打球数 ≥ 80</li>
                <li className="ml-3">• CV = stddev(xwOBA) / avg(xwOBA) → 低いほど一貫</li>
                <li className="ml-3">• neg_cv_z × 0.35 + avg_xwoba_z × 0.35</li>
                <li className="ml-3">• + hard_hit_z × 0.20 + sweet_spot_z × 0.10</li>
                <li className="ml-3">• 合成後に再Zスコア化 → 100 + Z × 15</li>
                <li className="mt-2">補足</li>
                <li className="ml-3 font-mono text-gray-500">• HH%: EV ≥ 95 mph</li>
                <li className="ml-3 font-mono text-gray-500">• SS%: LA 8°〜32°</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // B3 Clutch Hitting — Metric Detail
  // ============================================================
  const ClutchDetailView = () => {
    const rawData    = getRankingsForMetric('B3');
    const metric     = BATTING_METRICS.find((m) => m.id === 'B3');
    const scatterData = clutchRankings?.scatter_all || [];
    const topN = new Set(rawData.slice(0, 5).map((r) => r.name));

    const [sortKey, setSortKey] = React.useState('score');
    const [sortDir, setSortDir] = React.useState('desc');

    const handleSort = (key) => {
      if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      else { setSortKey(key); setSortDir('desc'); }
    };
    const data = [...rawData].sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      return sortDir === 'desc' ? bv - av : av - bv;
    });
    const SortIcon = ({ col }) => {
      if (sortKey !== col) return <span className="text-gray-600 ml-0.5">⇅</span>;
      return <span className="text-rose-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getClutchScoreColor = (score) => {
      if (score >= 115) return 'text-green-400';
      if (score >= 105) return 'text-emerald-400';
      if (score >= 95)  return 'text-rose-300';
      return 'text-orange-400';
    };

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
              高レバレッジ(LI上位25%)時の wOBA − 全体wOBA = clutch_index の合成Zスコア
            </p>
            <span className="inline-flex items-center mt-1.5 px-2 py-0.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[11px] rounded">
              100 = リーグ平均（OPS+ スタイル）
            </span>
          </div>
          <button onClick={fetchClutchRankings}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white text-xs transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Left: Rankings Table */}
          <div className="xl:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-2 w-8">#</th>
                  <SortTh col="name"         label="Batter"      right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="total_pa"     label="PA" />
                  <SortTh col="high_li_pa"   label="High LI PA" />
                  <SortTh col="woba_overall" label="wOBA" />
                  <SortTh col="woba_high_li" label="wOBA(HiLI)" />
                  <SortTh col="ba_overall"   label="BA" />
                  <SortTh col="ba_high_li"   label="BA(HiLI)" />
                  <SortTh col="clutch_index" label="Clutch Δ" />
                  <SortTh col="score"        label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.total_pa?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.high_li_pa?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.woba_overall?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-rose-300 font-mono text-xs">{r.woba_high_li?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.ba_overall?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-rose-300 font-mono text-xs">{r.ba_high_li?.toFixed(3)}</td>
                    <td className={`py-2 px-2 text-right font-mono text-xs ${r.clutch_index >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {r.clutch_index >= 0 ? '+' : ''}{r.clutch_index?.toFixed(3)}
                    </td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getClutchScoreColor(r.score)}`}>
                      {Math.round(r.score)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right: Scatter + Info */}
          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">Overall wOBA vs High-LI wOBA</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} batters</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                対角線より <span className="text-rose-400">上</span> = 高LIで通常より良い（クラッチ）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="woba_overall" name="Overall wOBA"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Overall wOBA', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="woba_high_li" name="High-LI wOBA"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'High-LI wOBA', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData}>
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#f43f5e'}
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
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 opacity-50" />
                  <span className="text-gray-500 text-[10px]">Others</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• LI = 1 / |bat_win_exp − 0.5|（接戦 = 高LI）</li>
                <li className="ml-3">• 閾値: 全PA LIの上位25%</li>
                <li className="ml-3">• Clutch Δ = wOBA(高LI) − wOBA(全体)</li>
                <li className="ml-3">• Score = 100 + Z(clutch_index) × 30</li>
                <li className="mt-2">補足カラム</li>
                <li className="ml-3 font-mono text-gray-500">• BA / BA(HiLI): 高LI時打率</li>
                <li className="mt-2">フィルタ</li>
                <li className="ml-3 font-mono text-gray-500">• 総PA 200以上</li>
                <li className="ml-3 font-mono text-gray-500">• 高LI PA 30以上</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // B2 Plate Discipline — Metric Detail
  // ============================================================
  const PlateDisciplineDetailView = () => {
    const rawData    = getRankingsForMetric('B2');
    const metric     = BATTING_METRICS.find((m) => m.id === 'B2');
    const scatterData = plateDisciplineRankings?.scatter_all || [];
    const topN = new Set(rawData.slice(0, 5).map((r) => r.name));

    const [sortKey, setSortKey] = React.useState('score');
    const [sortDir, setSortDir] = React.useState('desc');

    const handleSort = (key) => {
      if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      else { setSortKey(key); setSortDir('desc'); }
    };

    const data = [...rawData].sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      return sortDir === 'desc' ? bv - av : av - bv;
    });

    const SortIcon = ({ col }) => {
      if (sortKey !== col) return <span className="text-gray-600 ml-0.5">⇅</span>;
      return <span className="text-teal-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );

    const getScoreCol = (score) => {
      if (score >= 1.5) return 'text-green-400';
      if (score >= 0.5) return 'text-emerald-400';
      if (score >= 0)   return 'text-teal-400';
      return 'text-orange-400';
    };

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
              O-Swing%(ゾーン外スイング抑制) × Z-Swing%(ゾーン内スイング) × 判断価値 の合成Zスコア
            </p>
            <span className="inline-flex items-center mt-1.5 px-2 py-0.5 bg-teal-500/10 border border-teal-500/20 text-teal-400 text-[11px] rounded">
              100 = リーグ平均（OPS+ スタイル）
            </span>
          </div>
          <button onClick={fetchPlateDisciplineRankings}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white text-xs transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Left: Rankings Table */}
          <div className="xl:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-2 w-8">#</th>
                  <SortTh col="name"               label="Batter"      right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="total_pitches"      label="Pitches" />
                  <SortTh col="o_swing_pct"        label="O-Swing%" />
                  <SortTh col="z_swing_pct"        label="Z-Swing%" />
                  <SortTh col="o_take_pct"         label="O-Take%" />
                  <SortTh col="z_take_pct"         label="Z-Take%" />
                  <SortTh col="avg_decision_value" label="Dec.Val" />
                  <SortTh col="score"              label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.total_pitches?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-red-400 font-mono">{r.o_swing_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-teal-400 font-mono">{r.z_swing_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-gray-500 font-mono text-xs">{r.o_take_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-gray-500 font-mono text-xs">{r.z_take_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.avg_decision_value?.toFixed(4)}</td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getScoreCol(r.score)}`}>
                      {Math.round(r.score)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right: Scatter + Info */}
          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">O-Swing% vs Z-Swing%</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} batters</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                理想は <span className="text-teal-400">左上</span>（O-Swing↓ Z-Swing↑）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="o_swing_pct" name="O-Swing%"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'O-Swing% (lower = better)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="z_swing_pct" name="Z-Swing%"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Z-Swing% (higher = better)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData}>
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#14b8a6'}
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
                  <div className="w-2.5 h-2.5 rounded-full bg-teal-500 opacity-50" />
                  <span className="text-gray-500 text-[10px]">Others</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• ゾーン判定: zone 1–9 = ゾーン内、11–14 = ゾーン外</li>
                <li className="ml-3">• O-Swing%: ゾーン外スイング率（低いほど良）</li>
                <li className="ml-3">• Z-Swing%: ゾーン内スイング率（高いほど良）</li>
                <li className="ml-3">• Dec.Val: 1投球あたり delta_run_exp 平均</li>
                <li className="ml-3">• Score = Z(O-Swing反転)×0.35 + Z(Z-Swing)×0.35 + Z(Dec.Val)×0.30</li>
                <li className="mt-2">フィルタ</li>
                <li className="ml-3 font-mono text-gray-500">• 総投球数 300球以上</li>
                <li className="ml-3 font-mono text-gray-500">• ゾーン内外それぞれ 50球以上</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // Render
  // ============================================================
  if (expandedMetric === 'B2') return <PlateDisciplineDetailView />;
  if (expandedMetric === 'B3') return <ClutchDetailView />;
  if (expandedMetric === 'B4') return <ContactConsistencyDetailView />;

  // Generic expanded view (dummy metrics)
  if (expandedMetric) {
    const metric = BATTING_METRICS.find((m) => m.id === expandedMetric);
    const data   = getRankingsForMetric(expandedMetric);
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

  // Overview card grid
  return (
    <div className="space-y-4">
      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500" />
          データ読み込み中...
        </div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-2 text-sm">
          API Error: {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {BATTING_METRICS.map((metric) => {
          const data   = getRankingsForMetric(metric.id).slice(0, 5);
          const isLive = (metric.id === 'B2' && !!plateDisciplineRankings)
                       || (metric.id === 'B3' && !!clutchRankings)
                       || (metric.id === 'B4' && !!contactConsistencyRankings);
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
                    onClick={() => setExpandedMetric(metric.id)}>
                    <span className="text-gray-500 text-xs font-medium w-4">{i + 1}</span>
                    <span className="text-white text-sm font-medium flex-1 truncate">{r.name}</span>
                    <span className="text-gray-500 text-xs">{r.team}</span>
                    {metric.id === 'B2' ? (
                      <span className="text-sm font-bold w-16 text-right text-teal-400 font-mono">
                        {Math.round(r.score)}
                      </span>
                    ) : metric.id === 'B3' ? (
                      <span className="text-sm font-bold w-16 text-right text-rose-400 font-mono">
                        {Math.round(r.score)}
                      </span>
                    ) : metric.id === 'B4' ? (
                      <span className="text-sm font-bold w-16 text-right text-indigo-400 font-mono">
                        {Math.round(r.score)}
                      </span>
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
                View Full Rankings <span className="text-xs">›</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AdvancedStatsBatting;
