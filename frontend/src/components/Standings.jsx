import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import Icon from './layout/Icon.jsx';

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

const AL_ID = 103;
const NL_ID = 104;

const pctColor = (pct) => {
  const v = parseFloat(pct);
  if (isNaN(v)) return 'var(--ink-3)';
  if (v >= 0.600) return 'var(--pos)';
  if (v >= 0.500) return 'var(--ink-1)';
  return 'var(--neg)';
};

const streakColor = (code) => {
  if (!code || code === '-') return 'var(--ink-3)';
  if (code.startsWith('W')) return 'var(--pos)';
  return 'var(--neg)';
};

const TH_COLS = ["TEAM", "W", "L", "PCT", "GB", "HOME", "AWAY", "L10", "STREAK"];

const DivisionTable = ({ division }) => (
  <div style={{ marginBottom: 20 }}>
    <div className="rule-b" style={{ padding: "5px 12px", background: "var(--bg-1)" }}>
      <span className="h-label" style={{ fontSize: 10, color: "var(--ink-2)" }}>
        {division.division_name}
      </span>
    </div>
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "var(--bg-1)" }}>
            {TH_COLS.map(h => (
              <th key={h} style={{
                padding: "6px 8px",
                fontFamily: "var(--ff-mono)",
                fontWeight: 600,
                fontSize: 10,
                letterSpacing: "0.08em",
                color: "var(--ink-3)",
                textAlign: h === "TEAM" ? "left" : "center",
                borderBottom: "1px solid var(--rule)",
                whiteSpace: "nowrap",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {division.teams.map((team, idx) => (
            <tr
              key={team.team_id}
              style={{
                borderBottom: "1px solid var(--rule-dim)",
                background: idx === 0 ? "oklch(from var(--bg-1) l c h / 0.5)" : "transparent",
              }}
            >
              <td style={{ padding: "7px 12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="t-mono" style={{ fontSize: 9, color: "var(--ink-4)", width: 14, textAlign: "right" }}>
                    {idx + 1}
                  </span>
                  <span style={{
                    fontWeight: idx === 0 ? 600 : 400,
                    color: idx === 0 ? "var(--ink-0)" : "var(--ink-1)",
                  }}>
                    {team.team_abbrev || team.team_name}
                  </span>
                </div>
              </td>
              <td className="t-mono" style={{ textAlign: "center", padding: "7px 8px", color: "var(--ink-1)" }}>{team.wins}</td>
              <td className="t-mono" style={{ textAlign: "center", padding: "7px 8px", color: "var(--ink-1)" }}>{team.losses}</td>
              <td className="t-mono" style={{
                textAlign: "center", padding: "7px 8px",
                color: pctColor(team.win_pct),
                fontWeight: parseFloat(team.win_pct) >= 0.600 ? 600 : 400,
              }}>{team.win_pct}</td>
              <td className="t-mono" style={{ textAlign: "center", padding: "7px 8px", color: "var(--ink-3)" }}>
                {team.games_back === '-' ? <span style={{ color: "var(--amber)" }}>—</span> : team.games_back}
              </td>
              <td className="t-mono" style={{ textAlign: "center", padding: "7px 8px", color: "var(--ink-3)" }}>
                {team.home_wins}-{team.home_losses}
              </td>
              <td className="t-mono" style={{ textAlign: "center", padding: "7px 8px", color: "var(--ink-3)" }}>
                {team.away_wins}-{team.away_losses}
              </td>
              <td className="t-mono" style={{ textAlign: "center", padding: "7px 8px", color: "var(--ink-1)" }}>
                {team.last_ten_wins}-{team.last_ten_losses}
              </td>
              <td className="t-mono" style={{
                textAlign: "center", padding: "7px 8px",
                color: streakColor(team.streak),
                fontWeight: 600,
              }}>{team.streak || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

const LeagueSection = ({ leagueName, divisions }) => (
  <div style={{ marginBottom: 28 }}>
    <div style={{ paddingBottom: 8, borderBottom: "1px solid var(--amber-dim)", marginBottom: 12 }}>
      <span className="h-label" style={{ color: "var(--amber)", fontSize: 11 }}>{leagueName}</span>
    </div>
    {divisions.map((div) => (
      <DivisionTable key={div.division_name} division={div} />
    ))}
  </div>
);

export default function Standings() {
  const { getIdToken } = useAuth();
  const getIdTokenRef = useRef(getIdToken);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('division');
  const [activeLeague, setActiveLeague] = useState('AL');
  const [updatedAt, setUpdatedAt] = useState(null);

  const fetchStandings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const idToken = await getIdTokenRef.current();
      const headers = {
        'Accept': 'application/json',
        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
      };
      const res = await fetch(`${BACKEND_URL}/api/v1/live/standings`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setUpdatedAt(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStandings();
  }, [fetchStandings]);

  const alDivisions = data?.standings?.filter((d) => d.league_id === AL_ID) ?? [];
  const nlDivisions = data?.standings?.filter((d) => d.league_id === NL_ID) ?? [];

  const buildLeagueRanking = (divisions) =>
    divisions
      .flatMap((d) => d.teams)
      .sort((a, b) => parseFloat(b.win_pct) - parseFloat(a.win_pct));

  const alTeams = buildLeagueRanking(alDivisions);
  const nlTeams = buildLeagueRanking(nlDivisions);

  const leagueDivision = {
    division_name: activeLeague === 'AL' ? 'American League' : 'National League',
    teams: activeLeague === 'AL' ? alTeams : nlTeams,
  };

  const tabBtn = (active) => ({
    padding: "5px 16px",
    fontSize: 11,
    fontFamily: "var(--ff-mono)",
    letterSpacing: "0.06em",
    fontWeight: active ? 600 : 400,
    background: active ? "var(--amber)" : "transparent",
    color: active ? "var(--bg-0)" : "var(--ink-3)",
    border: `1px solid ${active ? "var(--amber)" : "var(--rule)"}`,
    transition: "all .12s",
  });

  return (
    <div style={{ width: "100%", maxWidth: 780, margin: "0 auto" }}>
      {/* Header */}
      <div className="rule-b" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 12, marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon name="chart" size={16} style={{ color: "var(--amber)" }}/>
          <span className="h-display" style={{ fontSize: 16 }}>
            Standings
          </span>
          {data?.season && (
            <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
              {data.season}
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {updatedAt && (
            <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
              更新: {updatedAt.toLocaleDateString('ja-JP', { month: 'numeric', day: 'numeric' })}{' '}
              {updatedAt.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
          <button
            onClick={fetchStandings}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", fontSize: 11,
              border: "1px solid var(--rule)", color: "var(--ink-2)",
              opacity: loading ? 0.5 : 1,
              fontFamily: "var(--ff-mono)",
            }}
          >
            <Icon name="refresh" size={12} className={loading ? "dl-spin" : ""}/>
            更新
          </button>
        </div>
      </div>

      {/* View mode tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
        {['division', 'league'].map((mode) => (
          <button key={mode} onClick={() => setViewMode(mode)} style={tabBtn(viewMode === mode)}>
            {mode === 'division' ? 'DIVISION' : 'LEAGUE'}
          </button>
        ))}
      </div>

      {/* League view AL/NL toggle */}
      {viewMode === 'league' && (
        <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
          {['AL', 'NL'].map((lg) => (
            <button key={lg} onClick={() => setActiveLeague(lg)} style={tabBtn(activeLeague === lg)}>
              {lg}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "80px 0", gap: 8 }}>
          <span className="think-dot"/>
          <span className="think-dot" style={{ animationDelay: ".2s" }}/>
          <span className="think-dot" style={{ animationDelay: ".4s" }}/>
          <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>取得中...</span>
        </div>
      ) : error ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px 0", gap: 10 }}>
          <span style={{ color: "var(--neg)", fontSize: 13 }}>データを取得できませんでした</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{error}</span>
          <button
            onClick={fetchStandings}
            style={{ marginTop: 8, padding: "6px 16px", fontSize: 12, border: "1px solid var(--rule)", color: "var(--ink-2)" }}
          >
            再試行
          </button>
        </div>
      ) : viewMode === 'division' ? (
        <>
          <LeagueSection leagueName="American League" divisions={alDivisions} />
          <LeagueSection leagueName="National League" divisions={nlDivisions} />
        </>
      ) : (
        <DivisionTable division={leagueDivision} />
      )}

      {/* Legend */}
      {!loading && !error && (
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 12 }}>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>GB = Games Behind</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>L10 = Last 10 Games</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--pos)" }}>W = Winning Streak</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--neg)" }}>L = Losing Streak</span>
        </div>
      )}
    </div>
  );
}
