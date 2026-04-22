import React from 'react';
import { TrendingUp } from 'lucide-react';

// BigQueryから取得した統計データをカード形式で表示
const StatCard = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 transition-colors duration-200">
      {/* カードヘッダー */}
      <div className="flex items-center gap-2 mb-2">
        <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400 transition-colors duration-200" />
        <span className="text-sm font-semibold text-blue-800 dark:text-blue-300 transition-colors duration-200">統計データ</span>
      </div>
      {/* 統計データをキー・バリューペアで表示 */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        {Object.entries(stats).map(([key, value]) => (
          <div key={key} className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400 transition-colors duration-200">{key}:</span>
            <span className="font-semibold text-gray-900 dark:text-white transition-colors duration-200">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default StatCard;
