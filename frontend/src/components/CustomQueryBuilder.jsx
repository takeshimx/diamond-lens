import React, { useState } from 'react';
import { TrendingUp } from 'lucide-react';
import CategorySelector from './CategorySelector.jsx';
import PlayerAutocomplete from './PlayerAutocomplete.jsx';
import SeasonSelector from './SeasonSelector.jsx';
import MetricSelector from './MetricSelector.jsx';
import QueryPreview from './QueryPreview.jsx';
import SimpleChatChart from './ChatChart.jsx';
import LeagueSelector from './LeagueSelector.jsx';
import MetricOrderSelector from './MetricOrderSelector.jsx';
import LeaderboardTable from './LeaderboardTable.jsx';

const CustomQueryBuilder = ({ isLoading, onExecuteQuery, customResult, onClearResult, onSearchPlayers }) => {
  // Query builder state
  const [queryState, setQueryState] = useState({
    category: null,
    player: null,
    seasonMode: 'specific', // 'all' or 'specific'
    specificYear: 2024,
    metrics: [],
    league: 'MLB', // For leaderboard categories
    metricOrder: '', // For leaderboard categories
    step: 1 // Current step in the builder (1-5)
  });

  // Update query state
  const updateQueryState = (updates) => {
    setQueryState(prev => ({ ...prev, ...updates }));
  };

  // Reset builder to initial state
  const resetBuilder = () => {
    setQueryState({
      category: null,
      player: null,
      seasonMode: 'specific',
      specificYear: 2024,
      metrics: [],
      league: 'MLB',
      metricOrder: '',
      step: 1
    });
    if (onClearResult) {
      onClearResult();
    }
  };

  // Execute the query
  const executeQuery = () => {
    if (onExecuteQuery) {
      onExecuteQuery(queryState);
    }
  };

  // Check if current step is complete
  const isStepComplete = (step) => {
    const isLeaderboard = queryState.category && 
      (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
    
    switch (step) {
      case 1: return queryState.category !== null;
      case 2: 
        if (isLeaderboard) return true; // Skip player selection for leaderboards
        return queryState.player !== null;
      case 3: return true; // Season selection always valid (has default)
      case 4: 
        if (isLeaderboard) return queryState.metricOrder !== '';
        return queryState.metrics.length > 0;
      case 5: 
        if (isLeaderboard) return isStepComplete(1) && isStepComplete(3) && isStepComplete(4);
        return isStepComplete(1) && isStepComplete(2) && isStepComplete(4);
      default: return false;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 transition-colors duration-200">
          カスタムクエリ作成
        </h2>
        <p className="text-gray-600 dark:text-gray-300 transition-colors duration-200">
          ステップに従って詳細な分析クエリを作成できます
        </p>
      </div>

      {/* Progress Indicator */}
      <div className="flex items-center justify-center space-x-4">
        {[1, 2, 3, 4, 5].map((step) => (
          <div key={step} className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors duration-200 ${
              queryState.step > step || isStepComplete(step)
                ? 'bg-blue-600 dark:bg-blue-500 text-white'
                : queryState.step === step
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 border-2 border-blue-600 dark:border-blue-500'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}>
              {step}
            </div>
            {step < 5 && (
              <div className={`w-12 h-0.5 mx-2 transition-colors duration-200 ${
                queryState.step > step ? 'bg-blue-600 dark:bg-blue-500' : 'bg-gray-200 dark:bg-gray-700'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* Step Labels */}
      <div className="grid grid-cols-5 gap-4 text-center text-xs text-gray-500 dark:text-gray-400">
        {(() => {
          const isLeaderboard = queryState.category && 
            (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
          
          if (isLeaderboard) {
            return (
              <>
                <div>カテゴリ</div>
                <div>リーグ</div>
                <div>シーズン</div>
                <div>ソート指標</div>
                <div>実行</div>
              </>
            );
          } else {
            return (
              <>
                <div>カテゴリ</div>
                <div>選手選択</div>
                <div>シーズン</div>
                <div>指標選択</div>
                <div>実行</div>
              </>
            );
          }
        })()}
      </div>

      {/* Query Builder Steps */}
      <div className="space-y-8">
        {/* Step 1: Category Selection */}
        {queryState.step >= 1 && (
          <div className={`transition-opacity duration-300 ${
            queryState.step === 1 ? 'opacity-100' : 'opacity-75'
          }`}>
            <CategorySelector 
              selectedCategory={queryState.category}
              onCategorySelect={(category) => {
                const isLeaderboard = category.id === 'batting_leaderboard' || category.id === 'pitching_leaderboard';
                // Set default metricOrder for leaderboards
                const defaultMetricOrder = category.id === 'batting_leaderboard' ? 'ops' : 
                                         category.id === 'pitching_leaderboard' ? 'era' : '';
                updateQueryState({ 
                  category, 
                  metricOrder: isLeaderboard ? defaultMetricOrder : queryState.metricOrder,
                  step: 2 
                });
              }}
              isActive={queryState.step === 1}
            />
          </div>
        )}

        {/* Step 2: Player Selection or League Selection */}
        {queryState.step >= 2 && (() => {
          const isLeaderboard = queryState.category && 
            (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
          
          if (isLeaderboard) {
            return (
              <div className={`transition-opacity duration-300 ${
                queryState.step === 2 ? 'opacity-100' : 'opacity-75'
              }`}>
                <LeagueSelector
                  selectedLeague={queryState.league}
                  onLeagueChange={(league) => {
                    updateQueryState({ league, step: 3 });
                  }}
                  isActive={queryState.step === 2}
                />
              </div>
            );
          } else {
            return (
              <div className={`transition-opacity duration-300 ${
                queryState.step === 2 ? 'opacity-100' : 'opacity-75'
              }`}>
                <PlayerAutocomplete
                  selectedPlayer={queryState.player}
                  onPlayerSelect={(player) => {
                    updateQueryState({ player, step: 3 });
                  }}
                  isActive={queryState.step === 2}
                  onSearchPlayers={onSearchPlayers}
                />
              </div>
            );
          }
        })()}

        {/* Step 3: Season Selection */}
        {queryState.step >= 3 && (
          <div className={`transition-opacity duration-300 ${
            queryState.step === 3 ? 'opacity-100' : 'opacity-75'
          }`}>
            <SeasonSelector
              seasonMode={queryState.seasonMode}
              specificYear={queryState.specificYear}
              onSeasonChange={(seasonMode, specificYear) => {
                updateQueryState({ seasonMode, specificYear, step: 4 });
              }}
              isActive={queryState.step === 3}
            />
          </div>
        )}

        {/* Step 4: Metrics Selection or Metric Order Selection */}
        {queryState.step >= 4 && queryState.category && (() => {
          const isLeaderboard = queryState.category && 
            (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
          
          if (isLeaderboard) {
            return (
              <div className={`transition-opacity duration-300 ${
                queryState.step === 4 ? 'opacity-100' : 'opacity-75'
              }`}>
                <MetricOrderSelector
                  selectedMetricOrder={queryState.metricOrder}
                  onMetricOrderChange={(metricOrder) => {
                    updateQueryState({ 
                      metricOrder, 
                      step: metricOrder ? 5 : 4 
                    });
                  }}
                  category={queryState.category}
                  isActive={queryState.step === 4}
                />
              </div>
            );
          } else {
            return (
              <div className={`transition-opacity duration-300 ${
                queryState.step === 4 ? 'opacity-100' : 'opacity-75'
              }`}>
                <MetricSelector
                  category={queryState.category}
                  selectedMetrics={queryState.metrics}
                  onMetricsChange={(metrics) => {
                    console.log('CustomQueryBuilder: Received metrics update:', metrics);
                    console.log('CustomQueryBuilder: Current queryState.metrics:', queryState.metrics);
                    console.log('CustomQueryBuilder: Current step:', queryState.step);
                    console.log('CustomQueryBuilder: isActive will be:', queryState.step === 4);
                    updateQueryState({ 
                      metrics 
                      // Don't auto-advance step - let user manually go to step 5
                    });
                  }}
                  isActive={queryState.step === 4}
                />
              </div>
            );
          }
        })()}

        {/* Step 5: Query Preview & Execute */}
        {queryState.step >= 5 && (
          <div className="transition-opacity duration-300 opacity-100">
            <QueryPreview
              queryState={queryState}
              onExecute={executeQuery}
              onReset={resetBuilder}
              isLoading={isLoading}
              canExecute={isStepComplete(5)}
            />
          </div>
        )}
      </div>

      {/* Navigation Buttons (for steps 2-4) */}
      {queryState.step > 1 && queryState.step < 5 && (
        <div className="flex justify-between">
          <button
            onClick={() => updateQueryState({ step: queryState.step - 1 })}
            className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors duration-200"
          >
            ← 前のステップ
          </button>
          
          {isStepComplete(queryState.step) && (
            <button
              onClick={() => updateQueryState({ step: queryState.step + 1 })}
              className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors duration-200"
            >
              次のステップ →
            </button>
          )}
        </div>
      )}

      {/* Results Display Section */}
      {customResult && (() => {
        console.log('🔍 CustomQueryBuilder - customResult:', customResult);
        console.log('🔍 CustomQueryBuilder - isMultiChart:', customResult.isMultiChart);
        console.log('🔍 CustomQueryBuilder - charts:', customResult.charts);
        const isLeaderboardResult = customResult.isLeaderboard || 
          (queryState.category && 
           (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard'));
        
        if (isLeaderboardResult) {
          return (
            <div className="mt-8 border-t border-gray-200 dark:border-gray-700 pt-8">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white transition-colors duration-200">
                  リーダーボード結果
                </h3>
                <button
                  onClick={onClearResult}
                  className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors duration-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  結果をクリア
                </button>
              </div>
              
              <LeaderboardTable
                data={customResult.data || customResult.leaderboardData}
                category={queryState.category}
                metricOrder={queryState.metricOrder}
                isLoading={false}
                error={customResult.error}
              />
            </div>
          );
        }
        
        return (
        <div className="mt-8 border-t border-gray-200 dark:border-gray-700 pt-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white transition-colors duration-200">
              クエリ結果
            </h3>
            <button
              onClick={onClearResult}
              className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors duration-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              結果をクリア
            </button>
          </div>

          {/* Query Summary */}
          <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
              実行されたクエリ
            </h4>
            <p className="text-blue-800 dark:text-blue-200 text-sm">
              {customResult.query}
            </p>
          </div>

          {/* Result Content */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            {/* Answer Text */}
            <div className="mb-4">
              <p className="text-gray-900 dark:text-white whitespace-pre-wrap">
                {customResult.answer}
              </p>
            </div>

            {/* Multiple Charts Display */}
            {customResult.isMultiChart && customResult.charts && (
              <div className="mb-4 space-y-6">
                {customResult.charts.map((chart, index) => (
                  <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <h5 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                      {chart.metricDisplayName} の月別推移
                    </h5>
                    <SimpleChatChart 
                      chartData={chart.chartData}
                      chartConfig={chart.chartConfig}
                      chartType={chart.chartType}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* Chart Display */}
            {customResult.isChart && customResult.chartData && customResult.chartConfig && (
              <div className="mb-4">
                <SimpleChatChart 
                  chartData={customResult.chartData}
                  chartConfig={customResult.chartConfig}
                  chartType={customResult.chartType}
                />
              </div>
            )}

            {/* Table Display */}
            {customResult.isTable && customResult.tableData && customResult.columns && (
              <div className="mb-4">
                <div className="overflow-x-auto">
                  <div className="inline-block min-w-full align-middle">
                    <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg">
                      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800">
                          <tr>
                            {customResult.columns.map((column) => (
                              <th
                                key={column.key}
                                className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                              >
                                {column.label}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600">
                          {customResult.tableData.map((row, index) => (
                            <tr key={index} className={index % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
                              {customResult.columns.map((column) => (
                                <td
                                  key={column.key}
                                  className="px-4 py-3 text-sm text-gray-900 dark:text-white whitespace-nowrap"
                                >
                                  {typeof row[column.key] === 'number' 
                                    ? row[column.key].toLocaleString('ja-JP')
                                    : row[column.key]
                                  }
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* KPI Cards Display */}
            {customResult.isCards && customResult.cardsData && (
              <div className="mb-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {customResult.cardsData.map((card, index) => {
                    // Define metric display names based on context (batting vs pitching)
                    const getMetricDisplayName = (metric, isPitching = false) => {
                      const battingMetrics = {
                        'pa': '打席数',
                        'ab': '打数',
                        'g': '試合数',
                        'avg': '打率',
                        'obp': '出塁率',
                        'slg': '長打率',
                        'ops': 'OPS',
                        'h': '安打数',
                        'hr': '本塁打',
                        'doubles': '二塁打',
                        'triples': '三塁打',
                        'singles': '単打',
                        'rbi': '打点',
                        'r': '得点',
                        'bb': '四球',
                        'so': '三振',
                        'war': 'fWAR',
                        'woba': 'wOBA',
                        'babip': 'BABIP',
                        'iso': 'ISO',
                        'wrcplus': 'wRC+',
                        'hardhitpct': 'ハードヒット率',
                        'barrelpct': 'バレル率',
                        'batting_average_at_risp': 'RISP時打率',
                        'slugging_percentage_at_risp': 'RISP時長打率',
                        'home_runs_at_risp': 'RISP時HR'
                      };
                      
                      const pitchingMetrics = {
                        'era': '防御率',
                        'whip': 'WHIP',
                        'fip': 'FIP',
                        'w': '勝利数',
                        'l': '敗戦数',
                        'sv': 'セーブ数',
                        'g': '登板数',
                        'gs': '先発数',
                        'cg': '完投数',
                        'sho': '完封数',
                        'ip': '投球回',
                        'so': '奪三振数',
                        'avg': '被打率',
                        'h': '被安打数',
                        'hr': '被本塁打数',
                        'bb': '与四球数',
                        'r': '失点',
                        'er': '自責点',
                        'k_9': 'K/9',
                        'bb_9': 'BB/9',
                        'k_bb': 'K/BB',
                        'hr_9': 'HR/9',
                        'lobpct': '残塁率',
                        'gbpct': 'ゴロ率',
                        'swstrpct': 'スイングミス率',
                        'hardhitpct': '被ハードヒット率',
                        'barrelpct': '被バレル率',
                        'war': 'fWAR'
                      };
                      
                      if (isPitching) {
                        return pitchingMetrics[metric] || metric;
                      } else {
                        return battingMetrics[metric] || metric;
                      }
                    };
                    
                    // Detect if this is a pitching metric card
                    // Check if ANY card in the current result set contains pitching-only metrics
                    const isPitchingContext = customResult.cardsData.some(c => 
                      ['era', 'whip', 'fip', 'w', 'l', 'sv', 'gs', 'cg', 'sho', 'ip', 'k_9', 'bb_9', 'k_bb', 'hr_9', 'lobpct', 'gbpct', 'swstrpct'].includes(c.metric)
                    );
                    const isPitchingCard = isPitchingContext;

                    // Define rate stats that should show 3 decimal places
                    const rateStats = ['avg', 'obp', 'slg', 'ops', 'woba', 'hardhitpct', 'barrelpct', 'babip', 'iso', 'lobpct', 'gbpct', 'swstrpct', 'batting_average_at_risp', 'slugging_percentage_at_risp'];
                    // Define rate stats that should show 1 decimal place
                    const oneDecimalRateStats = ['ip', 'war', 'k_9', 'bb_9', 'k_bb', 'hr_9'];
                    // Define rate stats that should show 2 decimal places
                    const twoDecimalRateStats = ['era', 'fip', 'whip'];

                    // Format value based on metric type
                    const formatValue = (value, metric) => {
                      if (value === null || value === undefined) return 'N/A';
                      
                      if (rateStats.includes(metric)) {
                        return Number(value).toFixed(3);
                      } else if (oneDecimalRateStats.includes(metric)) {
                        return Number(value).toFixed(1);
                      } else if (twoDecimalRateStats.includes(metric)) {
                        return Number(value).toFixed(2);
                      } else {
                        return Math.round(Number(value)).toLocaleString('ja-JP');
                      }
                    };

                    // Get gradient colors based on metric type
                    const getCardColors = (metric) => {
                      if (rateStats.includes(metric)) {
                        return {
                          bg: 'from-blue-500 to-blue-600',
                          icon: 'text-blue-100',
                          text: 'text-blue-100'
                        };
                      } else {
                        return {
                          bg: 'from-green-500 to-green-600', 
                          icon: 'text-green-100',
                          text: 'text-green-100'
                        };
                      }
                    };

                    const colors = getCardColors(card.metric);
                    const displayName = getMetricDisplayName(card.metric, isPitchingCard);
                    const formattedValue = formatValue(card.value, card.metric);

                    return (
                      <div 
                        key={index}
                        className={`p-6 rounded-xl bg-gradient-to-br ${colors.bg} shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1`}
                      >
                        <div className="flex items-center justify-between mb-4">
                          <div className={`p-3 rounded-lg bg-white bg-opacity-20 ${colors.icon}`}>
                            <TrendingUp className="w-6 h-6" />
                          </div>
                          <div className={`text-sm font-medium ${colors.text} opacity-90`}>
                            {card.season}年
                          </div>
                        </div>
                        
                        <div className="mb-2">
                          <div className={`text-3xl font-bold ${colors.text} mb-1`}>
                            {formattedValue}
                          </div>
                          <div className={`text-lg font-medium ${colors.text} opacity-90`}>
                            {displayName}
                          </div>
                        </div>
                        
                        <div className={`text-sm ${colors.text} opacity-75 border-t border-white border-opacity-20 pt-3 mt-3`}>
                          {card.playerName}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Stats Display */}
            {customResult.stats && (
              <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-sm font-semibold text-blue-800 dark:text-blue-300">統計データ</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(customResult.stats).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">{key}:</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timestamp */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                実行時刻: {customResult.timestamp.toLocaleTimeString('ja-JP', { 
                  hour: '2-digit', 
                  minute: '2-digit',
                  second: '2-digit'
                })}
              </p>
            </div>
          </div>
        </div>
        );
      })()}
    </div>
  );
};

export default CustomQueryBuilder;