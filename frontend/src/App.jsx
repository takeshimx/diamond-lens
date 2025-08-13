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

  // ===== モックデータ =====
  // 実際のAPIレスポンスの構造を模倣したサンプルデータ
  // 本番では削除し、実際のバックエンドAPIから取得する
  const mockMLBData = {
    "大谷翔平 2024 打率": {
      stats: { battingAverage: 0.285, homeRuns: 54, rbi: 130 },
      answer: "大谷翔平選手の2024年シーズンの打率は.285でした。54本塁打、130打点の素晴らしい成績を残しています。"
    },
    "ヤンキース 勝率": {
      stats: { wins: 82, losses: 80, winPercentage: 0.506 },
      answer: "ニューヨーク・ヤンキースの今シーズンの勝率は50.6%（82勝80敗）です。"
    },
    "ドジャース 防御率": {
      stats: { era: 3.45, strikeouts: 1456, whip: 1.18 },
      answer: "ロサンゼルス・ドジャースのチーム防御率は3.45です。奪三振数は1456個で、WHIPは1.18となっています。"
    }
  };

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
    try {
      // 【実際の実装】Q&AエンドポイントにPOSTリクエスト
      const response = await fetch('/qa/player-stats', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: query,
          season: 2024 // デフォルト値、必要に応じて動的に設定
        })
      });

      // HTTPエラーの場合は例外をスロー
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // レスポンスをJSONとして解析
      const aiResponse = await response.text(); // サービス関数がstrを返すため

      // フロントエンド用の形式に変換
      return {
        stats: null, // 統計データは回答テキストに含まれているため
        answer: aiResponse
      };

    } catch (error) {
      console.error('API呼び出しエラー:', error);
      
      // エラーの場合はユーザーフレンドリーなメッセージを返す
      return {
        stats: null,
        answer: `申し訳ございませんが、エラーが発生しました。しばらく後でもう一度お試しください。（${error.message}）`
      };
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
  const handleKeyPress = (e) => {
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

  // ===== メインUIレンダリング =====
  return (
    <div className="flex flex-col h-screen bg-gray-50">
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
              onKeyPress={handleKeyPress}
              placeholder="例: 大谷翔平の2024年の打率は？"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
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
            サンプル質問: 「大谷翔平 打率」「ヤンキース 勝率」「ドジャース 防御率」
          </p>
        </div>
      </div>
    </div>
  );
};

export default MLBChatApp;