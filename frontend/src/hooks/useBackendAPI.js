/**
 * バックエンドURL検出・認証ヘッダー生成・チャットAPI呼び出し・選手検索を提供するフック。
 *
 * @param {object} deps
 * @param {Function} deps.getIdToken  - useAuth が返す Firebase ID トークン取得関数
 * @param {string|null} deps.sessionId  - 現在のチャットセッションID
 * @param {Function} deps.setSessionId  - セッションID更新関数
 * @param {boolean} deps.isAgentMode  - エージェントモードのON/OFF
 */
// ===== feature flag =====
// 新しい統合オートコンプリート API (/api/v1/players/autocomplete) を使うか。
// 既存 4 系統 (/players/search, /advanced-stats/{pitching|batting}/search,
// /stuff-plus/search) からの段階移行用。
// .env で VITE_USE_AUTOCOMPLETE_API=true にすると有効。
export const USE_AUTOCOMPLETE_API =
  String(import.meta.env.VITE_USE_AUTOCOMPLETE_API).toLowerCase() === 'true';

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
  // USE_AUTOCOMPLETE_API=true のとき新統合エンドポイントを叩き、
  // 新形式 (mlbid, full_name, team) を旧形式 (mlbid, player_name, team, league) に
  // マッピングして既存呼び出し側との互換を保つ。
  const searchPlayers = async (searchTerm, signal) => {
    const baseURL = getBackendURL();
    const endpoint = USE_AUTOCOMPLETE_API
      ? `${baseURL}/api/v1/players/autocomplete?q=${encodeURIComponent(searchTerm)}&context=all&limit=10`
      : `${baseURL}/api/v1/players/search?q=${encodeURIComponent(searchTerm)}`;
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, { headers, signal });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      const results = data.results || [];

      if (USE_AUTOCOMPLETE_API) {
        return results.map((item) => ({
          mlbid: item.mlbid,
          player_name: item.full_name,
          team: item.team || null,
          league: null, // 新 API は league を返さない（Vol.1 スコープ外）
        }));
      }
      return results;
    } catch (error) {
      if (error.name === 'AbortError') return [];
      console.error('選手検索API呼び出しエラー:', error);
      return [];
    }
  };

  // ===== Statcast 投手・打者検索（AdvancedStats trends 用） =====
  // category: 'pitching' | 'batting'
  // 旧 API は配列を直接返す: [{pitcher_id|batter_id, player_name, team}]
  // 新 API は {results: [{mlbid, full_name, team, ...}]} を返すので、
  // ID 名のエイリアス (mlbid → pitcher_id / batter_id) を吸収して旧形式に揃える。
  const searchAdvancedStatsPlayers = async (searchTerm, category, season, signal) => {
    const baseURL = getBackendURL();
    const isPitching = category === 'pitching';

    const endpoint = USE_AUTOCOMPLETE_API
      ? `${baseURL}/api/v1/players/autocomplete?q=${encodeURIComponent(searchTerm)}&context=${
          isPitching ? 'statcast_pitcher' : 'statcast_batter'
        }&season=${season}&limit=10`
      : `${baseURL}/api/v1/advanced-stats/${
          isPitching ? 'pitching' : 'batting'
        }/search?name=${encodeURIComponent(searchTerm)}&season=${season}&limit=10`;

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, { headers, signal });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();

      if (USE_AUTOCOMPLETE_API) {
        const results = data.results || [];
        const idKey = isPitching ? 'pitcher_id' : 'batter_id';
        return results.map((item) => ({
          [idKey]: item.mlbid,
          player_name: item.full_name,
          team: item.team || '',
        }));
      }
      return Array.isArray(data) ? data : [];
    } catch (error) {
      if (error.name === 'AbortError') return [];
      console.error('Statcast 選手検索 API 呼び出しエラー:', error);
      return [];
    }
  };

  // ===== Stuff+ 投手検索 =====
  // 旧 API: [{pitcher_id, player_name, team, hand}]
  // 新 API: {results: [...]} → pitcher_id にエイリアス
  const searchStuffPlusPitchers = async (searchTerm, season, signal) => {
    const baseURL = getBackendURL();
    const endpoint = USE_AUTOCOMPLETE_API
      ? `${baseURL}/api/v1/players/autocomplete?q=${encodeURIComponent(searchTerm)}&context=stuffplus&season=${season}&limit=10`
      : `${baseURL}/api/v1/stuff-plus/search?name=${encodeURIComponent(searchTerm)}&season=${season}&limit=10`;

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, { headers, signal });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();

      if (USE_AUTOCOMPLETE_API) {
        const results = data.results || [];
        return results.map((item) => ({
          pitcher_id: item.mlbid,
          player_name: item.full_name,
          team: item.team || '',
          hand: item.pitch_hand || '',
        }));
      }
      return Array.isArray(data) ? data : [];
    } catch (error) {
      if (error.name === 'AbortError') return [];
      console.error('Stuff+ 選手検索 API 呼び出しエラー:', error);
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

  return {
    getBackendURL,
    getAuthHeaders,
    callBackendAPI,
    searchPlayers,
    searchAdvancedStatsPlayers,
    searchStuffPlusPitchers,
  };
};
