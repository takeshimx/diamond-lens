"""
用語集 RAG の検索精度を測る評価ハーネス。

測るのは「検索が正解チャンクを引けたか」だけ。回答の良し悪しは対象外。
誤発火（呼ぶべきでない質問でツールが呼ばれる）はツール選択の問題であり、
ChatOrchestrator を動かす必要があるため本スクリプトの対象外とする。

指標:
  命中率 hit@k     上位 k 件に正解が 1 件でも入った質問の割合
                   （RAG 文献で Recall@k と呼ばれるもの）
  網羅率 recall@k  正解集合のうち上位 k 件に入った割合（ML の定義通り）
  MRR              正解の最上位順位の逆数の平均。順位の改善を検出する

コスト:
  --validate    課金なし（BQ に接続しない）
  --warm-cache  質問 1 件につき埋め込み API 1 コール。未登録のものだけ生成する
  評価実行      課金なし（キャッシュ済み埋め込みを再利用）

使い方:
  python -m backend.scripts.run_retrieval_eval --validate
  python -m backend.scripts.run_retrieval_eval --warm-cache
  python -m backend.scripts.run_retrieval_eval
  python -m backend.scripts.run_retrieval_eval --no-category-filter
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
EMBEDDINGS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.glossary_embeddings"
EMBEDDING_MODEL = f"{PROJECT_ID}.{DATASET_ID}.query_embedding_model"
CACHE_TABLE = f"{PROJECT_ID}.{DATASET_ID}.retrieval_eval_query_embeddings"

FIXTURES_PATH = Path("backend/tests/golden/retrieval_fixtures.json")
REPORT_DIR = Path("docs/reports")

# 評価対象外の型（検索ではなくツール選択の問題のため）
EXCLUDED_TYPES = {"should_not_fire"}
K_VALUES = (3, 5)


# ---------------------------------------------------------------- fixtures


def load_fixtures() -> list[dict]:
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return data["fixtures"]


def validate_fixtures(fixtures: list[dict]) -> int:
    """relevant_chunk_ids が実在するチャンクと一致するかを検査する。

    BQ には接続せず、Markdown を解析して照合する（課金なし）。
    存在しない chunk_id を書いてしまう事故を機械的に防ぐ。
    """
    from backend.scripts.ingest_glossary import KNOWLEDGE_DIR, chunk_markdown

    real: set[str] = set()
    for md in sorted(KNOWLEDGE_DIR.glob("glossary_*.md")):
        for c in chunk_markdown(md):
            real.add(c["chunk_id"])

    # Tier 2（公式ルール PDF）。PDF は Git 管理外のため、無い環境では検証をスキップする
    try:
        from backend.scripts.ingest_rules import (
            PDF_PATH,
            build_chunks,
            extract_text,
        )
        if PDF_PATH.exists():
            for c in build_chunks(extract_text(PDF_PATH)):
                real.add(c["chunk_id"])
        else:
            print(f"NOTE: {PDF_PATH} が無いため rules の chunk_id は検証されません")
    except ImportError as e:
        print(f"NOTE: rules の検証をスキップします ({e})")

    bad = [
        (f["id"], cid)
        for f in fixtures
        for cid in f["relevant_chunk_ids"]
        if cid not in real
    ]
    print(f"chunks in knowledge base : {len(real)}")
    print(f"fixtures                 : {len(fixtures)}")
    print(f"invalid chunk_ids        : {len(bad)}")
    for fid, cid in bad:
        print(f"    {fid} -> {cid}")
    return len(bad)


# ---------------------------------------------------------------- cache


def ensure_cache_table(client: bigquery.Client) -> None:
    """キャッシュテーブルを作成する（存在すれば何もしない）。"""
    client.query(f"""
        CREATE TABLE IF NOT EXISTS `{CACHE_TABLE}` (
          query_text  STRING NOT NULL,
          embedding   ARRAY<FLOAT64>,
          created_at  TIMESTAMP
        )
    """).result()


def warm_cache(client: bigquery.Client, queries: list[str]) -> int:
    """未登録の質問だけ埋め込みを生成してキャッシュに入れる。

    ここが本スクリプト唯一の課金ポイント。
    本番と同じモデル・同じ task_type='RETRIEVAL_QUERY' を使う。
    乖離すると評価の意味がなくなるため変更しないこと。
    """
    ensure_cache_table(client)

    rows = client.query(
        f"SELECT query_text FROM `{CACHE_TABLE}`"
    ).result()
    cached = {r.query_text for r in rows}
    missing = [q for q in queries if q not in cached]

    print(f"cached  : {len(cached)}")
    print(f"missing : {len(missing)}")
    if not missing:
        print("nothing to generate. no API call made.")
        return 0

    print(f"-> generating {len(missing)} embeddings (billable)")
    sql = f"""
    INSERT INTO `{CACHE_TABLE}` (query_text, embedding, created_at)
    SELECT content AS query_text,
           ml_generate_embedding_result AS embedding,
           CURRENT_TIMESTAMP()
    FROM ML.GENERATE_EMBEDDING(
      MODEL `{EMBEDDING_MODEL}`,
      (SELECT q AS content FROM UNNEST(@queries) AS q),
      STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_QUERY' AS task_type)
    )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("queries", "STRING", missing)
        ]
    )
    client.query(sql, job_config=job_config).result()
    print(f"done. {len(missing)} embeddings cached.")
    return len(missing)


# ---------------------------------------------------------------- ranking


def fetch_rankings(
    client: bigquery.Client,
    fixtures: list[dict],
    use_category_filter: bool,
) -> dict[str, list[str]]:
    """各質問について、全チャンクを距離の昇順に並べた chunk_id のリストを返す。

    閾値は適用しない。順位が分からないと MRR が計算できないため。
    本番と同じ埋め込み・同じテーブル・同じ距離計算 (COSINE) を使う。
    """
    queries = [f["query"] for f in fixtures]
    # BigQuery の ARRAY は NULL 要素を持てないため、フィルタなしは空文字で表す
    categories = [
        (f.get("category_hint") or "") if use_category_filter else ""
        for f in fixtures
    ]

    sql = f"""
    WITH hints AS (
      SELECT qt AS query_text, ct AS category_hint
      FROM UNNEST(@queries) AS qt WITH OFFSET o1
      JOIN UNNEST(@categories) AS ct WITH OFFSET o2 ON o1 = o2
    ),
    q AS (
      SELECT h.query_text, h.category_hint, c.embedding AS qv
      FROM hints h
      JOIN `{CACHE_TABLE}` c ON c.query_text = h.query_text
    )
    SELECT
      q.query_text,
      e.chunk_id,
      e.section,
      e.chunk_text,
      ML.DISTANCE(e.embedding, q.qv, 'COSINE') AS distance
    FROM `{EMBEDDINGS_TABLE}` e
    CROSS JOIN q
    WHERE q.category_hint = '' OR e.category = q.category_hint
    ORDER BY q.query_text, distance ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("queries", "STRING", queries),
            bigquery.ArrayQueryParameter("categories", "STRING", categories),
        ]
    )
    rankings: dict[str, list[dict]] = {}
    for row in client.query(sql, job_config=job_config).result():
        rankings.setdefault(row.query_text, []).append({
            "chunk_id": row.chunk_id,
            "section": row.section,
            "chunk_text": row.chunk_text,
            "distance": float(row.distance),
        })
    return rankings


def apply_rerank(
    query: str,
    ranked: list[dict],
    candidates: int,
    threshold: float,
    top_k: int,
) -> list[dict]:
    """本番と同じ手順で並べ直す（候補を広めに取る → 閾値で絞る → LLM）。

    並べ直しで選ばれなかったチャンクは、元の距離順のまま後ろに繋ぐ。
    そうしないと MRR が「圏外=0」に潰れ、リランク前後の比較ができなくなる。
    """
    from backend.app.services.rerank_service import rerank_hits

    head = [c for c in ranked[:candidates] if c["distance"] <= threshold]
    if not head:
        return ranked

    picked = rerank_hits(query, head, top_k=top_k)
    picked_ids = {c["chunk_id"] for c in picked}
    rest = [c for c in ranked if c["chunk_id"] not in picked_ids]
    return picked + rest


# ---------------------------------------------------------------- metrics


def score_one(ranked: list[str], relevant: list[str]) -> dict[str, float]:
    """1 問分の指標を計算する。"""
    rel = set(relevant)
    scores: dict[str, float] = {}

    for k in K_VALUES:
        top_k = ranked[:k]
        found = rel & set(top_k)
        scores[f"hit@{k}"] = 1.0 if found else 0.0
        scores[f"recall@{k}"] = len(found) / len(rel) if rel else 0.0

    # MRR: 最も上位に来た正解の順位の逆数
    best = next((i + 1 for i, cid in enumerate(ranked) if cid in rel), None)
    scores["mrr"] = 1.0 / best if best else 0.0
    scores["_best_rank"] = float(best) if best else 0.0
    return scores


def sweep_thresholds(
    rows: list[dict],
    thresholds: list[float],
    k: int = 5,
) -> list[dict]:
    """閾値を振って「正解を落とす率」と「通過するノイズ件数」を測る。

    閾値は順位ではなく距離の絶対値で足切りするため、順位指標だけでは決められない。
    正解保持率が下がる直前が実用的な上限になる。
    """
    out = []
    for t in thresholds:
        kept_correct = 0
        noise_total = 0
        empty_answers = 0
        for r in rows:
            top = r["ranked"][:k]
            passed = [c for c in top if c["distance"] <= t]
            rel = set(r["relevant"])
            if any(c["chunk_id"] in rel for c in passed):
                kept_correct += 1
            noise_total += sum(1 for c in passed if c["chunk_id"] not in rel)
            if not passed:
                empty_answers += 1
        n = len(rows) or 1
        out.append({
            "threshold": t,
            "correct_kept": kept_correct / n,
            "noise_per_query": noise_total / n,
            "empty_rate": empty_answers / n,
        })
    return out


def distance_stats(rows: list[dict]) -> dict[str, float]:
    """正解チャンクの距離と、最上位の不正解チャンクの距離を集計する。"""
    correct, wrong_top = [], []
    for r in rows:
        rel = set(r["relevant"])
        best = next(
            (c["distance"] for c in r["ranked"] if c["chunk_id"] in rel), None
        )
        if best is not None:
            correct.append(best)
        first_wrong = next(
            (c["distance"] for c in r["ranked"] if c["chunk_id"] not in rel), None
        )
        if first_wrong is not None:
            wrong_top.append(first_wrong)

    def pct(vals: list[float], p: float) -> float:
        if not vals:
            return 0.0
        s = sorted(vals)
        return s[min(int(len(s) * p), len(s) - 1)]

    return {
        "correct_min": min(correct) if correct else 0.0,
        "correct_p50": pct(correct, 0.5),
        "correct_p90": pct(correct, 0.9),
        "correct_max": max(correct) if correct else 0.0,
        "wrong_top_min": min(wrong_top) if wrong_top else 0.0,
        "wrong_top_p50": pct(wrong_top, 0.5),
    }


def aggregate(rows: list[dict]) -> dict[str, float]:
    if not rows:
        return {}
    keys = [f"hit@{k}" for k in K_VALUES] + [f"recall@{k}" for k in K_VALUES] + ["mrr"]
    return {k: sum(r["scores"][k] for r in rows) / len(rows) for k in keys}


# ---------------------------------------------------------------- report


def render(rows: list[dict], header: str) -> str:
    lines = [header, ""]
    lines.append("| type | n | 命中@3 | 命中@5 | 網羅@3 | 網羅@5 | MRR |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    by_type: dict[str, list[dict]] = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r)

    for t in sorted(by_type):
        a = aggregate(by_type[t])
        lines.append(
            f"| {t} | {len(by_type[t])} | {a['hit@3']:.3f} | {a['hit@5']:.3f} | "
            f"{a['recall@3']:.3f} | {a['recall@5']:.3f} | {a['mrr']:.3f} |"
        )
    a = aggregate(rows)
    lines.append(
        f"| **ALL** | **{len(rows)}** | **{a['hit@3']:.3f}** | **{a['hit@5']:.3f}** | "
        f"**{a['recall@3']:.3f}** | **{a['recall@5']:.3f}** | **{a['mrr']:.3f}** |"
    )

    st = distance_stats(rows)
    lines += [
        "",
        "### 距離の分布",
        "",
        "| 対象 | min | p50 | p90 | max |",
        "|---|---:|---:|---:|---:|",
        f"| 正解チャンク | {st['correct_min']:.4f} | {st['correct_p50']:.4f} | "
        f"{st['correct_p90']:.4f} | {st['correct_max']:.4f} |",
        f"| 最上位の不正解 | {st['wrong_top_min']:.4f} | {st['wrong_top_p50']:.4f} | - | - |",
        "",
        "### 閾値スイープ（top_k=5）",
        "",
        "| 閾値 | 正解保持率 | ノイズ件数/問 | 空回答率 |",
        "|---:|---:|---:|---:|",
    ]
    for s in sweep_thresholds(rows, [0.20, 0.225, 0.25, 0.275, 0.30, 0.325, 0.35, 0.40]):
        lines.append(
            f"| {s['threshold']:.3f} | {s['correct_kept']:.3f} | "
            f"{s['noise_per_query']:.2f} | {s['empty_rate']:.3f} |"
        )

    failed = [r for r in rows if r["scores"]["hit@5"] == 0.0]
    if failed:
        lines += ["", "### 上位 5 件で正解を拾えなかった質問", ""]
        for r in failed:
            rank = int(r["scores"]["_best_rank"]) or None
            pos = f"{rank} 位" if rank else "圏外"
            lines.append(f"- `{r['id']}` （正解 {pos}） {r['query']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description="Glossary retrieval evaluation")
    parser.add_argument("--validate", action="store_true",
                        help="正解 chunk_id の実在確認のみ（課金なし）")
    parser.add_argument("--warm-cache", action="store_true",
                        help="未登録の質問の埋め込みを生成する（課金あり）")
    parser.add_argument("--no-category-filter", action="store_true",
                        help="category_hint による事前フィルタを無効化して比較する")
    parser.add_argument("--rerank", action="store_true",
                        help="LLM で並べ直してから評価する（Gemini を質問数だけ呼ぶ）")
    parser.add_argument("--report", type=str, default=None,
                        help="Markdown レポートの出力先。省略時は docs/reports/ に自動命名")
    args = parser.parse_args()

    fixtures = load_fixtures()

    if args.validate:
        raise SystemExit(1 if validate_fixtures(fixtures) else 0)

    targets = [f for f in fixtures if f["type"] not in EXCLUDED_TYPES]
    client = bigquery.Client(project=PROJECT_ID)

    if args.warm_cache:
        warm_cache(client, [f["query"] for f in targets])
        return

    use_filter = not args.no_category_filter
    rankings = fetch_rankings(client, targets, use_filter)

    if args.rerank:
        from backend.app.services.glossary_rag_service import (
            DEFAULT_DISTANCE_THRESHOLD,
            DEFAULT_RERANK_CANDIDATES,
            DEFAULT_TOP_K,
        )
        print(f"reranking {len(targets)} queries (billable: Gemini x{len(targets)})")
        for f in targets:
            q = f["query"]
            if q in rankings:
                rankings[q] = apply_rerank(
                    q,
                    rankings[q],
                    candidates=DEFAULT_RERANK_CANDIDATES,
                    threshold=DEFAULT_DISTANCE_THRESHOLD,
                    top_k=DEFAULT_TOP_K,
                )

    missing = [f["id"] for f in targets if f["query"] not in rankings]
    if missing:
        print("埋め込み未生成の質問があります。--warm-cache を先に実行してください:")
        for m in missing:
            print(f"    {m}")
        raise SystemExit(1)

    rows = [
        {
            "id": f["id"],
            "type": f["type"],
            "query": f["query"],
            "relevant": f["relevant_chunk_ids"],
            "ranked": rankings[f["query"]],
            "scores": score_one(
                [c["chunk_id"] for c in rankings[f["query"]]],
                f["relevant_chunk_ids"],
            ),
        }
        for f in targets
    ]

    # Windows コンソールは cp932 のため、em dash 等の非対応文字は使わない
    header = (
        f"# Retrieval Eval - {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n\n"
        f"- category filter: `{'ON' if use_filter else 'OFF'}`\n"
        f"- rerank: `{'ON' if args.rerank else 'OFF'}`\n"
        f"- 対象: {len(rows)} 問（`should_not_fire` は検索評価の対象外）\n"
    )
    body = render(rows, header)
    print(body)

    out = Path(args.report) if args.report else (
        REPORT_DIR / f"retrieval_eval_{datetime.now(timezone.utc):%Y%m%d_%H%M}.md"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body + "\n", encoding="utf-8")
    print(f"\nreport written: {out}")


if __name__ == "__main__":
    main()
