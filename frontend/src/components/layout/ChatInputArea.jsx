import { Send, Brain } from 'lucide-react';

const ChatInputArea = ({
  inputMessage,
  setInputMessage,
  handleKeyDown,
  isLoading,
  handleSendMessageStream,
  isAgentMode,
  setIsAgentMode,
}) => (
  <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 sm:px-6 py-4 transition-colors duration-200">
    <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
      {/* エージェントモード切替トグル */}
      <div className="flex items-center gap-2 mb-2 sm:mb-0">
        <button
          onClick={() => setIsAgentMode(!isAgentMode)}
          title={isAgentMode ? 'エージェントモード：ON' : 'エージェントモード：OFF'}
          className={`p-3 rounded-lg transition-all duration-200 flex items-center gap-2 ${isAgentMode
            ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/30'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
        >
          <Brain className={`w-5 h-5 ${isAgentMode ? 'animate-pulse' : ''}`} />
          <span className="text-xs font-bold sm:hidden">エージェント</span>
        </button>
      </div>

      {/* テキストエリア */}
      <div className="flex-1">
        <textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="例: 大谷翔平の2024年の打率は？"
          className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 bg-white dark:bg-gray-700 transition-colors duration-200"
          rows="2"
          disabled={isLoading}
        />
      </div>

      {/* 送信ボタン */}
      <button
        onClick={handleSendMessageStream}
        disabled={!inputMessage.trim() || isLoading}
        className="px-4 sm:px-6 py-3 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium transition-colors duration-200 w-full sm:w-auto"
      >
        <Send className="w-4 h-4" />
        🌊 送信
      </button>
    </div>

    <div className="mt-3 text-center">
      <p className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
        サンプル質問: 「大谷翔平 打率」「ヤンキース 勝率」「2024年のホームラン王トップ10を表で」
      </p>
    </div>
  </div>
);

export default ChatInputArea;
