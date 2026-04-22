import { Menu, Trash2 } from 'lucide-react';

const MODE_LABELS = {
  chat: 'MLBの統計データについて質問してください',
  quick: 'よく使われる質問をワンクリックで実行',
  custom: 'カスタムクエリを作成して詳細な分析を実行',
  statistics: '統計分析モデルを使用してチームの勝率を予測',
  segmentation: 'K-meansクラスタリングで選手タイプを分析',
  'stuff-plus': '球質（Stuff+）評価',
  'advanced-stats': 'Advanced Stats Rankings',
  'hot-slump': '直近7日スタッツで打者のホット/スランプをランキング',
  leaderboard: '打者・投手のシーズンリーダーボード',
  live: '進行中の試合をリアルタイム表示',
  monitor: '全試合をグリッドで一覧監視・異常検知',
  standings: 'MLB順位表（AL/NL ディビジョン別）',
  'player-profile': '選手名を検索してプロフィール・KPIを確認',
};

const ChatTopBar = ({ sidebarOpen, setSidebarOpen, uiMode, sessionId, handleClearHistory }) => (
  <div className="flex items-center gap-3 px-4 h-14 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex-shrink-0 transition-colors duration-200">
    <button
      onClick={() => setSidebarOpen(!sidebarOpen)}
      className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
    >
      <Menu className="w-5 h-5" />
    </button>

    <div className="flex-1 min-w-0">
      <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
        {MODE_LABELS[uiMode] ?? ''}
      </p>
    </div>

    {uiMode === 'chat' && sessionId && (
      <button
        onClick={handleClearHistory}
        className="p-1.5 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 flex-shrink-0"
        title="会話履歴をクリア"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    )}
  </div>
);

export default ChatTopBar;
