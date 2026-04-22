import React, { useState, useEffect } from 'react';
import QuickQuestions from './components/QuickQuestions.jsx';
import CustomQueryBuilder from './components/CustomQueryBuilder.jsx';
import StatisticalAnalysis from './components/StatisticalAnalysis.jsx';
import PlayerSegmentation from './components/PlayerSegmentation.jsx';
import PitcherFatigue from './components/PitcherFatigue.jsx';
import PitcherWhiffPredictor from './components/PitcherWhiffPredictor.jsx';
import StuffPlus from './components/StuffPlus.jsx';
import AdvancedStats from './components/AdvancedStats.jsx';
import LiveScoreboard from './components/LiveScoreboard.jsx';
import LiveMonitorBoard from './components/LiveMonitorBoard.jsx';
import Standings from './components/Standings.jsx';
import Leaderboard from './components/Leaderboard.jsx';
import HotSlumpDashboard from './components/HotSlumpDashboard.jsx';
import PlayerProfile from './components/PlayerProfile.jsx';
import VoiceInput from './components/VoiceInput.jsx';
import { useAuth } from './hooks/useAuth';
import { useSession } from './hooks/useSession.js';
import { useBackendAPI } from './hooks/useBackendAPI.js';
import { useFixedQueryAPI } from './hooks/useFixedQueryAPI.js';
import { useFeedback } from './hooks/useFeedback.js';
import { useMessages } from './hooks/useMessages.js';
import { useQuickQuery } from './hooks/useQuickQuery.js';
import { useCustomQuery } from './hooks/useCustomQuery.js';
import { useStreamChat } from './hooks/useStreamChat.js';
import LoginScreen from './components/layout/LoginScreen.jsx';
import AppSidebar from './components/layout/AppSidebar.jsx';
import ChatTopBar from './components/layout/ChatTopBar.jsx';
import ChatInputArea from './components/layout/ChatInputArea.jsx';
import ChatMessageList from './components/layout/ChatMessageList.jsx';

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
  const {
    messages, setMessages,
    inputMessage, setInputMessage,
    isLoading, setIsLoading,
    messagesEndRef,
    resetMessages,
    formatTime,
    handleVoiceTranscript,
  } = useMessages();

  // Firebase認証（Googleログイン）
  const { user, loading: authLoading, error: authError, loginWithGoogle, logout, getIdToken } = useAuth();
  const [isCheckingAuth, setIsCheckingAuth] = useState(false);

  // UIモード管理のstate
  const [uiMode, setUiMode] = useState('chat'); // 'chat', 'quick', 'custom', 'statistics', 'segmentation', 'fatigue', 'pitcher-whiff'
  const [sidebarOpen, setSidebarOpen] = useState(true);


  // エージェントモード（推論ループ）のON/OFF
  const [isAgentMode, setIsAgentMode] = useState(false);

  // ★ 会話履歴用のセッションID管理 ★
  const { sessionId, setSessionId, clearSession } = useSession();

  // ===== API フック =====
  // getBackendURL / getAuthHeaders / callBackendAPI / searchPlayers
  const { getBackendURL, getAuthHeaders, callBackendAPI, searchPlayers } = useBackendAPI({
    getIdToken,
    sessionId,
    setSessionId,
    isAgentMode,
  });

  const { callFixedQueryAPI } = useFixedQueryAPI({ getBackendURL, getAuthHeaders });

  // ===== クイック質問 =====
  const { quickResult, setQuickResult, handleQuickQuestion } = useQuickQuery({ callFixedQueryAPI, setIsLoading });

  // ===== カスタムクエリ =====
  const { customResult, setCustomResult, handleCustomQuery } = useCustomQuery({ callFixedQueryAPI, getBackendURL, getAuthHeaders, setIsLoading });

  // ===== フィードバック =====
  const {
    feedbackState,
    activeFeedbackForm,
    setActiveFeedbackForm,
    feedbackFormData,
    setFeedbackFormData,
    handleFeedback,
  } = useFeedback({ getBackendURL, getAuthHeaders, sessionId });

  // ===== チャット送信・履歴クリア =====
  const { handleClearHistory, handleSendMessage, handleSendMessageStream, handleKeyDown } = useStreamChat({
    inputMessage, isLoading, sessionId,
    setMessages, setInputMessage, setIsLoading, setSessionId, resetMessages, clearSession,
    getBackendURL, getAuthHeaders, callBackendAPI,
  });

  // Googleログイン処理
  const handleGoogleLogin = async () => {
    setIsCheckingAuth(true);
    try {
      await loginWithGoogle();
    } catch (err) {
      // エラーは useAuth 内で処理済み
    } finally {
      setIsCheckingAuth(false);
    }
  };


  // ===== メインUIレンダリング =====
  return (
    <div className="flex flex-col h-screen w-full bg-white dark:bg-gray-900 transition-colors duration-200" data-theme-test>
      {authLoading ? (
        <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-black">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : !user ? (
        <LoginScreen
          authError={authError}
          isCheckingAuth={isCheckingAuth}
          handleGoogleLogin={handleGoogleLogin}
        />
      ) : (
        <div className="flex flex-row flex-1 min-h-0 overflow-hidden">
          {/* モバイルオーバーレイ */}
          {sidebarOpen && (
            <div className="fixed inset-0 z-20 bg-black/60 md:hidden" onClick={() => setSidebarOpen(false)} />
          )}
          <AppSidebar
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
            uiMode={uiMode}
            setUiMode={setUiMode}
            setQuickResult={setQuickResult}
            setCustomResult={setCustomResult}
            logout={logout}
          />
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <ChatTopBar
              sidebarOpen={sidebarOpen}
              setSidebarOpen={setSidebarOpen}
              uiMode={uiMode}
              sessionId={sessionId}
              handleClearHistory={handleClearHistory}
            />
            <div className="flex-1 overflow-y-auto">
              {uiMode === 'chat' ? (
                <ChatMessageList
                  messages={messages}
                  feedbackState={feedbackState}
                  activeFeedbackForm={activeFeedbackForm}
                  feedbackFormData={feedbackFormData}
                  setFeedbackFormData={setFeedbackFormData}
                  setActiveFeedbackForm={setActiveFeedbackForm}
                  handleFeedback={handleFeedback}
                  messagesEndRef={messagesEndRef}
                  formatTime={formatTime}
                />
              ) : uiMode === 'quick' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full flex items-center justify-center">
                  <QuickQuestions
                    onQuestionClick={handleQuickQuestion}
                    isLoading={isLoading}
                    quickResult={quickResult}
                    onClearResult={() => setQuickResult(null)}
                  />
                </div>
              ) : uiMode === 'statistics' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
                  <StatisticalAnalysis />
                </div>
              ) : uiMode === 'segmentation' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
                  <PlayerSegmentation />
                </div>
              ) : uiMode === 'stuff-plus' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
                  <StuffPlus />
                </div>
              ) : uiMode === 'advanced-stats' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
                  <AdvancedStats />
                </div>
              ) : uiMode === 'fatigue' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
                  <PitcherFatigue />
                </div>
              ) : uiMode === 'pitcher-whiff' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
                  <PitcherWhiffPredictor />
                </div>
              ) : uiMode === 'hot-slump' ? (
                <div className="h-full overflow-y-auto">
                  <HotSlumpDashboard />
                </div>
              ) : uiMode === 'leaderboard' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full">
                  <Leaderboard />
                </div>
              ) : uiMode === 'live' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full w-full">
                  <LiveScoreboard />
                </div>
              ) : uiMode === 'monitor' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full w-full">
                  <LiveMonitorBoard />
                </div>
              ) : uiMode === 'standings' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full w-full">
                  <Standings />
                </div>
              ) : uiMode === 'player-profile' ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 h-full w-full">
                  <PlayerProfile
                    onSearchPlayers={searchPlayers}
                    getAuthHeaders={getAuthHeaders}
                    getBackendURL={getBackendURL}
                  />
                </div>
              ) : (
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
            {uiMode === 'chat' && (
              <ChatInputArea
                inputMessage={inputMessage}
                setInputMessage={setInputMessage}
                handleKeyDown={handleKeyDown}
                isLoading={isLoading}
                handleSendMessageStream={handleSendMessageStream}
                isAgentMode={isAgentMode}
                setIsAgentMode={setIsAgentMode}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// メインアプリケーション（ダークモード固定）
const App = () => {
  return <MLBChatApp />;
};

export default App;