import React, { useState, useEffect, useMemo } from 'react';
import {
  CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, XAxis, YAxis, Cell,
} from 'recharts';
import { ChevronLeft, RefreshCw } from 'lucide-react';
import {
  PITCHING_METRICS, DUMMY_PITCHERS, generateDummyRankings,
  PITCH_TYPE_COLORS, getPitchColor, getScoreColor, getBarFill,
} from './advancedStatsConstants';

// ============================================================
// AdvancedStatsPitching
// Props: season, getAuthHeaders, BACKEND_URL
// ============================================================
const AdvancedStatsPitching = ({ season, getAuthHeaders, BACKEND_URL }) => {
  const [expandedMetric, setExpandedMetric]               = useState(null);
  const [isLoading, setIsLoading]                         = useState(false);
  const [error, setError]                                 = useState(null);
  const [arsenalRankings, setArsenalRankings]             = useState(null);
  const [pitchTunnelRankings, setPitchTunnelRankings]     = useState(null);
  const [finisherRankings, setFinisherRankings]           = useState(null);
  const [staminaRankings, setStaminaRankings]             = useState(null);
  const [pressureRankings, setPressureRankings]           = useState(null);
  const [platoonRankings, setPlatoonRankings]             = useState(null);

  const dummyRankingsData = useMemo(
    () => generateDummyRankings(PITCHING_METRICS, DUMMY_PITCHERS),
    []
  );

  // ----------------------------------------------------------
  // API Calls
  // ----------------------------------------------------------
  const fetchPitchTunnelRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/pitching/pitch-tunnel/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setPitchTunnelRankings(await res.json());
    } catch (e) { console.error('Pitch tunnel fetch failed:', e); setError(e.message); }
    finally { setIsLoading(false); }
  };

  const fetchPressureRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/pitching/pressure-dominance/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setPressureRankings(await res.json());
    } catch (e) { console.error('Pressure dominance fetch failed:', e); setError(e.message); }
    finally { setIsLoading(false); }
  };

  const fetchStaminaRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/pitching/stamina/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setStaminaRankings(await res.json());
    } catch (e) { console.error('Stamina fetch failed:', e); setError(e.message); }
    finally { setIsLoading(false); }
  };

  const fetchFinisherRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/pitching/finisher/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setFinisherRankings(await res.json());
    } catch (e) { console.error('Finisher fetch failed:', e); setError(e.message); }
    finally { setIsLoading(false); }
  };

  const fetchArsenalRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ season, min_pitches: 100, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/pitching/arsenal/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setArsenalRankings(await res.json());
    } catch (e) { console.error('Arsenal fetch failed:', e); setError(e.message); }
    finally { setIsLoading(false); }
  };

  const fetchPlatoonRankings = async () => {
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ season, limit: 40, offset: 0 });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/advanced-stats/pitching/platoon-neutrality/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setPlatoonRankings(await res.json());
    } catch (e) { console.error('Platoon neutrality fetch failed:', e); setError(e.message); }
    finally { setIsLoading(false); }
  };

  useEffect(() => {
    fetchPressureRankings();
    fetchPitchTunnelRankings();
    fetchStaminaRankings();
    fetchFinisherRankings();
    fetchArsenalRankings();
    fetchPlatoonRankings();
  }, [season]);

  // ----------------------------------------------------------
  // getRankingsForMetric
  // ----------------------------------------------------------
  const getRankingsForMetric = (metricId) => {
    if (metricId === 'P2' && pressureRankings?.rankings) {
      return pressureRankings.rankings.map((r) => ({
        id: r.pitcher_id, name: r.player_name, team: r.team || '',
        score: r.pressure_dominance_index,
        total_pitches: r.total_pitches, high_li_pitches: r.high_li_pitches,
        high_li_run_exp: r.high_li_run_exp, low_li_run_exp: r.low_li_run_exp,
        pressure_delta: r.pressure_delta,
      }));
    }
    if (metricId === 'P1' && pitchTunnelRankings?.rankings) {
      return pitchTunnelRankings.rankings.map((r, i) => ({
        id: i, name: r.player_name, team: r.team || '',
        score: r.pitch_tunnel_score,
        deception_rate_pct: r.deception_rate_pct, whiffs: r.whiffs,
        called_strikes: r.called_strikes, total_sequences: r.total_sequences,
        avg_release_diff: r.avg_release_diff, avg_velocity_diff: r.avg_velocity_diff,
        avg_plate_diff: r.avg_plate_diff,
      }));
    }
    if (metricId === 'P3' && staminaRankings?.rankings) {
      return staminaRankings.rankings.map((r) => ({
        id: r.pitcher_id, name: r.player_name, team: r.team || '',
        score: r.stamina_score,
        games: r.games, ip: r.ip,
        avg_speed_slope: r.avg_speed_slope, avg_spin_slope: r.avg_spin_slope,
        run_exp_1st: r.run_exp_1st, run_exp_3rd_plus: r.run_exp_3rd_plus,
        tto_delta: r.tto_delta,
      }));
    }
    if (metricId === 'P4' && finisherRankings?.rankings) {
      return finisherRankings.rankings.map((r) => ({
        id: r.pitcher_id, name: r.player_name, team: r.team || '',
        score: r.finisher_score,
        whiff_rate: r.whiff_rate, put_away_woba: r.put_away_woba,
        total_2_strike_pitches: r.total_2_strike_pitches,
        primary_finishing_pitch: r.primary_finishing_pitch,
      }));
    }
    if (metricId === 'P6' && arsenalRankings?.rankings) {
      return arsenalRankings.rankings.map((r) => ({
        id: r.pitcher_id, name: r.player_name, team: r.team || '',
        score: r.arsenal_effectiveness_score,
        diversity_score: r.diversity_score, effectiveness_score: r.effectiveness_score,
        pitch_mix: r.pitch_mix || [],
      }));
    }
    if (metricId === 'P8' && platoonRankings?.rankings) {
      return platoonRankings.rankings.map((r) => ({
        id: r.pitcher_id, name: r.player_name, team: r.team || '',
        p_throws: r.p_throws || '',
        score: r.platoon_neutrality_score,
        total_pitches: r.total_pitches,
        pitches_vs_l: r.pitches_vs_l, pitches_vs_r: r.pitches_vs_r,
        woba_vs_l: r.woba_vs_l, woba_vs_r: r.woba_vs_r,
        woba_diff_abs: r.woba_diff_abs,
        delta_run_vs_l: r.delta_run_vs_l, delta_run_vs_r: r.delta_run_vs_r,
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
        <p className="text-white font-medium text-sm">{d.name || d.player_name || d.season}</p>
        {payload.map((p, i) => (
          <p key={i} className="text-gray-300 text-xs">
            {p.name}: {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
          </p>
        ))}
      </div>
    );
  };

  // ============================================================
  // P1 Pitch Tunnel Score — Metric Detail
  // ============================================================
  const PitchTunnelDetailView = () => {
    const rawData    = getRankingsForMetric('P1');
    const metric     = PITCHING_METRICS.find((m) => m.id === 'P1');
    const scatterData = pitchTunnelRankings?.scatter_all || [];
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
      return <span className="text-blue-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getTunnelScoreColor = (score) => {
      if (score >= 1.5) return 'text-green-400';
      if (score >= 0.5) return 'text-emerald-400';
      if (score >= 0)   return 'text-yellow-400';
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
              速球→変化球シーケンスで打者を騙せた割合（空振り＋見逃しストライク）のリーグ平均対比 z-score
            </p>
          </div>
          <button onClick={fetchPitchTunnelRankings}
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
                  <SortTh col="name"               label="Pitcher"     right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="total_sequences"    label="Seqs" />
                  <SortTh col="deception_rate_pct" label="Deception%" />
                  <SortTh col="whiffs"             label="Whiffs" />
                  <SortTh col="called_strikes"     label="Called K" />
                  <SortTh col="avg_release_diff"   label="Rel Diff" />
                  <SortTh col="avg_velocity_diff"  label="Vel Diff" />
                  <SortTh col="avg_plate_diff"     label="Plate Diff" />
                  <SortTh col="score"              label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.total_sequences?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-cyan-400 font-mono">{r.deception_rate_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-gray-300 font-mono">{r.whiffs}</td>
                    <td className="py-2 px-2 text-right text-gray-300 font-mono">{r.called_strikes}</td>
                    <td className="py-2 px-2 text-right text-gray-500 font-mono text-xs">{r.avg_release_diff?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-gray-500 font-mono text-xs">{r.avg_velocity_diff?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-gray-500 font-mono text-xs">{r.avg_plate_diff?.toFixed(3)}</td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getTunnelScoreColor(r.score)}`}>
                      {r.score?.toFixed(0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">Release Diff vs Plate Diff</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} pitchers</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                左下 = リリース収束↑ / 上 = プレート発散↑ → 理想は <span className="text-indigo-400">左上</span>
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="avg_release_diff" name="Release Diff"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Release Diff (lower = tighter)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="avg_plate_diff" name="Plate Diff"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Plate Diff (higher = more break)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData} fill="#6366f1">
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
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-indigo-500 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• 対象: FB (FF/SI/FC) → 変化球 (SL/ST/CH/FS/CU)</li>
                <li className="ml-3">• deception = swinging_strike + called_strike</li>
                <li className="ml-3">• Score = z-score(deception_rate)</li>
                <li className="mt-2">参考指標（スコア外）</li>
                <li className="ml-3 font-mono text-gray-500">• Rel Diff: リリース収束度</li>
                <li className="ml-3 font-mono text-gray-500">• Vel Diff: 速度ベクトル収束度</li>
                <li className="ml-3 font-mono text-gray-500">• Plate Diff: プレート発散度</li>
                <li className="mt-2">フィルタ: 最低 100 シーケンス以上</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // P6 Arsenal Expanded View — Metric Detail
  // ============================================================
  const ArsenalDetailView = () => {
    const data       = getRankingsForMetric('P6');
    const metric     = PITCHING_METRICS.find((m) => m.id === 'P6');
    const scatterData = arsenalRankings?.scatter_all || data.map((r) => ({
      player_name: r.name, diversity_score: r.diversity_score,
      effectiveness_score: r.effectiveness_score, synthetic_score: r.score,
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
          <div className="xl:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-4">
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
                        <td className={`py-2 px-2 text-right font-bold ${getScoreColor(r.score)}`}>{r.score?.toFixed(0)}</td>
                        <td className="py-2 px-2">
                          {mix && mix.length > 0 ? (
                            <div className="relative">
                              <div className="flex h-3 rounded-full overflow-hidden">
                                {mix.map((p) => (
                                  <div key={p.pitch_name}
                                    style={{ width: `${p.usage_pct * 100}%`, backgroundColor: getPitchColor(p.pitch_name) }} />
                                ))}
                              </div>
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

          <div className="space-y-4">
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
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-purple-500 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
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
  // P3 Stamina Score — Metric Detail
  // ============================================================
  const StaminaDetailView = () => {
    const rawData    = getRankingsForMetric('P3');
    const metric     = PITCHING_METRICS.find((m) => m.id === 'P3');
    const scatterData = staminaRankings?.scatter_all || [];
    const topN = new Set(rawData.slice(0, 5).map((r) => r.name));

    const [sortKey, setSortKey] = React.useState('score');
    const [sortDir, setSortDir] = React.useState('desc');

    const handleSort = (key) => {
      if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      else { setSortKey(key); setSortDir('desc'); }
    };
    const slopeKeys = new Set(['avg_speed_slope', 'avg_spin_slope']);
    const data = [...rawData].sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      const inv = slopeKeys.has(sortKey);
      return (sortDir === 'desc') !== inv ? bv - av : av - bv;
    });
    const SortIcon = ({ col }) => {
      if (sortKey !== col) return <span className="text-gray-600 ml-0.5">⇅</span>;
      return <span className="text-blue-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getSlopeColor = (v) => {
      if (v >= -0.005) return 'text-green-400';
      if (v >= -0.015) return 'text-emerald-400';
      if (v >= -0.03)  return 'text-yellow-400';
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
              球速・回転数の投球数対比減衰スロープ（70%）と打順3巡目以降の run expectancy 差分（30%）の合成スコア
            </p>
          </div>
          <button onClick={fetchStaminaRankings}
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
                  <SortTh col="name"             label="Pitcher"       right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="ip"               label="IP" />
                  <SortTh col="avg_speed_slope"  label="Spd Slope" />
                  <SortTh col="avg_spin_slope"   label="Spin Slope" />
                  <SortTh col="run_exp_1st"      label="RE 1st TTO" />
                  <SortTh col="run_exp_3rd_plus" label="RE 3rd+ TTO" />
                  <SortTh col="tto_delta"        label="TTO Δ" />
                  <SortTh col="score"            label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-300 font-mono">{r.ip?.toFixed(1)}</td>
                    <td className={`py-2 px-2 text-right font-mono text-xs ${getSlopeColor(r.avg_speed_slope)}`}>{r.avg_speed_slope?.toFixed(4)}</td>
                    <td className={`py-2 px-2 text-right font-mono text-xs ${getSlopeColor(r.avg_spin_slope)}`}>{r.avg_spin_slope?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.run_exp_1st?.toFixed(4)}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono text-xs">{r.run_exp_3rd_plus?.toFixed(4)}</td>
                    <td className="py-2 px-2 text-right text-cyan-400 font-mono">{r.tto_delta?.toFixed(4)}</td>
                    <td className="py-2 px-2 text-right font-bold font-mono text-emerald-400">{r.score?.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">Speed Decay vs TTO Delta</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} pitchers</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                理想は <span className="text-green-400">右上</span>（球速維持 ＋ TTO差なし）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="avg_speed_slope" name="Speed Slope"
                    tickFormatter={(v) => v.toFixed(3)} stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Speed Slope (→ 0 = better)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="tto_delta" name="TTO Delta"
                    tickFormatter={(v) => v.toFixed(3)} stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'TTO Δ (higher = better)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData}>
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#10b981'}
                        fillOpacity={topN.has(entry.player_name) ? 0.9 : 0.45}
                        r={topN.has(entry.player_name) ? 5 : 3} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-3 mt-1.5">
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-emerald-500 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• Speed Slope: pitch_number vs release_speed の線形回帰傾き</li>
                <li className="ml-3">• Spin Slope: pitch_number vs release_spin_rate の線形回帰傾き</li>
                <li className="ml-3">• TTO Δ: 3巡目以降 − 1巡目の delta_pitcher_run_exp</li>
                <li className="ml-3">• Score = Speed Z×0.4 + Spin Z×0.3 + TTO Z×0.3</li>
                <li className="mt-2">入力カラム</li>
                <li className="ml-3 font-mono text-gray-500">release_speed, release_spin_rate, pitch_number, n_thruorder_pitcher</li>
                <li className="mt-2">フィルタ: 100 IP 以上</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // P4 Two-Strike Finisher — Metric Detail
  // ============================================================
  const FinisherDetailView = () => {
    const rawData    = getRankingsForMetric('P4');
    const metric     = PITCHING_METRICS.find((m) => m.id === 'P4');
    const scatterData = finisherRankings?.scatter_all || [];
    const topN = new Set(rawData.slice(0, 5).map((r) => r.name));

    const [sortKey, setSortKey] = React.useState('score');
    const [sortDir, setSortDir] = React.useState('desc');

    const handleSort = (key) => {
      if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      else { setSortKey(key); setSortDir('desc'); }
    };
    const data = [...rawData].sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      const inv = sortKey === 'put_away_woba';
      return (sortDir === 'desc') !== inv ? bv - av : av - bv;
    });
    const SortIcon = ({ col }) => {
      if (sortKey !== col) return <span className="text-gray-600 ml-0.5">⇅</span>;
      return <span className="text-blue-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getFinisherColor = (score) => {
      if (score >= 1.2) return 'text-green-400';
      if (score >= 0.8) return 'text-emerald-400';
      if (score >= 0.4) return 'text-yellow-400';
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
              2ストライク時の Whiff Rate（50%）と被 wOBA の低さ（50%）を合成した決め球力スコア
            </p>
          </div>
          <button onClick={fetchFinisherRankings}
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
                  <SortTh col="name"                   label="Pitcher"        right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="total_2_strike_pitches" label="2K Pitches" />
                  <th className="text-left text-gray-400 py-2 px-2">Primary Pitch</th>
                  <SortTh col="whiff_rate"             label="Whiff%" />
                  <SortTh col="put_away_woba"          label="Put Away wOBA" />
                  <SortTh col="score"                  label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-300 font-mono">{r.total_2_strike_pitches?.toLocaleString()}</td>
                    <td className="py-2 px-2">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                        style={{ backgroundColor: `${getPitchColor(r.primary_finishing_pitch)}22`, color: getPitchColor(r.primary_finishing_pitch) }}>
                        {r.primary_finishing_pitch || '—'}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right text-cyan-400 font-mono">{r.whiff_rate != null ? `${(r.whiff_rate * 100).toFixed(1)}%` : '—'}</td>
                    <td className="py-2 px-2 text-right text-amber-400 font-mono">{r.put_away_woba?.toFixed(3)}</td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getFinisherColor(r.score)}`}>{r.score?.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">Whiff% vs Put Away wOBA</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} pitchers</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                理想は <span className="text-green-400">右下</span>（Whiff% 高い ＋ wOBA 低い）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="whiff_rate" name="Whiff Rate"
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Whiff% (higher = better)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="put_away_woba" name="Put Away wOBA"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Put Away wOBA (lower = better)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData}>
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#22d3ee'}
                        fillOpacity={topN.has(entry.player_name) ? 0.9 : 0.45}
                        r={topN.has(entry.player_name) ? 5 : 3} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-3 mt-1.5">
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-cyan-400 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• 対象: 2ストライクカウント時の全投球</li>
                <li className="ml-3">• Whiff Rate: 空振り / スイング数</li>
                <li className="ml-3">• Put Away wOBA: 2K時の被 wOBA 平均（低いほど良）</li>
                <li className="ml-3">• Score = Whiff Rate × 0.5 + (1 − wOBA) Z-score × 0.5</li>
                <li className="mt-2">入力カラム</li>
                <li className="ml-3 font-mono text-gray-500">strikes, description, woba_value</li>
                <li className="mt-2">フィルタ: 最低 100 球（2K）以上</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // P8 Platoon Neutrality Score — Metric Detail
  // ============================================================
  const PlatoonNeutralityDetailView = () => {
    const rawData    = getRankingsForMetric('P8');
    const metric     = PITCHING_METRICS.find((m) => m.id === 'P8');
    const scatterData = platoonRankings?.scatter_all || [];
    const topN = new Set(rawData.slice(0, 5).map((r) => r.name));

    const [sortKey, setSortKey] = React.useState('score');
    const [sortDir, setSortDir] = React.useState('desc');

    const handleSort = (key) => {
      if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      else { setSortKey(key); setSortDir('desc'); }
    };
    // woba_diff_abs は小さいほど良いので昇順反転
    const invertKeys = new Set(['woba_diff_abs']);
    const data = [...rawData].sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      const inv = invertKeys.has(sortKey);
      return (sortDir === 'desc') !== inv ? bv - av : av - bv;
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
    const getPlatoonScoreColor = (score) => {
      if (score >= 130) return 'text-green-400';
      if (score >= 115) return 'text-emerald-400';
      if (score >= 85)  return 'text-yellow-400';
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
              対左右 wOBA 差の絶対値を均等性スコアに変換し、偏差値スタイル（50 ± 10）でランキング化
            </p>
          </div>
          <button onClick={fetchPlatoonRankings}
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
                  <SortTh col="name"          label="Pitcher"     right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <th className="text-left text-gray-400 py-2 px-2">Hand</th>
                  <SortTh col="total_pitches" label="Pitches" />
                  <SortTh col="pitches_vs_l"  label="vs L" />
                  <SortTh col="pitches_vs_r"  label="vs R" />
                  <SortTh col="woba_vs_l"     label="wOBA L" />
                  <SortTh col="woba_vs_r"     label="wOBA R" />
                  <SortTh col="woba_diff_abs" label="Diff↓" />
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
                      <span className={`px-1.5 py-0.5 rounded font-mono font-bold ${r.p_throws === 'L' ? 'bg-blue-500/20 text-blue-300' : 'bg-red-500/20 text-red-300'}`}>
                        {r.p_throws ? `${r.p_throws}HP` : '—'}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.total_pitches?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-blue-300 font-mono text-xs">{r.pitches_vs_l?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-red-300 font-mono text-xs">{r.pitches_vs_r?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-blue-400 font-mono">{r.woba_vs_l?.toFixed(3)}</td>
                    <td className="py-2 px-2 text-right text-red-400 font-mono">{r.woba_vs_r?.toFixed(3)}</td>
                    <td className={`py-2 px-2 text-right font-mono text-xs ${r.woba_diff_abs <= 0.02 ? 'text-green-400' : r.woba_diff_abs <= 0.05 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {r.woba_diff_abs?.toFixed(3)}
                    </td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getPlatoonScoreColor(r.score)}`}>
                      {r.score != null ? Math.round(r.score) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">wOBA vs L vs wOBA vs R</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} pitchers</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                対角線に近い = 左右均等 → 理想は <span className="text-teal-400">左下の対角線上</span>（両側を低wOBAで抑制）
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="woba_vs_l" name="wOBA vs L"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'wOBA vs LHB (lower = better)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="woba_vs_r" name="wOBA vs R"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'wOBA vs RHB (lower = better)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
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
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-teal-500 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック（OPS+スタイル、100=リーグ平均）</li>
                <li className="ml-3">• 均等性 Z (60%): wOBA Diff の小ささを z-score 化</li>
                <li className="ml-3">• パフォーマンス Z (40%): 対左右平均 wOBA の低さを z-score 化</li>
                <li className="ml-3">• composite_raw = neutrality_z × 0.6 + performance_z × 0.4</li>
                <li className="ml-3">• composite_raw を再 z-score 化 → 100 + Z × 15</li>
                <li className="mt-2">スケール</li>
                <li className="ml-3 font-mono text-gray-500">• ±1σ = 85〜115 / ±2σ = 70〜130</li>
                <li className="mt-2">入力カラム</li>
                <li className="ml-3 font-mono text-gray-500">stand, woba_value, delta_pitcher_run_exp</li>
                <li className="mt-2">フィルタ: 対左・対右それぞれ 100 球以上</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // P2 Pressure Dominance — Metric Detail
  // ============================================================
  const PressureDominanceDetailView = () => {
    const rawData    = getRankingsForMetric('P2');
    const metric     = PITCHING_METRICS.find((m) => m.id === 'P2');
    const scatterData = pressureRankings?.scatter_all || [];
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
      return <span className="text-orange-400 ml-0.5">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };
    const SortTh = ({ col, label, right = true }) => (
      <th onClick={() => handleSort(col)}
        className={`${right ? 'text-right' : 'text-left'} text-gray-400 py-2 px-2 cursor-pointer hover:text-white select-none transition-colors`}>
        {label}<SortIcon col={col} />
      </th>
    );
    const getPressureScoreColor = (score) => {
      if (score >= 1.5) return 'text-green-400';
      if (score >= 0.5) return 'text-emerald-400';
      if (score >= 0)   return 'text-yellow-400';
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
              高レバレッジ状況(LI上位25%)での delta_pitcher_run_exp と低LI差分のZスコア合成（先発投手限定）
            </p>
          </div>
          <button onClick={fetchPressureRankings}
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
                  <SortTh col="name"            label="Pitcher"      right={false} />
                  <th className="text-left text-gray-400 py-2 px-2">Team</th>
                  <SortTh col="total_pitches"   label="Pitches" />
                  <SortTh col="high_li_pitches" label="High LI" />
                  <SortTh col="high_li_run_exp" label="High LI RE" />
                  <SortTh col="low_li_run_exp"  label="Low LI RE" />
                  <SortTh col="pressure_delta"  label="Delta" />
                  <SortTh col="score"           label="Score" />
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-2 px-2 text-gray-500 font-medium">{i + 1}</td>
                    <td className="py-2 px-2 text-white font-medium">{r.name}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">{r.team}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.total_pitches?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-gray-400 font-mono">{r.high_li_pitches?.toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-orange-300 font-mono text-xs">{r.high_li_run_exp?.toFixed(4)}</td>
                    <td className="py-2 px-2 text-right text-gray-500 font-mono text-xs">{r.low_li_run_exp?.toFixed(4)}</td>
                    <td className={`py-2 px-2 text-right font-mono text-xs ${r.pressure_delta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {r.pressure_delta >= 0 ? '+' : ''}{r.pressure_delta?.toFixed(4)}
                    </td>
                    <td className={`py-2 px-2 text-right font-bold font-mono ${getPressureScoreColor(r.score)}`}>
                      {r.score >= 0 ? '+' : ''}{r.score?.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-300">High LI Run Exp vs Pressure Delta</h4>
                <span className="text-[10px] text-gray-500">{scatterData.length} pitchers</span>
              </div>
              <p className="text-[10px] text-gray-500 mb-2">
                右上 = 高LIで好成績 かつ 低LIより更に良い → 理想は <span className="text-orange-400">右上</span>
              </p>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" dataKey="high_li_run_exp" name="High LI RE"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'High LI Run Exp', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }} />
                  <YAxis type="number" dataKey="pressure_delta" name="Pressure Delta"
                    stroke="#9ca3af" tick={{ fontSize: 10 }}
                    label={{ value: 'Pressure Delta', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={scatterData} fill="#f97316">
                    {scatterData.map((entry, i) => (
                      <Cell key={i}
                        fill={topN.has(entry.player_name) ? '#f59e0b' : '#f97316'}
                        fillOpacity={topN.has(entry.player_name) ? 0.9 : 0.5}
                        r={topN.has(entry.player_name) ? 5 : 3} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-3 mt-1.5">
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-amber-500" /><span className="text-gray-500 text-[10px]">Top 5</span></div>
                <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-orange-500 opacity-50" /><span className="text-gray-500 text-[10px]">Others</span></div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Calculation Details</h4>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>算出ロジック</li>
                <li className="ml-3">• LI = 1 / |bat_win_exp − 0.5|（接戦 = 高LI）</li>
                <li className="ml-3">• 閾値: 全投球LIの上位25%（PERCENTILE 0.75）</li>
                <li className="ml-3">• Score = Z(high_li_RE) × 0.5 + Z(pressure_delta) × 0.5</li>
                <li className="mt-2">先発投手の定義</li>
                <li className="ml-3">• 月単位で打順2巡以上登板が50%以上</li>
                <li className="ml-3">• その月に先発2回以上</li>
                <li className="mt-2">フィルタ</li>
                <li className="ml-3 font-mono text-gray-500">• 総投球数 100球以上</li>
                <li className="ml-3 font-mono text-gray-500">• 高LI投球 20球以上</li>
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
  if (expandedMetric === 'P1') return <PitchTunnelDetailView />;
  if (expandedMetric === 'P2') return <PressureDominanceDetailView />;
  if (expandedMetric === 'P3') return <StaminaDetailView />;
  if (expandedMetric === 'P4') return <FinisherDetailView />;
  if (expandedMetric === 'P6') return <ArsenalDetailView />;
  if (expandedMetric === 'P8') return <PlatoonNeutralityDetailView />;

  // Generic expanded view (dummy metrics)
  if (expandedMetric) {
    const metric = PITCHING_METRICS.find((m) => m.id === expandedMetric);
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
        {PITCHING_METRICS.map((metric) => {
          const data   = getRankingsForMetric(metric.id).slice(0, 5);
          const isLive = (metric.id === 'P1' && !!pitchTunnelRankings)
                      || (metric.id === 'P2' && !!pressureRankings)
                      || (metric.id === 'P3' && !!staminaRankings)
                      || (metric.id === 'P4' && !!finisherRankings)
                      || (metric.id === 'P6' && !!arsenalRankings)
                      || (metric.id === 'P8' && !!platoonRankings);
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
                    {metric.id === 'P1' ? (
                      <span className="text-sm font-bold w-16 text-right text-indigo-400 font-mono">
                        {r.score?.toFixed(0)}
                      </span>
                    ) : metric.id === 'P2' ? (
                      <span className="text-sm font-bold w-16 text-right text-orange-400 font-mono">
                        {r.score?.toFixed(0)}
                      </span>
                    ) : metric.id === 'P3' ? (
                      <span className="text-sm font-bold w-16 text-right text-emerald-400 font-mono">{r.score?.toFixed(0)}</span>
                    ) : metric.id === 'P4' ? (
                      <span className="text-sm font-bold w-16 text-right text-cyan-400 font-mono">{r.score?.toFixed(2)}</span>
                    ) : metric.id === 'P6' ? (
                      <span className="text-sm font-bold w-16 text-right text-amber-400 font-mono">{r.score?.toFixed(0)}</span>
                    ) : metric.id === 'P8' ? (
                      <span className="text-sm font-bold w-16 text-right text-teal-400 font-mono">{r.score != null ? Math.round(r.score) : '—'}</span>
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

export default AdvancedStatsPitching;
