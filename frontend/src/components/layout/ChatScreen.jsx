import React from 'react';
import Icon, { DLMark } from './Icon.jsx';
import ChatMessageList from './ChatMessageList.jsx';
import ChatInputArea from './ChatInputArea.jsx';

// ============================================================
// Session Panel (left 240px)
// ============================================================
const SessionPanel = ({ sessionId, onNewSession }) => (
  <div className="rule-r" style={{
    width: 240, flexShrink: 0,
    background: "var(--bg-0)", display: "flex", flexDirection: "column",
  }}>
    {/* Header */}
    <div className="rule-b" style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: 10 }}>
      <span className="h-label" style={{ color: "var(--ink-0)" }}>SESSIONS</span>
      <div style={{ flex: 1 }}/>
      <button
        onClick={onNewSession}
        style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--amber)" }}
        title="新規セッション"
      >
        <Icon name="plus" size={12}/>
        <span className="h-label" style={{ fontSize: 9.5, color: "var(--amber)" }}>NEW</span>
      </button>
    </div>

    {/* Session list */}
    <div style={{ flex: 1, overflowY: "auto" }}>
      {sessionId ? (
        <button style={{
          width: "100%", textAlign: "left",
          padding: "10px 14px",
          background: "var(--bg-2)",
          borderLeft: "2px solid var(--amber)",
          borderBottom: "1px solid var(--rule-dim)",
        }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 3 }}>
            <span className="t-mono" style={{ fontSize: 9.5, color: "var(--amber)" }}>#001</span>
            <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)", marginLeft: "auto" }}>現在</span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--ink-0)", fontWeight: 600 }}>アクティブセッション</div>
          <div className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)", marginTop: 4 }}>
            {sessionId.slice(0, 16)}…
          </div>
        </button>
      ) : (
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          height: "100%", flexDirection: "column", gap: 8,
          color: "var(--ink-4)", padding: "24px 16px", textAlign: "center",
        }}>
          <DLMark size={28}/>
          <div className="t-mono" style={{ fontSize: 10, letterSpacing: "0.08em" }}>NO SESSION</div>
          <div style={{ fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5 }}>
            質問するとセッションが開始されます
          </div>
        </div>
      )}
    </div>

    {/* CTX usage footer */}
    <div className="rule-t" style={{ padding: "10px 14px", flexShrink: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span className="h-label" style={{ fontSize: 9, color: "var(--ink-3)" }}>CTX USAGE</span>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-1)" }}>— / 200K</span>
      </div>
      <div style={{ height: 3, background: "var(--bg-2)" }}>
        <div style={{ width: "0%", height: "100%", background: "var(--amber)" }}/>
      </div>
    </div>
  </div>
);

// ============================================================
// Conversation header bar
// ============================================================
const ConversationHeader = ({ sessionId, onClearHistory }) => (
  <div className="rule-b" style={{
    padding: "0 28px", height: 40,
    display: "flex", alignItems: "center", gap: 12, flexShrink: 0,
  }}>
    <span className="t-mono" style={{ fontSize: 10, color: "var(--amber)", letterSpacing: "0.08em" }}>
      MLB INTELLIGENCE
    </span>
    <div style={{ width: 1, height: 12, background: "var(--rule)" }}/>
    <span style={{ fontSize: 12.5, color: "var(--ink-0)", fontWeight: 500 }}>チャット</span>
    <div style={{ flex: 1 }}/>
    {sessionId && onClearHistory && (
      <button
        onClick={onClearHistory}
        title="会話履歴をクリア"
        style={{ display: "flex", alignItems: "center", gap: 5, color: "var(--ink-3)", padding: "3px 6px" }}
        onMouseEnter={e => e.currentTarget.style.color = "var(--neg)"}
        onMouseLeave={e => e.currentTarget.style.color = "var(--ink-3)"}
      >
        <Icon name="trash" size={13}/>
        <span className="h-label" style={{ fontSize: 9, color: "inherit" }}>CLEAR</span>
      </button>
    )}
  </div>
);

// ============================================================
// ChatScreen — 2-panel layout
// ============================================================
const ChatScreen = ({
  // message list
  messages, feedbackState, activeFeedbackForm, feedbackFormData,
  setFeedbackFormData, setActiveFeedbackForm, handleFeedback,
  handleFormatSelect,
  messagesEndRef, formatTime, user,
  // input
  inputMessage, setInputMessage, handleKeyDown, isLoading,
  handleSendMessageStream, isAgentMode, setIsAgentMode,
  // session
  sessionId, handleClearHistory,
}) => (
  <div style={{ flex: 1, display: "flex", minHeight: 0, overflow: "hidden" }}>
    <SessionPanel sessionId={sessionId} onNewSession={handleClearHistory}/>

    <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, background: "var(--bg-0)" }}>
      <ConversationHeader sessionId={sessionId} onClearHistory={handleClearHistory}/>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <ChatMessageList
          messages={messages}
          feedbackState={feedbackState}
          activeFeedbackForm={activeFeedbackForm}
          feedbackFormData={feedbackFormData}
          setFeedbackFormData={setFeedbackFormData}
          setActiveFeedbackForm={setActiveFeedbackForm}
          handleFeedback={handleFeedback}
          handleFormatSelect={handleFormatSelect}
          messagesEndRef={messagesEndRef}
          formatTime={formatTime}
          user={user}
        />
      </div>

      {/* Composer */}
      <ChatInputArea
        inputMessage={inputMessage}
        setInputMessage={setInputMessage}
        handleKeyDown={handleKeyDown}
        isLoading={isLoading}
        handleSendMessageStream={handleSendMessageStream}
        isAgentMode={isAgentMode}
        setIsAgentMode={setIsAgentMode}
      />
    </div>
  </div>
);

export default ChatScreen;
