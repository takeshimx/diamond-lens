import { DLMark } from './Icon.jsx';

const LoginScreen = ({ authError, isCheckingAuth, handleGoogleLogin }) => (
  <div style={{
    position: "fixed", inset: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
    background: "var(--bg-0)",
  }}>
    {/* 背景グリッド装飾 */}
    <div style={{
      position: "absolute", inset: 0, pointerEvents: "none",
      backgroundImage: "linear-gradient(var(--rule-dim) 1px, transparent 1px), linear-gradient(90deg, var(--rule-dim) 1px, transparent 1px)",
      backgroundSize: "48px 48px",
      opacity: 0.5,
    }} />

    <div style={{
      position: "relative",
      background: "var(--bg-1)", border: "1px solid var(--rule)",
      padding: "40px 48px", width: "100%", maxWidth: 380,
    }}>
      {/* ロゴ＋タイトル */}
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
          <DLMark size={48} />
        </div>
        <h1 className="h-display" style={{ fontSize: 22, marginBottom: 6 }}>Diamond Lens</h1>
        <p className="t-mono" style={{ fontSize: 11, color: "var(--ink-4)", letterSpacing: "0.1em" }}>
          MLB STATS ASSISTANT
        </p>
      </div>

      {/* エラー */}
      {authError && (
        <div style={{
          marginBottom: 16, padding: "8px 12px",
          background: "oklch(0.26 0.10 28 / 0.12)",
          border: "1px solid var(--neg-dim)",
        }}>
          <p className="t-mono" style={{ fontSize: 11, color: "var(--neg)" }}>{authError}</p>
        </div>
      )}

      {/* Google ログインボタン */}
      <button
        onClick={handleGoogleLogin}
        disabled={isCheckingAuth}
        style={{
          width: "100%", padding: "10px 16px",
          background: "var(--bg-2)", border: "1px solid var(--rule)",
          color: "var(--ink-1)", cursor: isCheckingAuth ? "not-allowed" : "pointer",
          opacity: isCheckingAuth ? 0.5 : 1,
          display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
          fontFamily: "var(--ff-mono)", fontSize: 12, fontWeight: 600, letterSpacing: "0.05em",
          transition: "all .12s",
        }}
        onMouseEnter={e => { if (!isCheckingAuth) e.currentTarget.style.background = "var(--bg-3)"; }}
        onMouseLeave={e => { e.currentTarget.style.background = "var(--bg-2)"; }}
      >
        {isCheckingAuth ? (
          <>
            <span className="think-dot" />
            <span className="think-dot" style={{ animationDelay: ".2s" }} />
            <span className="think-dot" style={{ animationDelay: ".4s" }} />
            <span style={{ marginLeft: 6 }}>ログイン中...</span>
          </>
        ) : (
          <>
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Google でログイン
          </>
        )}
      </button>

      {/* フッター */}
      <p className="t-mono" style={{ textAlign: "center", fontSize: 10, color: "var(--ink-4)", marginTop: 24 }}>
        © 2025 Diamond Lens · Powered by Statcast
      </p>
    </div>
  </div>
);

export default LoginScreen;
