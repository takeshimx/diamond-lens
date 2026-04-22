import {
  BATTING_METRIC_DISPLAY_NAMES,
  PITCHING_METRIC_DISPLAY_NAMES,
  getMonthlyBattingChartConfig,
  getMonthlyBattingAnswerText,
} from '../constants/metricConfigs.js';

/** KPIカードデータを生成するユーティリティ */
const createKPICards = (data, metrics, season, playerName) => {
  const metricsArray = typeof metrics === 'string' ? [metrics] : (metrics || []);
  return metricsArray
    .filter(metricKey => data[metricKey] !== undefined && data[metricKey] !== null)
    .map(metricKey => ({
      metric: metricKey,
      value: data[metricKey],
      playerName,
      season,
    }));
};

/**
 * 構造化クエリ（PlayerProfile / QuickQuestions / CustomQueryBuilder）用
 * 固定エンドポイント呼び出しフック。
 *
 * @param {object} deps
 * @param {Function} deps.getBackendURL
 * @param {Function} deps.getAuthHeaders
 */
export const useFixedQueryAPI = ({ getBackendURL, getAuthHeaders }) => {

  const callFixedQueryAPI = async (questionParams) => {
    console.log('🚀 デバッグ：固定クエリ API呼び出し開始:', questionParams);

    try {
      const baseURL = getBackendURL();
      console.log('🎯 デバッグ：Fixed Query baseURL:', baseURL);

      // エンドポイント構築
      let endpoint;
      if (questionParams.queryType === 'season_batting_stats') {
        const seasonParam = questionParams.season ? `season=${questionParams.season}&` : '';
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/season-batting-stats?${seasonParam}metrics=${questionParams.metrics || questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_batting_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/monthly-batting-stats?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_offensive_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/monthly-offensive-stats?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_risp_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/performance-at-risp?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'season_pitching_stats') {
        const seasonParam = questionParams.season ? `season=${questionParams.season}&` : '';
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/season-pitching-stats?${seasonParam}metrics=${questionParams.metrics || questionParams.metric}`;
      } else if (questionParams.queryType === 'season_batting_splits') {
        const seasonParam = questionParams.season ? `season=${questionParams.season}&` : '';
        const metricsParams = Array.isArray(questionParams.metrics)
          ? questionParams.metrics.map(m => `metrics=${m}`).join('&')
          : `metrics=${questionParams.metrics}`;
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/season-batting-splits?${seasonParam}split_type=${questionParams.split_type}&${metricsParams}`;
      } else {
        throw new Error(`Unsupported query type: ${questionParams.queryType}`);
      }

      console.log('🎯 デバッグ：Fixed Query endpoint:', endpoint);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log('⏰ デバッグ：リクエストタイムアウト（120秒）');
        controller.abort();
      }, 120000);

      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, { method: 'GET', headers, signal: controller.signal });

      clearTimeout(timeoutId);

      console.log('📥 デバッグ：Fixed Query response received:', {
        status: response.status, statusText: response.statusText, ok: response.ok, url: response.url
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      const apiResponse = await response.json();
      console.log('🔍 デバッグ：Fixed Query JSON response:', apiResponse);

      // ===== season_batting_stats =====
      if (questionParams.queryType === 'season_batting_stats') {
        if (apiResponse && (Array.isArray(apiResponse) ? apiResponse.length > 0 : typeof apiResponse === 'object')) {
          const isMultiSeason = questionParams.season === null || questionParams.season === undefined;
          const dataArray = Array.isArray(apiResponse) ? apiResponse : [apiResponse];
          const playerName = dataArray[0].name || dataArray[0].player_name || dataArray[0].batter_name || 'Selected Player';

          if (isMultiSeason && dataArray.length > 1) {
            const primaryMetric = Array.isArray(questionParams.metrics) ? questionParams.metrics[0] : questionParams.metrics;
            const rateMetrics = ['avg', 'obp', 'slg', 'ops', 'woba', 'babip', 'iso'];
            const chartType = rateMetrics.includes(primaryMetric) ? 'line' : 'bar';
            const chartData = dataArray
              .map(item => ({ year: item.season?.toString() || 'Unknown', value: item[primaryMetric] || 0 }))
              .filter(item => item.value !== null && item.value !== undefined);

            return {
              answer: `${playerName}選手の通算成績推移（${BATTING_METRIC_DISPLAY_NAMES[primaryMetric] || primaryMetric}）を表示します。`,
              isChart: true, chartType,
              chartData,
              chartConfig: {
                title: `${playerName} - ${BATTING_METRIC_DISPLAY_NAMES[primaryMetric] || primaryMetric} 年度別推移`,
                xAxis: 'year', dataKey: 'value',
                lineColor: rateMetrics.includes(primaryMetric) ? '#3B82F6' : '#10B981',
                lineName: BATTING_METRIC_DISPLAY_NAMES[primaryMetric] || primaryMetric,
                yDomain: [0, 'dataMax'],
              },
              isTable: false, isCards: false,
            };
          } else {
            const data = dataArray[0];
            const season = data.season || questionParams.season;
            const kpiCards = createKPICards(data, questionParams.metrics || [questionParams.metric], season, playerName);
            return {
              answer: `${playerName}選手の${season}年シーズン成績をKPIカードで表示します。`,
              isCards: true, cardsData: kpiCards, isTable: false, isChart: false,
            };
          }
        }
        console.log('⚠️ デバッグ：No season batting stats data found');
        return { answer: 'シーズン打撃成績データが見つかりませんでした。', isTable: false, isChart: false, isCards: false };
      }

      // ===== season_batting_splits =====
      if (questionParams.queryType === 'season_batting_splits') {
        if (apiResponse && Array.isArray(apiResponse) && apiResponse.length > 0) {
          const data = apiResponse[0];
          const playerName = data.batter_name || data.player_name || 'Selected Player';
          const season = data.game_year || questionParams.season || new Date().getFullYear();
          const kpiCards = createKPICards(data, questionParams.metrics, season, playerName);
          return {
            answer: `${playerName}選手の${season}年場面別成績をKPIカードで表示します。`,
            isCards: true, cardsData: kpiCards, isTable: false, isChart: false,
          };
        }
      }

      // ===== season_pitching_stats =====
      if (questionParams.queryType === 'season_pitching_stats') {
        if (apiResponse && (Array.isArray(apiResponse) ? apiResponse.length > 0 : typeof apiResponse === 'object')) {
          const isMultiSeason = questionParams.season === null || questionParams.season === undefined;
          const dataArray = Array.isArray(apiResponse) ? apiResponse : [apiResponse];
          const playerName = dataArray[0].name || dataArray[0].player_name || dataArray[0].pitcher_name || 'Selected Player';

          if (isMultiSeason && dataArray.length > 1) {
            const primaryMetric = Array.isArray(questionParams.metrics) ? questionParams.metrics[0] : questionParams.metrics;
            const chartData = dataArray
              .map(item => ({ year: item.season?.toString() || 'Unknown', value: item[primaryMetric] || 0 }))
              .filter(item => item.value !== null && item.value !== undefined);

            return {
              answer: `${playerName}選手の通算投球成績推移（${PITCHING_METRIC_DISPLAY_NAMES[primaryMetric] || primaryMetric}）を表示します。`,
              isChart: true, chartType: 'line',
              chartData,
              chartConfig: {
                title: `${playerName} - ${PITCHING_METRIC_DISPLAY_NAMES[primaryMetric] || primaryMetric} 年度別推移`,
                xAxis: 'year', dataKey: 'value', lineColor: '#EF4444',
                lineName: PITCHING_METRIC_DISPLAY_NAMES[primaryMetric] || primaryMetric,
                yDomain: [0, 'dataMax'],
              },
              isTable: false, isCards: false,
            };
          } else {
            const data = dataArray[0];
            const season = data.season || questionParams.season;
            const kpiCards = createKPICards(data, questionParams.metrics || [questionParams.metric], season, playerName);
            return {
              answer: `${playerName}選手の${season}年シーズン投球成績をKPIカードで表示します。`,
              isCards: true, cardsData: kpiCards, isTable: false, isChart: false,
            };
          }
        }
        console.log('⚠️ デバッグ：No season pitching stats data found');
        return { answer: 'シーズン投球成績データが見つかりませんでした。', isTable: false, isChart: false, isCards: false };
      }

      // ===== 月別データ（monthly_batting_stats 等）=====
      if (Array.isArray(apiResponse) && apiResponse.length > 0) {
        const metricField = questionParams.metric;
        const playerName = apiResponse[0].batter_name || 'Selected Player';
        console.log('🔍 Debug - Metric field:', metricField, '| Player:', playerName);

        const chartData = apiResponse.map(item => ({
          month: `${item.game_month}月`,
          value: item[metricField] || 0,
        }));
        const chartConfig = getMonthlyBattingChartConfig(questionParams.metric, questionParams.season, playerName);

        console.log('✅ デバッグ：Fixed Query API呼び出し成功');
        return {
          answer: getMonthlyBattingAnswerText(questionParams.metric, questionParams.season, playerName),
          isTable: false, isTransposed: false, tableData: null, columns: null,
          decimalColumns: [], grouping: null, stats: null,
          isChart: true, chartType: chartConfig.chartType, chartData, chartConfig,
        };
      }

      // データなし（モックデータ）
      console.log('⚠️ デバッグ：No data found, using mock data');
      return {
        answer: '現在データが取得できないため、サンプルデータで大谷翔平選手の月別打率推移を表示しています。',
        isTable: false, isTransposed: false, tableData: null, columns: null,
        decimalColumns: [], grouping: null, stats: null,
        isChart: true, chartType: 'line',
        chartData: [
          { month: '3月', batting_average: 0.125 },
          { month: '4月', batting_average: 0.238 },
          { month: '5月', batting_average: 0.278 },
          { month: '6月', batting_average: 0.301 },
          { month: '7月', batting_average: 0.295 },
          { month: '8月', batting_average: 0.264 },
          { month: '9月', batting_average: 0.289 },
        ],
        chartConfig: {
          title: '大谷翔平 2024年月別打率推移 (サンプルデータ)',
          xAxis: 'month', dataKey: 'batting_average',
          lineColor: '#3B82F6', lineName: '打率', yDomain: [0, 0.4],
        },
      };

    } catch (error) {
      console.error('❌ デバッグ：Fixed Query API呼び出しエラー:', error);
      if (error.name === 'AbortError') {
        return { answer: 'リクエストがタイムアウトしました（60秒）。バックエンドの処理が重い可能性があります。', isTable: false, isChart: false };
      }
      return { answer: `エラーが発生しました: ${error.message}`, isTable: false, isChart: false };
    }
  };

  return { callFixedQueryAPI };
};
