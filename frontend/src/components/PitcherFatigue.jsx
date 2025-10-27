import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingDown, Activity, AlertTriangle } from 'lucide-react';

const PitcherFatigue = () => {
  const [pitcherName, setPitcherName] = useState('');
  const [season, setSeason] = useState(2025);
  const [data, setData] = useState(null);
  const [leagueAverage, setLeagueAverage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Backend URL detection
  const getBackendUrl = () => {
    if (window.location.hostname.includes('github.dev') || window.location.hostname.includes('codespaces')) {
      const frontendUrl = window.location.origin;
      const backendUrl = frontendUrl.replace('5173', '8000');
      return backendUrl;
    }
    return 'http://localhost:8000';
  };

  const backendUrl = getBackendUrl();

  // Fetch league average on mount
  useEffect(() => {
    fetchLeagueAverage();
  }, [season]);

  const fetchLeagueAverage = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/v1/pitcher-fatigue/league-average?season=${season}`);
      const result = await response.json();
      if (!result.error) {
        setLeagueAverage(result.inning_stats);
      }
    } catch (err) {
      console.error('Failed to fetch league average:', err);
    }
  };

  const handleSearch = async () => {
    if (!pitcherName.trim()) {
      setError('Please enter a pitcher name');
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await fetch(
        `${backendUrl}/api/v1/pitcher-fatigue?pitcher_name=${encodeURIComponent(pitcherName)}&season=${season}`
      );
      const result = await response.json();

      if (result.error) {
        setError(result.message);
        if (result.suggestions && result.suggestions.length > 0) {
          setError(`${result.message}\n\nSuggestions: ${result.suggestions.join(', ')}`);
        }
      } else {
        setData(result);
      }
    } catch (err) {
      setError('Failed to fetch data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getFatigueColor = (risk) => {
    if (risk === 'high') return 'text-red-600 bg-red-100';
    if (risk === 'moderate') return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-800 to-gray-900">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
            <Activity className="w-10 h-10 text-blue-400" />
            Pitcher Fatigue Analysis
          </h1>
          <p className="text-gray-300">
            Analyze pitcher performance deterioration by inning to optimize substitution timing
          </p>
        </div>

        {/* Search Section */}
        <div className="bg-gray-700 rounded-xl shadow-md p-6 mb-8">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-200 mb-2">
                Pitcher Name
              </label>
              <input
                type="text"
                value={pitcherName}
                onChange={(e) => setPitcherName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="e.g., Justin Verlander"
                className="w-full px-4 py-2 bg-gray-600 border border-gray-500 text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="w-32">
              <label className="block text-sm font-medium text-gray-200 mb-2">
                Season
              </label>
              <select
                value={season}
                onChange={(e) => setSeason(Number(e.target.value))}
                className="w-full px-4 py-2 bg-gray-600 border border-gray-500 text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {[2025, 2024, 2023, 2022, 2021].map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Loading...' : 'Analyze'}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 whitespace-pre-line">
              {error}
            </div>
          )}
        </div>

        {/* Results */}
        {data && (
          <div className="space-y-8">
            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Fastball Speed Chart */}
              <div className="bg-gray-700 rounded-xl shadow-md p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-blue-400" />
                  Fastball Speed (mph)
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={data.innings}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="inning" label={{ value: 'Inning', position: 'insideBottom', offset: -5 }} />
                    <YAxis
                      label={{ value: 'Speed (mph)', angle: -90, position: 'insideLeft' }}
                      domain={['dataMin - 2', 'dataMax + 1']}
                    />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="fastball_speed" stroke="#3b82f6" strokeWidth={2} name="Fastball Speed" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* OPS Against Chart */}
              <div className="bg-gray-700 rounded-xl shadow-md p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-orange-400" />
                  OPS Against
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={data.innings}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="inning" label={{ value: 'Inning', position: 'insideBottom', offset: -5 }} />
                    <YAxis label={{ value: 'OPS', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="ops_against" stroke="#f97316" strokeWidth={2} name="OPS Against" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Inning-by-Inning Table */}
            <div className="bg-gray-700 rounded-xl shadow-md p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                Inning-by-Inning Breakdown
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-600 border-b-2 border-gray-500">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200">Inning</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200">Fastball Speed</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200">Speed Drop</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200">Cumulative Pitches</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200">OPS Against</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200">Strike Rate</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200">Fatigue Risk</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-600">
                    {data.innings.map((inning) => (
                      <tr key={inning.inning} className="hover:bg-gray-600">
                        <td className="px-4 py-3 text-sm text-gray-200">{inning.inning}</td>
                        <td className="px-4 py-3 text-sm text-gray-200">{inning.fastball_speed?.toFixed(1)} mph</td>
                        <td className="px-4 py-3 text-sm text-gray-200">{inning.speed_drop?.toFixed(2)}</td>
                        <td className="px-4 py-3 text-sm text-gray-200">{inning.cumulative_pitches}</td>
                        <td className="px-4 py-3 text-sm text-gray-200">{inning.ops_against?.toFixed(3)}</td>
                        <td className="px-4 py-3 text-sm text-gray-200">{(inning.strike_rate * 100)?.toFixed(1)}%</td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getFatigueColor(inning.fatigue_risk)}`}>
                            {inning.fatigue_risk.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PitcherFatigue;
