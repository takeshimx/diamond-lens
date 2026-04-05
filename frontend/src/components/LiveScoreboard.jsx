import { useState, useEffect, useCallback } from 'react';
import { Radio, RefreshCw } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const POLL_INTERVAL_MS = 60000;

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

// 走者表示コンポーネント（ダイヤモンド形）
const BaseDiamond = ({ runners }) => {
  const occupied = 'bg-yellow-400';
  const empty = 'bg-gray-600';

  return (
    <div className="relative w-12 h-12 flex-shrink-0">
      {/* 2塁（上） */}
      <div className={`absolute w-4 h-4 rotate-45 top-0 left-1/2 -translate-x-1/2 ${runners.second ? occupied : empty}`} />
      {/* 3塁（左） */}
      <div className={`absolute w-4 h-4 rotate-45 top-1/2 left-0 -translate-y-1/2 ${runners.third ? occupied : empty}`} />
      {/* 1塁（右） */}
      <div className={`absolute w-4 h-4 rotate-45 top-1/2 right-0 -translate-y-1/2 ${runners.first ? occupied : empty}`} />
      {/* ホーム（下） */}
      <div className={`absolute w-4 h-4 rotate-45 bottom-0 left-1/2 -translate-x-1/2 bg-gray-600`} />
    </div>
  );
};

const GameCard = ({ game }) => {
  const inningText = `${game.inning}回${game.inning_half === 'Top' ? '表' : '裏'}`;
  const hasRunners = game.runners && (game.runners.first || game.runners.second || game.runners.third);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex flex-col gap-3">
      {/* スコアヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-lg font-bold text-white">
          <span>{game.away_team}</span>
          <span className="text-2xl text-yellow-400">{game.away_score}</span>
          <span className="text-gray-500 text-base font-normal">vs</span>
          <span className="text-2xl text-yellow-400">{game.home_score}</span>
          <span>{game.home_team}</span>
        </div>
        <span className="text-sm text-green-400 font-semibold bg-green-900/40 px-2 py-0.5 rounded-full">
          {inningText}
        </span>
      </div>

      {/* 投手・打者 + 走者ダイヤモンド */}
      <div className="flex items-center gap-3">
        <div className="grid grid-cols-2 gap-2 text-sm flex-1">
          <div className="bg-gray-700/50 rounded-lg px-3 py-2">
            <span className="text-gray-400 text-xs block mb-0.5">投手</span>
            <span className="text-white font-medium">{game.pitcher}</span>
          </div>
          <div className="bg-gray-700/50 rounded-lg px-3 py-2">
            <span className="text-gray-400 text-xs block mb-0.5">打者</span>
            <span className="text-white font-medium">{game.batter}</span>
          </div>
        </div>
        {/* 走者ダイヤモンド */}
        <div className="flex flex-col items-center gap-1">
          <BaseDiamond runners={game.runners || {}} />
          {hasRunners && (
            <span className="text-xs text-yellow-400">走者あり</span>
          )}
        </div>
      </div>

      {/* カウント + 直近球種・球速 */}
      <div className="flex items-center gap-2 text-sm flex-wrap">
        <span className="bg-gray-700 rounded px-2 py-1 font-mono text-gray-300">
          {game.balls}-{game.strikes}  {game.outs}アウト
        </span>
        {game.last_pitch?.pitch_type && (
          <span className="bg-blue-900/50 border border-blue-700/50 text-blue-300 rounded px-2 py-1 font-medium">
            {game.last_pitch.pitch_type}
          </span>
        )}
        {game.last_pitch?.speed && (
          <span className="bg-gray-700 rounded px-2 py-1 text-gray-300 font-mono">
            {game.last_pitch.speed.toFixed(1)} mph
          </span>
        )}
        {game.last_pitch?.pitch_call && (
          <span className="text-gray-500 text-xs">— {game.last_pitch.pitch_call}</span>
        )}
        {game.last_event && !game.last_pitch?.pitch_call && (
          <span className="text-gray-400 truncate">— {game.last_event}</span>
        )}
      </div>

      {/* 走者名の詳細（走者がいる場合のみ） */}
      {hasRunners && (
        <div className="flex gap-3 text-xs text-gray-400">
          {game.runners.third && <span>3塁: <span className="text-white">{game.runners.third}</span></span>}
          {game.runners.second && <span>2塁: <span className="text-white">{game.runners.second}</span></span>}
          {game.runners.first && <span>1塁: <span className="text-white">{game.runners.first}</span></span>}
        </div>
      )}

      {/* 投球シーケンス（新しい順） */}
      {game.pitch_sequence?.length > 0 && (
        <div className="bg-gray-900/50 rounded-lg px-3 py-2 flex flex-col gap-1">
          <span className="text-xs text-gray-500 mb-1">投球シーケンス</span>
          {[...game.pitch_sequence].reverse().map((p) => {
            const call = p.pitch_call ?? '';
            const isStrike = /strike/i.test(call);
            const isBall = /^ball$/i.test(call);
            const callColor = isStrike
              ? 'text-red-400'
              : isBall
              ? 'text-green-400'
              : 'text-gray-400';
            return (
              <div key={p.num} className="flex items-center gap-2 text-xs font-mono">
                <span className="text-gray-600 w-4 text-right">{p.num}:</span>
                <span className={`font-semibold ${callColor}`}>{call || '—'}</span>
                {p.pitch_type && (
                  <span className="text-gray-500">({p.pitch_type}{p.speed != null ? ` / ${p.speed} mph` : ''})</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const LiveScoreboard = () => {
  const { getIdToken } = useAuth();
  const [liveGames, setLiveGames] = useState([]);
  const [finalGames, setFinalGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchGames = useCallback(async () => {
    try {
      const idToken = await getIdToken();
      const headers = {
        'Accept': 'application/json',
        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
      };
      const res = await fetch(`${BACKEND_URL}/api/v1/live/games/today`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLiveGames(data.live ?? []);
      setFinalGames(data.final ?? []);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [getIdToken]);

  useEffect(() => {
    fetchGames();
    const timer = setInterval(fetchGames, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchGames]);

  return (
    <div className="max-w-3xl mx-auto w-full">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Radio className="w-5 h-5 text-green-400 animate-pulse" />
          <h2 className="text-xl font-bold text-white">試合速報</h2>
          <span className="text-xs text-gray-500 ml-1">（60秒ごと自動更新）</span>
        </div>
        <button
          onClick={fetchGames}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          更新
        </button>
      </div>

      {/* 最終更新時刻 */}
      {lastUpdated && (
        <p className="text-xs text-gray-500 mb-4">
          最終更新: {lastUpdated.toLocaleTimeString('ja-JP')}
        </p>
      )}

      {/* コンテンツ */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          <span>取得中...</span>
        </div>
      ) : error ? (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-6 text-center">
          <p className="text-red-400 font-medium">データ取得エラー</p>
          <p className="text-red-500 text-sm mt-1">{error}</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* 進行中試合 */}
          {liveGames.length > 0 ? (
            <div className="flex flex-col gap-4">
              <p className="text-sm text-gray-400">{liveGames.length}試合進行中</p>
              {liveGames.map((game) => (
                <GameCard key={game.gamePk} game={game} />
              ))}
            </div>
          ) : (
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-8 text-center">
              <Radio className="w-8 h-8 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-400">現在進行中の試合はありません</p>
            </div>
          )}

          {/* 本日終了試合 */}
          {finalGames.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-gray-500 font-medium">本日終了</p>
              {finalGames.map((game) => {
                const awayWin = game.away_score > game.home_score;
                const homeWin = game.home_score > game.away_score;
                return (
                  <div
                    key={game.gamePk}
                    className="bg-gray-800/60 border border-gray-700/60 rounded-lg px-4 py-3 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2 text-sm">
                      <span className={awayWin ? 'text-white font-semibold' : 'text-gray-500'}>{game.away_team}</span>
                      <span className={`font-bold text-base ${awayWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.away_score}</span>
                      <span className="text-gray-600 mx-1">-</span>
                      <span className={`font-bold text-base ${homeWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.home_score}</span>
                      <span className={homeWin ? 'text-white font-semibold' : 'text-gray-500'}>{game.home_team}</span>
                    </div>
                    <span className="text-xs text-gray-600">Final</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LiveScoreboard;
