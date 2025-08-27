import React from 'react';
import { TrendingUp, BarChart3 } from 'lucide-react';
import SimpleChatChart from './ChatChart.jsx';

const QuickQuestions = ({ onQuestionClick, isLoading, quickResult, onClearResult }) => {
  // Predefined questions with their corresponding API parameters
  const quickQuestions = [
    {
      id: 'ohtani-monthly-ba-2024',
      title: '大谷さんの2024年の打率を月毎の推移をチャートで教えて',
      description: '大谷翔平選手の2024年シーズンの月別打率推移',
      icon: TrendingUp,
      params: {
        playerId: 660271, // Ohtani's player ID (needs to be confirmed from backend)
        season: 2024,
        metric: 'batting_average',
        queryType: 'monthly_offensive_stats'
      }
    },
    // Add more predefined questions as needed
    {
      id: 'ohtani-monthly-risp-ba-2025',
      title: '大谷さんの2025年のRISPでの打率を月毎の推移を教えて',
      description: '大谷翔平選手の2025年シーズンのRISPでの月別打率推移',
      icon: TrendingUp,
      params: {
        playerId: 660271,
        season: 2025,
        metric: 'batting_average_at_risp',
        queryType: 'monthly_risp_stats'
      }
    },
    // another predefined question and expected respones with bar chart
    {
      id: 'ohtani-monthly-hr-2024',
      title: '大谷さんの2024年のホームランを月毎の推移',
      description: '大谷翔平選手の2024年シーズンの月別ホームラン推移',
      icon: TrendingUp,
      params: {
        playerId: 660271,
        season: 2024,
        metric: 'home_runs',
        queryType: 'monthly_offensive_stats'
      }
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 transition-colors duration-200">
          クイック質問
        </h2>
        <p className="text-gray-600 dark:text-gray-300 transition-colors duration-200">
          よく使われる質問をワンクリックで実行できます
        </p>
      </div>

      {/* Quick Questions Grid */}
      <div className="grid gap-4 max-w-4xl mx-auto">
        {quickQuestions.map((question) => {
          const IconComponent = question.icon;
          
          return (
            <div
              key={question.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-200 cursor-pointer"
              onClick={() => !isLoading && onQuestionClick(question)}
            >
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex-shrink-0">
                  <IconComponent className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 transition-colors duration-200">
                    {question.title}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">
                    {question.description}
                  </p>
                  
                  {/* Question Details */}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                      {question.params.season}年
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
                      月別推移
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300">
                      チャート表示
                    </span>
                  </div>
                </div>

                {/* Action Icon */}
                <div className="flex-shrink-0">
                  <BarChart3 className="w-5 h-5 text-gray-400 dark:text-gray-500" />
                </div>
              </div>
              
              {/* Loading State Overlay */}
              {isLoading && (
                <div className="absolute inset-0 bg-white dark:bg-gray-800 bg-opacity-50 flex items-center justify-center rounded-lg">
                  <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                    <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    処理中...
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Quick Question Result Display */}
      {quickResult && (
        <div className="max-w-4xl mx-auto mt-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 transition-colors duration-200">
            {/* Result Header */}
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                クエリ結果
              </h3>
            </div>
            
            {/* Result Content */}
            <div className="mb-4">
              <p className="text-gray-700 dark:text-gray-300 mb-4">
                {quickResult.answer}
              </p>
              
              {/* Chart Display */}
              {quickResult.isChart && quickResult.chartData && quickResult.chartConfig && (
                <SimpleChatChart 
                  chartData={quickResult.chartData}
                  chartConfig={quickResult.chartConfig}
                  chartType={quickResult.chartType}
                />
              )}
              
              {/* Table Display (if needed) */}
              {quickResult.isTable && quickResult.tableData && quickResult.columns && (
                <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                  表形式のデータも利用可能
                </div>
              )}
            </div>
            
            {/* Clear Result Button */}
            <div className="text-right">
              <button
                onClick={() => onClearResult && onClearResult()}
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors duration-200"
              >
                結果をクリア
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help Text */}
      <div className="text-center text-sm text-gray-500 dark:text-gray-400 transition-colors duration-200 mt-6">
        その他の質問は「チャット」モードをご利用ください
      </div>
    </div>
  );
};

export default QuickQuestions;