import React, { useState } from 'react';

// ============================================================
// Advanced Stats — New Design (仮作成・モックデータ)
// Design: Bloomberg Terminal × ESPN Statcast
// ============================================================

const PITCHERS = [
  { r: 1,  n: "P. Skenes",   tm: "PIT", stuff: 142, loc: 108, pitch: 128, ip: 121.1, k9: 11.4, era: 2.12, whip: 0.96, delta: "+3"  },
  { r: 2,  n: "T. Skubal",   tm: "DET", stuff: 138, loc: 112, pitch: 126, ip: 168.0, k9: 10.9, era: 2.61, whip: 0.89, delta: "-1"  },
  { r: 3,  n: "E. Crochet",  tm: "CWS", stuff: 136, loc: 102, pitch: 120, ip: 146.1, k9: 12.8, era: 3.42, whip: 1.08, delta: "+2"  },
  { r: 4,  n: "C. Sale",     tm: "ATL", stuff: 131, loc: 109, pitch: 122, ip: 159.0, k9: 11.6, era: 2.42, whip: 1.01, delta: "0"   },
  { r: 5,  n: "D. Cease",    tm: "SD",  stuff: 130, loc: 101, pitch: 117, ip: 171.0, k9: 11.2, era: 3.18, whip: 1.09, delta: "+1"  },
  { r: 6,  n: "G. Cole",     tm: "NYY", stuff: 128, loc: 114, pitch: 124, ip: 88.2,  k9: 9.6,  era: 3.54, whip: 1.13, delta: "-2"  },
  { r: 7,  n: "T. Glasnow",  tm: "LAD", stuff: 127, loc: 98,  pitch: 115, ip: 121.0, k9: 12.1, era: 3.52, whip: 1.02, delta: "+4"  },
  { r: 8,  n: "Z. Wheeler",  tm: "PHI", stuff: 125, loc: 118, pitch: 124, ip: 175.2, k9: 10.5, era: 2.89, whip: 0.95, delta: "0"   },
  { r: 9,  n: "L. Webb",     tm: "SF",  stuff: 119, loc: 116, pitch: 121, ip: 176.0, k9: 8.2,  era: 3.41, whip: 1.17, delta: "+1"  },
  { r: 10, n: "S. Yamamoto", tm: "LAD", stuff: 118, loc: 107, pitch: 116, ip: 78.2,  k9: 10.3, era: 3.02, whip: 1.07, delta: "+6"  },
];

const ARSENAL_SKENES = [
  { t: "FF", name: "Four-Seam", mph: 99.1, spin: 2412, iVB:  18.4, HB:  -6.2, stf: 148, usage: 48 },
  { t: "SL", name: "Sweeper",   mph: 88.2, spin: 2914, iVB:   3.1, HB:  14.5, stf: 136, usage: 22 },
  { t: "SI", name: "Sinker",    mph: 98.4, spin: 2180, iVB:  10.1, HB: -15.2, stf: 130, usage: 14 },
  { t: "CH", name: "Splinker",  mph: 95.0, spin: 1420, iVB:   2.8, HB: -12.8, stf: 158, usage: 11 },
  { t: "CB", name: "Curveball", mph: 83.4, spin: 2920, iVB: -12.4, HB:  10.1, stf: 118, usage:  5 },
];

const FILTER_TABS = ["ALL", "SP", "RP", "L/R", "L/L", "R/R", "R/L"];

const HEADLINE_METRICS = [
  { k: "LEAGUE STUFF+ MED", v: "98",   d: "±14",   tint: "var(--ink-0)" },
  { k: "TOP 10% THRESHOLD", v: "118",  d: "N=9",   tint: "var(--amber)" },
  { k: "STUFF+ ↔ xERA r²",  v: "0.61", d: "STRONG", tint: "var(--pos)"  },
  { k: "ROOKIE PEAK",       v: "142",  d: "SKENES", tint: "var(--amber)" },
];

const COLOR_KEY = [
  { v: "130+",    l: "ELITE",     c: "var(--amber)" },
  { v: "115–129", l: "ABOVE AVG", c: "var(--pos)"   },
  { v: "100–114", l: "AVERAGE",   c: "var(--ink-1)" },
  { v: "90–99",   l: "BELOW",     c: "var(--ink-3)" },
  { v: "<90",     l: "POOR",      c: "var(--neg)"   },
];

const MOST_IMPROVED = [
  { n: "S. Yamamoto", d: "+11", f: "LAD" },
  { n: "H. Greene",   d: "+9",  f: "CIN" },
  { n: "T. Glasnow",  d: "+7",  f: "LAD" },
  { n: "J. Ryan",     d: "+6",  f: "MIN" },
  { n: "Sp. Strider", d: "+5",  f: "ATL" },
];

// Stuff+ → color
const stuffColor = (v) => {
  if (v >= 130) return "var(--amber)";
  if (v >= 115) return "var(--pos)";
  if (v >= 100) return "var(--ink-1)";
  if (v >= 90)  return "var(--ink-3)";
  return "var(--neg)";
};

// ============================================================
// Leaderboard table
// ============================================================
const LeaderboardTable = ({ pitchers }) => (
  <div style={{ border: "1px solid var(--rule)" }}>
    {/* Header */}
    <div style={{
      display: "grid",
      gridTemplateColumns: "32px 1fr 48px 72px 72px 72px 60px 54px 58px 58px 44px",
      padding: "8px 14px", background: "var(--bg-1)",
      fontSize: 9.5, letterSpacing: "0.12em", color: "var(--ink-2)", fontWeight: 600,
    }} className="rule-b">
      <div>#</div>
      <div>PITCHER</div>
      <div>TM</div>
      <div style={{ textAlign: "right", color: "var(--amber)" }}>STUFF+</div>
      <div style={{ textAlign: "right" }}>LOC+</div>
      <div style={{ textAlign: "right" }}>PITCH+</div>
      <div style={{ textAlign: "right" }}>IP</div>
      <div style={{ textAlign: "right" }}>K/9</div>
      <div style={{ textAlign: "right" }}>ERA</div>
      <div style={{ textAlign: "right" }}>WHIP</div>
      <div style={{ textAlign: "right" }}>Δ</div>
    </div>

    {pitchers.map((p, i) => {
      const featured = p.r === 1;
      return (
        <div key={p.r} style={{
          display: "grid",
          gridTemplateColumns: "32px 1fr 48px 72px 72px 72px 60px 54px 58px 58px 44px",
          padding: "10px 14px",
          fontFamily: "var(--ff-mono)", fontSize: 12,
          background: featured
            ? "oklch(from var(--amber) l c h / 0.06)"
            : i % 2 ? "var(--bg-1)" : "transparent",
          borderBottom: i < pitchers.length - 1 ? "1px solid var(--rule-dim)" : "none",
          alignItems: "center",
          cursor: "pointer",
          transition: "background .1s",
        }}
          onMouseEnter={e => { if (!featured) e.currentTarget.style.background = "var(--bg-2)"; }}
          onMouseLeave={e => { if (!featured) e.currentTarget.style.background = i % 2 ? "var(--bg-1)" : "transparent"; }}
        >
          <div style={{ color: featured ? "var(--amber)" : "var(--ink-4)", fontSize: 11, fontWeight: 700 }}>{p.r}</div>
          <div style={{ color: featured ? "var(--amber)" : "var(--ink-0)", fontWeight: 600, fontFamily: "var(--ff-text)" }}>{p.n}</div>
          <div style={{ color: "var(--ink-3)", fontSize: 11 }}>{p.tm}</div>

          {/* Stuff+ with bar */}
          <div style={{ textAlign: "right", position: "relative" }}>
            <div style={{
              position: "absolute", left: 0, right: 0, top: 0, bottom: 0,
              display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 2,
            }}>
              <div style={{
                width: `${(p.stuff - 80) * 1.4}%`, height: 14,
                background: stuffColor(p.stuff), opacity: 0.18,
              }}/>
            </div>
            <span style={{ position: "relative", color: stuffColor(p.stuff), fontWeight: 700, fontSize: 13 }}>{p.stuff}</span>
          </div>

          <div style={{ textAlign: "right", color: stuffColor(p.loc) }}>{p.loc}</div>
          <div style={{ textAlign: "right", color: stuffColor(p.pitch) }}>{p.pitch}</div>
          <div style={{ textAlign: "right", color: "var(--ink-1)" }}>{p.ip.toFixed(1)}</div>
          <div style={{ textAlign: "right", color: "var(--ink-1)" }}>{p.k9.toFixed(1)}</div>
          <div style={{ textAlign: "right", color: "var(--ink-0)" }}>{p.era.toFixed(2)}</div>
          <div style={{ textAlign: "right", color: "var(--ink-1)" }}>{p.whip.toFixed(2)}</div>
          <div style={{ textAlign: "right", fontSize: 10, color: p.delta.startsWith("+") ? "var(--pos)" : p.delta.startsWith("-") ? "var(--neg)" : "var(--ink-4)" }}>
            {p.delta}
          </div>
        </div>
      );
    })}
  </div>
);

// ============================================================
// Arsenal detail panel
// ============================================================
const ArsenalDetail = ({ arsenal }) => {
  const W = 300, H = 220;

  return (
    <div style={{ border: "1px solid var(--rule)" }}>
      <div className="rule-b" style={{ padding: "10px 16px", background: "var(--bg-1)", display: "flex", alignItems: "center", gap: 10 }}>
        <span className="h-label" style={{ color: "var(--ink-0)" }}>ARSENAL DETAIL · SKENES, P. (PIT)</span>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>5 PITCH TYPES · 2,134 PITCHES</span>
        <div style={{ flex: 1 }}/>
        <span className="t-mono" style={{ fontSize: 10, color: "var(--amber)" }}>PEAK: SPLINKER Stf+ 158</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr" }}>
        {/* Movement chart */}
        <div style={{ padding: 16, borderRight: "1px solid var(--rule)" }}>
          <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 8 }}>
            MOVEMENT PROFILE · iVB vs HB (in)
          </div>
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", display: "block" }}>
            {/* axes */}
            <line x1="150" y1="10" x2="150" y2="210" stroke="var(--rule-dim)"/>
            <line x1="20" y1="110" x2="290" y2="110" stroke="var(--rule-dim)"/>
            {/* gridlines */}
            {[-15, -10, -5, 5, 10, 15].map(v => (
              <g key={v}>
                <line x1={150 + v * 8} y1="10" x2={150 + v * 8} y2="210" stroke="var(--rule-dim)" strokeDasharray="1 3" strokeWidth="0.5"/>
                <line x1="20" y1={110 - v * 6} x2="290" y2={110 - v * 6} stroke="var(--rule-dim)" strokeDasharray="1 3" strokeWidth="0.5"/>
              </g>
            ))}
            <text x="288" y="108" fill="var(--ink-4)" fontSize="8" textAnchor="end" fontFamily="var(--ff-mono)">HB →</text>
            <text x="152" y="16" fill="var(--ink-4)" fontSize="8" fontFamily="var(--ff-mono)">↑ iVB</text>
            {/* bubbles */}
            {arsenal.map(a => {
              const cx = 150 + a.HB * 8;
              const cy = 110 - a.iVB * 6;
              const r  = 6 + a.usage / 4;
              return (
                <g key={a.t}>
                  <circle cx={cx} cy={cy} r={r} fill={stuffColor(a.stf)} opacity="0.25" stroke={stuffColor(a.stf)} strokeWidth="1.5"/>
                  <text x={cx} y={cy + 3} fill={stuffColor(a.stf)} fontSize="8.5" fontWeight="700" textAnchor="middle" fontFamily="var(--ff-mono)">{a.t}</text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Arsenal table */}
        <div>
          <div style={{
            display: "grid", gridTemplateColumns: "48px 1fr 52px 52px 52px",
            padding: "7px 12px", fontSize: 9, letterSpacing: "0.1em", color: "var(--ink-3)", fontWeight: 600,
          }} className="rule-b">
            <div>TYPE</div>
            <div>NAME</div>
            <div style={{ textAlign: "right" }}>MPH</div>
            <div style={{ textAlign: "right" }}>USE%</div>
            <div style={{ textAlign: "right", color: "var(--amber)" }}>Stf+</div>
          </div>
          {arsenal.map((a, i) => (
            <div key={a.t} style={{
              display: "grid", gridTemplateColumns: "48px 1fr 52px 52px 52px",
              padding: "10px 12px", fontFamily: "var(--ff-mono)", fontSize: 12,
              borderBottom: i < arsenal.length - 1 ? "1px solid var(--rule-dim)" : "none",
              alignItems: "center",
            }}>
              <div style={{ color: stuffColor(a.stf), fontWeight: 700 }}>{a.t}</div>
              <div style={{ color: "var(--ink-1)", fontFamily: "var(--ff-text)" }}>{a.name}</div>
              <div style={{ textAlign: "right", color: "var(--ink-1)" }}>{a.mph.toFixed(1)}</div>
              <div style={{ textAlign: "right", color: "var(--ink-2)" }}>{a.usage}</div>
              <div style={{ textAlign: "right", color: stuffColor(a.stf), fontWeight: 700 }}>{a.stf}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Right sidebar
// ============================================================
const RightPanel = () => (
  <aside className="rule-l" style={{ width: 260, flexShrink: 0, overflowY: "auto" }}>
    {/* Color key */}
    <div className="rule-b" style={{ padding: "12px 16px" }}>
      <div className="h-label" style={{ marginBottom: 10 }}>STUFF+ COLOR KEY</div>
      {COLOR_KEY.map(l => (
        <div key={l.v} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0", fontSize: 11 }}>
          <span style={{ width: 16, height: 4, background: l.c, flexShrink: 0 }}/>
          <span className="t-mono" style={{ color: "var(--ink-0)", width: 72 }}>{l.v}</span>
          <span className="h-label" style={{ fontSize: 9.5, color: l.c }}>{l.l}</span>
        </div>
      ))}
      <div className="t-mono" style={{ fontSize: 10, color: "var(--ink-4)", marginTop: 10, lineHeight: 1.6 }}>
        100 = League avg · SD=10<br/>
        Source: Statcast pitch-level
      </div>
    </div>

    {/* Model info */}
    <div className="rule-b" style={{ padding: "12px 16px" }}>
      <div className="h-label" style={{ marginBottom: 8 }}>MODEL · STUFF+ v3.1</div>
      <div style={{ fontSize: 11.5, color: "var(--ink-1)", lineHeight: 1.6 }}>
        投球品質の期待ランRVを、
        <span className="t-mono" style={{ color: "var(--amber)" }}>GBDT</span>
        で球種・球速・回転・リリース位置から予測。
        <span className="t-mono" style={{ color: "var(--amber)" }}> Loc+</span>はコース別xwOBA。
        <span className="t-mono" style={{ color: "var(--amber)" }}> Pitch+</span>は総合指標
        (0.6×Stuff + 0.4×Loc)。
      </div>
    </div>

    {/* Most improved */}
    <div style={{ padding: "12px 16px" }}>
      <div className="h-label" style={{ marginBottom: 8 }}>MOST IMPROVED · 30D</div>
      {MOST_IMPROVED.map((p, i) => (
        <div key={i} style={{
          display: "grid", gridTemplateColumns: "1fr 38px 40px",
          padding: "7px 0", fontSize: 11.5,
          borderBottom: "1px dashed var(--rule-dim)", alignItems: "center",
        }}>
          <span style={{ color: "var(--ink-0)" }}>{p.n}</span>
          <span className="t-mono" style={{ color: "var(--ink-3)", fontSize: 10 }}>{p.f}</span>
          <span className="t-mono" style={{ color: "var(--pos)", textAlign: "right", fontWeight: 700 }}>{p.d}</span>
        </div>
      ))}
    </div>
  </aside>
);

// ============================================================
// Main component
// ============================================================
const AdvancedStatsDesign = () => {
  const [activeFilter, setActiveFilter] = useState(0);

  return (
    <div style={{ flex: 1, display: "flex", minHeight: 0, background: "var(--bg-0)", overflow: "hidden" }}>
      {/* Main content */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {/* Filter bar */}
        <div className="rule-b" style={{
          padding: "10px 24px", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
        }}>
          <span className="h-label" style={{ color: "var(--ink-0)" }}>
            STUFF+ LEADERBOARD · 2024 SEASON
          </span>
          <span className="t-mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
            MIN 50 IP · N=84 PITCHERS
          </span>
          <div style={{ flex: 1 }}/>
          {FILTER_TABS.map((x, i) => (
            <button
              key={x}
              onClick={() => setActiveFilter(i)}
              style={{
                fontSize: 10.5, padding: "4px 9px",
                border: "1px solid var(--rule)",
                color: activeFilter === i ? "var(--bg-0)" : "var(--ink-2)",
                background: activeFilter === i ? "var(--amber)" : "transparent",
                fontFamily: "var(--ff-mono)", letterSpacing: "0.06em", fontWeight: 600,
                transition: "all .1s",
              }}
            >{x}</button>
          ))}
          <button className="t-mono" style={{
            fontSize: 10, padding: "4px 10px",
            border: "1px solid var(--rule-hi)", color: "var(--ink-1)", letterSpacing: "0.08em",
          }}>
            EXPORT CSV ↓
          </button>
        </div>

        {/* Headline metrics */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0 }} className="rule-b">
          {HEADLINE_METRICS.map((m, i) => (
            <div key={m.k} style={{
              padding: "14px 18px",
              borderRight: i < 3 ? "1px solid var(--rule)" : "none",
            }}>
              <div className="h-label" style={{ fontSize: 9, color: "var(--ink-3)", marginBottom: 4 }}>{m.k}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span style={{
                  fontSize: 28, fontFamily: "var(--ff-head)", fontWeight: 700,
                  color: m.tint, lineHeight: 1,
                }}>{m.v}</span>
                <span className="t-mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{m.d}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Leaderboard */}
        <div style={{ padding: "16px 24px" }}>
          <LeaderboardTable pitchers={PITCHERS}/>
        </div>

        {/* Arsenal detail */}
        <div style={{ padding: "0 24px 24px" }}>
          <ArsenalDetail arsenal={ARSENAL_SKENES}/>
        </div>
      </div>

      <RightPanel/>
    </div>
  );
};

export default AdvancedStatsDesign;
