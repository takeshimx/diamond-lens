import React from 'react';
import { Clock, Target, User, MapPin, Zap, CheckCircle } from 'lucide-react';

const CustomSituationBuilder = ({ customSituation = {}, onCustomSituationChange, isActive }) => {
  
  const handleUpdate = (field, value) => {
    const newSituation = { ...customSituation, [field]: value };
    onCustomSituationChange(newSituation);
  };

  const handleToggle = (field, value) => {
    const current = customSituation[field] || [];
    
    // Special handling for runners
    if (field === 'runnersOnBase') {
      if (value === 'empty') {
        // Empty is exclusive - clear all others
        handleUpdate(field, ['empty']);
        return;
      } else if (value === 'loaded' || value === 'risp') {
        // loaded/risp are exclusive - clear all others
        handleUpdate(field, [value]);
        return;
      } else {
        // For base runners (1st, 2nd, 3rd), remove empty/loaded/risp first
        const baseRunners = current.filter(v => ['1st', '2nd', '3rd'].includes(v));
        const updated = baseRunners.includes(value)
          ? baseRunners.filter(v => v !== value)
          : [...baseRunners, value];
        handleUpdate(field, updated);
        return;
      }
    }
    
    // Normal toggle for other fields
    const updated = current.includes(value) 
      ? current.filter(v => v !== value)
      : [...current, value];
    handleUpdate(field, updated);
  };

  return (
    <div className="space-y-4">
      {/* Selected Conditions Summary - Moved to top */}
      {customSituation && Object.keys(customSituation).some(key => 
        (Array.isArray(customSituation[key]) && customSituation[key].length > 0) || 
        (customSituation[key] !== null && customSituation[key] !== undefined)
      ) && (
        <div className="bg-emerald-800 rounded-lg p-4 border-2 border-emerald-600">
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircle className="w-5 h-5 text-white" />
            <h5 className="font-bold text-white text-lg">現在の選択</h5>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {customSituation.innings?.length > 0 && (
              <div className="bg-emerald-700 rounded-lg p-3 border border-emerald-500">
                <div className="text-emerald-200 text-xs font-medium mb-1">イニング</div>
                <div className="text-white font-bold">{customSituation.innings.join(', ')}回</div>
              </div>
            )}
            {((customSituation.strikes !== null && customSituation.strikes !== undefined) || 
              (customSituation.balls !== null && customSituation.balls !== undefined)) && (
              <div className="bg-emerald-700 rounded-lg p-3 border border-emerald-500">
                <div className="text-emerald-200 text-xs font-medium mb-1">カウント</div>
                <div className="text-white font-bold">
                  {customSituation.balls !== null && customSituation.balls !== undefined ? customSituation.balls : '-'}-
                  {customSituation.strikes !== null && customSituation.strikes !== undefined ? customSituation.strikes : '-'}
                </div>
              </div>
            )}
            {customSituation.pitcherType && (
              <div className="bg-emerald-700 rounded-lg p-3 border border-emerald-500">
                <div className="text-emerald-200 text-xs font-medium mb-1">投手タイプ</div>
                <div className="text-white font-bold">{customSituation.pitcherType === 'R' ? '右投手' : '左投手'}</div>
              </div>
            )}
            {customSituation.runnersOnBase?.length > 0 && (
              <div className="bg-emerald-700 rounded-lg p-3 border border-emerald-500">
                <div className="text-emerald-200 text-xs font-medium mb-1">ランナー状況</div>
                <div className="text-white font-bold">{customSituation.runnersOnBase.join(', ')}</div>
              </div>
            )}
            {customSituation.pitchTypes?.length > 0 && (
              <div className="bg-emerald-700 rounded-lg p-3 border border-emerald-500">
                <div className="text-emerald-200 text-xs font-medium mb-1">球種</div>
                <div className="text-white font-bold">{customSituation.pitchTypes.join(', ')}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Inning Section */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center space-x-2 mb-3">
          <Clock className="w-4 h-4 text-blue-400" />
          <h4 className="text-white font-medium text-sm">イニング</h4>
        </div>

        {/* Inning presets */}
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => handleUpdate('innings', [1, 2, 3])}
            className="px-3 py-1 bg-gray-700 text-gray-200 rounded text-xs hover:bg-emerald-700"
          >
            序盤(1-3回)
          </button>
          <button
            onClick={() => handleUpdate('innings', [4, 5, 6])}
            className="px-3 py-1 bg-gray-700 text-gray-200 rounded text-xs hover:bg-emerald-700"
          >
            中盤(4-6回)
          </button>
          <button
            onClick={() => handleUpdate('innings', [7, 8, 9])}
            className="px-3 py-1 bg-gray-700 text-gray-200 rounded text-xs hover:bg-emerald-700"
          >
            終盤(7-9回)
          </button>
        </div>
        
        <div className="grid grid-cols-9 gap-1">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(inning => (
            <button
              key={inning}
              onClick={() => handleToggle('innings', inning)}
              className={`px-2 py-2 text-sm rounded ${
                (customSituation?.innings || []).includes(inning)
                  ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                  : 'bg-gray-700 text-gray-300 hover:bg-emerald-700'
              }`}
            >
              {inning}
            </button>
          ))}
        </div>
        
        <button
          onClick={() => handleUpdate('innings', [])}
          className="mt-2 px-2 py-1 text-xs bg-red-700 text-red-200 rounded hover:bg-red-600"
        >
          すべてクリア
        </button>
      </div>

      {/* Count Section */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center space-x-2 mb-3">
          <Target className="w-4 h-4 text-green-400" />
          <h4 className="text-white font-medium text-sm">カウント</h4>
        </div>
        
        {/* Count presets */}
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => { handleUpdate('strikes', 0); handleUpdate('balls', 0); }}
            className="px-3 py-1 bg-gray-700 text-gray-200 rounded text-xs hover:bg-emerald-700"
          >
            初球
          </button>
          <button
            onClick={() => { 
              const newSituation = { ...customSituation, strikes: 2, balls: 3 };
              onCustomSituationChange(newSituation);
            }}
            className="px-3 py-1 bg-gray-700 text-gray-200 rounded text-xs hover:bg-emerald-700"
          >
            フルカウント
          </button>
          <button
            onClick={() => { handleUpdate('strikes', 2); handleUpdate('balls', null); }}
            className="px-3 py-1 bg-gray-700 text-gray-200 rounded text-xs hover:bg-emerald-700"
          >
            追い込み
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Strikes */}
          <div>
            <div className="text-xs text-gray-400 mb-2">ストライク (0-2)</div>
            <div className="flex gap-1">
              {[0, 1, 2].map(num => (
                <button
                  key={num}
                  onClick={() => handleUpdate('strikes', num)}
                  className={`px-3 py-2 text-sm rounded ${
                    customSituation?.strikes === num
                      ? 'bg-blue-500 text-blue-300 border-2 border-blue-300' 
                      : 'bg-gray-700 text-gray-300 hover:bg-emerald-700'
                  }`}
                >
                  {num}
                </button>
              ))}
              <button
                onClick={() => handleUpdate('strikes', null)}
                className="px-2 py-2 text-xs bg-red-700 text-red-200 rounded hover:bg-red-600"
              >
                クリア
              </button>
            </div>
          </div>

          {/* Balls */}
          <div>
            <div className="text-xs text-gray-400 mb-2">ボール (0-3)</div>
            <div className="flex gap-1">
              {[0, 1, 2, 3].map(num => (
                <button
                  key={num}
                  onClick={() => handleUpdate('balls', num)}
                  className={`px-3 py-2 text-sm rounded ${
                    customSituation?.balls === num
                      ? 'bg-blue-500 text-blue-300 border-2 border-blue-300' 
                      : 'bg-gray-700 text-gray-300 hover:bg-emerald-700'
                  }`}
                >
                  {num}
                </button>
              ))}
              <button
                onClick={() => handleUpdate('balls', null)}
                className="px-2 py-2 text-xs bg-red-700 text-red-200 rounded hover:bg-red-600"
              >
                クリア
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Pitcher Type Section */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center space-x-2 mb-3">
          <User className="w-4 h-4 text-orange-400" />
          <h4 className="text-white font-medium text-sm">投手タイプ</h4>
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => handleUpdate('pitcherType', 'R')}
            className={`px-4 py-3 text-sm rounded-lg ${
              customSituation?.pitcherType === 'R'
                ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            右投手
          </button>
          <button
            onClick={() => handleUpdate('pitcherType', 'L')}
            className={`px-4 py-3 text-sm rounded-lg ${
              customSituation?.pitcherType === 'L'
                ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            左投手
          </button>
        </div>
        <button
          onClick={() => handleUpdate('pitcherType', null)}
          className="mt-2 px-2 py-1 text-xs bg-red-700 text-red-200 rounded hover:bg-red-600"
        >
          クリア
        </button>
      </div>

      {/* Runners Section */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center space-x-2 mb-3">
          <MapPin className="w-4 h-4 text-red-400" />
          <h4 className="text-white font-medium text-sm">ランナー状況</h4>
        </div>
        
        <div className="grid grid-cols-3 gap-2 mb-2">
          {['ランナー無し', '1塁', '2塁'].map((label, idx) => {
            const ids = ['empty', '1b', '2b'];
            return (
              <button
                key={ids[idx]}
                onClick={() => handleToggle('runnersOnBase', ids[idx])}
                className={`px-3 py-2 text-sm rounded ${
                  (customSituation?.runnersOnBase || []).includes(ids[idx])
                    ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
        
        <div className="grid grid-cols-3 gap-2">
          {['3塁', '満塁', 'RISP'].map((label, idx) => {
            const ids = ['3b', 'bases_loaded', 'risp'];
            return (
              <button
                key={ids[idx]}
                onClick={() => handleToggle('runnersOnBase', ids[idx])}
                className={`px-3 py-2 text-sm rounded ${
                  (customSituation?.runnersOnBase || []).includes(ids[idx])
                    ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
        
        <button
          onClick={() => handleUpdate('runnersOnBase', [])}
          className="mt-2 px-2 py-1 text-xs bg-red-700 text-red-200 rounded hover:bg-red-600"
        >
          すべてクリア
        </button>
      </div>

      {/* Pitch Type Section */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center space-x-2 mb-3">
          <Zap className="w-4 h-4 text-purple-400" />
          <h4 className="text-white font-medium text-sm">球種</h4>
        </div>
        
        <div className="grid grid-cols-3 gap-1 mb-2">
          {[
            { id: 'FF', label: '4-Seam Fastball' },
            { id: 'CU', label: 'Curveball' },
            { id: 'SL', label: 'Slider' },
            { id: 'FS', label: 'Split-Finger' },
            { id: 'SI', label: 'Sinker' },
            { id: 'ST', label: 'Sweeper' }
          ].map(pitch => (
            <button
              key={pitch.id}
              onClick={() => handleToggle('pitchTypes', pitch.id)}
              className={`px-2 py-2 text-xs rounded ${
                (customSituation?.pitchTypes || []).includes(pitch.id)
                  ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {pitch.label}
            </button>
          ))}
        </div>
        
        <div className="grid grid-cols-3 gap-1 mb-2">
          {[
            { id: 'CH', label: 'Changeup' },
            { id: 'FC', label: 'Cutter' },
            { id: 'KN', label: 'Knuckleball' },
            { id: 'FO', label: 'Forkball' },
            { id: 'SV', label: 'Slurve' },
            { id: 'CS', label: 'Slow Curve' }
          ].map(pitch => (
            <button
              key={pitch.id}
              onClick={() => handleToggle('pitchTypes', pitch.id)}
              className={`px-2 py-2 text-xs rounded ${
                (customSituation?.pitchTypes || []).includes(pitch.id)
                  ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {pitch.label}
            </button>
          ))}
        </div>
        
        <div className="grid grid-cols-3 gap-1">
          {[
            { id: 'KC', label: 'Knuckle Curve' },
            { id: 'EP', label: 'Eephus' },
            { id: 'SC', label: 'Screwball' },
            { id: 'PO', label: 'Pitch Out' },
            { id: '', label: '' }
          ].filter(pitch => pitch.id).map(pitch => (
            <button
              key={pitch.id}
              onClick={() => handleToggle('pitchTypes', pitch.id)}
              className={`px-2 py-2 text-xs rounded ${
                (customSituation?.pitchTypes || []).includes(pitch.id)
                  ? 'bg-blue-500 text-blue-300 border-2 border-blue-300'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {pitch.label}
            </button>
          ))}
        </div>
        
        <button
          onClick={() => handleUpdate('pitchTypes', [])}
          className="mt-2 px-2 py-1 text-xs bg-red-700 text-red-200 rounded hover:bg-red-600"
        >
          すべてクリア
        </button>
      </div>

    </div>
  );
};

export default CustomSituationBuilder;