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
  const [swingEfficiencyRankings, setSwingEfficiencyRankings]   = useState(null); // B1
  const [plateDisciplineRankings, setPlateDisciplineRankings]   = useState(null); // B2
  const [clutchRankings, setClutchRankings]                     = useState(null); // B3
  const [contactConsistencyRankings, setContactConsistencyRankings] = useState(null); // B4
  const [sprayMasteryRankings, setSprayMasteryRankings]         = useState(null); // B6

  const dummyRankingsData = useMemo(
    () => generateDummyRankings(BATTING_METRICS, DUMMY_BATTERS),
    []
  );

  // ----------------------------------------------------------
  // API Calls — B1 Swing Efficiency
  // ----------------------------------------------------------
  const fetchSwingEfficiencyRankings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 500, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/batting/swing-efficiency/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setSwingEfficiencyRankings(await res.json());
    } catch (e) {
      console.error('Swing efficiency rankings fetch failed:', e);
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

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

  const fetchSprayMasteryRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/batting/spray-mastery/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setSprayMasteryRankings(await res.json());
    } catch (e) { console.error('Spray mastery rankings fetch failed:', e); setError(e.message); }
    finally { setIsLoading(false); }
  };

  useEffect(() => {
    fetchSwingEfficiencyRankings();
    fetchPlateDisciplineRankings();
    fetchClutchRankings();
    fetchContactConsistencyRankings();
    fetchSprayMasteryRankings();
  }, [season]);

  // ----------------------------------------------------------
  // getRankingsForMetric
  // ----------------------------------------------------------
  const getRankingsForMetric = (metricId) => {
    if (metricId === 'B1' && swingEfficiencyRankings?.rankings) {
      return swingEfficiencyRankings.rankings.map((r) => ({
        id: r.batter_id, name: r.player_name, team: r.team || '',
        score: r.swing_efficiency_score,
        contact_count: r.contact_count,
        avg_efficiency: r.avg_efficiency,
        avg_bat_speed: r.avg_bat_speed,
        avg_swing_length: r.avg_swing_length,
        avg_ev: r.avg_ev,
        avg_attack_angle: r.avg_attack_angle,
        hard_hit_pct: r.hard_hit_pct,
      }));
    }
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
    if (metricId === 'B6' && sprayMasteryRankings?.rankings) {
      return sprayMasteryRankings.rankings.map((r) => ({
        id: r.batter_id, name: r.player_name, team: r.team || '',
        stand: r.stand || '',
        score: r.spray_mastery_score,
        total_bb: r.total_bb,
        pull_pct: r.pull_pct, center_pct: r.center_pct, oppo_pct: r.oppo_pct,
        spray_entropy: r.spray_entropy,
        avg_xwoba: r.avg_xwoba,
        pull_xwoba: r.pull_xwoba, center_xwoba: r.center_xwoba, oppo_xwoba: r.oppo_xwoba,
        oppo_exit_velo: r.oppo_exit_velo,
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
  // B6 Spray Mastery — Metric Detail
  // ============================================================
  const SprayMasteryDetailView = () => {
    const rawData    = getRankingsForMetric('B6');
    const metric     = BATTING_METRICS.find((m) => m.id === 'B6');
    const scatterData = sprayMasteryRankings?.scatter_all || [];
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
      return <span className="text-lime-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getSprayScoreColor = (score) => {
      if (score >= 115) return 'text-green-400';
      if (score >= 107) return 'text-emerald-400';
      if (score >= 100) return 'text-lime-400';
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
              打球方向エントロピー(40%) × 全体 xwOBA(35%) × オポジット xwOBA(25%) の合成Zスコア
            </p>
            <span className="inline-flex items-center mt-1.5 px-2 py-0.5 bg-lime-500/10 border border-lime-500/20 text-lime-400 text-[11px] rounded">
              100 = リーグ平均（OPS+ スタイル）
            </span>
          </div>
          <button onClick={fetchSprayMasteryRankings}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white text-xs transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-2 w-8">#</th>
                  <SortTh col="name"          label="Batter"    right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <th className="text-left text-gray-400 py-2 px-2">B</th>
                  <SortTh col="total_bb"      label="BB" />
                  <SortTh col="pull_pct"      label="Pull%" />
                  <SortTh col="center_pct"    label="Cent%" />
                  <SortTh col="oppo_pct"      label="Oppo%" />
                  <SortTh col="spray_entropy" label="H(entropy)" />
                  <SortTh col="avg_xwoba"     label="xwOBA" />
                  <SortTh col="oppo_xwoba"    label="Oppo xwOBA" />
                  <SortTh col="score"         label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-xs">
                      <span className={`px-1 py-0.5 rounded font-mono font-bold text-[10px] ${r.stand === 'L' ? 'bg-blue-500/20 text-blue-300' : 'bg-red-500/20 text-red-300'}`}>
                        {r.stand || '—'}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.total_bb}</td>
                    <td className="py-2 px-2 text-right text-red-300 font-mono text-xs">{r.pull_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.center_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-lime-300 font-mono text-xs">{r.oppo_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-cyan-400 font-mono text-xs">{r.spray_entropy?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-amber-400 font-mono">{r.avg_xwoba?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-lime-400 font-mono">{r.oppo_xwoba?.toFixed(3) ?? '—'}</td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getSprayScoreColor(r.score)}`}>
                      {Math.round(r.score)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">Entropy vs xwOBA</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} batters</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                理想は <span className="text-lime-400">右上</span>（エントロピー高い ＋ xwOBA 高い）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="spray_entropy" name="Entropy"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Spray Entropy (higher = more balanced)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="avg_xwoba" name="avg xwOBA"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'avg xwOBA', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData}>
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#84cc16'}
                        fillOpacity={topN.has(entry.player_name) ? 0.9 : 0.45}
                        r={topN.has(entry.player_name) ? 5 : 3} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-3 mt-1.5">
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-lime-500 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>打球方向分類（hc_x 基準）</li>
                <li className="ml-3 font-mono text-gray-500">• RHB: Pull &lt;100 / Center 100〜155 / Oppo &gt;155</li>
                <li className="ml-3 font-mono text-gray-500">• LHB: Oppo &lt;100 / Center 100〜155 / Pull &gt;155</li>
                <li className="mt-2">算出ロジック</li>
                <li className="ml-3">• H = -Σ p(i) × ln(p(i))（最大 ln(3) ≈ 1.099）</li>
                <li className="ml-3">• entropy_z × 0.40 + avg_xwoba_z × 0.35</li>
                <li className="ml-3">• + oppo_xwoba_z × 0.25 → 再Zスコア化 → 100 + Z × 15</li>
                <li className="mt-2">フィルタ: 打球数 ≥ 80</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // B1 Swing Efficiency — Metric Detail
  // ============================================================
  const SwingEfficiencyDetailView = () => {
    const rawData = getRankingsForMetric('B1');
    const metric  = BATTING_METRICS.find((m) => m.id === 'B1');

    const defaultMinContact = season >= 2026 ? 20 : 250;
    const [minContact, setMinContact] = React.useState(defaultMinContact);
    const [inputVal, setInputVal]     = React.useState(String(defaultMinContact));

    const allRawData   = rawData;
    const filteredData = allRawData.filter((r) => (r.contact_count ?? 0) >= minContact);
    const scatterDataFiltered = (swingEfficiencyRankings?.scatter_all || [])
      .filter((r) => (r.contact_count ?? 0) >= minContact);

    const [sortKey, setSortKey] = React.useState('score');
    const [sortDir, setSortDir] = React.useState('desc');

    const handleSort = (key) => {
      if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      else { setSortKey(key); setSortDir('desc'); }
    };
    const data = [...filteredData].sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      return sortDir === 'desc' ? bv - av : av - bv;
    }).slice(0, 40);
    const topN = new Set(data.slice(0, 5).map((r) => r.name));
    const SortIcon = ({ col }) => {
      if (sortKey !== col) return <span className="text-gray-600 ml-0.5">⇅</span>;
      return <span className="text-cyan-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getSwingScoreColor = (score) => {
      if (score >= 115) return 'text-green-400';
      if (score >= 107) return 'text-emerald-400';
      if (score >= 100) return 'text-cyan-400';
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
              スイング効率(EV/bat×len)(50%) + スイング長の短さ(30%) + ハードヒット率(20%)
            </p>
            <span className="inline-flex items-center mt-1.5 px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[11px] rounded">
              100 = リーグ平均（OPS+ スタイル / ±1σ = 85〜115）⚠️ 2024年〜限定
            </span>
          </div>
          <button onClick={fetchSwingEfficiencyRankings}
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
                  <SortTh col="name"             label="Batter"      right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="contact_count"    label="Contact" />
                  <SortTh col="avg_efficiency"   label="Efficiency" />
                  <SortTh col="avg_bat_speed"    label="Bat Spd" />
                  <SortTh col="avg_swing_length" label="Sw Len↓" />
                  <SortTh col="avg_ev"           label="avg EV" />
                  <SortTh col="avg_attack_angle" label="Atk Ang" />
                  <SortTh col="hard_hit_pct"     label="HH%" />
                  <SortTh col="score"            label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.contact_count?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-cyan-300 font-mono text-xs">{r.avg_efficiency?.toFixed(4)}</td>
                    <td className="py-2 px-2 text-right text-amber-400 font-mono text-xs">{r.avg_bat_speed?.toFixed(1)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.avg_swing_length?.toFixed(2)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.avg_ev?.toFixed(1)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.avg_attack_angle?.toFixed(1) ?? '—'}</td>
                    <td className="py-2 px-2 text-right text-amber-400 font-mono text-xs">{r.hard_hit_pct?.toFixed(1)}%</td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getSwingScoreColor(r.score)}`}>
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
                <h4 className="text-sm font-medium text-gray-300">Bat Speed vs Swing Efficiency</h4>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-gray-500">min contact</span>
                  <input
                    type="number" min={1} step={10}
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    onBlur={() => {
                      const v = parseInt(inputVal, 10);
                      if (!isNaN(v) && v >= 1) setMinContact(v);
                      else setInputVal(String(minContact));
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        const v = parseInt(inputVal, 10);
                        if (!isNaN(v) && v >= 1) setMinContact(v);
                        else setInputVal(String(minContact));
                      }
                    }}
                    className="w-16 bg-gray-700 border border-gray-600 rounded px-1.5 py-0.5 text-white text-xs text-right"
                  />
                  <span className="text-[10px] text-gray-500">{scatterDataFiltered.length} batters</span>
                </div>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                理想は <span className="text-cyan-400">右上</span>（速いスイングで高効率）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="avg_bat_speed" name="Bat Speed"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'avg Bat Speed (mph)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="avg_efficiency" name="Swing Efficiency"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Swing Efficiency', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterDataFiltered}>
                    {scatterDataFiltered.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#06b6d4'}
                        fillOpacity={topN.has(entry.player_name) ? 0.9 : 0.45}
                        r={topN.has(entry.player_name) ? 5 : 3} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-3 mt-1.5">
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-cyan-500 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• Efficiency = EV / (BatSpeed × SwingLen)</li>
                <li className="ml-3">• Z(efficiency)×0.50 + Z(neg_swing_len)×0.30</li>
                <li className="ml-3">• + Z(hard_hit)×0.20 → 再Zスコア化 → 100 + Z × 15</li>
                <li className="mt-2">補足カラム</li>
                <li className="ml-3 font-mono text-gray-500">• Attack Angle: 参考値のみ（スコア不含）</li>
                <li className="mt-2">フィルタ</li>
                <li className="ml-3 font-mono text-gray-500">• 打球数 ≥ 50（2024年〜限定）</li>
              </ul>
            </div>
          </div>
        </div>
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
  if (expandedMetric === 'B1') return <SwingEfficiencyDetailView />;
  if (expandedMetric === 'B2') return <PlateDisciplineDetailView />;
  if (expandedMetric === 'B3') return <ClutchDetailView />;
  if (expandedMetric === 'B4') return <ContactConsistencyDetailView />;
  if (expandedMetric === 'B6') return <SprayMasteryDetailView />;

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
          const isLive = (metric.id === 'B1' && !!swingEfficiencyRankings)
                       || (metric.id === 'B2' && !!plateDisciplineRankings)
                       || (metric.id === 'B3' && !!clutchRankings)
                       || (metric.id === 'B4' && !!contactConsistencyRankings)
                       || (metric.id === 'B6' && !!sprayMasteryRankings);
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
                    {metric.id === 'B1' ? (
                      <span className="text-sm font-bold w-16 text-right text-cyan-400 font-mono">
                        {Math.round(r.score)}
                      </span>
                    ) : metric.id === 'B2' ? (
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
                    ) : metric.id === 'B6' ? (
                      <span className="text-sm font-bold w-16 text-right text-lime-400 font-mono">
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
