import { useCallback, useEffect, useState } from 'react';
import { TRACE_LABELS, TRACE_LABEL_MAP, nodeColor, nodeMeta } from '../constants/traceLabels.js';

/**
 * Trace Viewer + Failure Labeling (P0-1)
 *
 * llm_interaction_logs を trace_id 単位で束ねたエージェント実行経路を閲覧し、
 * 失敗ラベルを付与する画面。視覚は UsageDashboard と同じ diamond-lens トークンに統一。
 */

// ─── Formatters ─────────────────────────────────────────────
const fmtMs = (ms) => {
  if (!ms) return '—';
  if (ms >= 10000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
};
const fmtUsd = (v) => {
  if (!v) return '$0';
  if (v < 0.01) return `$${v.toFixed(5)}`;
  return `$${v.toFixed(4)}`;
};
const fmtTime = (iso) => {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const p = (n) => String(n).padStart(2, '0');
    return `${p(d.getMonth() + 1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  } catch { return iso; }
};
const fmtClock = (iso) => {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const p = (n) => String(n).padStart(2, '0');
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${String(d.getMilliseconds()).padStart(3, '0')}`;
  } catch { return ''; }
};

// ─── Primitives ─────────────────────────────────────────────
const Card = ({ children, style }) => (
  <div style={{ background: 'var(--bg-1)', border: '1px solid var(--rule)', ...style }}>
    {children}
  </div>
);

const CardHead = ({ title, subtitle, right }) => (
  <div className="rule-b" style={{
    padding: '10px 14px', display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', gap: 12,
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

const Chip = ({ color, children, filled = false, title }) => (
  <span title={title} style={{
    fontFamily: 'var(--ff-mono)', fontSize: 9, fontWeight: 700, letterSpacing: '0.1em',
    padding: '2px 6px', border: `1px solid ${color}`,
    color: filled ? 'var(--bg-0)' : color,
    background: filled ? color : 'transparent',
    whiteSpace: 'nowrap',
  }}>{children}</span>
);

const btn = (active = false, disabled = false) => ({
  height: 26, padding: '0 10px',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  border: '1px solid var(--rule)',
  color: disabled ? 'var(--ink-4)' : active ? 'var(--ink-0)' : 'var(--ink-2)',
  background: active ? 'var(--bg-3)' : 'transparent',
  fontFamily: 'var(--ff-mono)', fontSize: 10.5, letterSpacing: '0.08em',
  textTransform: 'uppercase', cursor: disabled ? 'not-allowed' : 'pointer',
});

// ─── Step row ───────────────────────────────────────────────
function StepRow({ step, index }) {
  const [open, setOpen] = useState(false);
  const color = nodeColor(step.node);
  const failed = step.success === false;
  // 「LLM を呼んでいないステップ」= ツール実行行。model が NULL であることで判別する
  const isTool = !step.is_llm_call;
  const tools = step.tool_calls || [];

  return (
    <div style={{ borderBottom: '1px solid var(--rule)' }}>
      <div
        onClick={() => setOpen((v) => !v)}
        style={{
          padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 10,
          cursor: 'pointer', background: failed ? 'oklch(from var(--neg) l c h / 0.07)' : 'transparent',
        }}
      >
        <span style={{
          fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--ink-4)',
          width: 20, textAlign: 'right', flexShrink: 0,
        }}>{index + 1}</span>
        <span style={{ width: 6, height: 6, background: color, flexShrink: 0 }} />
        <Chip color={color} title={nodeMeta(step.node).desc}>{step.node.toUpperCase()}</Chip>
        {step.iteration !== null && step.iteration !== undefined && (
          <Chip color="var(--ink-3)" title="ループ周回数">ITER {step.iteration}</Chip>
        )}
        {isTool && <Chip color="var(--ink-4)" title="LLM を呼んでいないステップ">TOOL</Chip>}
        {failed && <Chip color="var(--neg)" filled>FAIL</Chip>}

        <span style={{
          flex: 1, minWidth: 0, fontFamily: 'var(--ff-mono)', fontSize: 10.5,
          color: 'var(--ink-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {tools.length > 0
            ? tools.map((t) => t.name).join(' · ')
            : (step.response_answer || '').slice(0, 80) || '—'}
        </span>

        <span style={{ fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--ink-4)', flexShrink: 0 }}>
          {fmtMs(step.llm_latency_ms)}
        </span>
        <span style={{ fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--ink-4)', flexShrink: 0, width: 62, textAlign: 'right' }}>
          {fmtClock(step.timestamp)}
        </span>
      </div>

      {open && (
        <div style={{ padding: '10px 12px 14px 42px', background: 'var(--bg-0)', fontSize: 11 }}>
          {tools.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div className="h-label" style={{ fontSize: 9, color: 'var(--ink-3)', marginBottom: 5 }}>TOOL CALLS</div>
              {tools.map((t, i) => (
                <div key={i} style={{
                  fontFamily: 'var(--ff-mono)', fontSize: 10.5, padding: '4px 8px',
                  border: '1px solid var(--rule)', marginBottom: 4,
                  color: t.ok === false ? 'var(--neg)' : 'var(--ink-2)',
                }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontWeight: 700 }}>{t.name}</span>
                    {t.ok === false && <Chip color="var(--neg)" filled>ERROR</Chip>}
                    {t.latency_ms !== undefined && (
                      <span style={{ color: 'var(--ink-4)' }}>{fmtMs(t.latency_ms)}</span>
                    )}
                  </div>
                  {t.args && (
                    <div style={{ color: 'var(--ink-4)', marginTop: 3, wordBreak: 'break-all' }}>
                      {JSON.stringify(t.args)}
                    </div>
                  )}
                  {t.error && <div style={{ color: 'var(--neg)', marginTop: 3 }}>{t.error}</div>}
                </div>
              ))}
            </div>
          )}

          {step.response_answer && (
            <div style={{ marginBottom: 10 }}>
              <div className="h-label" style={{ fontSize: 9, color: 'var(--ink-3)', marginBottom: 5 }}>RESPONSE</div>
              <pre style={{
                fontFamily: 'var(--ff-mono)', fontSize: 10.5, color: 'var(--ink-2)',
                whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
                maxHeight: 200, overflowY: 'auto',
              }}>{step.response_answer}</pre>
            </div>
          )}

          {step.error_message && (
            <div style={{ marginBottom: 10 }}>
              <div className="h-label" style={{ fontSize: 9, color: 'var(--neg)', marginBottom: 5 }}>ERROR</div>
              <div style={{ fontFamily: 'var(--ff-mono)', fontSize: 10.5, color: 'var(--neg)' }}>
                {step.error_type}: {step.error_message}
              </div>
            </div>
          )}

          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
            gap: 6, fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--ink-4)',
          }}>
            {step.model && <div>model: {step.model}</div>}
            {step.input_tokens !== null && <div>in: {step.input_tokens} tok</div>}
            {step.output_tokens !== null && <div>out: {step.output_tokens} tok</div>}
            {step.estimated_cost_usd ? <div>cost: {fmtUsd(step.estimated_cost_usd)}</div> : null}
            {step.bigquery_latency_ms ? <div>bq: {fmtMs(step.bigquery_latency_ms)}</div> : null}
            {step.parsed_query_type && <div>type: {step.parsed_query_type}</div>}
            {step.parsed_player_name && <div>player: {step.parsed_player_name}</div>}
            {step.user_rating && <div>rating: {step.user_rating}</div>}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main ───────────────────────────────────────────────────
export default function TraceViewer({ getBackendURL, getAuthHeaders }) {
  const [traces, setTraces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);   // trace_id
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [onlyUnlabeled, setOnlyUnlabeled] = useState(false);
  const [onlyFailed, setOnlyFailed] = useState(false);
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const call = useCallback(async (path, options = {}) => {
    const baseURL = getBackendURL ? getBackendURL() : '';
    const headers = getAuthHeaders ? await getAuthHeaders() : {};
    const res = await fetch(`${baseURL}/api/v1${path}`, { ...options, headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }, [getBackendURL, getAuthHeaders]);

  const loadTraces = useCallback(async (force = false) => {
    setLoading(true); setError(null);
    try {
      const qs = new URLSearchParams({
        days: '30', limit: '100',
        only_unlabeled: String(onlyUnlabeled),
        only_failed: String(onlyFailed),
        force: String(force),
      });
      const json = await call(`/traces?${qs}`);
      setTraces(json.traces || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [call, onlyUnlabeled, onlyFailed]);

  useEffect(() => { loadTraces(); }, [loadTraces]);

  const loadDetail = useCallback(async (traceId) => {
    setSelected(traceId); setDetail(null); setDetailLoading(true); setNote('');
    try {
      const json = await call(`/traces/${traceId}`);
      setDetail(json.data);
    } catch (e) {
      setError(e.message);
    } finally {
      setDetailLoading(false);
    }
  }, [call]);

  const applyLabel = useCallback(async (labelId) => {
    if (!selected) return;
    setSaving(true);
    try {
      await call(`/traces/${selected}/label`, {
        method: 'POST',
        headers: {
          ...(getAuthHeaders ? await getAuthHeaders() : {}),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ label: labelId, note: note || null }),
      });
      await loadDetail(selected);
      await loadTraces(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }, [selected, note, call, getAuthHeaders, loadDetail, loadTraces]);

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0,
      background: 'var(--bg-0)', color: 'var(--ink-1)',
    }} data-screen-label="TRACE · AGENT RUNS">

      {/* Header */}
      <div className="rule-b" style={{
        padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
      }}>
        <div className="h-label" style={{ fontSize: 11, letterSpacing: '0.16em', color: 'var(--amber)' }}>
          TRACE VIEWER
        </div>
        <div style={{ fontFamily: 'var(--ff-mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>
          {traces.length} TRACES · LAST 30D
        </div>
        <div style={{ flex: 1 }} />
        <button style={btn(onlyFailed)} onClick={() => setOnlyFailed((v) => !v)}>FAILED ONLY</button>
        <button style={btn(onlyUnlabeled)} onClick={() => setOnlyUnlabeled((v) => !v)}>UNLABELED</button>
        <button style={btn(false, loading)} disabled={loading} onClick={() => loadTraces(true)}>
          {loading ? 'LOADING…' : '↻ REFRESH'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '8px 16px', background: 'oklch(from var(--neg) l c h / 0.12)',
          color: 'var(--neg)', fontFamily: 'var(--ff-mono)', fontSize: 10.5,
        }}>ERROR: {error}</div>
      )}

      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>

        {/* Left: trace list */}
        <div style={{
          width: 340, flexShrink: 0, borderRight: '1px solid var(--rule)',
          overflowY: 'auto', background: 'var(--bg-1)',
        }}>
          {!loading && traces.length === 0 && (
            <div style={{ padding: 16, fontFamily: 'var(--ff-mono)', fontSize: 10.5, color: 'var(--ink-4)', lineHeight: 1.7 }}>
              NO TRACES.<br />
              チャットでエージェントを実行すると<br />ここに表示されます。
            </div>
          )}
          {traces.map((t) => {
            const active = t.trace_id === selected;
            const lbl = t.label ? TRACE_LABEL_MAP[t.label] : null;
            return (
              <div
                key={t.trace_id}
                onClick={() => loadDetail(t.trace_id)}
                style={{
                  padding: '10px 12px', borderBottom: '1px solid var(--rule)', cursor: 'pointer',
                  background: active ? 'var(--bg-3)' : 'transparent',
                  borderLeft: `2px solid ${active ? 'var(--amber)' : 'transparent'}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
                  <span style={{ fontFamily: 'var(--ff-mono)', fontSize: 9.5, color: 'var(--ink-4)' }}>
                    {fmtTime(t.started_at)}
                  </span>
                  <div style={{ flex: 1 }} />
                  {t.failed_steps > 0 && <Chip color="var(--neg)" filled>{t.failed_steps} FAIL</Chip>}
                  {lbl && <Chip color={lbl.color}>{lbl.en}</Chip>}
                </div>
                <div style={{
                  fontSize: 11.5, color: 'var(--ink-1)', lineHeight: 1.45,
                  display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                }}>
                  {t.user_query || '(no query)'}
                </div>
                <div style={{
                  marginTop: 5, display: 'flex', gap: 6, flexWrap: 'wrap',
                  fontFamily: 'var(--ff-mono)', fontSize: 9.5, color: 'var(--ink-4)',
                }}>
                  <span>{t.step_count} STEPS</span>
                  {/* LLM 呼び出し回数は model の有無で数えた値を使う。iteration は
                      経路ごとに意味が違うため横断表示には使えない。
                      複数回の呼び出しは異常ではない（文章化が必須のツールがあるため）ので
                      警告色にはしない。 */}
                  {t.llm_calls > 1 && <span>· {t.llm_calls} LLM CALLS</span>}
                  <span>· {fmtMs(t.llm_latency_ms)}</span>
                  <span>· {fmtUsd(t.cost_usd)}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: detail */}
        <div style={{ flex: 1, minWidth: 0, overflowY: 'auto', padding: 16 }}>
          {!selected && (
            <div style={{ fontFamily: 'var(--ff-mono)', fontSize: 11, color: 'var(--ink-4)' }}>
              ← 左のリストから trace を選択してください
            </div>
          )}
          {detailLoading && (
            <div style={{ fontFamily: 'var(--ff-mono)', fontSize: 11, color: 'var(--ink-4)' }}>LOADING…</div>
          )}

          {detail && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

              {/* Labeling */}
              <Card>
                <CardHead
                  title="FAILURE LABEL"
                  subtitle={detail.current_label
                    ? `現在: ${TRACE_LABEL_MAP[detail.current_label]?.jp ?? detail.current_label}`
                    : '未ラベル'}
                />
                <div style={{ padding: '12px 14px' }}>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                    {TRACE_LABELS.map((l) => (
                      <button
                        key={l.id}
                        disabled={saving}
                        onClick={() => applyLabel(l.id)}
                        style={{
                          padding: '5px 10px', border: `1px solid ${l.color}`,
                          background: detail.current_label === l.id ? l.color : 'transparent',
                          color: detail.current_label === l.id ? 'var(--bg-0)' : l.color,
                          fontFamily: 'var(--ff-mono)', fontSize: 10, fontWeight: 700,
                          letterSpacing: '0.08em', cursor: saving ? 'wait' : 'pointer',
                        }}
                      >{l.jp}</button>
                    ))}
                  </div>
                  <input
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="判断理由（任意）— ラベルを押す前に入力"
                    style={{
                      width: '100%', padding: '6px 8px', background: 'var(--bg-0)',
                      border: '1px solid var(--rule)', color: 'var(--ink-1)',
                      fontFamily: 'var(--ff-mono)', fontSize: 10.5, outline: 'none',
                    }}
                  />
                  {detail.labels?.length > 1 && (
                    <div style={{ marginTop: 8, fontFamily: 'var(--ff-mono)', fontSize: 9.5, color: 'var(--ink-4)' }}>
                      履歴 {detail.labels.length} 件（最新を採用）
                    </div>
                  )}
                </div>
              </Card>

              {/* Steps */}
              <Card>
                <CardHead
                  title="EXECUTION PATH"
                  subtitle={`${detail.steps.length} steps · trace ${detail.trace_id}`}
                />
                <div>
                  {detail.steps.map((s, i) => (
                    <StepRow key={s.log_id ?? i} step={s} index={i} />
                  ))}
                  {detail.steps.length === 0 && (
                    <div style={{ padding: 14, fontFamily: 'var(--ff-mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>
                      NO INSTRUMENTED STEPS — this trace predates trace instrumentation.
                    </div>
                  )}
                </div>
              </Card>

              {/* Request summary — node が NULL の行。エージェントのステップではなく
                  エンドポイントが書くリクエスト全体の 1 行。timestamp はリクエスト受信時に
                  打たれるため、ステップ列に混ぜると最終回答が先頭に来てしまう。 */}
              {detail.summary && (
                <Card>
                  <CardHead
                    title="FINAL RESULT"
                    subtitle={`endpoint row · total ${fmtMs(detail.summary.total_latency_ms)}`}
                    right={detail.summary.user_rating
                      ? <Chip color={detail.summary.user_rating === 'good' ? 'var(--pos)' : 'var(--neg)'} filled>
                          {detail.summary.user_rating.toUpperCase()}
                        </Chip>
                      : null}
                  />
                  <div style={{ padding: '12px 14px' }}>
                    {detail.summary.response_answer ? (
                      <pre style={{
                        fontFamily: 'var(--ff-mono)', fontSize: 10.5, color: 'var(--ink-2)',
                        whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
                        maxHeight: 260, overflowY: 'auto',
                      }}>{detail.summary.response_answer}</pre>
                    ) : (
                      <div style={{ fontFamily: 'var(--ff-mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>
                        (no answer recorded)
                      </div>
                    )}
                    {detail.summary.feedback_category && (
                      <div style={{ marginTop: 8, fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--ink-4)' }}>
                        feedback: {detail.summary.feedback_category}
                        {detail.summary.feedback_reason ? ` — ${detail.summary.feedback_reason}` : ''}
                      </div>
                    )}
                  </div>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
