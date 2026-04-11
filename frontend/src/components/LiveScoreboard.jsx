import { useState, useEffect, useCallback, useRef } from 'react';
import { Radio, RefreshCw, X } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const POLL_INTERVAL_MS = 40000;

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
      <div className={`absolute w-4 h-4 rotate-45 top-0 left-1/2 -translate-x-1/2 ${runners.second ? occupied : empty}`} />
      <div className={`absolute w-4 h-4 rotate-45 top-1/2 left-0 -translate-y-1/2 ${runners.third ? occupied : empty}`} />
      <div className={`absolute w-4 h-4 rotate-45 top-1/2 right-0 -translate-y-1/2 ${runners.first ? occupied : empty}`} />
      <div className={`absolute w-4 h-4 rotate-45 bottom-0 left-1/2 -translate-x-1/2 bg-gray-600`} />
    </div>
  );
};

// ボックススコア モーダル
const BoxscoreModal = ({ game, onClose, getIdToken }) => {
  const [boxscore, setBoxscore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('away');
  const getIdTokenRef = useRef(getIdToken);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const idToken = await getIdTokenRef.current();
        const headers = {
          'Accept': 'application/json',
          ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
        };
        const res = await fetch(`${BACKEND_URL}/api/v1/live/games/${game.gamePk}/boxscore`, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setBoxscore(data);
        setActiveTab('away');
      } catch (e) {
        setBoxscore(null);
      } finally {
        setLoading(false);
      }
    };
    fetch_();
  }, [game.gamePk]);

  const awayWin = game.away_score > game.home_score;
  const homeWin = game.home_score > game.away_score;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3 text-white font-bold text-base">
            <span className={awayWin ? 'text-white' : 'text-gray-500'}>{game.away_team}</span>
            <span className={`text-xl ${awayWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.away_score}</span>
            <span className="text-gray-600 text-sm font-normal">-</span>
            <span className={`text-xl ${homeWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.home_score}</span>
            <span className={homeWin ? 'text-white' : 'text-gray-500'}>{game.home_team}</span>
            <span className="text-xs text-gray-500 font-normal ml-1">Final</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            <span>取得中...</span>
          </div>
        ) : !boxscore ? (
          <div className="p-8 text-center text-gray-500">データを取得できませんでした</div>
        ) : (
          <>
            {/* チームタブ */}
            <div className="flex border-b border-gray-700 flex-shrink-0">
              {['away', 'home'].map(side => (
                <button
                  key={side}
                  onClick={() => setActiveTab(side)}
                  className={`flex-1 py-2.5 text-sm font-medium transition-colors ${activeTab === side
                      ? 'text-white border-b-2 border-blue-500'
                      : 'text-gray-500 hover:text-gray-300'
                    }`}
                >
                  {boxscore[side]?.team}
                </button>
              ))}
            </div>

            {/* コンテンツ */}
            <div className="overflow-y-auto flex-1 px-4 py-3">
              {/* 投手 */}
              <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider mb-2">Pitchers</p>
              <div className="overflow-x-auto mb-5">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700">
                      <th className="text-left py-1.5 pr-3 font-medium min-w-[120px]">PITCHER</th>
                      <th className="text-right py-1.5 px-2 font-medium">ERA</th>
                      <th className="text-right py-1.5 px-2 font-medium">IP</th>
                      <th className="text-right py-1.5 px-2 font-medium">H</th>
                      <th className="text-right py-1.5 px-2 font-medium">R</th>
                      <th className="text-right py-1.5 px-2 font-medium">ER</th>
                      <th className="text-right py-1.5 px-2 font-medium">HR</th>
                      <th className="text-right py-1.5 px-2 font-medium">K</th>
                      <th className="text-right py-1.5 px-2 font-medium">BB</th>
                      <th className="text-right py-1.5 px-2 font-medium">PT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {boxscore[activeTab]?.pitchers.map((p, i) => (
                      <tr key={i} className="border-b border-gray-800 text-gray-300">
                        <td className="py-2 pr-3">
                          <div className="font-medium text-white">{p.name}</div>
                          {p.note && <div className="text-gray-500 text-xs">{p.note}</div>}
                        </td>
                        <td className="text-right px-2">{p.era}</td>
                        <td className="text-right px-2">{p.ip}</td>
                        <td className="text-right px-2">{p.h}</td>
                        <td className="text-right px-2">{p.r}</td>
                        <td className="text-right px-2">{p.er}</td>
                        <td className="text-right px-2">{p.hr}</td>
                        <td className="text-right px-2">{p.k}</td>
                        <td className="text-right px-2">{p.bb}</td>
                        <td className="text-right px-2">{p.pitches}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 野手 */}
              <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider mb-2">Batters</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700">
                      <th className="text-left py-1.5 pr-3 font-medium min-w-[120px]">BATTER</th>
                      <th className="text-right py-1.5 px-2 font-medium">AVG</th>
                      <th className="text-right py-1.5 px-2 font-medium">AB</th>
                      <th className="text-right py-1.5 px-2 font-medium">H</th>
                      <th className="text-right py-1.5 px-2 font-medium">R</th>
                      <th className="text-right py-1.5 px-2 font-medium">RBI</th>
                      <th className="text-right py-1.5 px-2 font-medium">HR</th>
                      <th className="text-right py-1.5 px-2 font-medium">BB</th>
                      <th className="text-right py-1.5 px-2 font-medium">K</th>
                      <th className="text-right py-1.5 px-2 font-medium">OBP</th>
                      <th className="text-right py-1.5 px-2 font-medium">SLG</th>
                      <th className="text-right py-1.5 px-2 font-medium">OPS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {boxscore[activeTab]?.batters.map((b, i) => (
                      <tr key={i} className="border-b border-gray-800 text-gray-300">
                        <td className="py-2 pr-3">
                          <div className="font-medium text-white">{b.name}</div>
                          <div className="text-gray-500">{b.position}</div>
                        </td>
                        <td className="text-right px-2">{b.avg}</td>
                        <td className="text-right px-2">{b.ab}</td>
                        <td className="text-right px-2">{b.h}</td>
                        <td className="text-right px-2">{b.r}</td>
                        <td className="text-right px-2">{b.rbi}</td>
                        <td className="text-right px-2">{b.hr}</td>
                        <td className="text-right px-2">{b.bb}</td>
                        <td className="text-right px-2">{b.k}</td>
                        <td className="text-right px-2">{b.obp}</td>
                        <td className="text-right px-2">{b.slg}</td>
                        <td className="text-right px-2">{b.ops}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const GameCard = ({ game }) => {
  const inningText = `${game.inning}回${game.inning_half === 'Top' ? '表' : '裏'}`;
  const hasRunners = game.runners && (game.runners.first || game.runners.second || game.runners.third);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex flex-col gap-3">
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

      <div className="flex items-center gap-3">
        <div className="grid grid-cols-2 gap-2 text-sm flex-1">
          <div className="bg-gray-700/50 rounded-lg px-3 py-2">
            <span className="text-gray-400 text-xs block mb-0.5">投手</span>
            <span className="text-white font-medium">{game.pitcher}</span>
            {game.pitcher_stats?.pitches > 0 && (
              <span className="text-gray-400 text-xs block mt-0.5 font-mono">
                {game.pitcher_stats.pitches}P | {game.pitcher_stats.ip}IP {game.pitcher_stats.k}K {game.pitcher_stats.er}ER
              </span>
            )}
          </div>
          <div className="bg-gray-700/50 rounded-lg px-3 py-2">
            <span className="text-gray-400 text-xs block mb-0.5">打者</span>
            <span className="text-white font-medium">{game.batter}</span>
            {game.batter_stats && (
              <span className="text-gray-400 text-xs block mt-0.5 font-mono">
                {game.batter_stats.h}-{game.batter_stats.ab}
                {game.batter_stats.rbi > 0 && ` | ${game.batter_stats.rbi}RBI`}
                {game.batter_stats.hr > 0 && ` ${game.batter_stats.hr}HR`}
                {game.batter_stats.sb > 0 && ` ${game.batter_stats.sb}SB`}
                {game.batter_stats.bb > 0 && ` ${game.batter_stats.bb}BB`}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-center gap-1">
          <BaseDiamond runners={game.runners || {}} />
          <span className="text-xs font-mono text-gray-300 whitespace-nowrap">
            {game.balls}-{game.strikes}, {game.outs} Out{game.outs !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-sm flex-wrap">
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

      {hasRunners && (
        <div className="flex gap-3 text-xs text-gray-400">
          {game.runners.third && <span>3塁: <span className="text-white">{game.runners.third}</span></span>}
          {game.runners.second && <span>2塁: <span className="text-white">{game.runners.second}</span></span>}
          {game.runners.first && <span>1塁: <span className="text-white">{game.runners.first}</span></span>}
        </div>
      )}

      {game.scoring_plays?.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-xs text-gray-500">Runs</span>
          {game.scoring_plays.map((sp, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="text-yellow-400 font-bold w-12 shrink-0">
                {sp.runs > 0 ? `+${sp.runs}` : '—'}
              </span>
              <span className="text-white font-medium">{sp.batter}</span>
              <span className="text-gray-400">
                {sp.event}{sp.season_hr != null ? ` (${sp.season_hr})` : ''}
              </span>
              <span className="text-gray-500">
                {sp.half === 'top' ? '表' : '裏'}{sp.inning}回
              </span>
            </div>
          ))}
        </div>
      )}

      {game.pitch_sequence?.length > 0 && (
        <div className="bg-gray-900/50 rounded-lg px-3 py-2 flex flex-col gap-1">
          <span className="text-xs text-gray-500 mb-1">投球シーケンス</span>
          {[...game.pitch_sequence].reverse().map((p) => {
            const call = p.pitch_call ?? '';
            const isStrike = /strike|foul/i.test(call);
            const isBall = /ball/i.test(call);
            const isInPlay = /^in play/i.test(call);
            const callColor = isStrike ? 'text-red-400' : isBall ? 'text-blue-400' : isInPlay ? 'text-green-400' : 'text-gray-400';
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

// JST の日付情報を返すユーティリティ
const getJstDateInfo = (offsetDays = 0) => {
  const now = new Date();
  const jst = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));
  jst.setDate(jst.getDate() + offsetDays);
  const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const label = `${jst.getMonth() + 1}/${jst.getDate()} (${weekdays[jst.getDay()]})`;
  const dateStr = `${jst.getFullYear()}-${String(jst.getMonth() + 1).padStart(2, '0')}-${String(jst.getDate()).padStart(2, '0')}`;
  return { label, dateStr };
};

const LiveScoreboard = () => {
  const { getIdToken } = useAuth();
  const getIdTokenRef = useRef(getIdToken);
  const [activeTab, setActiveTab] = useState('today');
  const [liveGames, setLiveGames] = useState([]);
  const [finalGames, setFinalGames] = useState([]);
  const [previewGames, setPreviewGames] = useState([]);
  const [scheduledGames, setScheduledGames] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedGame, setSelectedGame] = useState(null);

  const yesterdayInfo = getJstDateInfo(-1);
  const todayInfo = getJstDateInfo(0);
  const futureDays = [1, 2, 3, 4, 5].map(i => getJstDateInfo(i));

  const fetchGames = useCallback(async () => {
    try {
      const idToken = await getIdTokenRef.current();
      const headers = {
        'Accept': 'application/json',
        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
      };
      const res = await fetch(`${BACKEND_URL}/api/v1/live/games/today`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLiveGames(data.live ?? []);
      setFinalGames(data.final ?? []);
      setPreviewGames(data.preview ?? []);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHighlights = useCallback(async (dateStr) => {
    try {
      const idToken = await getIdTokenRef.current();
      const headers = {
        'Accept': 'application/json',
        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
      };
      const res = await fetch(`${BACKEND_URL}/api/v1/live/games/highlights?date=${dateStr}`, { headers });
      if (!res.ok) return;
      const data = await res.json();
      setHighlights(data ?? []);
    } catch {
      setHighlights([]);
    }
  }, []);

  const fetchSchedule = useCallback(async (dateStr) => {
    setScheduleLoading(true);
    setScheduledGames([]);
    try {
      const idToken = await getIdTokenRef.current();
      const headers = {
        'Accept': 'application/json',
        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
      };
      const res = await fetch(`${BACKEND_URL}/api/v1/live/games/schedule?date=${dateStr}`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setScheduledGames(data ?? []);
    } catch (e) {
      setScheduledGames([]);
    } finally {
      setScheduleLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGames();
    const timer = setInterval(fetchGames, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchGames]);

  useEffect(() => {
    if (activeTab !== 'today') {
      fetchSchedule(activeTab);
    }
    // 今日・前日タブのみハイライト取得（未来日は対象外）
    const dateStr = activeTab === 'today' ? todayInfo.dateStr : activeTab;
    if (dateStr <= todayInfo.dateStr) {
      fetchHighlights(dateStr);
    } else {
      setHighlights([]);
    }
  }, [activeTab, fetchSchedule, fetchHighlights, todayInfo.dateStr]);

  return (
    <div className="w-full">
      {selectedGame && (
        <BoxscoreModal
          game={selectedGame}
          onClose={() => setSelectedGame(null)}
          getIdToken={getIdToken}
        />
      )}

      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-4">
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

      {/* 日付タブ */}
      <div className="flex gap-1 mb-4 bg-gray-800 rounded-lg p-1 overflow-x-auto w-full">
        <button
          onClick={() => setActiveTab(yesterdayInfo.dateStr)}
          className={`px-4 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${activeTab === yesterdayInfo.dateStr ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
        >
          {yesterdayInfo.label}
        </button>
        <button
          onClick={() => setActiveTab('today')}
          className={`px-4 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${activeTab === 'today' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
        >
          {todayInfo.label}
        </button>
        {futureDays.map(day => (
          <button
            key={day.dateStr}
            onClick={() => setActiveTab(day.dateStr)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${activeTab === day.dateStr ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
          >
            {day.label}
          </button>
        ))}
      </div>

      {lastUpdated && activeTab === 'today' && (
        <p className="text-xs text-gray-500 mb-4">
          最終更新: {lastUpdated.toLocaleTimeString('ja-JP')}
        </p>
      )}

      {/* ハイライト */}
      {highlights.length > 0 && (
        <div className="bg-gray-800/60 border border-yellow-700/40 rounded-xl px-5 py-4 mb-4">
          <p className="text-xs text-yellow-500/80 font-semibold uppercase tracking-wider mb-2">Highlights</p>
          <ul className="flex flex-col gap-1.5">
            {highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-200">
                <span className="text-yellow-400 mt-0.5 flex-shrink-0">●</span>
                <span>{h.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 今日タブ */}
      {activeTab === 'today' && (
        loading ? (
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
            {liveGames.length > 0 ? (
              <div className="flex flex-col gap-4">
                <p className="text-sm text-gray-400">{liveGames.length}試合進行中</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {liveGames.map((game) => (
                    <GameCard key={game.gamePk} game={game} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-8 text-center">
                <Radio className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-400">現在進行中の試合はありません</p>
              </div>
            )}

            {previewGames.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-gray-500 font-medium">本日予定</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {previewGames.map((game) => (
                    <div
                      key={game.gamePk}
                      className="bg-gray-800/40 border border-gray-700/40 rounded-lg px-4 py-3 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2 text-sm">
                        <div className="flex flex-col">
                          <span className="text-gray-300">{game.away_team}</span>
                          {game.away_wins != null && <span className="text-xs text-gray-500">{game.away_wins}-{game.away_losses}</span>}
                        </div>
                        <span className="text-gray-600 mx-1">@</span>
                        <div className="flex flex-col">
                          <span className="text-gray-300">{game.home_team}</span>
                          {game.home_wins != null && <span className="text-xs text-gray-500">{game.home_wins}-{game.home_losses}</span>}
                        </div>
                      </div>
                      <span className="text-sm text-blue-400 font-mono">{game.start_time_jst} JST</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {finalGames.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-gray-500 font-medium">本日終了</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {finalGames.map((game) => {
                    const awayWin = game.away_score > game.home_score;
                    const homeWin = game.home_score > game.away_score;
                    return (
                      <button
                        key={game.gamePk}
                        onClick={() => setSelectedGame(game)}
                        className="bg-gray-800/60 border border-gray-700/60 rounded-lg px-4 py-3 flex items-center justify-between hover:bg-gray-700/60 hover:border-gray-600 transition-colors text-left w-full"
                      >
                        <div className="flex items-center gap-2 text-sm">
                          <div className="flex flex-col">
                            <span className={awayWin ? 'text-white font-semibold' : 'text-gray-500'}>{game.away_team}</span>
                            {game.away_wins != null && <span className="text-xs text-gray-500">{game.away_wins}-{game.away_losses}</span>}
                          </div>
                          <span className={`font-bold text-base ${awayWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.away_score}</span>
                          <span className="text-gray-600 mx-1">-</span>
                          <span className={`font-bold text-base ${homeWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.home_score}</span>
                          <div className="flex flex-col">
                            <span className={homeWin ? 'text-white font-semibold' : 'text-gray-500'}>{game.home_team}</span>
                            {game.home_wins != null && <span className="text-xs text-gray-500">{game.home_wins}-{game.home_losses}</span>}
                          </div>
                        </div>
                        <span className="text-xs text-gray-600">Final →</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )
      )}

      {/* 前日・翌日以降タブ */}
      {activeTab !== 'today' && (
        scheduleLoading ? (
          <div className="flex items-center justify-center py-20 text-gray-400">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            <span>取得中...</span>
          </div>
        ) : scheduledGames.length === 0 ? (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-8 text-center">
            <p className="text-gray-400">試合情報はありません</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {scheduledGames.map((game) => {
                if (game.status === 'Final') {
                  const awayWin = game.away_score > game.home_score;
                  const homeWin = game.home_score > game.away_score;
                  return (
                    <button
                      key={game.gamePk}
                      onClick={() => setSelectedGame(game)}
                      className="bg-gray-800/60 border border-gray-700/60 rounded-lg px-4 py-3 flex items-center justify-between hover:bg-gray-700/60 hover:border-gray-600 transition-colors text-left w-full"
                    >
                      <div className="flex items-center gap-2 text-sm">
                        <div className="flex flex-col">
                          <span className={awayWin ? 'text-white font-semibold' : 'text-gray-500'}>{game.away_team}</span>
                          {game.away_wins != null && <span className="text-xs text-gray-500">{game.away_wins}-{game.away_losses}</span>}
                        </div>
                        <span className={`font-bold text-base ${awayWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.away_score}</span>
                        <span className="text-gray-600 mx-1">-</span>
                        <span className={`font-bold text-base ${homeWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.home_score}</span>
                        <div className="flex flex-col">
                          <span className={homeWin ? 'text-white font-semibold' : 'text-gray-500'}>{game.home_team}</span>
                          {game.home_wins != null && <span className="text-xs text-gray-500">{game.home_wins}-{game.home_losses}</span>}
                        </div>
                      </div>
                      <span className="text-xs text-gray-600">Final →</span>
                    </button>
                  );
                }
                return (
                  <div
                    key={game.gamePk}
                    className="bg-gray-800/40 border border-gray-700/40 rounded-lg px-4 py-3 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2 text-sm">
                      <div className="flex flex-col">
                        <span className="text-gray-300">{game.away_team}</span>
                        {game.away_wins != null && <span className="text-xs text-gray-500">{game.away_wins}-{game.away_losses}</span>}
                      </div>
                      <span className="text-gray-600 mx-1">@</span>
                      <div className="flex flex-col">
                        <span className="text-gray-300">{game.home_team}</span>
                        {game.home_wins != null && <span className="text-xs text-gray-500">{game.home_wins}-{game.home_losses}</span>}
                      </div>
                    </div>
                    <span className="text-sm text-blue-400 font-mono">{game.start_time_jst} JST</span>
                  </div>
                );
              })}
            </div>
          </div>
        )
      )}
    </div>
  );
};

export default LiveScoreboard;
