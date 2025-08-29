import React, { useState } from 'react';
import { Calendar, CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react';

const SeasonSelector = ({ seasonMode, specificYear, onSeasonChange, isActive }) => {
  const currentYear = new Date().getFullYear();
  const availableYears = Array.from({ length: 20 }, (_, i) => currentYear - i);
  
  const handleModeChange = (mode) => {
    onSeasonChange(mode, specificYear);
  };

  const handleYearChange = (year) => {
    onSeasonChange(seasonMode, year);
  };

  const handleYearIncrement = () => {
    const currentIndex = availableYears.indexOf(specificYear);
    if (currentIndex > 0) {
      handleYearChange(availableYears[currentIndex - 1]);
    }
  };

  const handleYearDecrement = () => {
    const currentIndex = availableYears.indexOf(specificYear);
    if (currentIndex < availableYears.length - 1) {
      handleYearChange(availableYears[currentIndex + 1]);
    }
  };

  const canIncrementYear = availableYears.indexOf(specificYear) > 0;
  const canDecrementYear = availableYears.indexOf(specificYear) < availableYears.length - 1;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className={`text-xl font-semibold mb-2 transition-colors duration-200 ${
          isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'
        }`}>
          シーズンを選択
        </h3>
        <p className={`text-sm transition-colors duration-200 ${
          isActive ? 'text-gray-600 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
        }`}>
          分析する期間を選択してください
        </p>
      </div>

      {/* Season Mode Toggle */}
      <div className="max-w-md mx-auto">
        <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
          <button
            onClick={() => handleModeChange('all')}
            disabled={!isActive}
            className={`
              flex-1 flex items-center justify-center space-x-2 px-4 py-3 rounded-md text-sm font-medium transition-all duration-200
              ${seasonMode === 'all'
                ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 shadow-sm'
                : isActive
                ? 'text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100'
                : 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
              }
            `}
          >
            <CalendarDays className="w-4 h-4" />
            <span>全シーズン</span>
          </button>
          <button
            onClick={() => handleModeChange('specific')}
            disabled={!isActive}
            className={`
              flex-1 flex items-center justify-center space-x-2 px-4 py-3 rounded-md text-sm font-medium transition-all duration-200
              ${seasonMode === 'specific'
                ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 shadow-sm'
                : isActive
                ? 'text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100'
                : 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
              }
            `}
          >
            <Calendar className="w-4 h-4" />
            <span>特定シーズン</span>
          </button>
        </div>
      </div>

      {/* Specific Year Selector */}
      {seasonMode === 'specific' && (
        <div className="max-w-sm mx-auto space-y-4">
          {/* Year Input with Controls */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <button
                onClick={handleYearDecrement}
                disabled={!isActive || !canDecrementYear}
                className={`
                  p-3 border-r border-gray-200 dark:border-gray-700 rounded-l-lg transition-colors duration-200
                  ${isActive && canDecrementYear
                    ? 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                  }
                `}
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              
              <div className="flex-1 text-center py-3">
                <span className={`text-2xl font-bold transition-colors duration-200 ${
                  isActive ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-500'
                }`}>
                  {specificYear}
                </span>
              </div>
              
              <button
                onClick={handleYearIncrement}
                disabled={!isActive || !canIncrementYear}
                className={`
                  p-3 border-l border-gray-200 dark:border-gray-700 rounded-r-lg transition-colors duration-200
                  ${isActive && canIncrementYear
                    ? 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                  }
                `}
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Year Dropdown */}
          <div>
            <label className={`block text-sm font-medium mb-2 transition-colors duration-200 ${
              isActive ? 'text-gray-700 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
            }`}>
              年度選択
            </label>
            <select
              value={specificYear}
              onChange={(e) => handleYearChange(parseInt(e.target.value))}
              disabled={!isActive}
              className={`
                w-full px-3 py-2 border rounded-lg text-base transition-all duration-200
                ${isActive 
                  ? 'border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent' 
                  : 'border-gray-200 dark:border-gray-700 opacity-60 cursor-not-allowed'
                }
                bg-white dark:bg-gray-800 text-gray-900 dark:text-white
              `}
            >
              {availableYears.map(year => (
                <option key={year} value={year}>
                  {year}年シーズン
                </option>
              ))}
            </select>
          </div>

          {/* Quick Year Selection */}
          <div>
            <label className={`block text-sm font-medium mb-2 transition-colors duration-200 ${
              isActive ? 'text-gray-700 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
            }`}>
              クイック選択
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[currentYear, currentYear - 1, currentYear - 2, currentYear - 3, currentYear - 4].map(year => (
                <button
                  key={year}
                  onClick={() => handleYearChange(year)}
                  disabled={!isActive}
                  className={`
                    px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200
                    ${specificYear === year
                      ? 'bg-blue-600 dark:bg-blue-500 text-white shadow-lg'
                      : isActive
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      : 'bg-gray-50 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
                    }
                  `}
                >
                  {year}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Selection Summary */}
      <div className="max-w-md mx-auto p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <div className="flex items-center space-x-2 mb-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
          <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
            選択中の期間
          </span>
        </div>
        
        <div className="text-blue-700 dark:text-blue-200">
          {seasonMode === 'all' ? (
            <div>
              <p className="font-semibold">全シーズン</p>
              <p className="text-sm mt-1">
                利用可能なすべてのシーズンデータを対象とします
              </p>
            </div>
          ) : (
            <div>
              <p className="font-semibold">{specificYear}年シーズン</p>
              <p className="text-sm mt-1">
                {specificYear}年の{specificYear === currentYear ? '現在進行中の' : ''}シーズンデータを対象とします
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Season Info */}
      {seasonMode === 'specific' && (
        <div className="max-w-md mx-auto">
          <div className={`text-xs text-center space-y-1 transition-colors duration-200 ${
            isActive ? 'text-gray-500 dark:text-gray-400' : 'text-gray-400 dark:text-gray-600'
          }`}>
            <p>MLBシーズン: 3月末〜10月（レギュラーシーズン）</p>
            {specificYear === currentYear && (
              <p className="text-orange-600 dark:text-orange-400">
                * {currentYear}年は進行中のシーズンです
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SeasonSelector;