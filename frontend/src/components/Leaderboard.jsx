import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getBackendUrl } from './advancedStatsConstants';
import LeaderboardTable from './LeaderboardTable';

const SEASONS = [2026, 2025, 2024, 2023, 2022, 2021];

const CURRENT_YEAR = new Date().getFullYear();
const getDefaultMinPa = (yr) => yr === CURRENT_YEAR ? 10 : 350;
const getDefaultMinIp = (yr) => yr === CURRENT_YEAR ? 6 : 100;
const getPaRange = (yr) => yr === CURRENT_YEAR
  ? { min: 10, max: 300, step: 10 }
  : { min: 50, max: 600, step: 10 };
const getIpRange = (yr) => yr === CURRENT_YEAR
  ? { min: 1, max: 80, step: 1 }
  : { min: 10, max: 200, step: 5 };

const Leaderboard = () => {
  const { getIdToken } = useAuth();
  const BACKEND_URL = getBackendUrl();

  const [tab, setTab] = useState('batting');
  const [season, setSeason] = useState(2026);
  const [league, setLeague] = useState('MLB');
  const [minPa, setMinPa] = useState(getDefaultMinPa(2026));
  const [minIp, setMinIp] = useState(getDefaultMinIp(2026));
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

  const fetchLeaderboard = async (type, yr, lg, pa, ip) => {
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
        ...(isBatting ? { min_pa: pa } : { min_ip: ip }),
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

  const handleSeasonChange = (yr) => {
    setSeason(yr);
    setMinPa(getDefaultMinPa(yr));
    setMinIp(getDefaultMinIp(yr));
  };

  useEffect(() => {
    fetchLeaderboard(tab, season, league, minPa, minIp);
  }, [tab, season, league, minPa, minIp]);

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
          onChange={(e) => handleSeasonChange(Number(e.target.value))}
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

      {/* Row 3: PA / IP slider */}
      {tab === 'batting' ? (() => {
        const { min, max, step } = getPaRange(season);
        return (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 10, fontFamily: "var(--ff-mono)", color: "var(--ink-4)", whiteSpace: "nowrap" }}>Min PA</span>
            <input
              type="range" min={min} max={max} step={step} value={minPa}
              onChange={(e) => setMinPa(Number(e.target.value))}
              style={{ width: 140, accentColor: "var(--amber)", cursor: "pointer" }}
            />
            <span style={{ fontSize: 10, fontFamily: "var(--ff-mono)", color: "var(--ink-1)", minWidth: 28 }}>{minPa}</span>
          </div>
        );
      })() : (() => {
        const { min, max, step } = getIpRange(season);
        return (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 10, fontFamily: "var(--ff-mono)", color: "var(--ink-4)", whiteSpace: "nowrap" }}>Min IP</span>
            <input
              type="range" min={min} max={max} step={step} value={minIp}
              onChange={(e) => setMinIp(Number(e.target.value))}
              style={{ width: 140, accentColor: "var(--amber)", cursor: "pointer" }}
            />
            <span style={{ fontSize: 10, fontFamily: "var(--ff-mono)", color: "var(--ink-1)", minWidth: 28 }}>{minIp}</span>
          </div>
        );
      })()}

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
