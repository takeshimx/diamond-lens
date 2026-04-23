import React, { useState, useEffect } from 'react';
import Icon from './Icon.jsx';
import { NAV_ITEMS } from '../../constants/navItems.js';

const Topbar = ({ mode, collapsed, onToggleSidebar, sessionId, onClearHistory }) => {
  const current = NAV_ITEMS.find(n => n.id === mode);
  const idx     = NAV_ITEMS.findIndex(n => n.id === mode);

  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })
  );

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="rule-b" style={{
      height: 48, display: "flex", alignItems: "stretch",
      background: "var(--bg-0)", flexShrink: 0,
    }}>
      {/* Sidebar toggle */}
      <button
        onClick={onToggleSidebar}
        className="rule-r"
        style={{ width: 40, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink-2)" }}
      >
        <Icon name="menu" size={16}/>
      </button>

      {/* Module breadcrumb */}
      <div className="rule-r" style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "0 16px", minWidth: 220, flexShrink: 0,
      }}>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--amber)", letterSpacing: "0.1em" }}>
          {String(idx + 1).padStart(2, "0")} / {String(NAV_ITEMS.length).padStart(2, "0")}
        </span>
        <div style={{ width: 1, height: 16, background: "var(--rule)" }}/>
        <div className="h-display" style={{ fontSize: 14 }}>{current?.en || "—"}</div>
        <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)", letterSpacing: "0.06em" }}>
          / {current?.jp}
        </div>
      </div>

      {/* Command bar */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 10, padding: "0 16px" }}>
        <Icon name="search" size={13} style={{ color: "var(--ink-4)", flexShrink: 0 }}/>
        <input
          placeholder="GO / Symbol or command... 例: JUDGE, HR 2024, STUFF+ SKENES"
          style={{
            flex: 1, fontSize: 12.5, color: "var(--ink-1)",
            fontFamily: "var(--ff-mono)", letterSpacing: "0.01em",
          }}
          readOnly
        />
        <span className="t-mono" style={{
          fontSize: 9.5, color: "var(--ink-4)",
          padding: "2px 6px", border: "1px solid var(--rule)", flexShrink: 0,
        }}>⌘K</span>
      </div>

      {/* Status cluster */}
      <div className="rule-l" style={{
        display: "flex", alignItems: "center", gap: 14, padding: "0 16px", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className="live-dot"/>
          <span className="h-label" style={{ fontSize: 9, color: "var(--pos)" }}>API ONLINE</span>
        </div>

        {/* Chat-only: clear history */}
        {mode === "chat" && sessionId && onClearHistory && (
          <button
            onClick={onClearHistory}
            title="会話履歴をクリア"
            style={{ display: "flex", alignItems: "center", gap: 5, color: "var(--ink-3)", padding: "3px 6px" }}
            onMouseEnter={e => e.currentTarget.style.color = "var(--neg)"}
            onMouseLeave={e => e.currentTarget.style.color = "var(--ink-3)"}
          >
            <Icon name="trash" size={13}/>
            <span className="h-label" style={{ fontSize: 9 }}>CLEAR</span>
          </button>
        )}

        <div className="t-mono" style={{ fontSize: 11, color: "var(--ink-1)" }}>
          {time} <span style={{ color: "var(--ink-4)" }}>JST</span>
        </div>
      </div>
    </div>
  );
};

export default Topbar;
