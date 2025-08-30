import React from 'react';
import { Play, RotateCcw, Eye, Clock, BarChart3, User, Calendar, Target } from 'lucide-react';

const QueryPreview = ({ queryState, onExecute, onReset, isLoading, canExecute }) => {
  // Generate natural language summary
  const generateSummary = () => {
    // Check if batting splits and missing split type
    const isBattingSplits = queryState.category?.id === 'batting_splits';
    if (!queryState.category || !queryState.player || !queryState.metrics.length || 
        (isBattingSplits && !queryState.splitType)) {
      return "クエリが不完全です";
    }

    const categoryNames = {
      season_batting: 'シーズン打撃成績',
      season_pitching: 'シーズン投手成績', 
      batting_splits: '場面別打撃成績',
      monthly_trends: '月別推移',
      team_comparison: 'チーム比較',
      career_stats: '通算成績'
    };

    const seasonText = queryState.seasonMode === 'all' 
      ? '全シーズン'
      : `${queryState.specificYear}年シーズン`;

    const metricsText = queryState.metrics.length === 1 
      ? `${queryState.metrics.length}個の指標`
      : `${queryState.metrics.length}個の指標`;
    
    // Add split type for batting splits
    const splitTypeText = queryState.category.id === 'batting_splits' && queryState.splitType
      ? `(${queryState.splitType.title})`
      : '';

    return `${queryState.player.name}の${seasonText}における${categoryNames[queryState.category.id]}${splitTypeText}から${metricsText}を分析します`;
  };

  // Get metric names for display
  const getMetricNames = () => {
    const metricNameMap = {
      // Basic batting
      batting_average: '打率',
      home_runs: 'ホームラン',
      rbi: 'RBI',
      runs: '得点',
      hits: '安打',
      doubles: '二塁打',
      triples: '三塁打',
      // Advanced batting
      ops: 'OPS',
      obp: '出塁率',
      slg: '長打率',
      woba: 'wOBA',
      war: 'WAR',
      wrc_plus: 'wRC+',
      // Plate discipline
      walks: '四球',
      strikeouts: '三振',
      walk_rate: 'BB%',
      strikeout_rate: 'K%',
      swing_rate: 'Swing%',
      contact_rate: 'Contact%',
      // Basic pitching
      era: '防御率',
      wins: '勝利',
      losses: '敗戦',
      saves: 'セーブ',
      innings_pitched: '投球回',
      // Advanced pitching
      whip: 'WHIP',
      fip: 'FIP',
      xfip: 'xFIP',
      k_9: 'K/9',
      bb_9: 'BB/9',
      // Situational
      risp_avg: 'RISP打率',
      bases_loaded_avg: '満塁時打率',
      clutch_avg: 'クラッチ打率',
      two_outs_risp: '2死得点圏打率',
      vs_lhp_avg: '対左投手打率',
      vs_rhp_avg: '対右投手打率',
      vs_lhp_ops: '対左投手OPS',
      vs_rhp_ops: '対右投手OPS',
      // Monthly
      monthly_avg: '月別打率',
      monthly_hr: '月別ホームラン',
      monthly_rbi: '月別RBI',
      monthly_ops: '月別OPS',
      // Batting Splits - RISP
      hits_at_risp: 'RISP時安打',
      homeruns_at_risp: 'RISP時ホームラン',
      doubles_at_risp: 'RISP時二塁打',
      triples_at_risp: 'RISP時三塁打',
      singles_at_risp: 'RISP時単打',
      ab_at_risp: 'RISP時打数',
      avg_at_risp: 'RISP時打率',
      obp_at_risp: 'RISP時出塁率',
      slg_at_risp: 'RISP時長打率',
      ops_at_risp: 'RISP時OPS',
      strikeout_rate_at_risp: 'RISP時三振率',
      // Batting Splits - Bases Loaded
      hits_at_bases_loaded: '満塁時安打',
      grandslam: 'グランドスラム',
      doubles_at_bases_loaded: '満塁時二塁打',
      triples_at_bases_loaded: '満塁時三塁打',
      singles_at_bases_loaded: '満塁時単打',
      ab_at_bases_loaded: '満塁時打数',
      avg_at_bases_loaded: '満塁時打率',
      obp_at_bases_loaded: '満塁時出塁率',
      slg_at_bases_loaded: '満塁時長打率',
      ops_at_bases_loaded: '満塁時OPS',
      strikeout_rate_at_bases_loaded: '満塁時三振率'
    };

    return queryState.metrics.map(metricId => 
      metricNameMap[metricId] || metricId
    );
  };

  const estimatedTime = Math.ceil(queryState.metrics.length * 0.5 + 2); // Rough estimation

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 transition-colors duration-200">
          クエリプレビュー
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 transition-colors duration-200">
          設定内容を確認してクエリを実行してください
        </p>
      </div>

      {/* Query Summary Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="space-y-4">
          {/* Natural Language Summary */}
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-start space-x-3">
              <Eye className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-1">
                  クエリ概要
                </h4>
                <p className="text-blue-800 dark:text-blue-200 text-sm leading-relaxed">
                  {generateSummary()}
                </p>
              </div>
            </div>
          </div>

          {/* Query Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Category */}
            <div className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  カテゴリ
                </p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {queryState.category?.title || '未選択'}
                </p>
              </div>
            </div>

            {/* Player */}
            <div className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  選手
                </p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {queryState.player?.name || '未選択'}
                </p>
              </div>
            </div>

            {/* Season */}
            <div className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                <Calendar className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  シーズン
                </p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {queryState.seasonMode === 'all' ? '全シーズン' : `${queryState.specificYear}年`}
                </p>
              </div>
            </div>

            {/* Metrics Count */}
            <div className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
                <Target className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  指標数
                </p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {queryState.metrics.length}個選択済み
                </p>
              </div>
            </div>
          </div>

          {/* Selected Metrics */}
          {queryState.metrics.length > 0 && (
            <div>
              <h5 className="font-medium text-gray-900 dark:text-white mb-2">
                選択された指標
              </h5>
              <div className="flex flex-wrap gap-2">
                {getMetricNames().map((metricName, index) => (
                  <span
                    key={index}
                    className="inline-flex px-2 py-1 text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full"
                  >
                    {metricName}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Estimated Processing Time */}
          <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300">
            <Clock className="w-4 h-4" />
            <span>予想処理時間: 約{estimatedTime}秒</span>
          </div>
        </div>
      </div>

      {/* Validation Messages */}
      {!canExecute && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <h5 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">
            クエリを完成させてください
          </h5>
          <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
            {!queryState.category && <li>• カテゴリを選択してください</li>}
            {!queryState.player && <li>• 選手を選択してください</li>}
            {queryState.metrics.length === 0 && <li>• 少なくとも1つの指標を選択してください</li>}
          </ul>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          onClick={onReset}
          disabled={isLoading}
          className={`
            flex items-center justify-center space-x-2 px-6 py-3 text-sm font-medium rounded-lg transition-all duration-200
            ${isLoading
              ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-600 cursor-not-allowed'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }
          `}
        >
          <RotateCcw className="w-4 h-4" />
          <span>リセット</span>
        </button>

        <button
          onClick={onExecute}
          disabled={!canExecute || isLoading}
          className={`
            flex items-center justify-center space-x-2 px-8 py-3 text-sm font-medium rounded-lg transition-all duration-200
            ${canExecute && !isLoading
              ? 'bg-blue-600 dark:bg-blue-500 text-white hover:bg-blue-700 dark:hover:bg-blue-600 shadow-lg hover:shadow-xl transform hover:scale-105'
              : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
            }
          `}
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>実行中...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              <span>クエリを実行</span>
            </>
          )}
        </button>
      </div>

      {/* Additional Info */}
      <div className="text-center">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          クエリ実行後、結果はチャート形式で表示されます
        </p>
      </div>
    </div>
  );
};

export default QueryPreview;