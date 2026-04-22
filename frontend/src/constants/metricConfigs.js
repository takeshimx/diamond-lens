// ============================================================
// 打撃指標 表示名マップ（年度別トレンドチャート用）
// callFixedQueryAPI 内 season_batting_stats / season_pitching_stats で使用
// ============================================================
export const BATTING_METRIC_DISPLAY_NAMES = {
  avg: '打率',
  obp: '出塁率',
  slg: '長打率',
  ops: 'OPS',
  h: '安打数',
  hr: '本塁打',
  homeruns: 'ホームラン',
  doubles: '二塁打',
  triples: '三塁打',
  singles: '単打',
  rbi: '打点',
  r: '得点',
  bb: '四球',
  so: '三振',
  war: 'fWAR',
  woba: 'wOBA',
  wrcplus: 'wRC+',
};

// ============================================================
// 投球指標 表示名マップ（年度別トレンドチャート用）
// ============================================================
export const PITCHING_METRIC_DISPLAY_NAMES = {
  era: '防御率',
  whip: 'WHIP',
  so: '三振数',
  bb: '四球数',
  w: '勝利数',
  l: '敗戦数',
  sv: 'セーブ数',
  fip: 'FIP',
  war: 'fWAR',
  k_9: 'K/9',
  bb_9: 'BB/9',
  hr: '被本塁打',
  ip: '投球回',
  g: '登板数',
  gs: '先発数',
};

// ============================================================
// 月別打撃チャート設定ファクトリ
// getMonthlyBattingChartConfig(metric, season, playerName) で使用
// ============================================================
const MONTHLY_BATTING_CHART_CONFIGS = {
  // Rate stats (line charts)
  avg: (playerName, season) => ({
    title: `${playerName} ${season}年月別打率推移`,
    yAxisLabel: '打率',
    yDomain: [0, 0.5],
    lineColor: '#3B82F6',
    chartType: 'line',
  }),
  batting_average: (playerName, season) => ({
    title: `${playerName} ${season}年月別打率推移`,
    yAxisLabel: '打率',
    yDomain: [0, 0.5],
    lineColor: '#3B82F6',
    chartType: 'line',
  }),
  obp: (playerName, season) => ({
    title: `${playerName} ${season}年月別出塁率推移`,
    yAxisLabel: '出塁率',
    yDomain: [0, 0.5],
    lineColor: '#10B981',
    chartType: 'line',
  }),
  slg: (playerName, season) => ({
    title: `${playerName} ${season}年月別長打率推移`,
    yAxisLabel: '長打率',
    yDomain: [0, 0.8],
    lineColor: '#F59E0B',
    chartType: 'line',
  }),
  ops: (playerName, season) => ({
    title: `${playerName} ${season}年月別OPS推移`,
    yAxisLabel: 'OPS',
    yDomain: [0, 1.5],
    lineColor: '#8B5CF6',
    chartType: 'line',
  }),
  woba: (playerName, season) => ({
    title: `${playerName} ${season}年月別wOBA推移`,
    yAxisLabel: 'wOBA',
    yDomain: [0, 0.5],
    lineColor: '#EC4899',
    chartType: 'line',
  }),
  war: (playerName, season) => ({
    title: `${playerName} ${season}年月別WAR推移`,
    yAxisLabel: 'WAR',
    yDomain: [-1, 4],
    lineColor: '#6366F1',
    chartType: 'line',
  }),
  wrc_plus: (playerName, season) => ({
    title: `${playerName} ${season}年月別wRC+推移`,
    yAxisLabel: 'wRC+',
    yDomain: [0, 200],
    lineColor: '#DC2626',
    chartType: 'line',
  }),

  // Counting stats (bar charts)
  hits: (playerName, season) => ({
    title: `${playerName} ${season}年月別安打数`,
    yAxisLabel: '安打数',
    yDomain: [0, 50],
    lineColor: '#10B981',
    chartType: 'bar',
  }),
  homeruns: (playerName, season) => ({
    title: `${playerName} ${season}年月別ホームラン数`,
    yAxisLabel: 'ホームラン数',
    yDomain: [0, 15],
    lineColor: '#EF4444',
    chartType: 'bar',
  }),
  home_runs: (playerName, season) => ({
    title: `${playerName} ${season}年月別ホームラン数`,
    yAxisLabel: 'ホームラン数',
    yDomain: [0, 15],
    lineColor: '#EF4444',
    chartType: 'bar',
  }),
  doubles: (playerName, season) => ({
    title: `${playerName} ${season}年月別二塁打数`,
    yAxisLabel: '二塁打数',
    yDomain: [0, 12],
    lineColor: '#F59E0B',
    chartType: 'bar',
  }),
  triples: (playerName, season) => ({
    title: `${playerName} ${season}年月別三塁打数`,
    yAxisLabel: '三塁打数',
    yDomain: [0, 5],
    lineColor: '#8B5CF6',
    chartType: 'bar',
  }),
  singles: (playerName, season) => ({
    title: `${playerName} ${season}年月別単打数`,
    yAxisLabel: '単打数',
    yDomain: [0, 40],
    lineColor: '#06B6D4',
    chartType: 'bar',
  }),
  rbi: (playerName, season) => ({
    title: `${playerName} ${season}年月別打点数`,
    yAxisLabel: '打点数',
    yDomain: [0, 30],
    lineColor: '#DC2626',
    chartType: 'bar',
  }),
  runs: (playerName, season) => ({
    title: `${playerName} ${season}年月別得点数`,
    yAxisLabel: '得点数',
    yDomain: [0, 30],
    lineColor: '#059669',
    chartType: 'bar',
  }),
  walks: (playerName, season) => ({
    title: `${playerName} ${season}年月別四球数`,
    yAxisLabel: '四球数',
    yDomain: [0, 25],
    lineColor: '#7C3AED',
    chartType: 'bar',
  }),
  strikeouts: (playerName, season) => ({
    title: `${playerName} ${season}年月別三振数`,
    yAxisLabel: '三振数',
    yDomain: [0, 40],
    lineColor: '#DC2626',
    chartType: 'bar',
  }),

  // Rate percentage stats (line charts)
  hard_hit_rate: (playerName, season) => ({
    title: `${playerName} ${season}年月別ハードヒット率推移`,
    yAxisLabel: 'ハードヒット率',
    yDomain: [0, 1],
    lineColor: '#F59E0B',
    chartType: 'line',
  }),
  barrels_rate: (playerName, season) => ({
    title: `${playerName} ${season}年月別バレル率推移`,
    yAxisLabel: 'バレル率',
    yDomain: [0, 1],
    lineColor: '#10B981',
    chartType: 'line',
  }),
  walk_rate: (playerName, season) => ({
    title: `${playerName} ${season}年月別四球率推移`,
    yAxisLabel: '四球率 (%)',
    yDomain: [0, 25],
    lineColor: '#7C3AED',
    chartType: 'line',
  }),
  strikeout_rate: (playerName, season) => ({
    title: `${playerName} ${season}年月別三振率推移`,
    yAxisLabel: '三振率',
    yDomain: [0, 1],
    lineColor: '#DC2626',
    chartType: 'line',
  }),
  swing_rate: (playerName, season) => ({
    title: `${playerName} ${season}年月別スイング率推移`,
    yAxisLabel: 'スイング率 (%)',
    yDomain: [0, 100],
    lineColor: '#F59E0B',
    chartType: 'line',
  }),
  contact_rate: (playerName, season) => ({
    title: `${playerName} ${season}年月別コンタクト率推移`,
    yAxisLabel: 'コンタクト率 (%)',
    yDomain: [0, 100],
    lineColor: '#10B981',
    chartType: 'line',
  }),

  // Legacy/other stats
  batting_average_at_risp: (playerName, season) => ({
    title: `${playerName} ${season}年月別RISP打率推移`,
    yAxisLabel: 'RISP打率',
    yDomain: [0, 0.6],
    lineColor: '#10B981',
    chartType: 'line',
  }),
};

/**
 * 月別打撃チャート設定を返す。
 * 未知の指標は avg のフォールバックを使用。
 */
export const getMonthlyBattingChartConfig = (metric, season, playerName) => {
  const factory = MONTHLY_BATTING_CHART_CONFIGS[metric] ?? MONTHLY_BATTING_CHART_CONFIGS.avg;
  const config = factory(playerName, season);
  return {
    title: config.title,
    xAxis: 'month',
    dataKey: 'value',
    lineColor: config.lineColor,
    lineName: config.yAxisLabel,
    yDomain: config.yDomain,
    chartType: config.chartType,
  };
};

// ============================================================
// 月別打撃チャート 回答テキスト
// ============================================================
const MONTHLY_BATTING_ANSWER_TEXTS = {
  avg: (p, s) => `${p}選手の${s}年月別打率推移をチャートで表示します。`,
  batting_average: (p, s) => `${p}選手の${s}年月別打率推移をチャートで表示します。`,
  obp: (p, s) => `${p}選手の${s}年月別出塁率推移をチャートで表示します。`,
  slg: (p, s) => `${p}選手の${s}年月別長打率推移をチャートで表示します。`,
  ops: (p, s) => `${p}選手の${s}年月別OPS推移をチャートで表示します。`,
  hits: (p, s) => `${p}選手の${s}年月別安打数をチャートで表示します。`,
  homeruns: (p, s) => `${p}選手の${s}年月別ホームラン数をチャートで表示します。`,
  home_runs: (p, s) => `${p}選手の${s}年月別ホームラン数をチャートで表示します。`,
  doubles: (p, s) => `${p}選手の${s}年月別二塁打数をチャートで表示します。`,
  triples: (p, s) => `${p}選手の${s}年月別三塁打数をチャートで表示します。`,
  singles: (p, s) => `${p}選手の${s}年月別単打数をチャートで表示します。`,
  rbi: (p, s) => `${p}選手の${s}年月別打点数をチャートで表示します。`,
  runs: (p, s) => `${p}選手の${s}年月別得点数をチャートで表示します。`,
  walks: (p, s) => `${p}選手の${s}年月別四球数をチャートで表示します。`,
  strikeouts: (p, s) => `${p}選手の${s}年月別三振数をチャートで表示します。`,
  hard_hit_rate: (p, s) => `${p}選手の${s}年月別ハードヒット率推移をチャートで表示します。`,
  barrels_rate: (p, s) => `${p}選手の${s}年月別バレル率推移をチャートで表示します。`,
  walk_rate: (p, s) => `${p}選手の${s}年月別四球率推移をチャートで表示します。`,
  strikeout_rate: (p, s) => `${p}選手の${s}年月別三振率推移をチャートで表示します。`,
  swing_rate: (p, s) => `${p}選手の${s}年月別スイング率推移をチャートで表示します。`,
  contact_rate: (p, s) => `${p}選手の${s}年月別コンタクト率推移をチャートで表示します。`,
  batting_average_at_risp: (p, s) => `${p}選手の${s}年月別RISP打率推移をチャートで表示します。`,
};

export const getMonthlyBattingAnswerText = (metric, season, playerName) => {
  const fn = MONTHLY_BATTING_ANSWER_TEXTS[metric] ?? MONTHLY_BATTING_ANSWER_TEXTS.avg;
  return fn(playerName, season);
};

// ============================================================
// handleCustomQuery: 打撃指標フロントエンド→バックエンドマッピング
// ============================================================
export const SEASON_BATTING_METRIC_MAPPING = {
  plate_appearances: 'pa',
  at_bats: 'ab',
  games: 'g',
  batting_average: 'avg',
  hits: 'h',
  home_runs: 'hr',
  doubles: 'doubles',
  triples: 'triples',
  singles: 'singles',
  obp: 'obp',
  slg: 'slg',
  ops: 'ops',
  walks: 'bb',
  rbi: 'rbi',
  runs: 'r',
  woba: 'woba',
  war: 'war',
  wrc_plus: 'wrcplus',
  strikeouts: 'so',
  babip: 'babip',
  iso: 'iso',
  hard_hit_rate: 'hardhitpct',
  barrels_rate: 'barrelpct',
  batting_average_at_risp: 'batting_average_at_risp',
  slugging_percentage_at_risp: 'slugging_percentage_at_risp',
  home_runs_at_risp: 'home_runs_at_risp',
  launch_angle: null,
  exit_velocity: null,
  walk_rate: null,
  strikeout_rate: null,
  swing_rate: null,
  contact_rate: null,
};

// ============================================================
// handleCustomQuery: 月別トレンドフロントエンド→バックエンドマッピング
// ============================================================
export const MONTHLY_TRENDS_METRIC_MAPPING = {
  monthly_avg: 'avg',
  monthly_hits: 'hits',
  monthly_hr: 'homeruns',
  monthly_singles: 'singles',
  monthly_doubles: 'doubles',
  monthly_triples: 'triples',
  monthly_obp: 'obp',
  monthly_slg: 'slg',
  monthly_ops: 'ops',
  monthly_bb_hbp: 'bb_hbp',
  monthly_rbi: 'rbi',
  monthly_so: 'so',
  monthly_hard_hit_rate: 'hard_hit_rate',
  monthly_barrels_rate: 'barrels_rate',
  monthly_strikeout_rate: 'strikeout_rate',
  walk_rate: null,
  swing_rate: null,
  contact_rate: null,
};

// ============================================================
// handleCustomQuery: 投球指標フロントエンド→バックエンドマッピング
// ============================================================
export const SEASON_PITCHING_METRIC_MAPPING = {
  inning_pitched: 'ip',
  era: 'era',
  whip: 'whip',
  strikeouts: 'so',
  walks: 'bb',
  home_runs_allowed: 'hr',
  batting_average_against: 'avg',
  wins: 'w',
  losses: 'l',
  fip: 'fip',
  games: 'g',
  game_started: 'gs',
  shutouts: 'sho',
  saves: 'sv',
  runs: 'r',
  hits_allowed: 'h',
  homeruns_allowed: 'hr',
  earned_runs: 'er',
  left_on_base_percentage: 'lobpct',
  ground_ball_percentage: 'gbpct',
  barrel_percentage: 'barrelpct',
  hard_hit_percentage: 'hardhitpct',
  k_9: 'k_9',
  bb_9: 'bb_9',
  war: 'war',
};

// ============================================================
// handleCustomQuery: 月別マルチチャート用 指標カラーマップ
// ============================================================
export const MONTHLY_METRIC_COLOR_MAP = {
  monthly_avg: '#3B82F6',
  monthly_hr: '#EF4444',
  monthly_rbi: '#10B981',
  monthly_ops: '#8B5CF6',
  monthly_obp: '#F59E0B',
  monthly_slg: '#EC4899',
};

export const getMonthlyMetricColor = (metric) =>
  MONTHLY_METRIC_COLOR_MAP[metric] ?? '#6B7280';

// ============================================================
// handleCustomQuery: 月別マルチチャート用 指標表示名マップ
// ============================================================
export const MONTHLY_METRIC_DISPLAY_NAME_MAP = {
  monthly_avg: '月別打率',
  monthly_hr: '月別ホームラン',
  monthly_rbi: '月別打点',
  monthly_ops: '月別OPS',
  monthly_obp: '月別出塁率',
  monthly_slg: '月別長打率',
  monthly_hits: '月別安打',
  monthly_singles: '月別単打',
  monthly_doubles: '月別二塁打',
  monthly_triples: '月別三塁打',
  homeruns: 'ホームラン',
  hits: '安打',
  avg: '打率',
  obp: '出塁率',
  slg: '長打率',
  ops: 'OPS',
};

export const getMonthlyMetricDisplayName = (metric) =>
  MONTHLY_METRIC_DISPLAY_NAME_MAP[metric] ?? metric;
