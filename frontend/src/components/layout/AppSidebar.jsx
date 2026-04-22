import {
  Activity, MessageCircle, Zap, Settings, Users, Target, BarChart3,
  TrendingUp, Trophy, Radio, LayoutDashboard, Medal, User, LogOut,
} from 'lucide-react';

const NAV_ITEMS = [
  { mode: 'chat', icon: MessageCircle, label: 'チャット' },
  { mode: 'quick', icon: Zap, label: 'クイック質問' },
  // { mode: 'custom', icon: Settings, label: 'カスタムクエリ' },
  { mode: 'statistics', icon: Activity, label: '統計分析' },
  { mode: 'segmentation', icon: Users, label: '選手分類' },
  { mode: 'stuff-plus', icon: Target, label: '球質評価' },
  { mode: 'advanced-stats', icon: BarChart3, label: 'Advanced Stats' },
  { mode: 'hot-slump', icon: TrendingUp, label: 'Hot / Slump' },
  { mode: 'leaderboard', icon: Trophy, label: 'リーダーボード' },
  { mode: 'live', icon: Radio, label: '試合速報' },
  { mode: 'monitor', icon: LayoutDashboard, label: 'モニターボード' },
  { mode: 'standings', icon: Medal, label: '順位表' },
  { mode: 'player-profile', icon: User, label: '選手プロフィール' },
];

const AppSidebar = ({ sidebarOpen, setSidebarOpen, uiMode, setUiMode, setQuickResult, setCustomResult, logout }) => (
  <aside className={`fixed inset-y-0 left-0 z-30 flex flex-col bg-gray-900 border-r border-gray-700 transition-all duration-300 md:relative md:translate-x-0 ${sidebarOpen ? 'translate-x-0 w-56' : '-translate-x-full md:translate-x-0 md:w-14'}`}>
    <div className="flex items-center gap-3 px-3 h-14 border-b border-gray-700 flex-shrink-0">
      <div className="p-1.5 bg-blue-600 rounded-lg flex-shrink-0">
        <Activity className="w-4 h-4 text-white" />
      </div>
      {sidebarOpen && <span className="font-bold text-white text-sm truncate">Diamond Lens</span>}
    </div>

    <nav className="flex-1 py-2 flex flex-col gap-0.5 px-2 overflow-y-auto scrollbar-none">
      {NAV_ITEMS.map(({ mode, icon: Icon, label }) => (
        <button
          key={mode}
          onClick={() => {
            setUiMode(mode);
            setQuickResult(null);
            setCustomResult(null);
            if (window.innerWidth < 768) setSidebarOpen(false);
          }}
          title={!sidebarOpen ? label : undefined}
          className={`flex items-center gap-3 px-2 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 w-full ${sidebarOpen ? '' : 'justify-center'} ${uiMode === mode ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}
        >
          <Icon className="w-4 h-4 flex-shrink-0" />
          {sidebarOpen && <span className="truncate">{label}</span>}
        </button>
      ))}
    </nav>

    <div className="border-t border-gray-700 p-2 flex-shrink-0">
      <button
        onClick={logout}
        title={!sidebarOpen ? 'ログアウト' : undefined}
        className={`flex items-center gap-3 px-2 py-2.5 rounded-lg text-sm text-gray-400 hover:text-red-400 hover:bg-gray-700 transition-colors w-full ${sidebarOpen ? '' : 'justify-center'}`}
      >
        <LogOut className="w-4 h-4 flex-shrink-0" />
        {sidebarOpen && <span>ログアウト</span>}
      </button>
    </div>
  </aside>
);

export default AppSidebar;
