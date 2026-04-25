import { useState, useEffect } from 'react';
import QuickQuestions from './components/QuickQuestions.jsx';
import StatisticalAnalysis from './components/StatisticalAnalysis.jsx';
import PlayerSegmentation from './components/PlayerSegmentation.jsx';
import StuffPlus from './components/StuffPlus.jsx';
import AdvancedStats from './components/AdvancedStats.jsx';
import LiveScoreboard from './components/LiveScoreboard.jsx';
import LiveMonitorBoard from './components/LiveMonitorBoard.jsx';
import Standings from './components/Standings.jsx';
import Leaderboard from './components/Leaderboard.jsx';
import HotSlumpDashboard from './components/HotSlumpDashboard.jsx';
import PlayerProfile from './components/PlayerProfile.jsx';
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
import Topbar from './components/layout/ChatTopBar.jsx';
import Ticker from './components/layout/Ticker.jsx';
import ChatScreen from './components/layout/ChatScreen.jsx';
import { DLMark } from './components/layout/Icon.jsx';

// ============================================================
// Placeholder — 未実装画面のフォールバック
// ============================================================
const Placeholder = ({ label }) => (
  <div style={{
    flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
    flexDirection: "column", gap: 14, color: "var(--ink-3)",
  }}>
    <DLMark size={48}/>
    <div className="h-display" style={{ fontSize: 22, color: "var(--ink-1)" }}>{label}</div>
    <div className="t-mono" style={{ fontSize: 11, color: "var(--ink-4)", letterSpacing: "0.1em" }}>
      MODULE · 準備中
    </div>
  </div>
);

// ============================================================
// Main app
// ============================================================
const MLBChatApp = () => {
  // ===== STATE =====
  const {
    messages, setMessages,
    inputMessage, setInputMessage,
    isLoading, setIsLoading,
    messagesEndRef,
    resetMessages,
    formatTime,
  } = useMessages();

  const { user, loading: authLoading, error: authError, loginWithGoogle, logout, getIdToken } = useAuth();
  const [isCheckingAuth, setIsCheckingAuth] = useState(false);

  // mode: "chat" | "quick" | "stats" | "segment" | "stuff" | "advanced"
  //       "hot"  | "leader"| "live"  | "monitor" | "standings" | "profile"
  const [mode, setMode] = useState(() => localStorage.getItem("dl-mode") || "chat");
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => { localStorage.setItem("dl-mode", mode); }, [mode]);

  const [isAgentMode, setIsAgentMode] = useState(false);

  const { sessionId, setSessionId, clearSession } = useSession();

  // ===== API hooks =====
  const { getBackendURL, getAuthHeaders, callBackendAPI, searchPlayers } = useBackendAPI({
    getIdToken, sessionId, setSessionId, isAgentMode,
  });

  const { callFixedQueryAPI } = useFixedQueryAPI({ getBackendURL, getAuthHeaders });

  const { quickResult, setQuickResult, handleQuickQuestion } = useQuickQuery({ callFixedQueryAPI, setIsLoading });

  const { setCustomResult } = useCustomQuery({
    callFixedQueryAPI, getBackendURL, getAuthHeaders, setIsLoading,
  });

  const {
    feedbackState, activeFeedbackForm, setActiveFeedbackForm,
    feedbackFormData, setFeedbackFormData, handleFeedback,
  } = useFeedback({ getBackendURL, getAuthHeaders, sessionId });

  const { handleClearHistory, handleSendMessageStream, handleFormatSelect, handleKeyDown } = useStreamChat({
    inputMessage, isLoading, sessionId,
    setMessages, setInputMessage, setIsLoading, setSessionId, resetMessages, clearSession,
    getBackendURL, getAuthHeaders, callBackendAPI,
  });

  // Clear sub-results when switching modes
  const handleSetMode = (newMode) => {
    setMode(newMode);
    setQuickResult(null);
    setCustomResult(null);
  };

  const handleGoogleLogin = async () => {
    setIsCheckingAuth(true);
    try {
      await loginWithGoogle();
    } finally {
      setIsCheckingAuth(false);
    }
  };

  // ===== Screen routing =====
  const renderScreen = () => {
    switch (mode) {
      case "chat":
        return (
          <ChatScreen
            messages={messages}
            feedbackState={feedbackState}
            activeFeedbackForm={activeFeedbackForm}
            feedbackFormData={feedbackFormData}
            setFeedbackFormData={setFeedbackFormData}
            setActiveFeedbackForm={setActiveFeedbackForm}
            handleFeedback={handleFeedback}
            messagesEndRef={messagesEndRef}
            formatTime={formatTime}
            user={user}
            inputMessage={inputMessage}
            setInputMessage={setInputMessage}
            handleKeyDown={handleKeyDown}
            isLoading={isLoading}
            handleSendMessageStream={handleSendMessageStream}
            handleFormatSelect={handleFormatSelect}
            isAgentMode={isAgentMode}
            setIsAgentMode={setIsAgentMode}
            sessionId={sessionId}
            handleClearHistory={handleClearHistory}
          />
        );
      case "quick":
        return (
          <div style={{ padding: "24px 32px", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <QuickQuestions
              onQuestionClick={handleQuickQuestion}
              isLoading={isLoading}
              quickResult={quickResult}
              onClearResult={() => setQuickResult(null)}
            />
          </div>
        );
      case "stats":
        return <div style={{ padding: "24px 32px", height: "100%" }}><StatisticalAnalysis/></div>;
      case "segment":
        return <div style={{ padding: "24px 32px", height: "100%" }}><PlayerSegmentation/></div>;
      case "stuff":
        return <div style={{ padding: "24px 32px", height: "100%" }}><StuffPlus/></div>;
      case "advanced":
        return <div style={{ padding: "24px 32px", height: "100%" }}><AdvancedStats/></div>;
      case "hot":
        return <div style={{ height: "100%", overflowY: "auto" }}><HotSlumpDashboard/></div>;
      case "leader":
        return <div style={{ padding: "24px 32px", height: "100%" }}><Leaderboard/></div>;
      case "live":
        return <div style={{ padding: "24px 32px", height: "100%", width: "100%" }}><LiveScoreboard/></div>;
      case "monitor":
        return <div style={{ padding: "24px 32px", height: "100%", width: "100%" }}><LiveMonitorBoard/></div>;
      case "standings":
        return <div style={{ padding: "24px 32px", height: "100%", width: "100%" }}><Standings/></div>;
      case "profile":
        return (
          <div style={{ padding: "24px 32px", height: "100%", width: "100%" }}>
            <PlayerProfile
              onSearchPlayers={searchPlayers}
              getAuthHeaders={getAuthHeaders}
              getBackendURL={getBackendURL}
            />
          </div>
        );
      default:
        return <Placeholder label={mode.toUpperCase()}/>;
    }
  };

  // ===== Render =====
  return (
    <div style={{ height: "100%", display: "flex", background: "var(--bg-0)", color: "var(--ink-1)" }}>
      {authLoading ? (
        <div style={{
          flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
          background: "var(--bg-0)",
        }}>
          <div style={{
            width: 32, height: 32,
            border: "2px solid var(--bg-3)",
            borderTop: "2px solid var(--amber)",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}/>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : !user ? (
        <div style={{ flex: 1 }}>
          <LoginScreen
            authError={authError}
            isCheckingAuth={isCheckingAuth}
            handleGoogleLogin={handleGoogleLogin}
          />
        </div>
      ) : (
        <>
          <AppSidebar
            mode={mode}
            setMode={handleSetMode}
            collapsed={collapsed}
            setCollapsed={setCollapsed}
            user={user}
            logout={logout}
          />

          <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
            <Ticker/>
            <Topbar
              mode={mode}
              collapsed={collapsed}
              onToggleSidebar={() => setCollapsed(c => !c)}
              sessionId={sessionId}
              onClearHistory={handleClearHistory}
            />

            {/* Screen content */}
            <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflowY: mode === "chat" ? "hidden" : "auto" }}>
              {renderScreen()}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const App = () => <MLBChatApp/>;

export default App;
