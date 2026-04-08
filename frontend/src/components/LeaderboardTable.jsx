import { useState, useMemo } from 'react';
import { Trophy, Medal, Award, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

const BATTING_METRICS = {
  'avg': 'BA', 'hr': 'HR', 'rbi': 'RBI', 'r': 'Run', 'h': 'H',
  'ops': 'OPS', 'obp': 'OBP', 'slg': 'SLG', 'woba': 'wOBA', 'war': 'WAR',
  'wrcplus': 'wRC+', 'bb': 'BB', 'so': 'SO', 'babip': 'BABIP', 'iso': 'ISO',
  'hardhitpct': 'HH%', 'barrelspct': 'Barrel%', 'pa': 'PA', 'ab': 'AB', 'g': 'G',
  'batting_average_at_risp': 'RISP時打率',
  'slugging_percentage_at_risp': 'RISP時長打率',
  'home_runs_at_risp': 'RISP時HR',
};

const PITCHING_METRICS = {
  'era': '防御率', 'whip': 'WHIP', 'so': '奪三振', 'w': '勝', 'l': '敗',
  'sv': 'S', 'fip': 'FIP', 'war': 'WAR', 'k_9': 'K/9', 'bb_9': 'BB/9',
  'k_bb': 'K/BB', 'lobpct': 'LOB%', 'gbpct': 'GB%', 'barrelspct': 'Barrel%',
  'hardhitpct': 'HH%', 'avg': '被打率', 'ip': 'IP', 'gs': '先発',
  'bb': '与四球', 'h': '被安打', 'hr': '被HR',
};

const getMetricDisplayName = (metric, isPitching = false) => {
  if (isPitching) return PITCHING_METRICS[metric] || BATTING_METRICS[metric] || metric.toUpperCase();
  return BATTING_METRICS[metric] || metric.toUpperCase();
};

const getRankIcon = (rank) => {
  if (rank === 1) return <Trophy className="w-5 h-5 text-yellow-500" />;
  if (rank === 2) return <Medal className="w-5 h-5 text-gray-400" />;
  if (rank === 3) return <Award className="w-5 h-5 text-amber-600" />;
  return <span className="w-5 h-5 flex items-center justify-center text-sm font-bold text-gray-600">{rank}</span>;
};

const formatValue = (value, metric) => {
  if (value === null || value === undefined) return '-';
  if (metric.includes('rate') || metric.includes('percentage') || metric === 'avg' ||
      metric === 'obp' || metric === 'slg' || metric === 'ops' || metric === 'woba' ||
      metric === 'babip' || metric === 'iso' || metric === 'batting_average_at_risp' ||
      metric === 'slugging_percentage_at_risp') {
    return Number(value).toFixed(3);
  }
  if (metric === 'era' || metric === 'whip' || metric === 'fip') {
    return Number(value).toFixed(2);
  }
  if (metric === 'hr' || metric === 'rbi' || metric === 'r' || metric === 'h' ||
      metric === 'bb' || metric === 'so' || metric === 'w' || metric === 'l' ||
      metric === 'sv' || metric === 'g' || metric === 'pa' || metric === 'ab' ||
      metric === 'gs' || metric === 'home_runs_at_risp') {
    return Math.round(Number(value));
  }
  return Number(value).toFixed(1);
};

const LeaderboardTable = ({ data, category, metricOrder, isLoading, error }) => {
  const isPitching = category?.id === 'pitching_leaderboard';
  const keyColumns = isPitching
    ? ['ip', 'era', 'whip', 'so', 'w', 'l', 'fip', 'k_9', 'k_bb', 'war']
    : ['avg', 'hr', 'rbi', 'r', 'obp', 'slg', 'ops', 'war', 'wrcplus', 'batting_average_at_risp', 'slugging_percentage_at_risp', 'home_runs_at_risp'];

  // ===== フック類はすべてここに集約（アーリーリターンより前）=====
  const [sortKey, setSortKey] = useState(metricOrder);
  const [sortDir, setSortDir] = useState('desc');

  const sortedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return [...data].sort((a, b) => {
      const av = a[sortKey] ?? (sortDir === 'desc' ? -Infinity : Infinity);
      const bv = b[sortKey] ?? (sortDir === 'desc' ? -Infinity : Infinity);
      return sortDir === 'desc' ? bv - av : av - bv;
    });
  }, [data, sortKey, sortDir]);
  // ==============================================================

  const handleSort = (column) => {
    if (sortKey === column) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(column);
      setSortDir('desc');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600 dark:text-gray-400">リーダーボードを読み込み中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-2">エラーが発生しました</div>
        <div className="text-sm text-gray-600 dark:text-gray-400">{error}</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500 dark:text-gray-400">データが見つかりませんでした</div>
      </div>
    );
  }

  const SortIcon = ({ column }) => {
    if (sortKey !== column) return <ChevronsUpDown className="w-3 h-3 opacity-40" />;
    return sortDir === 'desc'
      ? <ChevronDown className="w-3 h-3 text-blue-400" />
      : <ChevronUp className="w-3 h-3 text-blue-400" />;
  };

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          {isPitching ? '投手' : '打者'}リーダーボード
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {getMetricDisplayName(sortKey, isPitching)} でソート済み
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full bg-white dark:bg-gray-800 rounded-lg shadow">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                順位
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                選手名
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                チーム
              </th>
              {keyColumns.map((column) => (
                <th
                  key={column}
                  onClick={() => handleSort(column)}
                  className={`px-4 py-3 text-center text-xs font-medium uppercase tracking-wider cursor-pointer select-none transition-colors hover:bg-gray-200 dark:hover:bg-gray-600 ${
                    sortKey === column
                      ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                      : 'text-gray-500 dark:text-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-center gap-1">
                    {getMetricDisplayName(column, isPitching)}
                    <SortIcon column={column} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {sortedData.slice(0, 30).map((player, index) => (
              <tr key={`${player.player_name || player.name}-${index}`} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    {getRankIcon(index + 1)}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {player.player_name || player.name}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {player.team}
                  </div>
                </td>
                {keyColumns.map((column) => (
                  <td
                    key={column}
                    className={`px-4 py-4 whitespace-nowrap text-center text-sm text-gray-900 dark:text-white ${
                      sortKey === column ? 'bg-blue-50 dark:bg-blue-900/20 font-semibold' : ''
                    }`}
                  >
                    {formatValue(player[column], column)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-center text-xs text-gray-500 dark:text-gray-400">
        トップ{Math.min(30, sortedData.length)}人を表示 ({sortedData.length}人中)
      </div>
    </div>
  );
};

export default LeaderboardTable;
