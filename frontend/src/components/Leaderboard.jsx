import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getBackendUrl } from './advancedStatsConstants';
import LeaderboardTable from './LeaderboardTable';

const SEASONS = [2026, 2025, 2024, 2023, 2022, 2021];

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

  const tabBtn = (active) => ({
    padding: "5px 20px", fontSize: 11,
    fontFamily: "var(--ff-mono)", letterSpacing: "0.06em",
    background: active ? "var(--amber)" : "transparent",
    color: active ? "var(--bg-0)" : "var(--ink-3)",
    border: `1px solid ${active ? "var(--amber)" : "var(--rule)"}`,
    fontWeight: active ? 600 : 400,
    transition: "all .12s",
  });

  const smTabBtn = (active) => ({
    padding: "4px 12px", fontSize: 10,
    fontFamily: "var(--ff-mono)", letterSpacing: "0.06em",
    background: active ? "var(--bg-3)" : "transparent",
    color: active ? "var(--ink-0)" : "var(--ink-4)",
    border: `1px solid ${active ? "var(--rule-hi)" : "var(--rule)"}`,
    fontWeight: active ? 600 : 400,
    transition: "all .12s",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Row 1: 打者 / 投手 + season */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 4 }}>
          {[
            { id: 'batting', label: '打者' },
            { id: 'pitching', label: '投手' },
          ].map(({ id, label }) => (
            <button key={id} onClick={() => setTab(id)} style={tabBtn(tab === id)}>
              {label}
            </button>
          ))}
        </div>

        <select
          value={season}
          onChange={(e) => setSeason(Number(e.target.value))}
          style={{
            background: "var(--bg-1)", color: "var(--ink-1)",
            border: "1px solid var(--rule)", fontSize: 11,
            padding: "5px 10px", fontFamily: "var(--ff-mono)",
          }}
        >
          {SEASONS.map((yr) => (
            <option key={yr} value={yr}>{yr}年</option>
          ))}
        </select>
      </div>

      {/* Row 2: MLB / NL / AL */}
      <div style={{ display: "flex", gap: 4 }}>
        {['MLB', 'NL', 'AL'].map((lg) => (
          <button key={lg} onClick={() => setLeague(lg)} style={smTabBtn(league === lg)}>
            {lg}
          </button>
        ))}
      </div>

      {/* Table */}
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
