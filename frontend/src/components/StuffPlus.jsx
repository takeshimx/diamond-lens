import React, { useState, useEffect, useRef } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { Target, Search, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const StuffPlus = () => {
  const { getIdToken } = useAuth();
  // サブビュー切替
  const [view, setView] = useState('rankings'); // 'rankings' | 'detail' | 'compare' | 'trend'

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

  // Shared
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Backend URL detection (既存パターン準拠)
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

  // 認証ヘッダー取得
  const getAuthHeaders = async () => {
    const idToken = await getIdToken();
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
    };
  };

  // ----------------------------------------------------------
  // 選手名検索 API
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

  // Detail 検索デバウンス
  useEffect(() => {
    if (detailSearchQuery.length < 2) { setDetailSuggestions([]); return; }
    const timer = setTimeout(async () => {
      const results = await searchPitchers(detailSearchQuery, detailSeason);
      setDetailSuggestions(results);
      setDetailShowSuggestions(results.length > 0);
    }, 300);
    return () => clearTimeout(timer);
  }, [detailSearchQuery, detailSeason]);

  // Compare 検索デバウンス
  useEffect(() => {
    if (compareSearchQuery.length < 2) { setCompareSuggestions([]); return; }
    const timer = setTimeout(async () => {
      const results = await searchPitchers(compareSearchQuery, compareSeason);
      setCompareSuggestions(results);
      setCompareShowSuggestions(results.length > 0);
    }, 300);
    return () => clearTimeout(timer);
  }, [compareSearchQuery, compareSeason]);

  // Trend 検索デバウンス
  useEffect(() => {
    if (trendSearchQuery.length < 2) { setTrendSuggestions([]); return; }
    const timer = setTimeout(async () => {
      const results = await searchPitchers(trendSearchQuery, trendSeason);
      setTrendSuggestions(results);
      setTrendShowSuggestions(results.length > 0);
    }, 300);
    return () => clearTimeout(timer);
  }, [trendSearchQuery, trendSeason]);

  // クリック外で候補を閉じる
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (detailSearchRef.current && !detailSearchRef.current.contains(e.target)) {
        setDetailShowSuggestions(false);
      }
      if (compareSearchRef.current && !compareSearchRef.current.contains(e.target)) {
        setCompareShowSuggestions(false);
      }
      if (trendSearchRef.current && !trendSearchRef.current.contains(e.target)) {
        setTrendShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ----------------------------------------------------------
  // スコアに応じた色
  // ----------------------------------------------------------
  const getScoreColor = (score) => {
    if (score >= 120) return 'text-green-400';
    if (score >= 110) return 'text-emerald-400';
    if (score >= 90) return 'text-yellow-400';
    if (score >= 80) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreBgColor = (score) => {
    if (score >= 120) return 'bg-green-500/20 border-green-500/30';
    if (score >= 110) return 'bg-emerald-500/20 border-emerald-500/30';
    if (score >= 90) return 'bg-yellow-500/20 border-yellow-500/30';
    if (score >= 80) return 'bg-orange-500/20 border-orange-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  const getBarColor = (score) => {
    if (score >= 120) return '#22c55e';
    if (score >= 110) return '#10b981';
    if (score >= 90) return '#eab308';
    if (score >= 80) return '#f97316';
    return '#ef4444';
  };

  // ----------------------------------------------------------
  // Rankings 取得
  // ----------------------------------------------------------
  const fetchRankings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        model_type: rankingsModelType,
        season: rankingsSeason,
        limit: rankingsLimit,
        offset: rankingsOffset,
        sort_order: rankingsSortOrder,
        min_pitches: rankingsMinPitches,
      });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/rankings?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      const filtered = (data.rankings || []).filter(r => r.pitch_name !== 'Pitch Out');
      setRankings(filtered);
      setRankingsTotal(data.total || 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (view === 'rankings') {
      fetchRankings();
    }
  }, [view, rankingsModelType, rankingsSeason, rankingsSortOrder, rankingsOffset, rankingsMinPitches]);

  // ----------------------------------------------------------
  // Pitcher Detail 取得
  // ----------------------------------------------------------
  const fetchPitcherDetail = async () => {
    if (!detailPitcherId) return;
    setIsLoading(true);
    setError(null);
    setDetailResult(null);
    try {
      const params = new URLSearchParams({
        model_type: detailModelType,
        season: detailSeason,
      });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/pitcher/${detailPitcherId}?${params}`, { headers });
      if (!res.ok) {
        if (res.status === 404) throw new Error('投手が見つかりませんでした');
        if (res.status === 503) throw new Error('モデルが利用できません');
        throw new Error(`API error: ${res.status}`);
      }
      const data = await res.json();
      if (data.pitches) {
        data.pitches = data.pitches.filter(p => p.pitch_name !== 'Pitch Out');
      }
      setDetailResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // detailModelType 変更時に自動再取得
  useEffect(() => {
    if (view === 'detail' && detailPitcherId) {
      fetchPitcherDetail();
    }
  }, [detailModelType]);

  // ----------------------------------------------------------
  // Compare 取得
  // ----------------------------------------------------------
  const fetchCompare = async () => {
    if (!comparePitcherId) return;
    setIsLoading(true);
    setError(null);
    setCompareResult(null);
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
      if (data.comparison) {
        data.comparison = data.comparison.filter(c => c.pitch_name !== 'Pitch Out');
      }
      setCompareResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // ----------------------------------------------------------
  // Monthly Trend 取得
  // ----------------------------------------------------------
  const fetchTrend = async () => {
    if (!trendPitcherId) return;
    setIsLoading(true);
    setError(null);
    setTrendResult(null);
    try {
      const params = new URLSearchParams({
        model_type: trendModelType,
        season: trendSeason,
      });
      const headers = await getAuthHeaders();
      const res = await fetch(`${BACKEND_URL}/api/v1/stuff-plus/pitcher/${trendPitcherId}/trend?${params}`, { headers });
      if (!res.ok) {
        if (res.status === 404) throw new Error('投手が見つかりませんでした');
        if (res.status === 503) throw new Error('モデルが利用できません');
        throw new Error(`API error: ${res.status}`);
      }
      setTrendResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // trendModelType 変更時に自動再取得
  useEffect(() => {
    if (view === 'trend' && trendPitcherId) {
      fetchTrend();
    }
  }, [trendModelType]);

  // ----------------------------------------------------------
  // Rankings ビュー内でクリックしてDetail遷移
  // ----------------------------------------------------------
  const goToDetail = (pitcherId, playerName) => {
    setDetailPitcherId(String(pitcherId));
    setDetailSearchQuery(playerName || '');
    setDetailShowSuggestions(false);
    setView('detail');
  };

  // ----------------------------------------------------------
  // カスタム Tooltip
  // ----------------------------------------------------------
  const DetailChartTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
        <p className="text-white font-medium">{d.pitch_name}</p>
        <p className={`text-sm ${getScoreColor(d.score)}`}>Score: {d.score}</p>
        <p className="text-gray-300 text-sm">投球数: {d.pitch_count}</p>
        <p className="text-gray-300 text-sm">平均球速: {d.avg_velo} mph</p>
        <p className="text-gray-300 text-sm">平均回転数: {d.avg_spin} rpm</p>
      </div>
    );
  };

  const CompareChartTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
        <p className="text-white font-medium">{d.pitch_name}</p>
        {d.stuff_plus != null && <p className="text-blue-400 text-sm">Stuff+: {d.stuff_plus}</p>}
        {d.pitching_plus != null && <p className="text-purple-400 text-sm">Pitching+: {d.pitching_plus}</p>}
        {d.pitching_plus_plus != null && <p className="text-green-400 text-sm">Pitching++: {d.pitching_plus_plus}</p>}
        {d.gap != null && <p className="text-gray-300 text-sm">Gap: {d.gap > 0 ? '+' : ''}{d.gap}</p>}
        <p className="text-gray-300 text-sm">投球数: {d.pitch_count}</p>
      </div>
    );
  };

  // ----------------------------------------------------------
  // プロファイルバッジの色
  // ----------------------------------------------------------
  const getProfileStyle = (profile) => {
    switch (profile) {
      case 'stuff_dominant':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'command_dominant':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    }
  };

  // ==========================================================
  // Rankings ビュー
  // ==========================================================
  const RankingsView = () => (
    <div className="space-y-4">
      {/* コントロール */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Model Type 切替 */}
        <div className="flex rounded-lg overflow-hidden border border-gray-600">
          <button
            onClick={() => { setRankingsModelType('stuff_plus'); setRankingsOffset(0); }}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              rankingsModelType === 'stuff_plus'
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(59,130,246,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Stuff+
          </button>
          <button
            onClick={() => { setRankingsModelType('pitching_plus'); setRankingsOffset(0); }}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              rankingsModelType === 'pitching_plus'
                ? 'bg-purple-600 text-white shadow-[0_0_12px_rgba(168,85,247,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Pitching+
          </button>
          <button
            onClick={() => { setRankingsModelType('pitching_plus_plus'); setRankingsOffset(0); }}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              rankingsModelType === 'pitching_plus_plus'
                ? 'bg-green-600 text-white shadow-[0_0_12px_rgba(34,197,94,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Pitching++
          </button>
        </div>

        {/* Season */}
        <select
          value={rankingsSeason}
          onChange={(e) => { setRankingsSeason(Number(e.target.value)); setRankingsOffset(0); }}
          className="bg-gray-700 text-white border border-gray-600 rounded-lg px-3 py-1.5 text-sm"
        >
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>

        {/* Sort */}
        <button
          onClick={() => {
            setRankingsSortOrder(prev => prev === 'desc' ? 'asc' : 'desc');
            setRankingsOffset(0);
          }}
          className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 text-gray-300 border border-gray-600 rounded-lg text-sm hover:bg-gray-600 transition-colors"
        >
          <ArrowUpDown className="w-3.5 h-3.5" />
          {rankingsSortOrder === 'desc' ? 'High → Low' : 'Low → High'}
        </button>

        {/* Min Pitches */}
        <div className="flex items-center gap-1.5">
          <label className="text-xs text-gray-400 whitespace-nowrap">Min投球数</label>
          <input
            type="number"
            value={rankingsMinPitches}
            onChange={(e) => { setRankingsMinPitches(Number(e.target.value)); setRankingsOffset(0); }}
            min={0}
            max={5000}
            step={50}
            className="bg-gray-700 text-white border border-gray-600 rounded-lg px-2 py-1.5 text-sm w-20"
          />
        </div>
      </div>

      {/* テーブル */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="text-left text-gray-400 py-2 px-3">#</th>
              <th className="text-left text-gray-400 py-2 px-3">Player</th>
              <th className="text-left text-gray-400 py-2 px-3">Team</th>
              <th className="text-center text-gray-400 py-2 px-3">Hand</th>
              <th className="text-left text-gray-400 py-2 px-3">Pitch</th>
              <th className="text-right text-gray-400 py-2 px-3">Score</th>
              <th className="text-right text-gray-400 py-2 px-3">Count</th>
              <th className="text-right text-gray-400 py-2 px-3">Velo <span className="text-gray-500 font-normal">(mph)</span></th>
              <th className="text-right text-gray-400 py-2 px-3">Spin <span className="text-gray-500 font-normal">(rpm)</span></th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((r, i) => (
              <tr
                key={`${r.pitcher_id}-${r.pitch_name}-${i}`}
                className="border-b border-gray-700/50 hover:bg-gray-700/30 cursor-pointer transition-colors"
                onClick={() => goToDetail(r.pitcher_id, r.player_name)}
              >
                <td className="py-2 px-3 text-gray-500">{rankingsOffset + i + 1}</td>
                <td className="py-2 px-3 text-white font-medium">{r.player_name}</td>
                <td className="py-2 px-3 text-gray-400 text-xs">{r.team}</td>
                <td className="py-2 px-3 text-center text-gray-400 text-xs">{r.hand === 'R' ? 'RHP' : r.hand === 'L' ? 'LHP' : r.hand}</td>
                <td className="py-2 px-3 text-gray-300">{r.pitch_name}</td>
                <td className="py-2 px-3 text-right">
                  <span className={`font-bold ${getScoreColor(r.score)}`}>{r.score}</span>
                </td>
                <td className="py-2 px-3 text-right text-gray-300">{r.pitch_count}</td>
                <td className="py-2 px-3 text-right text-gray-300">{r.avg_velo}</td>
                <td className="py-2 px-3 text-right text-gray-300">{r.avg_spin}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ページネーション */}
      {rankingsTotal > 0 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-sm text-gray-400">
            {rankingsOffset + 1} - {Math.min(rankingsOffset + rankingsLimit, rankingsTotal)} / {rankingsTotal}
          </span>
          <div className="flex gap-2">
            <button
              disabled={rankingsOffset === 0}
              onClick={() => setRankingsOffset(Math.max(0, rankingsOffset - rankingsLimit))}
              className="p-1.5 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={rankingsOffset + rankingsLimit >= rankingsTotal}
              onClick={() => setRankingsOffset(rankingsOffset + rankingsLimit)}
              className="p-1.5 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );

  // ==========================================================
  // Detail ビュー
  // ==========================================================
  const DetailView = () => (
    <div className="space-y-4">
      {/* 入力コントロール */}
      <div className="flex flex-wrap gap-3 items-end">
        {/* 選手名検索 */}
        <div className="relative" ref={detailSearchRef}>
          <label className="block text-xs text-gray-400 mb-1">投手名</label>
          <div className="flex items-center">
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-gray-500" />
            <input
              type="text"
              value={detailSearchQuery}
              onChange={(e) => {
                setDetailSearchQuery(e.target.value);
                setDetailPitcherId('');
                setDetailShowSuggestions(true);
              }}
              placeholder="e.g. Yamamoto"
              className="bg-gray-700 text-white border border-gray-600 rounded-lg pl-8 pr-3 py-1.5 text-sm w-52"
            />
          </div>
          {/* オートコンプリートドロップダウン */}
          {detailShowSuggestions && detailSuggestions.length > 0 && (
            <div className="absolute z-50 mt-1 w-72 bg-gray-800 border border-gray-600 rounded-lg shadow-xl max-h-60 overflow-y-auto">
              {detailSuggestions.map((s) => (
                <button
                  key={s.pitcher_id}
                  onClick={() => {
                    setDetailPitcherId(String(s.pitcher_id));
                    setDetailSearchQuery(s.player_name);
                    setDetailShowSuggestions(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-700 transition-colors flex items-center justify-between"
                >
                  <span className="text-white text-sm font-medium">{s.player_name}</span>
                  <span className="text-gray-500 text-xs">{s.team} / {s.hand === 'R' ? 'RHP' : s.hand === 'L' ? 'LHP' : s.hand}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex rounded-lg overflow-hidden border border-gray-600">
          <button
            onClick={() => setDetailModelType('stuff_plus')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              detailModelType === 'stuff_plus'
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(59,130,246,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Stuff+
          </button>
          <button
            onClick={() => setDetailModelType('pitching_plus')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              detailModelType === 'pitching_plus'
                ? 'bg-purple-600 text-white shadow-[0_0_12px_rgba(168,85,247,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Pitching+
          </button>
          <button
            onClick={() => setDetailModelType('pitching_plus_plus')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              detailModelType === 'pitching_plus_plus'
                ? 'bg-green-600 text-white shadow-[0_0_12px_rgba(34,197,94,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Pitching++
          </button>
        </div>

        <select
          value={detailSeason}
          onChange={(e) => setDetailSeason(Number(e.target.value))}
          className="bg-gray-700 text-white border border-gray-600 rounded-lg px-3 py-1.5 text-sm"
        >
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>

        <button
          onClick={fetchPitcherDetail}
          disabled={!detailPitcherId || isLoading}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Search className="w-3.5 h-3.5" />
          検索
        </button>
      </div>

      {/* 結果 */}
      {detailResult && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-white">{detailResult.player_name}</h3>
            <span className="text-sm text-gray-400">
              {detailResult.model_type === 'stuff_plus' ? 'Stuff+' : detailResult.model_type === 'pitching_plus' ? 'Pitching+' : 'Pitching++'} / {detailResult.season}
            </span>
          </div>

          {/* バーチャート */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={detailResult.pitches} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="pitch_name" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} domain={[60, 160]} />
                <Tooltip content={<DetailChartTooltip />} />
                <ReferenceLine y={100} stroke="#6b7280" strokeDasharray="4 4" label={{ value: 'Avg (100)', fill: '#6b7280', fontSize: 11 }} />
                <Bar
                  dataKey="score"
                  radius={[4, 4, 0, 0]}
                  fill="#3b82f6"
                  label={{ position: 'top', fill: '#d1d5db', fontSize: 11 }}
                >
                  {detailResult.pitches.map((entry, index) => (
                    <rect key={index} fill={getBarColor(entry.score)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* 詳細テーブル */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-3">Pitch</th>
                  <th className="text-right text-gray-400 py-2 px-3">Score</th>
                  <th className="text-right text-gray-400 py-2 px-3">Count</th>
                  <th className="text-right text-gray-400 py-2 px-3">Velo <span className="text-gray-500 font-normal">(mph)</span></th>
                  <th className="text-right text-gray-400 py-2 px-3">Spin <span className="text-gray-500 font-normal">(rpm)</span></th>
                  <th className="text-right text-gray-400 py-2 px-3">Pred RE</th>
                  <th className="text-right text-gray-400 py-2 px-3">Actual RE</th>
                  <th className="text-center text-gray-400 py-2 px-3">Sample</th>
                </tr>
              </thead>
              <tbody>
                {detailResult.pitches.map((p, i) => (
                  <tr key={i} className="border-b border-gray-700/50">
                    <td className="py-2 px-3 text-white font-medium">{p.pitch_name}</td>
                    <td className="py-2 px-3 text-right">
                      <span className={`font-bold ${getScoreColor(p.score)}`}>{p.score}</span>
                    </td>
                    <td className="py-2 px-3 text-right text-gray-300">{p.pitch_count}</td>
                    <td className="py-2 px-3 text-right text-gray-300">{p.avg_velo}</td>
                    <td className="py-2 px-3 text-right text-gray-300">{p.avg_spin}</td>
                    <td className="py-2 px-3 text-right text-gray-300">{p.mean_pred_run_exp.toFixed(4)}</td>
                    <td className="py-2 px-3 text-right text-gray-300">{p.actual_run_exp.toFixed(4)}</td>
                    <td className="py-2 px-3 text-center">
                      {p.sufficient_sample
                        ? <span className="text-green-400 text-xs">OK</span>
                        : <span className="text-yellow-400 text-xs">Low</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-gray-500 mt-2 px-3">
              RE = Run Expectancy (得点期待値の変化量)。負値ほど投手有利。Pred RE はモデル予測値、Actual RE は実際の結果。Sample は最低投球数を満たしているかの判定。
            </p>
          </div>
        </div>
      )}
    </div>
  );

  // ==========================================================
  // Compare ビュー
  // ==========================================================
  const CompareView = () => (
    <div className="space-y-4">
      {/* 入力コントロール */}
      <div className="flex flex-wrap gap-3 items-end">
        {/* 選手名検索 */}
        <div className="relative" ref={compareSearchRef}>
          <label className="block text-xs text-gray-400 mb-1">投手名</label>
          <div className="flex items-center">
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-gray-500" />
            <input
              type="text"
              value={compareSearchQuery}
              onChange={(e) => {
                setCompareSearchQuery(e.target.value);
                setComparePitcherId('');
                setCompareShowSuggestions(true);
              }}
              placeholder="e.g. Yamamoto"
              className="bg-gray-700 text-white border border-gray-600 rounded-lg pl-8 pr-3 py-1.5 text-sm w-52"
            />
          </div>
          {/* オートコンプリートドロップダウン */}
          {compareShowSuggestions && compareSuggestions.length > 0 && (
            <div className="absolute z-50 mt-1 w-72 bg-gray-800 border border-gray-600 rounded-lg shadow-xl max-h-60 overflow-y-auto">
              {compareSuggestions.map((s) => (
                <button
                  key={s.pitcher_id}
                  onClick={() => {
                    setComparePitcherId(String(s.pitcher_id));
                    setCompareSearchQuery(s.player_name);
                    setCompareShowSuggestions(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-700 transition-colors flex items-center justify-between"
                >
                  <span className="text-white text-sm font-medium">{s.player_name}</span>
                  <span className="text-gray-500 text-xs">{s.team} / {s.hand === 'R' ? 'RHP' : s.hand === 'L' ? 'LHP' : s.hand}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <select
          value={compareSeason}
          onChange={(e) => setCompareSeason(Number(e.target.value))}
          className="bg-gray-700 text-white border border-gray-600 rounded-lg px-3 py-1.5 text-sm"
        >
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>

        <button
          onClick={fetchCompare}
          disabled={!comparePitcherId || isLoading}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Search className="w-3.5 h-3.5" />
          比較
        </button>
      </div>

      {/* 結果 */}
      {compareResult && (
        <div className="space-y-4">
          {/* ヘッダー + プロファイル */}
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-lg font-bold text-white">{compareResult.player_name}</h3>
            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getProfileStyle(compareResult.profile)}`}>
              {compareResult.profile_desc}
            </span>
            <span className="text-sm text-gray-400">
              Avg Gap: <span className={compareResult.avg_gap > 0 ? 'text-blue-400' : compareResult.avg_gap < 0 ? 'text-purple-400' : 'text-gray-300'}>
                {compareResult.avg_gap > 0 ? '+' : ''}{compareResult.avg_gap}
              </span>
            </span>
          </div>

          {/* Grouped Bar Chart */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={compareResult.comparison} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="pitch_name" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} domain={[60, 160]} />
                <Tooltip content={<CompareChartTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
                <ReferenceLine y={100} stroke="#6b7280" strokeDasharray="4 4" />
                <Bar dataKey="stuff_plus" name="Stuff+" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="pitching_plus" name="Pitching+" fill="#a855f7" radius={[4, 4, 0, 0]} />
                <Bar dataKey="pitching_plus_plus" name="Pitching++" fill="#22c55e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* 比較テーブル */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-3">Pitch</th>
                  <th className="text-right text-blue-400 py-2 px-3">Stuff+</th>
                  <th className="text-right text-purple-400 py-2 px-3">Pitching+</th>
                  <th className="text-right text-green-400 py-2 px-3">Pitching++</th>
                  <th className="text-right text-gray-400 py-2 px-3">Gap</th>
                  <th className="text-right text-gray-400 py-2 px-3">Count</th>
                  <th className="text-right text-gray-400 py-2 px-3">Velo <span className="text-gray-500 font-normal">(mph)</span></th>
                </tr>
              </thead>
              <tbody>
                {compareResult.comparison.map((c, i) => (
                  <tr key={i} className="border-b border-gray-700/50">
                    <td className="py-2 px-3 text-white font-medium">{c.pitch_name}</td>
                    <td className="py-2 px-3 text-right">
                      {c.stuff_plus != null
                        ? <span className={`font-bold ${getScoreColor(c.stuff_plus)}`}>{c.stuff_plus}</span>
                        : <span className="text-gray-500">-</span>
                      }
                    </td>
                    <td className="py-2 px-3 text-right">
                      {c.pitching_plus != null
                        ? <span className={`font-bold ${getScoreColor(c.pitching_plus)}`}>{c.pitching_plus}</span>
                        : <span className="text-gray-500">-</span>
                      }
                    </td>
                    <td className="py-2 px-3 text-right">
                      {c.pitching_plus_plus != null
                        ? <span className={`font-bold ${getScoreColor(c.pitching_plus_plus)}`}>{c.pitching_plus_plus}</span>
                        : <span className="text-gray-500">-</span>
                      }
                    </td>
                    <td className="py-2 px-3 text-right">
                      {c.gap != null
                        ? <span className={c.gap > 0 ? 'text-blue-400' : c.gap < 0 ? 'text-purple-400' : 'text-gray-300'}>
                            {c.gap > 0 ? '+' : ''}{c.gap}
                          </span>
                        : <span className="text-gray-500">-</span>
                      }
                    </td>
                    <td className="py-2 px-3 text-right text-gray-300">{c.pitch_count}</td>
                    <td className="py-2 px-3 text-right text-gray-300">{c.avg_velo}</td>
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
  // Trend ビュー（月別推移）
  // ==========================================================
  const MONTH_LABELS = { 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov' };
  const PITCH_COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#a855f7', '#ec4899', '#06b6d4', '#f97316'];

  const TrendChartTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    const monthEntry = trendResult?.monthly?.find(m => m.month === label);
    return (
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
        <p className="text-white font-medium mb-1">{MONTH_LABELS[label] || `Month ${label}`}</p>
        {payload.map((p, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="text-gray-300">{p.name}:</span>
            <span className={`font-bold ${getScoreColor(p.value)}`}>{p.value}</span>
            {monthEntry && monthEntry[`${p.name}_count`] != null && (
              <span className="text-gray-500 text-xs">({monthEntry[`${p.name}_count`]}球)</span>
            )}
          </div>
        ))}
      </div>
    );
  };

  const TrendView = () => (
    <div className="space-y-4">
      {/* 入力コントロール */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="relative" ref={trendSearchRef}>
          <label className="block text-xs text-gray-400 mb-1">投手名</label>
          <div className="flex items-center">
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-gray-500" />
            <input
              type="text"
              value={trendSearchQuery}
              onChange={(e) => {
                setTrendSearchQuery(e.target.value);
                setTrendPitcherId('');
                setTrendShowSuggestions(true);
              }}
              placeholder="e.g. Ohtani"
              className="bg-gray-700 text-white border border-gray-600 rounded-lg pl-8 pr-3 py-1.5 text-sm w-52"
            />
          </div>
          {trendShowSuggestions && trendSuggestions.length > 0 && (
            <div className="absolute z-50 mt-1 w-72 bg-gray-800 border border-gray-600 rounded-lg shadow-xl max-h-60 overflow-y-auto">
              {trendSuggestions.map((s) => (
                <button
                  key={s.pitcher_id}
                  onClick={() => {
                    setTrendPitcherId(String(s.pitcher_id));
                    setTrendSearchQuery(s.player_name);
                    setTrendShowSuggestions(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-700 transition-colors flex items-center justify-between"
                >
                  <span className="text-white text-sm font-medium">{s.player_name}</span>
                  <span className="text-gray-500 text-xs">{s.team} / {s.hand === 'R' ? 'RHP' : s.hand === 'L' ? 'LHP' : s.hand}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex rounded-lg overflow-hidden border border-gray-600">
          <button
            onClick={() => setTrendModelType('stuff_plus')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              trendModelType === 'stuff_plus'
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(59,130,246,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Stuff+
          </button>
          <button
            onClick={() => setTrendModelType('pitching_plus')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              trendModelType === 'pitching_plus'
                ? 'bg-purple-600 text-white shadow-[0_0_12px_rgba(168,85,247,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Pitching+
          </button>
          <button
            onClick={() => setTrendModelType('pitching_plus_plus')}
            className={`px-3 py-1.5 text-sm font-medium transition-all ${
              trendModelType === 'pitching_plus_plus'
                ? 'bg-green-600 text-white shadow-[0_0_12px_rgba(34,197,94,0.5)]'
                : 'bg-gray-700 text-gray-500 hover:bg-gray-600 hover:text-gray-300'
            }`}
          >
            Pitching++
          </button>
        </div>

        <select
          value={trendSeason}
          onChange={(e) => setTrendSeason(Number(e.target.value))}
          className="bg-gray-700 text-white border border-gray-600 rounded-lg px-3 py-1.5 text-sm"
        >
          {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>

        <button
          onClick={fetchTrend}
          disabled={!trendPitcherId || isLoading}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Search className="w-3.5 h-3.5" />
          推移表示
        </button>
      </div>

      {/* 結果 */}
      {trendResult && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-white">{trendResult.player_name}</h3>
            <span className="text-sm text-gray-400">
              {trendModelType === 'stuff_plus' ? 'Stuff+' : trendModelType === 'pitching_plus' ? 'Pitching+' : 'Pitching++'} / {trendResult.season} 月別推移
            </span>
          </div>

          {/* LineChart */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={trendResult.monthly} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="month"
                  stroke="#9ca3af"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(m) => MONTH_LABELS[m] || m}
                />
                <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} domain={[60, 160]} />
                <Tooltip content={<TrendChartTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
                <ReferenceLine y={100} stroke="#6b7280" strokeDasharray="4 4" label={{ value: 'Avg (100)', fill: '#6b7280', fontSize: 11 }} />
                {trendResult.pitch_names.map((pn, i) => (
                  <Line
                    key={pn}
                    type="monotone"
                    dataKey={pn}
                    name={pn}
                    stroke={PITCH_COLORS[i % PITCH_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 月別テーブル */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 py-2 px-3">Month</th>
                  {trendResult.pitch_names.map((pn, i) => (
                    <th key={pn} className="text-right py-2 px-3" style={{ color: PITCH_COLORS[i % PITCH_COLORS.length] }}>{pn}</th>
                  ))}
                  <th className="text-right text-gray-400 py-2 px-3">Total</th>
                </tr>
              </thead>
              <tbody>
                {trendResult.monthly.map((m) => (
                  <tr key={m.month} className="border-b border-gray-700/50">
                    <td className="py-2 px-3 text-white font-medium">{MONTH_LABELS[m.month] || m.month}</td>
                    {trendResult.pitch_names.map((pn) => (
                      <td key={pn} className="py-2 px-3 text-right">
                        {m[pn] != null
                          ? <span className={`font-bold ${getScoreColor(m[pn])}`}>{m[pn]}</span>
                          : <span className="text-gray-500">-</span>
                        }
                        {m[`${pn}_count`] != null && (
                          <span className="text-gray-500 text-xs ml-1">({m[`${pn}_count`]})</span>
                        )}
                      </td>
                    ))}
                    <td className="py-2 px-3 text-right text-gray-300">{m.total_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-gray-500 mt-2 px-3">
              括弧内はその月の投球数。サンプルが少ない月はスコアの信頼度が低い点に注意。
            </p>
          </div>
        </div>
      )}
    </div>
  );

  // ==========================================================
  // メインレンダリング
  // ==========================================================
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-600/20 rounded-lg">
          <Target className="w-6 h-6 text-blue-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Stuff+ / Pitching+ / Pitching++</h2>
          <p className="text-sm text-gray-400">XGBoostベースの球質・投球評価モデル</p>
        </div>
      </div>

      {/* モデル定義 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg px-4 py-3">
          <span className="text-blue-400 font-semibold text-sm">Stuff+</span>
          <p className="text-xs text-gray-400 mt-1">球速・回転・変化量・リリースなど物理的な球質のみで評価。100 = MLB平均、15pt = 1SD。</p>
        </div>
        <div className="bg-purple-500/5 border border-purple-500/20 rounded-lg px-4 py-3">
          <span className="text-purple-400 font-semibold text-sm">Pitching+</span>
          <p className="text-xs text-gray-400 mt-1">Stuff+ に投球コースを追加。「良い球を、良い場所に投げられるか」を評価。コーナーワークに優れた投手が高スコア。</p>
        </div>
        <div className="bg-green-500/5 border border-green-500/20 rounded-lg px-4 py-3">
          <span className="text-green-400 font-semibold text-sm">Pitching++</span>
          <p className="text-xs text-gray-400 mt-1">Pitching+ に前球との球速差・リリース差・カウント状況を追加。「配球の組み立てで打者を翻弄できるか」を評価。</p>
        </div>
      </div>

      {/* サブビュータブ */}
      <div className="flex gap-1 bg-gray-800 rounded-lg p-1 border border-gray-700 w-fit">
        {[
          { key: 'rankings', label: 'ランキング' },
          { key: 'detail', label: '投手詳細' },
          { key: 'trend', label: '月別推移' },
          { key: 'compare', label: 'モデル比較' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => { setView(tab.key); setError(null); }}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              view === tab.key
                ? 'bg-gray-600 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-400">読み込み中...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* コンテンツ */}
      {!isLoading && !error && (
        <>
          {view === 'rankings' && RankingsView()}
          {view === 'detail' && DetailView()}
          {view === 'trend' && TrendView()}
          {view === 'compare' && CompareView()}
        </>
      )}
    </div>
  );
};

export default StuffPlus;
