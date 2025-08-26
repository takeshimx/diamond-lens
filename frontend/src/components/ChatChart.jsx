// Simple Chart Component for React Chat App
// Start with basic line charts only

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const SimpleChatChart = ({ chartData, chartConfig, chartType }) => {
  console.log('🔍 SimpleChatChart props:', { chartData, chartConfig, chartType });
  
  if (!chartData || !chartConfig) {
    console.log('❌ SimpleChatChart: Missing data or config');
    return null;
  }

  console.log('✅ SimpleChatChart: Rendering chart with data:', chartData.length, 'points');

  const renderLineChart = () => {
    return (
      <ResponsiveContainer width="100%" height={350}>
        <LineChart 
          data={chartData} 
          margin={{ top: 20, right: 50, left: 40, bottom: 40 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-300 dark:stroke-gray-600" />
          <XAxis 
            dataKey={chartConfig.xAxis} 
            className="fill-gray-600 dark:fill-gray-300"
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            className="fill-gray-600 dark:fill-gray-300"
            tick={{ fontSize: 12 }}
            domain={chartConfig.yDomain || ['auto', 'auto']}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'rgb(31 41 55)', 
              border: '1px solid rgb(75 85 99)',
              borderRadius: '0.5rem',
              color: 'white'
            }}
            formatter={(value, name) => [
              typeof value === 'number' ? value.toFixed(3) : value, 
              name
            ]}
          />
          <Legend />
          
          {/* 単一のライン表示（後で複数対応可能） */}
          <Line
            type="monotone"
            dataKey={chartConfig.dataKey}
            stroke={chartConfig.lineColor || "#3B82F6"}
            strokeWidth={3}
            dot={{ r: 5, fill: chartConfig.lineColor || "#3B82F6" }}
            activeDot={{ r: 7 }}
            name={chartConfig.lineName || "値"}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="mt-4 -mx-4 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <h4 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
        {chartConfig.title}
      </h4>
      <div className="mb-3 text-xs text-green-600 dark:text-green-400">
        🟢 Chart component loaded - Type: {chartType}, Data points: {chartData.length}
      </div>
      <div className="w-full min-w-[600px] overflow-x-auto">
        {chartType === 'line' && renderLineChart()}
        {chartType !== 'line' && (
          <div className="text-center text-gray-500">
            このチャート形式は現在サポートされていません
          </div>
        )}
      </div>
    </div>
  );
};

// メッセージコンポーネント内での使用例
const MessageBubble = ({ message }) => {
  return (
    <div className="message-bubble">
      <p className="whitespace-pre-wrap">{message.content}</p>
      
      {/* 既存のテーブル表示 */}
      {message.isTable && message.tableData && (
        <DataTable tableData={message.tableData} columns={message.columns} />
      )}
      
      {/* 新規追加: シンプルチャート表示 */}
      {message.isChart && message.chartData && (
        <SimpleChatChart 
          chartData={message.chartData}
          chartConfig={message.chartConfig}
          chartType={message.chartType}
        />
      )}
    </div>
  );
};

export default SimpleChatChart;