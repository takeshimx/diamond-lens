/**
 * チャット送信（ストリーミング・非ストリーミング）と履歴クリアを管理するフック。
 *
 * @param {object} deps
 * @param {string} deps.inputMessage
 * @param {boolean} deps.isLoading
 * @param {string|null} deps.sessionId
 * @param {Function} deps.setMessages
 * @param {Function} deps.setInputMessage
 * @param {Function} deps.setIsLoading
 * @param {Function} deps.resetMessages
 * @param {Function} deps.clearSession
 * @param {Function} deps.getBackendURL
 * @param {Function} deps.getAuthHeaders
 * @param {Function} deps.callBackendAPI
 */

// 表示形式の明示指定がないあいまいなクエリを検出するキーワード定義
const FORMAT_TRIGGER_WORDS = ['スタッツ', '成績', '統計', 'データ'];
const FORMAT_EXPLICIT_WORDS = [
  '表で', 'テーブル', '一覧で', 'まとめて',
  'テキスト', '文章で', '箇条書き', 'グラフ', 'チャート',
];

const needsClarification = (query) => {
  const hasTrigger = FORMAT_TRIGGER_WORDS.some(w => query.includes(w));
  const hasExplicit = FORMAT_EXPLICIT_WORDS.some(w => query.includes(w));
  return hasTrigger && !hasExplicit;
};

export const useStreamChat = ({
  inputMessage,
  isLoading,
  sessionId,
  setMessages,
  setInputMessage,
  setIsLoading,
  setSessionId,
  resetMessages,
  clearSession,
  getBackendURL,
  getAuthHeaders,
  callBackendAPI,
}) => {

  // ===== 会話履歴クリア =====
  const handleClearHistory = async () => {
    if (!sessionId) {
      console.log('⚠️ セッションIDが存在しないため、クリアをスキップします');
      return;
    }

    try {
      console.log('🗑️ 会話履歴をクリアします - Session ID:', sessionId);

      const backendURL = getBackendURL();
      const endpoint = `${backendURL}/api/v1/qa/history/${sessionId}`;
      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, { method: 'DELETE', headers });

      if (!response.ok) throw new Error(`履歴クリアに失敗しました: ${response.status}`);

      const result = await response.json();
      console.log('✅ 履歴クリア成功:', result);

      resetMessages();
      clearSession();

      console.log('✅ フロントエンドの会話履歴もリセットしました');
    } catch (error) {
      console.error('❌ 履歴クリアエラー:', error);
      alert('会話履歴のクリアに失敗しました。');
    }
  };

  // ===== ストリーミング送信の共通ロジック =====
  const _sendStream = async (query, outputFormat) => {
    const botMessageId = Date.now() + 1;
    setMessages(prev => [...prev, {
      id: botMessageId, type: 'bot', content: '',
      isStreaming: true, streamingStatus: '準備中...', steps: [], timestamp: new Date(),
    }]);

    try {
      const baseURL = getBackendURL();
      const endpoint = `${baseURL}/api/v1/qa/agentic-stats-stream`;
      const headers = await getAuthHeaders();

      const requestBody = {
        query,
        season: new Date().getFullYear(),
        session_id: sessionId,
      };
      if (outputFormat) requestBody.output_format = outputFormat;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const streamRequestId = response.headers.get('X-Request-ID');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) { console.log('✅ Stream complete'); break; }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;

          const eventLines = line.split('\n');
          let eventType = 'message';
          let dataStr = '';

          for (const eventLine of eventLines) {
            if (eventLine.startsWith('event: ')) eventType = eventLine.substring(7).trim();
            else if (eventLine.startsWith('data: ')) dataStr = eventLine.substring(6).trim();
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            console.log(`📨 SSE Event [${eventType}]:`, data);

            setMessages(prev => prev.map(msg => {
              if (msg.id !== botMessageId) return msg;

              switch (eventType) {
                case 'session_start':
                  if (data.session_id) setSessionId(data.session_id);
                  return { ...msg, streamingStatus: '接続確立...' };

                case 'routing':
                  return { ...msg, streamingStatus: data.message || `${data.agent_type}エージェントで処理中...` };

                case 'state_update': {
                  const statusLabels = { oracle: '質問を分析中 🤔', executor: 'データ取得中 🔍', synthesizer: '回答生成中 ✍️' };
                  const newStep = { node: data.node, status: data.status, message: data.message, detail: data.detail, timestamp: data.timestamp, step_type: data.step_type };
                  return { ...msg, streamingStatus: statusLabels[data.node] || data.message, steps: [...(msg.steps || []), newStep] };
                }

                case 'tool_start': {
                  const step = { tool_name: data.tool_name, message: data.message, timestamp: data.timestamp, step_type: data.step_type };
                  return { ...msg, streamingStatus: data.message || `🔧 ${data.tool_name} 実行中...`, steps: [...(msg.steps || []), step] };
                }

                case 'tool_end': {
                  const step = { tool_name: data.tool_name, message: data.message, timestamp: data.timestamp, step_type: data.step_type, output_summary: data.output_summary };
                  return { ...msg, streamingStatus: data.message || `✅ ${data.tool_name} 完了`, steps: [...(msg.steps || []), step] };
                }

                case 'token':
                  return { ...msg, content: msg.content + data.content };

                case 'final_answer':
                  return {
                    ...msg,
                    content: data.answer || msg.content,
                    isStreaming: false, streamingStatus: undefined,
                    requestId: streamRequestId,
                    isTable: data.isTable, tableData: data.tableData, columns: data.columns, isTransposed: data.isTransposed,
                    isChart: data.isChart, chartType: data.chartType, chartData: data.chartData, chartConfig: data.chartConfig,
                    isMatchupCard: data.isMatchupCard, matchupData: data.matchupData,
                    isStrategyReport: data.isStrategyReport || false, strategyData: data.strategyData || null,
                    isAgentic: true,
                  };

                case 'stream_end':
                  return { ...msg, isStreaming: false, streamingStatus: undefined };

                case 'error':
                  return { ...msg, content: `エラー: ${data.message}`, isStreaming: false, streamingStatus: undefined, isError: true };

                default:
                  return msg;
              }
            }));
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError, dataStr);
          }
        }
      }

    } catch (error) {
      console.error('❌ Stream Error:', error);
      setMessages(prev => prev.map(msg => {
        if (msg.id !== botMessageId) return msg;
        const errorStep = { message: `接続エラー: ${error.message}`, timestamp: new Date().toISOString(), step_type: 'error', status: 'error' };
        return { ...msg, content: msg.content || 'エラーが発生しました。再度お試しください。', isStreaming: false, streamingStatus: undefined, isError: true, steps: [...(msg.steps || []), errorStep] };
      }));
    } finally {
      setIsLoading(false);
    }
  };

  // ===== ストリーミング送信（メイン） =====
  const handleSendMessageStream = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const currentQuery = inputMessage;
    const userMessage = { id: Date.now(), type: 'user', content: currentQuery, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');

    // あいまいなクエリは表示形式を選択させる
    if (needsClarification(currentQuery)) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'clarification',
        pendingQuery: currentQuery,
        timestamp: new Date(),
      }]);
      return;
    }

    setIsLoading(true);
    await _sendStream(currentQuery, null);
  };

  // ===== 表示形式選択後の送信 =====
  const handleFormatSelect = async (clarificationId, pendingQuery, outputFormat) => {
    // 選択済みとしてマーク
    setMessages(prev => prev.map(msg =>
      msg.id === clarificationId
        ? { ...msg, resolved: true, selectedFormat: outputFormat }
        : msg
    ));
    setIsLoading(true);
    await _sendStream(pendingQuery, outputFormat);
  };

  // ===== 非ストリーミング送信（予備） =====
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = { id: Date.now(), type: 'user', content: inputMessage, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await callBackendAPI(inputMessage);

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: response.answer,
        requestId: response.requestId,
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
        isAgentic: response.isAgentic,
        steps: response.steps,
        isMatchupCard: response.isMatchupCard,
        matchupData: response.matchupData,
        isStrategyReport: response.isStrategyReport || false,
        strategyData: response.strategyData || null,
        qualityWarning: response.qualityWarning || null,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('❌ Chat API Error:', error);
      setMessages(prev => [...prev, {
        id: Date.now() + 1, type: 'bot',
        content: 'エラーが発生しました。しばらく後でもう一度お試しください。',
        timestamp: new Date(),
      }]);
    }

    setIsLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessageStream();
    }
  };

  return { handleClearHistory, handleSendMessage, handleSendMessageStream, handleFormatSelect, handleKeyDown };
};
