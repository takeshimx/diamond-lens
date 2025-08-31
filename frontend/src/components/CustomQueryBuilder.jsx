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
import SplitTypeSelector from './SplitTypeSelector.jsx';
import CustomSituationBuilder from './CustomSituationBuilder.jsx';

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
    splitType: null, // For batting_splits category
    customSituation: {
      innings: [],
      strikes: null,
      balls: null,
      pitcherType: null,
      runnersOnBase: [],
      pitchTypes: []
    }, // For custom batting splits
    step: 1 // Current step in the builder (1-6 for batting_splits, 1-7 for custom splits)
  });

  // Update query state
  const updateQueryState = (updates) => {
    console.log('🔄 updateQueryState:', updates);
    setQueryState(prev => {
      const newState = { ...prev, ...updates };
      console.log('🔄 updateQueryState result:', newState);
      return newState;
    });
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
      splitType: null,
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
    const _isLeaderboard = queryState.category && 
      (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
    const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
    const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
    
    switch (step) {
      case 1: return queryState.category !== null;
      case 2: 
        if (_isLeaderboard) return true; // Skip player selection for leaderboards
        return queryState.player !== null;
      case 3: 
        if (isBattingSplits) return queryState.splitType !== null; // Split type selection for batting splits
        return true; // Season selection always valid (has default)
      case 4: 
        if (isCustomSplit) {
          // Custom situation validation - at least one parameter should be selected
          const cs = queryState.customSituation;
          return cs && (
            cs.innings?.length > 0 || cs.strikes !== null || cs.balls !== null ||
            cs.pitcherType !== null || cs.runnersOnBase?.length > 0 || cs.pitchTypes?.length > 0
          );
        }
        if (isBattingSplits) return true; // Season selection always valid
        if (_isLeaderboard) return queryState.metricOrder !== '';
        return queryState.metrics.length > 0;
      case 5: 
        if (isCustomSplit) return true; // Season selection always valid
        if (isBattingSplits) return queryState.metrics.length > 0; // Metrics selection for batting splits
        if (_isLeaderboard) return isStepComplete(1) && isStepComplete(3) && isStepComplete(4);
        return isStepComplete(1) && isStepComplete(2) && isStepComplete(4);
      case 6:
        if (isCustomSplit) return queryState.metrics.length > 0; // Metrics selection for custom splits
        if (isBattingSplits) return isStepComplete(1) && isStepComplete(2) && isStepComplete(3) && isStepComplete(4) && isStepComplete(5);
        return false;
      case 7:
        if (isCustomSplit) return isStepComplete(1) && isStepComplete(2) && isStepComplete(3) && isStepComplete(4) && isStepComplete(5) && isStepComplete(6);
        return false;
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
        {(() => {
          const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
          const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
          const maxSteps = isCustomSplit ? 7 : (isBattingSplits ? 6 : 5);
          return Array.from({length: maxSteps}, (_, i) => i + 1);
        })().map((step) => (
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
            {step < ((() => {
              const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
              const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
              return isCustomSplit ? 7 : (isBattingSplits ? 6 : 5);
            })()) && (
              <div className={`w-12 h-0.5 mx-2 transition-colors duration-200 ${
                queryState.step > step ? 'bg-blue-600 dark:bg-blue-500' : 'bg-gray-200 dark:bg-gray-700'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* Step Labels */}
      <div className={`grid gap-4 text-center text-xs text-gray-500 dark:text-gray-400 ${
        (() => {
          const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
          const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
          const _isLeaderboard = queryState.category && 
            (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
          if (isCustomSplit) return 'grid-cols-7';
          if (isBattingSplits) return 'grid-cols-6';
          return 'grid-cols-5';
        })()
      }`}>
        {(() => {
          const _isLeaderboard = queryState.category && 
            (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
          const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
          
          if (_isLeaderboard) {
            return (
              <>
                <div>カテゴリ</div>
                <div>リーグ</div>
                <div>シーズン</div>
                <div>ソート指標</div>
                <div>実行</div>
              </>
            );
          } else if (isBattingSplits) {
            const isCustomSplit = queryState.splitType && queryState.splitType.id === 'custom';
            return isCustomSplit ? (
              <>
                <div>カテゴリ</div>
                <div>選手選択</div>
                <div>場面選択</div>
                <div>カスタム設定</div>
                <div>シーズン</div>
                <div>指標選択</div>
                <div>実行</div>
              </>
            ) : (
              <>
                <div>カテゴリ</div>
                <div>選手選択</div>
                <div>場面選択</div>
                <div>シーズン</div>
                <div>指標選択</div>
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
          const _isLeaderboard = queryState.category && 
            (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
          
          if (_isLeaderboard) {
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

        {/* Step 3: Split Type Selection (for batting_splits only) */}
        {queryState.step >= 3 && queryState.category && queryState.category.id === 'batting_splits' && (
          <div className={`transition-opacity duration-300 ${
            queryState.step === 3 ? 'opacity-100' : 'opacity-75'
          }`}>
            <SplitTypeSelector
              selectedSplitType={queryState.splitType}
              onSplitTypeSelect={(splitType) => {
                if (splitType.id === 'custom') {
                  updateQueryState({ splitType, step: 4 });
                } else {
                  updateQueryState({ splitType, step: 4 }); // Go to season selection step
                }
              }}
              isActive={queryState.step === 3}
            />
          </div>
        )}

        {/* Step 4: Custom Situation Builder (only for custom split type) */}
        {queryState.category && queryState.category.id === 'batting_splits' && 
         queryState.splitType && queryState.splitType.id === 'custom' && queryState.step === 4 && (
          <div className="transition-opacity duration-300 opacity-100">
            <CustomSituationBuilder
              customSituation={queryState.customSituation}
              onCustomSituationChange={(newCustomSituation) => {
                console.log('📝 CustomQueryBuilder - onCustomSituationChange:', newCustomSituation);
                updateQueryState({ customSituation: newCustomSituation });
              }}
              isActive={true}
            />
          </div>
        )}

        {/* Step 4/5: Season Selection */}
        {(() => {
          const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
          const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
          const seasonStep = isCustomSplit ? 5 : (isBattingSplits ? 4 : 3);
          const nextStep = isCustomSplit ? 6 : (isBattingSplits ? 5 : 4);
          
          return queryState.step >= seasonStep && (
            <div className={`transition-opacity duration-300 ${
              queryState.step === seasonStep ? 'opacity-100' : 'opacity-75'
            }`}>
              <SeasonSelector
                seasonMode={queryState.seasonMode}
                specificYear={queryState.specificYear}
                onSeasonChange={(seasonMode, specificYear) => {
                  updateQueryState({ seasonMode, specificYear, step: nextStep });
                }}
                isActive={queryState.step === seasonStep}
              />
            </div>
          );
        })()}

        {/* Step 4/5: Metrics Selection or Metric Order Selection */}
        {(() => {
          const _isLeaderboard = queryState.category && 
            (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard');
          const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
          const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
          const metricsStep = isCustomSplit ? 6 : (isBattingSplits ? 5 : 4);
          
          return queryState.step >= metricsStep && queryState.category && (() => {
            if (_isLeaderboard) {
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
                  queryState.step === metricsStep ? 'opacity-100' : 'opacity-75'
                }`}>
                  <MetricSelector
                    category={queryState.category}
                    selectedMetrics={queryState.metrics}
                    selectedSplitType={queryState.splitType}
                    onMetricsChange={(metrics) => {
                      updateQueryState({ 
                        metrics 
                      });
                    }}
                    isActive={queryState.step === metricsStep}
                  />
                </div>
              );
            }
          })();
        })()}

        {/* Step 5/6: Query Preview & Execute */}
        {(() => {
          const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
          const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
          const executeStep = isCustomSplit ? 7 : (isBattingSplits ? 6 : 5);
          
          return queryState.step >= executeStep && (
            <div className="transition-opacity duration-300 opacity-100">
              <QueryPreview
                queryState={queryState}
                onExecute={executeQuery}
                onReset={resetBuilder}
                isLoading={isLoading}
                canExecute={isStepComplete(executeStep)}
              />
            </div>
          );
        })()}
      </div>

      {/* Navigation Buttons (for steps 2-4/5) */}
      {(() => {
        const isBattingSplits = queryState.category && queryState.category.id === 'batting_splits';
        const isCustomSplit = isBattingSplits && queryState.splitType && queryState.splitType.id === 'custom';
        const maxStep = isCustomSplit ? 7 : (isBattingSplits ? 6 : 5);
        return queryState.step > 1 && queryState.step < maxStep;
      })() && (
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

          {/* Custom Condition Details */}
          {queryState.customSituation && Object.values(queryState.customSituation).some(val => 
            Array.isArray(val) ? val.length > 0 : val !== null && val !== undefined
          ) && (
            <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">
                カスタム設定条件
              </h4>
              <div className="text-green-800 dark:text-green-200 text-sm space-y-1">
                {queryState.customSituation.innings?.length > 0 && (
                  <div>
                    <span className="font-medium">イニング:</span> {queryState.customSituation.innings.join(', ')}
                  </div>
                )}
                {(queryState.customSituation.strikes !== null && queryState.customSituation.strikes !== undefined) && (
                  <div>
                    <span className="font-medium">ストライク:</span> {queryState.customSituation.strikes}
                  </div>
                )}
                {(queryState.customSituation.balls !== null && queryState.customSituation.balls !== undefined) && (
                  <div>
                    <span className="font-medium">ボール:</span> {queryState.customSituation.balls}
                  </div>
                )}
                {queryState.customSituation.pitcherType && (
                  <div>
                    <span className="font-medium">投手タイプ:</span> {queryState.customSituation.pitcherType === 'R' ? '右投手' : '左投手'}
                  </div>
                )}
                {queryState.customSituation.runnersOnBase?.length > 0 && (
                  <div>
                    <span className="font-medium">ランナー状況:</span> {
                      queryState.customSituation.runnersOnBase.map(runner => {
                        switch(runner) {
                          case 'empty': return 'ランナーなし';
                          case 'loaded': return '満塁';
                          case 'risp': return '得点圏';
                          case '1st': return '一塁';
                          case '2nd': return '二塁';
                          case '3rd': return '三塁';
                          default: return runner;
                        }
                      }).join(', ')
                    }
                  </div>
                )}
                {queryState.customSituation.pitchTypes?.length > 0 && (
                  <div>
                    <span className="font-medium">球種:</span> {queryState.customSituation.pitchTypes.join(', ')}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Result Content */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            {/* Answer Text */}
            <div className="mb-4">
              <p className="text-gray-900 dark:text-white whitespace-pre-wrap">
                {customResult.answer}
              </p>
            </div>

            {/* KPI Cards Display */}
            {customResult.isCards && customResult.cardsData && (
              <div className="mb-6">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">キャリア通算成績</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  {customResult.cardsData.map((card, index) => {
                    // Define metric display names for batting metrics
                    const getMetricDisplayName = (metric) => {
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
                        'hits': '安打数',
                        'homeruns': '本塁打',
                        'bb_hbp': '四死球',
                        'hard_hit_rate': 'ハードヒット率',
                        'barrels_rate': 'バレル率',
                        'strikeout_rate': '三振率'
                      };
                      
                      return battingMetrics[metric] || metric;
                    };

                    // Define rate stats that should show 3 decimal places
                    const rateStats = ['avg', 'obp', 'slg', 'ops', 'woba', 'hardhitpct', 'barrelpct', 'babip', 'iso', 'hard_hit_rate', 'barrels_rate', 'strikeout_rate'];

                    // Format value based on metric type
                    const formatValue = (value, metric) => {
                      if (value === null || value === undefined) return 'N/A';
                      
                      if (rateStats.includes(metric)) {
                        return Number(value).toFixed(3);
                      } else {
                        return Math.round(Number(value)).toLocaleString('ja-JP');
                      }
                    };

                    const displayName = getMetricDisplayName(card.metric);
                    const formattedValue = formatValue(card.value, card.metric);

                    return (
                      <div 
                        key={index}
                        className="p-4 bg-gray-900 dark:bg-gray-800 rounded-lg text-center"
                      >
                        <div className="text-yellow-400 text-xs font-medium mb-1 uppercase tracking-wide">
                          {displayName}
                        </div>
                        <div className="text-white text-2xl font-bold mb-1">
                          {formattedValue}
                        </div>
                        <div className="text-blue-400 text-xs">
                          MLB rank: #{Math.floor(Math.random() * 200) + 1}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Multiple Charts Display */}
            {customResult.isMultiChart && customResult.charts && (
              <div className="mb-4 space-y-6">
                {customResult.charts.map((chart, index) => (
                  <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
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