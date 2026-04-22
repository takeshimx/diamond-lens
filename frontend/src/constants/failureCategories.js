// LLM Judge の failure_category を日本語ラベルに変換するマップ
export const FAILURE_CATEGORY_LABELS = {
  unregistered_metric_key: '指標名の認識ミス',
  entity_resolution_error: '選手名の変換ミス',
  missing_context: '年度・条件の不足',
  schema_violation: 'スキーマ違反',
  over_extraction: '過剰なパラメータ抽出',
  type_misclassification: 'クエリ分類ミス',
};
