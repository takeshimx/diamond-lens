# ADR-052: 事前学習済みモデルを中心に構築し、ファインチューニングは行わない

- Status: Accepted
- Date: 2026-05-25（AI Engineering レビューで論点として明示。本 ADR で方針を明文化）
- Deciders: プロジェクトオーナー

## Context（背景・課題）

LLM アプリで回答品質を上げる手段は大きく 2 系統あります。

1. **モデルそのものを学習させる**: ファインチューニング（SFT / LoRA 等）で、自分のデータにモデルを適合させる。
2. **事前学習済みモデルをそのまま使い、周辺を作り込む**: プロンプトエンジニアリング、構造化ツール、RAG、メトリクスの単一真実源、context caching 等で、モデルの外側で品質と効率を担保する。

Diamond Lens は素材（ログ・golden データセット等）が揃っており、ファインチューニングは技術的には可能です。実際 AI Engineering レビューでも「**Fine-tuning：未実施（素材は揃っている）／P3／中期課題**」と論点化されています（[diamond-lens-review-05252026.md:91](../plan_docs/diamond-lens-review-05252026.md#L91)）。

しかし対象 JD（GenAI Forward Deployed Engineer, Google Cloud）は **pretrained foundation model を中心に構築する**役割であり、prompt engineering / RAG / 外部ツールのオーケストレーションを主眼とします。プロジェクトの主目的も新概念の習得とポートフォリオであり（[project memory] 学習サンドボックス兼公開候補）、ここで「あえてファインチューニングしない」判断を明確にしておく価値があります。

## Decision（決定）

**事前学習済みモデル（Gemini 2.5 Flash）をそのまま使い、ファインチューニングは行わない**ことを方針として明文化します。回答品質と効率は、モデルの**外側**の以下で担保します。

- **プロンプトエンジニアリング + 版管理**: 外部 txt + `prompt_registry` でプロンプトを資産化（[[014-prompt-as-config]]）。
- **構造化ツール + Semantic Layer**: メトリクス定義を dbt に一本化（SSOT）し、ツールは検証済みデータを返す（[[009-dbt-semantic-layer-over-text-to-sql]] / [[050-tools-return-raw-data-orchestrator-composes]]）。
- **context caching**: 固定プレフィックスをキャッシュして課金を抑える（[[015-gemini-context-caching]]）。
- **評価パイプライン**: LLM-as-a-Judge / shadow eval / golden dataset で品質を継続計測。

ファインチューニングは「やらない」のではなく、**中期課題として保留**し（レビュー P3）、上記の手段で要件を満たせる限り着手しない、という意思決定です。

## Alternatives Considered（検討した代替案）

- **SFT / LoRA でファインチューニングする**: 自分のデータに適合させれば回答精度が上がる可能性はある。しかし、学習データ整備・再学習パイプライン・モデル管理の運用コストが大きく、JD の主眼（pretrained 中心）からも外れる。プロンプト + Semantic Layer + caching で現状の要件を満たせるため、現時点では不採用（中期課題として保留）。
- **何もせず素のモデルに丸投げ**: ハルシネーションやメトリクス定義のズレが解決しない。本 ADR の「外側を作り込む」方針はこれを否定する（pretrained を使うが周辺は作り込む）。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 学習パイプライン・モデル再学習・バージョン管理の運用コストを負わない。
- モデル差し替え（将来 Gemini の新版や別モデルへ）が容易。特定の学習済み重みにロックインされない。
- 「なぜ FT しないのか」を trade-off で説明できる、意識的な技術選定として残る。

**悪くなったこと / 新たな負荷**

- ドメイン特化の細かなニュアンス（野球特有の言い回し等）は、プロンプトと RAG の作り込みで埋める必要があり、限界があり得る。
- 「素材は揃っているのに使っていない」状態が続く。FT で得られたかもしれない精度向上の機会費用は残る（中期課題として明示）。

## JD Alignment（この募集要件との対応）

- **FM★（prompt engineering / RAG / fine-tuning / pretrained model 中心）**: JD が列挙する手段のうち、**fine-tuning を「あえて選ばない」判断**と、その代わりに prompt / RAG / ツールで構築する方針を、trade-off で語れる。pretrained foundation model を中心に据える JD の役割定義と直接一致する。

## References

- レビュー: [diamond-lens-review-05252026.md](../plan_docs/diamond-lens-review-05252026.md)（#25 Fine-tuning 未実施・P3・中期課題）
- 関連 ADR: [[009-dbt-semantic-layer-over-text-to-sql]], [[014-prompt-as-config]], [[015-gemini-context-caching]], [[050-tools-return-raw-data-orchestrator-composes]]
- 補足: 本 ADR は個別コードではなくプロジェクト全体方針の明文化であり、特定ファイルに 1:1 で対応しない（「決定を記録に残す」性格の ADR）。
