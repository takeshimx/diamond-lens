import { useState, useCallback, useRef } from 'react';
import { Search, User, X, Calendar, Ruler, Weight, MapPin, Shield } from 'lucide-react';
import {
  ComposedChart, Bar, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, LabelList,
  ScatterChart, Scatter, ReferenceLine, ReferenceArea,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';

// =============================================
// 検索バー（inline、シンプル版）
// =============================================
const DEBOUNCE_MS = 300;
const MIN_CHARS   = 2;

const ProfileSearchBar = ({ onSearchPlayers, onPlayerSelect }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const debounceRef = useRef(null);
  const abortRef    = useRef(null);

  const handleChange = useCallback(
    (e) => {
      const val = e.target.value;
      setSearchTerm(val);

      // 前のタイマーをキャンセル
      if (debounceRef.current) clearTimeout(debounceRef.current);
      // 前のリクエストをキャンセル
      if (abortRef.current) abortRef.current.abort();

      if (!val || val.length < MIN_CHARS) {
        setResults([]);
        setIsOpen(false);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setIsOpen(true);

      debounceRef.current = setTimeout(async () => {
        const controller = new AbortController();
        abortRef.current = controller;
        try {
          const data = await onSearchPlayers(val, controller.signal);
          if (!controller.signal.aborted) {
            setResults(data?.slice(0, 10) ?? []);
          }
        } catch (err) {
          if (!controller.signal.aborted) setResults([]);
        } finally {
          if (!controller.signal.aborted) setIsLoading(false);
        }
      }, DEBOUNCE_MS);
    },
    [onSearchPlayers]
  );

  const handleSelect = (player) => {
    onPlayerSelect(player);
    setSearchTerm(player.player_name || player.name || '');
    setIsOpen(false);
  };

  const handleClear = () => {
    setSearchTerm('');
    setResults([]);
    setIsOpen(false);
    onPlayerSelect(null);
  };

  return (
    <div className="relative w-full max-w-lg">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={handleChange}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder="選手名で検索 (例: Ohtani, Judge)"
          className="w-full pl-9 pr-9 py-2.5 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        />
        {searchTerm && (
          <button onClick={handleClear} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-xl max-h-72 overflow-y-auto">
          {isLoading ? (
            <div className="px-4 py-3 text-sm text-gray-400 flex items-center gap-2">
              <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              検索中...
            </div>
          ) : results.length > 0 ? (
            results.map((player, i) => (
              <button
                key={player.mlbid || i}
                onMouseDown={() => handleSelect(player)}
                className="w-full px-4 py-2.5 text-left hover:bg-gray-700 flex items-center gap-3 border-b border-gray-700 last:border-0"
              >
                <div className="w-8 h-8 bg-blue-900 rounded-full flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <div className="text-white text-sm font-medium">{player.player_name || player.name}</div>
                  <div className="flex gap-2 mt-0.5">
                    {player.team && <span className="text-xs text-blue-400">{player.team}</span>}
                    {player.league && <span className="text-xs text-gray-400">{player.league}</span>}
                  </div>
                </div>
              </button>
            ))
          ) : (
            <div className="px-4 py-3 text-sm text-gray-400">該当する選手が見つかりません</div>
          )}
        </div>
      )}
    </div>
  );
};

// =============================================
// Bio パネル
// =============================================
const BioPanel = ({ bio, seasonTeam }) => {
  if (!bio) return null;
  const rows = [
    { icon: Calendar, label: '生年月日', value: bio.birth_date },
    { icon: User,     label: '年齢',     value: bio.current_age ? `${bio.current_age}歳` : null },
    { icon: Ruler,    label: '身長',     value: bio.height },
    { icon: Weight,   label: '体重',     value: bio.weight ? `${bio.weight} lbs` : null },
    { icon: Shield,   label: 'B/T',      value: [bio.bat_side, bio.pitch_hand].filter(Boolean).join('/') || null },
    { icon: Calendar, label: 'デビュー', value: bio.mlb_debut_date },
    { icon: MapPin,   label: 'リーグ',   value: [bio.league, bio.division].filter(Boolean).join(' / ') || null },
  ];

  // シーズン指定時はそのシーズンのチームを優先、なければ現所属チームを表示
  const displayTeam = seasonTeam || bio.team_abbreviation;
  const displayTeamFull = seasonTeam
    ? seasonTeam
    : bio.team_abbreviation ? `${bio.team_name} (${bio.team_abbreviation})` : null;

  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
      {/* 選手名・チーム */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium px-2 py-0.5 bg-blue-600 rounded text-white">
            {bio.primary_position || '—'}
          </span>
          {displayTeam && (
            <span className="text-xs text-gray-400">{displayTeamFull}</span>
          )}
        </div>
        <h2 className="text-xl font-bold text-white">{bio.full_name || '—'}</h2>
      </div>

      {/* Bio詳細 */}
      <div className="space-y-2">
        {rows.map(({ icon: Icon, label, value }) =>
          value ? (
            <div key={label} className="flex items-center gap-2 text-sm">
              <Icon className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
              <span className="text-gray-400 w-20 flex-shrink-0">{label}</span>
              <span className="text-gray-200">{value}</span>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
};

// =============================================
// KPIカード 1枚
// =============================================
const rankColor = (rank) => {
  if (rank == null) return '';
  if (rank <= 10)  return 'text-cyan-400';
  if (rank <= 50)  return 'text-yellow-400';
  return 'text-red-400';
};

const KPICard = ({ label, value, rank }) => (
  <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex flex-col items-center text-center">
    <div className="text-2xl font-bold text-white mb-0.5">
      {value ?? '—'}
    </div>
    <div className="text-xs text-gray-400 font-medium">{label}</div>
    {rank != null
      ? <div className={`text-xs font-semibold mt-0.5 ${rankColor(rank)}`}>MLB #{rank}</div>
      : <div className="text-xs mt-0.5 invisible">—</div>
    }
  </div>
);

// =============================================
// 打者KPIグリッド
// =============================================
const BattingKPIGrid = ({ kpi }) => {
  if (!kpi) return null;
  const fmt = (v, d = 3) => v != null ? v.toFixed(d) : '—';
  const fmtPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—';
  const cards = [
    { label: 'AVG',       value: fmt(kpi.avg),                              rank: kpi.avg_rank },
    { label: 'OBP',       value: fmt(kpi.obp),                              rank: kpi.obp_rank },
    { label: 'SLG',       value: fmt(kpi.slg),                              rank: kpi.slg_rank },
    { label: 'OPS',       value: fmt(kpi.ops),                              rank: kpi.ops_rank },
    { label: 'HR',        value: kpi.hr ?? '—',                             rank: kpi.hr_rank },
    { label: 'RBI',       value: kpi.rbi ?? '—',                            rank: kpi.rbi_rank },
    { label: 'SB',        value: kpi.sb ?? '—',                             rank: kpi.sb_rank },
    { label: 'BB',        value: kpi.bb ?? '—',                             rank: kpi.bb_rank },
    { label: 'K',         value: kpi.so ?? '—',                             rank: kpi.so_rank },
    { label: 'wOBA',      value: fmt(kpi.woba),                             rank: kpi.woba_rank },
    { label: 'wRC+',      value: kpi.wrcplus ?? '—',                        rank: kpi.wrcplus_rank },
    { label: 'fWAR',      value: kpi.war != null ? kpi.war.toFixed(1) : '—', rank: kpi.war_rank },
    { label: 'Hard Hit%', value: fmtPct(kpi.hardhitpct),                   rank: kpi.hardhitpct_rank },
    { label: 'Barrel%',   value: fmtPct(kpi.barrelpct),                    rank: kpi.barrelpct_rank },
    { label: 'SwStr%',    value: fmtPct(kpi.swstrpct),                     rank: kpi.swstrpct_rank },
  ];
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Batting</h3>
        {kpi.season && <span className="text-xs text-gray-500">{kpi.season}</span>}
        {kpi.g && <span className="text-xs text-gray-500">G: {kpi.g} / PA: {kpi.pa ?? '—'}</span>}
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
        {cards.map(({ label, value, rank }) => (
          <KPICard key={label} label={label} value={value} rank={rank} />
        ))}
      </div>
    </div>
  );
};

// =============================================
// 投手KPIグリッド
// =============================================
const PitchingKPIGrid = ({ kpi }) => {
  if (!kpi) return null;
  const fmt = (v, d = 2) => v != null ? v.toFixed(d) : '—';
  const fmtPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—';
  const cards = [
    { label: 'ERA',       value: fmt(kpi.era),                               rank: kpi.era_rank },
    { label: 'WHIP',      value: fmt(kpi.whip),                              rank: kpi.whip_rank },
    { label: 'FIP',       value: fmt(kpi.fip),                               rank: kpi.fip_rank },
    { label: 'K/9',       value: fmt(kpi.k_9),                               rank: kpi.k_9_rank },
    { label: 'BB/9',      value: fmt(kpi.bb_9),                              rank: kpi.bb_9_rank },
    { label: 'W',         value: kpi.w ?? '—',                               rank: null },
    { label: 'L',         value: kpi.l ?? '—',                               rank: null },
    { label: 'SV',        value: kpi.sv ?? '—',                              rank: null },
    { label: 'IP',        value: kpi.ip != null ? kpi.ip.toFixed(1) : '—',  rank: kpi.ip_rank },
    { label: 'SO',        value: kpi.so ?? '—',                              rank: kpi.so_rank },
    { label: 'BB',        value: kpi.bb ?? '—',                              rank: kpi.bb_rank },
    { label: 'fWAR',      value: kpi.war != null ? kpi.war.toFixed(1) : '—', rank: kpi.war_rank },
    { label: 'Hard Hit%', value: fmtPct(kpi.hardhitpct),                    rank: kpi.hardhitpct_rank },
    { label: 'Barrel%',   value: fmtPct(kpi.barrelpct),                     rank: kpi.barrelpct_rank },
    { label: 'SwStr%',    value: fmtPct(kpi.swstrpct),                      rank: kpi.swstrpct_rank },
  ];
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Pitching</h3>
        {kpi.season && <span className="text-xs text-gray-500">{kpi.season}</span>}
        {kpi.g && <span className="text-xs text-gray-500">G: {kpi.g} / GS: {kpi.gs ?? '—'}</span>}
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
        {cards.map(({ label, value, rank }) => (
          <KPICard key={label} label={label} value={value} rank={rank} />
        ))}
      </div>
    </div>
  );
};

// =============================================
// Hit Location & Type Distribution チャート
// =============================================
const BB_TYPE_META = {
  ground_ball: { label: 'Ground Ball', color: '#3b82f6' },
  line_drive:  { label: 'Line Drive',  color: '#ef4444' },
  fly_ball:    { label: 'Fly Ball',    color: '#f59e0b' },
  popup:       { label: 'Pop Up',      color: '#10b981' },
};
const BB_TYPE_ORDER = ['ground_ball', 'line_drive', 'fly_ball', 'popup'];
const DIR_ORDER     = ['Left', 'Center', 'Right'];

const HitLocationChart = ({ data, season }) => {
  const [pThrows, setPThrows] = useState('All'); // All / L / R

  if (!data || data.length === 0) return null;

  // p_throws フィルタ
  const filtered = pThrows === 'All'
    ? data
    : data.filter((r) => r.p_throws === pThrows);

  if (filtered.length === 0) return null;

  // 方向×bb_type で hit_count を集計（フィルタ後に再集計）
  const dirBbMap = {};
  DIR_ORDER.forEach((d) => { dirBbMap[d] = {}; });

  filtered.forEach((row) => {
    const dir = row.hit_direction;
    const bt  = row.bb_type;
    if (!dirBbMap[dir] || !bt) return;
    dirBbMap[dir][bt] = (dirBbMap[dir][bt] || 0) + (row.hit_count || 0);
  });

  // チャートデータ（各方向内での bb_type 構成%）
  const chartData = DIR_ORDER.map((dir) => {
    const counts = dirBbMap[dir];
    const total  = Object.values(counts).reduce((s, v) => s + v, 0);
    const entry  = { dir, total };
    BB_TYPE_ORDER.forEach((bt) => {
      entry[bt] = total > 0 ? +((counts[bt] || 0) / total * 100).toFixed(1) : 0;
    });
    return entry;
  });

  // 方向別 avg_exit_velocity（加重平均）
  const evByDir = DIR_ORDER.map((dir) => {
    const rows = filtered.filter((r) => r.hit_direction === dir && r.avg_exit_velocity != null);
    if (rows.length === 0) return { dir, avg_ev: null };
    const totalW = rows.reduce((s, r) => s + (r.hit_count || 1), 0);
    const weighted = rows.reduce((s, r) => s + r.avg_exit_velocity * (r.hit_count || 1), 0);
    return { dir, avg_ev: +(weighted / totalW).toFixed(1) };
  });

  // Pull% / Center% / Oppo% はVIEWから取得（p_throwsでフィルタした最初の行から）
  const summaryRow = filtered[0];
  const pct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—';

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-1">
            Hit Location &amp; Type Distribution
            {season && <span className="text-gray-500 ml-2 text-xs normal-case">{season}</span>}
          </h3>
          <p className="text-xs text-gray-500">打球方向別・打球タイプ構成 · Avg Exit Velocity 付き</p>
        </div>

        {/* vs LHP/RHP トグル */}
        <div className="flex items-center gap-1">
          {['All', 'L', 'R'].map((v) => (
            <button key={v}
              onClick={() => setPThrows(v)}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                pThrows === v ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}>
              {v === 'All' ? 'All' : `vs ${v}HP`}
            </button>
          ))}
        </div>
      </div>

      {/* Pull% / Center% / Oppo% サマリー */}
      <div className="flex gap-6 mb-5">
        {[
          { label: 'Pull%',   value: pct(summaryRow?.pull_pct) },
          { label: 'Center%', value: pct(summaryRow?.center_pct) },
          { label: 'Oppo%',   value: pct(summaryRow?.oppo_pct) },
          { label: 'Total BIP', value: filtered.reduce((s, r) => s + (r.hit_count || 0), 0) },
        ].map(({ label, value }) => (
          <div key={label}>
            <div className="text-xs text-gray-400 mb-0.5">{label}</div>
            <div className="text-xl font-bold text-white">{value}</div>
          </div>
        ))}
      </div>

      {/* EV ラベル行（チャート上部にHTMLで表示） */}
      <div className="flex justify-around px-10 mb-1">
        {evByDir.map(({ dir, avg_ev }) => (
          <div key={dir} className="text-center">
            {avg_ev != null
              ? <span className="text-xs font-semibold text-gray-300">{avg_ev} mph</span>
              : <span className="text-xs text-gray-600">—</span>
            }
          </div>
        ))}
      </div>

      {/* Stacked Area Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 4, right: 20, left: 0, bottom: 10 }}>
          <defs>
            {BB_TYPE_ORDER.map((bt) => (
              <linearGradient key={bt} id={`grad-${bt}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={BB_TYPE_META[bt].color} stopOpacity={0.9} />
                <stop offset="95%" stopColor={BB_TYPE_META[bt].color} stopOpacity={0.7} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis dataKey="dir" tick={{ fill: '#9ca3af', fontSize: 13, fontWeight: 600 }} />
          <YAxis
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            domain={[0, 100]}
          />
          <Tooltip
            formatter={(value, name) => [`${value}%`, BB_TYPE_META[name]?.label ?? name]}
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#f9fafb', fontWeight: 600 }}
            itemStyle={{ color: '#d1d5db' }}
          />
          <Legend
            verticalAlign="top"
            formatter={(value) => BB_TYPE_META[value]?.label ?? value}
            wrapperStyle={{ color: '#9ca3af', fontSize: 11 }}
          />
          {BB_TYPE_ORDER.map((bt) => (
            <Area
              key={bt}
              type="monotone"
              dataKey={bt}
              stackId="a"
              stroke={BB_TYPE_META[bt].color}
              strokeWidth={1.5}
              fill={`url(#grad-${bt})`}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

// =============================================
// =============================================
// wOBA 発散カラースケール（中心 = リーグ平均 .320）
// =============================================
const LEAGUE_AVG_WOBA = 0.320;
const _WOBA_STOPS = [
  [0.00, [0,   0,   180]],
  [0.20, [0,   120, 255]],
  [0.32, [70,  70,  70 ]],   // league avg → neutral gray
  [0.42, [255, 120, 0  ]],
  [0.55, [200, 0,   0  ]],
];
const _lerpWoba = (t) => {
  const v = Math.min(Math.max(t, 0), 0.55);
  const s = _WOBA_STOPS;
  if (v <= s[0][0]) return s[0][1];
  if (v >= s[s.length - 1][0]) return s[s.length - 1][1];
  for (let i = 0; i < s.length - 1; i++) {
    const [t0, c0] = s[i], [t1, c1] = s[i + 1];
    if (v >= t0 && v <= t1) {
      const f = (v - t0) / (t1 - t0);
      return c0.map((cv, j) => Math.round(cv + f * (c1[j] - cv)));
    }
  }
};
const wobaColor = (val) => {
  if (val == null) return 'rgba(75,85,99,0.25)';
  const [r, g, b] = _lerpWoba(val);
  return `rgb(${r},${g},${b})`;
};
const wobaLabelColor = (val) => {
  if (val == null) return 'rgba(255,255,255,0.85)';
  const [r, g, b] = _lerpWoba(val);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.5 ? 'rgba(0,0,0,0.85)' : 'rgba(255,255,255,0.9)';
};
const WOBA_LEGEND_GRADIENT =
  'linear-gradient(to right, #0000b4, #0078ff, #464646, #ff7800, #c80000)';

// =============================================
// Count State wOBA Matrix（打者のみ）
// =============================================
const CountStateWobaMatrix = ({ data, season }) => {
  const [metric, setMetric] = useState('woba');
  const [risp,   setRisp]   = useState(false);
  if (!data || data.length === 0) return null;

  const filtered = data.filter(r => risp ? r.is_risp === true : !r.is_risp);
  const cellMap = {};
  for (const row of filtered) cellMap[`${row.balls},${row.strikes}`] = row;

  const CW = 68, CH = 52;

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-200">
          Count State wOBA
          {season && <span className="ml-2 text-xs text-gray-400">{season}</span>}
        </h3>
        <div className="flex gap-1">
          {[['woba', 'wOBA'], ['xwoba', 'xwOBA']].map(([k, lbl]) => (
            <button key={k} onClick={() => setMetric(k)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                metric === k ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}>
              {lbl}
            </button>
          ))}
          <div className="w-px bg-gray-600 mx-1" />
          {[[false, 'Non-RISP'], [true, 'RISP']].map(([val, lbl]) => (
            <button key={lbl} onClick={() => setRisp(val)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                risp === val ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}>
              {lbl}
            </button>
          ))}
        </div>
      </div>

      {/* Strike header */}
      <div className="flex mb-1" style={{ marginLeft: 36 }}>
        {[0, 1, 2].map(s => (
          <div key={s} className="text-xs text-gray-400 text-center font-medium"
            style={{ width: CW, marginRight: 3 }}>
            {s}S
          </div>
        ))}
      </div>

      {[0, 1, 2, 3].map(b => (
        <div key={b} className="flex items-center mb-1">
          <div className="text-xs text-gray-400 font-medium text-right pr-2 flex-shrink-0"
            style={{ width: 36 }}>
            {b}B
          </div>
          {[0, 1, 2].map(s => {
            const cell = cellMap[`${b},${s}`];
            const val  = cell ? (metric === 'woba' ? cell.woba : cell.xwoba_contact) : null;
            return (
              <div key={s} className="rounded flex flex-col items-center justify-center"
                style={{ width: CW, height: CH, backgroundColor: wobaColor(val), marginRight: 3 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: wobaLabelColor(val) }}>
                  {val != null ? val.toFixed(3) : '—'}
                </span>
                {cell?.pa_count != null && (
                  <span style={{ fontSize: 9, color: wobaLabelColor(val), opacity: 0.7 }}>
                    {cell.pa_count} PA
                  </span>
                )}
              </div>
            );
          })}
        </div>
      ))}

      <div className="flex items-center gap-2 mt-3">
        <span className="text-xs text-gray-400">Low</span>
        <div style={{ flex: 1, maxWidth: 160, height: 8, borderRadius: 4, background: WOBA_LEGEND_GRADIENT }} />
        <span className="text-xs text-gray-400">High</span>
        <span className="text-xs text-gray-500 ml-2">Avg ≈ .320</span>
      </div>
    </div>
  );
};

// =============================================
// xwOBA Zone Heatmap（打者のみ）
// =============================================
const XwobaZoneHeatmap = ({ data, season }) => {
  const [metric,   setMetric]   = useState('woba');
  const [pThrows,  setPThrows]  = useState('All');
  const [risp,     setRisp]     = useState(false);
  const [tooltip,  setTooltip]  = useState(null);
  if (!data || data.length === 0) return null;

  const filtered = data.filter(d =>
    (pThrows === 'All' || d.p_throws === pThrows) &&
    (risp ? d.is_risp === true : !d.is_risp)
  );

  const cellMap = {};
  for (const row of filtered) {
    const key = `${row.zone_x},${row.zone_z}`;
    if (!cellMap[key]) {
      cellMap[key] = { zone_x: row.zone_x, zone_z: row.zone_z,
        pa_count: 0, woba_sum: 0, xwoba_sum: 0, contact_count: 0 };
    }
    cellMap[key].pa_count      += row.pa_count      ?? 0;
    cellMap[key].woba_sum      += (row.woba          ?? 0) * (row.pa_count      ?? 0);
    cellMap[key].xwoba_sum     += (row.xwoba_contact ?? 0) * (row.contact_count ?? 0);
    cellMap[key].contact_count += row.contact_count  ?? 0;
  }
  const cells = Object.values(cellMap).map(c => ({
    ...c,
    woba:  c.pa_count      > 0 ? c.woba_sum  / c.pa_count      : null,
    xwoba: c.contact_count > 0 ? c.xwoba_sum / c.contact_count : null,
  }));

  const gridW = HM_X_VALS.length * (HM_CELL_W + HM_GAP);
  const gridH = HM_Z_VALS.length * (HM_CELL_H + HM_GAP);
  const szL = hmPixelX(SZ_LEFT),  szR = hmPixelX(SZ_RIGHT);
  const szT = hmPixelZ(SZ_TOP_FT), szB = hmPixelZ(SZ_BOT_FT);

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-200">
          xwOBA Zone Map
          {season && <span className="ml-2 text-xs text-gray-400">{season}</span>}
        </h3>
        <div className="flex gap-1">
          {['All', 'L', 'R'].map(p => (
            <button key={p} onClick={() => setPThrows(p)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                pThrows === p ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}>
              {p === 'All' ? 'ALL' : `vs ${p}HP`}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-1 mb-3">
        {[['woba', 'wOBA'], ['xwoba', 'xwOBA']].map(([k, lbl]) => (
          <button key={k} onClick={() => setMetric(k)}
            className={`px-2.5 py-1 rounded text-xs transition-colors ${
              metric === k ? 'bg-gray-600 text-white ring-1 ring-white/30' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {lbl}
          </button>
        ))}
        <div className="w-px bg-gray-600 mx-1" />
        {[[false, 'Non-RISP'], [true, 'RISP']].map(([val, lbl]) => (
          <button key={lbl} onClick={() => setRisp(val)}
            className={`px-2.5 py-1 rounded text-xs transition-colors ${
              risp === val ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {lbl}
          </button>
        ))}
      </div>

      <div className="relative flex-shrink-0" style={{ width: gridW, height: gridH }}>
        {HM_Z_VALS.map((zv, zi) =>
          HM_X_VALS.map((xv, xi) => {
            const cell = cells.find(
              c => Math.abs(c.zone_x - xv) < 0.01 && Math.abs(c.zone_z - zv) < 0.01
            );
            const val = cell ? (metric === 'woba' ? cell.woba : cell.xwoba) : null;
            return (
              <div key={`${xi}-${zi}`}
                onMouseEnter={(e) => cell && setTooltip({
                  x: e.clientX, y: e.clientY,
                  woba: cell.woba, xwoba: cell.xwoba,
                  pa_count: cell.pa_count, contact_count: cell.contact_count,
                  zone_x: xv, zone_z: zv,
                })}
                onMouseLeave={() => setTooltip(null)}
                style={{
                  position: 'absolute',
                  left: xi * (HM_CELL_W + HM_GAP), top: zi * (HM_CELL_H + HM_GAP),
                  width: HM_CELL_W, height: HM_CELL_H,
                  backgroundColor: wobaColor(val),
                  borderRadius: 2, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  cursor: cell ? 'crosshair' : 'default',
                }}>
                {val != null && (
                  <span style={{ fontSize: 9, color: wobaLabelColor(val), fontWeight: 700 }}>
                    {val.toFixed(3)}
                  </span>
                )}
              </div>
            );
          })
        )}
        <div style={{
          position: 'absolute', left: szL, top: szT,
          width: szR - szL, height: szB - szT,
          border: '2px solid rgba(255,255,255,0.7)',
          borderRadius: 2, pointerEvents: 'none',
        }} />
      </div>

      <div className="mt-2" style={{ width: gridW }}>
        <div className="flex justify-between text-xs text-gray-500 mb-2">
          <span>Inside</span><span>← Horizontal Position →</span><span>Outside</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Low</span>
          <div style={{ flex: 1, height: 10, borderRadius: 4, background: WOBA_LEGEND_GRADIENT }} />
          <span className="text-xs text-gray-400">High</span>
          <span className="text-xs text-gray-500 ml-1">Avg≈.320</span>
        </div>
      </div>

      {tooltip && (
        <div style={{
          position: 'fixed', left: tooltip.x + 12, top: tooltip.y - 8,
          zIndex: 9999, pointerEvents: 'none',
          backgroundColor: '#1f2937', border: '1px solid #374151',
          borderRadius: 6, padding: '6px 10px',
          fontSize: 11, color: '#e5e7eb',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)', minWidth: 140,
        }}>
          <div className="font-semibold mb-1" style={{ fontSize: 11 }}>
            x={tooltip.zone_x?.toFixed(1)} · z={tooltip.zone_z?.toFixed(1)}
          </div>
          <div>wOBA:&nbsp;<span style={{ fontWeight: 700, color: '#60a5fa' }}>{tooltip.woba?.toFixed(3) ?? '—'}</span></div>
          <div>xwOBA:&nbsp;<span style={{ fontWeight: 700, color: '#34d399' }}>{tooltip.xwoba?.toFixed(3) ?? '—'}</span></div>
          <div>PA: {tooltip.pa_count} · Contact: {tooltip.contact_count}</div>
        </div>
      )}
    </div>
  );
};

// =============================================
// 月別打撃チャート
// =============================================
const MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const MonthlyOffensiveChart = ({ data, battingKpi }) => {
  if (!data || data.length === 0) return null;

  const fmt3 = (v) => (v != null ? v.toFixed(3) : '—');

  const chartData = data.map((row) => ({
    month: MONTH_NAMES[row.game_month] ?? row.game_month,
    HR: row.home_runs,
    OBP: row.on_base_percentage != null ? +row.on_base_percentage.toFixed(3) : null,
    SLG: row.slugging_percentage != null ? +row.slugging_percentage.toFixed(3) : null,
    OPS: row.on_base_plus_slugging != null ? +row.on_base_plus_slugging.toFixed(3) : null,
  }));

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      {/* シーズンサマリー */}
      {battingKpi && (
        <div className="mb-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
            Offensive Key Stats
            {battingKpi.season && <span className="text-gray-500 ml-2 text-xs normal-case">{battingKpi.season}</span>}
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Season OBP', value: fmt3(battingKpi.obp) },
              { label: 'Season SLG', value: fmt3(battingKpi.slg) },
              { label: 'Season OPS', value: fmt3(battingKpi.ops) },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="text-xs text-gray-400 mb-0.5">{label}</div>
                <div className="text-2xl font-bold text-white">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* チャート */}
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
        Monthly Offensive Stats
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 40, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="month" tick={{ fill: '#9ca3af', fontSize: 12 }} />
          <YAxis
            yAxisId="left"
            domain={[0, 'auto']}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: 'Batting Metrics', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11, dy: 55 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            allowDecimals={false}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: 'HRs', angle: 90, position: 'insideRight', fill: '#6b7280', fontSize: 11, dy: -15 }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#f9fafb', fontWeight: 600 }}
            itemStyle={{ color: '#d1d5db' }}
          />
          <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
          <Bar yAxisId="right" dataKey="HR" name="Home Runs" fill="#10b981" opacity={0.85} radius={[3, 3, 0, 0]} />
          <Line yAxisId="left" type="monotone" dataKey="OPS" name="OPS" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
          <Line yAxisId="left" type="monotone" dataKey="OBP" name="OBP" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
          <Line yAxisId="left" type="monotone" dataKey="SLG" name="SLG" stroke="#a78bfa" strokeWidth={2} dot={{ r: 3 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

// =============================================
// RISP チャート（All Seasons / Single Season 切替）
// =============================================
const toRISPChartRow = (r, xKey) => ({
  x:          String(r[xKey]),
  Single:     r.singles    ?? 0,
  Double:     r.doubles    ?? 0,
  Triple:     r.triples    ?? 0,
  'Home Run': r.home_runs  ?? 0,
  BA:  r.batting_average     != null ? +r.batting_average.toFixed(3)     : null,
  SLG: r.slugging_percentage != null ? +r.slugging_percentage.toFixed(3) : null,
});

const RISPChartBody = ({ chartData, xLabel }) => (
  <ResponsiveContainer width="100%" height={300}>
    <ComposedChart data={chartData} margin={{ top: 4, right: 40, left: 0, bottom: 0 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
      <XAxis dataKey="x" label={{ value: xLabel, position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }} tick={{ fill: '#9ca3af', fontSize: 12 }} />
      <YAxis
        yAxisId="left"
        domain={[0, 'auto']}
        tick={{ fill: '#9ca3af', fontSize: 11 }}
        label={{ value: 'Batting Average & Slugging', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10, dy: 80 }}
      />
      <YAxis
        yAxisId="right"
        orientation="right"
        allowDecimals={false}
        tick={{ fill: '#9ca3af', fontSize: 11 }}
        label={{ value: 'Hits', angle: 90, position: 'insideRight', fill: '#6b7280', fontSize: 11, dy: -20 }}
      />
      <Tooltip
        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
        labelStyle={{ color: '#f9fafb', fontWeight: 600 }}
        itemStyle={{ color: '#d1d5db' }}
      />
      <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
      <Bar yAxisId="right" dataKey="Single"    name="Single"   stackId="hits" fill="#3b82f6" />
      <Bar yAxisId="right" dataKey="Double"    name="Double"   stackId="hits" fill="#f472b6" />
      <Bar yAxisId="right" dataKey="Triple"    name="Triple"   stackId="hits" fill="#eab308" />
      <Bar yAxisId="right" dataKey="Home Run"  name="Home Run" stackId="hits" fill="#10b981" radius={[3, 3, 0, 0]} />
      <Line yAxisId="left" type="monotone" dataKey="SLG" name="Slugging % at RISP" stroke="#9ca3af" strokeWidth={2} dot={{ r: 3 }} />
      <Line yAxisId="left" type="monotone" dataKey="BA"  name="Batting Avg at RISP" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
    </ComposedChart>
  </ResponsiveContainer>
);

const RISPChart = ({ data, monthlyData, season }) => {
  const [unit, setUnit] = useState('all');

  const hasAll    = data        && data.length > 0;
  const hasMonthly = monthlyData && monthlyData.length > 0;

  if (!hasAll && !hasMonthly) return null;

  const fmt3 = (v) => (v != null ? v.toFixed(3) : '—');

  // All-seasons サマリー
  const src = hasAll ? data : [];
  const totalHits = src.reduce((s, r) => s + (r.hits ?? 0), 0);
  const totalAB   = src.reduce((s, r) => s + (r.at_bats ?? 0), 0);
  const totalTB   = src.reduce((s, r) => s + (r.singles ?? 0) + 2 * (r.doubles ?? 0) + 3 * (r.triples ?? 0) + 4 * (r.home_runs ?? 0), 0);
  const allBA  = totalAB > 0 ? totalHits / totalAB : null;
  const allSLG = totalAB > 0 ? totalTB   / totalAB : null;

  // Single Season サマリー（月別合算）
  const msrc = hasMonthly ? monthlyData : [];
  const mHits = msrc.reduce((s, r) => s + (r.hits ?? 0), 0);
  const mAB   = msrc.reduce((s, r) => s + (r.at_bats ?? 0), 0);
  const mTB   = msrc.reduce((s, r) => s + (r.singles ?? 0) + 2 * (r.doubles ?? 0) + 3 * (r.triples ?? 0) + 4 * (r.home_runs ?? 0), 0);
  const sBA  = mAB > 0 ? mHits / mAB : null;
  const sSLG = mAB > 0 ? mTB   / mAB : null;

  const isAll = unit === 'all';
  const summaryBA  = isAll ? allBA  : sBA;
  const summarySLG = isAll ? allSLG : sSLG;
  const summaryLabel = isAll ? 'All Seasons' : `${season ?? 'Season'}`;

  const allChartData     = hasAll     ? data.map((r) => toRISPChartRow(r, 'season')) : [];
  const monthlyChartData = hasMonthly ? monthlyData.map((r) => toRISPChartRow(r, 'month')) : [];

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      {/* タイトル＋サマリー */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
          Runners in Scoring Position (RISP) Stats
        </h3>
        <div className="grid grid-cols-2 gap-6 mb-4">
          {[
            { label: `${summaryLabel} BA`,  value: fmt3(summaryBA) },
            { label: `${summaryLabel} SLG`, value: fmt3(summarySLG) },
          ].map(({ label, value }) => (
            <div key={label}>
              <div className="text-xs text-gray-400 mb-0.5">{label}</div>
              <div className="text-2xl font-bold text-white">{value}</div>
            </div>
          ))}
        </div>

        {/* ラジオ切替 */}
        <div className="flex items-center gap-5">
          <span className="text-xs text-gray-400">Unit:</span>
          {[
            { value: 'all',    label: 'All Seasons',   disabled: !hasAll },
            { value: 'single', label: 'Single Season', disabled: !hasMonthly },
          ].map(({ value, label, disabled }) => (
            <label key={value} className={`flex items-center gap-2 cursor-pointer ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}>
              <div
                onClick={() => !disabled && setUnit(value)}
                className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ${
                  unit === value ? 'border-emerald-500' : 'border-gray-500'
                }`}
              >
                {unit === value && <div className="w-2 h-2 rounded-full bg-emerald-500" />}
              </div>
              <span className="text-sm text-gray-300">{label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* チャート */}
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
        Batting Stats at RISP
      </h3>
      {isAll
        ? <RISPChartBody chartData={allChartData}     xLabel="Season" />
        : <RISPChartBody chartData={monthlyChartData} xLabel="Month"  />
      }
    </div>
  );
};

// =============================================
// Pitching Performance by Inning チャート
// =============================================
const INNING_LINE_OPTIONS = [
  { key: 'era',         label: 'ERA',         color: '#ef4444' },
  { key: 'baa',         label: 'BAA',         color: '#f59e0b' },
  { key: 'obp_against', label: 'OBP Against', color: '#3b82f6' },
  { key: 'slg_against', label: 'SLG Against', color: '#a78bfa' },
  { key: 'ops_against', label: 'OPS Against', color: '#f43f5e' },
];

const INNING_BAR_OPTIONS = [
  { key: 'home_runs_allowed', label: 'HR Allowed',   fill: '#10b981' },
  { key: 'hits_allowed',      label: 'Hits Allowed', fill: '#f472b6' },
  { key: 'free_passes',       label: 'Free Passes',  fill: '#fb923c' },
];

const PitchingByInningChart = ({ data, season }) => {
  const [lineKey, setLineKey] = useState('era');
  const [barKey,  setBarKey]  = useState('home_runs_allowed');

  if (!data || data.length === 0) return null;

  const chartData = data.map((row) => ({
    inning:            row.inning,
    baa:               row.baa               != null ? +row.baa.toFixed(3)               : null,
    obp_against:       row.obp_against        != null ? +row.obp_against.toFixed(3)        : null,
    slg_against:       row.slg_against        != null ? +row.slg_against.toFixed(3)        : null,
    ops_against:       row.ops_against        != null ? +row.ops_against.toFixed(3)        : null,
    era:               row.era                != null ? +row.era.toFixed(2)                : null,
    home_runs_allowed: row.home_runs_allowed  ?? 0,
    hits_allowed:      row.hits_allowed       ?? 0,
    free_passes:       row.free_passes        ?? 0,
    outs_recorded:     row.outs_recorded      ?? 0,
  }));

  const lineOpt = INNING_LINE_OPTIONS.find((o) => o.key === lineKey);
  const barOpt  = INNING_BAR_OPTIONS.find((o)  => o.key === barKey);

  // サマリー: totals across all innings
  const totHR      = data.reduce((s, r) => s + (r.home_runs_allowed ?? 0), 0);
  const totHits    = data.reduce((s, r) => s + (r.hits_allowed ?? 0), 0);
  const totBB      = data.reduce((s, r) => s + (r.free_passes ?? 0), 0);
  const totOuts    = data.reduce((s, r) => s + (r.outs_recorded ?? 0), 0);
  const totEarned  = data.reduce((s, r) => s + (r.earned_runs ?? 0), 0);
  const totIP      = totOuts > 0 ? (totOuts / 3).toFixed(1) : null;
  const overallERA = totOuts > 0 ? ((totEarned / (totOuts / 3)) * 9).toFixed(2) : null;

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      {/* タイトル＋サマリー */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
          Pitching Performance by Inning
          {season && <span className="text-gray-500 ml-2 text-xs normal-case">{season}</span>}
          <span className="ml-3 text-xs font-normal normal-case text-gray-500">
            ※ ERA は Statcast ベースの近似値（公式 ERA と異なる場合があります）
          </span>
        </h3>
        <div className="grid grid-cols-6 gap-4 mb-4">
          {[
            { label: 'ERA',          value: overallERA ?? '—' },
            { label: 'IP',           value: totIP      ?? '—' },
            { label: 'HR Allowed',   value: totHR },
            { label: 'Hits Allowed', value: totHits },
            { label: 'Free Passes',  value: totBB },
            { label: 'Outs Recorded', value: totOuts },
          ].map(({ label, value }) => (
            <div key={label}>
              <div className="text-xs text-gray-400 mb-0.5">{label}</div>
              <div className="text-2xl font-bold text-white">{value}</div>
            </div>
          ))}
        </div>

        {/* メトリクス選択 */}
        <div className="flex flex-wrap items-center gap-6">
          {/* ライン選択 */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">Line:</span>
            {INNING_LINE_OPTIONS.map((opt) => (
              <label key={opt.key} className="flex items-center gap-1.5 cursor-pointer">
                <div
                  onClick={() => setLineKey(opt.key)}
                  className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors`}
                  style={{ borderColor: lineKey === opt.key ? opt.color : '#6b7280' }}
                >
                  {lineKey === opt.key && (
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: opt.color }} />
                  )}
                </div>
                <span className="text-xs text-gray-300">{opt.label}</span>
              </label>
            ))}
          </div>

          {/* バー選択 */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">Bar:</span>
            {INNING_BAR_OPTIONS.map((opt) => (
              <label key={opt.key} className="flex items-center gap-1.5 cursor-pointer">
                <div
                  onClick={() => setBarKey(opt.key)}
                  className={`w-4 h-4 rounded-md border-2 flex items-center justify-center transition-colors`}
                  style={{ borderColor: barKey === opt.key ? opt.fill : '#6b7280',
                           backgroundColor: barKey === opt.key ? opt.fill + '33' : 'transparent' }}
                >
                  {barKey === opt.key && (
                    <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: opt.fill }} />
                  )}
                </div>
                <span className="text-xs text-gray-300">{opt.label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* チャート */}
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 40, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="inning"
            tick={{ fill: '#9ca3af', fontSize: 12 }}
            label={{ value: 'Inning', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }}
          />
          <YAxis
            yAxisId="left"
            domain={[0, 'auto']}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: lineOpt?.label, angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11, dy: 40 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            allowDecimals={false}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: barOpt?.label, angle: 90, position: 'insideRight', fill: '#6b7280', fontSize: 11, dy: -40 }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#f9fafb', fontWeight: 600 }}
            labelFormatter={(v) => `Inning ${v}`}
            itemStyle={{ color: '#d1d5db' }}
          />
          <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
          <Bar
            yAxisId="right"
            dataKey={barKey}
            name={barOpt?.label}
            fill={barOpt?.fill}
            opacity={0.85}
            radius={[3, 3, 0, 0]}
          >
            <LabelList
              dataKey={barKey}
              position="top"
              style={{ fill: '#d1d5db', fontSize: 11, fontWeight: 500 }}
            />
          </Bar>
          <Line
            yAxisId="left"
            type="monotone"
            dataKey={lineKey}
            name={lineOpt?.label}
            stroke={lineOpt?.color}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          >
            <LabelList
              dataKey={lineKey}
              position="top"
              offset={8}
              style={{ fill: lineOpt?.color, fontSize: 11, fontWeight: 600 }}
            />
          </Line>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

// =============================================
// Pitch Arsenal Panel（Movement + Location）
// =============================================
const PITCH_TYPE_COLORS = {
  FF: '#ef4444', SI: '#f97316', FC: '#eab308',
  SL: '#3b82f6', ST: '#8b5cf6', CU: '#06b6d4',
  FS: '#10b981', CH: '#ec4899', KC: '#a3e635', KN: '#fbbf24',
};

const RESULT_META = {
  B: { label: 'Ball',     color: '#6b7280' },
  S: { label: 'Strike',   color: '#f59e0b' },
  X: { label: 'In Play',  color: '#10b981' },
};

// Strike zone constants (feet, catcher's view)
const SZ_L  = -0.83;
const SZ_R  =  0.83;
const SZ_B  =  1.5;
const SZ_T  =  3.5;
const SZ_W3 = (SZ_R - SZ_L) / 3;
const SZ_H3 = (SZ_T - SZ_B) / 3;


// =============================================
// =============================================
// Pitcher RISP Performance チャート
// =============================================
const RISP_METRICS = [
  { key: 'baa',          label: 'BAA',      fmt: (v) => v?.toFixed(3) ?? '—' },
  { key: 'xwoba',        label: 'xwOBA',    fmt: (v) => v?.toFixed(3) ?? '—' },
  { key: 'k_pct',        label: 'K%',       fmt: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
  { key: 'bb_pct',       label: 'BB%',      fmt: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
  { key: 'hard_hit_pct', label: 'Hard Hit%',fmt: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
];

// レーダーチャート用: メトリクスごとの正規化レンジ（MLB目安）
// lower_is_better=true のメトリクスは正規化スコアを反転（高スコア = 良い）
const RISP_RADAR_CONFIG = [
  { key: 'baa',          label: 'BAA',       min: 0.150, max: 0.380, lower_is_better: true },
  { key: 'xwoba',        label: 'xwOBA',     min: 0.200, max: 0.450, lower_is_better: true },
  { key: 'k_pct',        label: 'K%',        min: 0.10,  max: 0.38,  lower_is_better: false },
  { key: 'bb_pct',       label: 'BB%',       min: 0.03,  max: 0.18,  lower_is_better: true },
  { key: 'hard_hit_pct', label: 'Hard Hit%', min: 0.25,  max: 0.55,  lower_is_better: true },
];

// 値を 0–100 に正規化し、lower_is_better なら反転
const normalizeRisp = (value, { min, max, lower_is_better }) => {
  if (value == null) return 0;
  const clamped = Math.max(min, Math.min(max, value));
  const score = ((clamped - min) / (max - min)) * 100;
  return lower_is_better ? 100 - score : score;
};

const PitcherRispChart = ({ data, season }) => {
  if (!data || data.length === 0) return null;

  const risp    = data.find((r) => r.situation === 'risp');
  const nonRisp = data.find((r) => r.situation === 'non_risp');
  if (!risp || !nonRisp) return null;

  // レーダー用データ（正規化スコア）
  const radarData = RISP_RADAR_CONFIG.map((cfg) => ({
    metric:   cfg.label,
    risp:     +normalizeRisp(risp[cfg.key],    cfg).toFixed(1),
    non_risp: +normalizeRisp(nonRisp[cfg.key], cfg).toFixed(1),
    // 生値（ツールチップ表示用）
    rawRisp:    risp[cfg.key],
    rawNonRisp: nonRisp[cfg.key],
    cfg,
  }));

  // サマリーカード
  const summaryCards = [
    { label: 'PA (RISP)',      value: risp.pa    ?? '—' },
    { label: 'PA (Non-RISP)',  value: nonRisp.pa ?? '—' },
    { label: 'BAA RISP',       value: risp.baa?.toFixed(3)      ?? '—' },
    { label: 'BAA Non-RISP',   value: nonRisp.baa?.toFixed(3)   ?? '—' },
    { label: 'xwOBA RISP',     value: risp.xwoba?.toFixed(3)    ?? '—' },
    { label: 'xwOBA Non-RISP', value: nonRisp.xwoba?.toFixed(3) ?? '—' },
  ];

  // カスタムツールチップ: 生値を表示
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    const fmtVal = (v, cfg) => {
      if (v == null) return '—';
      return cfg.key.endsWith('pct') ? `${(v * 100).toFixed(1)}%` : v.toFixed(3);
    };
    return (
      <div style={{
        background: '#1f2937', border: '1px solid #374151',
        borderRadius: 8, padding: '8px 12px', fontSize: 12,
      }}>
        <p style={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 4 }}>{d.metric}</p>
        <p style={{ color: '#f87171' }}>RISP:     {fmtVal(d.rawRisp,    d.cfg)}</p>
        <p style={{ color: '#60a5fa' }}>Non-RISP: {fmtVal(d.rawNonRisp, d.cfg)}</p>
      </div>
    );
  };

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
        Pitching Performance — RISP vs Non-RISP
        {season && <span className="text-gray-500 ml-2 text-xs normal-case">{season}</span>}
      </h3>

      {/* サマリーカード */}
      <div className="grid grid-cols-3 gap-3 mb-5 sm:grid-cols-6">
        {summaryCards.map(({ label, value }) => (
          <div key={label}>
            <div className="text-xs text-gray-400 mb-0.5">{label}</div>
            <div className="text-lg font-bold text-white">{value}</div>
          </div>
        ))}
      </div>

      {/* レーダーチャート */}
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 11 }} />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#6b7280', fontSize: 9 }}
            tickCount={4}
          />
          <Radar
            name="RISP"
            dataKey="risp"
            stroke="#f87171"
            fill="#f87171"
            fillOpacity={0.25}
            dot={{ r: 3, fill: '#f87171' }}
          />
          <Radar
            name="Non-RISP"
            dataKey="non_risp"
            stroke="#60a5fa"
            fill="#60a5fa"
            fillOpacity={0.20}
            dot={{ r: 3, fill: '#60a5fa' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
        </RadarChart>
      </ResponsiveContainer>

      {/* 注釈 */}
      <p className="text-xs text-gray-500 mt-2">
        スコアは MLB 参照レンジで 0–100 に正規化。外周ほど良い（BAA・xwOBA・BB%・Hard Hit% は低いほど外周）。
      </p>
    </div>
  );
};

// xBA & Whiff% バブルチャート
// =============================================
// リーグ平均参照値（MLB全体の目安）
const LEAGUE_AVG_XBA    = 0.243;
const LEAGUE_AVG_WHIFF  = 0.245;

const PitchPerformanceChart = ({ data, season }) => {
  if (!data || data.length === 0) return null;

  // バブルサイズ: usage_pct を r に変換（最小8, 最大32）
  const toRadius = (usage) => {
    if (usage == null) return 10;
    return Math.max(8, Math.min(32, usage * 100 * 1.2));
  };

  // recharts Scatter 用: xba・whiff_pct を x/y にマップし半径情報を付与
  const chartData = data.map((row) => ({
    ...row,
    x: row.xba       != null ? +row.xba.toFixed(3)       : null,
    y: row.whiff_pct != null ? +row.whiff_pct.toFixed(3) : null,
    r: toRadius(row.usage_pct),
  })).filter((r) => r.x != null && r.y != null);

  const CustomDot = (props) => {
    const { cx, cy, payload } = props;
    const color = PITCH_TYPE_COLORS[payload.pitch_type] || '#9ca3af';
    return (
      <g>
        <circle cx={cx} cy={cy} r={payload.r} fill={color} fillOpacity={0.8} stroke={color} strokeWidth={1} />
        <text x={cx} y={cy - payload.r - 4} textAnchor="middle" fill={color}
          fontSize={10} fontWeight={600}>
          {payload.pitch_type}
        </text>
      </g>
    );
  };

  const tip = ({ active, payload }) => {
    if (!active || !payload?.[0]) return null;
    const p = payload[0].payload;
    return (
      <div className="bg-gray-900 border border-gray-600 rounded-lg p-3 text-xs space-y-1">
        <div className="font-semibold text-white">{p.pitch_name || p.pitch_type}</div>
        <div className="text-gray-300">xBA: <span className="text-white">{p.xba?.toFixed(3)}</span></div>
        <div className="text-gray-300">Whiff%: <span className="text-white">{p.whiff_pct != null ? `${(p.whiff_pct * 100).toFixed(1)}%` : '—'}</span></div>
        <div className="text-gray-300">Usage: <span className="text-white">{p.usage_pct != null ? `${(p.usage_pct * 100).toFixed(1)}%` : '—'}</span></div>
        <div className="text-gray-300">Avg Speed: <span className="text-white">{p.avg_speed != null ? `${p.avg_speed.toFixed(1)} mph` : '—'}</span></div>
        <div className="text-gray-300">Pitches: <span className="text-white">{p.pitch_count}</span></div>
      </div>
    );
  };

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-1">
          Pitch Performance: xBA &amp; Whiff%
          {season && <span className="text-gray-500 ml-2 text-xs normal-case">{season}</span>}
        </h3>
        <p className="text-xs text-gray-500">
          バブルサイズ = 使用率 · 左下 = 支配的 · 参照線 = リーグ平均
        </p>
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            type="number" dataKey="x"
            name="xBA" domain={[0.1, 0.45]}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: 'Expected Batting Average (xBA)', position: 'insideBottom', offset: -20, fill: '#6b7280', fontSize: 11 }}
          />
          <YAxis
            type="number" dataKey="y"
            name="Whiff%" domain={[0, 0.8]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: 'Whiff%', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11, dy: 25 }}
          />
          {/* リーグ平均参照線 */}
          <ReferenceLine x={LEAGUE_AVG_XBA}   stroke="#6b7280" strokeDasharray="5 3"
            label={{ value: 'Lg Avg xBA', position: 'top', fill: '#6b7280', fontSize: 9 }} />
          <ReferenceLine y={LEAGUE_AVG_WHIFF} stroke="#6b7280" strokeDasharray="5 3"
            label={{ value: 'Lg Avg Whiff%', position: 'right', fill: '#6b7280', fontSize: 9 }} />
          <Tooltip content={tip} />
          <Scatter
            data={chartData}
            shape={<CustomDot />}
          />
        </ScatterChart>
      </ResponsiveContainer>

      {/* 凡例テーブル */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
        {data.map((row) => (
          <div key={row.pitch_type}
            className="flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2">
            <div className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: PITCH_TYPE_COLORS[row.pitch_type] || '#9ca3af' }} />
            <div className="min-w-0">
              <div className="text-xs font-semibold text-white">{row.pitch_type}</div>
              <div className="text-xs text-gray-400 truncate">{row.pitch_name}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// =============================================
// Whiff Zone Heatmap（投手のみ）
// =============================================
const HM_X_VALS = [-2.0, -1.5, -1.0, -0.5,  0.0,  0.5,  1.0,  1.5,  2.0]; // 9 cols
const HM_Z_VALS = [ 4.5,  4.0,  3.5,  3.0,  2.5,  2.0,  1.5,  1.0,  0.5]; // 9 rows top→bottom
const HM_CELL_W  = 40;
const HM_CELL_H  = 34;
const HM_GAP     = 1;

const HM_X_MIN   = -2.0;
const HM_Z_MAX   =  4.5;
const HM_STEP    =  0.5;
const SZ_LEFT    = -0.83;
const SZ_RIGHT   =  0.83;
const SZ_TOP_FT  =  3.5;
const SZ_BOT_FT  =  1.5;

const hmPixelX = (x) => ((x - HM_X_MIN) / HM_STEP) * (HM_CELL_W + HM_GAP);
const hmPixelZ = (z) => ((HM_Z_MAX - z) / HM_STEP) * (HM_CELL_H + HM_GAP);

// Jet-like colormap: dark-blue → blue → cyan → green → yellow → orange → red
const _JET_STOPS = [
  [0.00, [0,   0,   100]],
  [0.15, [0,   0,   200]],
  [0.35, [0,   170, 200]],
  [0.50, [0,   200, 80 ]],
  [0.65, [200, 200, 0  ]],
  [0.82, [210, 105, 0  ]],
  [1.00, [180, 0,   0  ]],
];
const _lerpJet = (t) => {
  const s = _JET_STOPS;
  if (t <= s[0][0]) return s[0][1];
  if (t >= s[s.length - 1][0]) return s[s.length - 1][1];
  for (let i = 0; i < s.length - 1; i++) {
    const [t0, c0] = s[i], [t1, c1] = s[i + 1];
    if (t >= t0 && t <= t1) {
      const f = (t - t0) / (t1 - t0);
      return c0.map((v, j) => Math.round(v + f * (c1[j] - v)));
    }
  }
};
const whiffColor = (pct) => {
  if (pct == null) return 'rgba(75,85,99,0.25)';
  const [r, g, b] = _lerpJet(Math.min(Math.max(pct, 0), 1));
  return `rgb(${r},${g},${b})`;
};
// 輝度に応じてラベル色を決定（明るい背景→黒、暗い背景→白）
const whiffLabelColor = (pct) => {
  if (pct == null) return 'rgba(255,255,255,0.85)';
  const [r, g, b] = _lerpJet(Math.min(Math.max(pct, 0), 1));
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.55 ? 'rgba(0,0,0,0.85)' : 'rgba(255,255,255,0.9)';
};

const WhiffHeatmapChart = ({ data, season }) => {
  const [activePitch,  setActivePitch]  = useState(null);
  const [standFilter,  setStandFilter]  = useState('All');
  const [tooltip,      setTooltip]      = useState(null);

  if (!data || data.length === 0) return null;

  const pitchTypes = [...new Set(data.map(d => d.pitch_type).filter(Boolean))].sort();
  const currentPitch = activePitch ?? 'ALL';

  const filtered = data.filter(d =>
    (currentPitch === 'ALL' || d.pitch_type === currentPitch) &&
    (standFilter === 'All' || d.stand === standFilter)
  );

  // aggregate cells (sum when multiple stand values)
  const cellMap = {};
  for (const row of filtered) {
    const key = `${row.zone_x},${row.zone_z}`;
    if (!cellMap[key]) {
      cellMap[key] = { zone_x: row.zone_x, zone_z: row.zone_z, total_pitches: 0, whiff_count: 0, swing_count: 0 };
    }
    cellMap[key].total_pitches += row.total_pitches ?? 0;
    cellMap[key].whiff_count   += row.whiff_count   ?? 0;
    cellMap[key].swing_count   += row.swing_count   ?? 0;
  }
  const cells = Object.values(cellMap).map(c => ({
    ...c,
    whiff_pct: c.swing_count > 0 ? c.whiff_count / c.swing_count : null,
  }));

  const pitchName  = currentPitch === 'ALL'
    ? 'All Pitches'
    : (data.find(d => d.pitch_type === currentPitch)?.pitch_name ?? currentPitch);
  const gridW      = HM_X_VALS.length * (HM_CELL_W + HM_GAP);
  const gridH      = HM_Z_VALS.length * (HM_CELL_H + HM_GAP);

  const szL = hmPixelX(SZ_LEFT);
  const szR = hmPixelX(SZ_RIGHT);
  const szT = hmPixelZ(SZ_TOP_FT);
  const szB = hmPixelZ(SZ_BOT_FT);

  return (
    <div className="bg-gray-800 rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-200">
            Whiff Zone Heatmap
            {season && <span className="ml-2 text-xs text-gray-400">{season}</span>}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">{pitchName}</p>
        </div>
        <div className="flex gap-1">
          {['All', 'L', 'R'].map(s => (
            <button key={s} onClick={() => setStandFilter(s)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                standFilter === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}>
              {s === 'All' ? 'ALL' : `vs ${s}HB`}
            </button>
          ))}
        </div>
      </div>

      {/* Pitch type selector */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {/* ALL button */}
        <button onClick={() => setActivePitch('ALL')}
          className={`px-2.5 py-1 rounded text-xs transition-colors ${
            currentPitch === 'ALL'
              ? 'bg-gray-600 text-white ring-1 ring-white/30'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}>
          ALL
        </button>
        {pitchTypes.map(pt => (
          <button key={pt} onClick={() => setActivePitch(pt)}
            className={`px-2.5 py-1 rounded text-xs transition-colors ${
              pt === currentPitch
                ? 'bg-gray-600 text-white ring-1 ring-white/30'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {pt}
          </button>
        ))}
      </div>

      {/* Heatmap grid */}
      <div className="relative flex-shrink-0" style={{ width: gridW, height: gridH }}>
        {HM_Z_VALS.map((zv, zi) =>
          HM_X_VALS.map((xv, xi) => {
            const cell = cells.find(
              c => Math.abs(c.zone_x - xv) < 0.01 && Math.abs(c.zone_z - zv) < 0.01
            );
            return (
              <div key={`${xi}-${zi}`}
                onMouseEnter={(e) => cell && setTooltip({
                  x: e.clientX, y: e.clientY,
                  pct: cell.whiff_pct,
                  whiff: cell.whiff_count,
                  swing: cell.swing_count,
                  total: cell.total_pitches,
                  zone_x: xv, zone_z: zv,
                })}
                onMouseLeave={() => setTooltip(null)}
                style={{
                  position: 'absolute',
                  left:  xi * (HM_CELL_W + HM_GAP),
                  top:   zi * (HM_CELL_H + HM_GAP),
                  width:  HM_CELL_W,
                  height: HM_CELL_H,
                  backgroundColor: whiffColor(cell?.whiff_pct ?? null),
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: cell ? 'crosshair' : 'default',
                }}>
                {cell?.whiff_pct != null && (
                  <span style={{ fontSize: 9, color: whiffLabelColor(cell.whiff_pct), fontWeight: 700 }}>
                    {Math.round(cell.whiff_pct * 100)}%
                  </span>
                )}
              </div>
            );
          })
        )}
        {/* Strike zone border */}
        <div style={{
          position: 'absolute',
          left: szL, top: szT,
          width: szR - szL, height: szB - szT,
          border: '2px solid rgba(255,255,255,0.7)',
          borderRadius: 2,
          pointerEvents: 'none',
        }} />
      </div>

      {/* X-axis label + color legend（グリッド下） */}
      <div className="mt-2" style={{ width: gridW }}>
        <div className="flex justify-between text-xs text-gray-500 mb-2">
          <span>Inside</span>
          <span>← Horizontal Position →</span>
          <span>Outside</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">0%</span>
          <div style={{
            flex: 1, height: 10, borderRadius: 4,
            background: 'linear-gradient(to right, #000064, #0000c8, #00aac8, #00c850, #c8c800, #d26900, #b40000)',
          }} />
          <span className="text-xs text-gray-400">100% Whiff%</span>
        </div>
      </div>

      {/* Floating tooltip */}
      {tooltip && (
        <div style={{
          position: 'fixed',
          left: tooltip.x + 12, top: tooltip.y - 8,
          zIndex: 9999, pointerEvents: 'none',
          backgroundColor: '#1f2937',
          border: '1px solid #374151',
          borderRadius: 6,
          padding: '6px 10px',
          fontSize: 11, color: '#e5e7eb',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          minWidth: 130,
        }}>
          <div className="font-semibold mb-1" style={{ fontSize: 11 }}>
            x={tooltip.zone_x?.toFixed(1)} · z={tooltip.zone_z?.toFixed(1)}
          </div>
          <div>Whiff%:&nbsp;
            <span style={{ fontWeight: 700, color: '#fb923c' }}>
              {tooltip.pct != null ? (tooltip.pct * 100).toFixed(1) + '%' : '—'}
            </span>
          </div>
          <div>Whiff / Swing: {tooltip.whiff} / {tooltip.swing}</div>
          <div>Total pitches: {tooltip.total}</div>
        </div>
      )}
    </div>
  );
};

// =============================================
// Pitcher TTO — 2-panel chart (batting perf + fastball quality)
// =============================================
const TTO_LABELS = { 1: '1st Time', 2: '2nd Time', 3: '3rd+ Time' };

const PitcherTtoChart = ({ data, season }) => {
  if (!data || data.length === 0) return null;

  const chartData = data.map((r) => ({
    tto:           TTO_LABELS[r.tto] ?? `TTO ${r.tto}`,
    xwoba_against: r.xwoba_against,
    baa:           r.baa,
    pa:            r.pa,
    avg_velo:      r.avg_velo,
    avg_spin:      r.avg_spin,
    pitch_count:   r.pitch_count,
  }));

  const BattingTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <div style={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
        <p style={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 4 }}>{label}</p>
        <p style={{ color: '#fb923c' }}>xwOBA: {d?.xwoba_against?.toFixed(3) ?? '—'}</p>
        <p style={{ color: '#60a5fa' }}>BAA: {d?.baa?.toFixed(3) ?? '—'}</p>
        <p style={{ color: '#6b7280', marginTop: 4 }}>PA: {d?.pa ?? '—'}</p>
      </div>
    );
  };

  const VeloTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <div style={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
        <p style={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 4 }}>{label}</p>
        <p style={{ color: '#34d399' }}>Avg Velo: {d?.avg_velo?.toFixed(1) ?? '—'} mph</p>
        <p style={{ color: '#a78bfa' }}>Avg Spin: {d?.avg_spin?.toFixed(0) ?? '—'} rpm</p>
        <p style={{ color: '#6b7280', marginTop: 4 }}>Pitches: {d?.pitch_count ?? '—'}</p>
      </div>
    );
  };

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">
        Times Through Order (TTO)
        {season && <span className="text-gray-500 ml-2 text-xs normal-case">{season}</span>}
      </h3>

      <div className="grid grid-cols-2 gap-4">
        {/* 左: 被打撃成績 × TTO */}
        <div>
          <p className="text-xs text-gray-400 mb-2">Batting Performance Against</p>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={chartData} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="tto" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis
                domain={[0, 0.600]}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                tickFormatter={(v) => v.toFixed(3)}
              />
              <Tooltip content={<BattingTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
              <Line
                type="monotone"
                dataKey="xwoba_against"
                name="xwOBA Against"
                stroke="#fb923c"
                strokeWidth={2}
                dot={{ r: 4, fill: '#fb923c' }}
              />
              <Line
                type="monotone"
                dataKey="baa"
                name="BAA"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={{ r: 4, fill: '#60a5fa' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* 右: 球質 × TTO */}
        <div>
          <p className="text-xs text-gray-400 mb-2">Fastball Quality</p>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="tto" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis
                yAxisId="velo"
                orientation="left"
                domain={['auto', 'auto']}
                tick={{ fill: '#34d399', fontSize: 10 }}
                label={{ value: 'mph', angle: -90, position: 'insideLeft', fill: '#34d399', fontSize: 10, dy: 20 }}
              />
              <YAxis
                yAxisId="spin"
                orientation="right"
                domain={['auto', 'auto']}
                tick={{ fill: '#a78bfa', fontSize: 10 }}
                label={{ value: 'rpm', angle: 90, position: 'insideRight', fill: '#a78bfa', fontSize: 10, dy: -20 }}
              />
              <Tooltip content={<VeloTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
              <Line
                yAxisId="velo"
                type="monotone"
                dataKey="avg_velo"
                name="Avg Velo (mph)"
                stroke="#34d399"
                strokeWidth={2}
                dot={{ r: 4, fill: '#34d399' }}
              />
              <Line
                yAxisId="spin"
                type="monotone"
                dataKey="avg_spin"
                name="Avg Spin (rpm)"
                stroke="#a78bfa"
                strokeWidth={2}
                dot={{ r: 4, fill: '#a78bfa' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <p className="text-xs text-gray-500 mt-2">
        左: 被打撃成績。右: ファストボール系（FF / SI / FC / FS / FA）のみ。TTO = 同一打者への登場巡。
      </p>
    </div>
  );
};


const PitchArsenalPanel = ({ data, season }) => {
  const [posMode, setPosMode] = useState('result'); // 'result' | 'pitch'

  if (!data || data.length === 0) return null;

  // Group by pitch type
  const byType = data.reduce((acc, row) => {
    const pt = row.pitch_type || 'XX';
    if (!acc[pt]) acc[pt] = { rows: [], name: row.pitch_name || pt };
    acc[pt].rows.push(row);
    return acc;
  }, {});
  const pitchTypes = Object.keys(byType).sort();

  // Speed + usage summary
  const speedSummary = pitchTypes.map((pt) => {
    const speeds = byType[pt].rows.map((r) => r.release_speed).filter((v) => v != null);
    const avg = speeds.length > 0 ? speeds.reduce((s, v) => s + v, 0) / speeds.length : null;
    return { pt, avg, count: byType[pt].rows.length };
  }).sort((a, b) => (b.avg ?? 0) - (a.avg ?? 0));
  const total = data.length;

  // Group by result for position chart
  const byResult = { B: [], S: [], X: [] };
  data.forEach((row) => {
    const r = row.result || 'B';
    if (byResult[r]) byResult[r].push(row);
  });

  const movTip = ({ active, payload }) => {
    if (!active || !payload?.[0]) return null;
    const p = payload[0].payload;
    return (
      <div className="bg-gray-900 border border-gray-600 rounded-lg p-2 text-xs space-y-0.5">
        <div className="font-semibold text-white">{p.pitch_name || p.pitch_type}</div>
        <div className="text-gray-300">pfx_x: {p.pfx_x?.toFixed(2)} ft</div>
        <div className="text-gray-300">pfx_z: {p.pfx_z?.toFixed(2)} ft</div>
        {p.release_speed && <div className="text-gray-300">{p.release_speed} mph</div>}
      </div>
    );
  };

  const locTip = ({ active, payload }) => {
    if (!active || !payload?.[0]) return null;
    const p = payload[0].payload;
    return (
      <div className="bg-gray-900 border border-gray-600 rounded-lg p-2 text-xs space-y-0.5">
        <div className="font-semibold text-white">{p.pitch_name || p.pitch_type}</div>
        <div className="text-gray-300">plate_x: {p.plate_x?.toFixed(2)} ft</div>
        <div className="text-gray-300">plate_z: {p.plate_z?.toFixed(2)} ft</div>
        <div className="text-gray-300">{RESULT_META[p.result]?.label ?? p.result}</div>
      </div>
    );
  };

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700 space-y-5">
      {/* ヘッダー + 球速・球種サマリー */}
      <div>
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
          Pitch Arsenal
          {season && <span className="text-gray-500 ml-2 text-xs normal-case">{season}</span>}
          <span className="ml-2 text-xs text-gray-500 normal-case font-normal">{total.toLocaleString()} pitches</span>
        </h3>
        <div className="flex flex-wrap gap-6">
          {speedSummary.map(({ pt, avg, count }) => (
            <div key={pt}>
              <div className="text-xs font-semibold mb-0.5" style={{ color: PITCH_TYPE_COLORS[pt] || '#9ca3af' }}>{pt}</div>
              <div className="text-xl font-bold text-white">{avg != null ? avg.toFixed(1) : '—'}</div>
              <div className="text-xs text-gray-500">{count}球 ({((count / total) * 100).toFixed(0)}%)</div>
            </div>
          ))}
        </div>
      </div>

      {/* 2チャート横並び */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ① Pitch Movement */}
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-0.5">Pitch Movement</h4>
          <p className="text-xs text-gray-500 mb-3">Catcher's view · spin-induced break (ft)</p>
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 32 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number" dataKey="pfx_x" domain={[-2.5, 2.5]}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                label={{ value: 'pfx_x (ft)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }}
              />
              <YAxis
                type="number" dataKey="pfx_z" domain={[-2, 2]}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                label={{ value: 'pfx_z (ft)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10, dy: 30 }}
              />
              <ReferenceLine x={0} stroke="#4b5563" strokeDasharray="4 2" />
              <ReferenceLine y={0} stroke="#4b5563" strokeDasharray="4 2" />
              <Tooltip content={movTip} />
              <Legend verticalAlign="top" wrapperStyle={{ color: '#9ca3af', fontSize: 11 }} />
              {pitchTypes.map((pt) => (
                <Scatter
                  key={pt}
                  name={pt}
                  data={byType[pt].rows}
                  fill={PITCH_TYPE_COLORS[pt] || '#9ca3af'}
                  fillOpacity={0.7}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* ② Pitch Location */}
        <div>
          <div className="flex items-center justify-between mb-0.5">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Pitch Location</h4>
            <div className="flex items-center gap-4">
              {[
                { value: 'result', label: 'Result' },
                { value: 'pitch',  label: 'Pitch Type' },
              ].map(({ value, label }) => (
                <label key={value} className="flex items-center gap-1.5 cursor-pointer">
                  <div
                    onClick={() => setPosMode(value)}
                    className="w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center"
                    style={{ borderColor: posMode === value ? '#3b82f6' : '#6b7280' }}
                  >
                    {posMode === value && <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
                  </div>
                  <span className="text-xs text-gray-300">{label}</span>
                </label>
              ))}
            </div>
          </div>
          <p className="text-xs text-gray-500 mb-3">Catcher's view · strike zone overlay (zones 1–9)</p>
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 32 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number" dataKey="plate_x" domain={[-3, 3]}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                label={{ value: 'plate_x (ft)', position: 'insideBottom', offset: -12, fill: '#6b7280', fontSize: 10 }}
              />
              <YAxis
                type="number" dataKey="plate_z" domain={[0, 5]}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                label={{ value: 'plate_z (ft)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10, dy: 30 }}
              />
              {/* Strike zone outer box */}
              <ReferenceArea x1={SZ_L} x2={SZ_R} y1={SZ_B} y2={SZ_T}
                stroke="#d1d5db" strokeWidth={1.5} fill="transparent" />
              {/* Inner zone grid lines */}
              <ReferenceLine x={SZ_L + SZ_W3}     stroke="#9ca3af" strokeOpacity={0.5} strokeDasharray="3 2" />
              <ReferenceLine x={SZ_L + SZ_W3 * 2} stroke="#9ca3af" strokeOpacity={0.5} strokeDasharray="3 2" />
              <ReferenceLine y={SZ_B + SZ_H3}     stroke="#9ca3af" strokeOpacity={0.5} strokeDasharray="3 2" />
              <ReferenceLine y={SZ_B + SZ_H3 * 2} stroke="#9ca3af" strokeOpacity={0.5} strokeDasharray="3 2" />
              <Tooltip content={locTip} />
              <Legend verticalAlign="top" wrapperStyle={{ color: '#9ca3af', fontSize: 11 }} />
              {posMode === 'result'
                ? Object.entries(RESULT_META).map(([r, meta]) => (
                    <Scatter
                      key={r}
                      name={meta.label}
                      data={byResult[r]}
                      fill={meta.color}
                      fillOpacity={0.55}
                    />
                  ))
                : pitchTypes.map((pt) => (
                    <Scatter
                      key={pt}
                      name={pt}
                      data={byType[pt].rows}
                      fill={PITCH_TYPE_COLORS[pt] || '#9ca3af'}
                      fillOpacity={0.7}
                    />
                  ))
              }
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Clutch Situation Chart（打者のみ）
// =============================================
const SITUATION_ORDER  = ['no_runner', 'on_1b', 'risp', 'bases_loaded'];
const SITUATION_LABELS = {
  no_runner:    'No Runner',
  on_1b:        'On 1B',
  risp:         'RISP',
  bases_loaded: 'Bases Loaded',
};
const SITUATION_COLORS = {
  no_runner:    '#3b82f6',
  on_1b:        '#f59e0b',
  risp:         '#10b981',
  bases_loaded: '#ef4444',
};

const ClutchSituationChart = ({ data, season }) => {
  const [tab, setTab] = useState('rates');

  if (!data || data.length === 0) return null;

  const resolvedSeason = season ?? Math.max(...data.map(d => d.game_year));

  // 現シーズンデータ（situation別）
  const seasonRows = SITUATION_ORDER
    .map(sit => data.find(d => d.game_year === resolvedSeason && d.situation_type === sit))
    .filter(Boolean);

  // 年度トレンド（rispoのみ）
  const trendRows = data
    .filter(d => d.situation_type === 'risp')
    .sort((a, b) => a.game_year - b.game_year);

  const fmt = (v, d = 3) => v != null ? v.toFixed(d) : '—';
  const fmtPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—';

  const TOOLTIP_STYLE = {
    contentStyle: { backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 },
    labelStyle: { color: '#f9fafb', fontWeight: 600 },
    itemStyle: { color: '#d1d5db' },
  };

  // --- Chart 1: OPS / wOBA / xwOBA by situation ---
  const ratesData = seasonRows.map(r => ({
    situation: SITUATION_LABELS[r.situation_type] ?? r.situation_type,
    BA:    r.avg   != null ? +r.avg.toFixed(3)   : null,
    OPS:   r.ops   != null ? +r.ops.toFixed(3)   : null,
    wOBA:  r.woba  != null ? +r.woba.toFixed(3)  : null,
    xwOBA: r.xwoba != null ? +r.xwoba.toFixed(3) : null,
    pa:    r.pa,
  }));

  // --- Chart 2: Statcast quality by situation ---
  const statcastData = seasonRows.map(r => ({
    situation:  SITUATION_LABELS[r.situation_type] ?? r.situation_type,
    'Exit Velo': r.avg_exit_velocity != null ? +r.avg_exit_velocity.toFixed(1) : null,
    'Barrel%':   r.barrels_rate      != null ? +(r.barrels_rate * 100).toFixed(1) : null,
    'Hard Hit%': r.hard_hit_rate     != null ? +(r.hard_hit_rate * 100).toFixed(1) : null,
  }));

  // --- Chart 3: RISP wOBA trend ---
  const trendData = trendRows.map(r => ({
    year:  r.game_year,
    BA:    r.avg   != null ? +r.avg.toFixed(3)   : null,
    wOBA:  r.woba  != null ? +r.woba.toFixed(3)  : null,
    xwOBA: r.xwoba != null ? +r.xwoba.toFixed(3) : null,
    OPS:   r.ops   != null ? +r.ops.toFixed(3)   : null,
  }));

  const tabs = [
    { key: 'rates',    label: 'BA / OPS / wOBA' },
    { key: 'statcast', label: 'Statcast' },
    { key: 'trend',    label: 'RISP Trend' },
  ];

  return (
    <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
            Clutch Situation Breakdown
            {resolvedSeason && <span className="ml-2 text-xs text-gray-500 normal-case font-normal">{resolvedSeason}</span>}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">状況別打撃成績 · Statcast指標 · RISPトレンド</p>
        </div>
        <div className="flex gap-1">
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-2.5 py-1 text-xs rounded transition-colors ${
                tab === t.key ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* PA サマリーバッジ */}
      {tab !== 'trend' && (
        <div className="flex gap-3 mb-4 flex-wrap">
          {seasonRows.map(r => (
            <div key={r.situation_type} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: SITUATION_COLORS[r.situation_type] }} />
              <span className="text-xs text-gray-400">
                {SITUATION_LABELS[r.situation_type]}: <span className="text-gray-200">{r.pa ?? '—'} PA</span>
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Chart 1: OPS / wOBA / xwOBA */}
      {tab === 'rates' && (
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={ratesData} margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="situation" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis domain={[0, 1.2]} tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickFormatter={v => v.toFixed(2)} />
            <Tooltip {...TOOLTIP_STYLE} formatter={(v, name) => [v?.toFixed(3) ?? '—', name]} />
            <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
            <Line type="monotone" dataKey="BA" name="BA" stroke="#a78bfa" strokeWidth={2} dot={{ r: 4 }}>
              <LabelList dataKey="BA" position="top" style={{ fill: '#a78bfa', fontSize: 10, fontWeight: 600 }} formatter={v => v?.toFixed(3)} />
            </Line>
            <Line type="monotone" dataKey="OPS"   name="OPS"   stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="wOBA"  name="wOBA"  stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="xwOBA" name="xwOBA" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} strokeDasharray="4 2" />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* Chart 2: Statcast */}
      {tab === 'statcast' && (
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={statcastData} margin={{ top: 4, right: 40, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="situation" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis yAxisId="ev" domain={[80, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }}
              label={{ value: 'Exit Velo (mph)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10, dy: 55 }} />
            <YAxis yAxisId="pct" orientation="right" domain={[0, 30]}
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              label={{ value: '%', angle: 90, position: 'insideRight', fill: '#6b7280', fontSize: 10, dy: -10 }} />
            <Tooltip {...TOOLTIP_STYLE}
              formatter={(v, name) => name === 'Exit Velo' ? [`${v} mph`, name] : [`${v}%`, name]} />
            <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
            <Bar yAxisId="ev"  dataKey="Exit Velo" fill="#3b82f6" radius={[3,3,0,0]} opacity={0.85} />
            <Line yAxisId="pct" type="monotone" dataKey="Barrel%"   stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
            <Line yAxisId="pct" type="monotone" dataKey="Hard Hit%" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} strokeDasharray="4 2" />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* Chart 3: RISP Trend */}
      {tab === 'trend' && (
        trendData.length > 0 ? (
          <>
            <p className="text-xs text-gray-500 mb-3">RISP時のwOBA / xwOBA / OPS年度推移</p>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={trendData} margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="year" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis domain={[0, 1.2]} tick={{ fill: '#9ca3af', fontSize: 11 }}
                  tickFormatter={v => v.toFixed(2)} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v, name) => [v?.toFixed(3) ?? '—', name]} />
                <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
                <Line type="monotone" dataKey="BA"    name="BA (RISP)"    stroke="#a78bfa" strokeWidth={2} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="OPS"   name="OPS (RISP)"   stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="wOBA"  name="wOBA (RISP)"  stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="xwOBA" name="xwOBA (RISP)" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} strokeDasharray="4 2" />
              </ComposedChart>
            </ResponsiveContainer>
          </>
        ) : (
          <p className="text-sm text-gray-500">RISPトレンドデータなし</p>
        )
      )}
    </div>
  );
};

// =============================================
// シーズン選択ボタン
// =============================================
const SEASONS = [2021, 2022, 2023, 2024, 2025, 2026];

const SeasonSelector = ({ selectedSeason, onChange }) => (
  <div className="flex items-center gap-1.5">
    <span className="text-xs text-gray-400 mr-1">Season</span>
    {SEASONS.map((yr) => (
      <button
        key={yr}
        onClick={() => onChange(yr)}
        className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
          selectedSeason === yr
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        {yr}
      </button>
    ))}
  </div>
);

// =============================================
// メインコンポーネント
// =============================================
const RECENT_KEY = 'dl_recent_players';
const MAX_RECENT = 5;

const loadRecent = () => {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]'); }
  catch { return []; }
};

const saveRecent = (player, prev) => {
  const next = [player, ...prev.filter((p) => p.mlbid !== player.mlbid)].slice(0, MAX_RECENT);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  return next;
};

const PlayerProfile = ({ onSearchPlayers, getAuthHeaders, getBackendURL }) => {
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState(null);
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recentPlayers, setRecentPlayers] = useState(loadRecent);

  const fetchProfile = useCallback(
    async (mlbid, season) => {
      setProfile(null);
      setError(null);
      setIsLoading(true);
      try {
        const baseURL = getBackendURL();
        const headers = await getAuthHeaders();
        const url = season
          ? `${baseURL}/api/v1/players/${mlbid}/profile?season=${season}`
          : `${baseURL}/api/v1/players/${mlbid}/profile`;
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setProfile(data);
      } catch (e) {
        setError(`プロフィールの取得に失敗しました: ${e.message}`);
      } finally {
        setIsLoading(false);
      }
    },
    [getAuthHeaders, getBackendURL]
  );

  const handlePlayerSelect = useCallback(
    async (player) => {
      setSelectedPlayer(player);
      setSelectedSeason(null);
      setProfile(null);
      setError(null);
      if (!player) return;

      const mlbid = player.mlbid;
      if (!mlbid) {
        setError('この選手は mlbid が取得できませんでした。');
        return;
      }
      setRecentPlayers((prev) => saveRecent(player, prev));
      await fetchProfile(mlbid, null);
    },
    [fetchProfile]
  );

  const handleSeasonChange = useCallback(
    async (season) => {
      if (!selectedPlayer?.mlbid) return;
      setSelectedSeason(season);
      await fetchProfile(selectedPlayer.mlbid, season);
    },
    [selectedPlayer, fetchProfile]
  );

  const isTWP = profile?.bio?.primary_position === 'TWP';

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* ヘッダー */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex-1">
          <h1 className="text-xl font-bold text-white">Player Profile</h1>
          <p className="text-sm text-gray-400 mt-0.5">選手名を検索してプロフィールを表示</p>
        </div>
        <ProfileSearchBar
          onSearchPlayers={onSearchPlayers}
          onPlayerSelect={handlePlayerSelect}
        />
      </div>

      {/* シーズン選択（選手選択後に表示） */}
      {selectedPlayer && (
        <SeasonSelector selectedSeason={selectedSeason} onChange={handleSeasonChange} />
      )}

      {/* ローディング */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-gray-400">プロフィールを取得中...</span>
        </div>
      )}

      {/* エラー */}
      {error && !isLoading && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* プロフィール本体 */}
      {profile && !isLoading && (
        <div className="space-y-6">
          {/* Bio + 基本情報 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1">
              <BioPanel
                bio={profile.bio}
                seasonTeam={profile.batting_kpi?.team ?? profile.pitching_kpi?.team ?? null}
              />
            </div>
            <div className="md:col-span-2 space-y-4">
              {/* 打者KPI */}
              {(profile.batting_kpi || isTWP) && (
                <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
                  <BattingKPIGrid kpi={profile.batting_kpi} />
                  {!profile.batting_kpi && (
                    <p className="text-sm text-gray-500">打撃成績データなし</p>
                  )}
                </div>
              )}
              {/* 投手KPI */}
              {(profile.pitching_kpi || isTWP) && (
                <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700">
                  <PitchingKPIGrid kpi={profile.pitching_kpi} />
                  {!profile.pitching_kpi && (
                    <p className="text-sm text-gray-500">投球成績データなし</p>
                  )}
                </div>
              )}
              {/* どちらもない場合 */}
              {!profile.batting_kpi && !profile.pitching_kpi && (
                <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700 text-sm text-gray-400">
                  該当シーズンのスタッツデータが見つかりませんでした。
                </div>
              )}
            </div>
          </div>

          {/* Hit Location チャート（打者のみ） */}
          {(profile.batting_kpi || isTWP) && (
            <HitLocationChart
              data={profile.hit_location}
              season={profile.batting_kpi?.season}
            />
          )}

          {/* Count State wOBA ＋ xwOBA Zone Map（打者のみ、2カラム） */}
          {(profile.batting_kpi || isTWP) && (
            <div className="grid grid-cols-2 gap-4">
              <CountStateWobaMatrix
                data={profile.count_state_woba}
                season={profile.batting_kpi?.season}
              />
              <XwobaZoneHeatmap
                data={profile.xwoba_zone}
                season={profile.batting_kpi?.season}
              />
            </div>
          )}

          {/* Clutch Situation チャート（打者のみ） */}
          {(profile.batting_kpi || isTWP) && (
            <ClutchSituationChart
              data={profile.clutch_stats}
              season={profile.batting_kpi?.season}
            />
          )}

          {/* 月別打撃チャート */}
          <MonthlyOffensiveChart
            data={profile.monthly_offensive_stats}
            battingKpi={profile.batting_kpi}
          />

          {/* RISP チャート */}
          <RISPChart
            data={profile.risp_stats}
            monthlyData={profile.risp_monthly_stats}
            season={profile.batting_kpi?.season ?? profile.pitching_kpi?.season}
          />

          {/* Pitching by Inning チャート（投手のみ） */}
          {(profile.pitching_kpi || isTWP) && (
            <PitchingByInningChart
              data={profile.inning_stats}
              season={profile.pitching_kpi?.season}
            />
          )}

          {/* Pitcher RISP Performance（投手のみ） */}
          {(profile.pitching_kpi || isTWP) && (
            <PitcherRispChart
              data={profile.pitcher_risp_performance}
              season={profile.pitching_kpi?.season}
            />
          )}

          {/* Pitcher TTO — Fastball Velo & Spin（投手のみ） */}
          {(profile.pitching_kpi || isTWP) && (
            <PitcherTtoChart
              data={profile.pitcher_tto}
              season={profile.pitching_kpi?.season}
            />
          )}

          {/* Pitch Arsenal（投手のみ） */}
          {(profile.pitching_kpi || isTWP) && (
            <PitchArsenalPanel
              data={profile.statcast_pitches}
              season={profile.pitching_kpi?.season}
            />
          )}

          {/* xBA & Whiff% ＋ Whiff Zone Heatmap（投手のみ、2カラム） */}
          {(profile.pitching_kpi || isTWP) && (
            <div className="grid grid-cols-2 gap-4 mt-4">
              <PitchPerformanceChart
                data={profile.pitch_performance}
                season={profile.pitching_kpi?.season}
              />
              <WhiffHeatmapChart
                data={profile.whiff_heatmap}
                season={profile.pitching_kpi?.season}
              />
            </div>
          )}
        </div>
      )}

      {/* 未選択時のプレースホルダー */}
      {!selectedPlayer && !isLoading && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500">
          <User className="w-12 h-12 mb-4 opacity-30" />
          <p className="text-sm mb-6">上の検索バーで選手を選択してください</p>

          {recentPlayers.length > 0 && (
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-3">最近検索した選手</p>
              <div className="flex flex-wrap justify-center gap-2">
                {recentPlayers.map((player) => (
                  <button
                    key={player.mlbid}
                    onClick={() => handlePlayerSelect(player)}
                    className="px-4 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-600 hover:border-blue-500 rounded-full text-sm text-gray-200 transition-colors"
                  >
                    {player.player_name || player.name}
                    {player.team && <span className="ml-1.5 text-xs text-gray-500">{player.team}</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PlayerProfile;
