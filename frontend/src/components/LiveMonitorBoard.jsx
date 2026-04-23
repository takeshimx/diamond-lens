import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import Icon from './layout/Icon.jsx';

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

  if (game.pitcher_stats?.pitches >= 100) {
    alerts.push({ key: 'pitches', type: 'warning', iconName: 'alert', label: `${game.pitcher_stats.pitches}球超` });
  }
  if (game.inning > 9) {
    alerts.push({ key: 'extra', type: 'purple', iconName: 'clock', label: `延長${game.inning}回` });
  }
  if (game.inning >= 7 && scoreDiff <= 1) {
    alerts.push({ key: 'close', type: 'hot', iconName: 'fire', label: scoreDiff === 0 ? '同点' : '1点差' });
  }
  if (scoreDiff >= 5) {
    alerts.push({ key: 'blowout', type: 'neutral', iconName: 'chart', label: `${scoreDiff}点差` });
  }
  if (game.runners?.first && game.runners?.second && game.runners?.third) {
    alerts.push({ key: 'bases_loaded', type: 'hot', iconName: 'target', label: '満塁' });
  }
  return alerts;
};

// ===== 疲労判定（球種毎・シーズン平均との比較）=====
const computeFatigueAlert = (game, pitcherBaselines) => {
  const log = game.pitcher_pitch_log;
  if (!log || log.length === 0 || !pitcherBaselines) return null;

  const completedInning = game.outs >= 3 ? game.inning : game.inning - 1;
  if (completedInning < 1) return null;

  const lastInningPitches = log.filter(p => p.inning === completedInning);
  if (lastInningPitches.length < 3) return null;

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
    return { key: 'fatigue', type: 'warning', iconName: 'bolt', label: `疲労 ${shortType} ${detail}` };
  }
  if (maxScore >= 1.5) {
    return { key: 'fatigue', type: 'caution', iconName: 'bolt', label: `要注意 ${shortType} ${detail}` };
  }
  return null;
};

const ALERT_STYLES = {
  warning: { background: "oklch(0.32 0.10 45 / 0.6)", border: "1px solid oklch(0.50 0.14 45 / 0.5)", color: "oklch(0.82 0.14 55)" },
  caution: { background: "oklch(0.34 0.12 72 / 0.6)", border: "1px solid oklch(0.55 0.15 72 / 0.5)", color: "var(--amber)" },
  purple:  { background: "oklch(0.26 0.10 310 / 0.6)", border: "1px solid oklch(0.50 0.12 310 / 0.5)", color: "var(--purp)" },
  hot:     { background: "oklch(0.26 0.10 28 / 0.6)",  border: "1px solid oklch(0.50 0.14 28 / 0.5)",  color: "var(--neg)" },
  neutral: { background: "var(--bg-2)",                 border: "1px solid var(--rule)",                color: "var(--ink-2)" },
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

  const thStyle = (isName) => ({
    padding: "6px 8px",
    fontFamily: "var(--ff-mono)",
    fontWeight: 600,
    fontSize: 10,
    letterSpacing: "0.08em",
    color: "var(--ink-3)",
    textAlign: isName ? "left" : "right",
    borderBottom: "1px solid var(--rule)",
    whiteSpace: "nowrap",
  });

  return (
    <div
      style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, background: "oklch(0 0 0 / 0.75)" }}
      onClick={onClose}
    >
      <div
        style={{ background: "var(--bg-0)", border: "1px solid var(--rule-hi)", width: "100%", maxWidth: 680, maxHeight: "90vh", display: "flex", flexDirection: "column", overflow: "hidden" }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="rule-b" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--ff-mono)", fontWeight: 700, fontSize: 14 }}>
            <span style={{ color: awayWin ? "var(--ink-0)" : "var(--ink-4)" }}>{game.away_team}</span>
            <span style={{ fontSize: 18, color: awayWin ? "var(--amber)" : "var(--ink-4)" }}>{game.away_score}</span>
            <span style={{ color: "var(--ink-4)", fontSize: 12, fontWeight: 400 }}>-</span>
            <span style={{ fontSize: 18, color: homeWin ? "var(--amber)" : "var(--ink-4)" }}>{game.home_score}</span>
            <span style={{ color: homeWin ? "var(--ink-0)" : "var(--ink-4)" }}>{game.home_team}</span>
            <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)", fontWeight: 400, marginLeft: 4 }}>Final</span>
          </div>
          <button onClick={onClose} style={{ color: "var(--ink-3)", display: "flex", padding: 4 }}>
            <Icon name="close" size={16}/>
          </button>
        </div>

        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: 8 }}>
            <span className="think-dot"/>
            <span className="think-dot" style={{ animationDelay: ".2s" }}/>
            <span className="think-dot" style={{ animationDelay: ".4s" }}/>
            <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 4 }}>取得中...</span>
          </div>
        ) : !boxscore ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--ink-3)", fontSize: 13 }}>
            データを取得できませんでした
          </div>
        ) : (
          <>
            {/* Team tabs */}
            <div className="rule-b" style={{ display: "flex", flexShrink: 0 }}>
              {['away', 'home'].map(side => (
                <button
                  key={side}
                  onClick={() => setActiveTab(side)}
                  style={{
                    flex: 1, padding: "10px 0", fontSize: 12,
                    fontFamily: "var(--ff-mono)", fontWeight: 600,
                    color: activeTab === side ? "var(--amber)" : "var(--ink-3)",
                    borderBottom: activeTab === side ? "2px solid var(--amber)" : "2px solid transparent",
                    transition: "all .12s",
                  }}
                >
                  {boxscore[side]?.team}
                </button>
              ))}
            </div>

            {/* Content */}
            <div style={{ overflowY: "auto", flex: 1, padding: "12px 16px" }}>
              {/* Pitchers */}
              <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 8 }}>PITCHERS</div>
              <div style={{ overflowX: "auto", marginBottom: 20 }}>
                <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {['PITCHER','ERA','IP','H','R','ER','HR','K','BB','PT'].map(h => (
                        <th key={h} style={thStyle(h === 'PITCHER')}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {boxscore[activeTab]?.pitchers.map((p, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--rule-dim)" }}>
                        <td style={{ padding: "7px 8px" }}>
                          <div style={{ fontWeight: 600, color: "var(--ink-0)" }}>{p.name}</div>
                          {p.note && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{p.note}</div>}
                        </td>
                        {[p.era, p.ip, p.h, p.r, p.er, p.hr, p.k, p.bb, p.pitches].map((v, j) => (
                          <td key={j} className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Batters */}
              <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 8 }}>BATTERS</div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {['BATTER','AVG','AB','H','R','RBI','HR','BB','K','OBP','SLG','OPS'].map(h => (
                        <th key={h} style={thStyle(h === 'BATTER')}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {boxscore[activeTab]?.batters.map((b, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--rule-dim)" }}>
                        <td style={{ padding: "7px 8px" }}>
                          <div style={{ fontWeight: 600, color: "var(--ink-0)" }}>{b.name}</div>
                          <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{b.position}</div>
                        </td>
                        {[b.avg, b.ab, b.h, b.r, b.rbi, b.hr, b.bb, b.k, b.obp, b.slg, b.ops].map((v, j) => (
                          <td key={j} className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{v}</td>
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

  const statusBadge = () => {
    if (status === 'live') return (
      <span className="t-mono" style={{ fontSize: 10, color: "var(--pos)", border: "1px solid var(--pos-dim)", padding: "2px 6px", whiteSpace: "nowrap", flexShrink: 0 }}>
        {game.inning}回{game.inning_half === 'Top' ? '表' : '裏'}
      </span>
    );
    if (status === 'final') return (
      <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", border: "1px solid var(--rule)", padding: "2px 6px", flexShrink: 0 }}>Final</span>
    );
    if (status === 'preview') return (
      <span className="t-mono" style={{ fontSize: 10, color: "var(--info)", border: "1px solid var(--info)", padding: "2px 6px", flexShrink: 0, opacity: 0.7 }}>
        {game.game_time ?? '予定'}
      </span>
    );
    return null;
  };

  return (
    <button
      onClick={() => onClick(game)}
      style={{
        width: "100%", textAlign: "left",
        border: alerts.length > 0 ? "1px solid var(--amber-dim)" : "1px solid var(--rule)",
        background: "var(--bg-1)",
        padding: 12,
        display: "flex", flexDirection: "column", gap: 8,
        transition: "all .15s",
        boxShadow: alerts.length > 0 ? "inset 0 0 0 1px oklch(from var(--amber) l c h / 0.2)" : "none",
      }}
      onMouseEnter={e => { e.currentTarget.style.background = "var(--bg-2)"; e.currentTarget.style.borderColor = "var(--rule-hi)"; }}
      onMouseLeave={e => { e.currentTarget.style.background = "var(--bg-1)"; e.currentTarget.style.borderColor = alerts.length > 0 ? "var(--amber-dim)" : "var(--rule)"; }}
    >
      {/* Score row */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, flex: 1 }}>
          <span className="h-display" style={{ fontSize: 11, color: awayLeading ? "var(--ink-0)" : "var(--ink-4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {game.away_team}
          </span>
          <span className="t-mono" style={{ fontSize: 16, fontWeight: 700, color: awayLeading ? "var(--amber)" : "var(--ink-2)" }}>
            {game.away_score ?? '-'}
          </span>
          <span style={{ color: "var(--ink-4)", fontSize: 10 }}>:</span>
          <span className="t-mono" style={{ fontSize: 16, fontWeight: 700, color: homeLeading ? "var(--amber)" : "var(--ink-2)" }}>
            {game.home_score ?? '-'}
          </span>
          <span className="h-display" style={{ fontSize: 11, color: homeLeading ? "var(--ink-0)" : "var(--ink-4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {game.home_team}
          </span>
        </div>
        {statusBadge()}
      </div>

      {/* Pitcher info (live only) */}
      {status === 'live' && game.pitcher && (
        <div className="t-mono" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 10, color: "var(--ink-3)" }}>
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            <span>P: </span>
            <span style={{ color: "var(--ink-1)" }}>{game.pitcher}</span>
            {game.pitcher_stats?.pitches > 0 && (
              <span style={{ marginLeft: 4, color: game.pitcher_stats.pitches >= 100 ? "var(--amber)" : "var(--ink-3)", fontWeight: game.pitcher_stats.pitches >= 100 ? 600 : 400 }}>
                {game.pitcher_stats.pitches}球
              </span>
            )}
          </span>
          <span style={{ marginLeft: 8, flexShrink: 0, color: "var(--ink-4)" }}>
            {game.balls}-{game.strikes} {game.outs}out
          </span>
        </div>
      )}

      {/* Alert badges */}
      {alerts.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {alerts.map(alert => (
            <span
              key={alert.key}
              style={{
                ...ALERT_STYLES[alert.type],
                display: "inline-flex", alignItems: "center", gap: 4,
                fontSize: 10, padding: "2px 6px",
                fontFamily: "var(--ff-mono)",
              }}
            >
              <Icon name={alert.iconName} size={10}/>
              {alert.label}
            </span>
          ))}
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

  const SectionHeader = ({ dotColor, label }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
      <span style={{ width: 7, height: 7, background: dotColor, display: "inline-block" }}/>
      <span className="h-label" style={{ fontSize: 10, color: dotColor }}>{label}</span>
    </div>
  );

  return (
    <div style={{ width: "100%" }}>
      {selectedGame && (
        <BoxscoreModal
          game={selectedGame}
          onClose={() => setSelectedGame(null)}
          getIdToken={getIdToken}
        />
      )}

      {/* Header */}
      <div className="rule-b" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 12, marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span className="h-display" style={{ fontSize: 16 }}>全試合モニターボード</span>
          <div style={{ display: "flex", gap: 6 }}>
            <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)", border: "1px solid var(--rule)", padding: "2px 8px" }}>
              {totalGames} games
            </span>
            {anomalyCount > 0 && (
              <span style={{
                ...ALERT_STYLES.warning,
                display: "inline-flex", alignItems: "center", gap: 4,
                fontSize: 10, padding: "2px 8px", fontFamily: "var(--ff-mono)",
              }}>
                <Icon name="alert" size={10}/>
                {anomalyCount} alerts
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
            更新: {formatTime(lastUpdated)}
          </span>
          <button
            onClick={fetchGames}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", fontSize: 11,
              border: "1px solid var(--rule)", color: "var(--ink-2)",
              fontFamily: "var(--ff-mono)",
            }}
          >
            <Icon name="refresh" size={12}/>
            更新
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "80px 0", gap: 8 }}>
          <span className="think-dot"/>
          <span className="think-dot" style={{ animationDelay: ".2s" }}/>
          <span className="think-dot" style={{ animationDelay: ".4s" }}/>
          <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>取得中...</span>
        </div>
      ) : error ? (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--neg)", fontSize: 13 }}>{error}</div>
      ) : totalGames === 0 ? (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--ink-4)", fontSize: 13 }}>本日の試合データがありません</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

          {/* LIVE */}
          {liveGames.length > 0 && (
            <section>
              <SectionHeader dotColor="var(--pos)" label={`LIVE — ${liveGames.length}試合`}/>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 10 }}>
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

          {/* FINAL */}
          {finalGames.length > 0 && (
            <section>
              <SectionHeader dotColor="var(--ink-4)" label={`FINAL — ${finalGames.length}試合`}/>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 10 }}>
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

          {/* PREVIEW */}
          {previewGames.length > 0 && (
            <section>
              <SectionHeader dotColor="var(--info)" label={`UPCOMING — ${previewGames.length}試合`}/>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 10 }}>
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
