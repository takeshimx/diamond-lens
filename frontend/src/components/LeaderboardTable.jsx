import React from 'react';
import { Trophy, Medal, Award } from 'lucide-react';

const LeaderboardTable = ({ data, category, metricOrder, isLoading, error }) => {
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

  // Function to get display name for metrics with context awareness
  const getMetricDisplayName = (metric, isPitching = false) => {
    const battingMetrics = {
      'avg': 'BA',
      'hr': 'HR',
      'rbi': 'RBI',
      'r': 'Run',
      'h': 'H',
      'ops': 'OPS',
      'obp': 'OBP',
      'slg': 'SLG',
      'woba': 'wOBA',
      'war': 'WAR',
      'wrcplus': 'wRC+',
      'bb': 'BB',
      'so': 'SO',
      // 'strikeout_rate': 'K%',
      'babip': 'BABIP',
      'iso': 'ISO',
      'hardhitpct': 'HH%',
      'barrelspct': 'Barrel%',
      'pa': 'PA',
      'ab': 'AB',
      'g': 'G',
      'batting_average_at_risp': 'RISP時打率',
      'slugging_percentage_at_risp': 'RISP時長打率',
      'home_runs_at_risp': 'RISP時HR'
    };

    const pitchingMetrics = {
      'era': '防御率',
      'whip': 'WHIP', 
      'so': '奪三振',
      'w': '勝',
      'l': '敗',
      'sv': 'S',
      'fip': 'FIP',
      'war': 'WAR',
      'k_9': 'K/9',
      'bb_9': 'BB/9',
      'k_bb': 'K/BB',
      'lobpct': 'LOB%',
      'gbpct': 'GB%',
      'barrelspct': 'Barrel%',
      'hardhitpct': 'HH%',
      'avg': '被打率',
      'ip': 'IP',
      'gs': '先発',
      'bb': '与四球',
      'h': '被安打',
      'hr': '被HR'
    };

    if (isPitching) {
      return pitchingMetrics[metric] || battingMetrics[metric] || metric.toUpperCase();
    } else {
      return battingMetrics[metric] || metric.toUpperCase();
    }
  };

  // Determine if this is a pitching leaderboard
  const isPitching = category?.id === 'pitching_leaderboard';

  // Get rank icon based on position
  const getRankIcon = (rank) => {
    if (rank === 1) return <Trophy className="w-5 h-5 text-yellow-500" />;
    if (rank === 2) return <Medal className="w-5 h-5 text-gray-400" />;
    if (rank === 3) return <Award className="w-5 h-5 text-amber-600" />;
    return <span className="w-5 h-5 flex items-center justify-center text-sm font-bold text-gray-600">{rank}</span>;
  };

  // Format numeric values
  const formatValue = (value, metric) => {
    if (value === null || value === undefined) return '-';
    
    // Percentage metrics: decimal 3
    if (metric.includes('rate') || metric.includes('percentage') || metric === 'avg' || 
        metric === 'obp' || metric === 'slg' || metric === 'ops' || metric === 'woba' || 
        metric === 'babip' || metric === 'iso' || metric === 'batting_average_at_risp' || 
        metric === 'slugging_percentage_at_risp') {
      return Number(value).toFixed(3);
    }

    // Percentage metrics: decimal 2
    if (metric === 'era' || metric === 'whip' || metric === 'fip') {
      return Number(value).toFixed(2);
    }

    // Integer metrics
    if (metric === 'hr' || metric === 'rbi' || metric === 'r' || metric === 'h' ||
        metric === 'bb' || metric === 'so' || metric === 'w' || metric === 'l' ||
        metric === 'sv' || metric === 'g' || metric === 'pa' || metric === 'ab' ||
        metric === 'gs' || metric === 'home_runs_at_risp') {
      return Math.round(Number(value));
    }
    
    // Decimal metrics
    return Number(value).toFixed(1);
  };

  // Get key columns to display based on category
  const getKeyColumns = () => {
    if (isPitching) {
      return ['ip', 'era', 'whip', 'so', 'w', 'l', 'fip', 'k_9', 'k_bb', 'war'];
    } else {
      return ['avg', 'hr', 'rbi', 'r', 'obp', 'slg', 'ops', 'war', 'wrcplus', 'batting_average_at_risp', 'slugging_percentage_at_risp', 'home_runs_at_risp'];
    }
  };

  const keyColumns = getKeyColumns();

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          {isPitching ? '投手' : '打者'}リーダーボード
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {getMetricDisplayName(metricOrder, isPitching)} でソート済み
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
                  className={`px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider ${
                    column === metricOrder ? 'bg-blue-100 dark:bg-blue-900' : ''
                  }`}
                >
                  {getMetricDisplayName(column, isPitching)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {data.slice(0, 30).map((player, index) => (
              <tr key={`${player.player_name}-${index}`} className="hover:bg-gray-50 dark:hover:bg-gray-700">
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
                      column === metricOrder ? 'bg-blue-50 dark:bg-blue-900/20 font-semibold' : ''
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
        トップ{Math.min(30, data.length)}人を表示 ({data.length}人中)
      </div>
    </div>
  );
};

export default LeaderboardTable;