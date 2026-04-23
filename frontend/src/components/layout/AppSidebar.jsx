import React from 'react';
import Icon, { DLMark } from './Icon.jsx';
import { NAV_ITEMS } from '../../constants/navItems.js';

const AppSidebar = ({ mode, setMode, collapsed, setCollapsed, user, logout }) => {
  // Derive initials from Firebase displayName (e.g. "Takeshi M" → "TM")
  const initials = user?.displayName
    ? user.displayName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
    : (user?.email?.[0] ?? '?').toUpperCase();
  const displayName = user?.displayName ?? user?.email?.split('@')[0] ?? '—';

  return (
    <aside
      className="rule-r"
      style={{
        width: collapsed ? 56 : 224,
        flexShrink: 0,
        background: "var(--bg-0)",
        display: "flex", flexDirection: "column",
        transition: "width .18s ease",
        overflow: "hidden",
      }}
    >
      {/* Brand */}
      <div className="rule-b" style={{
        height: 56, display: "flex", alignItems: "center",
        gap: 10, padding: "0 14px", flexShrink: 0,
      }}>
        <DLMark size={22}/>
        {!collapsed && (
          <div style={{ lineHeight: 1, flex: 1, minWidth: 0 }}>
            <div className="h-display" style={{ fontSize: 15, letterSpacing: "0.06em" }}>
              DIAMOND&nbsp;LENS
            </div>
            <div className="h-label" style={{ fontSize: 8.5, marginTop: 3, color: "var(--amber-dim)" }}>
              MLB INTELLIGENCE v2.6
            </div>
          </div>
        )}
      </div>

      {/* Section header */}
      {!collapsed && (
        <div style={{ padding: "12px 14px 6px" }}>
          <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)" }}>
            MODULES / モジュール
          </div>
        </div>
      )}

      {/* Nav items */}
      <nav style={{ flex: 1, overflowY: "auto", padding: "4px 6px" }}>
        {NAV_ITEMS.map((item, i) => {
          const active = mode === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setMode(item.id)}
              title={collapsed ? item.jp : undefined}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                width: "100%", padding: collapsed ? "9px 0" : "8px 10px",
                justifyContent: collapsed ? "center" : "flex-start",
                color: active ? "var(--ink-0)" : "var(--ink-2)",
                background: active ? "var(--bg-2)" : "transparent",
                borderLeft: active ? "2px solid var(--amber)" : "2px solid transparent",
                marginBottom: 1,
                transition: "all .12s",
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = "var(--bg-1)"; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}
            >
              <Icon name={item.icon} size={15}/>
              {!collapsed && (
                <>
                  <span style={{ fontSize: 12.5, fontWeight: active ? 600 : 500, flex: 1, textAlign: "left" }}>
                    {item.jp}
                  </span>
                  <span className="t-mono" style={{
                    fontSize: 9, letterSpacing: "0.04em",
                    color: active ? "var(--amber)" : "var(--ink-4)",
                  }}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </>
              )}
            </button>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="rule-t" style={{ padding: collapsed ? "10px 0" : "10px 12px", flexShrink: 0 }}>
        {!collapsed ? (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 28, height: 28, background: "var(--bg-3)", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--amber)", fontFamily: "var(--ff-mono)", fontSize: 11, fontWeight: 600,
              border: "1px solid var(--rule)",
            }}>{initials}</div>
            <div style={{ flex: 1, minWidth: 0, lineHeight: 1.25 }}>
              <div style={{ fontSize: 11.5, color: "var(--ink-0)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {displayName}
              </div>
              <div className="t-mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>AUTH · ACTIVE</div>
            </div>
            <button onClick={logout} title="ログアウト" style={{ color: "var(--ink-3)", padding: 4 }}>
              <Icon name="logout" size={14}/>
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", justifyContent: "center" }}>
            <div style={{
              width: 28, height: 28, background: "var(--bg-3)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--amber)", fontFamily: "var(--ff-mono)", fontSize: 11, fontWeight: 600,
              border: "1px solid var(--rule)",
            }}>{initials}</div>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="rule-t"
        style={{
          padding: "8px 0", color: "var(--ink-3)",
          display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
          fontSize: 10, letterSpacing: "0.12em", fontFamily: "var(--ff-mono)",
        }}
      >
        <Icon name={collapsed ? "chevR" : "chevL"} size={12}/>
        {!collapsed && <span>COLLAPSE</span>}
      </button>
    </aside>
  );
};

export default AppSidebar;
