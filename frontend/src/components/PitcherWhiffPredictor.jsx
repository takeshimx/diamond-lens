import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Target, AlertCircle } from 'lucide-react';

const PitcherWhiffPredictor = () => {
  const [pitcherName, setPitcherName] = useState('Yamamoto, Yoshinobu');
  const [batterStand, setBatterStand] = useState('all');
  const [inning, setInning] = useState('all');
  const [orderThru, setOrderThru] = useState('all');
  const [runnerSituation, setRunnerSituation] = useState('all');
  const [batterLevel, setBatterLevel] = useState('all');
  const [countSituation, setCountSituation] = useState('all');
  const [pitchCountGroup, setPitchCountGroup] = useState('all');

  const [prediction, setPrediction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [availablePitchers, setAvailablePitchers] = useState([]);

  // Backend URL detection
  const getBackendUrl = () => {
    if (window.location.hostname.includes('run.app')) {
      return 'https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app';
    }
    const currentUrl = window.location.href;
    if (currentUrl.includes('app.github.dev')) {
      return currentUrl.replace('-5173.app.github.dev', '-8000.app.github.dev').split('?')[0];
    }
    return 'http://localhost:8000';
  };

  const BACKEND_URL = getBackendUrl();

  // Fetch available pitchers on mount
  useEffect(() => {
    const fetchPitchers = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/v1/pitcher-prediction/pitchers`);
        const data = await response.json();
        setAvailablePitchers(data);
      } catch (error) {
        console.error('Error fetching pitchers:', error);
      }
    };
    fetchPitchers();
  }, [BACKEND_URL]);

  const handlePredict = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/pitcher-prediction/predict-whiff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pitcher_name: pitcherName,
          batter_stand: batterStand === 'all' ? null : batterStand,
          inning: inning === 'all' ? null : parseInt(inning),
          order_thru: orderThru === 'all' ? null : parseInt(orderThru),
          runner_situation: runnerSituation === 'all' ? null : runnerSituation,
          batter_level: batterLevel === 'all' ? null : batterLevel,
          count_situation: countSituation === 'all' ? null : countSituation,
          pitch_count_group: pitchCountGroup === 'all' ? null : pitchCountGroup
        })
      });

      if (!response.ok) {
        throw new Error('Prediction failed');
      }

      const data = await response.json();
      setPrediction(data);
    } catch (error) {
      console.error('Error fetching prediction:', error);
      alert('予測の取得に失敗しました。投手名と状況を確認してください。');
    } finally {
      setIsLoading(false);
    }
  };

  // Chart data preparation
  const chartData = prediction?.predictions?.map(p => ({
    name: p.pitch_name,
    predicted: (p.predicted_whiff_rate * 100).toFixed(1),
    actual: p.actual_whiff_rate ? (p.actual_whiff_rate * 100).toFixed(1) : null
  })) || [];

  // Color mapping for bars
  const getBarColor = (value) => {
    if (value < 25) return '#10b981'; // Green - Easy to hit
    if (value < 40) return '#3b82f6'; // Blue - Moderate
    return '#ef4444'; // Red - Dangerous
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2 flex items-center justify-center gap-3">
          <Target className="w-8 h-8 text-blue-400" />
          Pitcher Whiff Rate Predictor
        </h2>
        <p className="text-gray-400">状況別に投手の空振り率を予測し、攻略ポイントを提示</p>
      </div>

      {/* Input Section */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
        <h3 className="text-xl font-semibold text-white mb-4">状況設定</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Pitcher Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">投手名</label>
            <input
              type="text"
              value={pitcherName}
              onChange={(e) => setPitcherName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="例: Yamamoto, Yoshinobu"
            />
          </div>

          {/* Batter Stand */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">打者の左右</label>
            <select
              value={batterStand}
              onChange={(e) => setBatterStand(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">指定なし</option>
              <option value="L">左打者</option>
              <option value="R">右打者</option>
            </select>
          </div>

          {/* Batter Level */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">打者レベル</label>
            <select
              value={batterLevel}
              onChange={(e) => setBatterLevel(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">指定なし</option>
              <option value="super elite">Super Elite (OPS ≥ 1.0)</option>
              <option value="elite">Elite (OPS 0.9-1.0)</option>
              <option value="great">Great (OPS 0.75-0.9)</option>
              <option value="average">Average (OPS 0.7-0.75)</option>
              <option value="below average">Below Average (OPS &lt; 0.7)</option>
            </select>
          </div>

          {/* Inning */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">イニング</label>
            <select
              value={inning}
              onChange={(e) => setInning(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">指定なし</option>
              {[1,2,3,4,5,6,7,8,9].map(i => (
                <option key={i} value={i}>{i}回</option>
              ))}
            </select>
          </div>

          {/* Order Thru */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">打順巡目</label>
            <select
              value={orderThru}
              onChange={(e) => setOrderThru(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">指定なし</option>
              <option value="1">1巡目</option>
              <option value="2">2巡目</option>
              <option value="3">3巡目</option>
            </select>
          </div>

          {/* Runner Situation */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">ランナー状況</label>
            <select
              value={runnerSituation}
              onChange={(e) => setRunnerSituation(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">指定なし</option>
              <option value="other">ランナーなし/1塁のみ</option>
              <option value="risp">得点圏</option>
              <option value="bases loaded">満塁</option>
            </select>
          </div>

          {/* Count Situation */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">カウント状況</label>
            <select
              value={countSituation}
              onChange={(e) => setCountSituation(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">指定なし</option>
              <option value="pitcher_advantage">投手有利 (0-2, 1-2, 2-2)</option>
              <option value="batter_advantage">打者有利 (2-0, 3-0, 3-1)</option>
              <option value="even">イーブン</option>
            </select>
          </div>

          {/* Pitch Count Group */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">球数</label>
            <select
              value={pitchCountGroup}
              onChange={(e) => setPitchCountGroup(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">指定なし</option>
              <option value="1-35">1-35球</option>
              <option value="36-69">36-69球</option>
              <option value="70-99">70-99球</option>
              <option value="100+">100球以上</option>
            </select>
          </div>
        </div>

        {/* Predict Button */}
        <button
          onClick={handlePredict}
          disabled={isLoading}
          className="mt-6 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
        >
          {isLoading ? '予測中...' : 'Whiff率を予測'}
        </button>
      </div>

      {/* Results Section */}
      {prediction && (
        <div className="space-y-6">
          {/* Chart */}
          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
            <h3 className="text-xl font-semibold text-white mb-4">球種別Whiff率予測</h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" label={{ value: 'Whiff率 (%)', angle: -90, position: 'insideLeft', fill: '#9ca3af' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#fff' }}
                  labelStyle={{ color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="predicted" name="予測値" radius={[8, 8, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getBarColor(parseFloat(entry.predicted))} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Recommendations */}
          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-400" />
              攻略ポイント
            </h3>
            <ul className="space-y-2">
              {prediction.recommendations.map((rec, index) => (
                <li key={index} className="text-gray-300 flex items-start gap-2">
                  <span className="text-blue-400 mt-1">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default PitcherWhiffPredictor;
