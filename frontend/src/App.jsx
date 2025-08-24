import React, { useState, useRef, useEffect } from 'react';
import { Send, TrendingUp, User, Bot, Activity } from 'lucide-react';

const MLBChatApp = () => {
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

  // 重要: 簡易的なパスワード認証用（本番では安全な方法を使用）
  const CORRECT_PASSWORD = (import.meta.env.VITE_APP_PASSWORD || 'defaultpassword').trim();
  
  // // Debug: Log the expected password (remove in production)
  // console.log('🔐 Debug: Expected password:', CORRECT_PASSWORD);
  // console.log('🔐 Debug: Password length:', CORRECT_PASSWORD.length);
  // console.log('🔐 Debug: Environment variables:', import.meta.env);

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
  // バックエンドAPIを呼び出してMLBデータとGemini回答を取得する関数
  const callBackendAPI = async (query) => {
    console.log('🚀 デバッグ：API呼び出し開始:', query);
    
    // Environment-aware backend URL detection (Cloud Run, Codespaces, localhost)
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
        stats: apiResponse.stats || null
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
          stats: null
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
        stats: null
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
        timestamp: new Date()
      };

      // メッセージ履歴にボットメッセージを追加
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
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
      <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
        {/* カードヘッダー */}
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-semibold text-blue-800">統計データ</span>
        </div>
        {/* 統計データをキー・バリューペアで表示 */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(stats).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-gray-600">{key}:</span>
              <span className="font-semibold">{value}</span>
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
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">{group.name}</h4>
                  <div className="inline-block min-w-full align-middle">
                    <div className="overflow-hidden border border-gray-200 rounded-lg">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              項目
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              値
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {groupColumns.map((column, index) => (
                            <tr key={column.key} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                                {column.label}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
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
            <div className="overflow-hidden border border-gray-200 rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      項目
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      値
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {columns.map((column, index) => (
                    <tr key={column.key} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                        {column.label}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
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
          <div className="overflow-hidden border border-gray-200 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {columns.map((column) => (
                    <th
                      key={column.key}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tableData.map((row, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap"
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
    <div className="flex flex-col h-screen bg-gray-50">
      {!isAuthenticated ? (
        // ===== 認証画面 =====
        <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
          <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">
            {/* ヘッダー */}
            <div className="text-center mb-6">
              <div className="mx-auto w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
                <Activity className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">MLB Stats Assistant</h1>
              <p className="text-gray-600">アクセスにはパスワードが必要です</p>
            </div>
            
            {/* パスワード入力フォーム */}
            <div className="space-y-4">
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  パスワード
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={handleAuthKeyDown}
                  placeholder="パスワードを入力してください"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent text-gray-900"
                  disabled={isCheckingAuth}
                />
              </div>
              
              {/* エラーメッセージ */}
              {authError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{authError}</p>
                </div>
              )}
              
              {/* ログインボタン */}
              <button
                onClick={handleAuthentication}
                disabled={!password.trim() || isCheckingAuth}
                className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
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
          <div className="bg-white border-b border-gray-200 px-6 py-4">
            <div className="flex items-center gap-3">
              {/* アプリアイコン */}
              <div className="p-2 bg-blue-600 rounded-lg">
                <Activity className="w-6 h-6 text-white" />
              </div>
              {/* アプリタイトルと説明 */}
              <div>
                <h1 className="text-xl font-bold text-gray-900">MLB Stats Assistant</h1>
                <p className="text-sm text-gray-600">MLBの統計データについて質問してください</p>
              </div>
            </div>
          </div>

      {/* ===== メッセージ表示エリア ===== */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {/* 各メッセージをレンダリング */}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {/* ボットアバター（ボットメッセージの場合のみ表示） */}
            {message.type === 'bot' && (
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}
            
            {/* メッセージ本体 */}
            <div className={`max-w-2xl ${message.type === 'user' ? 'order-2' : ''}`}>
              {/* メッセージバブル */}
              <div
                className={`px-4 py-3 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-blue-600 text-white' // ユーザーメッセージは青背景
                    : 'bg-white border border-gray-200 text-gray-900' // ボットメッセージは白背景
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
                {/* 統計データカード（データがある場合のみ表示） */}
                {message.stats && <StatCard stats={message.stats} />}
              </div>
              {/* タイムスタンプ */}
              <p className={`text-xs text-gray-500 mt-1 ${
                message.type === 'user' ? 'text-right' : 'text-left'
              }`}>
                {formatTime(message.timestamp)}
              </p>
            </div>

            {/* ユーザーアバター（ユーザーメッセージの場合のみ表示） */}
            {message.type === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0 order-3">
                <User className="w-5 h-5 text-white" />
              </div>
            )}
          </div>
        ))}

        {/* ===== ローディングアニメーション ===== */}
        {/* API呼び出し中に表示される点滅アニメーション */}
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
              <div className="flex gap-1">
                {/* 3つの点が順番に点滅するアニメーション */}
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
              </div>
            </div>
          </div>
        )}
        
        {/* 自動スクロール用の要素 */}
        <div ref={messagesEndRef} />
      </div>

      {/* ===== メッセージ入力エリア ===== */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="flex gap-3 items-end">
          {/* テキストエリア */}
          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="例: 大谷翔平の2024年の打率は？"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-gray-900 placeholder-gray-500"
              rows="2"
              disabled={isLoading} // ローディング中は入力を無効化
            />
          </div>
          {/* 送信ボタン */}
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading} // 入力が空またはローディング中は無効化
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
          >
            <Send className="w-4 h-4" />
            送信
          </button>
        </div>
        
        {/* サンプル質問の表示 */}
        <div className="mt-3 text-center">
          <p className="text-xs text-gray-500">
            サンプル質問: 「大谷翔平 打率」「ヤンキース 勝率」「2024年のホームラン王トップ10を表で」
          </p>
        </div>
      </div>
        </>
      )}
    </div>
  );
};

export default MLBChatApp;