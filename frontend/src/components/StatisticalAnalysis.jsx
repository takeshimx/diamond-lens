import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, Activity } from 'lucide-react';

const StatisticalAnalysis = () => {
  const [opsValue, setOpsValue] = useState(0.750);
  const [eraValue, setEraValue] = useState(4.00);
  const [hrsAllowedValue, setHrsAllowedValue] = useState(180);
  const [prediction, setPrediction] = useState(null);
  const [sensitivityData, setSensitivityData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Backend URL detection (same logic as App.jsx)
  const getBackendUrl = () => {
    const currentUrl = window.location.href;
    if (currentUrl.includes('app.github.dev')) {
      return currentUrl.replace('-5173.app.github.dev', '-8000.app.github.dev').split('?')[0];
    }
    return 'http://localhost:8000';
  };

  const BACKEND_URL = getBackendUrl();

  const handlePredict = async () => {
    setIsLoading(true);
    try {
      // Prediction API call
      const predictionResponse = await fetch(
        `${BACKEND_URL}/api/v1/statistics/predict-winrate?team_ops=${opsValue}&team_era=${eraValue}&team_hrs_allowed=${hrsAllowedValue}`
      );
      const predictionData = await predictionResponse.json();
      setPrediction(predictionData);

      // Sensitivity analysis API call
      const sensitivityResponse = await fetch(
        `${BACKEND_URL}/api/v1/statistics/ops-sensitivity?fixed_era=${eraValue}&fixed_hrs_allowed=${hrsAllowedValue}`
      );
      const sensitivityResult = await sensitivityResponse.json();
      setSensitivityData(sensitivityResult.data);
    } catch (error) {
      console.error('Error fetching prediction:', error);
      alert('予測の取得に失敗しました。');
    } finally {
      setIsLoading(false);
    }
  };

  const getPerformanceTier = (winRate) => {
    if (winRate >= 0.6) return { label: 'Postseason favorite', color: 'text-green-400' };
    if (winRate >= 0.55) return { label: 'Postseason contender', color: 'text-blue-400' };
    if (winRate >= 0.5) return { label: 'Playoff hopeful', color: 'text-yellow-400' };
    return { label: 'Non-contender', color: 'text-gray-400' };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2 flex items-center justify-center gap-3">
          <Activity className="w-8 h-8 text-blue-400" />
          Statistical Analysis Dashboard
        </h2>
        <p className="text-gray-400">Predict team win rate using OPS, ERA, and HRs Allowed</p>
      </div>

      {/* Input Section */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
        <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-400" />
          Input Parameters
        </h3>

        <div className="space-y-6">
          {/* OPS Slider */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Team OPS: <span className="text-blue-400 font-bold">{opsValue.toFixed(3)}</span>
            </label>
            <input
              type="range"
              min="0.500"
              max="1.000"
              step="0.001"
              value={opsValue}
              onChange={(e) => setOpsValue(parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-thumb"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0.500</span>
              <span>1.000</span>
            </div>
          </div>

          {/* ERA Slider */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Team ERA: <span className="text-blue-400 font-bold">{eraValue.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="2.00"
              max="6.00"
              step="0.01"
              value={eraValue}
              onChange={(e) => setEraValue(parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-thumb"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>2.00</span>
              <span>6.00</span>
            </div>
          </div>

          {/* HRs Allowed Slider */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              HRs Allowed: <span className="text-blue-400 font-bold">{hrsAllowedValue}</span>
            </label>
            <input
              type="range"
              min="100"
              max="250"
              step="1"
              value={hrsAllowedValue}
              onChange={(e) => setHrsAllowedValue(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-thumb"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>100</span>
              <span>250</span>
            </div>
          </div>

          {/* Predict Button */}
          <button
            onClick={handlePredict}
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Predicting...' : 'Predict Win Rate'}
          </button>
        </div>
      </div>

      {/* Prediction Result */}
      {prediction && (
        <div className="bg-gradient-to-br from-blue-900/50 to-purple-900/50 rounded-lg p-8 shadow-lg border border-blue-700">
          <h3 className="text-2xl font-bold text-white mb-6 text-center">Prediction Result</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* Win Rate */}
            <div className="text-center">
              <p className="text-gray-400 text-sm mb-2">Predicted Win Rate</p>
              <p className="text-5xl font-bold text-blue-400">
                {(prediction.predicted_win_rate * 100).toFixed(1)}%
              </p>
            </div>

            {/* Expected Wins */}
            <div className="text-center">
              <p className="text-gray-400 text-sm mb-2">Expected Wins (162 games)</p>
              <p className="text-5xl font-bold text-green-400">
                {prediction.expected_wins_per_season}
              </p>
            </div>

            {/* Performance Tier */}
            <div className="text-center">
              <p className="text-gray-400 text-sm mb-2">Performance Tier</p>
              <p className={`text-2xl font-bold ${getPerformanceTier(prediction.predicted_win_rate).color}`}>
                {getPerformanceTier(prediction.predicted_win_rate).label}
              </p>
            </div>
          </div>

          {/* Model Metrics */}
          <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400 mb-2">Model Evaluation Metrics</p>
            <div className="flex justify-around text-sm">
              <div>
                <span className="text-gray-400">R² Score: </span>
                <span className="text-white font-semibold">{prediction.model_metrics.r2_score}</span>
              </div>
              <div>
                <span className="text-gray-400">MSE: </span>
                <span className="text-white font-semibold">{prediction.model_metrics.mse}</span>
              </div>
              <div>
                <span className="text-gray-400">MAE: </span>
                <span className="text-white font-semibold">{prediction.model_metrics.mae}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* OPS Sensitivity Chart */}
      {sensitivityData && (
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
          <h3 className="text-xl font-semibold text-white mb-4">
            OPS Sensitivity Analysis (ERA: {eraValue.toFixed(2)}, HRs: {hrsAllowedValue})
          </h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={sensitivityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="ops"
                stroke="#9CA3AF"
                label={{ value: 'OPS', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }}
              />
              <YAxis
                stroke="#9CA3AF"
                label={{ value: 'Win Rate', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                domain={[0.3, 0.7]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
                labelStyle={{ color: '#9CA3AF' }}
                itemStyle={{ color: '#60A5FA' }}
              />
              <Line
                type="monotone"
                dataKey="win_rate"
                stroke="#60A5FA"
                strokeWidth={3}
                dot={{ fill: '#60A5FA', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default StatisticalAnalysis;
