// Trace Viewer の失敗ラベル軸 (P0-1)
// バックエンドの backend/app/services/trace_label_service.py VALID_LABELS と対。
// 追加・変更するときは必ず両方を更新すること。
export const TRACE_LABELS = [
  { id: 'correct',                 jp: '正しい',           en: 'CORRECT',      color: 'var(--pos)'      },
  { id: 'wrong_tool',              jp: 'ツール選択ミス',    en: 'WRONG TOOL',   color: 'var(--neg)'      },
  { id: 'wrong_params',            jp: '引数ミス',          en: 'WRONG PARAMS', color: 'var(--amber)'    },
  { id: 'right_answer_wrong_path', jp: '結果◯ 経路×',      en: 'RIGHT/WRONG',  color: 'var(--purp)'     },
  { id: 'should_have_abstained',   jp: '答えるべきでない',  en: 'OVER-ANSWER',  color: 'var(--info)'     },
  { id: 'retrieval_miss',          jp: '検索ミス',          en: 'RETRIEVAL',    color: 'var(--amber-hi)' },
  { id: 'tool_error',              jp: 'ツール実行エラー',  en: 'TOOL ERROR',   color: 'var(--neg)'      },
];

export const TRACE_LABEL_MAP = Object.fromEntries(
  TRACE_LABELS.map((l) => [l.id, l])
);

// ノード名 → 表示定義。ChatOrchestrator / StrategyAgent の両方をカバーする。
// jp は「そのノードが何をしたか」を1行で説明する。略語のまま出さない。
export const NODE_META = {
  oracle:            { jp: 'ツール選択',      desc: 'どのツールを使うか決める',   color: 'var(--info)'      },
  executor:          { jp: 'ツール実行',      desc: '選ばれたツールを実行',       color: 'var(--purp)'      },
  // ChatOrchestrator では oracle と同じ LLM 呼び出し箇所が、応答内容によって
  // ツール選択 (oracle) と文章化 (synthesizer) を使い分ける。
  synthesizer:       { jp: '文章化',          desc: 'ツール結果を回答文にまとめる', color: 'var(--pos)'     },
  planner:           { jp: '計画',            desc: '必要なツールを洗い出す',     color: 'var(--info)'      },
  parallel_executor: { jp: 'ツール並列実行',  desc: '複数ツールを同時に実行',     color: 'var(--purp)'      },
  aggregator:        { jp: '結果検証',        desc: '取得結果の妥当性を確認',     color: 'var(--amber-dim)' },
  reflection:        { jp: '再計画',          desc: '失敗を分析してやり直す',     color: 'var(--amber)'     },
  strategist:        { jp: 'レポート生成',    desc: '最終的な回答を作る',         color: 'var(--pos)'       },
};
const FALLBACK_NODE = { jp: '不明なステップ', desc: '計装対象外の処理', color: 'var(--ink-3)' };

export const nodeMeta  = (n) => NODE_META[n] ?? FALLBACK_NODE;
export const nodeColor = (n) => nodeMeta(n).color;
