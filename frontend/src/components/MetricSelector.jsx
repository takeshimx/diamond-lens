import React, { useState, useEffect } from 'react';
import { BarChart3, Target, Activity, TrendingUp, CheckCircle2, Circle } from 'lucide-react';

const MetricSelector = ({ category, selectedMetrics, onMetricsChange, isActive }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedGroups, setExpandedGroups] = useState({});

  // Metric definitions based on category
  const metricDefinitions = {
    season_batting: {
      basic: {
        title: '基本打撃指標',
        icon: BarChart3,
        color: 'bg-blue-500',
        metrics: [
          { id: 'plate_appearances', name: '打席数', description: '打席数', unit: 'PA' },
          { id: 'at_bats', name: '打数', description: '打数', unit: 'AB' },
          { id: 'games', name: '試合数', description: '試合数', unit: '試合' },
          { id: 'batting_average', name: '打率', description: '安打数 ÷ 打数', unit: '' },
          { id: 'home_runs', name: 'ホームラン', description: 'ホームラン数', unit: '本' },
          { id: 'rbi', name: 'RBI', description: '打点', unit: '点' },
          { id: 'runs', name: '得点', description: '得点数', unit: '点' },
          { id: 'hits', name: '安打', description: '安打数', unit: '本' },
          { id: 'doubles', name: '二塁打', description: '二塁打数', unit: '本' },
          { id: 'triples', name: '三塁打', description: '三塁打数', unit: '本' },
          { id: 'singles', name: '一塁打', description: '一塁打数', unit: '本' }
        ]
      },
      advanced: {
        title: '高度打撃指標',
        icon: TrendingUp,
        color: 'bg-purple-500',
        metrics: [
          { id: 'ops', name: 'OPS', description: '出塁率 + 長打率', unit: '' },
          { id: 'obp', name: '出塁率', description: '(安打+四球+死球) ÷ (打数+四球+死球+犠飛)', unit: '' },
          { id: 'slg', name: '長打率', description: '総塁打数 ÷ 打数', unit: '' },
          { id: 'woba', name: 'wOBA', description: '加重出塁率', unit: '' },
          { id: 'war', name: 'WAR', description: '代替選手に対する価値', unit: '' },
          { id: 'wrc_plus', name: 'wRC+', description: '調整済み得点創造', unit: '' },
        ]
      },
      plate_discipline: {
        title: '選球眼',
        icon: Target,
        color: 'bg-green-500',
        metrics: [
          { id: 'walks', name: '四球', description: '四球数', unit: '個' },
          { id: 'strikeouts', name: '三振', description: '三振数', unit: '個' },
          { id: 'walk_rate', name: 'BB%', description: '四球率', unit: '%' },
          { id: 'strikeout_rate', name: 'K%', description: '三振率', unit: '%' },
          { id: 'swing_rate', name: 'Swing%', description: 'スイング率', unit: '%' },
          { id: 'contact_rate', name: 'Contact%', description: 'コンタクト率', unit: '%' },
        ]
      },
      batted_ball: {
        title: '打球特性',
        icon: Activity,
        color: 'bg-red-500',
        metrics: [
          { id: 'babip', name: 'BABIP', description: '被本塁打以外の打球がヒットになる割合', unit: '' },
          { id: 'hard_hit_rate', name: 'ハードヒット率', description: 'ハードヒットの割合', unit: '%' },
          { id: 'barrels_rate', name: 'バレル率', description: 'バレルの割合', unit: '%' },
          { id: 'launch_angle', name: '打球角度', description: '平均打球角度', unit: '度' },
          { id: 'exit_velocity', name: '打球速度', description: '平均打球速度', unit: 'mph' },
        ]
      }
    },
    season_pitching: {
      basic: {
        title: '基本投手指標',
        icon: Target,
        color: 'bg-green-500',
        metrics: [
          { id: 'era', name: '防御率', description: '自責点 × 9 ÷ 投球回数', unit: '' },
          { id: 'wins', name: '勝利', description: '勝利数', unit: '勝' },
          { id: 'losses', name: '敗戦', description: '敗戦数', unit: '敗' },
          { id: 'saves', name: 'セーブ', description: 'セーブ数', unit: 'S' },
          { id: 'innings_pitched', name: '投球回', description: '投球回数', unit: '回' },
          { id: 'strikeouts', name: '奪三振', description: '奪三振数', unit: '個' },
          { id: 'walks', name: '四球', description: '与四球数', unit: '個' },
        ]
      },
      advanced: {
        title: '高度投手指標',
        icon: Activity,
        color: 'bg-purple-500',
        metrics: [
          { id: 'whip', name: 'WHIP', description: '(被安打+与四球) ÷ 投球回数', unit: '' },
          { id: 'fip', name: 'FIP', description: '守備無関係防御率', unit: '' },
          { id: 'xfip', name: 'xFIP', description: '予想FIP', unit: '' },
          { id: 'war', name: 'WAR', description: '代替選手に対する価値', unit: '' },
          { id: 'k_9', name: 'K/9', description: '9回あたり奪三振', unit: '' },
          { id: 'bb_9', name: 'BB/9', description: '9回あたり与四球', unit: '' },
        ]
      }
    },
    batting_splits: {
      situational: {
        title: '場面別成績',
        icon: Activity,
        color: 'bg-orange-500',
        metrics: [
          { id: 'risp_avg', name: 'RISP打率', description: '得点圏打率', unit: '' },
          { id: 'bases_loaded_avg', name: '満塁時打率', description: '満塁での打率', unit: '' },
          { id: 'clutch_avg', name: 'クラッチ打率', description: '接戦時の打率', unit: '' },
          { id: 'two_outs_risp', name: '2死得点圏打率', description: '2死得点圏での打率', unit: '' },
        ]
      },
      vs_pitcher: {
        title: '対投手別',
        icon: Target,
        color: 'bg-red-500',
        metrics: [
          { id: 'vs_lhp_avg', name: '対左投手打率', description: '左投手に対する打率', unit: '' },
          { id: 'vs_rhp_avg', name: '対右投手打率', description: '右投手に対する打率', unit: '' },
          { id: 'vs_lhp_ops', name: '対左投手OPS', description: '左投手に対するOPS', unit: '' },
          { id: 'vs_rhp_ops', name: '対右投手OPS', description: '右投手に対するOPS', unit: '' },
        ]
      }
    },
    monthly_trends: {
      monthly: {
        title: '月別指標',
        icon: TrendingUp,
        color: 'bg-blue-500',
        metrics: [
          { id: 'monthly_avg', name: '月別打率', description: '各月の打率推移', unit: '' },
          { id: 'monthly_hr', name: '月別ホームラン', description: '各月のホームラン数', unit: '本' },
          { id: 'monthly_rbi', name: '月別RBI', description: '各月の打点数', unit: '点' },
          { id: 'monthly_ops', name: '月別OPS', description: '各月のOPS', unit: '' },
          { id: 'monthly_obp', name: '月別出塁率', description: '各月の出塁率', unit: '' },
          { id: 'monthly_slg', name: '月別長打率', description: '各月の長打率', unit: '' },
          { id: 'monthly_singles', name: '月別単打', description: '各月の単打数', unit: '本' },
          { id: 'monthly_doubles', name: '月別二塁打', description: '各月の二塁打数', unit: '本' },
          { id: 'monthly_triples', name: '月別三塁打', description: '各月の三塁打数', unit: '本' },
          { id: 'monthly_hits', name: '月別ヒット', description: '各月のヒット数', unit: '本' },
          { id: 'monthly_bb_hbp', name: '月別四球・死球', description: '各月の四球・死球数', unit: '個' },
          { id: 'monthly_so', name: '月別三振', description: '各月の三振数', unit: '個' },
          { id: 'monthly_hard_hit_rate', name: '月別ハードヒット率', description: '各月のハードヒット率', unit: '%' },
          { id: 'monthly_barrels_rate', name: '月別バレル率', description: '各月のバレル率', unit: '%' },
          { id: 'monthly_strikeout_rate', name: '月別三振率', description: '各月の三振率', unit: '%' },
        ]
      }
    }
  };

  const availableMetrics = category ? metricDefinitions[category.id] || {} : {};

  // Filter metrics based on search term
  const filteredMetrics = {};
  Object.keys(availableMetrics).forEach(groupKey => {
    const group = availableMetrics[groupKey];
    const filteredGroupMetrics = group.metrics.filter(metric =>
      metric.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      metric.description.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    if (filteredGroupMetrics.length > 0) {
      filteredMetrics[groupKey] = {
        ...group,
        metrics: filteredGroupMetrics
      };
    }
  });

  // Initialize expanded groups
  useEffect(() => {
    const initialExpanded = {};
    Object.keys(availableMetrics).forEach(groupKey => {
      initialExpanded[groupKey] = true; // Expand all groups by default
    });
    setExpandedGroups(initialExpanded);
  }, [category]);

  const handleMetricToggle = (metricId) => {
    const updatedMetrics = selectedMetrics.includes(metricId)
      ? selectedMetrics.filter(id => id !== metricId)
      : [...selectedMetrics, metricId];
    
    onMetricsChange(updatedMetrics);
  };

  const handleSelectAll = (groupMetrics) => {
    const groupMetricIds = groupMetrics.map(m => m.id);
    const allSelected = groupMetricIds.every(id => selectedMetrics.includes(id));
    
    let updatedMetrics;
    if (allSelected) {
      // Deselect all in this group
      updatedMetrics = selectedMetrics.filter(id => !groupMetricIds.includes(id));
    } else {
      // Select all in this group
      const newSelections = groupMetricIds.filter(id => !selectedMetrics.includes(id));
      updatedMetrics = [...selectedMetrics, ...newSelections];
    }
    
    onMetricsChange(updatedMetrics);
  };

  const toggleGroupExpansion = (groupKey) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupKey]: !prev[groupKey]
    }));
  };

  if (!category) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <BarChart3 className="w-8 h-8 text-gray-400" />
        </div>
        <p className="text-gray-500 dark:text-gray-400">
          カテゴリを選択してください
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className={`text-xl font-semibold mb-2 transition-colors duration-200 ${
          isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'
        }`}>
          指標を選択
        </h3>
        <p className={`text-sm transition-colors duration-200 ${
          isActive ? 'text-gray-600 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
        }`}>
          分析したい指標を選択してください（複数選択可能）
        </p>
      </div>

      {/* Search Filter */}
      <div className="max-w-md mx-auto">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          disabled={!isActive}
          placeholder="指標を検索..."
          className={`
            w-full px-4 py-2 border rounded-lg text-sm transition-all duration-200
            ${isActive 
              ? 'border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent' 
              : 'border-gray-200 dark:border-gray-700 opacity-60 cursor-not-allowed'
            }
            bg-white dark:bg-gray-800 text-gray-900 dark:text-white
            placeholder-gray-500 dark:placeholder-gray-400
          `}
        />
      </div>

      {/* Selected Count */}
      {selectedMetrics.length > 0 && (
        <div className="text-center">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium transition-colors duration-200 ${
            isActive 
              ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
          }`}>
            {selectedMetrics.length}個の指標を選択中
          </span>
        </div>
      )}

      {/* Metric Groups */}
      <div className="space-y-4">
        {Object.keys(filteredMetrics).map(groupKey => {
          const group = filteredMetrics[groupKey];
          const IconComponent = group.icon;
          const isExpanded = expandedGroups[groupKey];
          const groupMetricIds = group.metrics.map(m => m.id);
          const allSelected = groupMetricIds.every(id => selectedMetrics.includes(id));
          const someSelected = groupMetricIds.some(id => selectedMetrics.includes(id));

          return (
            <div key={groupKey} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              {/* Group Header */}
              <div 
                className={`
                  flex items-center justify-between p-4 cursor-pointer transition-colors duration-200
                  ${isActive 
                    ? 'bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700'
                    : 'bg-gray-50 dark:bg-gray-800 opacity-60'
                  }
                `}
                onClick={() => isActive && toggleGroupExpansion(groupKey)}
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${group.color}`}>
                    <IconComponent className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h4 className={`font-medium transition-colors duration-200 ${
                      isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'
                    }`}>
                      {group.title}
                    </h4>
                    <p className={`text-xs transition-colors duration-200 ${
                      isActive ? 'text-gray-500 dark:text-gray-400' : 'text-gray-400 dark:text-gray-600'
                    }`}>
                      {group.metrics.length}個の指標
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      isActive && handleSelectAll(group.metrics);
                    }}
                    disabled={!isActive}
                    className={`text-sm font-medium transition-colors duration-200 ${
                      isActive
                        ? allSelected
                          ? 'text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300'
                          : 'text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300'
                        : 'text-gray-400 dark:text-gray-600'
                    }`}
                  >
                    {allSelected ? '全解除' : '全選択'}
                  </button>
                  
                  <div className={`transform transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Group Metrics */}
              {isExpanded && (
                <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {group.metrics.map(metric => {
                      const isSelected = selectedMetrics.includes(metric.id);
                      
                      return (
                        <button
                          key={metric.id}
                          onClick={() => isActive && handleMetricToggle(metric.id)}
                          disabled={!isActive}
                          className={`
                            flex items-start space-x-3 p-3 text-left rounded-lg border transition-all duration-200
                            ${isSelected 
                              ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' 
                              : isActive
                              ? 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                              : 'border-gray-200 dark:border-gray-700 opacity-60 cursor-not-allowed'
                            }
                          `}
                        >
                          <div className="flex-shrink-0 mt-0.5">
                            {isSelected ? (
                              <CheckCircle2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                            ) : (
                              <Circle className={`w-5 h-5 transition-colors duration-200 ${
                                isActive ? 'text-gray-400 dark:text-gray-500' : 'text-gray-300 dark:text-gray-600'
                              }`} />
                            )}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className={`font-medium text-sm transition-colors duration-200 ${
                              isSelected 
                                ? 'text-blue-900 dark:text-blue-100' 
                                : isActive
                                ? 'text-gray-900 dark:text-white'
                                : 'text-gray-600 dark:text-gray-400'
                            }`}>
                              {metric.name}
                              {metric.unit && (
                                <span className={`ml-1 font-normal transition-colors duration-200 ${
                                  isSelected 
                                    ? 'text-blue-700 dark:text-blue-200' 
                                    : isActive
                                    ? 'text-gray-500 dark:text-gray-400'
                                    : 'text-gray-400 dark:text-gray-600'
                                }`}>
                                  ({metric.unit})
                                </span>
                              )}
                            </div>
                            <p className={`text-xs mt-1 transition-colors duration-200 ${
                              isSelected 
                                ? 'text-blue-700 dark:text-blue-200' 
                                : isActive
                                ? 'text-gray-500 dark:text-gray-400'
                                : 'text-gray-400 dark:text-gray-600'
                            }`}>
                              {metric.description}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* No Results */}
      {searchTerm && Object.keys(filteredMetrics).length === 0 && (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="w-8 h-8 text-gray-400" />
          </div>
          <p className={`text-gray-500 dark:text-gray-400 transition-colors duration-200`}>
            「{searchTerm}」に一致する指標が見つかりません
          </p>
        </div>
      )}
    </div>
  );
};

export default MetricSelector;