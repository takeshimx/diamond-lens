import React, { useState, useRef, useEffect } from 'react';
import { Send, TrendingUp, User, Bot, Activity, MessageCircle, Zap, Settings, Users, AlertTriangle, Brain, Target } from 'lucide-react';
import SimpleChatChart from './components/ChatChart.jsx';
import QuickQuestions from './components/QuickQuestions.jsx';
import CustomQueryBuilder from './components/CustomQueryBuilder.jsx';
import StatisticalAnalysis from './components/StatisticalAnalysis.jsx';
import PlayerSegmentation from './components/PlayerSegmentation.jsx';
import PitcherFatigue from './components/PitcherFatigue.jsx';
import PitcherWhiffPredictor from './components/PitcherWhiffPredictor.jsx';

// Force dark mode on app load
const initializeDarkMode = () => {
  document.documentElement.classList.add('dark');
};



const MLBChatApp = () => {
  // Initialize dark mode on component mount
  useEffect(() => {
    initializeDarkMode();
  }, []);

  // ===== STATE管理 =====
  // チャット履歴を管理するstate - 各メッセージにはid, type(user/bot), content, timestampが含まれる
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'こんにちは！MLBスタッツについて何でも聞いてください。選手の成績、チーム統計、歴史的データなど、お答えします！',
      timestamp: new Date()
    }
  ]);
  
  // 現在の入力テキストを管理するstate
  const [inputMessage, setInputMessage] = useState('');
  
  // API呼び出し中のローディング状態を管理するstate
  const [isLoading, setIsLoading] = useState(false);
  
  // メッセージエリアの最下部への自動スクロール用のref
  const messagesEndRef = useRef(null);

  // 認証関連のstate
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isCheckingAuth, setIsCheckingAuth] = useState(false);

  // UIモード管理のstate
  const [uiMode, setUiMode] = useState('chat'); // 'chat', 'quick', 'custom', 'statistics', 'segmentation', 'fatigue', 'pitcher-whiff'
  
  // Quick Questions result state
  const [quickResult, setQuickResult] = useState(null);
  
  // Custom Query result state
  const [customResult, setCustomResult] = useState(null);

  // 重要: 簡易的なパスワード認証用（本番では安全な方法を使用）
  const CORRECT_PASSWORD = (import.meta.env.VITE_APP_PASSWORD || 'defaultpassword').trim();

  // ===== ユーティリティ関数 =====
  // メッセージエリアの最下部に自動スクロールする関数
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // メッセージが更新されるたびに最下部にスクロール
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ===== API呼び出し関数 =====

  // Environment-aware backend URL detection (shared function)
  const getBackendURL = () => {
    console.log('🔍 デバッグ：getBackendURL called');
    console.log('🔍 デバッグ：window.location.hostname:', window.location.hostname);
    
    // Cloud Run environment detection
    if (window.location.hostname.includes('run.app')) {
      const backendURL = 'https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app';
      console.log('🔄 デバッグ：Cloud Run environment detected, using backend URL:', backendURL);
      return backendURL;
    }
    
    // GitHub Codespaces environment detection
    if (window.location.hostname.includes('github.dev')) {
      const frontendHostname = window.location.hostname;
      console.log('🔍 デバッグ：Codespaces environment, original frontend hostname:', frontendHostname);
      
      // 複数の方法を試す
      const method1 = frontendHostname.replace('-5173.app.github.dev', '-8000.app.github.dev');
      const method2 = frontendHostname.replace(/5173/g, '8000');
      
      console.log('🔍 デバッグ：Method 1 result:', method1);
      console.log('🔍 デバッグ：Method 2 result:', method2);
      
      const backendHostname = method1;
      const backendURL = `https://${backendHostname}`;
      
      console.log('🔄 デバッグ：Final backend URL:', backendURL);
      return backendURL;
    }
    
    console.log('🔍 デバッグ：Using localhost fallback');
    return 'http://localhost:8000';
  };

  // Function to search players
  const searchPlayers = async (searchTerm) => {
    console.log('🚀 選手検索API呼び出し開始:', searchTerm);

    const baseURL = getBackendURL();
    const endpoint = `${baseURL}/api/v1/players/search?q=${encodeURIComponent(searchTerm)}`;

    try {
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data.results || [];
    } catch (error) {
      console.error('🚀 選手検索API呼び出しエラー:', error);
      return [];
    }
  };




  // バックエンドAPIを呼び出してMLBデータとGemini回答を取得する関数
  const callBackendAPI = async (query) => {
    console.log('🚀 デバッグ：API呼び出し開始:', query);

    console.log('🌐 デバッグ：Current location:', {
      hostname: window.location.hostname,
      origin: window.location.origin,
      isCodespaces: window.location.hostname.includes('github.dev')
    });

    try {
      const baseURL = getBackendURL();
      console.log('🎯 デバッグ：Final baseURL from getBackendURL():', baseURL);
      
      const endpoint = `${baseURL}/api/v1/qa/player-stats`;
      console.log('🎯 デバッグ：Final complete endpoint:', endpoint);
      
      const requestBody = {
        query: query,
        season: 2024
      };
      
      console.log('📤 デバッグ：Sending request to:', endpoint);
      console.log('📤 デバッグ：Request body:', JSON.stringify(requestBody, null, 2));
      
      // タイムアウトを設定（60秒）
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log('⏰ デバッグ：リクエストタイムアウト（60秒）');
        controller.abort();
      }, 60000);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      
      console.log('📥 デバッグ：Response received:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        url: response.url
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      console.log('📋 デバッグ：Content-Type:', contentType);
      
      let apiResponse;
      
      if (contentType && contentType.includes('application/json')) {
        apiResponse = await response.json();
        console.log('🔍 デバッグ：JSON レスポンス:', apiResponse);
        console.log('🔍 デバッグ：Chart fields in JSON response:', {
          isChart: apiResponse.isChart,
          chartType: apiResponse.chartType,
          hasChartData: !!apiResponse.chartData,
          hasChartConfig: !!apiResponse.chartConfig,
          chartDataLength: apiResponse.chartData ? apiResponse.chartData.length : 0
        });
      } else {
        const textResponse = await response.text();
        console.log('📝 デバッグ：テキスト レスポンス:', textResponse.substring(0, 200) + '...');
        apiResponse = { answer: textResponse, isTable: false };
      }

      console.log('✅ デバッグ：API呼び出し成功');
      
      return {
        answer: apiResponse.answer || "回答を受信しましたが、内容が空でした。",
        isTable: apiResponse.isTable || false,
        isTransposed: apiResponse.isTransposed || false,
        tableData: apiResponse.tableData || null,
        columns: apiResponse.columns || null,
        decimalColumns: apiResponse.decimalColumns || [],
        grouping: apiResponse.grouping || null,
        stats: apiResponse.stats || null,
        // Chart fields
        isChart: apiResponse.isChart || false,
        chartType: apiResponse.chartType || null,
        chartData: apiResponse.chartData || null,
        chartConfig: apiResponse.chartConfig || null
      };

    } catch (error) {
      console.error('❌ デバッグ：API呼び出しエラー:', error);
      
      if (error.name === 'AbortError') {
        return {
          answer: 'リクエストがタイムアウトしました（60秒）。バックエンドの処理が重い可能性があります。',
          isTable: false,
          isTransposed: false,
          tableData: null,
          columns: null,
          decimalColumns: [],
          grouping: null,
          stats: null,
          isChart: false,
          chartType: null,
          chartData: null,
          chartConfig: null
        };
      }
      
      return {
        answer: `エラーが発生しました: ${error.message}`,
        isTable: false,
        isTransposed: false,
        tableData: null,
        columns: null,
        decimalColumns: [],
        grouping: null,
        stats: null,
        isChart: false,
        chartType: null,
        chartData: null,
        chartConfig: null
      };
    }
  };

  // ===== 固定クエリ用API呼び出し関数 =====
  // 事前定義されたクエリのためのパフォーマンスアナリティクスエンドポイントを呼び出す
  const callFixedQueryAPI = async (questionParams) => {
    console.log('🚀 デバッグ：固定クエリ API呼び出し開始:', questionParams);

    try {
      const baseURL = getBackendURL();
      console.log('🎯 デバッグ：Fixed Query baseURL:', baseURL);
      
      // Build endpoint based on query type
      let endpoint;
      if (questionParams.queryType === 'season_batting_stats') {
        // Endpoint for batting stats - handles both single season (KPI cards) and all seasons (trend chart)
        const seasonParam = questionParams.season ? `season=${questionParams.season}&` : '';
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/season-batting-stats?${seasonParam}metrics=${questionParams.metrics || questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_batting_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/monthly-batting-stats?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_offensive_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/monthly-offensive-stats?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_risp_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/performance-at-risp?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'season_pitching_stats') {
        // Endpoint for pitching stats - handles both single season (KPI cards) and all seasons (trend chart)
        const seasonParam = questionParams.season ? `season=${questionParams.season}&` : '';
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/season-pitching-stats?${seasonParam}metrics=${questionParams.metrics || questionParams.metric}`;
      } else if (questionParams.queryType === 'season_batting_splits') {
        // Endpoint for batting splits stats
        const seasonParam = questionParams.season ? `season=${questionParams.season}&` : '';
        const metricsParams = Array.isArray(questionParams.metrics) 
          ? questionParams.metrics.map(m => `metrics=${m}`).join('&')
          : `metrics=${questionParams.metrics}`;
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/season-batting-splits?${seasonParam}split_type=${questionParams.split_type}&${metricsParams}`;
      } else {
        throw new Error(`Unsupported query type: ${questionParams.queryType}`);
      }
      
      console.log('🎯 デバッグ：Fixed Query endpoint:', endpoint);
      
      // Timeout setup
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log('⏰ デバッグ：リクエストタイムアウト（60秒）');
        controller.abort();
      }, 60000);

      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      
      console.log('📥 デバッグ：Fixed Query response received:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        url: response.url
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      // Handle different response types
      let apiResponse;
      if (response.ok) {
        apiResponse = await response.json();
        console.log('🔍 デバッグ：Fixed Query JSON response:', apiResponse);
        
        // Check if we got valid data and handle different query types
        if (questionParams.queryType === 'season_batting_stats') {
          if (apiResponse && (Array.isArray(apiResponse) ? apiResponse.length > 0 : typeof apiResponse === 'object')) {
            
            console.log('🔍 Debug - Season batting stats response:', apiResponse);
            console.log('🔍 Debug - Season parameter:', questionParams.season);
            
            // Determine if this is single season (KPI cards) or multi-season (trend chart)
            const isMultiSeason = questionParams.season === null || questionParams.season === undefined;
            const dataArray = Array.isArray(apiResponse) ? apiResponse : [apiResponse];
            const playerName = dataArray[0].name || dataArray[0].player_name || dataArray[0].batter_name || 'Selected Player';
            
            if (isMultiSeason && dataArray.length > 1) {
              // Multi-season data - create trend chart
              console.log('🔍 Debug - Creating trend chart for multi-season data');
              
              // Use the primary metric for the chart
              const primaryMetric = Array.isArray(questionParams.metrics) 
                ? questionParams.metrics[0] 
                : questionParams.metrics;
                
              const chartData = dataArray.map(item => ({
                year: item.season?.toString() || 'Unknown',
                value: item[primaryMetric] || 0
              })).filter(item => item.value !== null && item.value !== undefined);
              
              // Determine chart type based on metric
              const rateMetrics = ['avg', 'obp', 'slg', 'ops', 'woba', 'babip', 'iso'];
              const chartType = rateMetrics.includes(primaryMetric) ? 'line' : 'bar';
              
              const metricDisplayNames = {
                'avg': '打率', 'obp': '出塁率', 'slg': '長打率', 'ops': 'OPS',
                'h': '安打数', 'hr': '本塁打', 'homeruns': 'ホームラン', 'doubles': '二塁打', 'triples': '三塁打',
                'singles': '単打', 'rbi': '打点', 'r': '得点', 'bb': '四球',
                'so': '三振', 'war': 'fWAR', 'woba': 'wOBA', 'wrcplus': 'wRC+'
              };
              
              return {
                answer: `${playerName}選手の通算成績推移（${metricDisplayNames[primaryMetric] || primaryMetric}）を表示します。`,
                isChart: true,
                chartType: chartType,
                chartData: chartData,
                chartConfig: {
                  title: `${playerName} - ${metricDisplayNames[primaryMetric] || primaryMetric} 年度別推移`,
                  xAxis: 'year',
                  dataKey: 'value',
                  lineColor: rateMetrics.includes(primaryMetric) ? '#3B82F6' : '#10B981',
                  lineName: metricDisplayNames[primaryMetric] || primaryMetric,
                  yDomain: rateMetrics.includes(primaryMetric) ? [0, 'dataMax'] : [0, 'dataMax']
                },
                isTable: false,
                isCards: false
              };
              
            } else {
              // Single season data - create KPI cards
              console.log('🔍 Debug - Creating KPI cards for single season data');
              
              const data = dataArray[0];
              const season = data.season || questionParams.season;
              
              const createKPICards = (data, metrics, season, playerName) => {
                const cards = [];
                const metricsArray = typeof metrics === 'string' ? [metrics] : (metrics || []);
                
                metricsArray.forEach(metricKey => {
                  const value = data[metricKey];
                  if (value !== undefined && value !== null) {
                    cards.push({
                      metric: metricKey,
                      value: value,
                      playerName: playerName,
                      season: season
                    });
                  }
                });
                
                return cards;
              };
              
              const kpiCards = createKPICards(
                data, 
                questionParams.metrics || [questionParams.metric], 
                season, 
                playerName
              );
              
              return {
                answer: `${playerName}選手の${season}年シーズン成績をKPIカードで表示します。`,
                isCards: true,
                cardsData: kpiCards,
                isTable: false,
                isChart: false
              };
            }
          } else {
            // No data found for season batting stats
            console.log('⚠️ デバッグ：No season batting stats data found');
            return {
              answer: 'シーズン打撃成績データが見つかりませんでした。',
              isTable: false,
              isChart: false,
              isCards: false
            };
          }
        } else if (questionParams.queryType === 'season_batting_splits') {
          if (apiResponse && Array.isArray(apiResponse) && apiResponse.length > 0) {
            const data = apiResponse[0];
            const playerName = data.batter_name || data.player_name || 'Selected Player';
            const season = data.game_year || questionParams.season || 2024;
            
            const createKPICards = (data, metrics, season, playerName) => {
              const cards = [];
              const metricsArray = typeof metrics === 'string' ? [metrics] : (metrics || []);
              
              metricsArray.forEach(metricKey => {
                const value = data[metricKey];
                if (value !== undefined && value !== null) {
                  cards.push({
                    metric: metricKey,
                    value: value,
                    playerName: playerName,
                    season: season
                  });
                }
              });
              
              return cards;
            };
            
            const kpiCards = createKPICards(
              data, 
              questionParams.metrics, 
              season, 
              playerName
            );
            
            return {
              answer: `${playerName}選手の${season}年場面別成績をKPIカードで表示します。`,
              isCards: true,
              cardsData: kpiCards,
              isTable: false,
              isChart: false
            };
          }
        } else if (questionParams.queryType === 'season_pitching_stats') {
          // Handle season pitching stats - same logic as batting but for pitching
          if (apiResponse && (Array.isArray(apiResponse) ? apiResponse.length > 0 : typeof apiResponse === 'object')) {
            
            console.log('🔍 Debug - Season pitching stats response:', apiResponse);
            console.log('🔍 Debug - Season parameter:', questionParams.season);
            
            // Determine if this is single season (KPI cards) or multi-season (trend chart)
            const isMultiSeason = questionParams.season === null || questionParams.season === undefined;
            const dataArray = Array.isArray(apiResponse) ? apiResponse : [apiResponse];
            const playerName = dataArray[0].name || dataArray[0].player_name || dataArray[0].pitcher_name || 'Selected Player';
            
            if (isMultiSeason && dataArray.length > 1) {
              // Multi-season data - create trend chart
              console.log('🔍 Debug - Creating trend chart for multi-season pitching data');
              
              // Use the primary metric for the chart
              const primaryMetric = Array.isArray(questionParams.metrics) 
                ? questionParams.metrics[0] 
                : questionParams.metrics;
                
              const chartData = dataArray.map(item => ({
                year: item.season?.toString() || 'Unknown',
                value: item[primaryMetric] || 0
              })).filter(item => item.value !== null && item.value !== undefined);
              
              // Determine chart type - pitching metrics are generally better as line charts
              const chartType = 'line';
              
              const metricDisplayNames = {
                'era': '防御率', 'whip': 'WHIP', 'so': '三振数', 'bb': '四球数',
                'w': '勝利数', 'l': '敗戦数', 'sv': 'セーブ数', 'fip': 'FIP',
                'war': 'fWAR', 'k_9': 'K/9', 'bb_9': 'BB/9', 'hr': '被本塁打',
                'ip': '投球回', 'g': '登板数', 'gs': '先発数'
              };
              
              return {
                answer: `${playerName}選手の通算投球成績推移（${metricDisplayNames[primaryMetric] || primaryMetric}）を表示します。`,
                isChart: true,
                chartType: chartType,
                chartData: chartData,
                chartConfig: {
                  title: `${playerName} - ${metricDisplayNames[primaryMetric] || primaryMetric} 年度別推移`,
                  xAxis: 'year',
                  dataKey: 'value',
                  lineColor: '#EF4444',
                  lineName: metricDisplayNames[primaryMetric] || primaryMetric,
                  yDomain: [0, 'dataMax']
                },
                isTable: false,
                isCards: false
              };
              
            } else {
              // Single season data - create KPI cards
              console.log('🔍 Debug - Creating KPI cards for single season pitching data');
              
              const data = dataArray[0];
              const season = data.season || questionParams.season;
              
              const createKPICards = (data, metrics, season, playerName) => {
                const cards = [];
                const metricsArray = typeof metrics === 'string' ? [metrics] : (metrics || []);
                
                metricsArray.forEach(metricKey => {
                  const value = data[metricKey];
                  if (value !== undefined && value !== null) {
                    cards.push({
                      metric: metricKey,
                      value: value,
                      playerName: playerName,
                      season: season
                    });
                  }
                });
                
                return cards;
              };
              
              const kpiCards = createKPICards(
                data, 
                questionParams.metrics || [questionParams.metric], 
                season, 
                playerName
              );
              
              return {
                answer: `${playerName}選手の${season}年シーズン投球成績をKPIカードで表示します。`,
                isCards: true,
                cardsData: kpiCards,
                isTable: false,
                isChart: false
              };
            }
          } else {
            // No data found for season pitching stats
            console.log('⚠️ デバッグ：No season pitching stats data found');
            return {
              answer: 'シーズン投球成績データが見つかりませんでした。',
              isTable: false,
              isChart: false,
              isCards: false
            };
          }
        } else if (Array.isArray(apiResponse) && apiResponse.length > 0) {
          // Transform the response to chart format (for monthly data)
          // Use the actual metric field instead of metric_value
          const metricField = questionParams.metric; // e.g., 'avg', 'homeruns', etc.
          const playerName = apiResponse[0].batter_name || 'Selected Player';
          console.log('🔍 Debug - Metric field:', metricField);
          console.log('🔍 Debug - Player name:', playerName);
          console.log('🔍 Debug - Sample item:', apiResponse[0]);
          console.log('🔍 Debug - Sample metric value:', apiResponse[0][metricField]);
          
          // Create chart data with dynamic data key based on metric
          const chartData = apiResponse.map(item => ({
            month: `${item.game_month}月`,
            value: item[metricField] || 0  // Use 'value' as consistent data key
          }));
          
          console.log('🔍 Debug - Chart data:', chartData);
          
          // Generate dynamic chart configuration based on metric
          const getChartConfig = (metric, season, playerName) => {
            const configs = {
              // Rate stats (line charts)
              'avg': {
                title: `${playerName} ${season}年月別打率推移`,
                yAxisLabel: '打率',
                yDomain: [0, 0.500],
                lineColor: '#3B82F6',
                chartType: 'line'
              },
              'batting_average': {
                title: `${playerName} ${season}年月別打率推移`,
                yAxisLabel: '打率',
                yDomain: [0, 0.500],
                lineColor: '#3B82F6',
                chartType: 'line'
              },
              'obp': {
                title: `${playerName} ${season}年月別出塁率推移`,
                yAxisLabel: '出塁率',
                yDomain: [0, 0.500],
                lineColor: '#10B981',
                chartType: 'line'
              },
              'slg': {
                title: `${playerName} ${season}年月別長打率推移`,
                yAxisLabel: '長打率',
                yDomain: [0, 0.800],
                lineColor: '#F59E0B',
                chartType: 'line'
              },
              'ops': {
                title: `${playerName} ${season}年月別OPS推移`,
                yAxisLabel: 'OPS',
                yDomain: [0, 1.500],
                lineColor: '#8B5CF6',
                chartType: 'line'
              },
              'woba': {
                title: `${playerName} ${season}年月別wOBA推移`,
                yAxisLabel: 'wOBA',
                yDomain: [0, 0.500],
                lineColor: '#EC4899',
                chartType: 'line'
              },
              'war': {
                title: `${playerName} ${season}年月別WAR推移`,
                yAxisLabel: 'WAR',
                yDomain: [-1, 4],
                lineColor: '#6366F1',
                chartType: 'line'
              },
              'wrc_plus': {
                title: `${playerName} ${season}年月別wRC+推移`,
                yAxisLabel: 'wRC+',
                yDomain: [0, 200],
                lineColor: '#DC2626',
                chartType: 'line'
              },
              
              // Counting stats (bar charts)
              'hits': {
                title: `${playerName} ${season}年月別安打数`,
                yAxisLabel: '安打数',
                yDomain: [0, 50],
                lineColor: '#10B981',
                chartType: 'bar'
              },
              'homeruns': {
                title: `${playerName} ${season}年月別ホームラン数`,
                yAxisLabel: 'ホームラン数',
                yDomain: [0, 15],
                lineColor: '#EF4444',
                chartType: 'bar'
              },
              'home_runs': {
                title: `${playerName} ${season}年月別ホームラン数`,
                yAxisLabel: 'ホームラン数', 
                yDomain: [0, 15],
                lineColor: '#EF4444',
                chartType: 'bar'
              },
              'doubles': {
                title: `${playerName} ${season}年月別二塁打数`,
                yAxisLabel: '二塁打数',
                yDomain: [0, 12],
                lineColor: '#F59E0B',
                chartType: 'bar'
              },
              'triples': {
                title: `${playerName} ${season}年月別三塁打数`,
                yAxisLabel: '三塁打数',
                yDomain: [0, 5],
                lineColor: '#8B5CF6',
                chartType: 'bar'
              },
              'singles': {
                title: `${playerName} ${season}年月別単打数`,
                yAxisLabel: '単打数',
                yDomain: [0, 40],
                lineColor: '#06B6D4',
                chartType: 'bar'
              },
              'rbi': {
                title: `${playerName} ${season}年月別打点数`,
                yAxisLabel: '打点数',
                yDomain: [0, 30],
                lineColor: '#DC2626',
                chartType: 'bar'
              },
              'runs': {
                title: `${playerName} ${season}年月別得点数`,
                yAxisLabel: '得点数',
                yDomain: [0, 30],
                lineColor: '#059669',
                chartType: 'bar'
              },
              'walks': {
                title: `${playerName} ${season}年月別四球数`,
                yAxisLabel: '四球数',
                yDomain: [0, 25],
                lineColor: '#7C3AED',
                chartType: 'bar'
              },
              'strikeouts': {
                title: `${playerName} ${season}年月別三振数`,
                yAxisLabel: '三振数',
                yDomain: [0, 40],
                lineColor: '#DC2626',
                chartType: 'bar'
              },
              
              // Rate percentage stats (line charts)
              'hard_hit_rate': {
                title: `${playerName} ${season}年月別ハードヒット率推移`,
                yAxisLabel: 'ハードヒット率',
                yDomain: [0, 1],
                lineColor: '#F59E0B',
                chartType: 'line'
              },
              'barrels_rate': {
                title: `${playerName} ${season}年月別バレル率推移`,
                yAxisLabel: 'バレル率',
                yDomain: [0, 1],
                lineColor: '#10B981',
                chartType: 'line'
              },
              'walk_rate': {
                title: `${playerName} ${season}年月別四球率推移`,
                yAxisLabel: '四球率 (%)',
                yDomain: [0, 25],
                lineColor: '#7C3AED',
                chartType: 'line'
              },
              'strikeout_rate': {
                title: `${playerName} ${season}年月別三振率推移`,
                yAxisLabel: '三振率',
                yDomain: [0, 1],
                lineColor: '#DC2626',
                chartType: 'line'
              },
              'swing_rate': {
                title: `${playerName} ${season}年月別スイング率推移`,
                yAxisLabel: 'スイング率 (%)',
                yDomain: [0, 100],
                lineColor: '#F59E0B',
                chartType: 'line'
              },
              'contact_rate': {
                title: `${playerName} ${season}年月別コンタクト率推移`,
                yAxisLabel: 'コンタクト率 (%)',
                yDomain: [0, 100],
                lineColor: '#10B981',
                chartType: 'line'
              },
              
              // Legacy/other stats
              'batting_average_at_risp': {
                title: `${playerName} ${season}年月別RISP打率推移`,
                yAxisLabel: 'RISP打率',
                yDomain: [0, 0.600],
                lineColor: '#10B981',
                chartType: 'line'
              }
            };
            
            const config = configs[metric] || configs['avg'];
            
            return {
              title: config.title,
              xAxis: 'month',
              dataKey: 'value', // Use consistent 'value' data key
              lineColor: config.lineColor,
              lineName: config.yAxisLabel,
              yDomain: config.yDomain,
              chartType: config.chartType
            };
          };
          
          const chartConfig = getChartConfig(questionParams.metric, questionParams.season, playerName);
          
          console.log('✅ デバッグ：Fixed Query API呼び出し成功');
          
          // Generate dynamic answer text
          const getAnswerText = (metric, season, playerName) => {
            const texts = {
              // Rate stats
              'avg': `${playerName}選手の${season}年月別打率推移をチャートで表示します。`,
              'batting_average': `${playerName}選手の${season}年月別打率推移をチャートで表示します。`,
              'obp': `${playerName}選手の${season}年月別出塁率推移をチャートで表示します。`,
              'slg': `${playerName}選手の${season}年月別長打率推移をチャートで表示します。`,
              'ops': `${playerName}選手の${season}年月別OPS推移をチャートで表示します。`,
              
              // Counting stats
              'hits': `${playerName}選手の${season}年月別安打数をチャートで表示します。`,
              'homeruns': `${playerName}選手の${season}年月別ホームラン数をチャートで表示します。`,
              'home_runs': `${playerName}選手の${season}年月別ホームラン数をチャートで表示します。`,
              'doubles': `${playerName}選手の${season}年月別二塁打数をチャートで表示します。`,
              'triples': `${playerName}選手の${season}年月別三塁打数をチャートで表示します。`,
              'singles': `${playerName}選手の${season}年月別単打数をチャートで表示します。`,
              'rbi': `${playerName}選手の${season}年月別打点数をチャートで表示します。`,
              'runs': `${playerName}選手の${season}年月別得点数をチャートで表示します。`,
              'walks': `${playerName}選手の${season}年月別四球数をチャートで表示します。`,
              'strikeouts': `${playerName}選手の${season}年月別三振数をチャートで表示します。`,
              
              // Rate percentage stats  
              'hard_hit_rate': `${playerName}選手の${season}年月別ハードヒット率推移をチャートで表示します。`,
              'barrels_rate': `${playerName}選手の${season}年月別バレル率推移をチャートで表示します。`,
              'walk_rate': `${playerName}選手の${season}年月別四球率推移をチャートで表示します。`,
              'strikeout_rate': `${playerName}選手の${season}年月別三振率推移をチャートで表示します。`,
              'swing_rate': `${playerName}選手の${season}年月別スイング率推移をチャートで表示します。`,
              'contact_rate': `${playerName}選手の${season}年月別コンタクト率推移をチャートで表示します。`,
              
              // Legacy/other stats
              'batting_average_at_risp': `${playerName}選手の${season}年月別RISP打率推移をチャートで表示します。`
            };
            return texts[metric] || texts['avg'];
          };
          
          return {
            answer: getAnswerText(questionParams.metric, questionParams.season, playerName),
            isTable: false,
            isTransposed: false,
            tableData: null,
            columns: null,
            decimalColumns: [],
            grouping: null,
            stats: null,
            isChart: true,
            chartType: chartConfig.chartType,
            chartData: chartData,
            chartConfig: chartConfig
          };
        } else {
          // No data found, provide mock data for demonstration
          console.log('⚠️ デバッグ：No data found, using mock data');
          const mockChartData = [
            { month: '3月', batting_average: 0.125 },
            { month: '4月', batting_average: 0.238 },
            { month: '5月', batting_average: 0.278 },
            { month: '6月', batting_average: 0.301 },
            { month: '7月', batting_average: 0.295 },
            { month: '8月', batting_average: 0.264 },
            { month: '9月', batting_average: 0.289 }
          ];
          
          const chartConfig = {
            title: '大谷翔平 2024年月別打率推移 (サンプルデータ)',
            xAxis: 'month',
            dataKey: 'batting_average',
            lineColor: '#3B82F6',
            lineName: '打率',
            yDomain: [0, 0.400]
          };
          
          return {
            answer: `現在データが取得できないため、サンプルデータで大谷翔平選手の月別打率推移を表示しています。`,
            isTable: false,
            isTransposed: false,
            tableData: null,
            columns: null,
            decimalColumns: [],
            grouping: null,
            stats: null,
            isChart: true,
            chartType: 'line',
            chartData: mockChartData,
            chartConfig: chartConfig
          };
        }
      }

    } catch (error) {
      console.error('❌ デバッグ：Fixed Query API呼び出しエラー:', error);
      
      if (error.name === 'AbortError') {
        return {
          answer: 'リクエストがタイムアウトしました（60秒）。バックエンドの処理が重い可能性があります。',
          isTable: false,
          isChart: false
        };
      }
      
      return {
        answer: `エラーが発生しました: ${error.message}`,
        isTable: false,
        isChart: false
      };
    }
  };


  // 認証関連の処理
  const handleAuthentication = async () => {
    if (!password.trim()) return;

    setIsCheckingAuth(true);
    setAuthError('');

    // パスワードをチェック
    if (password === CORRECT_PASSWORD) {
      setIsAuthenticated(true);
      // 認証成功時はパスワードをクリア
      setPassword('');
    } else {
      setAuthError('パスワードが正しくありません。もう一度お試しください。');
    }

    setIsCheckingAuth(false);
  }

  // Enterキーで認証処理
  const handleAuthKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAuthentication();
    }
  };

  // ===== メッセージ送信処理 =====
  const handleSendMessage = async () => {
    // 入力が空またはローディング中の場合は処理を停止
    if (!inputMessage.trim() || isLoading) return;

    // ユーザーのメッセージオブジェクトを作成
    const userMessage = {
      id: Date.now(), // 簡易的なユニークID生成
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    // メッセージ履歴にユーザーメッセージを追加
    setMessages(prev => [...prev, userMessage]);
    // 入力フィールドをクリア
    setInputMessage('');
    // ローディング状態を開始
    setIsLoading(true);

    try {
      // バックエンドAPIを呼び出してレスポンスを取得
      const response = await callBackendAPI(inputMessage);
      
      // Debug: Log the API response
      console.log('🔍 API Response:', response);
      console.log('🔍 Chart flags:', {
        isChart: response.isChart,
        hasChartData: !!response.chartData,
        hasChartConfig: !!response.chartConfig,
        chartType: response.chartType
      });

      // ボットの回答メッセージオブジェクトを作成
      const botMessage = {
        id: Date.now() + 1, // ユーザーメッセージとの重複を避けるため+1
        type: 'bot',
        content: response.answer, // Gemini APIからの回答テキスト
        stats: response.stats, // BigQueryからの統計データ
        isTable: response.isTable, // テーブル表示フラグ
        isTransposed: response.isTransposed, // テーブル転置フラグ
        tableData: response.tableData, // テーブルデータ
        columns: response.columns, // テーブルカラム定義
        decimalColumns: response.decimalColumns, // 小数点表示カラムリスト
        grouping: response.grouping, // グループ分け情報
        isChart: response.isChart, // チャート表示フラグ
        chartType: response.chartType, // チャートタイプ
        chartData: response.chartData, // チャートデータ
        chartConfig: response.chartConfig, // チャート設定
        timestamp: new Date()
      };

      // Debug: Log the message object
      console.log('🔍 Bot Message:', botMessage);
      console.log('🔍 Bot Message Chart Fields:', {
        isChart: botMessage.isChart,
        chartType: botMessage.chartType,
        hasChartData: !!botMessage.chartData,
        hasChartConfig: !!botMessage.chartConfig
      });

      // メッセージ履歴にボットメッセージを追加
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('❌ Chat API Error:', error);
      // エラーが発生した場合のエラーメッセージを作成
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: 'エラーが発生しました。しばらく後でもう一度お試しください。',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }

    // ローディング状態を終了
    setIsLoading(false);
  };

  // ===== クイック質問処理 =====
  const handleQuickQuestion = async (question) => {
    console.log('🚀 Quick Question clicked:', question);
    
    // Clear any existing result and start loading
    setQuickResult(null);
    setIsLoading(true);
    
    try {
      // Fixed Query APIを呼び出し
      const response = await callFixedQueryAPI(question.params);
      
      console.log('🔍 Quick Question API Response:', response);
      
      // Store the result for display in Quick Questions section
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
        timestamp: new Date()
      });
      
    } catch (error) {
      console.error('❌ Quick Question Error:', error);
      setQuickResult({
        question: question.title,
        answer: 'エラーが発生しました。しばらく後でもう一度お試しください。',
        isChart: false,
        isTable: false,
        timestamp: new Date()
      });
    }
    
    setIsLoading(false);
  };

  // ===== カスタムクエリ処理 =====
  const handleCustomQuery = async (queryState) => {
    console.log('🚀 Custom Query execution:', queryState);
    
    // Clear any existing result and start loading
    setCustomResult(null);
    setIsLoading(true);
    
    try {
      // Check if this is a leaderboard category (no player selection needed)
      const isLeaderboard = queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard';
      
      // Extract parameters from queryState for direct BigQuery API calls
      const params = {
        playerId: isLeaderboard ? null : (queryState.player?.mlb_id || queryState.player?.id), // Use mlb_id when available
        season: queryState.seasonMode === 'all' ? null : queryState.specificYear,
        metrics: queryState.metrics,
        category: queryState.category.id
      };

      console.log('🔍 Custom Query Params:', params);

      // Determine which endpoint to call based on category and metrics
      let response;
      const primaryMetric = queryState.metrics[0]; // Use first metric for API call

      // Route to appropriate endpoint based on category
      if (queryState.category.id === 'season_batting' && primaryMetric) {
        // Season batting stats - different behavior based on season selection
        const metricMapping = {
          // Direct mapping to backend fields (based on PlayerBattingSeasonStats schema)
          'plate_appearances': 'pa',
          'at_bats': 'ab',
          'games': 'g',
          'batting_average': 'avg',
          'hits': 'h', 
          'home_runs': 'hr',
          'doubles': 'doubles',  // Use Pydantic field name, not alias
          'triples': 'triples',  // Use Pydantic field name, not alias  
          'singles': 'singles',  // Use Pydantic field name, not alias
          'obp': 'obp',
          'slg': 'slg',
          'ops': 'ops',
          'walks': 'bb',
          'rbi': 'rbi',
          'runs': 'r',
          'woba': 'woba',
          'war': 'war',
          'wrc_plus': 'wrcplus',
          'strikeouts': 'so',

          // Advanced metrics (may be added later)
          'babip': 'babip',
          'iso': 'iso',
          'hard_hit_rate': 'hardhitpct',
          'barrels_rate': 'barrelpct',
          'batting_average_at_risp': 'batting_average_at_risp',
          'slugging_percentage_at_risp': 'slugging_percentage_at_risp',
          'home_runs_at_risp': 'home_runs_at_risp',
          'launch_angle': null,
          'exit_velocity': null,
          'walk_rate': null,
          'strikeout_rate': null,
          'swing_rate': null,
          'contact_rate': null
        };
        
        // Map all selected metrics
        const mappedMetrics = queryState.metrics
          .map(metric => {
            const backendMetric = metricMapping[metric];
            if (backendMetric === null) {
              console.warn(`Metric "${metric}" not supported yet`);
              return null;
            }
            if (!backendMetric) {
              console.warn(`Unknown metric: ${metric}`);
              return null;
            }
            return backendMetric;
          })
          .filter(Boolean);
          
        console.log('🔍 Season batting - Frontend metrics:', queryState.metrics, '-> Backend metrics:', mappedMetrics);
        
        if (mappedMetrics.length === 0) {
          throw new Error(`選択された指標はサポートされていません。`);
        }
        
        // Use same endpoint for both single season and all seasons
        const queryParams = {
          playerId: params.playerId,
          season: queryState.seasonMode === 'all' ? null : (params.season || 2024),
          metrics: mappedMetrics,
          queryType: 'season_batting_stats' // Same endpoint handles both cases
        };
        response = await callFixedQueryAPI(queryParams);
        
      } else if (queryState.category.id === 'monthly_trends' && queryState.metrics.length > 0) {
        // Monthly trends - support multiple metrics, create multiple charts
        console.log('🔍 Debug - Monthly trends execution started');
        console.log('🔍 Debug - Selected metrics:', queryState.metrics);

        const metricMapping = {
          // Direct mapping to backend fields
          'monthly_avg': 'avg',
          'monthly_hits': 'hits', 
          'monthly_hr': 'homeruns',
          'monthly_singles': 'singles',
          'monthly_doubles': 'doubles',
          'monthly_triples': 'triples',
          'monthly_obp': 'obp',
          'monthly_slg': 'slg',
          'monthly_ops': 'ops',
          'monthly_bb_hbp': 'bb_hbp',  // walks + HBP combined
          'monthly_rbi': 'rbi',
          'monthly_so': 'so',
          'monthly_hard_hit_rate': 'hard_hit_rate',
          'monthly_barrels_rate': 'barrels_rate',
          'monthly_strikeout_rate': 'strikeout_rate',

          // Metrics not supported by backend yet (will show as unavailable)
          'walk_rate': null,
          'swing_rate': null,
          'contact_rate': null
        };

        // Process all selected metrics
        const chartPromises = [];
        const validMetrics = [];

        for (const metric of queryState.metrics) {
          const backendMetric = metricMapping[metric];
          
          console.log('🔍 Monthly trends - Frontend metric:', metric, '-> Backend metric:', backendMetric);
          
          // Check if metric is supported by backend
          if (backendMetric === null) {
            console.warn(`指標「${metric}」は現在サポートされていません。スキップします。`);
            continue;
          }
          
          if (!backendMetric) {
            console.warn(`未知の指標です: ${metric}。スキップします。`);
            continue;
          }

          validMetrics.push({
            frontendMetric: metric,
            backendMetric: backendMetric
          });

          // Create API call promise for this metric
          const queryParams = {
            playerId: params.playerId,
            season: params.season || 2024,
            metric: backendMetric,
            queryType: 'monthly_batting_stats'
          };
          
          chartPromises.push(
            callFixedQueryAPI(queryParams).then(apiResponse => ({
              metric: metric,
              backendMetric: backendMetric,
              data: apiResponse
            }))
          );
        }

        if (validMetrics.length === 0) {
          throw new Error('選択された指標はいずれもサポートされていません。');
        }

        // Execute all API calls in parallel
        console.log('🔍 Debug - Making parallel API calls, count:', chartPromises.length);
        const chartResults = await Promise.all(chartPromises);
        console.log('🔍 Debug - Chart results received:', chartResults);
        
        // Format response with multiple charts
        response = {
          isMultiChart: true,
          charts: chartResults.map(result => {
            console.log('🔍 Debug - Processing chart result for:', result.metric);
            console.log('🔍 Debug - Result data:', result.data);
            
            // Check if backend already provided chart data (preferred) or if we need to transform raw data
            let chartData = result.data.chartData || [];
            let chartConfig = result.data.chartConfig || {};
            
            // If backend didn't provide chart data, transform raw monthly stats
            if (!result.data.isChart && Array.isArray(result.data) && result.data.length > 0) {
              // Transform monthly data into chart format
              chartData = result.data.map(monthData => ({
                month: monthData.game_month || monthData.month,
                value: monthData[result.backendMetric] || 0,
                year: monthData.game_year || monthData.year || 2024
              })).sort((a, b) => a.month - b.month);
              
              // Create chart config based on metric type
              const playerName = result.data[0]?.batter_name || result.data[0]?.player_name || 'Selected Player';
              const year = result.data[0]?.game_year || 2024;
              
              chartConfig = {
                title: `${playerName} ${year}年 ${result.metric} 月別推移`,
                xAxis: 'month',
                dataKey: 'value',
                lineColor: getMetricColor(result.metric),
                lineName: getMetricDisplayName(result.metric),
                yDomain: [0, 'dataMax']
              };
            }
            
            console.log('🔍 Debug - Final chart data:', chartData);
            console.log('🔍 Debug - Final chart config:', chartConfig);
            
            return {
              metric: result.metric,
              backendMetric: result.backendMetric,
              metricDisplayName: getMetricDisplayName(result.metric),
              isChart: result.data.isChart || chartData.length > 0,
              chartType: result.data.chartType || 'line',
              chartData: chartData,
              chartConfig: chartConfig,
              answer: result.data.answer || `${getMetricDisplayName(result.metric)}の月別推移`
            };
          }),
          answer: `${validMetrics.length}個の指標の月別推移を表示します。`,
          stats: {
            '対象指標数': validMetrics.length,
            '対象シーズン': params.season || 2024
          }
        };
        
        console.log('🔍 Debug - Final response:', response);
        
        // Helper function to get metric color
        function getMetricColor(metric) {
          const colorMap = {
            'monthly_avg': '#3B82F6',
            'monthly_hr': '#EF4444', 
            'monthly_rbi': '#10B981',
            'monthly_ops': '#8B5CF6',
            'monthly_obp': '#F59E0B',
            'monthly_slg': '#EC4899'
          };
          return colorMap[metric] || '#6B7280';
        }
        
        // Helper function to get metric display name
        function getMetricDisplayName(metric) {
          const nameMap = {
            'monthly_avg': '月別打率',
            'monthly_hr': '月別ホームラン',
            'monthly_rbi': '月別打点',
            'monthly_ops': '月別OPS',
            'monthly_obp': '月別出塁率',
            'monthly_slg': '月別長打率',
            'monthly_hits': '月別安打',
            'monthly_singles': '月別単打',
            'monthly_doubles': '月別二塁打',
            'monthly_triples': '月別三塁打',
            'homeruns': 'ホームラン',
            'hits': '安打',
            'avg': '打率',
            'obp': '出塁率',
            'slg': '長打率',
            'ops': 'OPS'
          };
          return nameMap[metric] || metric;
        }
        
      } else if (queryState.category.id === 'batting_splits' && queryState.splitType && queryState.metrics.length > 0) {
        
        if (queryState.splitType.id === 'custom') {
          // Custom situation splits using statcast endpoint
          const baseURL = getBackendURL();
          const cs = queryState.customSituation;
          
          if (queryState.seasonMode === 'all') {
            // Multiple seasons - create YoY trend charts
            const chartPromises = [];
            
            for (const metric of queryState.metrics) {
              let endpoint = `${baseURL}/api/v1/players/${params.playerId}/statcast/batter/advanced-stats?`;
              const urlParams = new URLSearchParams();
              
              if (cs?.innings?.length > 0) {
                cs.innings.forEach(inning => urlParams.append('innings', inning.toString()));
              }
              if (cs?.strikes !== null && cs?.strikes !== undefined) urlParams.append('strikes', cs.strikes.toString());
              if (cs?.balls !== null && cs?.balls !== undefined) urlParams.append('balls', cs.balls.toString());
              if (cs?.pitcherType) urlParams.append('p_throws', cs.pitcherType);
              if (cs?.runnersOnBase?.length > 0) {
                cs.runnersOnBase.forEach(runner => urlParams.append('runners', runner));
              }
              if (cs?.pitchTypes?.length > 0) {
                cs.pitchTypes.forEach(pitch => urlParams.append('pitch_types', pitch));
              }
              
              endpoint += urlParams.toString();
              
              chartPromises.push(
                fetch(endpoint).then(res => res.json()).then(apiResponse => ({
                  metric: metric,
                  data: apiResponse
                }))
              );
            }
            
            // 2. Get career aggregate data for KPIs
            let careerEndpoint = `${baseURL}/api/v1/players/${params.playerId}/statcast/batter/advanced-stats?is_career=true&`;
            const careerUrlParams = new URLSearchParams();
            
            if (cs?.innings?.length > 0) {
              cs.innings.forEach(inning => careerUrlParams.append('innings', inning.toString()));
            }
            if (cs?.strikes !== null && cs?.strikes !== undefined) careerUrlParams.append('strikes', cs.strikes.toString());
            if (cs?.balls !== null && cs?.balls !== undefined) careerUrlParams.append('balls', cs.balls.toString());
            if (cs?.pitcherType) careerUrlParams.append('p_throws', cs.pitcherType);
            if (cs?.runnersOnBase?.length > 0) {
              cs.runnersOnBase.forEach(runner => careerUrlParams.append('runners', runner));
            }
            if (cs?.pitchTypes?.length > 0) {
              cs.pitchTypes.forEach(pitch => careerUrlParams.append('pitch_types', pitch));
            }
            
            careerEndpoint += careerUrlParams.toString();
            
            const [chartResults, careerResponse] = await Promise.all([
              Promise.all(chartPromises),
              fetch(careerEndpoint).then(res => res.json())
            ]);
            
            // Create KPI cards from career data
            let careerKpis = [];
            if (careerResponse && Array.isArray(careerResponse) && careerResponse.length > 0) {
              const careerData = careerResponse[0]; // Should be single aggregated record
              careerKpis = queryState.metrics.map(metric => ({
                metric: metric,
                value: careerData[metric],
                playerName: careerData.batter_name,
                season: 'キャリア通算'
              }));
            }
            
            // Format response with multiple charts
            response = {
              isMultiChart: true,
              isChart: false,
              isCards: careerKpis.length > 0,
              cardsData: careerKpis,
              charts: chartResults.map(result => {
                let chartData = [];
                let chartConfig = {};
                
                if (Array.isArray(result.data) && result.data.length > 0) {
                  const playerName = result.data[0]?.batter_name || 'Selected Player';
                  
                  chartData = result.data.map(seasonData => {
                    const value = seasonData[result.metric];
                    return {
                      year: seasonData.game_year?.toString() || 'Unknown',
                      value: value
                    };
                  }).filter(item => item.value !== null && item.value !== undefined);
                  
                  // Determine chart type based on metric
                  const countingStats = ['hits', 'homeruns', 'doubles', 'triples', 'singles', 'at_bats', 'strikeouts', 'bb_hbp'];
                  const chartType = countingStats.includes(result.metric) ? 'bar' : 'line';
                  
                  // Get display name for metric
                  const metricDisplayNames = {
                    'hits': '安打', 'homeruns': 'ホームラン', 'doubles': '二塁打', 'triples': '三塁打', 'singles': '単打',
                    'at_bats': '打数', 'avg': '打率', 'obp': '出塁率', 'slg': '長打率', 'ops': 'OPS',
                    'strikeouts': '三振', 'bb_hbp': '四死球', 'strikeout_rate': '三振率'
                  };
                  
                  const displayName = metricDisplayNames[result.metric] || result.metric;
                  
                  chartConfig = {
                    title: `${playerName} ${displayName} 年次推移`,
                    xAxis: 'year',
                    dataKey: 'value',
                    lineColor: '#3B82F6',
                    lineName: displayName,
                    yDomain: [0, 'dataMax']
                  };
                  
                  return {
                    metric: result.metric,
                    metricDisplayName: displayName,
                    isChart: chartData.length > 0,
                    chartType: chartType,
                    chartData: chartData,
                    chartConfig: chartConfig,
                    answer: `${displayName}の年次推移`
                  };
                } else {
                  return {
                    metric: result.metric,
                    isChart: false,
                    chartType: 'line',
                    chartData: [],
                    chartConfig: {},
                    answer: `${result.metric}のデータがありません`
                  };
                }
              }),
              answer: `選択条件でのキャリア通算成績と${queryState.metrics.length}個の指標の年次推移を表示します。`
            };
            
          } else {
            // Single season - create KPI cards
            let endpoint = `${baseURL}/api/v1/players/${params.playerId}/statcast/batter/advanced-stats?`;
            const urlParams = new URLSearchParams();
            
            if (params.season) urlParams.append('season', params.season.toString());
            
            if (cs?.innings?.length > 0) {
              cs.innings.forEach(inning => urlParams.append('innings', inning.toString()));
            }
            if (cs?.strikes !== null && cs?.strikes !== undefined) urlParams.append('strikes', cs.strikes.toString());
            if (cs?.balls !== null && cs?.balls !== undefined) urlParams.append('balls', cs.balls.toString());
            if (cs?.pitcherType) urlParams.append('p_throws', cs.pitcherType);
            if (cs?.runnersOnBase?.length > 0) {
              cs.runnersOnBase.forEach(runner => urlParams.append('runners', runner));
            }
            if (cs?.pitchTypes?.length > 0) {
              cs.pitchTypes.forEach(pitch => urlParams.append('pitch_types', pitch));
            }
            
            endpoint += urlParams.toString();
            
            const apiResponse = await fetch(endpoint);
            if (!apiResponse.ok) {
              throw new Error(`Custom situation API call failed: ${apiResponse.status}`);
            }
            
            const data = await apiResponse.json();
            
            // Format as KPI cards for single season
            if (Array.isArray(data) && data.length > 0) {
              const seasonData = data[0];
              const playerName = seasonData.batter_name || 'Selected Player';
              
              const createKPICards = (data, metrics, playerName) => {
                const cards = [];
                const metricsArray = Array.isArray(metrics) ? metrics : [metrics];
                
                metricsArray.forEach(metricKey => {
                  const value = data[metricKey];
                  if (value !== undefined && value !== null) {
                    cards.push({
                      metric: metricKey,
                      value: value,
                      playerName: playerName,
                      season: params.season || 'カスタム状況'
                    });
                  }
                });
                
                return cards;
              };
              
              const kpiCards = createKPICards(
                seasonData, 
                queryState.metrics, 
                playerName
              );
              
              response = {
                answer: `${playerName}選手のカスタム状況成績をKPIカードで表示します。`,
                isCards: true,
                cardsData: kpiCards,
                isTable: false,
                isChart: false
              };
            } else {
              response = {
                answer: 'カスタム状況データが見つかりませんでした。',
                isTable: false,
                isChart: false,
                isCards: false
              };
            }
          }
        } else if (queryState.seasonMode === 'all') {
          // Multiple seasons - create YoY trend charts (direct API calls)
          const chartPromises = [];
          const baseURL = getBackendURL();
          
          for (const metric of queryState.metrics) {
            const endpoint = `${baseURL}/api/v1/players/${params.playerId}/season-batting-splits?split_type=${queryState.splitType.id}&metrics=${metric}`;
            
            chartPromises.push(
              fetch(endpoint).then(res => res.json()).then(apiResponse => ({
                metric: metric,
                data: apiResponse
              }))
            );
          }
          
          const chartResults = await Promise.all(chartPromises);
          console.log('🔍 Debug - Chart results for batting splits:', chartResults);
          
          // Format response with multiple charts
          response = {
            isMultiChart: true,
            isChart: false,
            isCards: false,
            charts: chartResults.map(result => {
              let chartData = [];
              let chartConfig = {};
              
              if (Array.isArray(result.data) && result.data.length > 0) {
                const playerName = result.data[0]?.batter_name || 'Selected Player';
                
                console.log('🔍 Debug - Processing data for metric:', result.metric);
                console.log('🔍 Debug - Raw data:', result.data);
                
                chartData = result.data.map(seasonData => {
                  console.log('🔍 Debug - Season data keys:', Object.keys(seasonData));
                  const value = seasonData[result.metric];
                  console.log('🔍 Debug - Value for', result.metric, ':', value);
                  return {
                    year: seasonData.game_year?.toString() || 'Unknown',
                    value: value
                  };
                }).filter(item => {
                  console.log('🔍 Debug - Filtering item:', item);
                  return item.value !== null && item.value !== undefined;
                });
                
                // Determine chart type based on metric
                const countingStats = ['hits_at_risp', 'homeruns_at_risp', 'doubles_at_risp', 'triples_at_risp', 'singles_at_risp', 'ab_at_risp',
                                     'hits_at_bases_loaded', 'grandslam', 'doubles_at_bases_loaded', 'triples_at_bases_loaded', 'singles_at_bases_loaded', 'ab_at_bases_loaded'];
                const chartType = countingStats.includes(result.metric) ? 'bar' : 'line';
                
                // Get display name for metric
                const metricDisplayNames = {
                  'hits_at_risp': 'RISP時安打',
                  'homeruns_at_risp': 'RISP時ホームラン',
                  'doubles_at_risp': 'RISP時二塁打',
                  'triples_at_risp': 'RISP時三塁打',
                  'singles_at_risp': 'RISP時単打',
                  'ab_at_risp': 'RISP時打数',
                  'avg_at_risp': 'RISP時打率',
                  'obp_at_risp': 'RISP時出塁率',
                  'slg_at_risp': 'RISP時長打率',
                  'ops_at_risp': 'RISP時OPS',
                  'strikeout_rate_at_risp': 'RISP時三振率',
                  'hits_at_bases_loaded': '満塁時安打',
                  'grandslam': 'グランドスラム',
                  'doubles_at_bases_loaded': '満塁時二塁打',
                  'triples_at_bases_loaded': '満塁時三塁打',
                  'singles_at_bases_loaded': '満塁時単打',
                  'ab_at_bases_loaded': '満塁時打数',
                  'avg_at_bases_loaded': '満塁時打率',
                  'obp_at_bases_loaded': '満塁時出塁率',
                  'slg_at_bases_loaded': '満塁時長打率',
                  'ops_at_bases_loaded': '満塁時OPS',
                  'strikeout_rate_at_bases_loaded': '満塁時三振率'
                };
                
                const displayName = metricDisplayNames[result.metric] || result.metric;
                
                chartConfig = {
                  title: `${playerName} ${displayName} 年次推移`,
                  xAxis: 'year',
                  dataKey: 'value',
                  lineColor: '#3B82F6',
                  lineName: displayName,
                  yDomain: [0, 'dataMax']
                };
                
                return {
                  metric: result.metric,
                  metricDisplayName: displayName,
                  isChart: chartData.length > 0,
                  chartType: chartType,
                  chartData: chartData,
                  chartConfig: chartConfig,
                  answer: `${displayName}の年次推移`
                };
              } else {
                // No data case
                return {
                  metric: result.metric,
                  isChart: false,
                  chartType: 'line',
                  chartData: [],
                  chartConfig: {},
                  answer: `${result.metric}のデータがありません`
                };
              }
            }),
            answer: `${queryState.metrics.length}個の指標の年次推移を表示します。`
          };
          
        } else {
          // Single season - create KPI cards
          const queryParams = {
            playerId: params.playerId,
            season: params.season || 2024,
            split_type: queryState.splitType.id,
            metrics: queryState.metrics,
            queryType: 'season_batting_splits'
          };
          
          response = await callFixedQueryAPI(queryParams);
        }
        
      } else if (queryState.category.id === 'season_pitching' && primaryMetric) {
        // Direct mapping to backend fields
        const metricMapping = {
          'inning_pitched': 'ip',
          'era': 'era',
          'whip': 'whip',
          'strikeouts': 'so',
          'walks': 'bb',
          'home_runs_allowed': 'hr',
          'batting_average_against': 'avg',
          'wins': 'w',
          'losses': 'l',
          'fip': 'fip',
          'games': 'g',
          'game_started': 'gs',
          'shutouts': 'sho',
          'saves': 'sv',
          'runs': 'r',
          'hits_allowed': 'h',
          'homeruns_allowed': 'hr',
          'earned_runs': 'er',
          'left_on_base_percentage': 'lobpct',
          'ground_ball_percentage': 'gbpct',
          'barrel_percentage': 'barrelpct',
          'hard_hit_percentage': 'hardhitpct',
          'k_9': 'k_9',
          'bb_9': 'bb_9',
          'war': 'war'
        };

        // Map all selected metrics
        const mappedMetrics = queryState.metrics
          .map(metric => {
            const backendMetric = metricMapping[metric];
            if (backendMetric === null) {
              console.warn(`Metric "${metric}" not supported yet`);
              return null;
            }
            if (!backendMetric) {
              console.warn(`Unknown metric: ${metric}`);
              return null;
            }
            return backendMetric;
          })
          .filter(Boolean);
        
          console.log('🔍 Season pitching - Frontend metrics:', queryState.metrics, '-> Backend metrics:', mappedMetrics);

          if (mappedMetrics.length === 0) {
            throw new Error(`選択された指標はサポートされていません。`);
          }

          // Use same endpoint for both single season and all seasons
          const queryParams = {
            playerId: params.playerId,
            season: queryState.seasonMode === 'all' ? null : (params.season || 2024),
            metrics: mappedMetrics,
            queryType: 'season_pitching_stats' // Same endpoint handles both cases
          };
          response = await callFixedQueryAPI(queryParams);

      } else if (queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard') {
        // Leaderboard handling
        console.log('🏆 Leaderboard query execution:', queryState);
        
        // Implement automatic min_pa or min_ip logic
        const currentYear = new Date().getFullYear();
        const queryYear = queryState.specificYear || currentYear;
        const min_pa = queryYear === 2025 ? 280 : 350; // This threshold is as of Jul 8, 2025
        const min_ip = queryYear === 2025 ? 70 : 100;  // This threshold is as of Jul 8, 2025

        // Prepare leaderboard API parameters
        let leaderboardParams;
        
        if (queryState.category.id === 'batting_leaderboard') {
          leaderboardParams = {
            season: queryYear,
            league: queryState.league || 'MLB',
            metric_order: queryState.metricOrder,
            min_pa: min_pa,
          };
        } else if (queryState.category.id === 'pitching_leaderboard') {
          leaderboardParams = {
            season: queryYear,
            league: queryState.league || 'MLB',
            metric_order: queryState.metricOrder,
            min_ip: min_ip,
          };
        }

        console.log('🏆 Leaderboard API params:', leaderboardParams);
        
        // Call leaderboard API
        const backendURL = getBackendURL();
        
        const endpoint = queryState.category.id === 'batting_leaderboard' 
        ? `${backendURL}/api/v1/leaderboards/batting` 
        : `${backendURL}/api/v1/leaderboards/pitching`;

        const queryString = new URLSearchParams(leaderboardParams).toString();
        const fullUrl = `${endpoint}?${queryString}`;
        
        console.log('🔗 Leaderboard API URL:', fullUrl);
        
        const apiResponse = await fetch(fullUrl);
        if (!apiResponse.ok) {
          throw new Error(`Leaderboard API call failed: ${apiResponse.status} ${apiResponse.statusText}`);
        }
        
        const leaderboardData = await apiResponse.json();
        console.log('📊 Leaderboard API response:', leaderboardData);
        
        // Format response for leaderboard display
        response = {
          isLeaderboard: true,
          leaderboardData: leaderboardData,
          data: leaderboardData, // alias for compatibility
          answer: `${queryState.category.name}（${queryYear}年シーズン、${queryState.league}、${queryState.metricOrder}でソート）`,
          query: `${queryState.category.name} - ${queryYear}年 ${queryState.league} (最小打席数: ${min_pa})`
        };

      } else if (!response) {
        // For categories not yet implemented, generate appropriate mock data
        console.log('⚠️ Category not implemented yet, using mock data:', queryState.category.id);
        
        const mockDataGenerators = {
          season_batting: () => ({
            answer: `${queryState.player?.name || '選手'}の${params.season || 2024}年シーズン打撃成績を表示します。（バックエンド実装予定）`,
            isTable: true,
            tableData: [
              {
                metric: '打率',
                value: (Math.random() * 0.200 + 0.200).toFixed(3),
                rank: Math.floor(Math.random() * 10) + 1
              },
              {
                metric: 'ホームラン',
                value: Math.floor(Math.random() * 30) + 10,
                rank: Math.floor(Math.random() * 15) + 1
              },
              {
                metric: 'RBI',
                value: Math.floor(Math.random() * 60) + 40,
                rank: Math.floor(Math.random() * 20) + 1
              }
            ],
            columns: [
              { key: 'metric', label: '指標' },
              { key: 'value', label: '値' },
              { key: 'rank', label: 'リーグ順位' }
            ]
          }),
          
          season_pitching: () => ({
            answer: `${queryState.player?.name || '選手'}の${params.season || 2024}年シーズン投手成績を表示します。（バックエンド実装予定）`,
            isTable: true,
            tableData: [
              {
                metric: '防御率',
                value: (Math.random() * 2.0 + 2.0).toFixed(2),
                rank: Math.floor(Math.random() * 15) + 1
              },
              {
                metric: '奪三振',
                value: Math.floor(Math.random() * 100) + 150,
                rank: Math.floor(Math.random() * 10) + 1
              },
              {
                metric: 'WHIP',
                value: (Math.random() * 0.5 + 1.0).toFixed(2),
                rank: Math.floor(Math.random() * 20) + 1
              }
            ],
            columns: [
              { key: 'metric', label: '指標' },
              { key: 'value', label: '値' },
              { key: 'rank', label: 'リーグ順位' }
            ]
          }),
          
          team_comparison: () => ({
            answer: `チーム比較データを表示します。（バックエンド実装予定）`,
            isChart: true,
            chartType: 'bar',
            chartData: [
              { team: 'LAA', value: Math.random() * 50 + 70 },
              { team: 'NYY', value: Math.random() * 50 + 80 },
              { team: 'HOU', value: Math.random() * 50 + 85 },
              { team: 'LAD', value: Math.random() * 50 + 90 },
              { team: 'TB', value: Math.random() * 50 + 75 }
            ],
            chartConfig: {
              title: `${params.season || 2024}年 チーム成績比較 (サンプルデータ)`,
              xAxis: 'team',
              dataKey: 'value',
              lineColor: '#EF4444',
              lineName: primaryMetric || 'チーム成績',
              yDomain: [0, 150]
            }
          }),
          
          career_stats: () => ({
            answer: `${queryState.player?.name || '選手'}の通算成績推移を表示します。（バックエンド実装予定）`,
            isChart: true,
            chartType: 'line',
            chartData: Array.from({ length: 8 }, (_, i) => ({
              year: `${2017 + i}`,
              value: Math.random() * 0.150 + 0.200
            })),
            chartConfig: {
              title: `${queryState.player?.name || '選手'} 通算成績推移 (サンプルデータ)`,
              xAxis: 'year',
              dataKey: 'value',
              lineColor: '#10B981',
              lineName: primaryMetric || 'キャリア成績',
              yDomain: [0, 0.400]
            }
          })
        };
        
        const generator = mockDataGenerators[queryState.category.id] || mockDataGenerators.season_batting;
        response = {
          isTable: false,
          isChart: false,
          ...generator()
        };
      }

      // Generate summary text for the query
      const generateSummaryText = (queryState) => {
        const categoryNames = {
          season_batting: 'シーズン打撃成績',
          season_pitching: 'シーズン投手成績', 
          batting_splits: '場面別打撃成績',
          monthly_trends: '月別推移',
          team_comparison: 'チーム比較',
          career_stats: '通算成績',
          batting_leaderboard: '打撃リーダーボード',
          pitching_leaderboard: '投手リーダーボード'
        };

        const seasonText = queryState.seasonMode === 'all' 
          ? '全シーズン'
          : `${queryState.specificYear}年シーズン`;

        const metricsText = queryState.metrics.length === 1 
          ? queryState.metrics[0]
          : `${queryState.metrics.join('、')}など`;

        const isLeaderboard = queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard';
        
        if (isLeaderboard) {
          return `${seasonText}における${categoryNames[queryState.category.id]} (${queryState.league}、${queryState.metricOrder}でソート)`;
        } else {
          return `${queryState.player?.name || '選手'}の${seasonText}における${categoryNames[queryState.category.id]}から${metricsText}の分析結果`;
        }
      };
      
      console.log('🔍 Custom Query API Response:', response);
      console.log('🔍 Debug - Response isCards:', response.isCards);
      console.log('🔍 Debug - Response isChart:', response.isChart);
      console.log('🔍 Debug - Response cardsData:', response.cardsData);
      
      // Store the result for display in Custom Query section
      setCustomResult({
        query: generateSummaryText(queryState),
        queryState: queryState,
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
        // Add support for multiple charts
        isMultiChart: response.isMultiChart || false,
        charts: response.charts || null,
        cardsData: response.cardsData || null,
        // Add leaderboard specific properties
        isLeaderboard: response.isLeaderboard || false,
        data: response.data || null,
        leaderboardData: response.leaderboardData || null,
        timestamp: new Date()
      });
      
    } catch (error) {
      console.error('❌ Custom Query Error:', error);
      
      // Generate error summary
      const categoryNames = {
        season_batting: 'シーズン打撃成績',
        season_pitching: 'シーズン投手成績', 
        batting_splits: '場面別打撃成績',
        monthly_trends: '月別推移',
        team_comparison: 'チーム比較',
        career_stats: '通算成績',
        batting_leaderboard: '打撃リーダーボード',
        pitching_leaderboard: '投手リーダーボード'
      };

      const isLeaderboard = queryState.category.id === 'batting_leaderboard' || queryState.category.id === 'pitching_leaderboard';
      const errorSummary = isLeaderboard 
        ? `${categoryNames[queryState.category.id]}クエリでエラーが発生`
        : `${queryState.player?.name || '選手'}の${categoryNames[queryState.category.id]}クエリでエラーが発生`;
      
      setCustomResult({
        query: errorSummary,
        queryState: queryState,
        answer: 'エラーが発生しました。しばらく後でもう一度お試しください。',
        isChart: false,
        isTable: false,
        timestamp: new Date()
      });
    }
    
    setIsLoading(false);
  };

  // ===== キーボードイベント処理 =====
  // Enterキーでメッセージ送信（Shift+Enterは改行）
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ===== 時刻フォーマット関数 =====
  // タイムスタンプを日本語形式（HH:MM）でフォーマット
  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString('ja-JP', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // ===== 統計データ表示コンポーネント =====
  // BigQueryから取得した統計データをカード形式で表示
  const StatCard = ({ stats }) => {
    // 統計データがない場合は何も表示しない
    if (!stats) return null;

    return (
      <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 transition-colors duration-200">
        {/* カードヘッダー */}
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400 transition-colors duration-200" />
          <span className="text-sm font-semibold text-blue-800 dark:text-blue-300 transition-colors duration-200">統計データ</span>
        </div>
        {/* 統計データをキー・バリューペアで表示 */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(stats).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400 transition-colors duration-200">{key}:</span>
              <span className="font-semibold text-gray-900 dark:text-white transition-colors duration-200">{value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ===== テーブル表示コンポーネント =====
  // 構造化されたテーブルデータを表示
  const DataTable = ({ tableData, columns, isTransposed, decimalColumns = [], grouping = null }) => {
    if (!tableData || !columns) return null;

    // 単一行結果の場合は縦表示（転置）
    if (isTransposed && tableData.length === 1) {
      const row = tableData[0];
      
      // Handle grouped display for career batting
      if (grouping && grouping.type === "career_batting_chunks") {
        return (
          <div className="mt-3 space-y-6">
            {grouping.groups.map((group, groupIndex) => {
              const groupColumns = columns.filter(col => group.columns.includes(col.key));
              if (groupColumns.length === 0) return null;
              
              return (
                <div key={groupIndex} className="overflow-x-auto">
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-200">{group.name}</h4>
                  <div className="inline-block min-w-full align-middle">
                    <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg transition-colors duration-200">
                      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800 transition-colors duration-200">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                              項目
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                              値
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600 transition-colors duration-200">
                          {groupColumns.map((column, index) => (
                            <tr key={column.key} className={index % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                                {column.label}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                                {typeof row[column.key] === 'number' 
                                  ? (() => {
                                      const shouldShowDecimals = decimalColumns.includes(column.key);
                                      
                                      return Number(row[column.key]).toLocaleString('ja-JP', {
                                        minimumFractionDigits: shouldShowDecimals ? 3 : 0,
                                        maximumFractionDigits: shouldShowDecimals ? 3 : 0
                                      });
                                    })()
                                  : row[column.key]
                                }
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        );
      }
      
      // Default single table display
      return (
        <div className="mt-3 overflow-x-auto">
          <div className="inline-block min-w-full align-middle">
            <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg transition-colors duration-200">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800 transition-colors duration-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                      項目
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                      値
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600 transition-colors duration-200">
                  {columns.map((column, index) => (
                    <tr key={column.key} className={index % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                        {column.label}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                        {typeof row[column.key] === 'number' 
                          ? (() => {
                              // Use centralized decimal columns from backend
                              const shouldShowDecimals = decimalColumns.includes(column.key);
                              
                              return Number(row[column.key]).toLocaleString('ja-JP', {
                                minimumFractionDigits: shouldShowDecimals ? 3 : 0,
                                maximumFractionDigits: shouldShowDecimals ? 3 : 0
                              });
                            })()
                          : row[column.key]
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      );
    }

    // 複数行結果の場合は通常の横表示
    return (
      <div className="mt-3 overflow-x-auto">
        <div className="inline-block min-w-full align-middle">
          <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg transition-colors duration-200">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800 transition-colors duration-200">
                <tr>
                  {columns.map((column) => (
                    <th
                      key={column.key}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200"
                    >
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600 transition-colors duration-200">
                {tableData.map((row, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className="px-4 py-3 text-sm text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200"
                      >
                        {typeof row[column.key] === 'number' 
                          ? (() => {
                              // Use centralized decimal columns from backend
                              const shouldShowDecimals = decimalColumns.includes(column.key);
                              
                              return Number(row[column.key]).toLocaleString('ja-JP', {
                                minimumFractionDigits: shouldShowDecimals ? 3 : 0,
                                maximumFractionDigits: shouldShowDecimals ? 3 : 0
                              });
                            })()
                          : row[column.key]
                        }
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ===== メインUIレンダリング =====
  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900 transition-colors duration-200" data-theme-test>
      {!isAuthenticated ? (
        // ===== 認証画面 =====
        <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-black transition-colors duration-200">
          <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg w-full max-w-md transition-colors duration-200">
            {/* ヘッダー */}
            <div className="text-center mb-6">
              <div className="mx-auto w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
                <Activity className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 transition-colors duration-200">Diamond Lens MLB Stats Assistant</h1>
              <p className="text-gray-600 dark:text-gray-300 transition-colors duration-200">アクセスにはパスワードが必要です</p>
            </div>
            
            {/* パスワード入力フォーム */}
            <div className="space-y-4">
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-200">
                  パスワード
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={handleAuthKeyDown}
                  placeholder="パスワードを入力してください"
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent text-gray-900 dark:text-white bg-white dark:bg-gray-700 transition-colors duration-200"
                  disabled={isCheckingAuth}
                />
              </div>
              
              {/* エラーメッセージ */}
              {authError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg transition-colors duration-200">
                  <p className="text-sm text-red-600 dark:text-red-400 transition-colors duration-200">{authError}</p>
                </div>
              )}
              
              {/* ログインボタン */}
              <button
                onClick={handleAuthentication}
                disabled={!password.trim() || isCheckingAuth}
                className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2 transition-colors duration-200"
              >
                {isCheckingAuth ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    認証中...
                  </>
                ) : (
                  'ログイン'
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        // ===== メインチャットインターフェース =====
        <>
          {/* ===== ヘッダーセクション ===== */}
          <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 sm:px-6 py-4 transition-colors duration-200">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-8">
              <div className="flex items-center gap-3">
                {/* アプリアイコン */}
                <div className="p-2 bg-blue-600 rounded-lg">
                  <Activity className="w-6 h-6 text-white" />
                </div>
                {/* アプリタイトルと説明 */}
                <div>
                  <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-purple-400 transition-all duration-200">Diamond Lens</h1>
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">MLB Stats Assistant</div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 transition-colors duration-200">
                    {uiMode === 'chat' && 'MLBの統計データについて質問してください'}
                    {uiMode === 'quick' && 'よく使われる質問をワンクリックで実行'}
                    {uiMode === 'custom' && 'カスタムクエリを作成して詳細な分析を実行'}
                    {uiMode === 'statistics' && '統計分析モデルを使用してチームの勝率を予測'}
                    {uiMode === 'segmentation' && 'K-meansクラスタリングで選手タイプを分析'}
                  </p>
                </div>
              </div>
              
              {/* モード切り替えボタン */}
              <div className="flex flex-col sm:flex-row bg-gray-100 dark:bg-gray-700 rounded-lg p-1.5 gap-1 transition-colors duration-200">
                <button
                  onClick={() => {
                    setUiMode('chat');
                    setQuickResult(null); // Clear quick result when switching to chat
                    setCustomResult(null); // Clear custom result when switching to chat
                  }}
                  className={`px-4 py-3 sm:py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center justify-center sm:justify-start gap-2 min-w-0 w-full sm:w-auto ${
                    uiMode === 'chat' 
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' 
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <MessageCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">チャット</span>
                </button>
                <button
                  onClick={() => {
                    setUiMode('quick');
                    setCustomResult(null); // Clear custom result when switching to quick
                    // Keep quick result when switching to quick mode
                  }}
                  className={`px-4 py-3 sm:py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center justify-center sm:justify-start gap-2 min-w-0 w-full sm:w-auto ${
                    uiMode === 'quick' 
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' 
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Zap className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">クイック質問</span>
                </button>
                <button
                  onClick={() => {
                    setUiMode('custom');
                    setQuickResult(null); // Clear quick result when switching to custom
                    // Keep custom result when switching to custom mode
                  }}
                  className={`px-4 py-3 sm:py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center justify-center sm:justify-start gap-2 min-w-0 w-full sm:w-auto ${
                    uiMode === 'custom'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Settings className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">カスタムクエリ</span>
                </button>
                <button
                  onClick={() => {
                    setUiMode('statistics');
                    setQuickResult(null);
                    setCustomResult(null);
                  }}
                  className={`px-4 py-3 sm:py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center justify-center sm:justify-start gap-2 min-w-0 w-full sm:w-auto ${
                    uiMode === 'statistics'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Activity className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">統計分析</span>
                </button>
                <button
                  onClick={() => {
                    setUiMode('segmentation');
                    setQuickResult(null);
                    setCustomResult(null);
                  }}
                  className={`px-4 py-3 sm:py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center justify-center sm:justify-start gap-2 min-w-0 w-full sm:w-auto ${
                    uiMode === 'segmentation'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Users className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">選手分類</span>
                </button>

                {/* 疲労分析 - 一時無効化 */}
                {/* <button
                  onClick={() => {
                    setUiMode('fatigue');
                    setQuickResult(null);
                    setCustomResult(null);
                  }}
                  className={`px-4 py-3 sm:py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center justify-center sm:justify-start gap-2 min-w-0 w-full sm:w-auto ${
                    uiMode === 'fatigue'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">疲労分析</span>
                </button> */}

                {/* Whiff予測 - 実戦価値が限定的なため一時無効化 */}
                {/* <button
                  onClick={() => {
                    setUiMode('pitcher-whiff');
                    setQuickResult(null);
                    setCustomResult(null);
                  }}
                  className={`px-4 py-3 sm:py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center justify-center sm:justify-start gap-2 min-w-0 w-full sm:w-auto ${
                    uiMode === 'pitcher-whiff'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Target className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">Whiff予測</span>
                </button> */}

              </div>
            </div>
          </div>

      {/* ===== メインコンテンツエリア ===== */}
      <div className="flex-1 overflow-y-auto">
        {uiMode === 'chat' ? (
          /* ===== メッセージ表示エリア ===== */
          <div className="px-4 sm:px-6 py-4 space-y-4 h-full">
        {/* 各メッセージをレンダリング */}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {/* ボットアバター（ボットメッセージの場合のみ表示） */}
            {message.type === 'bot' && (
              <div className="w-8 h-8 rounded-full bg-blue-600 dark:bg-blue-500 flex items-center justify-center flex-shrink-0 transition-colors duration-200">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}
            
            {/* メッセージ本体 */}
            <div className={`${message.isChart ? 'max-w-full lg:max-w-5xl' : 'max-w-full sm:max-w-2xl'} ${message.type === 'user' ? 'order-2' : ''}`}>
              {/* メッセージバブル */}
              <div
                className={`px-4 py-3 rounded-lg transition-colors duration-200 ${
                  message.type === 'user'
                    ? 'bg-blue-600 dark:bg-blue-500 text-white' // ユーザーメッセージは青背景
                    : 'bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white' // ボットメッセージは白背景
                }`}
              >
                {/* メッセージテキスト */}
                <p className="whitespace-pre-wrap">{message.content}</p>
                {/* テーブル表示（テーブルデータがある場合のみ表示） */}
                {message.isTable && message.tableData && message.columns && (
                  <DataTable 
                    tableData={message.tableData} 
                    columns={message.columns} 
                    isTransposed={message.isTransposed}
                    decimalColumns={message.decimalColumns}
                    grouping={message.grouping}
                  />
                )}
                {/* チャート表示（チャートデータがある場合のみ表示） */}
                {(() => {
                  console.log('🔍 Chart render check:', {
                    messageId: message.id,
                    isChart: message.isChart,
                    hasChartData: !!message.chartData,
                    hasChartConfig: !!message.chartConfig,
                    chartType: message.chartType,
                    shouldRender: message.isChart && message.chartData && message.chartConfig
                  });
                  return null;
                })()}
                {message.isChart && message.chartData && message.chartConfig ? (
                  <SimpleChatChart 
                    chartData={message.chartData}
                    chartConfig={message.chartConfig}
                    chartType={message.chartType}
                  />
                ) : message.isChart ? (
                  <div className="mt-4 p-4 bg-red-100 dark:bg-red-900 rounded-lg">
                    <p className="text-red-800 dark:text-red-200">Chart data missing: isChart={String(message.isChart)}, hasData={String(!!message.chartData)}, hasConfig={String(!!message.chartConfig)}</p>
                  </div>
                ) : null}
                {/* 統計データカード（データがある場合のみ表示） */}
                {message.stats && <StatCard stats={message.stats} />}
              </div>
              {/* タイムスタンプ */}
              <p className={`text-xs text-gray-500 dark:text-gray-400 mt-1 transition-colors duration-200 ${
                message.type === 'user' ? 'text-right' : 'text-left'
              }`}>
                {formatTime(message.timestamp)}
              </p>
            </div>

            {/* ユーザーアバター（ユーザーメッセージの場合のみ表示） */}
            {message.type === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-600 dark:bg-gray-500 flex items-center justify-center flex-shrink-0 order-3 transition-colors duration-200">
                <User className="w-5 h-5 text-white" />
              </div>
            )}
          </div>
        ))}

        {/* ===== ローディングアニメーション ===== */}
        {/* API呼び出し中に表示される点滅アニメーション */}
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-blue-600 dark:bg-blue-500 flex items-center justify-center flex-shrink-0 transition-colors duration-200">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-3 transition-colors duration-200">
              <div className="flex gap-1">
                {/* 3つの点が順番に点滅するアニメーション */}
                <div className="w-2 h-2 bg-gray-400 dark:bg-gray-300 rounded-full animate-bounce transition-colors duration-200"></div>
                <div className="w-2 h-2 bg-gray-400 dark:bg-gray-300 rounded-full animate-bounce transition-colors duration-200" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-gray-400 dark:bg-gray-300 rounded-full animate-bounce transition-colors duration-200" style={{animationDelay: '0.2s'}}></div>
              </div>
            </div>
          </div>
        )}
        
        {/* 自動スクロール用の要素 */}
        <div ref={messagesEndRef} />
          </div>
        ) : uiMode === 'quick' ? (
          /* ===== クイック質問エリア ===== */
          <div className="px-4 sm:px-6 py-6 sm:py-8 h-full flex items-center justify-center">
            <QuickQuestions 
              onQuestionClick={handleQuickQuestion} 
              isLoading={isLoading}
              quickResult={quickResult}
              onClearResult={() => setQuickResult(null)}
            />
          </div>
        ) : uiMode === 'statistics' ? (
          /* ===== 統計分析エリア ===== */
          <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
            <StatisticalAnalysis />
          </div>
        ) : uiMode === 'segmentation' ? (
          /* ===== 選手セグメンテーションエリア ===== */
          <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
            <PlayerSegmentation />
          </div>
        ) : uiMode === 'fatigue' ? (
          /* ===== 投手疲労分析エリア ===== */
          <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
            <PitcherFatigue />
          </div>
        ) : uiMode === 'pitcher-whiff' ? (
          /* ===== Pitcher Whiff予測エリア ===== */
          <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
            <PitcherWhiffPredictor />
          </div>
        ) : (
          /* ===== カスタムクエリビルダーエリア ===== */
          <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
            <CustomQueryBuilder
              isLoading={isLoading}
              onExecuteQuery={handleCustomQuery}
              customResult={customResult}
              onClearResult={() => setCustomResult(null)}
              onSearchPlayers={searchPlayers}
            />
          </div>
        )}
      </div>

      {/* ===== メッセージ入力エリア ===== */}
      {uiMode === 'chat' && (
        <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 sm:px-6 py-4 transition-colors duration-200">
        <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
          {/* テキストエリア */}
          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="例: 大谷翔平の2024年の打率は？"
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 bg-white dark:bg-gray-700 transition-colors duration-200"
              rows="2"
              disabled={isLoading} // ローディング中は入力を無効化
            />
          </div>
          {/* 送信ボタン */}
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading} // 入力が空またはローディング中は無効化
            className="px-4 sm:px-6 py-3 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium transition-colors duration-200 w-full sm:w-auto"
          >
            <Send className="w-4 h-4" />
            送信
          </button>
        </div>
        
        {/* サンプル質問の表示 */}
        <div className="mt-3 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
            サンプル質問: 「大谷翔平 打率」「ヤンキース 勝率」「2024年のホームラン王トップ10を表で」
          </p>
        </div>
        </div>
      )}
      </>
      )}
    </div>
  );
};

// メインアプリケーション（ダークモード固定）
const App = () => {
  return <MLBChatApp />;
};

export default App;