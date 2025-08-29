import React from 'react';

const MetricOrderSelector = ({ selectedMetricOrder, onMetricOrderChange, category }) => {
  // Define available metrics for ordering based on category
  const metricOrderOptions = {
    batting_leaderboard: [
      { value: 'ops', label: 'OPS' },
      { value: 'avg', label: '打率' },
      { value: 'hr', label: 'ホームラン' },
      { value: 'rbi', label: 'RBI' },
      { value: 'r', label: '得点' },
      { value: 'h', label: '安打' },
      { value: 'obp', label: '出塁率' },
      { value: 'slg', label: '長打率' },
      { value: 'woba', label: 'wOBA' },
      { value: 'war', label: 'fWAR' },
      { value: 'wrcplus', label: 'wRC+' },
      { value: 'bb', label: '四球' },
      { value: 'so', label: '三振' },
      // { value: 'strikeout_rate', label: 'K%' },
      { value: 'babip', label: 'BABIP' },
      { value: 'iso', label: 'ISO' },
      { value: 'hardhitpct', label: 'ハードヒット率' },
      { value: 'barrelspct', label: 'バレル率' },
      { value: 'batting_average_at_risp', label: 'RISP時打率' },
      { value: 'slugging_percentage_at_risp', label: 'RISP時長打率' },
      { value: 'home_runs_at_risp', label: 'RISP時ホームラン' }
    ],
    pitching_leaderboard: [
      { value: 'era', label: '防御率' },
      { value: 'whip', label: 'WHIP' },
      { value: 'so', label: '奪三振' },
      { value: 'w', label: '勝利' },
      { value: 'sv', label: 'セーブ' },
      { value: 'fip', label: 'FIP' },
      { value: 'war', label: 'fWAR' },
      { value: 'k_9', label: 'K/9' },
      { value: 'bb_9', label: 'BB/9' },
      { value: 'k_bb', label: 'K/BB' },
      { value: 'lobpct', label: 'LOB%' },
      { value: 'gbpct', label: 'GB%' },
      { value: 'barrelpct', label: 'Barrel%' },
      { value: 'hardhitpct', label: 'Hard Hit%' },
      { value: 'avg', label: '被打率' },
      { value: 'ip', label: 'IP' },
      { value: 'gs', label: '先発' },
      { value: 'bb', label: '与四球' },
      { value: 'hr', label: '被本塁打' },
      { value: 'h', label: '被安打' }
    ]
  };

  const currentOptions = metricOrderOptions[category?.id] || [];
  
  // Set default metric order based on category
  const getDefaultMetricOrder = (categoryId) => {
    if (categoryId === 'batting_leaderboard') return 'ops';
    if (categoryId === 'pitching_leaderboard') return 'era';
    return '';
  };

  // If no metric order is selected, use the default
  const effectiveMetricOrder = selectedMetricOrder || getDefaultMetricOrder(category?.id);

  return (
    <div className="step-container">
      <h3>ソート指標を選択</h3>
      <div className="options-container">
        {currentOptions.map((option) => (
          <button
            key={option.value}
            className={`option-button ${effectiveMetricOrder === option.value ? 'selected' : ''}`}
            onClick={() => onMetricOrderChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default MetricOrderSelector;