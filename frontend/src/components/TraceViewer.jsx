import { useCallback, useEffect, useState } from 'react';
import { TRACE_LABELS, TRACE_LABEL_MAP, nodeColor, nodeMeta } from '../constants/traceLabels.js';

/**
 * Trace Viewer + Failure Labeling (P0-1)
 *
 * llm_interaction_logs を trace_id 単位で束ねたエージェント実行経路を閲覧し、
 * 失敗ラベルと「正解の期待値」を付与する画面。
 * 視覚は UsageDashboard と同じ diamond-lens トークンに統一。
 *
 * 期待値は golden_dataset.json への昇格元になる (HITL フライホイール)。
 * query_type / split_type / metrics の選択肢は必ず GET /traces/expected-options
 * から取得する。ここに定数を置くと tool schema の enum と同期漏れを起こす。
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

const EMPTY_EXPECTATION = {
  query_type: '', split_type: '', metrics: [], player_name: '',
  season: '', order_by: '', expected_no_tool: false, user_query: '',
};

const fieldStyle = {
  width: '100%', padding: '5px 7px', background: 'var(--bg-0)',
  border: '1px solid var(--rule)', color: 'var(--ink-1)',
  fontFamily: 'var(--ff-mono)', fontSize: 10.5, outline: 'none',
};

const Field = ({ label, hint, children }) => (
  <label style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
    <span className="h-label" style={{
      fontSize: 9, letterSpacing: '0.12em', color: 'var(--ink-3)',
    }}>{label}</span>
    {children}
    {hint && (
      <span style={{ fontFamily: 'var(--ff-mono)', fontSize: 9, color: 'var(--ink-4)' }}>
        {hint}
      </span>
    )}
  </label>
);

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
  const [onlyBadRating, setOnlyBadRating] = useState(false);
  const [onlyUnexpected, setOnlyUnexpected] = useState(false);
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  // 期待値入力の選択肢。サーバ (tool schema の enum) が唯一のソース。
  const [options, setOptions] = useState({
    query_types: [], split_types: {}, metrics: [], pr_enabled: false,
  });
  const [exp, setExp] = useState(EMPTY_EXPECTATION);
  const [expSaving, setExpSaving] = useState(false);
  const [expSaved, setExpSaved] = useState(false);
  // 保存済みの期待値は既定で編集不可。golden の元データなので、
  // 開いたついでに書き換わる事故を防ぐ。直すときは明示的に解除させる。
  const [expEditing, setExpEditing] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const [promoteResult, setPromoteResult] = useState(null);

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
        only_bad_rating: String(onlyBadRating),
        only_unexpected: String(onlyUnexpected),
        force: String(force),
      });
      const json = await call(`/traces?${qs}`);
      setTraces(json.traces || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [call, onlyUnlabeled, onlyFailed, onlyBadRating, onlyUnexpected]);

  useEffect(() => { loadTraces(); }, [loadTraces]);

  // 選択肢は画面が生きている間 1 回だけ取れば足りる（enum は再デプロイまで不変）
  useEffect(() => {
    let alive = true;
    call('/traces/expected-options')
      .then((json) => {
        if (!alive) return;
        setOptions({
          query_types: json.query_types || [],
          split_types: json.split_types || {},
          metrics: json.metrics || [],
          pr_enabled: !!json.pr_enabled,
        });
      })
      .catch(() => { /* 期待値入力が使えないだけで trace 閲覧は継続できる */ });
    return () => { alive = false; };
  }, [call]);

  const loadDetail = useCallback(async (traceId) => {
    setSelected(traceId); setDetail(null); setDetailLoading(true); setNote('');
    setExpSaved(false); setExpEditing(false);
    try {
      const json = await call(`/traces/${traceId}`);
      setDetail(json.data);
      // 付与済みなら復元し、未付与なら質問文だけ埋めて残りは空にする。
      // LLM が実際に返した値 (parsed_*) は入れない。間違いをそのまま
      // 正解として承認してしまう事故を防ぐため、正解は必ず人が選ぶ。
      const prev = json.data?.expectation;
      setExp(prev ? {
        query_type: prev.query_type || '',
        split_type: prev.split_type || '',
        metrics: prev.metrics || [],
        player_name: prev.player_name || '',
        season: prev.season ?? '',
        order_by: prev.order_by || '',
        expected_no_tool: !!prev.expected_no_tool,
        user_query: prev.user_query || '',
      } : {
        ...EMPTY_EXPECTATION,
        user_query: json.data?.summary?.user_query
          || json.data?.steps?.find((s) => s.user_query)?.user_query
          || '',
      });
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
      // 再取得しない。trace_labels も Streaming Buffer に入るため直後の
      // SELECT には現れず、付けたラベルが消えたように見える。さらに
      // loadDetail は期待値フォームも初期化するため、入力途中の内容を失う。
      setDetail((d) => (d ? {
        ...d,
        current_label: labelId,
        labels: [{ label: labelId, note: note || null }, ...(d.labels || [])],
      } : d));
      setTraces((list) => list.map(
        (t) => (t.trace_id === selected ? { ...t, label: labelId } : t)
      ));
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }, [selected, note, call, getAuthHeaders]);

  // 通算 (career_*) は年の概念を持たない。UI 上も送信時も season を落とす。
  const isCareer = exp.query_type.startsWith('career_');
  // 付与済みの期待値は golden の元データ。開いたついでに書き換わらないよう
  // 既定でロックし、直すときだけ明示的に解除させる。
  const expLocked = !!detail?.expectation && !expEditing;

  const saveExpectation = useCallback(async () => {
    if (!selected) return;
    setExpSaving(true); setExpSaved(false); setError(null);
    try {
      const json = await call(`/traces/${selected}/expected`, {
        method: 'POST',
        headers: {
          ...(getAuthHeaders ? await getAuthHeaders() : {}),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_query: exp.user_query,
          query_type: exp.query_type,
          split_type: exp.split_type || null,
          metrics: exp.metrics,
          player_name: exp.player_name || null,
          season: (isCareer || exp.season === '') ? null : Number(exp.season),
          order_by: exp.order_by || null,
          expected_no_tool: exp.expected_no_tool,
          request_id: detail?.request_id || null,
          note: note || null,
        }),
      });
      setExpSaved(true);
      setExpEditing(false);
      // ここで trace を再取得してはいけない。BigQuery の Streaming Buffer は
      // insert 直後の SELECT にまだ現れず、「未登録」と判定されてフォームが
      // 初期化される（保存は成功しているのに消えたように見える）。
      // POST が書き込んだ行をそのまま返すので、それで画面を更新する。
      setDetail((d) => (d ? { ...d, expectation: json.data } : d));
      // 一覧の「処理済み」表示も同時に更新する。未処理フィルタ表示中なら
      // その場で行を落とし、待ち行列が減ったことが見て分かるようにする。
      setTraces((list) => (onlyUnexpected
        ? list.filter((t) => t.trace_id !== selected)
        : list.map((t) => (t.trace_id === selected
          ? { ...t, has_expectation: true, expected_query_type: json.data.query_type }
          : t))));
    } catch (e) {
      setError(e.message);
    } finally {
      setExpSaving(false);
    }
  }, [selected, exp, isCareer, note, detail, call, getAuthHeaders, onlyUnexpected]);

  // 人の作業（ラベル付与と期待値入力）はここまで。以降は自動で走る:
  // golden_dataset.json への取り込み → ブランチ作成 → コミット → PR 作成。
  // 直接 main へは書かない。golden は CI の合格ラインそのもので、
  // 変更履歴とレビューを必ず通す必要があるため。
  const promoteToGolden = useCallback(async () => {
    setPromoting(true); setPromoteResult(null); setError(null);
    try {
      const json = await call('/traces/promote?days=90', {
        method: 'POST',
        headers: { ...(getAuthHeaders ? await getAuthHeaders() : {}) },
      });
      setPromoteResult(json);
    } catch (e) {
      setError(e.message);
    } finally {
      setPromoting(false);
    }
  }, [call, getAuthHeaders]);

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
        <button style={btn(onlyBadRating)} onClick={() => setOnlyBadRating((v) => !v)}>👎 ONLY</button>
        <button style={btn(onlyUnexpected)} onClick={() => setOnlyUnexpected((v) => !v)}>未処理のみ</button>
        <button style={btn(onlyFailed)} onClick={() => setOnlyFailed((v) => !v)}>FAILED ONLY</button>
        <button style={btn(onlyUnlabeled)} onClick={() => setOnlyUnlabeled((v) => !v)}>UNLABELED</button>
        <button style={btn(false, loading)} disabled={loading} onClick={() => loadTraces(true)}>
          {loading ? 'LOADING…' : '↻ REFRESH'}
        </button>
        <button
          style={{ ...btn(false, promoting), borderColor: 'var(--amber)', color: 'var(--amber)' }}
          disabled={promoting}
          onClick={promoteToGolden}
          title={options.pr_enabled
            ? '承認済みの期待値を golden に取り込む PR を作成します'
            : 'GITHUB_TOKEN / GITHUB_REPO が未設定です'}
        >{promoting ? 'CREATING PR…' : '承認して PR 作成'}</button>
      </div>

      {promoteResult && (
        <div className="rule-b" style={{
          padding: '8px 16px', fontFamily: 'var(--ff-mono)', fontSize: 10.5,
          color: 'var(--ink-2)', display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
          {promoteResult.created ? (
            <>
              <Chip color="var(--pos)" filled>PR CREATED</Chip>
              <span>{promoteResult.added.length} 件を昇格しました</span>
              <a
                href={promoteResult.pr_url}
                target="_blank"
                rel="noreferrer"
                style={{ color: 'var(--amber)' }}
              >{promoteResult.pr_url}</a>
            </>
          ) : (
            <>
              <Chip color="var(--ink-3)">NO CHANGE</Chip>
              <span>昇格できるものがありませんでした</span>
            </>
          )}
          {Object.keys(promoteResult.held || {}).length > 0 && (
            <span style={{ color: 'var(--amber)' }}>
              保留 {Object.keys(promoteResult.held).length} 件:
              {' '}{Object.values(promoteResult.held)[0]}
            </span>
          )}
          <div style={{ flex: 1 }} />
          <button style={btn()} onClick={() => setPromoteResult(null)}>閉じる</button>
        </div>
      )}

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
                  {t.user_rating === 'bad' && (
                    <Chip color="var(--neg)" filled title={t.feedback_reason || ''}>
                      👎 {(t.feedback_category || '').toUpperCase()}
                    </Chip>
                  )}
                  {t.has_expectation && (
                    <Chip color="var(--pos)" title={'期待値: ' + t.expected_query_type}>
                      ✓ EXPECTED
                    </Chip>
                  )}
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

              {/* Expected answer (HITL) — golden_dataset への昇格元 */}
              <Card>
                <CardHead
                  title="EXPECTED ANSWER"
                  subtitle={detail.expectation
                    ? '付与済み: ' + detail.expectation.query_type
                      + (detail.expectation.split_type ? ' / ' + detail.expectation.split_type : '')
                    : '本来どう解釈されるべきだったかを入力する'}
                  right={detail.feedback?.user_rating === 'bad'
                    ? <Chip color="var(--neg)" filled title={detail.feedback.feedback_reason || ''}>
                        👎 {(detail.feedback.feedback_category || '').toUpperCase()}
                      </Chip>
                    : null}
                />
                <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>

                  <Field label="QUERY（golden に入る質問文）">
                    <input
                      value={exp.user_query}
                      disabled={expLocked}
                      onChange={(e) => setExp((v) => ({ ...v, user_query: e.target.value }))}
                      placeholder="例: 鈴木誠也の2025年の打率は？"
                      style={fieldStyle}
                    />
                  </Field>

                  <label style={{
                    display: 'flex', alignItems: 'center', gap: 7,
                    fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--ink-2)',
                  }}>
                    <input
                      type="checkbox"
                      checked={exp.expected_no_tool}
                      disabled={expLocked}
                      onChange={(e) => setExp((v) => ({ ...v, expected_no_tool: e.target.checked }))}
                    />
                    ツールを呼ばず断るのが正解（データが無い等）
                  </label>

                  {!exp.expected_no_tool && (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                        <Field label="QUERY TYPE">
                          <select
                            value={exp.query_type}
                            disabled={expLocked}
                            onChange={(e) => setExp((v) => ({
                              ...v, query_type: e.target.value, split_type: '',
                            }))}
                            style={fieldStyle}
                          >
                            <option value="">— 選択 —</option>
                            {options.query_types.map((q) => (
                              <option key={q} value={q}>{q}</option>
                            ))}
                          </select>
                        </Field>

                        <Field
                          label="SPLIT TYPE"
                          hint={options.split_types[exp.query_type] ? '' : 'splits 系の query type のみ'}
                        >
                          <select
                            value={exp.split_type}
                            disabled={expLocked || !options.split_types[exp.query_type]}
                            onChange={(e) => setExp((v) => ({ ...v, split_type: e.target.value }))}
                            style={fieldStyle}
                          >
                            <option value="">— なし —</option>
                            {(options.split_types[exp.query_type] || []).map((q) => (
                              <option key={q} value={q}>{q}</option>
                            ))}
                          </select>
                        </Field>
                      </div>

                      <Field
                        label="METRICS"
                        hint={exp.metrics.length + ' 件選択中 — Ctrl または Cmd + クリックで複数選択'}
                      >
                        <select
                          multiple
                          value={exp.metrics}
                          disabled={expLocked}
                          onChange={(e) => setExp((v) => ({
                            ...v,
                            metrics: Array.from(e.target.selectedOptions, (o) => o.value),
                          }))}
                          style={{ ...fieldStyle, height: 110 }}
                        >
                          {options.metrics.map((m) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      </Field>

                      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 0.8fr 1fr', gap: 10 }}>
                        <Field
                          label="PLAYER NAME"
                          hint="英語フルネーム。空欄だと選手名は採点対象から外れる"
                        >
                          <input
                            value={exp.player_name}
                            disabled={expLocked}
                            onChange={(e) => setExp((v) => ({ ...v, player_name: e.target.value }))}
                            placeholder="例: Clayton Kershaw"
                            style={fieldStyle}
                          />
                        </Field>
                        {/* 通算成績に年は存在しない。career_* を選んだ時点で入力させない。
                            年を入れると「その年を指定するのが正解」という誤った期待値になる。 */}
                        <Field
                          label="SEASON"
                          hint={isCareer ? '通算は年を持たない' : ''}
                        >
                          <input
                            type="number"
                            value={isCareer ? '' : exp.season}
                            disabled={expLocked || isCareer}
                            onChange={(e) => setExp((v) => ({ ...v, season: e.target.value }))}
                            placeholder={isCareer ? '—' : '例: 2025'}
                            style={fieldStyle}
                          />
                        </Field>
                        <Field label="ORDER BY" hint="ランキング系のみ">
                          <select
                            value={exp.order_by}
                            disabled={expLocked}
                            onChange={(e) => setExp((v) => ({ ...v, order_by: e.target.value }))}
                            style={fieldStyle}
                          >
                            <option value="">— なし —</option>
                            {options.metrics.map((m) => (
                              <option key={m} value={m}>{m}</option>
                            ))}
                          </select>
                        </Field>
                      </div>
                    </>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {expLocked ? (
                      <>
                        <Chip color="var(--pos)">✓ 付与済み</Chip>
                        <span style={{ fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--ink-4)' }}>
                          この trace は処理済みです。approve_to_golden.py で golden に昇格します
                        </span>
                        <div style={{ flex: 1 }} />
                        <button onClick={() => setExpEditing(true)} style={btn()}>修正する</button>
                      </>
                    ) : (
                      <>
                        <button
                          disabled={expSaving || !exp.user_query || (!exp.expected_no_tool && !exp.query_type)}
                          onClick={saveExpectation}
                          style={{
                            ...btn(false, expSaving || !exp.user_query || (!exp.expected_no_tool && !exp.query_type)),
                            borderColor: 'var(--amber)', color: 'var(--amber)',
                          }}
                        >{expSaving ? 'SAVING…' : '期待値を保存'}</button>
                        {detail.expectation && (
                          <button onClick={() => setExpEditing(false)} style={btn()}>キャンセル</button>
                        )}
                        {expSaved && (
                          <span style={{ fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--pos)' }}>
                            保存しました
                          </span>
                        )}
                      </>
                    )}
                  </div>

                  <div style={{
                    fontFamily: 'var(--ff-mono)', fontSize: 9, color: 'var(--ink-4)', lineHeight: 1.6,
                  }}>
                    保存してもプロダクトの振る舞いは変わりません。ここで作るのはテストケースです。
                    昇格後、まだ壊れていれば CI の精度ゲートが落ちます（それが修正待ちの合図です）。
                  </div>
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
