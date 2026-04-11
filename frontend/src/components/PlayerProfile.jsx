import { useState, useCallback, useRef } from 'react';
import { Search, User, X, Calendar, Ruler, Weight, MapPin, Shield } from 'lucide-react';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
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
                key={player.idfg || player.mlb_id || i}
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
    { label: 'IP',        value: kpi.ip != null ? kpi.ip.toFixed(1) : '—',  rank: null },
    { label: 'SO',        value: kpi.so ?? '—',                              rank: kpi.so_rank },
    { label: 'BB',        value: kpi.bb ?? '—',                              rank: null },
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
// シーズン選択ボタン
// =============================================
const SEASONS = [2021, 2022, 2023, 2024, 2025];

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
  const next = [player, ...prev.filter((p) => p.idfg !== player.idfg)].slice(0, MAX_RECENT);
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
    async (idfg, season) => {
      setProfile(null);
      setError(null);
      setIsLoading(true);
      try {
        const baseURL = getBackendURL();
        const headers = await getAuthHeaders();
        const url = season
          ? `${baseURL}/api/v1/players/${idfg}/profile?season=${season}`
          : `${baseURL}/api/v1/players/${idfg}/profile`;
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

      const idfg = player.idfg;
      if (!idfg) {
        setError('この選手は idfg が取得できませんでした。');
        return;
      }
      setRecentPlayers((prev) => saveRecent(player, prev));
      await fetchProfile(idfg, null);
    },
    [fetchProfile]
  );

  const handleSeasonChange = useCallback(
    async (season) => {
      if (!selectedPlayer?.idfg) return;
      setSelectedSeason(season);
      await fetchProfile(selectedPlayer.idfg, season);
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
                    key={player.idfg}
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
