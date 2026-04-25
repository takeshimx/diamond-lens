import React from 'react';
import { DLMark } from './Icon.jsx';
import Icon from './Icon.jsx';
import AgentReasoningTracker from '../AgentReasoningTracker.jsx';
import SimpleChatChart from '../ChatChart.jsx';
import StatCard from '../chat/StatCard.jsx';
import DataTable from '../chat/DataTable.jsx';
import MatchupAnalysisCard from '../MatchupAnalysisCard.jsx';
import StrategyReportCard from '../StrategyReportCard.jsx';
import { FAILURE_CATEGORY_LABELS } from '../../constants/failureCategories.js';

// ============================================================
// User message
// ============================================================
const UserMessage = ({ message, formatTime, user }) => {
  const initials = user?.displayName
    ? user.displayName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
    : (user?.email?.[0] ?? 'U').toUpperCase();
  const displayName = user?.displayName ?? user?.email?.split('@')[0] ?? 'USER';

  return (
    <div className="rule-b" style={{ padding: "16px 28px", display: "flex", gap: 14 }}>
      {/* Avatar */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, minWidth: 56, flexShrink: 0 }}>
        <div style={{
          width: 26, height: 26, background: "var(--bg-3)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--ink-0)",
          border: "1px solid var(--rule)", fontWeight: 600,
        }}>{initials}</div>
        <span className="h-label" style={{ fontSize: 8, color: "var(--ink-4)" }}>USER</span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 12.5, color: "var(--ink-0)", fontWeight: 600 }}>{displayName}</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
            {formatTime(message.timestamp)}
          </span>
        </div>
        <div style={{ fontSize: 14, color: "var(--ink-1)", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
          {message.content}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Feedback buttons
// ============================================================
const FeedbackRow = ({
  message, feedbackState, activeFeedbackForm,
  feedbackFormData, setFeedbackFormData, setActiveFeedbackForm, handleFeedback,
}) => {
  if (!message.requestId) return null;
  const state = feedbackState[message.id];
  const FEEDBACK_CATEGORIES = [
    { id: 'inaccurate',   label: '不正確・誤り' },
    { id: 'irrelevant',   label: '無関係な回答' },
    { id: 'wrong_player', label: '選手が違う' },
    { id: 'wrong_stats',  label: '統計が違う' },
    { id: 'slow',         label: '応答が遅い' },
  ];

  return (
    <>
      <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 4, color: "var(--ink-3)" }}>
        <button
          onClick={() => handleFeedback(message.id, message.requestId, 'good')}
          disabled={state === 'loading' || state === 'good' || state === 'bad'}
          title="正確な回答"
          style={{ padding: 6, display: "flex", color: state === 'good' ? "var(--pos)" : "var(--ink-3)" }}
        >
          <Icon name="thumbUp" size={13}/>
        </button>
        <button
          onClick={() => handleFeedback(message.id, message.requestId, 'bad')}
          disabled={state === 'loading' || state === 'good' || state === 'bad'}
          title="改善が必要"
          style={{ padding: 6, display: "flex", color: state === 'bad' ? "var(--neg)" : "var(--ink-3)" }}
        >
          <Icon name="thumbDown" size={13}/>
        </button>
        {state === 'error' && (
          <span className="t-mono" style={{ fontSize: 9.5, color: "var(--neg)", marginLeft: 4 }}>送信失敗</span>
        )}
      </div>

      {/* Detail feedback form */}
      {activeFeedbackForm && String(activeFeedbackForm.messageId) === String(message.id) && (
        <div style={{
          marginTop: 10, padding: 12,
          border: "1px solid var(--rule)", background: "var(--bg-1)",
        }}>
          <div className="h-label" style={{ fontSize: 9, color: "var(--ink-2)", marginBottom: 10 }}>
            FEEDBACK DETAIL
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
            {FEEDBACK_CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => setFeedbackFormData(prev => ({ ...prev, category: cat.id }))}
                style={{
                  fontSize: 10.5, padding: "3px 8px",
                  border: `1px solid ${feedbackFormData.category === cat.id ? "var(--amber)" : "var(--rule)"}`,
                  color: feedbackFormData.category === cat.id ? "var(--amber)" : "var(--ink-2)",
                  background: feedbackFormData.category === cat.id ? "var(--amber-glow)" : "transparent",
                }}
              >{cat.label}</button>
            ))}
          </div>
          <textarea
            value={feedbackFormData.reason}
            onChange={e => setFeedbackFormData(prev => ({ ...prev, reason: e.target.value }))}
            placeholder="具体的な問題点（任意）"
            rows={2}
            style={{ width: "100%", fontSize: 12, marginBottom: 10, padding: 8, background: "var(--bg-0)", border: "1px solid var(--rule)", color: "var(--ink-1)", resize: "none" }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button
              onClick={() => setActiveFeedbackForm(null)}
              style={{ fontSize: 11, color: "var(--ink-3)", padding: "4px 10px" }}
            >キャンセル</button>
            <button
              onClick={() => handleFeedback(message.id, message.requestId, 'bad', feedbackFormData)}
              disabled={!feedbackFormData.category}
              style={{
                fontSize: 11, padding: "4px 12px",
                background: feedbackFormData.category ? "var(--amber)" : "var(--bg-3)",
                color: feedbackFormData.category ? "var(--bg-0)" : "var(--ink-4)",
                fontWeight: 600,
              }}
            >送信する</button>
          </div>
        </div>
      )}
    </>
  );
};

// ============================================================
// Clarification message (表示形式を選択させるボットメッセージ)
// ============================================================
const ClarificationMessage = ({ message, onSelect, formatTime }) => (
  <div style={{ padding: "20px 28px", background: "var(--bg-0)" }} className="rule-b">
    <div style={{ display: "flex", gap: 14 }}>
      {/* Avatar */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, minWidth: 56, flexShrink: 0 }}>
        <DLMark size={26}/>
        <span className="h-label" style={{ fontSize: 8, color: "var(--amber)" }}>DL·AI</span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <span style={{
            fontSize: 12.5, color: "var(--ink-0)", fontWeight: 600,
            fontFamily: "var(--ff-head)", letterSpacing: "0.04em",
          }}>DIAMOND LENS</span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
            {formatTime(message.timestamp)}
          </span>
        </div>

        {message.resolved ? (
          <div className="t-mono" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
            {message.selectedFormat === 'table' ? 'A. テーブル' : 'B. テキスト'} を選択しました
          </div>
        ) : (
          <>
            <div style={{ fontSize: 13.5, color: "var(--ink-1)", lineHeight: 1.65, marginBottom: 14 }}>
              表示形式はどうしますか？
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => onSelect(message.id, message.pendingQuery, 'table')}
                style={{
                  fontSize: 11.5, padding: "6px 18px",
                  border: "1px solid var(--amber)",
                  color: "var(--amber)",
                  fontFamily: "var(--ff-mono)",
                  letterSpacing: "0.06em",
                  transition: "background .12s",
                }}
                onMouseEnter={e => e.currentTarget.style.background = "oklch(from var(--amber) l c h / 0.1)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >A. テーブル</button>
              <button
                onClick={() => onSelect(message.id, message.pendingQuery, 'text')}
                style={{
                  fontSize: 11.5, padding: "6px 18px",
                  border: "1px solid var(--rule-hi)",
                  color: "var(--ink-2)",
                  fontFamily: "var(--ff-mono)",
                  letterSpacing: "0.06em",
                  transition: "background .12s",
                }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >B. テキスト</button>
            </div>
          </>
        )}
      </div>
    </div>
  </div>
);

// ============================================================
// Bot message
// ============================================================
const BotMessage = ({
  message, feedbackState, activeFeedbackForm,
  feedbackFormData, setFeedbackFormData, setActiveFeedbackForm, handleFeedback,
  formatTime,
}) => {
  const isThinking = message.isStreaming && !message.content && !message.streamingStatus;
  const isStreaming = message.isStreaming;

  return (
    <div style={{ padding: "20px 28px", background: "var(--bg-0)" }} className="rule-b">
      <div style={{ display: "flex", gap: 14 }}>
        {/* Avatar */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, minWidth: 56, flexShrink: 0 }}>
          <DLMark size={26}/>
          <span className="h-label" style={{ fontSize: 8, color: "var(--amber)" }}>DL·AI</span>
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Message header */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <span style={{
              fontSize: 12.5, color: "var(--ink-0)", fontWeight: 600,
              fontFamily: "var(--ff-head)", letterSpacing: "0.04em",
            }}>DIAMOND LENS</span>
            <span className="t-mono" style={{
              fontSize: 9.5, color: "var(--amber)",
              padding: "1px 6px", border: "1px solid var(--amber-dim)", letterSpacing: "0.08em",
            }}>
              {isStreaming ? "STREAMING" : "SONNET"}
            </span>
            <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
              {formatTime(message.timestamp)}
            </span>
          </div>

          {/* Streaming status */}
          {isStreaming && message.streamingStatus && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
              <span className="t-mono" style={{ fontSize: 11, color: "var(--amber)", letterSpacing: "0.08em" }}>
                {message.streamingStatus.toUpperCase()}
              </span>
              <span>
                <span className="think-dot"/>
                <span className="think-dot" style={{ animationDelay: ".2s" }}/>
                <span className="think-dot" style={{ animationDelay: ".4s" }}/>
              </span>
            </div>
          )}

          {/* Thinking state (no content yet) */}
          {isThinking && (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className="t-mono" style={{ fontSize: 11, color: "var(--amber)", letterSpacing: "0.08em" }}>
                PROCESSING
              </span>
              <span>
                <span className="think-dot"/>
                <span className="think-dot" style={{ animationDelay: ".2s" }}/>
                <span className="think-dot" style={{ animationDelay: ".4s" }}/>
              </span>
            </div>
          )}

          {/* Quality warning */}
          {message.qualityWarning?.has_warning && (
            <div style={{
              marginBottom: 12, display: "flex", alignItems: "flex-start", gap: 8,
              padding: "8px 12px", border: "1px solid var(--neg-dim)", background: "oklch(from var(--neg) l c h / 0.08)",
            }}>
              <Icon name="alert" size={14} style={{ color: "var(--neg)", flexShrink: 0, marginTop: 1 }}/>
              <div style={{ fontSize: 12, color: "var(--ink-1)", lineHeight: 1.5 }}>
                類似の質問で精度が低かった事例があります。回答内容を慎重にご確認ください。
                {message.qualityWarning.top_failure_category && (
                  <span style={{ marginLeft: 6, color: "var(--neg)" }}>
                    ({FAILURE_CATEGORY_LABELS[message.qualityWarning.top_failure_category] ?? message.qualityWarning.top_failure_category})
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Agent reasoning steps */}
          {message.steps && message.steps.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <AgentReasoningTracker
                steps={message.steps}
                isStreaming={message.isStreaming}
                isCollapsible={!message.isStreaming}
              />
            </div>
          )}

          {/* Main text */}
          {!message.isStrategyReport && !message.isTable && !message.isChart && message.content && (
            <div style={{ fontSize: 13.5, color: "var(--ink-1)", lineHeight: 1.65, marginBottom: 14, whiteSpace: "pre-wrap" }}>
              {message.content}
            </div>
          )}

          {/* Table */}
          {message.isTable && message.tableData && message.columns && (
            <div style={{ marginBottom: 14 }}>
              <DataTable
                tableData={message.tableData}
                columns={message.columns}
                isTransposed={message.isTransposed}
                decimalColumns={message.decimalColumns}
                grouping={message.grouping}
              />
            </div>
          )}

          {/* Chart */}
          {message.isChart && message.chartData && message.chartConfig ? (
            <div style={{ marginBottom: 14 }}>
              <SimpleChatChart
                chartData={message.chartData}
                chartConfig={message.chartConfig}
                chartType={message.chartType}
              />
            </div>
          ) : message.isChart ? (
            <div style={{ marginBottom: 14, padding: 12, border: "1px solid var(--neg-dim)", color: "var(--neg)", fontSize: 11 }}>
              Chart data missing.
            </div>
          ) : null}

          {/* Stats card */}
          {message.stats && (
            <div style={{ marginBottom: 14 }}>
              <StatCard stats={message.stats}/>
            </div>
          )}

          {/* Matchup card */}
          {message.isMatchupCard && message.matchupData && (
            <div style={{ marginBottom: 14 }}>
              <MatchupAnalysisCard matchupData={message.matchupData}/>
            </div>
          )}

          {/* Strategy report */}
          {message.isStrategyReport && message.content && !message.isStreaming && (
            <div style={{ marginBottom: 14 }}>
              <StrategyReportCard finalAnswer={message.content} strategyData={message.strategyData}/>
            </div>
          )}

          {/* Feedback */}
          {!isStreaming && (
            <FeedbackRow
              message={message}
              feedbackState={feedbackState}
              activeFeedbackForm={activeFeedbackForm}
              feedbackFormData={feedbackFormData}
              setFeedbackFormData={setFeedbackFormData}
              setActiveFeedbackForm={setActiveFeedbackForm}
              handleFeedback={handleFeedback}
            />
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// ChatMessageList
// ============================================================
const ChatMessageList = ({
  messages,
  feedbackState,
  activeFeedbackForm,
  feedbackFormData,
  setFeedbackFormData,
  setActiveFeedbackForm,
  handleFeedback,
  handleFormatSelect,
  messagesEndRef,
  formatTime,
  user,
}) => (
  <div style={{ paddingBottom: 8 }}>
    {messages.map(message => {
      if (message.type === 'user') {
        return <UserMessage key={message.id} message={message} formatTime={formatTime} user={user}/>;
      }
      if (message.type === 'clarification') {
        return (
          <ClarificationMessage
            key={message.id}
            message={message}
            onSelect={handleFormatSelect}
            formatTime={formatTime}
          />
        );
      }
      return (
        <BotMessage
          key={message.id}
          message={message}
          feedbackState={feedbackState}
          activeFeedbackForm={activeFeedbackForm}
          feedbackFormData={feedbackFormData}
          setFeedbackFormData={setFeedbackFormData}
          setActiveFeedbackForm={setActiveFeedbackForm}
          handleFeedback={handleFeedback}
          formatTime={formatTime}
        />
      );
    })}
    <div ref={messagesEndRef}/>
  </div>
);

export default ChatMessageList;
