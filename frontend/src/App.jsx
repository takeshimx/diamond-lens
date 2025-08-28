import React, { useState, useRef, useEffect } from 'react';
import { Send, TrendingUp, User, Bot, Activity, MessageCircle, Zap, Settings } from 'lucide-react';
import SimpleChatChart from './components/ChatChart.jsx';
import QuickQuestions from './components/QuickQuestions.jsx';
import CustomQueryBuilder from './components/CustomQueryBuilder.jsx';

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
  const [uiMode, setUiMode] = useState('chat'); // 'chat', 'quick', または 'custom'
  
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
        // Placeholder endpoint for season-level batting stats (will be implemented by backend)
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/season-batting-stats?season=${questionParams.season}&metrics=${questionParams.metrics || questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_batting_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/monthly-batting-stats?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_offensive_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/monthly-offensive-stats?season=${questionParams.season}&metric=${questionParams.metric}`;
      } else if (questionParams.queryType === 'monthly_risp_stats') {
        endpoint = `${baseURL}/api/v1/players/${questionParams.playerId}/performance-at-risp?season=${questionParams.season}&metric=${questionParams.metric}`;
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
          // Handle season batting stats - display as KPI cards
          if (apiResponse && (Array.isArray(apiResponse) ? apiResponse.length > 0 : typeof apiResponse === 'object')) {
            
            // Handle both array and object responses
            const data = Array.isArray(apiResponse) ? apiResponse[0] : apiResponse;
            const playerName = data.name || data.player_name || data.batter_name || 'Selected Player';
            const season = data.season || questionParams.season;
            
            console.log('🔍 Debug - Season batting stats response:', apiResponse);
            console.log('🔍 Debug - Extracted data:', data);
            console.log('🔍 Debug - Player name:', playerName);
            console.log('🔍 Debug - Season:', season);
            
            // Create KPI cards data from the season stats response
            const createKPICards = (data, metrics, season, playerName) => {
              const cards = [];
              
              // If metrics is a string, convert to array
              const metricsArray = typeof metrics === 'string' ? [metrics] : (metrics || []);
              
              console.log('🔍 Debug - Metrics array:', metricsArray);
              console.log('🔍 Debug - Data keys:', Object.keys(data));
              
              metricsArray.forEach(metricKey => {
                const value = data[metricKey];
                console.log(`🔍 Debug - Checking metric "${metricKey}":`, value);
                
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
            
            console.log('🔍 Debug - KPI cards data:', kpiCards);
            
            return {
              answer: `${playerName}選手の${season}年シーズン成績をKPIカードで表示します。`,
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
              chartConfig: null,
              isCards: true, // New property to indicate card display
              cardsData: kpiCards
            };
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
                yAxisLabel: '三振率 (%)',
                yDomain: [0, 40],
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
      // Extract parameters from queryState for direct BigQuery API calls
      const params = {
        playerId: queryState.player.mlb_id || queryState.player.id, // Use mlb_id when available
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
        // Season batting stats - use season-level batting stats endpoint for KPI cards
        // Backend will use fact_batting_stats_with_risp table with PlayerBattingSeasonStats model
        const metricMapping = {
          // Direct mapping to backend fields (based on PlayerBattingSeasonStats schema)
          'plate_appearances': 'pa',
          'at_bats': 'ab',
          'games': 'g',
          'batting_average': 'avg',
          'hits': 'h', 
          'home_runs': 'hr',
          'doubles': '2b',
          'triples': '3b',
          'singles': '1b',
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
        
        const queryParams = {
          playerId: params.playerId,
          season: params.season || 2024,
          metrics: mappedMetrics, // Pass all mapped metrics
          queryType: 'season_batting_stats' // New query type for season-level KPI cards
        };
        response = await callFixedQueryAPI(queryParams);
        
      } else if (queryState.category.id === 'monthly_trends' && primaryMetric) {
        // Monthly trends - use endpoint depending on metric

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

        const backendMetric = metricMapping[primaryMetric];
        console.log('🔍 Monthly trends - Frontend metric:', primaryMetric, '-> Backend metric:', backendMetric);
        
        // Check if metric is supported by backend
        if (backendMetric === null) {
          throw new Error(`指標「${primaryMetric}」は現在サポートされていません。サポート済み指標: 打率、安打数、打点、ホームラン数、二塁打、三塁打、単打、四球、出塁率、長打率、OPS`);
        }
        
        if (!backendMetric) {
          throw new Error(`未知の指標です: ${primaryMetric}`);
        }

        const queryParams = {
          playerId: params.playerId,
          season: params.season || 2024,
          metric: backendMetric,
          queryType: 'monthly_batting_stats'
        };
        response = await callFixedQueryAPI(queryParams);
        
      } else if (queryState.category.id === 'batting_splits' && primaryMetric) {
        // Batting splits - use RISP endpoint for now
        const queryParams = {
          playerId: params.playerId,
          season: params.season || 2024,
          metric: primaryMetric.includes('risp') ? primaryMetric : 'batting_average_at_risp',
          queryType: 'monthly_risp_stats'
        };
        response = await callFixedQueryAPI(queryParams);
        
      } else {
        // For categories not yet implemented, generate appropriate mock data
        console.log('⚠️ Category not implemented yet, using mock data:', queryState.category.id);
        
        const mockDataGenerators = {
          season_batting: () => ({
            answer: `${queryState.player.name}の${params.season || 2024}年シーズン打撃成績を表示します。（バックエンド実装予定）`,
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
            answer: `${queryState.player.name}の${params.season || 2024}年シーズン投手成績を表示します。（バックエンド実装予定）`,
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
            answer: `${queryState.player.name}の通算成績推移を表示します。（バックエンド実装予定）`,
            isChart: true,
            chartType: 'line',
            chartData: Array.from({ length: 8 }, (_, i) => ({
              year: `${2017 + i}`,
              value: Math.random() * 0.150 + 0.200
            })),
            chartConfig: {
              title: `${queryState.player.name} 通算成績推移 (サンプルデータ)`,
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
          career_stats: '通算成績'
        };

        const seasonText = queryState.seasonMode === 'all' 
          ? '全シーズン'
          : `${queryState.specificYear}年シーズン`;

        const metricsText = queryState.metrics.length === 1 
          ? queryState.metrics[0]
          : `${queryState.metrics.join('、')}など`;

        return `${queryState.player.name}の${seasonText}における${categoryNames[queryState.category.id]}から${metricsText}の分析結果`;
      };
      
      console.log('🔍 Custom Query API Response:', response);
      
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
        cardsData: response.cardsData || null,
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
        career_stats: '通算成績'
      };

      const errorSummary = `${queryState.player.name}の${categoryNames[queryState.category.id]}クエリでエラーが発生`;
      
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
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 transition-colors duration-200">MLB Stats Assistant</h1>
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
          <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 transition-colors duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* アプリアイコン */}
                <div className="p-2 bg-blue-600 rounded-lg">
                  <Activity className="w-6 h-6 text-white" />
                </div>
                {/* アプリタイトルと説明 */}
                <div>
                  <h1 className="text-xl font-bold text-gray-900 dark:text-white transition-colors duration-200">MLB Stats Assistant</h1>
                  <p className="text-sm text-gray-600 dark:text-gray-300 transition-colors duration-200">
                    {uiMode === 'chat' && 'MLBの統計データについて質問してください'}
                    {uiMode === 'quick' && 'よく使われる質問をワンクリックで実行'}
                    {uiMode === 'custom' && 'カスタムクエリを作成して詳細な分析を実行'}
                  </p>
                </div>
              </div>
              
              {/* モード切り替えボタン */}
              <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1 transition-colors duration-200">
                <button
                  onClick={() => {
                    setUiMode('chat');
                    setQuickResult(null); // Clear quick result when switching to chat
                    setCustomResult(null); // Clear custom result when switching to chat
                  }}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                    uiMode === 'chat' 
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' 
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <MessageCircle className="w-4 h-4" />
                  チャット
                </button>
                <button
                  onClick={() => {
                    setUiMode('quick');
                    setCustomResult(null); // Clear custom result when switching to quick
                    // Keep quick result when switching to quick mode
                  }}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                    uiMode === 'quick' 
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' 
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Zap className="w-4 h-4" />
                  クイック質問
                </button>
                <button
                  onClick={() => {
                    setUiMode('custom');
                    setQuickResult(null); // Clear quick result when switching to custom
                    // Keep custom result when switching to custom mode
                  }}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                    uiMode === 'custom' 
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' 
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Settings className="w-4 h-4" />
                  カスタムクエリ
                </button>
              </div>
            </div>
          </div>

      {/* ===== メインコンテンツエリア ===== */}
      <div className="flex-1 overflow-y-auto">
        {uiMode === 'chat' ? (
          /* ===== メッセージ表示エリア ===== */
          <div className="px-6 py-4 space-y-4 h-full">
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
            <div className={`${message.isChart ? 'max-w-5xl' : 'max-w-2xl'} ${message.type === 'user' ? 'order-2' : ''}`}>
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
          <div className="px-6 py-8 h-full flex items-center justify-center">
            <QuickQuestions 
              onQuestionClick={handleQuickQuestion} 
              isLoading={isLoading}
              quickResult={quickResult}
              onClearResult={() => setQuickResult(null)}
            />
          </div>
        ) : (
          /* ===== カスタムクエリビルダーエリア ===== */
          <div className="px-6 py-8 h-full">
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
        <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4 transition-colors duration-200">
        <div className="flex gap-3 items-end">
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
            className="px-6 py-3 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium transition-colors duration-200"
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