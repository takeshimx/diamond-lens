import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getBackendUrl } from './advancedStatsConstants';
import LeaderboardTable from './LeaderboardTable';

const SEASONS = [2026, 2025, 2024, 2023, 2022, 2021];

// シーズン序盤は閾値を低めに設定
const getMinPa = (yr) => yr === new Date().getFullYear() ? 10 : 350;
const getMinIp = (yr) => yr === new Date().getFullYear() ? 6 : 100;

const Leaderboard = () => {
  const { getIdToken } = useAuth();
  const BACKEND_URL = getBackendUrl();

  const [tab, setTab] = useState('batting');
  const [season, setSeason] = useState(2025);
  const [league, setLeague] = useState('MLB');
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const getAuthHeaders = async () => {
    const idToken = await getIdToken();
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
    };
  };

  const fetchLeaderboard = async (type, yr, lg) => {
    setIsLoading(true);
    setError(null);
    setData(null);
    try {
      const headers = await getAuthHeaders();
      const isBatting = type === 'batting';
      const params = new URLSearchParams({
        season: yr,
        league: lg,
        metric_order: isBatting ? 'ops' : 'era',
        ...(isBatting ? { min_pa: getMinPa(yr) } : { min_ip: getMinIp(yr) }),
      });
      const res = await fetch(`${BACKEND_URL}/api/v1/leaderboards/${type}?${params}`, { headers });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard(tab, season, league);
  }, [tab, season, league]);

  const category = {
    id: tab === 'batting' ? 'batting_leaderboard' : 'pitching_leaderboard',
  };
  const metricOrder = tab === 'batting' ? 'ops' : 'era';

  return (
    <div className="space-y-4">
      {/* 1行目: 打者/投手 + シーズン */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex gap-2">
          {[
            { id: 'batting', label: '打者' },
            { id: 'pitching', label: '投手' },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                tab === id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <select
          value={season}
          onChange={(e) => setSeason(Number(e.target.value))}
          className="px-3 py-2 rounded-lg text-sm bg-gray-700 text-white border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {SEASONS.map((yr) => (
            <option key={yr} value={yr}>{yr}年</option>
          ))}
        </select>
      </div>

      {/* 2行目: MLB / NL / AL */}
      <div className="flex gap-2">
        {['MLB', 'NL', 'AL'].map((lg) => (
          <button
            key={lg}
            onClick={() => setLeague(lg)}
            className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              league === lg
                ? 'bg-gray-200 dark:bg-gray-500 text-gray-900 dark:text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            {lg}
          </button>
        ))}
      </div>

      {/* テーブル */}
      <LeaderboardTable
        data={data}
        category={category}
        metricOrder={metricOrder}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
};

export default Leaderboard;
