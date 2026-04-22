import { useState } from 'react';
import {
  SEASON_BATTING_METRIC_MAPPING,
  MONTHLY_TRENDS_METRIC_MAPPING,
  SEASON_PITCHING_METRIC_MAPPING,
  getMonthlyMetricColor,
  getMonthlyMetricDisplayName,
} from '../constants/metricConfigs.js';

const CATEGORY_NAMES = {
  season_batting: 'シーズン打撃成績',
  season_pitching: 'シーズン投手成績',
  batting_splits: '場面別打撃成績',
  monthly_trends: '月別推移',
  team_comparison: 'チーム比較',
  career_stats: '通算成績',
  batting_leaderboard: '打撃リーダーボード',
  pitching_leaderboard: '投手リーダーボード',
};

const generateSummaryText = (queryState) => {
  const seasonText = queryState.seasonMode === 'all'
    ? '全シーズン'
    : `${queryState.specificYear}年シーズン`;

  const metricsText = queryState.metrics.length === 1
    ? queryState.metrics[0]
    : `${queryState.metrics.join('、')}など`;

  const isLeaderboard = queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard';

  if (isLeaderboard) {
    return `${seasonText}における${CATEGORY_NAMES[queryState.category.id]} (${queryState.league}、${queryState.metricOrder}でソート)`;
  }
  return `${queryState.player?.name || '選手'}の${seasonText}における${CATEGORY_NAMES[queryState.category.id]}から${metricsText}の分析結果`;
};

/**
 * カスタムクエリの結果状態と実行ロジックを管理するフック。
 *
 * @param {object} deps
 * @param {Function} deps.callFixedQueryAPI
 * @param {Function} deps.getBackendURL
 * @param {Function} deps.getAuthHeaders
 * @param {Function} deps.setIsLoading
 */
export const useCustomQuery = ({ callFixedQueryAPI, getBackendURL, getAuthHeaders, setIsLoading }) => {
  const [customResult, setCustomResult] = useState(null);

  const handleCustomQuery = async (queryState) => {
    console.log('🚀 Custom Query execution:', queryState);

    setCustomResult(null);
    setIsLoading(true);

    try {
      const isLeaderboard = queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard';

      const params = {
        playerId: isLeaderboard ? null : (queryState.player?.mlb_id || queryState.player?.id),
        season: queryState.seasonMode === 'all' ? null : queryState.specificYear,
        metrics: queryState.metrics,
        category: queryState.category.id,
      };

      console.log('🔍 Custom Query Params:', params);

      let response;
      const primaryMetric = queryState.metrics[0];

      if (queryState.category.id === 'season_batting' && primaryMetric) {
        const mappedMetrics = queryState.metrics
          .map(metric => {
            const backendMetric = SEASON_BATTING_METRIC_MAPPING[metric];
            if (backendMetric === null) { console.warn(`Metric "${metric}" not supported yet`); return null; }
            if (!backendMetric) { console.warn(`Unknown metric: ${metric}`); return null; }
            return backendMetric;
          })
          .filter(Boolean);

        console.log('🔍 Season batting - Frontend metrics:', queryState.metrics, '-> Backend metrics:', mappedMetrics);

        if (mappedMetrics.length === 0) throw new Error('選択された指標はサポートされていません。');

        response = await callFixedQueryAPI({
          playerId: params.playerId,
          season: queryState.seasonMode === 'all' ? null : (params.season || 2024),
          metrics: mappedMetrics,
          queryType: 'season_batting_stats',
        });

      } else if (queryState.category.id === 'monthly_trends' && queryState.metrics.length > 0) {
        console.log('🔍 Debug - Monthly trends execution started');

        const chartPromises = [];
        const validMetrics = [];

        for (const metric of queryState.metrics) {
          const backendMetric = MONTHLY_TRENDS_METRIC_MAPPING[metric];
          console.log('🔍 Monthly trends - Frontend metric:', metric, '-> Backend metric:', backendMetric);

          if (backendMetric === null) { console.warn(`指標「${metric}」は現在サポートされていません。スキップします。`); continue; }
          if (!backendMetric) { console.warn(`未知の指標です: ${metric}。スキップします。`); continue; }

          validMetrics.push({ frontendMetric: metric, backendMetric });

          chartPromises.push(
            callFixedQueryAPI({
              playerId: params.playerId,
              season: params.season || 2024,
              metric: backendMetric,
              queryType: 'monthly_batting_stats',
            }).then(apiResponse => ({ metric, backendMetric, data: apiResponse }))
          );
        }

        if (validMetrics.length === 0) throw new Error('選択された指標はいずれもサポートされていません。');

        console.log('🔍 Debug - Making parallel API calls, count:', chartPromises.length);
        const chartResults = await Promise.all(chartPromises);
        console.log('🔍 Debug - Chart results received:', chartResults);

        response = {
          isMultiChart: true,
          charts: chartResults.map(result => {
            let chartData = result.data.chartData || [];
            let chartConfig = result.data.chartConfig || {};

            if (!result.data.isChart && Array.isArray(result.data) && result.data.length > 0) {
              const playerName = result.data[0]?.batter_name || result.data[0]?.player_name || 'Selected Player';
              const year = result.data[0]?.game_year || 2024;

              chartData = result.data.map(monthData => ({
                month: monthData.game_month || monthData.month,
                value: monthData[result.backendMetric] || 0,
                year: monthData.game_year || monthData.year || 2024,
              })).sort((a, b) => a.month - b.month);

              chartConfig = {
                title: `${playerName} ${year}年 ${result.metric} 月別推移`,
                xAxis: 'month', dataKey: 'value',
                lineColor: getMonthlyMetricColor(result.metric),
                lineName: getMonthlyMetricDisplayName(result.metric),
                yDomain: [0, 'dataMax'],
              };
            }

            return {
              metric: result.metric,
              backendMetric: result.backendMetric,
              metricDisplayName: getMonthlyMetricDisplayName(result.metric),
              isChart: result.data.isChart || chartData.length > 0,
              chartType: result.data.chartType || 'line',
              chartData,
              chartConfig,
              answer: result.data.answer || `${getMonthlyMetricDisplayName(result.metric)}の月別推移`,
            };
          }),
          answer: `${validMetrics.length}個の指標の月別推移を表示します。`,
          stats: { '対象指標数': validMetrics.length, '対象シーズン': params.season || 2024 },
        };

      } else if (queryState.category.id === 'batting_splits' && queryState.splitType && queryState.metrics.length > 0) {

        if (queryState.splitType.id === 'custom') {
          const baseURL = getBackendURL();
          const cs = queryState.customSituation;

          if (queryState.seasonMode === 'all') {
            const chartPromises = [];

            for (const metric of queryState.metrics) {
              const urlParams = new URLSearchParams();
              if (cs?.innings?.length > 0) cs.innings.forEach(inning => urlParams.append('innings', inning.toString()));
              if (cs?.strikes != null) urlParams.append('strikes', cs.strikes.toString());
              if (cs?.balls != null) urlParams.append('balls', cs.balls.toString());
              if (cs?.pitcherType) urlParams.append('p_throws', cs.pitcherType);
              if (cs?.runnersOnBase?.length > 0) cs.runnersOnBase.forEach(r => urlParams.append('runners', r));
              if (cs?.pitchTypes?.length > 0) cs.pitchTypes.forEach(p => urlParams.append('pitch_types', p));

              const endpoint = `${baseURL}/api/v1/players/${params.playerId}/statcast/batter/advanced-stats?${urlParams.toString()}`;
              chartPromises.push(fetch(endpoint).then(res => res.json()).then(apiResponse => ({ metric, data: apiResponse })));
            }

            const careerUrlParams = new URLSearchParams();
            careerUrlParams.append('is_career', 'true');
            if (cs?.innings?.length > 0) cs.innings.forEach(inning => careerUrlParams.append('innings', inning.toString()));
            if (cs?.strikes != null) careerUrlParams.append('strikes', cs.strikes.toString());
            if (cs?.balls != null) careerUrlParams.append('balls', cs.balls.toString());
            if (cs?.pitcherType) careerUrlParams.append('p_throws', cs.pitcherType);
            if (cs?.runnersOnBase?.length > 0) cs.runnersOnBase.forEach(r => careerUrlParams.append('runners', r));
            if (cs?.pitchTypes?.length > 0) cs.pitchTypes.forEach(p => careerUrlParams.append('pitch_types', p));

            const careerEndpoint = `${baseURL}/api/v1/players/${params.playerId}/statcast/batter/advanced-stats?${careerUrlParams.toString()}`;

            const [chartResults, careerResponse] = await Promise.all([
              Promise.all(chartPromises),
              fetch(careerEndpoint).then(res => res.json()),
            ]);

            let careerKpis = [];
            if (careerResponse && Array.isArray(careerResponse) && careerResponse.length > 0) {
              const careerData = careerResponse[0];
              careerKpis = queryState.metrics.map(metric => ({
                metric, value: careerData[metric], playerName: careerData.batter_name, season: 'キャリア通算',
              }));
            }

            const metricDisplayNames = {
              'hits': '安打', 'homeruns': 'ホームラン', 'doubles': '二塁打', 'triples': '三塁打', 'singles': '単打',
              'at_bats': '打数', 'avg': '打率', 'obp': '出塁率', 'slg': '長打率', 'ops': 'OPS',
              'strikeouts': '三振', 'bb_hbp': '四死球', 'strikeout_rate': '三振率',
            };
            const countingStats = ['hits', 'homeruns', 'doubles', 'triples', 'singles', 'at_bats', 'strikeouts', 'bb_hbp'];

            response = {
              isMultiChart: true, isChart: false,
              isCards: careerKpis.length > 0, cardsData: careerKpis,
              charts: chartResults.map(result => {
                if (Array.isArray(result.data) && result.data.length > 0) {
                  const playerName = result.data[0]?.batter_name || 'Selected Player';
                  const chartData = result.data.map(s => ({
                    year: s.game_year?.toString() || 'Unknown', value: s[result.metric],
                  })).filter(item => item.value != null);
                  const displayName = metricDisplayNames[result.metric] || result.metric;
                  return {
                    metric: result.metric, metricDisplayName: displayName,
                    isChart: chartData.length > 0,
                    chartType: countingStats.includes(result.metric) ? 'bar' : 'line',
                    chartData,
                    chartConfig: { title: `${playerName} ${displayName} 年次推移`, xAxis: 'year', dataKey: 'value', lineColor: '#3B82F6', lineName: displayName, yDomain: [0, 'dataMax'] },
                    answer: `${displayName}の年次推移`,
                  };
                }
                return { metric: result.metric, isChart: false, chartType: 'line', chartData: [], chartConfig: {}, answer: `${result.metric}のデータがありません` };
              }),
              answer: `選択条件でのキャリア通算成績と${queryState.metrics.length}個の指標の年次推移を表示します。`,
            };

          } else {
            const urlParams = new URLSearchParams();
            if (params.season) urlParams.append('season', params.season.toString());
            if (cs?.innings?.length > 0) cs.innings.forEach(inning => urlParams.append('innings', inning.toString()));
            if (cs?.strikes != null) urlParams.append('strikes', cs.strikes.toString());
            if (cs?.balls != null) urlParams.append('balls', cs.balls.toString());
            if (cs?.pitcherType) urlParams.append('p_throws', cs.pitcherType);
            if (cs?.runnersOnBase?.length > 0) cs.runnersOnBase.forEach(r => urlParams.append('runners', r));
            if (cs?.pitchTypes?.length > 0) cs.pitchTypes.forEach(p => urlParams.append('pitch_types', p));

            const endpoint = `${baseURL}/api/v1/players/${params.playerId}/statcast/batter/advanced-stats?${urlParams.toString()}`;
            const headers = await getAuthHeaders();
            const apiResponse = await fetch(endpoint, { headers });
            if (!apiResponse.ok) throw new Error(`Custom situation API call failed: ${apiResponse.status}`);

            const data = await apiResponse.json();

            if (Array.isArray(data) && data.length > 0) {
              const seasonData = data[0];
              const playerName = seasonData.batter_name || 'Selected Player';
              const kpiCards = queryState.metrics
                .map(metric => ({ metric, value: seasonData[metric], playerName, season: params.season || 'カスタム状況' }))
                .filter(card => card.value != null);

              response = {
                answer: `${playerName}選手のカスタム状況成績をKPIカードで表示します。`,
                isCards: true, cardsData: kpiCards, isTable: false, isChart: false,
              };
            } else {
              response = { answer: 'カスタム状況データが見つかりませんでした。', isTable: false, isChart: false, isCards: false };
            }
          }

        } else if (queryState.seasonMode === 'all') {
          const baseURL = getBackendURL();
          const chartPromises = queryState.metrics.map(metric => {
            const endpoint = `${baseURL}/api/v1/players/${params.playerId}/season-batting-splits?split_type=${queryState.splitType.id}&metrics=${metric}`;
            return fetch(endpoint).then(res => res.json()).then(apiResponse => ({ metric, data: apiResponse }));
          });

          const chartResults = await Promise.all(chartPromises);
          console.log('🔍 Debug - Chart results for batting splits:', chartResults);

          const splitMetricDisplayNames = {
            'hits_at_risp': 'RISP時安打', 'homeruns_at_risp': 'RISP時ホームラン', 'doubles_at_risp': 'RISP時二塁打',
            'triples_at_risp': 'RISP時三塁打', 'singles_at_risp': 'RISP時単打', 'ab_at_risp': 'RISP時打数',
            'avg_at_risp': 'RISP時打率', 'obp_at_risp': 'RISP時出塁率', 'slg_at_risp': 'RISP時長打率',
            'ops_at_risp': 'RISP時OPS', 'strikeout_rate_at_risp': 'RISP時三振率',
            'hits_at_bases_loaded': '満塁時安打', 'grandslam': 'グランドスラム', 'doubles_at_bases_loaded': '満塁時二塁打',
            'triples_at_bases_loaded': '満塁時三塁打', 'singles_at_bases_loaded': '満塁時単打', 'ab_at_bases_loaded': '満塁時打数',
            'avg_at_bases_loaded': '満塁時打率', 'obp_at_bases_loaded': '満塁時出塁率', 'slg_at_bases_loaded': '満塁時長打率',
            'ops_at_bases_loaded': '満塁時OPS', 'strikeout_rate_at_bases_loaded': '満塁時三振率',
          };
          const splitCountingStats = ['hits_at_risp', 'homeruns_at_risp', 'doubles_at_risp', 'triples_at_risp', 'singles_at_risp', 'ab_at_risp',
            'hits_at_bases_loaded', 'grandslam', 'doubles_at_bases_loaded', 'triples_at_bases_loaded', 'singles_at_bases_loaded', 'ab_at_bases_loaded'];

          response = {
            isMultiChart: true, isChart: false, isCards: false,
            charts: chartResults.map(result => {
              if (Array.isArray(result.data) && result.data.length > 0) {
                const playerName = result.data[0]?.batter_name || 'Selected Player';
                const chartData = result.data.map(s => ({
                  year: s.game_year?.toString() || 'Unknown', value: s[result.metric],
                })).filter(item => item.value != null);
                const displayName = splitMetricDisplayNames[result.metric] || result.metric;
                return {
                  metric: result.metric, metricDisplayName: displayName,
                  isChart: chartData.length > 0,
                  chartType: splitCountingStats.includes(result.metric) ? 'bar' : 'line',
                  chartData,
                  chartConfig: { title: `${playerName} ${displayName} 年次推移`, xAxis: 'year', dataKey: 'value', lineColor: '#3B82F6', lineName: displayName, yDomain: [0, 'dataMax'] },
                  answer: `${displayName}の年次推移`,
                };
              }
              return { metric: result.metric, isChart: false, chartType: 'line', chartData: [], chartConfig: {}, answer: `${result.metric}のデータがありません` };
            }),
            answer: `${queryState.metrics.length}個の指標の年次推移を表示します。`,
          };

        } else {
          response = await callFixedQueryAPI({
            playerId: params.playerId,
            season: params.season || 2024,
            split_type: queryState.splitType.id,
            metrics: queryState.metrics,
            queryType: 'season_batting_splits',
          });
        }

      } else if (queryState.category.id === 'season_pitching' && primaryMetric) {
        const mappedMetrics = queryState.metrics
          .map(metric => {
            const backendMetric = SEASON_PITCHING_METRIC_MAPPING[metric];
            if (backendMetric === null) { console.warn(`Metric "${metric}" not supported yet`); return null; }
            if (!backendMetric) { console.warn(`Unknown metric: ${metric}`); return null; }
            return backendMetric;
          })
          .filter(Boolean);

        console.log('🔍 Season pitching - Frontend metrics:', queryState.metrics, '-> Backend metrics:', mappedMetrics);
        if (mappedMetrics.length === 0) throw new Error('選択された指標はサポートされていません。');

        response = await callFixedQueryAPI({
          playerId: params.playerId,
          season: queryState.seasonMode === 'all' ? null : (params.season || 2024),
          metrics: mappedMetrics,
          queryType: 'season_pitching_stats',
        });

      } else if (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard') {
        console.log('🏆 Leaderboard query execution:', queryState);

        const currentYear = new Date().getFullYear();
        const queryYear = queryState.specificYear || currentYear;
        const min_pa = queryYear === 2025 ? 280 : 350;
        const min_ip = queryYear === 2025 ? 70 : 100;

        const leaderboardParams = queryState.category.id === 'batting_leaderboard'
          ? { season: queryYear, league: queryState.league || 'MLB', metric_order: queryState.metricOrder, min_pa }
          : { season: queryYear, league: queryState.league || 'MLB', metric_order: queryState.metricOrder, min_ip };

        console.log('🏆 Leaderboard API params:', leaderboardParams);

        const backendURL = getBackendURL();
        const endpoint = queryState.category.id === 'batting_leaderboard'
          ? `${backendURL}/api/v1/leaderboards/batting`
          : `${backendURL}/api/v1/leaderboards/pitching`;

        const fullUrl = `${endpoint}?${new URLSearchParams(leaderboardParams).toString()}`;
        console.log('🔗 Leaderboard API URL:', fullUrl);

        const headers = await getAuthHeaders();
        const apiResponse = await fetch(fullUrl, { headers });
        if (!apiResponse.ok) throw new Error(`Leaderboard API call failed: ${apiResponse.status} ${apiResponse.statusText}`);

        const leaderboardData = await apiResponse.json();
        console.log('📊 Leaderboard API response:', leaderboardData);

        response = {
          isLeaderboard: true,
          leaderboardData,
          data: leaderboardData,
          answer: `${queryState.category.name}（${queryYear}年シーズン、${queryState.league}、${queryState.metricOrder}でソート）`,
          query: `${queryState.category.name} - ${queryYear}年 ${queryState.league} (最小打席数: ${min_pa})`,
        };

      } else if (!response) {
        console.log('⚠️ Category not implemented yet, using mock data:', queryState.category.id);

        const mockDataGenerators = {
          season_batting: () => ({
            answer: `${queryState.player?.name || '選手'}の${params.season || 2024}年シーズン打撃成績を表示します。（バックエンド実装予定）`,
            isTable: true,
            tableData: [
              { metric: '打率', value: (Math.random() * 0.200 + 0.200).toFixed(3), rank: Math.floor(Math.random() * 10) + 1 },
              { metric: 'ホームラン', value: Math.floor(Math.random() * 30) + 10, rank: Math.floor(Math.random() * 15) + 1 },
              { metric: 'RBI', value: Math.floor(Math.random() * 60) + 40, rank: Math.floor(Math.random() * 20) + 1 },
            ],
            columns: [{ key: 'metric', label: '指標' }, { key: 'value', label: '値' }, { key: 'rank', label: 'リーグ順位' }],
          }),
          season_pitching: () => ({
            answer: `${queryState.player?.name || '選手'}の${params.season || 2024}年シーズン投手成績を表示します。（バックエンド実装予定）`,
            isTable: true,
            tableData: [
              { metric: '防御率', value: (Math.random() * 2.0 + 2.0).toFixed(2), rank: Math.floor(Math.random() * 15) + 1 },
              { metric: '奪三振', value: Math.floor(Math.random() * 100) + 150, rank: Math.floor(Math.random() * 10) + 1 },
              { metric: 'WHIP', value: (Math.random() * 0.5 + 1.0).toFixed(2), rank: Math.floor(Math.random() * 20) + 1 },
            ],
            columns: [{ key: 'metric', label: '指標' }, { key: 'value', label: '値' }, { key: 'rank', label: 'リーグ順位' }],
          }),
          team_comparison: () => ({
            answer: 'チーム比較データを表示します。（バックエンド実装予定）',
            isChart: true, chartType: 'bar',
            chartData: [
              { team: 'LAA', value: Math.random() * 50 + 70 }, { team: 'NYY', value: Math.random() * 50 + 80 },
              { team: 'HOU', value: Math.random() * 50 + 85 }, { team: 'LAD', value: Math.random() * 50 + 90 },
              { team: 'TB', value: Math.random() * 50 + 75 },
            ],
            chartConfig: { title: `${params.season || 2024}年 チーム成績比較 (サンプルデータ)`, xAxis: 'team', dataKey: 'value', lineColor: '#EF4444', lineName: primaryMetric || 'チーム成績', yDomain: [0, 150] },
          }),
          career_stats: () => ({
            answer: `${queryState.player?.name || '選手'}の通算成績推移を表示します。（バックエンド実装予定）`,
            isChart: true, chartType: 'line',
            chartData: Array.from({ length: 8 }, (_, i) => ({ year: `${2017 + i}`, value: Math.random() * 0.150 + 0.200 })),
            chartConfig: { title: `${queryState.player?.name || '選手'} 通算成績推移 (サンプルデータ)`, xAxis: 'year', dataKey: 'value', lineColor: '#10B981', lineName: primaryMetric || 'キャリア成績', yDomain: [0, 0.400] },
          }),
        };

        const generator = mockDataGenerators[queryState.category.id] || mockDataGenerators.season_batting;
        response = { isTable: false, isChart: false, ...generator() };
      }

      console.log('🔍 Custom Query API Response:', response);

      setCustomResult({
        query: generateSummaryText(queryState),
        queryState,
        answer: response.answer,
        stats: response.stats,
        isTable: response.isTable || false,
        isTransposed: response.isTransposed || false,
        tableData: response.tableData || null,
        columns: response.columns || null,
        decimalColumns: response.decimalColumns || [],
        grouping: response.grouping || null,
        isChart: response.isChart || false,
        chartType: response.chartType || null,
        chartData: response.chartData || null,
        chartConfig: response.chartConfig || null,
        isCards: response.isCards || false,
        isMultiChart: response.isMultiChart || false,
        charts: response.charts || null,
        cardsData: response.cardsData || null,
        isLeaderboard: response.isLeaderboard || false,
        data: response.data || null,
        leaderboardData: response.leaderboardData || null,
        timestamp: new Date(),
      });

    } catch (error) {
      console.error('❌ Custom Query Error:', error);

      const isLeaderboard = queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard';
      const errorSummary = isLeaderboard
        ? `${CATEGORY_NAMES[queryState.category.id]}クエリでエラーが発生`
        : `${queryState.player?.name || '選手'}の${CATEGORY_NAMES[queryState.category.id]}クエリでエラーが発生`;

      setCustomResult({
        query: errorSummary,
        queryState,
        answer: 'エラーが発生しました。しばらく後でもう一度お試しください。',
        isChart: false,
        isTable: false,
        timestamp: new Date(),
      });
    }

    setIsLoading(false);
  };

  return { customResult, setCustomResult, handleCustomQuery };
};
