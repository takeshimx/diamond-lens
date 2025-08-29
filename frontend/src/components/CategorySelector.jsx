import React from 'react';
import { BarChart3, Activity, TrendingUp, Users, Target, Calendar } from 'lucide-react';

const CategorySelector = ({ selectedCategory, onCategorySelect, isActive }) => {
  const categories = [
    {
      id: 'season_batting',
      title: 'シーズン打撃成績',
      description: '選手のシーズン全体の打撃指標',
      icon: BarChart3,
      color: 'bg-blue-500',
      examples: ['打率', 'ホームラン数', 'RBI', 'OPS']
    },
    {
      id: 'season_pitching', 
      title: 'シーズン投手成績',
      description: '投手のシーズン全体の投球指標',
      icon: Target,
      color: 'bg-green-500',
      examples: ['防御率', '奪三振数', 'WHIP', '勝利数']
    },
    {
      id: 'batting_splits',
      title: '場面別打撃成績 (TBU)',
      description: 'RISP、対左右投手など特定場面での成績',
      icon: Activity,
      color: 'bg-purple-500',
      examples: ['RISP', '対左投手', '満塁時', 'イニング別']
    },
    {
      id: 'monthly_trends',
      title: '月別推移',
      description: 'シーズン中の月ごとのパフォーマンス推移',
      icon: TrendingUp,
      color: 'bg-orange-500',
      examples: ['月別打率', '月別ホームラン', '月別防御率']
    },
    {
      id: 'pitching_splits',
      title: '場面別投手成績 (TBU)',
      description: 'イニング別、RISPなど特定場面での成績',
      icon: Activity,
      color: 'bg-purple-500',
      examples: ['RISP', '対左打者', '満塁時', 'イニング別']
    },
    // { [P1] TBU
    //   id: 'team_comparison',
    //   title: 'チーム比較',
    //   description: 'リーグ内でのチーム成績比較',
    //   icon: Users,
    //   color: 'bg-red-500',
    //   examples: ['チーム打率', 'チーム防御率', 'ホームラン数']
    // },
    {
      id: 'career_stats',
      title: '通算成績 (TBU)',
      description: '選手のキャリア全体の成績推移',
      icon: Calendar,
      color: 'bg-indigo-500',
      examples: ['年度別推移', '通算記録', 'キャリアハイ']
    },
    {
      id: 'batting_leaderboard',
      title: '打撃リーダーボード',
      description: 'MLB全体、リーグ別の打撃トップ選手',
      icon: BarChart3,
      color: 'bg-blue-500',
      examples: ['打率', 'ホームラン数', 'RBI', 'OPS']
    },
    {
      id: 'pitching_leaderboard',
      title: '投手リーダーボード',
      description: 'MLB全体、リーグ別の投手トップ選手',
      icon: BarChart3,
      color: 'bg-green-500',
      examples: ['防御率', '奪三振数', 'WHIP', '勝利数']
    },
    {
      id: 'pitching_advanced_analysis',
      title: '投手高度分析 (TBU)',
      description: '投手の詳細なパフォーマンス分析',
      icon: BarChart3,
      color: 'bg-green-500',
      examples: ['球種割合分析', '配球分析']
    }
  ];

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className={`text-xl font-semibold mb-2 transition-colors duration-200 ${
          isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'
        }`}>
          クエリカテゴリを選択
        </h3>
        <p className={`text-sm transition-colors duration-200 ${
          isActive ? 'text-gray-600 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
        }`}>
          分析したいデータの種類を選んでください
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {categories.map((category) => {
          const IconComponent = category.icon;
          const isSelected = selectedCategory?.id === category.id;
          
          return (
            <button
              key={category.id}
              onClick={() => onCategorySelect(category)}
              disabled={!isActive}
              className={`
                group relative p-6 rounded-xl border-2 text-left transition-all duration-200
                ${isSelected 
                  ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 shadow-lg transform scale-105' 
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 bg-white dark:bg-gray-800'
                }
                ${isActive 
                  ? 'hover:shadow-md hover:transform hover:scale-102 cursor-pointer' 
                  : 'opacity-60 cursor-not-allowed'
                }
              `}
            >
              {/* アイコンと色付きバッジ */}
              <div className="flex items-start space-x-4 mb-4">
                <div className={`
                  p-3 rounded-lg ${category.color} 
                  ${isSelected ? 'shadow-lg' : 'opacity-80'}
                  transition-all duration-200
                `}>
                  <IconComponent className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className={`
                    font-semibold text-lg mb-2 transition-colors duration-200
                    ${isSelected 
                      ? 'text-blue-900 dark:text-blue-100' 
                      : 'text-gray-900 dark:text-white'
                    }
                  `}>
                    {category.title}
                  </h4>
                  <p className={`
                    text-sm leading-relaxed transition-colors duration-200
                    ${isSelected 
                      ? 'text-blue-700 dark:text-blue-200' 
                      : 'text-gray-600 dark:text-gray-300'
                    }
                  `}>
                    {category.description}
                  </p>
                </div>
              </div>

              {/* 例のタグ */}
              <div className="flex flex-wrap gap-2">
                {category.examples.slice(0, 3).map((example, index) => (
                  <span
                    key={index}
                    className={`
                      px-2 py-1 text-xs rounded-full transition-colors duration-200
                      ${isSelected 
                        ? 'bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200' 
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                      }
                    `}
                  >
                    {example}
                  </span>
                ))}
                {category.examples.length > 3 && (
                  <span className={`
                    px-2 py-1 text-xs rounded-full transition-colors duration-200
                    ${isSelected 
                      ? 'bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200' 
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                    }
                  `}>
                    +{category.examples.length - 3}
                  </span>
                )}
              </div>

              {/* 選択インジケーター */}
              {isSelected && (
                <div className="absolute top-3 right-3">
                  <div className="w-6 h-6 bg-blue-500 dark:bg-blue-400 rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {selectedCategory && (
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center space-x-2 mb-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
              選択中: {selectedCategory.title}
            </span>
          </div>
          <p className="text-sm text-blue-700 dark:text-blue-200">
            {selectedCategory.description}
          </p>
        </div>
      )}
    </div>
  );
};

export default CategorySelector;