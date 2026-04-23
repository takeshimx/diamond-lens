import React from 'react';
import Icon from './Icon.jsx';

const QUICK_PROMPTS = [
  { k: "HR",  label: "本塁打数ランキング" },
  { k: "BA",  label: "打率 .300 以上" },
  { k: "K9",  label: "K/9 トップ15 投手" },
  { k: "WAR", label: "fWAR 年間推移" },
  { k: "OPS", label: "OPS リーダーボード" },
  { k: "STF", label: "球種別 Stuff+" },
];

const ChatInputArea = ({
  inputMessage,
  setInputMessage,
  handleKeyDown,
  isLoading,
  handleSendMessageStream,
  isAgentMode,
  setIsAgentMode,
}) => (
  <div className="rule-t" style={{
    background: "var(--bg-0)", padding: "12px 28px 16px", flexShrink: 0,
  }}>
    {/* Quick prompts */}
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
      <span className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginRight: 4 }}>QUICK</span>
      {QUICK_PROMPTS.map(q => (
        <button
          key={q.k}
          onClick={() => setInputMessage(`${q.label}を見せて`)}
          disabled={isLoading}
          style={{
            fontSize: 10.5, padding: "3px 8px",
            border: "1px solid var(--rule)", color: "var(--ink-2)",
            letterSpacing: "0.01em", display: "inline-flex", gap: 6,
            transition: "border-color .1s, color .1s",
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = "var(--amber-dim)";
            e.currentTarget.style.color = "var(--ink-0)";
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = "var(--rule)";
            e.currentTarget.style.color = "var(--ink-2)";
          }}
        >
          <span className="t-mono" style={{ color: "var(--amber)" }}>{q.k}</span>
          <span>{q.label}</span>
        </button>
      ))}
    </div>

    {/* Composer box */}
    <div style={{ border: "1px solid var(--rule-hi)", background: "var(--bg-1)" }}>
      {/* Textarea */}
      <div style={{ padding: "10px 14px" }}>
        <textarea
          value={inputMessage}
          onChange={e => setInputMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="例: 大谷翔平の2024年打率は？Skenes の Stuff+ を月別で。"
          rows={2}
          disabled={isLoading}
          style={{
            width: "100%", fontSize: 13.5, lineHeight: 1.5,
            color: "var(--ink-0)", resize: "none",
            fontFamily: "var(--ff-text)",
          }}
        />
      </div>

      {/* Action row */}
      <div className="rule-t" style={{ padding: "6px 10px 6px 14px", display: "flex", alignItems: "center", gap: 8 }}>
        {/* Agent mode toggle */}
        <button
          onClick={() => setIsAgentMode(!isAgentMode)}
          title={isAgentMode ? 'エージェントモード: ON' : 'エージェントモード: OFF'}
          style={{
            fontSize: 10.5, padding: "3px 8px",
            border: `1px solid ${isAgentMode ? "var(--purp)" : "var(--rule-hi)"}`,
            color: isAgentMode ? "var(--purp)" : "var(--ink-2)",
            display: "inline-flex", alignItems: "center", gap: 5,
            background: isAgentMode ? "oklch(from var(--purp) l c h / 0.12)" : "transparent",
            letterSpacing: "0.04em",
            transition: "all .12s",
          }}
        >
          <Icon name="sparkle" size={11}/> AGENT {isAgentMode ? "ON" : "OFF"}
        </button>

        <button
          style={{
            fontSize: 10.5, padding: "3px 8px",
            border: "1px solid var(--rule-hi)", color: "var(--ink-2)",
            display: "inline-flex", alignItems: "center", gap: 5,
          }}
        >
          <Icon name="grid" size={11}/> STATCAST
        </button>

        <div style={{ flex: 1 }}/>

        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>
          {inputMessage.length} CHARS
        </span>

        <button style={{ padding: 5, color: "var(--ink-3)", display: "flex" }} title="音声入力">
          <Icon name="mic" size={14}/>
        </button>

        <button
          onClick={handleSendMessageStream}
          disabled={!inputMessage.trim() || isLoading}
          style={{
            padding: "5px 14px",
            background: inputMessage.trim() && !isLoading ? "var(--amber)" : "var(--bg-3)",
            color: inputMessage.trim() && !isLoading ? "var(--bg-0)" : "var(--ink-4)",
            display: "inline-flex", alignItems: "center", gap: 6,
            fontWeight: 600, fontSize: 11.5, letterSpacing: "0.08em",
            fontFamily: "var(--ff-mono)", transition: "all .12s",
          }}
        >
          {isLoading ? (
            <>
              <span className="think-dot"/>
              <span className="think-dot" style={{ animationDelay: ".2s" }}/>
              <span className="think-dot" style={{ animationDelay: ".4s" }}/>
            </>
          ) : (
            <>EXECUTE <Icon name="send" size={12}/></>
          )}
        </button>
      </div>
    </div>

    {/* Hint row */}
    <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 8 }}>
      <span className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>
        ⏎ 送信 · ⇧⏎ 改行
      </span>
    </div>
  </div>
);

export default ChatInputArea;
