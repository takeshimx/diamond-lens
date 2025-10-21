import React, { useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity } from 'lucide-react';

const PlayerSegmentation = () => {
  const [playerType, setPlayerType] = useState('batters');
  const [segmentationData, setSegmentationData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Backend URL detection
  const getBackendUrl = () => {
    // Cloud Run environment detection
    if (window.location.hostname.includes('run.app')) {
      return 'https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app';
    }
    
    // GitHub Codespaces environment detection
    const currentUrl = window.location.href;
    if (currentUrl.includes('app.github.dev')) {
      return currentUrl.replace('-5173.app.github.dev', '-8000.app.github.dev').split('?')[0];
    }
    return 'http://localhost:8000';
  };

  const BACKEND_URL = getBackendUrl();

  const fetchSegmentation = async (type) => {
    setIsLoading(true);
    try {
      const endpoint = type === 'batters'
        ? '/api/v1/batter-segmentation?season=2024&min_pa=300'
        : '/api/v1/pitcher-segmentation?season=2025&min_ip=90';

      const response = await fetch(`${BACKEND_URL}${endpoint}`);
      const data = await response.json();
      setSegmentationData(data);
    } catch (error) {
      console.error('Error fetching segmentation:', error);
      alert('データ取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  // Load data on mount
  React.useEffect(() => {
    fetchSegmentation(playerType);
  }, [playerType]);

  // Batter scatter plot
  const BatterScatterPlot = ({ players }) => {
    const cluster0 = players.filter(p => p.cluster === 0);
    const cluster1 = players.filter(p => p.cluster === 1);
    const cluster2 = players.filter(p => p.cluster === 2);
    const cluster3 = players.filter(p => p.cluster === 3);

    return (
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            type="number"
            dataKey="ops"
            name="OPS"
            stroke="#9CA3AF"
            label={{ value: 'OPS', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }}
            domain={[0.5, 1.2]}
          />
          <YAxis
            type="number"
            dataKey="iso"
            name="ISO"
            stroke="#9CA3AF"
            label={{ value: 'ISO', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
          />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div style={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px', padding: '10px' }}>
                    <p style={{ color: '#FFFFFF', fontWeight: 'bold', marginBottom: '5px' }}>{data.name}</p>
                    <p style={{ color: '#E5E7EB', fontSize: '12px' }}>Team: {data.team}</p>
                    <p style={{ color: '#E5E7EB', fontSize: '12px' }}>OPS: {data.ops?.toFixed(3)}</p>
                    <p style={{ color: '#E5E7EB', fontSize: '12px' }}>ISO: {data.iso?.toFixed(3)}</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Legend />
          <Scatter name="Struggling" data={cluster3} fill="#ff7c7c" />
          <Scatter name="Solid Regulars" data={cluster0} fill="#8884d8" />
          <Scatter name="Elite Contact" data={cluster1} fill="#82ca9d" />
          <Scatter name="Superstar Sluggers" data={cluster2} fill="#ffc658" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  };

  // Pitcher scatter plot
  const PitcherScatterPlot = ({ players }) => {
    const cluster0 = players.filter(p => p.cluster === 0);
    const cluster1 = players.filter(p => p.cluster === 1);
    const cluster2 = players.filter(p => p.cluster === 2);
    const cluster3 = players.filter(p => p.cluster === 3);

    return (
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            type="number"
            dataKey="era"
            name="ERA"
            stroke="#9CA3AF"
            reversed
            label={{ value: 'ERA', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }}
          />
          <YAxis
            type="number"
            dataKey="k_9"
            name="K/9"
            stroke="#9CA3AF"
            label={{ value: 'K/9', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
          />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div style={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px', padding: '10px' }}>
                    <p style={{ color: '#FFFFFF', fontWeight: 'bold', marginBottom: '5px' }}>{data.name}</p>
                    <p style={{ color: '#E5E7EB', fontSize: '12px' }}>Team: {data.team}</p>
                    <p style={{ color: '#E5E7EB', fontSize: '12px' }}>ERA: {data.era?.toFixed(2)}</p>
                    <p style={{ color: '#E5E7EB', fontSize: '12px' }}>K/9: {data.k_9?.toFixed(2)}</p>
                    {data.gbpct != null && <p style={{ color: '#E5E7EB', fontSize: '12px' }}>GB%: {(data.gbpct * 100)?.toFixed(1)}%</p>}
                  </div>
                );
              }
              return null;
            }}
          />
          <Legend />
          <Scatter name="Struggling" data={cluster1} fill="#ff7c7c" />
          <Scatter name="Mid-Tier" data={cluster3} fill="#82ca9d" />
          <Scatter name="Strikeout Dom" data={cluster2} fill="#ffc658" />
          <Scatter name="Elite Balanced" data={cluster0} fill="#8884d8" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  };

  // Cluster summary table
  const ClusterSummaryTable = ({ clusterSummary, playerType }) => {
    // Batter cluster order: 2 (Superstar), 1 (Elite Contact), 0 (Solid), 3 (Struggling)
    // Pitcher cluster order: 2 (Strikeout Dom), 0 (Elite Balanced), 3 (Mid-Tier), 1 (Struggling)
    const batterOrder = [2, 1, 0, 3];
    const pitcherOrder = [2, 0, 3, 1];
    const clusterOrder = playerType === 'batters' ? batterOrder : pitcherOrder;

    const sortedClusters = clusterOrder.map(id =>
      clusterSummary.find(c => c.cluster_id === id)
    ).filter(Boolean);

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-gray-300">
          <thead className="text-xs uppercase bg-gray-700">
            <tr>
              <th className="px-4 py-3">Cluster</th>
              <th className="px-4 py-3">Count</th>
              {playerType === 'batters' ? (
                <>
                  <th className="px-4 py-3">Avg OPS</th>
                  <th className="px-4 py-3">Avg ISO</th>
                  <th className="px-4 py-3">Avg K%</th>
                </>
              ) : (
                <>
                  <th className="px-4 py-3">Avg ERA</th>
                  <th className="px-4 py-3">Avg K/9</th>
                  <th className="px-4 py-3">Avg GB%</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {sortedClusters.filter(cluster => cluster != null).map((cluster) => (
              <tr key={cluster.cluster_id} className="border-b border-gray-700">
                <td className="px-4 py-3 font-semibold">{cluster.cluster_name}</td>
                <td className="px-4 py-3">{cluster.count}</td>
                {playerType === 'batters' ? (
                  <>
                    <td className="px-4 py-3">{cluster.avg_ops?.toFixed(3)}</td>
                    <td className="px-4 py-3">{cluster.avg_iso?.toFixed(3)}</td>
                    <td className="px-4 py-3">{cluster.avg_k_rate?.toFixed(1)}%</td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-3">{cluster.avg_era?.toFixed(2)}</td>
                    <td className="px-4 py-3">{cluster.avg_k_9?.toFixed(2)}</td>
                    <td className="px-4 py-3">{cluster.avg_gbpct ? (cluster.avg_gbpct * 100).toFixed(1) : 'N/A'}%</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2 flex items-center justify-center gap-3">
          <Activity className="w-8 h-8 text-blue-400" />
          Player Segmentation
        </h2>
        <p className="text-gray-400">K-means clustering analysis</p>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => setPlayerType('batters')}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              playerType === 'batters'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Batters
          </button>
          <button
            onClick={() => setPlayerType('pitchers')}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              playerType === 'pitchers'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Pitchers
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="text-center text-gray-400 py-8">
          <p>Loading...</p>
        </div>
      )}

      {segmentationData && !isLoading && (
        <>
          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
            <h3 className="text-xl font-semibold text-white mb-4">
              {playerType === 'batters' ? 'OPS vs ISO' : 'ERA vs K/9'}
            </h3>
            {playerType === 'batters' ? (
              <BatterScatterPlot players={segmentationData.players} />
            ) : (
              <PitcherScatterPlot players={segmentationData.players} />
            )}
          </div>

          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
            <h3 className="text-xl font-semibold text-white mb-4">Cluster Summary</h3>
            <ClusterSummaryTable
              clusterSummary={segmentationData.cluster_summary}
              playerType={playerType}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default PlayerSegmentation;