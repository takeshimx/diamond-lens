import React, { useCallback } from 'react';
import { Target, Clock, User, MapPin, Zap, CheckCircle } from 'lucide-react';

const CustomSituationBuilder = ({ customSituation, onCustomSituationChange, isActive }) => {
  console.log('🎯 Render - Received customSituation:', customSituation);


  const updateSituation = useCallback((key, value) => {
    const updated = { ...customSituation, [key]: value };
    console.log('🔄 UpdateSituation:', { key, value, before: customSituation, after: updated });
    onCustomSituationChange(updated);
  }, [customSituation, onCustomSituationChange]);

  const toggleArrayValue = useCallback((key, value) => {
    const currentArray = customSituation?.[key] || [];
    const newArray = currentArray.includes(value)
      ? currentArray.filter(item => item !== value)
      : [...currentArray, value];
    console.log('🔢 ToggleArrayValue:', { key, value, currentArray, newArray });
    const updated = { ...customSituation, [key]: newArray };
    onCustomSituationChange(updated);
  }, [customSituation, onCustomSituationChange]);

  const innings = [1, 2, 3, 4, 5, 6, 7, 8, 9];
  const inningPresets = [
    { label: 'Early (1-3)', values: [1, 2, 3] },
    { label: 'Middle (4-6)', values: [4, 5, 6] },
    { label: 'Late (7-9)', values: [7, 8, 9] }
  ];

  const countPresets = [
    { label: '初球', strikes: 0, balls: 0 },
    { label: 'フルカウント', strikes: 2, balls: 3 },
    { label: '追い込み', strikes: 2, balls: null }
  ];

  const runnerSituations = [
    { id: 'empty', label: '無走者', bases: [] },
    { id: '1st', label: '一塁', bases: ['1st'] },
    { id: '2nd', label: '二塁', bases: ['2nd'] },
    { id: '3rd', label: '三塁', bases: ['3rd'] },
    { id: '1st_2nd', label: '一・二塁', bases: ['1st', '2nd'] },
    { id: '1st_3rd', label: '一・三塁', bases: ['1st', '3rd'] },
    { id: '2nd_3rd', label: '二・三塁', bases: ['2nd', '3rd'] },
    { id: 'loaded', label: '満塁', bases: ['1st', '2nd', '3rd'] }
  ];

  const pitchTypes = [
    { id: 'FF', label: '4-seam' },
    { id: 'SL', label: 'Slider' },
    { id: 'CH', label: 'Changeup' },
    { id: 'CU', label: 'Curve' },
    { id: 'FC', label: 'Cutter' },
    { id: 'SI', label: 'Sinker' }
  ];

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className={`text-xl font-semibold mb-2 transition-colors duration-200 ${
          isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'
        }`}>
          カスタム状況設定
        </h3>
        <p className={`text-sm transition-colors duration-200 ${
          isActive ? 'text-gray-600 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
        }`}>
          分析したい状況をカスタマイズしてください（複数選択可能）
        </p>
      </div>

      {/* Inning Selection */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h4 className="font-medium text-gray-900 dark:text-white">イニング</h4>
        </div>
        
        {/* Preset buttons */}
        <div className="flex flex-wrap gap-2 mb-3">
          {inningPresets.map((preset) => (
            <button
              key={preset.label}
              onClick={() => updateSituation('innings', preset.values)}
              disabled={!isActive}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              {preset.label}
            </button>
          ))}
          <button
            onClick={() => updateSituation('innings', [])}
            disabled={!isActive}
            className="px-3 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-full hover:bg-red-200 dark:hover:bg-red-800 disabled:opacity-50"
          >
            クリア
          </button>
        </div>

        {/* Individual inning selection */}
        <div className="grid grid-cols-9 gap-2">
          {innings.map((inning) => (
            <button
              key={inning}
              onClick={() => toggleArrayValue('innings', inning)}
              disabled={!isActive}
              className={`
                p-2 text-sm font-medium rounded-lg transition-all duration-200
                ${customSituation?.innings?.includes(inning)
                  ? 'bg-blue-500 text-white shadow-md border-2 border-blue-400 transform scale-105'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-transparent'
                }
                ${!isActive && 'opacity-50 cursor-not-allowed'}
              `}
            >
              {inning}
            </button>
          ))}
        </div>
      </div>

      {/* Count Selection */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <Target className="w-5 h-5 text-green-600 dark:text-green-400" />
          <h4 className="font-medium text-gray-900 dark:text-white">カウント</h4>
        </div>

        {/* Count presets */}
        <div className="flex flex-wrap gap-2 mb-4">
          {countPresets.map((preset) => (
            <button
              key={preset.label}
              onClick={() => {
                updateSituation('strikes', preset.strikes);
                updateSituation('balls', preset.balls);
              }}
              disabled={!isActive}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Strikes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              ストライク (0-2)
            </label>
            <div className="flex gap-2">
              {[0, 1, 2].map((count) => (
                <button
                  key={count}
                  onClick={() => updateSituation('strikes', count)}
                  disabled={!isActive}
                  className={`
                    px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200
                    ${customSituation.strikes === count
                      ? 'bg-green-500 text-white shadow-md border-2 border-green-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-transparent'
                    }
                    ${!isActive && 'opacity-50 cursor-not-allowed'}
                  `}
                >
                  {count}
                </button>
              ))}
              <button
                onClick={() => updateSituation('strikes', null)}
                disabled={!isActive}
                className="px-3 py-2 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-800 disabled:opacity-50"
              >
                クリア
              </button>
            </div>
          </div>

          {/* Balls */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              ボール (0-3)
            </label>
            <div className="flex gap-2">
              {[0, 1, 2, 3].map((count) => (
                <button
                  key={count}
                  onClick={() => updateSituation('balls', count)}
                  disabled={!isActive}
                  className={`
                    px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200
                    ${customSituation.balls === count
                      ? 'bg-green-500 text-white shadow-md border-2 border-green-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-transparent'
                    }
                    ${!isActive && 'opacity-50 cursor-not-allowed'}
                  `}
                >
                  {count}
                </button>
              ))}
              <button
                onClick={() => updateSituation('balls', null)}
                disabled={!isActive}
                className="px-3 py-2 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-800 disabled:opacity-50"
              >
                クリア
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Pitcher Type */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <User className="w-5 h-5 text-orange-600 dark:text-orange-400" />
          <h4 className="font-medium text-gray-900 dark:text-white">投手タイプ</h4>
        </div>
        
        <div className="flex gap-2">
          {['RHP', 'LHP'].map((type) => (
            <button
              key={type}
              onClick={() => updateSituation('pitcherType', type)}
              disabled={!isActive}
              className={`
                flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200
                ${customSituation?.pitcherType === type
                  ? 'bg-orange-500 text-white shadow-md border-2 border-orange-400'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-transparent'
                }
                ${!isActive && 'opacity-50 cursor-not-allowed'}
              `}
            >
              {type === 'RHP' ? '右投手' : '左投手'}
            </button>
          ))}
          <button
            onClick={() => updateSituation('pitcherType', null)}
            disabled={!isActive}
            className="px-3 py-2 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-800 disabled:opacity-50"
          >
            クリア
          </button>
        </div>
      </div>

      {/* Runners on Base */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <MapPin className="w-5 h-5 text-red-600 dark:text-red-400" />
          <h4 className="font-medium text-gray-900 dark:text-white">ランナー状況</h4>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {runnerSituations.map((situation) => (
            <button
              key={situation.id}
              onClick={() => toggleArrayValue('runnersOnBase', situation.id)}
              disabled={!isActive}
              className={`
                p-2 text-sm font-medium rounded-lg transition-all duration-200
                ${customSituation.runnersOnBase.includes(situation.id)
                  ? 'bg-red-500 text-white shadow-md border-2 border-red-400 transform scale-105'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-transparent'
                }
                ${!isActive && 'opacity-50 cursor-not-allowed'}
              `}
            >
              {situation.label}
            </button>
          ))}
        </div>
        
        <button
          onClick={() => updateSituation('runnersOnBase', [])}
          disabled={!isActive}
          className="mt-2 px-3 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-full hover:bg-red-200 dark:hover:bg-red-800 disabled:opacity-50"
        >
          すべてクリア
        </button>
      </div>

      {/* Pitch Type */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2 mb-3">
          <Zap className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          <h4 className="font-medium text-gray-900 dark:text-white">球種</h4>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {pitchTypes.map((pitch) => (
            <button
              key={pitch.id}
              onClick={() => toggleArrayValue('pitchTypes', pitch.id)}
              disabled={!isActive}
              className={`
                p-2 text-sm font-medium rounded-lg transition-all duration-200
                ${customSituation.pitchTypes.includes(pitch.id)
                  ? 'bg-purple-500 text-white shadow-md border-2 border-purple-400 transform scale-105'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-transparent'
                }
                ${!isActive && 'opacity-50 cursor-not-allowed'}
              `}
            >
              {pitch.label}
            </button>
          ))}
        </div>
        
        <button
          onClick={() => updateSituation('pitchTypes', [])}
          disabled={!isActive}
          className="mt-2 px-3 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-full hover:bg-red-200 dark:hover:bg-red-800 disabled:opacity-50"
        >
          すべてクリア
        </button>
      </div>

      {/* Summary */}
      {(customSituation.innings.length > 0 || customSituation.strikes !== null || customSituation.balls !== null || 
        customSituation.pitcherType || customSituation.runnersOnBase.length > 0 || customSituation.pitchTypes.length > 0) && (
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-4">
          <div className="flex items-center space-x-2 mb-2">
            <CheckCircle className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h5 className="font-medium text-blue-900 dark:text-blue-100">選択中の条件</h5>
          </div>
          
          <div className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
            {customSituation.innings.length > 0 && (
              <div>イニング: {customSituation.innings.join(', ')}回</div>
            )}
            {customSituation.strikes !== null && (
              <div>ストライク: {customSituation.strikes}</div>
            )}
            {customSituation.balls !== null && (
              <div>ボール: {customSituation.balls}</div>
            )}
            {customSituation.pitcherType && (
              <div>投手: {customSituation.pitcherType === 'RHP' ? '右投手' : '左投手'}</div>
            )}
            {customSituation.runnersOnBase.length > 0 && (
              <div>ランナー: {customSituation.runnersOnBase.map(id => 
                runnerSituations.find(s => s.id === id)?.label
              ).join(', ')}</div>
            )}
            {customSituation.pitchTypes.length > 0 && (
              <div>球種: {customSituation.pitchTypes.map(id => 
                pitchTypes.find(p => p.id === id)?.label
              ).join(', ')}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomSituationBuilder;