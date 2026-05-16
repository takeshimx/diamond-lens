import { useEffect, useRef, useState } from 'react';

/**
 * LLM Usage Dashboard - Diamond Lens edition
 * Bloomberg Terminal x ESPN Statcast aesthetic.
 * 構造は project-2b-cbs ベース、視覚は diamond-lens の既存トークンに統一。
 */

// ─── Configurable ───────────────────────────────────────────
const MONTHLY_BUDGET_CAP_USD = 7.0;

// Feature / model color palette — diamond-lens の既存アクセント色のみ使用
const FEATURE_COLOR = {
  parse_query:        'var(--amber)',
  conversation:       'var(--info)',
  routing_judge:      'var(--pos)',
  reflection_judge:   'var(--purp)',
  synthesizer_judge:  'var(--amber-hi)',
  llm_judge:          'var(--amber-dim)',
  drift_alert_judge:  'var(--neg)',
  mlb_data_engine:    'var(--info)',
  analytics_base:     'var(--pos-dim)',
  analytics_pitcher:  'var(--amber)',
  analytics_batter:   'var(--purp)',
};
const featureColor = (id) => FEATURE_COLOR[id] ?? 'var(--ink-3)';

const MODEL_COLOR = {
  'gemini-2.5-flash':     'var(--amber)',
  'gemini-2.0-flash':     'var(--info)',
  'gemini-embedding-001': 'var(--purp)',
};
const modelColor = (id) => MODEL_COLOR[id] ?? 'var(--ink-3)';

// ─── Formatters ─────────────────────────────────────────────
const fmtUsd = (v) => {
  if (v === 0) return '$0.00';
  if (v < 0.01) return `$${v.toFixed(5)}`;
  if (v < 1) return `$${v.toFixed(4)}`;
  return `$${v.toFixed(2)}`;
};
const fmtInt = (v) => Math.round(v).toLocaleString();
const fmtMs = (ms) => {
  if (ms >= 10000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
};
const fmtMd = (iso) => {
  const [, m, d] = iso.split('-');
  return `${parseInt(m, 10)}/${parseInt(d, 10)}`;
};
const fmtTimeShort = (iso) => {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch { return iso; }
};

const MONTH_NAMES = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];

function shiftMonth(year, month, delta) {
  const m0 = (month - 1) + delta;
  const dy = Math.floor(m0 / 12);
  const dm = ((m0 % 12) + 12) % 12;
  return { year: year + dy, month: dm + 1 };
}
function daysInMonth(year, month) { return new Date(year, month, 0).getDate(); }

// ─── Inline SVG icons (currentColor) ────────────────────────
const Icon = ({ size = 12, stroke = 2, children }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block' }}>
    {children}
  </svg>
);
const IconL  = (p) => <Icon {...p}><polyline points="15 18 9 12 15 6" /></Icon>;
const IconR  = (p) => <Icon {...p}><polyline points="9 18 15 12 9 6" /></Icon>;
const IconU  = (p) => <Icon {...p}><polyline points="18 15 12 9 6 15" /></Icon>;
const IconD  = (p) => <Icon {...p}><polyline points="6 9 12 15 18 9" /></Icon>;
const IconRefresh = (p) => <Icon {...p}><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></Icon>;

// ─── Card primitive (sharp, ruled) ───────────────────────────
const Card = ({ children, style }) => (
  <div style={{
    background: 'var(--bg-1)',
    border: '1px solid var(--rule)',
    ...style,
  }}>
    {children}
  </div>
);

const CardHead = ({ title, subtitle, right }) => (
  <div className="rule-b" style={{
    padding: '10px 14px',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
  }}>
    <div>
      <div className="h-label" style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--ink-2)' }}>{title}</div>
      {subtitle && (
        <div style={{ fontSize: 10.5, color: 'var(--ink-4)', marginTop: 3, fontFamily: 'var(--ff-mono)' }}>
          {subtitle}
        </div>
      )}
    </div>
    {right}
  </div>
);

// ─── Month strip ────────────────────────────────────────────
function MonthStrip({ year, month, range, onPrev, onNext, onRange, canGoNext }) {
  const btnStyle = (active = false) => ({
    height: 26, padding: '0 10px',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    color: active ? 'var(--ink-0)' : 'var(--ink-2)',
    background: active ? 'var(--bg-3)' : 'transparent',
    fontFamily: 'var(--ff-mono)', fontSize: 10.5, letterSpacing: '0.08em',
    textTransform: 'uppercase',
  });
  const navBtn = (disabled = false) => ({
    width: 26, height: 26,
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    color: disabled ? 'var(--ink-4)' : 'var(--ink-2)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.4 : 1,
  });
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: 4,
      background: 'var(--bg-1)', border: '1px solid var(--rule)',
      marginBottom: 16,
    }}>
      <button onClick={onPrev} title="Previous month" style={navBtn(false)}><IconL /></button>
      <div className="t-mono" style={{
        padding: '0 10px', minWidth: 120, textAlign: 'center',
        fontSize: 12.5, color: 'var(--ink-0)', letterSpacing: '0.06em',
      }}>
        {year} / {MONTH_NAMES[month - 1]}
      </div>
      <button onClick={onNext} disabled={!canGoNext} title="Next month" style={navBtn(!canGoNext)}><IconR /></button>
      <div style={{ width: 1, height: 16, background: 'var(--rule)', margin: '0 4px' }} />
      {['Month', '30d', 'YTD'].map(r => (
        <button key={r} onClick={() => onRange(r)} style={btnStyle(range === r)}>
          {r === 'Month' ? 'This month' : r === '30d' ? 'Last 30d' : 'YTD'}
        </button>
      ))}
    </div>
  );
}

// ─── KPI cards ──────────────────────────────────────────────
function KPICards({ data }) {
  const s = data.summary;
  const ps = data.prev_summary || {};
  const tokens = (s.total_input_tokens || 0) + (s.total_output_tokens || 0);
  const inPct = tokens === 0 ? 0 : ((s.total_input_tokens || 0) / tokens) * 100;

  const deltaPct = ps.total_cost_usd > 0
    ? Math.round(((s.total_cost_usd - ps.total_cost_usd) / ps.total_cost_usd) * 100) : 0;

  const today = new Date();
  const isCurrentMonth = s.year === today.getFullYear() && s.month === today.getMonth() + 1;
  const daysElapsed = isCurrentMonth ? today.getDate() : daysInMonth(s.year, s.month);
  const callsPerDay = daysElapsed > 0 ? (s.total_invocations || 0) / daysElapsed : 0;
  const prevMonthLabel = MONTH_NAMES[shiftMonth(s.year, s.month, -1).month - 1];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
      <KpiCard
        label="TOTAL COST"
        dotColor="var(--amber)"
        value={fmtUsd(s.total_cost_usd || 0)}
        foot="USD this month"
        delta={ps.total_cost_usd > 0 ? { sign: deltaPct, label: `${Math.abs(deltaPct)}% vs ${prevMonthLabel}` } : null}
      />
      <KpiCard
        label="INVOCATIONS"
        dotColor="var(--info)"
        value={(s.total_invocations || 0).toLocaleString()}
        foot={`API calls · ${callsPerDay.toFixed(2)} / day avg`}
      />
      <KpiCard
        label="TOKENS"
        dotColor="var(--amber-hi)"
        value={fmtInt(tokens)}
        custom={
          <>
            <div style={{ display: 'flex', height: 4, background: 'var(--bg-3)', marginTop: 6 }}>
              <span style={{ width: inPct + '%', background: 'var(--amber)' }} />
              <span style={{ width: (100 - inPct) + '%', background: 'var(--info)' }} />
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 10, color: 'var(--ink-3)', fontFamily: 'var(--ff-mono)' }}>
              <span><span style={{ display: 'inline-block', width: 7, height: 7, background: 'var(--amber)', marginRight: 5, verticalAlign: 'middle' }} />In {fmtInt(s.total_input_tokens || 0)}</span>
              <span><span style={{ display: 'inline-block', width: 7, height: 7, background: 'var(--info)', marginRight: 5, verticalAlign: 'middle' }} />Out {fmtInt(s.total_output_tokens || 0)}</span>
            </div>
          </>
        }
      />
      <KpiCard
        label="LATENCY"
        dotColor="var(--pos)"
        value={<>{((s.avg_latency_ms || 0) / 1000).toFixed(1)}<span style={{ fontSize: 16, color: 'var(--ink-2)', fontWeight: 400, marginLeft: 2 }}>s</span></>}
        foot={`avg · p95 ${fmtMs(s.p95_latency_ms || 0)}`}
        statusBadge="OK"
      />
    </div>
  );
}

function KpiCard({ label, dotColor, value, foot, delta, custom, statusBadge }) {
  return (
    <div style={{
      background: 'var(--bg-1)', border: '1px solid var(--rule)',
      padding: '14px 16px 12px', minHeight: 118,
      display: 'flex', flexDirection: 'column',
    }}>
      <div className="h-label" style={{ fontSize: 9.5, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 6, letterSpacing: '0.14em' }}>
        <span style={{ width: 7, height: 7, background: dotColor, display: 'inline-block' }} />
        {label}
      </div>
      <div className="t-digit" style={{ fontSize: 28, color: 'var(--ink-0)', letterSpacing: '-0.02em', lineHeight: 1.05, marginTop: 8 }}>
        {value}
      </div>
      {custom}
      {(foot || delta || statusBadge) && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginTop: 'auto', paddingTop: 8 }}>
          {foot && <span style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>{foot}</span>}
          {delta != null && (
            <span className="t-mono" style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              fontSize: 10, fontWeight: 600, padding: '2px 6px',
              color: delta.sign > 0 ? 'var(--neg)' : delta.sign < 0 ? 'var(--pos)' : 'var(--ink-3)',
              background: 'var(--bg-2)', border: '1px solid var(--rule)',
            }}>
              {delta.sign > 0 ? <IconU size={9} stroke={3} /> : delta.sign < 0 ? <IconD size={9} stroke={3} /> : null}
              {delta.label}
            </span>
          )}
          {statusBadge && (
            <span className="t-mono" style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              fontSize: 10, fontWeight: 600, padding: '2px 6px',
              color: 'var(--pos)', background: 'var(--bg-2)', border: '1px solid var(--rule)',
            }}>
              <IconU size={9} stroke={3} />{statusBadge}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Budget + Efficiency ────────────────────────────────────
function BudgetAndEfficiency({ data }) {
  const s = data.summary;
  const cap = MONTHLY_BUDGET_CAP_USD;
  const spent = s.total_cost_usd || 0;
  const today = new Date();
  const isCurrentMonth = s.year === today.getFullYear() && s.month === today.getMonth() + 1;
  const daysElapsed = isCurrentMonth ? today.getDate() : daysInMonth(s.year, s.month);
  const totalDays = daysInMonth(s.year, s.month);
  const dailyAvg = daysElapsed > 0 ? spent / daysElapsed : 0;
  const projected = dailyAvg * totalDays;
  const pct = (spent / cap) * 100;
  const projPct = Math.min((projected / cap) * 100, 100);
  const { year: ny, month: nm } = shiftMonth(s.year, s.month, 1);
  const resetISO = `${ny}-${String(nm).padStart(2, '0')}-01`;
  const tokens = (s.total_input_tokens || 0) + (s.total_output_tokens || 0);
  const costPerCall = s.total_invocations > 0 ? spent / s.total_invocations : 0;
  const costPer1K = tokens > 0 ? (spent / tokens) * 1000 : 0;
  const successRate = s.total_invocations > 0 ? (s.success_count || 0) / s.total_invocations : 1;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 10, marginBottom: 16 }}>
      <Card>
        <CardHead
          title="MONTHLY BUDGET"
          subtitle={`Cap: $${cap.toFixed(2)} · Resets ${resetISO}`}
          right={
            <span className="t-mono" style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              fontSize: 10.5, color: 'var(--amber)',
              border: '1px solid var(--amber-dim)', padding: '3px 8px',
              background: 'var(--bg-2)',
            }}>
              <IconU size={9} stroke={2.4} />
              Projected {fmtUsd(projected)} ({((projected / cap) * 100).toFixed(2)}%)
            </span>
          }
        />
        <div style={{ padding: '14px' }}>
          <div style={{ position: 'relative', height: 10, background: 'var(--bg-3)', border: '1px solid var(--rule-dim)' }}>
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: Math.max(pct, 0.6) + '%', background: 'var(--amber)' }} />
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: projPct + '%', borderRight: '1px dashed var(--amber-hi)' }} />
          </div>
          <div className="t-mono" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--ink-4)', marginTop: 6 }}>
            <span>$0</span><span>${(cap * 0.25).toFixed(2)}</span><span>${(cap * 0.5).toFixed(0)}</span><span>${(cap * 0.75).toFixed(2)}</span><span>${cap.toFixed(0)}</span>
          </div>
          <div className="rule-t" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10, paddingTop: 10, fontSize: 10.5, color: 'var(--ink-3)' }}>
            <span>
              Spent <b className="t-mono" style={{ color: 'var(--ink-0)' }}>{fmtUsd(spent)}</b> of ${cap.toFixed(2)} ({pct.toFixed(3)}%) · <span style={{ color: 'var(--pos)' }}>{fmtUsd(cap - spent)} remaining</span>
            </span>
            <span>Daily avg <b className="t-mono" style={{ color: 'var(--ink-0)' }}>{fmtUsd(dailyAvg)}</b></span>
          </div>
        </div>
      </Card>

      <Card>
        <CardHead title="EFFICIENCY" right={<span className="t-mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>{MONTH_NAMES[s.month - 1]}</span>} />
        <div style={{ padding: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <EffCell label="COST / CALL" value={fmtUsd(costPerCall)} />
          <EffCell label="$ / 1K TOKENS" value={fmtUsd(costPer1K)} />
          <EffCell label="CACHE HIT" value="—" muted />
          <EffCell label="SUCCESS" value={`${Math.round(successRate * 100)}%`} color="var(--pos)" />
        </div>
      </Card>
    </div>
  );
}

function EffCell({ label, value, muted, color }) {
  return (
    <div>
      <div className="h-label" style={{ fontSize: 9.5, color: 'var(--ink-3)', letterSpacing: '0.12em' }}>{label}</div>
      <div className="t-digit" style={{ fontSize: 18, color: muted ? 'var(--ink-3)' : (color || 'var(--ink-0)'), marginTop: 3 }}>{value}</div>
    </div>
  );
}

// ─── Cost by feature ────────────────────────────────────────
function FeatureCard({ features }) {
  const total = features.reduce((sum, f) => sum + (f.cost_usd || 0), 0) || 1;
  const maxLat = Math.max(...features.map(f => f.avg_latency_ms || 0), 1);
  return (
    <Card>
      <CardHead
        title="COST BY FEATURE"
        subtitle="Token volume (in/out) and average latency per feature"
        right={
          <div style={{ display: 'flex', gap: 12, fontSize: 10, color: 'var(--ink-2)' }}>
            <span><span style={{ display: 'inline-block', width: 8, height: 8, background: 'var(--amber)', marginRight: 5, verticalAlign: 'middle' }} />Input tokens</span>
            <span><span style={{ display: 'inline-block', width: 8, height: 8, background: 'var(--info)', marginRight: 5, verticalAlign: 'middle' }} />Output tokens</span>
          </div>
        }
      />
      {features.length === 0 ? (
        <div style={{ padding: 24, textAlign: 'center', fontSize: 11, color: 'var(--ink-4)', fontFamily: 'var(--ff-mono)', letterSpacing: '0.08em' }}>NO DATA THIS MONTH</div>
      ) : (
        <div style={{ padding: 6 }}>
          {features.map((f, idx) => {
            const tokensTotal = (f.input_tokens || 0) + (f.output_tokens || 0) || 1;
            const inPct = ((f.input_tokens || 0) / tokensTotal) * 100;
            const outPct = ((f.output_tokens || 0) / tokensTotal) * 100;
            const sharePct = ((f.cost_usd || 0) / total) * 100;
            const color = featureColor(f.feature);
            return (
              <div key={f.feature} style={{
                display: 'grid', gridTemplateColumns: '140px 1fr 90px', gap: 14,
                alignItems: 'center', padding: '10px 10px',
                borderBottom: idx === features.length - 1 ? 'none' : '1px solid var(--rule-dim)',
              }}>
                <div className="t-mono" style={{ fontSize: 12, color: 'var(--ink-1)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, background: color, flexShrink: 0 }} />
                  {f.feature}
                </div>
                <div>
                  <div style={{ display: 'flex', height: 8, background: 'var(--bg-3)' }}>
                    <span style={{ width: inPct + '%', background: color }} />
                    <span style={{ width: outPct + '%', background: 'var(--info)' }} />
                  </div>
                  <div className="t-mono" style={{ display: 'flex', gap: 14, fontSize: 9.5, color: 'var(--ink-3)', marginTop: 5 }}>
                    <span>{f.invocations} call{f.invocations === 1 ? '' : 's'}</span>
                    <span>{fmtInt(f.input_tokens || 0)} in</span>
                    <span>{fmtInt(f.output_tokens || 0)} out</span>
                    <span>
                      {fmtMs(f.avg_latency_ms || 0)} avg
                      <span style={{ display: 'inline-block', width: 40, height: 3, background: 'var(--bg-3)', marginLeft: 6, verticalAlign: 'middle' }}>
                        <span style={{ display: 'block', height: '100%', width: ((f.avg_latency_ms || 0) / maxLat * 100) + '%', background: 'var(--info)' }} />
                      </span>
                    </span>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="t-digit" style={{ fontSize: 13, color: 'var(--ink-0)' }}>{fmtUsd(f.cost_usd || 0)}</div>
                  <div className="t-mono" style={{ fontSize: 9.5, color: 'var(--ink-4)', marginTop: 2 }}>{sharePct.toFixed(1)}% of total</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <div className="rule-t" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', fontSize: 10.5, color: 'var(--ink-3)' }}>
        <span>Active features <b className="t-mono" style={{ color: 'var(--ink-0)' }}>{features.length}</b></span>
      </div>
    </Card>
  );
}

// ─── Models card (donut) ────────────────────────────────────
function ModelDonut({ models }) {
  const total = models.reduce((sum, m) => sum + (m.cost_usd || 0), 0);
  const totalCalls = models.reduce((sum, m) => sum + (m.invocations || 0), 0);
  const activeModels = models.filter(m => (m.invocations || 0) > 0).length;
  const R = 15.915;
  let acc = 0;
  return (
    <svg width="150" height="150" viewBox="0 0 42 42">
      <circle cx="21" cy="21" r={R} fill="none" stroke="var(--bg-3)" strokeWidth="5" />
      {models.map(m => {
        if (!m.cost_usd) return null;
        const pct = total > 0 ? (m.cost_usd / total) * 100 : 0;
        const dasharray = `${pct} ${100 - pct}`;
        const dashoffset = 25 - acc;
        acc += pct;
        return (
          <circle key={m.model} cx="21" cy="21" r={R} fill="none"
            stroke={modelColor(m.model)} strokeWidth="5"
            strokeDasharray={dasharray} strokeDashoffset={dashoffset}
            transform="rotate(-90 21 21)" />
        );
      })}
      <text x="21" y="20" textAnchor="middle" fill="var(--ink-0)"
        fontSize="5.5" fontWeight="600" fontFamily="JetBrains Mono, monospace">
        {fmtUsd(total)}
      </text>
      <text x="21" y="25" textAnchor="middle" fill="var(--ink-4)"
        fontSize="2.6" fontFamily="JetBrains Mono, monospace">
        {totalCalls} call{totalCalls === 1 ? '' : 's'} · {activeModels} model{activeModels === 1 ? '' : 's'}
      </text>
    </svg>
  );
}

function ModelsCard({ models }) {
  const total = models.reduce((sum, m) => sum + (m.cost_usd || 0), 0) || 1;
  return (
    <Card>
      <CardHead title="MODELS" subtitle="Cost share & call count" />
      <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 16px' }}>
        <ModelDonut models={models} />
      </div>
      {models.length === 0 ? (
        <div style={{ padding: 16, textAlign: 'center', fontSize: 11, color: 'var(--ink-4)', fontFamily: 'var(--ff-mono)', letterSpacing: '0.08em' }}>NO INVOCATIONS</div>
      ) : (
        <div style={{ padding: '0 14px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {models.map(m => {
            const pct = total > 0 ? Math.round(((m.cost_usd || 0) / total) * 100) : 0;
            return (
              <div key={m.model} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 9, height: 9, background: modelColor(m.model), flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="t-mono" style={{ fontSize: 11.5, color: 'var(--ink-1)' }}>{m.model}</div>
                  <div className="t-mono" style={{ fontSize: 9.5, color: 'var(--ink-4)', marginTop: 2 }}>{m.invocations} call{m.invocations === 1 ? '' : 's'}</div>
                </div>
                <div className="t-mono" style={{ width: 40, textAlign: 'right', fontSize: 11.5, color: 'var(--ink-2)' }}>{pct}%</div>
                <div className="t-digit" style={{ width: 76, textAlign: 'right', fontSize: 12, color: 'var(--ink-0)' }}>{fmtUsd(m.cost_usd || 0)}</div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

// ─── Daily trend chart ──────────────────────────────────────
function TrendChart({ daily }) {
  const [metric, setMetric] = useState('cost');
  const wrapRef = useRef(null);
  const ttRef = useRef(null);
  const [w, setW] = useState(800);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(entries => { for (const e of entries) setW(e.contentRect.width); });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const H = 240;
  const pad = { l: 46, r: 14, t: 14, b: 26 };
  const innerW = w - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;
  const n = daily.length;
  const values = daily.map(d => metric === 'cost' ? d.cost_usd : metric === 'tokens' ? d.tokens : d.invocations);
  const maxV = (Math.max(...values, 0) * 1.18) || 1;
  const xs = (i) => pad.l + (innerW * i) / Math.max(n - 1, 1);
  const ys = (v) => pad.t + innerH - (v / maxV) * innerH;
  const color = metric === 'cost' ? 'var(--amber)' : metric === 'tokens' ? 'var(--amber-hi)' : 'var(--info)';
  const colorRaw = metric === 'cost' ? '#d49b3f' : metric === 'tokens' ? '#e3b35a' : '#7da4cc';
  const gridVals = [0.25, 0.5, 0.75, 1].map(k => maxV * k);
  const ticks = [];
  for (let i = 0; i < n; i++) if (i === 0 || i === n - 1 || i % 2 === 0) ticks.push(i);

  const fmtAxisV = (v) => {
    if (metric === 'cost') return '$' + v.toFixed(3);
    if (metric === 'tokens') return v >= 1000 ? (v / 1000).toFixed(1) + 'k' : String(Math.round(v));
    return String(Math.round(v));
  };

  let dArea = `M ${xs(0)} ${ys(0)} `;
  let dLine = `M ${xs(0)} ${ys(values[0] ?? 0)} `;
  for (let i = 1; i < n; i++) {
    dArea += `L ${xs(i)} ${ys(values[i])} `;
    dLine += `L ${xs(i)} ${ys(values[i])} `;
  }
  dArea += `L ${xs(Math.max(n - 1, 0))} ${ys(0)} Z`;
  const gradId = 'usage-grad-' + metric;

  const onMove = (i, e) => {
    const d = daily[i];
    const tt = ttRef.current; if (!tt) return;
    const cv = metric === 'cost' ? fmtUsd(d.cost_usd) : metric === 'tokens' ? fmtInt(d.tokens) : fmtInt(d.invocations);
    tt.innerHTML = `
      <div style="color: var(--ink-3); font-size: 9.5px; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px;">${d.date}</div>
      <div style="display:flex;justify-content:space-between;gap:14px;"><span>${metric}</span><span style="color:var(--ink-0);font-family:var(--ff-mono);">${cv}</span></div>
      <div style="display:flex;justify-content:space-between;gap:14px;"><span>calls</span><span style="color:var(--ink-0);font-family:var(--ff-mono);">${fmtInt(d.invocations)}</span></div>
      <div style="display:flex;justify-content:space-between;gap:14px;"><span>tokens</span><span style="color:var(--ink-0);font-family:var(--ff-mono);">${fmtInt(d.tokens)}</span></div>
      <div style="display:flex;justify-content:space-between;gap:14px;"><span>cost</span><span style="color:var(--ink-0);font-family:var(--ff-mono);">${fmtUsd(d.cost_usd)}</span></div>`;
    tt.style.opacity = 1;
    tt.style.left = e.clientX + 'px';
    tt.style.top = (e.clientY - 8) + 'px';
  };
  const onLeave = () => { if (ttRef.current) ttRef.current.style.opacity = 0; };

  return (
    <Card style={{ marginBottom: 16 }}>
      <CardHead
        title="DAILY TREND"
        subtitle={n > 0 ? `Last ${n} days · ${fmtMd(daily[0].date)} → ${fmtMd(daily[n - 1].date)}` : `Last ${n} days`}
        right={
          <div style={{ display: 'inline-flex', border: '1px solid var(--rule)', background: 'var(--bg-2)' }}>
            {['cost', 'tokens', 'calls'].map(m => (
              <button key={m} onClick={() => setMetric(m)} style={{
                padding: '5px 10px', fontSize: 10.5,
                fontFamily: 'var(--ff-mono)', letterSpacing: '0.08em',
                color: metric === m ? 'var(--ink-0)' : 'var(--ink-2)',
                background: metric === m ? 'var(--bg-3)' : 'transparent',
                textTransform: 'uppercase',
              }}>{m}</button>
            ))}
          </div>
        }
      />
      <div ref={wrapRef} style={{ position: 'relative', width: '100%', height: H, padding: 4 }}>
        <svg width="100%" height={H} viewBox={`0 0 ${w} ${H}`} preserveAspectRatio="none">
          <defs>
            <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor={colorRaw} stopOpacity=".30" />
              <stop offset="1" stopColor={colorRaw} stopOpacity="0" />
            </linearGradient>
          </defs>
          {gridVals.map((v, i) => (
            <line key={i} x1={pad.l} x2={w - pad.r} y1={ys(v)} y2={ys(v)} stroke="var(--rule-dim)" strokeDasharray="2 4" />
          ))}
          <line x1={pad.l} x2={w - pad.r} y1={ys(0)} y2={ys(0)} stroke="var(--rule)" />
          {gridVals.map((v, i) => (
            <text key={i} x={pad.l - 8} y={ys(v) + 3} textAnchor="end" fill="var(--ink-4)" fontSize="9" fontFamily="JetBrains Mono, monospace">{fmtAxisV(v)}</text>
          ))}
          {ticks.map(i => (
            <text key={i} x={xs(i)} y={H - pad.b + 14} textAnchor="middle" fill="var(--ink-4)" fontSize="9" fontFamily="JetBrains Mono, monospace">{fmtMd(daily[i].date)}</text>
          ))}
          <path d={dArea} fill={`url(#${gradId})`} />
          <path d={dLine} stroke={color} strokeWidth="1.6" fill="none" strokeLinejoin="round" />
          {values.map((v, i) => v > 0 ? (
            <g key={i}>
              <circle cx={xs(i)} cy={ys(v)} r="7" fill={color} opacity=".18" />
              <circle cx={xs(i)} cy={ys(v)} r="3" fill={color} stroke="var(--bg-0)" strokeWidth="1.6" />
            </g>
          ) : null)}
          {daily.map((_, i) => (
            <rect key={i}
              x={xs(i) - innerW / Math.max(n - 1, 1) / 2} y={pad.t}
              width={innerW / Math.max(n - 1, 1)} height={innerH}
              fill="transparent" style={{ cursor: 'crosshair' }}
              onMouseMove={(e) => onMove(i, e)} onMouseLeave={onLeave} />
          ))}
        </svg>
        <div ref={ttRef} style={{
          position: 'fixed', pointerEvents: 'none',
          background: 'var(--bg-2)', border: '1px solid var(--rule-hi)',
          padding: '8px 10px', fontSize: 11, color: 'var(--ink-1)',
          opacity: 0, transition: 'opacity 80ms',
          transform: 'translate(-50%, -100%)', zIndex: 100, whiteSpace: 'nowrap',
        }} />
      </div>
    </Card>
  );
}

// ─── Recent invocations table ───────────────────────────────
function RecentTable({ rows }) {
  return (
    <Card>
      <CardHead title="RECENT INVOCATIONS" subtitle={`Most recent ${rows.length} call${rows.length === 1 ? '' : 's'} · hover row for error detail`} />
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['TIME', 'FEATURE', 'MODEL', 'IN', 'OUT', 'LATENCY', 'COST', 'STATUS'].map((h, i) => (
                <th key={h} className="h-label" style={{
                  textAlign: i >= 3 && i <= 6 ? 'right' : 'left',
                  fontSize: 9.5, color: 'var(--ink-3)', letterSpacing: '0.12em',
                  padding: '8px 12px', borderBottom: '1px solid var(--rule)',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={8} style={{ padding: 24, textAlign: 'center', color: 'var(--ink-4)', fontFamily: 'var(--ff-mono)', letterSpacing: '0.08em' }}>NO INVOCATIONS YET</td></tr>
            ) : rows.map(r => {
              const ok = r.success === true;
              return (
                <tr key={r.log_id} title={r.error_type ?? undefined}>
                  <td className="t-mono" style={cellStyle()}>{fmtTimeShort(r.timestamp)}</td>
                  <td style={cellStyle()}>
                    <span style={{ display: 'inline-block', width: 8, height: 8, background: featureColor(r.feature), marginRight: 8, verticalAlign: 'middle' }} />
                    <span className="t-mono">{r.feature}</span>
                  </td>
                  <td className="t-mono" style={cellStyle()}>{r.model}</td>
                  <td className="t-mono" style={cellStyle('right')}>{fmtInt(r.input_tokens || 0)}</td>
                  <td className="t-mono" style={cellStyle('right')}>{fmtInt(r.output_tokens || 0)}</td>
                  <td className="t-mono" style={cellStyle('right')}>{Math.round(r.llm_latency_ms || 0).toLocaleString()} ms</td>
                  <td className="t-mono" style={cellStyle('right')}>{fmtUsd(r.estimated_cost_usd || 0)}</td>
                  <td style={cellStyle()}>
                    <span className="t-mono" style={{
                      display: 'inline-flex', alignItems: 'center', gap: 5,
                      fontSize: 10, fontWeight: 600, padding: '2px 8px',
                      color: ok ? 'var(--pos)' : 'var(--neg)',
                      border: `1px solid ${ok ? 'var(--pos-dim)' : 'var(--neg-dim)'}`,
                      background: 'var(--bg-2)',
                    }}>
                      <span style={{ width: 5, height: 5, background: 'currentColor' }} />
                      {ok ? '200' : 'ERR'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
const cellStyle = (align = 'left') => ({
  padding: '10px 12px', borderBottom: '1px solid var(--rule-dim)',
  fontSize: 11.5, color: 'var(--ink-1)', textAlign: align,
});

// ─── Root component ─────────────────────────────────────────
const UsageDashboard = ({ getBackendURL, getAuthHeaders }) => {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [range, setRange] = useState('Month');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let aborted = false;
    setLoading(true); setError(null);
    (async () => {
      try {
        const baseURL = getBackendURL();
        const url = `${baseURL}/api/v1/usage/dashboard?year=${year}&month=${month}&trend_days=30&recent_limit=20`;
        const headers = await getAuthHeaders();
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = await res.json();
        if (!payload.success) throw new Error('API returned success=false');
        if (!aborted) setData(payload.data);
      } catch (e) {
        if (!aborted) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!aborted) setLoading(false);
      }
    })();
    return () => { aborted = true; };
  }, [year, month, refreshTick, getBackendURL, getAuthHeaders]);

  const handlePrev = () => { const { year: y, month: m } = shiftMonth(year, month, -1); setYear(y); setMonth(m); };
  const handleNext = () => { const { year: y, month: m } = shiftMonth(year, month, 1); setYear(y); setMonth(m); };
  const canGoNext = !(year === today.getFullYear() && month === today.getMonth() + 1);

  return (
    <div style={{ padding: '24px 32px', height: '100%', overflowY: 'auto', background: 'var(--bg-0)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
        <div>
          <div className="h-display" style={{ fontSize: 26, color: 'var(--ink-0)' }}>LLM USAGE</div>
          <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 4 }}>
            AI機能のトークン使用量・コスト・呼び出し履歴。月次予算と着地予測も併記。
          </div>
        </div>
        <button onClick={() => setRefreshTick(t => t + 1)} className="t-mono" style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '6px 12px', fontSize: 10.5,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--ink-1)', background: 'var(--bg-1)',
          border: '1px solid var(--rule)',
        }}>
          <IconRefresh size={11} /> Refresh
        </button>
      </div>

      <MonthStrip
        year={year} month={month} range={range}
        onPrev={handlePrev} onNext={handleNext} onRange={setRange}
        canGoNext={canGoNext}
      />

      {error && (
        <div style={{
          padding: 12, marginBottom: 16,
          background: 'var(--bg-1)', border: '1px solid var(--neg-dim)',
          color: 'var(--neg)', fontSize: 12, fontFamily: 'var(--ff-mono)',
        }}>
          Failed to load: {error}
        </div>
      )}

      {loading && !data && (
        <Card><div style={{ padding: 32, textAlign: 'center', color: 'var(--ink-4)', fontFamily: 'var(--ff-mono)', letterSpacing: '0.08em' }}>LOADING…</div></Card>
      )}

      {data && (
        <>
          <KPICards data={data} />
          <BudgetAndEfficiency data={data} />
          <div style={{ display: 'grid', gridTemplateColumns: '1.55fr 1fr', gap: 10, marginBottom: 16 }}>
            <FeatureCard features={data.by_feature || []} />
            <ModelsCard models={data.by_model || []} />
          </div>
          <TrendChart daily={data.daily || []} />
          <RecentTable rows={data.recent || []} />
        </>
      )}
    </div>
  );
};

export default UsageDashboard;
