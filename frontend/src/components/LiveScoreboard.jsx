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

// ===== 走者ダイヤモンド =====
const BaseDiamond = ({ runners }) => {
  const base = (occupied) => ({
    position: "absolute", width: 14, height: 14,
    background: occupied ? "var(--amber)" : "var(--bg-3)",
    transform: "rotate(45deg)",
  });

  return (
    <div style={{ position: "relative", width: 48, height: 48, flexShrink: 0 }}>
      {/* 2B - top */}
      <div style={{ ...base(runners.second), top: 0, left: "50%", marginLeft: -7 }}/>
      {/* 3B - left */}
      <div style={{ ...base(runners.third), top: "50%", left: 0, marginTop: -7 }}/>
      {/* 1B - right */}
      <div style={{ ...base(runners.first), top: "50%", right: 0, marginTop: -7 }}/>
      {/* Home */}
      <div style={{ ...base(false), bottom: 0, left: "50%", marginLeft: -7 }}/>
    </div>
  );
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
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.era}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.ip}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.h}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.r}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.er}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.hr}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.k}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.bb}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{p.pitches}</td>
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
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.avg}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.ab}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.h}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.r}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.rbi}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.hr}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.bb}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.k}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.obp}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.slg}</td>
                        <td className="t-mono" style={{ textAlign: "right", padding: "7px 8px", color: "var(--ink-2)" }}>{b.ops}</td>
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

// ===== ゲームカード (進行中) =====
const GameCard = ({ game }) => {
  const inningText = `${game.inning}回${game.inning_half === 'Top' ? '表' : '裏'}`;
  const hasRunners = game.runners && (game.runners.first || game.runners.second || game.runners.third);

  return (
    <div style={{ border: "1px solid var(--rule)", background: "var(--bg-1)", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Score + inning */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: "var(--ff-mono)", fontWeight: 700, fontSize: 15 }}>
          <span style={{ color: "var(--ink-0)" }}>{game.away_team}</span>
          <span style={{ fontSize: 22, color: "var(--amber)" }}>{game.away_score}</span>
          <span style={{ color: "var(--ink-3)", fontSize: 13, fontWeight: 400 }}>vs</span>
          <span style={{ fontSize: 22, color: "var(--amber)" }}>{game.home_score}</span>
          <span style={{ color: "var(--ink-0)" }}>{game.home_team}</span>
        </div>
        <span className="t-mono" style={{ fontSize: 11, color: "var(--pos)", border: "1px solid var(--pos-dim)", padding: "2px 8px" }}>
          {inningText}
        </span>
      </div>

      {/* Pitcher / Batter + Base diamond */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, flex: 1 }}>
          {/* Pitcher */}
          <div style={{ border: "1px solid var(--rule)", background: "var(--bg-0)", padding: "8px 10px" }}>
            <span className="h-label" style={{ fontSize: 8, color: "var(--ink-4)", display: "block", marginBottom: 2 }}>投手</span>
            <span style={{ fontSize: 13, color: "var(--ink-0)", fontWeight: 600 }}>{game.pitcher}</span>
            {game.pitcher_stats?.pitches > 0 && (
              <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)", display: "block", marginTop: 2 }}>
                {game.pitcher_stats.pitches}P | {game.pitcher_stats.ip}IP {game.pitcher_stats.k}K {game.pitcher_stats.er}ER
              </span>
            )}
          </div>
          {/* Batter */}
          <div style={{ border: "1px solid var(--rule)", background: "var(--bg-0)", padding: "8px 10px" }}>
            <span className="h-label" style={{ fontSize: 8, color: "var(--ink-4)", display: "block", marginBottom: 2 }}>打者</span>
            <span style={{ fontSize: 13, color: "var(--ink-0)", fontWeight: 600 }}>{game.batter}</span>
            {game.batter_stats && (
              <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)", display: "block", marginTop: 2 }}>
                {game.batter_stats.h}-{game.batter_stats.ab}
                {game.batter_stats.rbi > 0 && ` | ${game.batter_stats.rbi}RBI`}
                {game.batter_stats.hr > 0 && ` ${game.batter_stats.hr}HR`}
                {game.batter_stats.sb > 0 && ` ${game.batter_stats.sb}SB`}
                {game.batter_stats.bb > 0 && ` ${game.batter_stats.bb}BB`}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
          <BaseDiamond runners={game.runners || {}} />
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-2)", whiteSpace: "nowrap" }}>
            {game.balls}-{game.strikes}, {game.outs} Out{game.outs !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Last pitch chips */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        {game.last_pitch?.pitch_type && (
          <span className="t-mono" style={{
            fontSize: 11, padding: "2px 8px",
            border: "1px solid var(--info)", color: "var(--info)",
            background: "oklch(from var(--info) l c h / 0.08)",
          }}>
            {game.last_pitch.pitch_type}
          </span>
        )}
        {game.last_pitch?.speed && (
          <span className="t-mono" style={{ fontSize: 11, padding: "2px 8px", border: "1px solid var(--rule)", color: "var(--ink-1)" }}>
            {game.last_pitch.speed.toFixed(1)} mph
          </span>
        )}
        {game.last_pitch?.pitch_call && (
          <span style={{ fontSize: 11, color: "var(--ink-3)" }}>— {game.last_pitch.pitch_call}</span>
        )}
        {game.last_event && !game.last_pitch?.pitch_call && (
          <span style={{ fontSize: 11, color: "var(--ink-2)" }}>— {game.last_event}</span>
        )}
      </div>

      {/* Runners on base */}
      {hasRunners && (
        <div style={{ display: "flex", gap: 12, fontSize: 11, color: "var(--ink-3)" }}>
          {game.runners.third && <span>3塁: <span style={{ color: "var(--ink-0)" }}>{game.runners.third}</span></span>}
          {game.runners.second && <span>2塁: <span style={{ color: "var(--ink-0)" }}>{game.runners.second}</span></span>}
          {game.runners.first && <span>1塁: <span style={{ color: "var(--ink-0)" }}>{game.runners.first}</span></span>}
        </div>
      )}

      {/* Scoring plays */}
      {game.scoring_plays?.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span className="h-label" style={{ fontSize: 8, color: "var(--ink-4)" }}>RUNS</span>
          {game.scoring_plays.map((sp, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
              <span className="t-mono" style={{ color: "var(--amber)", fontWeight: 700, minWidth: 32 }}>
                {sp.runs > 0 ? `+${sp.runs}` : '—'}
              </span>
              <span style={{ color: "var(--ink-0)", fontWeight: 600 }}>{sp.batter}</span>
              <span style={{ color: "var(--ink-2)" }}>
                {sp.event}{sp.season_hr != null ? ` (${sp.season_hr})` : ''}
              </span>
              <span style={{ color: "var(--ink-4)" }}>
                {sp.half === 'top' ? '表' : '裏'}{sp.inning}回
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Pitch sequence */}
      {game.pitch_sequence?.length > 0 && (
        <div style={{ border: "1px solid var(--rule-dim)", background: "var(--bg-0)", padding: "8px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
          <span className="h-label" style={{ fontSize: 8, color: "var(--ink-4)", marginBottom: 2 }}>投球シーケンス</span>
          {[...game.pitch_sequence].reverse().map((p) => {
            const call = p.pitch_call ?? '';
            const isStrike = /strike|foul/i.test(call);
            const isBall = /ball/i.test(call);
            const isInPlay = /^in play/i.test(call);
            const callColor = isStrike ? 'var(--neg)' : isBall ? 'var(--info)' : isInPlay ? 'var(--pos)' : 'var(--ink-3)';
            return (
              <div key={p.num} className="t-mono" style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
                <span style={{ color: "var(--ink-4)", width: 16, textAlign: "right" }}>{p.num}:</span>
                <span style={{ fontWeight: 600, color: callColor }}>{call || '—'}</span>
                {p.pitch_type && (
                  <span style={{ color: "var(--ink-4)" }}>({p.pitch_type}{p.speed != null ? ` / ${p.speed} mph` : ''})</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ===== JST 日付ユーティリティ =====
const getJstDateInfo = (offsetDays = 0) => {
  const now = new Date();
  const jst = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));
  jst.setDate(jst.getDate() + offsetDays);
  const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const label = `${jst.getMonth() + 1}/${jst.getDate()} (${weekdays[jst.getDay()]})`;
  const dateStr = `${jst.getFullYear()}-${String(jst.getMonth() + 1).padStart(2, '0')}-${String(jst.getDate()).padStart(2, '0')}`;
  return { label, dateStr };
};

// ===== メインコンポーネント =====
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
    const dateStr = activeTab === 'today' ? todayInfo.dateStr : activeTab;
    if (dateStr <= todayInfo.dateStr) {
      fetchHighlights(dateStr);
    } else {
      setHighlights([]);
    }
  }, [activeTab, fetchSchedule, fetchHighlights, todayInfo.dateStr]);

  const tabBtn = (active) => ({
    padding: "5px 14px",
    fontSize: 10.5,
    fontFamily: "var(--ff-mono)",
    letterSpacing: "0.06em",
    fontWeight: active ? 600 : 400,
    background: active ? "var(--amber)" : "transparent",
    color: active ? "var(--bg-0)" : "var(--ink-3)",
    border: `1px solid ${active ? "var(--amber)" : "var(--rule)"}`,
    whiteSpace: "nowrap",
    flexShrink: 0,
    transition: "all .12s",
  });

  const LoadingState = () => (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "80px 0", gap: 8 }}>
      <span className="think-dot"/>
      <span className="think-dot" style={{ animationDelay: ".2s" }}/>
      <span className="think-dot" style={{ animationDelay: ".4s" }}/>
      <span className="t-mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>取得中...</span>
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
      <div className="rule-b" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 12, marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span className="live-dot"/>
          <span className="h-display" style={{ fontSize: 16 }}>試合速報</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>60秒ごと自動更新</span>
        </div>
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

      {/* Date tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 14, overflowX: "auto", paddingBottom: 2 }} className="scrollbar-none">
        <button onClick={() => setActiveTab(yesterdayInfo.dateStr)} style={tabBtn(activeTab === yesterdayInfo.dateStr)}>
          {yesterdayInfo.label}
        </button>
        <button onClick={() => setActiveTab('today')} style={tabBtn(activeTab === 'today')}>
          {todayInfo.label}
        </button>
        {futureDays.map(day => (
          <button key={day.dateStr} onClick={() => setActiveTab(day.dateStr)} style={tabBtn(activeTab === day.dateStr)}>
            {day.label}
          </button>
        ))}
      </div>

      {/* Last updated */}
      {lastUpdated && activeTab === 'today' && (
        <p className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 12 }}>
          最終更新: {lastUpdated.toLocaleTimeString('ja-JP')}
        </p>
      )}

      {/* Highlights */}
      {highlights.length > 0 && (
        <div style={{ border: "1px solid var(--amber-dim)", background: "oklch(from var(--bg-1) l c h / 0.6)", padding: "12px 16px", marginBottom: 16 }}>
          <div className="h-label" style={{ fontSize: 9, color: "var(--amber)", marginBottom: 8 }}>HIGHLIGHTS</div>
          <ul style={{ display: "flex", flexDirection: "column", gap: 6, listStyle: "none", margin: 0, padding: 0 }}>
            {highlights.map((h, i) => (
              <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: "var(--ink-1)" }}>
                <span style={{ color: "var(--amber)", flexShrink: 0, marginTop: 2 }}>●</span>
                <span>{h.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Today tab content */}
      {activeTab === 'today' && (
        loading ? <LoadingState/> : error ? (
          <div style={{ border: "1px solid var(--neg-dim)", background: "oklch(from var(--neg) l c h / 0.08)", padding: 24, textAlign: "center" }}>
            <p style={{ color: "var(--neg)", fontWeight: 600, marginBottom: 4 }}>データ取得エラー</p>
            <p className="t-mono" style={{ fontSize: 11, color: "var(--neg)", opacity: 0.7 }}>{error}</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Live games */}
            {liveGames.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="live-dot"/>
                  <span className="h-label" style={{ fontSize: 10, color: "var(--pos)" }}>{liveGames.length}試合進行中</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))", gap: 14 }}>
                  {liveGames.map((game) => (
                    <GameCard key={game.gamePk} game={game} />
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ border: "1px solid var(--rule)", background: "var(--bg-1)", padding: 32, textAlign: "center" }}>
                <Icon name="radio" size={28} style={{ color: "var(--ink-4)", margin: "0 auto 8px" }}/>
                <p style={{ color: "var(--ink-3)", fontSize: 13 }}>現在進行中の試合はありません</p>
              </div>
            )}

            {/* Preview games */}
            {previewGames.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <span className="h-label" style={{ fontSize: 10, color: "var(--ink-3)" }}>本日予定</span>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 6 }}>
                  {previewGames.map((game) => (
                    <div
                      key={game.gamePk}
                      style={{ border: "1px solid var(--rule-dim)", background: "var(--bg-1)", padding: "10px 14px", display: "flex", alignItems: "center", justifyContent: "space-between" }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                        <div>
                          <div style={{ color: "var(--ink-1)" }}>{game.away_team}</div>
                          {game.away_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.away_wins}-{game.away_losses}</div>}
                        </div>
                        <span style={{ color: "var(--ink-4)", margin: "0 4px" }}>@</span>
                        <div>
                          <div style={{ color: "var(--ink-1)" }}>{game.home_team}</div>
                          {game.home_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.home_wins}-{game.home_losses}</div>}
                        </div>
                      </div>
                      <span className="t-mono" style={{ fontSize: 11, color: "var(--info)" }}>{game.start_time_jst} JST</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Final games */}
            {finalGames.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <span className="h-label" style={{ fontSize: 10, color: "var(--ink-3)" }}>本日終了</span>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 6 }}>
                  {finalGames.map((game) => {
                    const awayWin = game.away_score > game.home_score;
                    const homeWin = game.home_score > game.away_score;
                    return (
                      <button
                        key={game.gamePk}
                        onClick={() => setSelectedGame(game)}
                        style={{ border: "1px solid var(--rule)", background: "var(--bg-1)", padding: "10px 14px", display: "flex", alignItems: "center", justifyContent: "space-between", textAlign: "left", width: "100%", transition: "all .12s" }}
                        onMouseEnter={e => { e.currentTarget.style.background = "var(--bg-2)"; e.currentTarget.style.borderColor = "var(--rule-hi)"; }}
                        onMouseLeave={e => { e.currentTarget.style.background = "var(--bg-1)"; e.currentTarget.style.borderColor = "var(--rule)"; }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                          <div>
                            <div style={{ color: awayWin ? "var(--ink-0)" : "var(--ink-4)", fontWeight: awayWin ? 600 : 400 }}>{game.away_team}</div>
                            {game.away_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.away_wins}-{game.away_losses}</div>}
                          </div>
                          <span className="t-mono" style={{ fontSize: 15, fontWeight: 700, color: awayWin ? "var(--amber)" : "var(--ink-4)" }}>{game.away_score}</span>
                          <span style={{ color: "var(--ink-4)" }}>-</span>
                          <span className="t-mono" style={{ fontSize: 15, fontWeight: 700, color: homeWin ? "var(--amber)" : "var(--ink-4)" }}>{game.home_score}</span>
                          <div>
                            <div style={{ color: homeWin ? "var(--ink-0)" : "var(--ink-4)", fontWeight: homeWin ? 600 : 400 }}>{game.home_team}</div>
                            {game.home_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.home_wins}-{game.home_losses}</div>}
                          </div>
                        </div>
                        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", flexShrink: 0 }}>Final →</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )
      )}

      {/* Other date tabs */}
      {activeTab !== 'today' && (
        scheduleLoading ? <LoadingState/> : scheduledGames.length === 0 ? (
          <div style={{ border: "1px solid var(--rule)", background: "var(--bg-1)", padding: 32, textAlign: "center" }}>
            <p style={{ color: "var(--ink-4)", fontSize: 13 }}>試合情報はありません</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 6 }}>
            {scheduledGames.map((game) => {
              if (game.status === 'Final') {
                const awayWin = game.away_score > game.home_score;
                const homeWin = game.home_score > game.away_score;
                return (
                  <button
                    key={game.gamePk}
                    onClick={() => setSelectedGame(game)}
                    style={{ border: "1px solid var(--rule)", background: "var(--bg-1)", padding: "10px 14px", display: "flex", alignItems: "center", justifyContent: "space-between", textAlign: "left", width: "100%", transition: "all .12s" }}
                    onMouseEnter={e => { e.currentTarget.style.background = "var(--bg-2)"; }}
                    onMouseLeave={e => { e.currentTarget.style.background = "var(--bg-1)"; }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                      <div>
                        <div style={{ color: awayWin ? "var(--ink-0)" : "var(--ink-4)", fontWeight: awayWin ? 600 : 400 }}>{game.away_team}</div>
                        {game.away_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.away_wins}-{game.away_losses}</div>}
                      </div>
                      <span className="t-mono" style={{ fontSize: 15, fontWeight: 700, color: awayWin ? "var(--amber)" : "var(--ink-4)" }}>{game.away_score}</span>
                      <span style={{ color: "var(--ink-4)" }}>-</span>
                      <span className="t-mono" style={{ fontSize: 15, fontWeight: 700, color: homeWin ? "var(--amber)" : "var(--ink-4)" }}>{game.home_score}</span>
                      <div>
                        <div style={{ color: homeWin ? "var(--ink-0)" : "var(--ink-4)", fontWeight: homeWin ? 600 : 400 }}>{game.home_team}</div>
                        {game.home_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.home_wins}-{game.home_losses}</div>}
                      </div>
                    </div>
                    <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>Final →</span>
                  </button>
                );
              }
              return (
                <div
                  key={game.gamePk}
                  style={{ border: "1px solid var(--rule-dim)", background: "var(--bg-1)", padding: "10px 14px", display: "flex", alignItems: "center", justifyContent: "space-between" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                    <div>
                      <div style={{ color: "var(--ink-1)" }}>{game.away_team}</div>
                      {game.away_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.away_wins}-{game.away_losses}</div>}
                    </div>
                    <span style={{ color: "var(--ink-4)", margin: "0 4px" }}>@</span>
                    <div>
                      <div style={{ color: "var(--ink-1)" }}>{game.home_team}</div>
                      {game.home_wins != null && <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{game.home_wins}-{game.home_losses}</div>}
                    </div>
                  </div>
                  <span className="t-mono" style={{ fontSize: 11, color: "var(--info)" }}>{game.start_time_jst} JST</span>
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
};

export default LiveScoreboard;
