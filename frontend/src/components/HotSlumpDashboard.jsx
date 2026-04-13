import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getBackendUrl } from './advancedStatsConstants';

const METRIC_DEFS = [
  { id: 'ops',      label: 'OPS',       colFn: (p) => `ops_${p}days`,                 fmt: (v) => v?.toFixed(3) ?? '—' },
  { id: 'ba',       label: 'BA',        colFn: (p) => `ba_${p}days`,                  fmt: (v) => v?.toFixed(3) ?? '—' },
  { id: 'barrels',  label: 'Barrel%',   colFn: (p) => `barrels_percentage_${p}days`,  fmt: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
  { id: 'hard_hit', label: 'Hard Hit%', colFn: (p) => `hard_hit_percentage_${p}days`, fmt: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
];

const hotFlagsFn = (p) => [
  { key: `is_red_hot_ba_${p}days`,       label: 'BA' },
  { key: `is_red_hot_ops_${p}days`,      label: 'OPS' },
  { key: `is_red_hot_barrels_${p}days`,  label: 'Barrel' },
  { key: `is_red_hot_hard_hit_${p}days`, label: 'HH' },
];
const slumpFlagsFn = (p) => [
  { key: `is_slump_ba_${p}days`,       label: 'BA' },
  { key: `is_slump_ops_${p}days`,      label: 'OPS' },
  { key: `is_slump_barrels_${p}days`,  label: 'Barrel' },
  { key: `is_slump_hard_hit_${p}days`, label: 'HH' },
];

const RankRow = ({ rank, player, metricDef, period, flagDefs, accentColor }) => {
  const col = metricDef.colFn(period);
  const value = metricDef.fmt(player[col]);
  const activeBadges = flagDefs.filter((f) => player[f.key]);

  return (
    <tr className="border-b border-gray-700 hover:bg-gray-750 transition-colors">
      <td className="py-2 px-3 text-gray-400 text-sm w-8">{rank}</td>
      <td className="py-2 px-3">
        <div className="flex flex-col">
          <span className="text-white text-sm font-medium">{player.batter_name}</span>
          <span className="text-gray-400 text-xs">{player.team ?? '—'}</span>
        </div>
      </td>
      <td className="py-2 px-3 text-right">
        <span className={`text-sm font-semibold ${accentColor}`}>{value}</span>
      </td>
      <td className="py-2 px-3">
        <div className="flex gap-1 flex-wrap justify-end">
          {activeBadges.map((f) => (
            <span
              key={f.key}
              className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                accentColor === 'text-orange-400'
                  ? 'bg-orange-900/50 text-orange-300'
                  : 'bg-blue-900/50 text-blue-300'
              }`}
            >
              {f.label}
            </span>
          ))}
        </div>
      </td>
    </tr>
  );
};

const RankTable = ({ title, emoji, players, metricDef, period, flagDefs, accentColor, isLoading }) => (
  <div className="flex-1 min-w-0">
    <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
      <span>{emoji}</span>
      <span>{title}</span>
      {!isLoading && (
        <span className="ml-1 text-xs text-gray-400 font-normal">({players.length}人)</span>
      )}
    </h3>
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      {isLoading ? (
        <div className="py-8 text-center text-gray-400 text-sm">読み込み中...</div>
      ) : players.length === 0 ? (
        <div className="py-8 text-center text-gray-400 text-sm">該当選手なし</div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="py-2 px-3 text-left text-xs text-gray-400 font-medium w-8">#</th>
              <th className="py-2 px-3 text-left text-xs text-gray-400 font-medium">選手</th>
              <th className="py-2 px-3 text-right text-xs text-gray-400 font-medium">{metricDef.label}</th>
              <th className="py-2 px-3 text-right text-xs text-gray-400 font-medium">該当指標</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p, i) => (
              <RankRow
                key={p.batter_id ?? i}
                rank={i + 1}
                player={p}
                metricDef={metricDef}
                period={period}
                flagDefs={flagDefs}
                accentColor={accentColor}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  </div>
);

const HotSlumpDashboard = () => {
  const { getIdToken } = useAuth();
  const BACKEND_URL = getBackendUrl();

  const [period, setPeriod] = useState(7);
  const [metric, setMetric] = useState('ops');
  const [selectedDate, setSelectedDate] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const getAuthHeaders = async () => {
    const idToken = await getIdToken();
    return {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(idToken ? { Authorization: `Bearer ${idToken}` } : {}),
    };
  };

  // period が変わったら日付リストを再取得
  useEffect(() => {
    const fetchDates = async () => {
      setSelectedDate(null);
      setData(null);
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(
          `${BACKEND_URL}/api/v1/hot-slump/available-dates?period=${period}`,
          { headers }
        );
        if (!res.ok) return;
        const json = await res.json();
        const dates = json.dates ?? [];
        setAvailableDates(dates);
        if (dates.length > 0) setSelectedDate(dates[0]);
      } catch (e) {
        console.error('Failed to fetch available dates:', e);
      }
    };
    fetchDates();
  }, [period]);

  // ランキングデータを取得
  useEffect(() => {
    if (!selectedDate) return;
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const headers = await getAuthHeaders();
        const params = new URLSearchParams({ metric, period, game_date: selectedDate, top_n: 10 });
        const res = await fetch(`${BACKEND_URL}/api/v1/hot-slump/batters?${params}`, { headers });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        setError(e.message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [metric, period, selectedDate]);

  const metricDef = METRIC_DEFS.find((m) => m.id === metric);
  const hotFlags = hotFlagsFn(period);
  const slumpFlags = slumpFlagsFn(period);

  return (
    <div className="p-4 space-y-4">
      {/* ヘッダー行 */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* 期間トグル */}
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
          {[7, 15].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {p}日
            </button>
          ))}
        </div>

        {/* 指標タブ */}
        <div className="flex gap-2">
          {METRIC_DEFS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setMetric(id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                metric === id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* 日付セレクター */}
        <select
          value={selectedDate ?? ''}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="ml-auto bg-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 border border-gray-600 focus:outline-none focus:border-blue-500"
        >
          {availableDates.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* 判定基準の説明 */}
      <p className="text-xs text-gray-500">
        直近{period}日スタッツがシーズン平均比 +20% 以上 → 🔥 Red Hot　／　−20% 以下 → 📉 Slump
      </p>

      {error && (
        <div className="text-red-400 text-sm bg-red-900/20 rounded-lg px-4 py-2">{error}</div>
      )}

      {/* ランキング表（Hot / Slump 横並び） */}
      <div className="flex gap-4 flex-col lg:flex-row">
        <RankTable
          title="Red Hot Top 10"
          emoji="🔥"
          players={data?.hot ?? []}
          metricDef={metricDef}
          period={period}
          flagDefs={hotFlags}
          accentColor="text-orange-400"
          isLoading={isLoading}
        />
        <RankTable
          title="Slump Top 10"
          emoji="📉"
          players={data?.slump ?? []}
          metricDef={metricDef}
          period={period}
          flagDefs={slumpFlags}
          accentColor="text-blue-400"
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};

export default HotSlumpDashboard;
