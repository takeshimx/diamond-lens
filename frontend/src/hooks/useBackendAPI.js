/**
 * バックエンドURL検出・認証ヘッダー生成・チャットAPI呼び出し・選手検索を提供するフック。
 *
 * @param {object} deps
 * @param {Function} deps.getIdToken  - useAuth が返す Firebase ID トークン取得関数
 * @param {string|null} deps.sessionId  - 現在のチャットセッションID
 * @param {Function} deps.setSessionId  - セッションID更新関数
 * @param {boolean} deps.isAgentMode  - エージェントモードのON/OFF
 */
export const useBackendAPI = ({ getIdToken, sessionId, setSessionId, isAgentMode }) => {

  // ===== 環境別バックエンドURL検出 =====
  const getBackendURL = () => {
    console.log('🔍 デバッグ：getBackendURL called');
    console.log('🔍 デバッグ：window.location.hostname:', window.location.hostname);

    if (window.location.hostname.includes('run.app')) {
      const backendURL = 'https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app';
      console.log('🔄 デバッグ：Cloud Run environment detected, using backend URL:', backendURL);
      return backendURL;
    }

    if (window.location.hostname.includes('github.dev')) {
      const frontendHostname = window.location.hostname;
      console.log('🔍 デバッグ：Codespaces environment, original frontend hostname:', frontendHostname);
      const backendHostname = frontendHostname.replace('-5173.app.github.dev', '-8000.app.github.dev');
      const backendURL = `https://${backendHostname}`;
      console.log('🔄 デバッグ：Final backend URL:', backendURL);
      return backendURL;
    }

    console.log('🔍 デバッグ：Using localhost fallback');
    return 'http://localhost:8000';
  };

  // ===== 認証ヘッダー生成 =====
  const getAuthHeaders = async () => {
    const idToken = await getIdToken();
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
    };
  };

  // ===== 選手検索 =====
  const searchPlayers = async (searchTerm, signal) => {
    const baseURL = getBackendURL();
    const endpoint = `${baseURL}/api/v1/players/search?q=${encodeURIComponent(searchTerm)}`;
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, { headers, signal });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      return data.results || [];
    } catch (error) {
      if (error.name === 'AbortError') return [];
      console.error('選手検索API呼び出しエラー:', error);
      return [];
    }
  };

  // ===== メインチャットAPI呼び出し =====
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

      const endpoint = isAgentMode
        ? `${baseURL}/api/v1/qa/agentic-stats`
        : `${baseURL}/api/v1/qa/player-stats`;
      console.log('🎯 デバッグ：Final complete endpoint:', endpoint);

      const requestBody = {
        query: query,
        season: new Date().getFullYear(),
        session_id: sessionId,
      };

      console.log('📤 デバッグ：Sending request to:', endpoint);
      console.log('📤 デバッグ：Request body:', JSON.stringify(requestBody, null, 2));

      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log('⏰ デバッグ：リクエストタイムアウト（120秒）');
        controller.abort();
      }, 120000);

      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
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

      const requestId = response.headers.get('X-Request-ID');
      console.log(`🔗 Request ID: ${requestId}`);

      if (apiResponse.session_id) {
        console.log('💾 デバッグ：セッションID保存:', apiResponse.session_id);
        setSessionId(apiResponse.session_id);
      }

      return {
        answer: apiResponse.answer || "回答を受信しましたが、内容が空でした。",
        requestId,
        isTable: apiResponse.isTable || false,
        isAgentic: apiResponse.is_agentic || false,
        steps: apiResponse.steps || [],
        isTransposed: apiResponse.isTransposed || false,
        tableData: apiResponse.tableData || null,
        columns: apiResponse.columns || null,
        decimalColumns: apiResponse.decimalColumns || [],
        grouping: apiResponse.grouping || null,
        stats: apiResponse.stats || null,
        isChart: apiResponse.isChart || false,
        chartType: apiResponse.chartType || null,
        chartData: apiResponse.chartData || null,
        chartConfig: apiResponse.chartConfig || null,
        isMatchupCard: apiResponse.isMatchupCard || false,
        matchupData: apiResponse.matchupData || null,
        isStrategyReport: apiResponse.isStrategyReport || false,
        strategyData: apiResponse.strategyData || null,
        qualityWarning: apiResponse.quality_warning || null,
      };

    } catch (error) {
      console.error('❌ デバッグ：API呼び出しエラー:', error);

      if (error.name === 'AbortError') {
        return {
          answer: 'リクエストがタイムアウトしました（60秒）。バックエンドの処理が重い可能性があります。',
          requestId: null, isTable: false, isTransposed: false, tableData: null,
          columns: null, decimalColumns: [], grouping: null, stats: null,
          isChart: false, chartType: null, chartData: null, chartConfig: null,
        };
      }

      return {
        answer: `エラーが発生しました: ${error.message}`,
        requestId: null, isTable: false, isTransposed: false, tableData: null,
        columns: null, decimalColumns: [], grouping: null, stats: null,
        isChart: false, chartType: null, chartData: null, chartConfig: null,
      };
    }
  };

  return { getBackendURL, getAuthHeaders, callBackendAPI, searchPlayers };
};
