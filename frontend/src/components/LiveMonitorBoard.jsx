import { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, X, AlertTriangle, Flame, Clock, TrendingUp, CircleDot, Zap } from 'lucide-react';
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

// ===== ルールベース異常検知 =====
const detectAnomalies = (game) => {
  const alerts = [];
  const scoreDiff = Math.abs((game.away_score ?? 0) - (game.home_score ?? 0));

  // 投手100球超え
  if (game.pitcher_stats?.pitches >= 100) {
    alerts.push({
      key: 'pitches',
      type: 'warning',
      icon: AlertTriangle,
      label: `${game.pitcher_stats.pitches}球超`,
    });
  }

  // 延長戦
  if (game.inning > 9) {
    alerts.push({
      key: 'extra',
      type: 'purple',
      icon: Clock,
      label: `延長${game.inning}回`,
    });
  }

  // 接戦（7回以降・1点差以内）
  if (game.inning >= 7 && scoreDiff <= 1) {
    alerts.push({
      key: 'close',
      type: 'hot',
      icon: Flame,
      label: scoreDiff === 0 ? '同点' : '1点差',
    });
  }

  // 大差（5点差以上）
  if (scoreDiff >= 5) {
    alerts.push({
      key: 'blowout',
      type: 'neutral',
      icon: TrendingUp,
      label: `${scoreDiff}点差`,
    });
  }

  // 満塁
  if (game.runners?.first && game.runners?.second && game.runners?.third) {
    alerts.push({
      key: 'bases_loaded',
      type: 'hot',
      icon: CircleDot,
      label: '満塁',
    });
  }

  return alerts;
};

// ===== 疲労判定（球種毎・シーズン平均との比較）=====
const computeFatigueAlert = (game, pitcherBaselines) => {
  const log = game.pitcher_pitch_log;
  if (!log || log.length === 0 || !pitcherBaselines) return null;

  // 終了済みイニングのみ対象（現在進行中のイニングは除く）
  const completedInning = game.outs >= 3 ? game.inning : game.inning - 1;
  if (completedInning < 1) return null;

  const lastInningPitches = log.filter(p => p.inning === completedInning);
  if (lastInningPitches.length < 3) return null; // サンプル少なすぎは無視

  // 球種毎に平均速度・スピンレートを集計
  const byType = {};
  lastInningPitches.forEach(p => {
    if (!byType[p.pitch_type]) byType[p.pitch_type] = { speeds: [], spins: [] };
    if (p.speed) byType[p.pitch_type].speeds.push(p.speed);
    if (p.spin_rate) byType[p.pitch_type].spins.push(p.spin_rate);
  });

  let maxScore = 0;
  let worstType = null;
  let worstSpeedDrop = 0;
  let worstSpinDrop = 0;

  Object.entries(byType).forEach(([type, { speeds, spins }]) => {
    const baseline = pitcherBaselines[type];
    if (!baseline) return;
    const speedDrop = speeds.length > 0 && baseline.speed
      ? baseline.speed - speeds.reduce((a, b) => a + b, 0) / speeds.length
      : 0;
    const spinDrop = spins.length > 0 && baseline.spin
      ? baseline.spin - spins.reduce((a, b) => a + b, 0) / spins.length
      : 0;
    // speedとspinの複合スコア（speed 1mph ≈ spin 50rpm で正規化）
    const score = speedDrop + spinDrop / 50;
    if (score > maxScore) {
      maxScore = score;
      worstType = type;
      worstSpeedDrop = speedDrop;
      worstSpinDrop = spinDrop;
    }
  });

  if (!worstType || maxScore <= 0) return null;

  const shortType = worstType.replace('4-Seam Fastball', 'FF').replace('Fastball', 'FF')
    .replace('Slider', 'SL').replace('Curveball', 'CU').replace('Changeup', 'CH')
    .replace('Sinker', 'SI').replace('Cutter', 'FC').replace('Sweeper', 'SW').split(' ')[0];

  const speedStr = worstSpeedDrop > 0.1 ? `spd-${worstSpeedDrop.toFixed(1)}` : null;
  const spinStr = worstSpinDrop > 10 ? `spin-${Math.round(worstSpinDrop)}` : null;
  const detail = [speedStr, spinStr].filter(Boolean).join(' ');

  if (maxScore >= 2.5) {
    return { key: 'fatigue', type: 'warning', icon: Zap, label: `疲労 ${shortType} ${detail}` };
  }
  if (maxScore >= 1.5) {
    return { key: 'fatigue', type: 'caution', icon: Zap, label: `要注意 ${shortType} ${detail}` };
  }
  return null;
};

const ALERT_STYLES = {
  warning: 'bg-orange-900/60 border-orange-600/50 text-orange-300',
  caution: 'bg-yellow-900/60 border-yellow-600/50 text-yellow-300',
  purple:  'bg-purple-900/60 border-purple-600/50 text-purple-300',
  hot:     'bg-red-900/60 border-red-500/50 text-red-300',
  neutral: 'bg-gray-700/60 border-gray-500/50 text-gray-300',
};

// ===== ボックススコアモーダル =====
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
      } catch {
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
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3 text-white font-bold text-base">
            <span className={awayWin ? 'text-white' : 'text-gray-500'}>{game.away_team}</span>
            <span className={`text-xl ${awayWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.away_score}</span>
            <span className="text-gray-600 text-sm font-normal">-</span>
            <span className={`text-xl ${homeWin ? 'text-yellow-400' : 'text-gray-500'}`}>{game.home_score}</span>
            <span className={homeWin ? 'text-white' : 'text-gray-500'}>{game.home_team}</span>
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
            <div className="overflow-y-auto flex-1 px-4 py-3">
              <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider mb-2">Pitchers</p>
              <div className="overflow-x-auto mb-5">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700">
                      {['PITCHER','ERA','IP','H','R','ER','HR','K','BB','PT'].map(h => (
                        <th key={h} className={`py-1.5 px-2 font-medium ${h === 'PITCHER' ? 'text-left min-w-[120px]' : 'text-right'}`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {boxscore[activeTab]?.pitchers.map((p, i) => (
                      <tr key={i} className="border-b border-gray-800 text-gray-300">
                        <td className="py-2 pr-3">
                          <div className="font-medium text-white">{p.name}</div>
                          {p.note && <div className="text-gray-500 text-xs">{p.note}</div>}
                        </td>
                        {[p.era, p.ip, p.h, p.r, p.er, p.hr, p.k, p.bb, p.pitches].map((v, j) => (
                          <td key={j} className="text-right px-2">{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider mb-2">Batters</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700">
                      {['BATTER','AVG','AB','H','R','RBI','HR','BB','K','OBP','SLG','OPS'].map(h => (
                        <th key={h} className={`py-1.5 px-2 font-medium ${h === 'BATTER' ? 'text-left min-w-[120px]' : 'text-right'}`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {boxscore[activeTab]?.batters.map((b, i) => (
                      <tr key={i} className="border-b border-gray-800 text-gray-300">
                        <td className="py-2 pr-3">
                          <div className="font-medium text-white">{b.name}</div>
                          <div className="text-gray-500">{b.position}</div>
                        </td>
                        {[b.avg, b.ab, b.h, b.r, b.rbi, b.hr, b.bb, b.k, b.obp, b.slg, b.ops].map((v, j) => (
                          <td key={j} className="text-right px-2">{v}</td>
                        ))}
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

// ===== コンパクトゲームカード =====
const MonitorCard = ({ game, status, onClick, pitcherBaselines }) => {
  const alerts = status === 'live' ? detectAnomalies(game) : [];
  const fatigueAlert = status === 'live' ? computeFatigueAlert(game, pitcherBaselines) : null;
  if (fatigueAlert) alerts.push(fatigueAlert);
  const scoreDiff = (game.away_score ?? 0) - (game.home_score ?? 0);
  const awayLeading = scoreDiff > 0;
  const homeLeading = scoreDiff < 0;

  return (
    <button
      onClick={() => onClick(game)}
      className={`
        w-full text-left rounded-xl border p-3 flex flex-col gap-2 transition-all duration-200
        hover:border-gray-500 hover:bg-gray-750 active:scale-[0.98]
        ${alerts.length > 0
          ? 'bg-gray-800 border-gray-600 ring-1 ring-orange-500/30'
          : 'bg-gray-800 border-gray-700'
        }
      `}
    >
      {/* スコア行 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className={`text-sm font-bold truncate ${awayLeading ? 'text-white' : 'text-gray-400'}`}>
            {game.away_team}
          </span>
          <span className={`text-lg font-black tabular-nums ${awayLeading ? 'text-yellow-400' : 'text-gray-300'}`}>
            {game.away_score ?? '-'}
          </span>
          <span className="text-gray-600 text-xs">:</span>
          <span className={`text-lg font-black tabular-nums ${homeLeading ? 'text-yellow-400' : 'text-gray-300'}`}>
            {game.home_score ?? '-'}
          </span>
          <span className={`text-sm font-bold truncate ${homeLeading ? 'text-white' : 'text-gray-400'}`}>
            {game.home_team}
          </span>
        </div>

        {/* ステータスバッジ */}
        {status === 'live' && (
          <span className="text-xs text-green-400 bg-green-900/40 px-1.5 py-0.5 rounded-full whitespace-nowrap flex-shrink-0">
            {game.inning}回{game.inning_half === 'Top' ? '表' : '裏'}
          </span>
        )}
        {status === 'final' && (
          <span className="text-xs text-gray-500 bg-gray-700/50 px-1.5 py-0.5 rounded-full flex-shrink-0">
            Final
          </span>
        )}
        {status === 'preview' && (
          <span className="text-xs text-blue-400 bg-blue-900/30 px-1.5 py-0.5 rounded-full flex-shrink-0">
            {game.game_time ?? '予定'}
          </span>
        )}
      </div>

      {/* 投手情報（ライブのみ） */}
      {status === 'live' && game.pitcher && (
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span className="truncate">
            <span className="text-gray-500">P: </span>
            <span className="text-gray-200">{game.pitcher}</span>
            {game.pitcher_stats?.pitches > 0 && (
              <span className={`ml-1 tabular-nums ${game.pitcher_stats.pitches >= 100 ? 'text-orange-400 font-semibold' : ''}`}>
                {game.pitcher_stats.pitches}球
              </span>
            )}
          </span>
          <span className="font-mono text-gray-500 ml-2 flex-shrink-0">
            {game.balls}-{game.strikes} {game.outs}out
          </span>
        </div>
      )}

      {/* 異常検知バッジ */}
      {alerts.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {alerts.map(alert => {
            const Icon = alert.icon;
            return (
              <span
                key={alert.key}
                className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded border ${ALERT_STYLES[alert.type]}`}
              >
                <Icon className="w-3 h-3" />
                {alert.label}
              </span>
            );
          })}
        </div>
      )}
    </button>
  );
};

// ===== メインコンポーネント =====
const LiveMonitorBoard = () => {
  const { getIdToken } = useAuth();
  const getIdTokenRef = useRef(getIdToken);
  const [liveGames, setLiveGames] = useState([]);
  const [finalGames, setFinalGames] = useState([]);
  const [previewGames, setPreviewGames] = useState([]);
  const [fatigueBaselines, setFatigueBaselines] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedGame, setSelectedGame] = useState(null);

  const fetchBaselines = useCallback(async (games, idToken) => {
    const pitchers = games
      .map(g => g.pitcher)
      .filter(p => p && p !== 'N/A');
    if (pitchers.length === 0) return;

    const params = new URLSearchParams();
    pitchers.forEach(p => params.append('pitchers', p));
    params.append('season', new Date().getFullYear().toString());

    try {
      const headers = {
        'Accept': 'application/json',
        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
      };
      const res = await fetch(`${BACKEND_URL}/api/v1/live/fatigue/baselines?${params}`, { headers });
      if (!res.ok) return;
      const data = await res.json();
      setFatigueBaselines(data);
    } catch {
      // baselines 取得失敗はサイレントに無視
    }
  }, []);

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
      const live = data.live ?? [];
      setLiveGames(live);
      setFinalGames(data.final ?? []);
      setPreviewGames(data.preview ?? []);
      setLastUpdated(new Date());
      setError(null);
      if (live.length > 0) {
        fetchBaselines(live, idToken);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [fetchBaselines]);

  useEffect(() => {
    fetchGames();
    const timer = setInterval(fetchGames, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchGames]);

  const totalGames = liveGames.length + finalGames.length + previewGames.length;
  const anomalyCount = liveGames.filter(g => detectAnomalies(g).length > 0).length;

  const formatTime = (date) =>
    date ? date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--';

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
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          <h2 className="text-xl font-bold text-white">全試合モニターボード</h2>
          <div className="flex items-center gap-2 text-sm">
            <span className="bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">
              {totalGames} games
            </span>
            {anomalyCount > 0 && (
              <span className="bg-orange-900/60 border border-orange-600/50 text-orange-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {anomalyCount} alerts
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            更新: {formatTime(lastUpdated)}
          </span>
          <button
            onClick={fetchGames}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            更新
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          <span>取得中...</span>
        </div>
      ) : error ? (
        <div className="text-center py-12 text-red-400">{error}</div>
      ) : totalGames === 0 ? (
        <div className="text-center py-12 text-gray-500">本日の試合データがありません</div>
      ) : (
        <div className="flex flex-col gap-6">

          {/* ===== LIVE ===== */}
          {liveGames.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                <h3 className="text-sm font-semibold text-green-400 uppercase tracking-wider">
                  Live — {liveGames.length}試合
                </h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {liveGames.map(game => (
                  <MonitorCard
                    key={game.gamePk}
                    game={game}
                    status="live"
                    onClick={setSelectedGame}
                    pitcherBaselines={fatigueBaselines[game.pitcher] ?? null}
                  />
                ))}
              </div>
            </section>
          )}

          {/* ===== FINAL ===== */}
          {finalGames.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 bg-gray-500 rounded-full" />
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
                  Final — {finalGames.length}試合
                </h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {finalGames.map(game => (
                  <MonitorCard
                    key={game.gamePk}
                    game={game}
                    status="final"
                    onClick={setSelectedGame}
                  />
                ))}
              </div>
            </section>
          )}

          {/* ===== PREVIEW ===== */}
          {previewGames.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 bg-blue-400 rounded-full" />
                <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wider">
                  Upcoming — {previewGames.length}試合
                </h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {previewGames.map(game => (
                  <MonitorCard
                    key={game.gamePk}
                    game={game}
                    status="preview"
                    onClick={setSelectedGame}
                  />
                ))}
              </div>
            </section>
          )}

        </div>
      )}
    </div>
  );
};

export default LiveMonitorBoard;
