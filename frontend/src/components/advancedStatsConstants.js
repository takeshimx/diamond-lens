// ============================================================
// Metric Definitions — 追加・削除はここだけ
// ============================================================
export const PITCHING_METRICS = [
  { id: 'P1', name: 'Pitch Tunnel Score',   nameJp: 'ピッチトンネルスコア',  question: '最も球の見分けがつきにくい投手は？',   apiReady: true  },
  { id: 'P2', name: 'Pressure Dominance',   nameJp: 'プレッシャー支配力',    question: '最もプレッシャーに強い投手は？',       apiReady: true  },
  { id: 'P3', name: 'Stamina Score',        nameJp: 'スタミナスコア',        question: '最もスタミナのある投手は？',           apiReady: true  },
  { id: 'P4', name: 'Two-Strike Finisher',  nameJp: '2ストライク仕留め力',   question: '最も追い込んでから仕留める投手は？',   apiReady: true  },
  { id: 'P6', name: 'Arsenal Effectiveness',nameJp: '球種構成効果',          question: '最も多彩で効果的な球種構成は？',       apiReady: true  },
  { id: 'P7', name: 'First-Pitch Strike',   nameJp: '初球ストライク支配力',  question: '初球の支配力が最も高い投手は？',       apiReady: false },
];

export const BATTING_METRICS = [
  { id: 'B1', name: 'Swing Efficiency',     nameJp: 'スイング効率',          question: '最も効率的なスイングをする打者は？',   apiReady: false },
  { id: 'B2', name: 'Plate Discipline',     nameJp: '選球眼スコア',          question: '最も選球眼の良い打者は？',             apiReady: true  },
  { id: 'B3', name: 'Clutch Hitting',       nameJp: 'クラッチ打撃',          question: '最もチャンスに強い打者は？',           apiReady: true  },
  { id: 'B4', name: 'Contact Consistency',  nameJp: 'コンタクト一貫性',      question: '最もコンタクトの質が安定している打者は？', apiReady: true  },
  { id: 'B5', name: 'Adjustment Ability',   nameJp: '対応力',                question: '同一投手への対応力が最も高い打者は？', apiReady: false },
  { id: 'B6', name: 'Spray Mastery',        nameJp: '打球方向マスタリー',    question: '最も広角に打ち分けられる打者は？',     apiReady: false },
  { id: 'B7', name: 'Power Under Pressure', nameJp: 'プレッシャー下パワー',  question: 'チャンスで最も長打力を発揮する打者は？', apiReady: false },
];

// ============================================================
// Dummy Data (API未接続の指標用)
// ============================================================
export const DUMMY_PITCHERS = [
  { id: 1,  name: 'Shohei Ohtani',    team: 'LAD' },
  { id: 2,  name: 'Gerrit Cole',      team: 'NYY' },
  { id: 3,  name: 'Corbin Burns',     team: 'BAL' },
  { id: 4,  name: 'Zack Wheeler',     team: 'PHI' },
  { id: 5,  name: 'Paul Skenes',      team: 'PIT' },
  { id: 6,  name: 'Chris Sale',       team: 'ATL' },
  { id: 7,  name: 'Spencer Strider',  team: 'ATL' },
  { id: 8,  name: 'Logan Webb',       team: 'SF'  },
  { id: 9,  name: 'Tarik Skubal',     team: 'DET' },
  { id: 10, name: 'Dylan Cease',      team: 'SD'  },
];

export const DUMMY_BATTERS = [
  { id: 101, name: 'Shohei Ohtani',     team: 'LAD' },
  { id: 102, name: 'Aaron Judge',       team: 'NYY' },
  { id: 103, name: 'Mookie Betts',      team: 'LAD' },
  { id: 104, name: 'Ronald Acuna Jr.',  team: 'ATL' },
  { id: 105, name: 'Juan Soto',         team: 'NYM' },
  { id: 106, name: 'Freddie Freeman',   team: 'LAD' },
  { id: 107, name: 'Corey Seager',      team: 'TEX' },
  { id: 108, name: 'Trea Turner',       team: 'PHI' },
  { id: 109, name: 'Marcus Semien',     team: 'TEX' },
  { id: 110, name: 'Bobby Witt Jr.',    team: 'KC'  },
];

export const seededRandom = (seed) => {
  let s = seed;
  return () => { s = (s * 16807 + 0) % 2147483647; return (s - 1) / 2147483646; };
};

export const generateDummyRankings = (metrics, players) => {
  const result = {};
  metrics.forEach((metric) => {
    if (metric.apiReady) return;
    const rng = seededRandom(metric.id.charCodeAt(0) * 100 + metric.id.charCodeAt(1));
    const ranked = players
      .map((p) => ({ ...p, score: Math.round((60 + rng() * 35) * 10) / 10 }))
      .sort((a, b) => b.score - a.score);
    result[metric.id] = ranked;
  });
  return result;
};

export const generateDummyProfile = (metrics, playerId) => {
  const rng = seededRandom(playerId * 7);
  return metrics.map((m) => ({
    metricId: m.id, metricName: m.name, metricNameJp: m.nameJp,
    score: Math.round((65 + rng() * 30) * 10) / 10,
    rank: Math.floor(rng() * 20) + 1, leagueAvg: 75,
  }));
};

export const generateDummyTrends = (metrics, playerId) => {
  const rng = seededRandom(playerId * 13);
  return [2021, 2022, 2023, 2024].map((year) => {
    const row = { season: year };
    metrics.forEach((m) => { row[m.id] = Math.round((65 + rng() * 30) * 10) / 10; });
    return row;
  });
};

// ============================================================
// Color / Chart Helpers
// ============================================================
export const PITCH_TYPE_COLORS = {
  '4-Seam Fastball': '#ef4444', 'Sinker': '#f97316',     'Cutter': '#eab308',
  'Slider': '#3b82f6',          'Sweeper': '#6366f1',     'Curveball': '#8b5cf6',
  'Changeup': '#22c55e',        'Split-Finger': '#14b8a6','Knuckle Curve': '#a855f7',
  'Slurve': '#ec4899',          'Screwball': '#f43f5e',   'Knuckleball': '#64748b',
};
export const getPitchColor = (name) => PITCH_TYPE_COLORS[name] || '#6b7280';

export const getScoreColor = (score) => {
  if (score >= 90) return 'text-green-400';
  if (score >= 80) return 'text-emerald-400';
  if (score >= 70) return 'text-yellow-400';
  return 'text-orange-400';
};
export const getBarFill = (score) => {
  if (score >= 90) return '#22c55e';
  if (score >= 80) return '#10b981';
  if (score >= 70) return '#eab308';
  return '#f97316';
};

export const RADAR_COLORS = ['#3b82f6', '#ef4444', '#6b7280'];
export const LINE_COLORS  = ['#3b82f6', '#8b5cf6', '#22c55e', '#ef4444', '#eab308', '#ec4899', '#06b6d4'];

export const getBackendUrl = () => {
  if (window.location.hostname.includes('run.app')) {
    return 'https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app';
  }
  const currentUrl = window.location.href;
  if (currentUrl.includes('app.github.dev')) {
    return currentUrl.replace('-5173.app.github.dev', '-8000.app.github.dev').split('?')[0];
  }
  return 'http://localhost:8000';
};
