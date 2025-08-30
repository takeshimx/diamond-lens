import React from 'react';
import { Target, Activity, Settings } from 'lucide-react';

const SplitTypeSelector = ({ selectedSplitType, onSplitTypeSelect, isActive }) => {
  const splitTypes = [
    {
      id: 'risp',
      title: 'RISP (得点圏)',
      description: '得点圏に走者がいる場面での打撃成績',
      icon: Target,
      color: 'bg-blue-500',
      examples: ['RISP時打率', 'RISP時長打率', 'RISP時ホームラン']
    },
    {
      id: 'bases_loaded',
      title: '満塁',
      description: '満塁の場面での打撃成績',
      icon: Activity,
      color: 'bg-green-500',
      examples: ['満塁時打率', 'グランドスラム', '満塁時OPS']
    },
    {
      id: 'custom',
      title: 'カスタム',
      description: '複数の状況を組み合わせたカスタム分析',
      icon: Settings,
      color: 'bg-purple-500',
      examples: ['イニング別', 'カウント別', '投手タイプ別', '球種別']
    }
  ];

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className={`text-xl font-semibold mb-2 transition-colors duration-200 ${
          isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'
        }`}>
          場面を選択
        </h3>
        <p className={`text-sm transition-colors duration-200 ${
          isActive ? 'text-gray-600 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
        }`}>
          分析したい場面を選んでください
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {splitTypes.map((splitType) => {
          const IconComponent = splitType.icon;
          const isSelected = selectedSplitType?.id === splitType.id;
          
          return (
            <button
              key={splitType.id}
              onClick={() => onSplitTypeSelect(splitType)}
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
                  p-3 rounded-lg ${splitType.color} 
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
                    {splitType.title}
                  </h4>
                  <p className={`
                    text-sm leading-relaxed transition-colors duration-200
                    ${isSelected 
                      ? 'text-blue-700 dark:text-blue-200' 
                      : 'text-gray-600 dark:text-gray-300'
                    }
                  `}>
                    {splitType.description}
                  </p>
                </div>
              </div>

              {/* 例のタグ */}
              <div className="flex flex-wrap gap-2">
                {splitType.examples.map((example, index) => (
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

      {selectedSplitType && (
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center space-x-2 mb-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
              選択中: {selectedSplitType.title}
            </span>
          </div>
          <p className="text-sm text-blue-700 dark:text-blue-200">
            {selectedSplitType.description}
          </p>
        </div>
      )}
    </div>
  );
};

export default SplitTypeSelector;