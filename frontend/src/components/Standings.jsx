import { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, TrendingUp } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

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

// AL/NL の leagueId
const AL_ID = 103;
const NL_ID = 104;

// 勝率の色分け
const pctColor = (pct) => {
  const v = parseFloat(pct);
  if (isNaN(v)) return 'text-gray-400';
  if (v >= 0.600) return 'text-green-400 font-bold';
  if (v >= 0.500) return 'text-gray-200';
  return 'text-red-400';
};

// 連勝/連敗のバッジ色
const streakColor = (code) => {
  if (!code || code === '-') return 'text-gray-500';
  if (code.startsWith('W')) return 'text-green-400';
  return 'text-red-400';
};

const DivisionTable = ({ division }) => (
  <div className="mb-6">
    {/* ディビジョン名ヘッダー */}
    <div className="px-3 py-1.5 bg-gray-800 rounded-t-lg border-b border-gray-600">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        {division.division_name}
      </span>
    </div>

    {/* テーブル */}
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-gray-800/60 text-gray-500 uppercase">
            <th className="text-left px-3 py-2 font-medium w-32">チーム</th>
            <th className="text-center px-2 py-2 font-medium">W</th>
            <th className="text-center px-2 py-2 font-medium">L</th>
            <th className="text-center px-2 py-2 font-medium">PCT</th>
            <th className="text-center px-2 py-2 font-medium">GB</th>
            <th className="text-center px-2 py-2 font-medium hidden sm:table-cell">Home</th>
            <th className="text-center px-2 py-2 font-medium hidden sm:table-cell">Away</th>
            <th className="text-center px-2 py-2 font-medium">L10</th>
            <th className="text-center px-2 py-2 font-medium">Streak</th>
          </tr>
        </thead>
        <tbody>
          {division.teams.map((team, idx) => (
            <tr
              key={team.team_id}
              className={`border-b border-gray-700/50 transition-colors hover:bg-gray-700/30 ${
                idx === 0 ? 'bg-gray-800/20' : ''
              }`}
            >
              {/* チーム名 */}
              <td className="px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 w-4 text-right text-[10px]">{idx + 1}</span>
                  <span className={`font-semibold ${idx === 0 ? 'text-white' : 'text-gray-300'}`}>
                    {team.team_abbrev || team.team_name}
                  </span>
                </div>
              </td>
              <td className="text-center px-2 py-2.5 text-gray-200">{team.wins}</td>
              <td className="text-center px-2 py-2.5 text-gray-200">{team.losses}</td>
              <td className={`text-center px-2 py-2.5 ${pctColor(team.win_pct)}`}>
                {team.win_pct}
              </td>
              <td className="text-center px-2 py-2.5 text-gray-400">
                {team.games_back === '-' ? <span className="text-yellow-400">—</span> : team.games_back}
              </td>
              <td className="text-center px-2 py-2.5 text-gray-400 hidden sm:table-cell">
                {team.home_wins}-{team.home_losses}
              </td>
              <td className="text-center px-2 py-2.5 text-gray-400 hidden sm:table-cell">
                {team.away_wins}-{team.away_losses}
              </td>
              <td className="text-center px-2 py-2.5 text-gray-300">
                {team.last_ten_wins}-{team.last_ten_losses}
              </td>
              <td className={`text-center px-2 py-2.5 font-medium ${streakColor(team.streak)}`}>
                {team.streak || '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

const LeagueSection = ({ leagueName, divisions }) => (
  <div className="mb-8">
    <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-3 px-1">
      {leagueName}
    </h2>
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
  const [viewMode, setViewMode] = useState('division'); // 'division' | 'league'
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

  // Division view: AL/NL 別に仕分け
  const alDivisions = data?.standings?.filter((d) => d.league_id === AL_ID) ?? [];
  const nlDivisions = data?.standings?.filter((d) => d.league_id === NL_ID) ?? [];

  // League view: リーグ内全チームを勝率順に並べる
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

  return (
    <div className="w-full max-w-3xl mx-auto">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <TrendingUp className="w-5 h-5 text-blue-400" />
          <h1 className="text-lg font-bold text-white">
            Standings
            {data?.season && (
              <span className="ml-2 text-sm font-normal text-gray-500">{data.season}</span>
            )}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {updatedAt && (
            <span className="text-[11px] text-gray-500">
              更新: {updatedAt.toLocaleDateString('ja-JP', { month: 'numeric', day: 'numeric' })}{' '}
              {updatedAt.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
          <button
            onClick={fetchStandings}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            更新
          </button>
        </div>
      </div>

      {/* League / Division タブ */}
      <div className="flex gap-1 mb-4 bg-gray-800 p-1 rounded-lg w-fit">
        {['division', 'league'].map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              viewMode === mode
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {mode === 'division' ? 'Division' : 'League'}
          </button>
        ))}
      </div>

      {/* League ビュー時の AL/NL 切替 */}
      {viewMode === 'league' && (
        <div className="flex gap-1 mb-4 bg-gray-800 p-1 rounded-lg w-fit">
          {['AL', 'NL'].map((lg) => (
            <button
              key={lg}
              onClick={() => setActiveLeague(lg)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeLeague === lg
                  ? 'bg-gray-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {lg}
            </button>
          ))}
        </div>
      )}

      {/* コンテンツ */}
      {loading ? (
        <div className="flex items-center justify-center py-24 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          <span>データ取得中...</span>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-24 text-gray-500">
          <p className="text-red-400 mb-3">データを取得できませんでした</p>
          <p className="text-xs text-gray-600">{error}</p>
          <button
            onClick={fetchStandings}
            className="mt-4 px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
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

      {/* 凡例 */}
      {!loading && !error && (
        <div className="mt-4 flex flex-wrap gap-3 text-[10px] text-gray-600 px-1">
          <span>GB = Games Behind</span>
          <span>L10 = Last 10 Games</span>
          <span className="text-green-600">W = Winning Streak</span>
          <span className="text-red-600">L = Losing Streak</span>
        </div>
      )}
    </div>
  );
}
