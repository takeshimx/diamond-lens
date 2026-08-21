"""
docs/knowledge/*.md をチャンク分割し、BQ glossary_chunks → glossary_embeddings へ取り込む。

冪等性:
  source（ファイル名）単位で DELETE してから INSERT する。
  llm_query_embeddings（append-only）とは方針が異なる。
  用語定義は「最新版が正」であり、履歴に価値がないため。

埋め込み対象の方針:
  chunk_text（＝ベクトル化される文字列）には EMBED_FIELDS のみを含める。
  カテゴリ・メトリクス名・検証ステータスは別カラムへ退避する。
  理由:
    (1) 「検証ステータス: MLB.com Glossary で確認済（2026-08-20）」等の定型文は
        全チャンクにほぼ同一文字列で入るため、チャンク間の識別力を下げる。
    (2) `fg_xwoba` のような snake_case は日本語質問と意味空間で接点がなく、
        シグナルを薄めるノイズにしかならない。
    (3) category は別カラムに持てば VECTOR_SEARCH の事前フィルタに使える。

使い方:
  python -m backend.scripts.ingest_glossary --dry-run   # 分割結果だけ表示
  python -m backend.scripts.ingest_glossary             # BQ へ投入
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
CHUNKS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.glossary_chunks"
EMBEDDINGS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.glossary_embeddings"
EMBEDDING_MODEL = f"{PROJECT_ID}.{DATASET_ID}.query_embedding_model"

KNOWLEDGE_DIR = Path("docs/knowledge")
MAX_CHARS = 800  # 1 チャンクの上限。超過分は part 分割する

# ベクトル化する意味フィールド（順序は本文の読み順に合わせる）
EMBED_FIELDS = ("定義", "解釈", "注意")
# ベクトル化せず、別カラムへ退避するメタフィールド
META_FIELD_COLUMNS = {
    "カテゴリ": "category_raw",
    "メトリクス名": "metric_names",
    "検証ステータス": "verified_source",
}

# "- **定義**: 本文" 形式の 1 行を拾う
_FIELD_RE = re.compile(r"^-\s*\*\*(?P<key>[^*]+)\*\*\s*[:：]\s*(?P<value>.*)$")


def _strip_markup(text: str) -> str:
    """埋め込みの邪魔になる装飾記号を落とす。

    "**" や backtick は意味を持たないため、除去して素の日本語に近づける。
    """
    return text.replace("**", "").replace("`", "").strip()


def parse_entry(part: str) -> dict:
    """`## 見出し` 1 つ分のテキストを、意味フィールドとメタフィールドに仕分ける。

    未知のフィールド（将来 "- **例**:" 等を足した場合）は EMBED 側に倒す。
    メタとして扱いたいものは META_FIELD_COLUMNS に明示追加すること。
    """
    lines = part.split("\n")
    section = lines[0].removeprefix("## ").strip()

    embed_parts: list[str] = [_strip_markup(section)]
    meta: dict[str, str] = {}

    for line in lines[1:]:
        m = _FIELD_RE.match(line.strip())
        if not m:
            continue
        key = m.group("key").strip()
        value = _strip_markup(m.group("value"))
        if not value:
            continue

        if key in META_FIELD_COLUMNS:
            meta[META_FIELD_COLUMNS[key]] = value
        else:
            # EMBED_FIELDS に無い未知キーもここに入る（fail-open）
            embed_parts.append(f"{key}: {value}")

    # EMBED_FIELDS の順に並べ替える（見出しは常に先頭）
    head, rest = embed_parts[0], embed_parts[1:]
    rest.sort(key=lambda s: _embed_field_order(s.split(":", 1)[0]))

    return {
        "section": section,
        "chunk_text": "\n".join([head, *rest]),
        **meta,
    }


def _embed_field_order(key: str) -> int:
    """EMBED_FIELDS の並び順。未知キーは末尾へ。"""
    return EMBED_FIELDS.index(key) if key in EMBED_FIELDS else len(EMBED_FIELDS)


def _normalize_category(category_raw: str | None) -> str | None:
    """"batting / statcast" -> "batting"。

    VECTOR_SEARCH の事前フィルタに使うため、先頭の主カテゴリのみを採用する。
    """
    if not category_raw:
        return None
    return category_raw.split("/")[0].strip() or None


def chunk_markdown(md_path: Path, tier: str = "curated") -> list[dict]:
    """`## 見出し` 単位で分割する。

    見出し行を chunk_text の先頭に含めることで、見出し語そのものも
    ベクトルに乗せる（「xwOBA」という語での検索に効く）。
    """
    text = md_path.read_text(encoding="utf-8")
    # 行頭の "## " で区切る。(?=...) は「その位置の直前で切る」先読み表現
    parts = re.split(r"\n(?=## )", text)

    chunks: list[dict] = []
    for part in parts:
        part = part.strip()
        if not part.startswith("## "):
            continue  # ファイル冒頭のコメント・前書きはスキップ

        entry = parse_entry(part)
        section = entry["section"]
        body_full = entry["chunk_text"]
        category = _normalize_category(entry.get("category_raw"))

        # 上限を超える場合のみ part 分割（curated 用語集では通常発生しない）
        bodies = [
            body_full[i:i + MAX_CHARS] for i in range(0, len(body_full), MAX_CHARS)
        ] or [body_full]

        for n, body in enumerate(bodies):
            suffix = "" if len(bodies) == 1 else f"#part{n}"
            chunks.append({
                "chunk_id": f"{md_path.name}#{section}{suffix}",
                "doc_id": md_path.stem,
                "source": md_path.name,
                "section": section,
                "parent_section": None,
                "chunk_text": body,
                "char_len": len(body),
                "tier": tier,
                "category": category,
                "metric_names": entry.get("metric_names"),
                "verified_source": entry.get("verified_source"),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
    return chunks


def delete_by_source(client: bigquery.Client, sources: list[str]) -> None:
    """再取込前に、対象ファイル由来の行を両テーブルから消す。"""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("sources", "STRING", sources)
        ]
    )
    for table in (CHUNKS_TABLE, EMBEDDINGS_TABLE):
        sql = f"DELETE FROM `{table}` WHERE source IN UNNEST(@sources)"
        client.query(sql, job_config=job_config).result()
        print(f"  deleted rows from {table} for {sources}")


def insert_chunks(client: bigquery.Client, chunks: list[dict]) -> None:
    """load_table_from_json でまとめて投入する。

    insert_rows_json（ストリーミング）ではなくロードジョブを使うのは、
    直後の DELETE / UPDATE がストリーミングバッファに阻まれないため。
    """
    job = client.load_table_from_json(
        chunks,
        CHUNKS_TABLE,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()
    print(f"  inserted {len(chunks)} chunks")


def generate_embeddings(client: bigquery.Client, sources: list[str]) -> None:
    """BQ 内で Embedding を生成する。

    Python から Vertex AI を直接叩かないのは、
    (1) 既存 bq_embedding_service.py と同じサーバレス構成に揃えるため
    (2) ローカル環境の HTTPS 傍受による TLS エラーを回避するため

    task_type='RETRIEVAL_DOCUMENT' は文書側の指定。
    検索クエリ側は 'RETRIEVAL_QUERY' を使い、非対称な埋め込みを生成する。
    """
    sql = f"""
    INSERT INTO `{EMBEDDINGS_TABLE}`
      (chunk_id, chunk_text, source, section, tier, category, embedding, ingested_at)
    SELECT
      chunk_id, content AS chunk_text, source, section, tier, category,
      ml_generate_embedding_result AS embedding,
      CURRENT_TIMESTAMP()
    FROM ML.GENERATE_EMBEDDING(
      MODEL `{EMBEDDING_MODEL}`,
      (
        SELECT chunk_id, chunk_text AS content, source, section, tier, category
        FROM `{CHUNKS_TABLE}`
        WHERE source IN UNNEST(@sources)
      ),
      STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_DOCUMENT' AS task_type)
    )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("sources", "STRING", sources)
        ]
    )
    client.query(sql, job_config=job_config).result()
    print("  embeddings generated")


def main() -> None:
    parser = argparse.ArgumentParser(description="Glossary ingestion for RAG")
    parser.add_argument("--dry-run", action="store_true",
                        help="BQ に書かず、分割結果のみ表示する")
    parser.add_argument("--show-text", action="store_true",
                        help="--dry-run 時に chunk_text 本文も表示する")
    parser.add_argument("--pattern", default="glossary_*.md",
                        help="対象ファイルの glob パターン")
    args = parser.parse_args()

    md_files = sorted(KNOWLEDGE_DIR.glob(args.pattern))
    if not md_files:
        print(f"No files matched: {KNOWLEDGE_DIR}/{args.pattern}")
        return

    all_chunks: list[dict] = []
    for md in md_files:
        chunks = chunk_markdown(md)
        print(f"{md.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    if args.dry_run:
        for c in all_chunks:
            print(f"  [{c['char_len']:>4}c] [{c['category']}] {c['chunk_id']}")
            if args.show_text:
                print("  " + "-" * 60)
                for line in c["chunk_text"].split("\n"):
                    print(f"    {line}")
                print("  " + "-" * 60)
        print(f"\nTotal: {len(all_chunks)} chunks (dry-run, nothing written)")
        return

    sources = sorted({c["source"] for c in all_chunks})
    client = bigquery.Client(project=PROJECT_ID)
    delete_by_source(client, sources)
    insert_chunks(client, all_chunks)
    generate_embeddings(client, sources)
    print(f"\nDone. {len(all_chunks)} chunks ingested from {len(sources)} file(s).")


if __name__ == "__main__":
    main()
