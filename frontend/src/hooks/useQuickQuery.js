import { useState } from 'react';

/**
 * クイック質問の結果状態と実行ロジックを管理するフック。
 *
 * @param {object} deps
 * @param {Function} deps.callFixedQueryAPI
 * @param {Function} deps.setIsLoading
 */
export const useQuickQuery = ({ callFixedQueryAPI, setIsLoading }) => {
  const [quickResult, setQuickResult] = useState(null);

  const handleQuickQuestion = async (question) => {
    console.log('🚀 Quick Question clicked:', question);

    setQuickResult(null);
    setIsLoading(true);

    try {
      const response = await callFixedQueryAPI(question.params);
      console.log('🔍 Quick Question API Response:', response);

      setQuickResult({
        question: question.title,
        answer: response.answer,
        stats: response.stats,
        isTable: response.isTable,
        isTransposed: response.isTransposed,
        tableData: response.tableData,
        columns: response.columns,
        decimalColumns: response.decimalColumns,
        grouping: response.grouping,
        isChart: response.isChart,
        chartType: response.chartType,
        chartData: response.chartData,
        chartConfig: response.chartConfig,
        timestamp: new Date(),
      });
    } catch (error) {
      console.error('❌ Quick Question Error:', error);
      setQuickResult({
        question: question.title,
        answer: 'エラーが発生しました。しばらく後でもう一度お試しください。',
        isChart: false,
        isTable: false,
        timestamp: new Date(),
      });
    }

    setIsLoading(false);
  };

  return { quickResult, setQuickResult, handleQuickQuestion };
};
