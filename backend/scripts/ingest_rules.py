"""
MLB 公式ルール PDF を BQ glossary_chunks / glossary_embeddings へ取り込む。

用語集 (ingest_glossary.py) とは分割ロジックが根本的に異なるため、別スクリプトにする。
BQ への投入処理は ingest_glossary.py の関数を再利用する。

依存:
  pypdf（取り込み専用。Cloud Run のイメージには含めない）

冪等性:
  source 単位の DELETE -> INSERT（用語集と同じ方針）

使い方:
  python -m backend.scripts.ingest_rules --dry-run          # 件数と本文を確認
  python -m backend.scripts.ingest_rules --dry-run --show 5 # 本文を 5 件表示
  python -m backend.scripts.ingest_rules                    # BQ へ投入（課金あり）
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery

from backend.scripts.ingest_glossary import (
    PROJECT_ID,
    delete_by_source,
    generate_embeddings,
    insert_chunks,
)

PDF_PATH = Path("backend/app/data/knowledge_base/official_baseball_rules_2026.pdf")
SOURCE_NAME = "official_baseball_rules_2026.pdf"
CATEGORY = "rules"
TIER = "official_rules"

MAX_CHARS = 800
OVERLAP_CHARS = 100
# 目次・前付けを捨てる。本文が始まる手前までは章番号だけが並ぶため短い塊になる
# 前付けは BODY_START_RE で切り落とすため、ここは小さくてよい。
# 大きくすると "1.02 The offensive team's objective is..." のような
# 短い正規のルールまで失われる。
MIN_CHARS = 40

# 行頭のルール番号 "1.01" "5.09" 等
# 区切りは [^A-Za-z] に限定する。".{0,3}" だと見出し語の先頭文字まで食べてしまう
# （"1.00—OBJECTIVES" が "JECTIVES" になる事故があった）
# 見出し語にはカンマも入る（"6.00-INTERFERENCE, OBSTRUCTION, AND ..."）。
# 文字クラスから漏らすと、その章のルールが直前の章に吸収されるため要注意。
SECTION_RE = re.compile(
    r"^\s*(\d{1,2}\.00)[^A-Za-z]{0,3}([A-Z][A-Z ,\-'’]{4,})\s*$", re.M
)
RULE_RE = re.compile(r"^\s*(\d{1,2}\.(?!00)\d{2})[\s\u3000]", re.M)
# Definitions of Terms の各定義。"An INFIELD FLY is ..." "The HOME TEAM is ..."
DEF_RE = re.compile(
    r"^(?:(?:A|An|The)\s+)?"
    r"([A-Z][A-Z’'\- ]{2,}?(?:\s*\([^)]{1,40}\))?)"
    r"\s+(?:is|are|shall)\b",
    re.M,
)
# 小項目の下の番号項目 "(1)" "(2)"。(a)(b) で割っても長い条文を更に割る
NUM_RE = re.compile(r"^\s*(\(\d{1,2}\))\s", re.M)
# 小項目 "(a)" "(b)" 等。長いルールを更に割るときに使う
SUB_RE = re.compile(r"^\s*(\([a-z]\))[\s\u3000]", re.M)


# 目次行。"5.04 Batting ......... 21" のようにドットリーダーを含む。
# 本文中にドットが 5 個以上連続することはないため、行ごと落とす。
DOT_LEADER_RE = re.compile(r"^.*\.{5,}.*$", re.M)
# 本文の開始位置。ここより前は目次・前付け（ローマ数字ページ）。
# 実データを確認したところ、この文字列は文書中に 1 度しか出現しない。
BODY_START_RE = re.compile(r"1\.00.{0,3}OBJECTIVES OF THE GAME")
# 各ページ上部の柱（ランニングヘッダ）。"Rule 1.01 to 1.06" の形。
RUNNING_HEAD_RE = re.compile(
    r"^\s*Rule \d{1,2}\.\d{2}(?:\s*(?:to|-)\s*\d{1,2}\.\d{2})?\s*$", re.M
)


def safe_print(s: str) -> None:
    """Windows コンソール (cp932) が扱えない文字を置換して表示する。

    ルール本文には em dash 等が含まれるため、そのまま print すると
    UnicodeEncodeError で落ちる。BQ に入るデータは元のまま。
    """
    enc = sys.stdout.encoding or "utf-8"
    print(s.encode(enc, errors="replace").decode(enc))


def extract_text(pdf_path: Path) -> str:
    """PDF 全ページのテキストを 1 本に連結する。"""
    from pypdf import PdfReader


    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        # ページ番号だけの行・過剰な空白を落とす
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        pages.append(text)

    text = "\n".join(pages)
    # 目次を丸ごと落とす
    text = DOT_LEADER_RE.sub("", text)
    # ドット行を消しても見出し語の断片が残るため、本文の開始位置で切り落とす
    m = BODY_START_RE.search(text)
    if m:
        text = text[m.start():]
    else:
        print("WARNING: 本文の開始位置を検出できませんでした。前付けが混入します。")
    # 各ページの柱を落とす（全ページに入るためベクトルを汚す）
    text = RUNNING_HEAD_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def find_sections(text: str) -> list[tuple[int, str]]:
    """章見出し "1.00-OBJECTIVES OF THE GAME" の (位置, 見出し) 一覧。"""
    return [
        (m.start(), f"{m.group(1)} {m.group(2).strip()}")
        for m in SECTION_RE.finditer(text)
    ]


def section_at(sections: list[tuple[int, str]], pos: int) -> str:
    """pos の直前にある章見出しを返す。無ければ空文字。"""
    title = ""
    for start, name in sections:
        if start > pos:
            break
        title = name
    return title


def split_by_rule(text: str) -> list[tuple[str, str, int]]:
    """ルール番号ごとに (rule_no, 本文, 出現位置) へ分割する。

    出現位置は、そのルールが属する章見出しを引くために使う。
    """
    matches = list(RULE_RE.finditer(text))
    blocks: list[tuple[str, str, int]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) >= MIN_CHARS:
            blocks.append((m.group(1), body, start))
    return blocks


def split_on_sentences(body: str) -> list[str]:
    """構造が無いブロックを文境界で割る。

    文字数で機械的に切ると単語の途中で切れ、断片が意味を失う。
    ピリオド・セミコロンの直後で区切り、直前チャンクの末尾を
    OVERLAP_CHARS だけ持ち越して文脈を繋ぐ。
    """
    sentences = re.split(r"(?<=[.;])\s+", body)
    out: list[str] = []
    cur = ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > MAX_CHARS:
            out.append(cur)
            cur = (cur[-OVERLAP_CHARS:] + " " + s).strip()
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def split_block(label: str, body: str) -> list[tuple[str, str]]:
    """条文を構造に沿って再帰的に割る。

    (a)(b) -> (1)(2) の順に構造を探し、どちらも無い場合のみ文境界で割る。
    以前は (a) だけを見て残りを文字数で切っていたため、
    653 件中 576 件（88%）が文の途中で切れた断片になっていた。
    """
    if len(body) <= MAX_CHARS:
        return [(label, body)]

    for pattern in (SUB_RE, NUM_RE):
        marks = list(pattern.finditer(body))
        if len(marks) < 2:
            continue
        parts: list[tuple[str, str]] = []
        head = body[: marks[0].start()].strip()
        if len(head) >= MIN_CHARS:
            parts.append((label, head))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
            parts.extend(
                split_block(f"{label}{m.group(1)}", body[m.start():end].strip())
            )
        return parts

    return [(label, p) for p in split_on_sentences(body)]


def split_definitions(text: str) -> list[tuple[str, str]]:
    """Definitions of Terms を用語ごとに (用語, 本文) へ割る。

    "An INFIELD FLY is a fair fly ball ..." のように
    「冠詞 + 大文字の用語 + is/are」で各定義が始まる。
    """
    matches = list(DEF_RE.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end].strip()
        if len(body) >= MIN_CHARS:
            out.append((m.group(1).strip(), body))
    return out


def split_long_block(rule_no: str, body: str) -> list[tuple[str, str]]:
    """後方互換のための薄いラッパ。実体は split_block。"""
    return split_block(rule_no, body)


def rule_title(body: str, rule_no: str) -> str:
    """条文ブロックの冒頭からルールの見出し語を取り出す。

    "6.02 Balks" -> "Balks"。見出しを持たない条文
    （"1.01 Baseball is a game between..."）では文の先頭が返るため、
    ピリオドまでか 48 字で打ち切る。
    """
    first = body.split("\n", 1)[0].strip()
    title = first[len(rule_no):].strip(" .-—:")
    if "." in title[:48]:
        title = title[: title.index(".")]
    return title[:48].strip()


def split_definitions_section(text: str) -> tuple[str, str]:
    """本文と Definitions of Terms を分ける。

    Definitions は "N.00" 形式の章見出しを持たないため、
    最後のルール以降に定義パターンが密集する位置を境界とみなす。
    見つからなければ全体を本文として扱う（fail-open）。
    """
    rules = list(RULE_RE.finditer(text))
    if not rules:
        return text, ""
    last_rule_pos = rules[-1].start()
    defs = [m for m in DEF_RE.finditer(text) if m.start() > last_rule_pos]
    # 定義は数十件が連続する。少数のヒットは本文中の偶然の一致とみなす
    if len(defs) < 20:
        return text, ""
    start = defs[0].start()
    return text[:start], text[start:]


def build_chunks(text: str) -> list[dict]:
    """契約は ingest_glossary.chunk_markdown と同じキー構成にする。"""
    now = datetime.now(timezone.utc).isoformat()
    chunks: list[dict] = []

    body_text, defs_text = split_definitions_section(text)
    sections = find_sections(body_text)

    for rule_no, body, pos in split_by_rule(body_text):
        # 親見出し = 章見出し + ルール番号 + ルールの見出し語。
        # 「どの章の、何についてのルールか」を与えるのが contextual prefix の目的。
        section = section_at(sections, pos)
        title = rule_title(body, rule_no)
        parent = " / ".join(x for x in (section, f"Rule {rule_no} {title}".strip()) if x)

        for seq, (section_no, part) in enumerate(split_block(rule_no, body)):
            # contextual prefix: 本文だけでは「何についてのルールか」が
            # ベクトルに乗らないため、親見出しを機械的に前置する
            chunk_text = f"【{parent}】{part}"
            suffix = "" if seq == 0 else f"#part{seq}"
            chunks.append({
                "chunk_id": f"{SOURCE_NAME}#{section_no}{suffix}",
                "doc_id": "official_baseball_rules_2026",
                "source": SOURCE_NAME,
                "section": section_no,
                "parent_section": parent,
                "chunk_text": chunk_text,
                "char_len": len(chunk_text),
                "tier": TIER,
                "category": CATEGORY,
                "metric_names": None,
                "verified_source": "MLB Official Baseball Rules 2026",
                "ingested_at": now,
            })

    # Definitions of Terms は用語ごとに 1 チャンク。
    # 「インフィールドフライとは」型の質問はここに正解がある。
    for term, body in split_definitions(defs_text):
        for seq, (label, part) in enumerate(split_block(term, body)):
            chunk_text = f"【Definitions of Terms / {term}】{part}"
            suffix = "" if seq == 0 else f"#part{seq}"
            chunks.append({
                "chunk_id": f"{SOURCE_NAME}#def:{label}{suffix}",
                "doc_id": "official_baseball_rules_2026",
                "source": SOURCE_NAME,
                "section": f"Definitions: {term}",
                "parent_section": "Definitions of Terms",
                "chunk_text": chunk_text,
                "char_len": len(chunk_text),
                "tier": TIER,
                "category": CATEGORY,
                "metric_names": None,
                "verified_source": "MLB Official Baseball Rules 2026",
                "ingested_at": now,
            })
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Official rules PDF ingestion")
    parser.add_argument("--dry-run", action="store_true",
                        help="BQ に書かず、分割結果のみ表示する")
    parser.add_argument("--show", type=int, default=0,
                        help="--dry-run 時に本文を先頭 N 件表示する")
    args = parser.parse_args()

    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}")
        return

    text = extract_text(PDF_PATH)
    print(f"extracted: {len(text):,} chars")

    chunks = build_chunks(text)
    print(f"chunks   : {len(chunks)}")
    if chunks:
        lens = [c["char_len"] for c in chunks]
        print(f"char_len : min={min(lens)} avg={sum(lens) // len(lens)} max={max(lens)}")

    if args.dry_run:
        for c in chunks[:args.show]:
            print("-" * 70)
            print(f"[{c['char_len']:>4}c] {c['chunk_id']}")
            safe_print(c["chunk_text"][:400])
        print(f"\nTotal: {len(chunks)} chunks (dry-run, nothing written)")
        print(f"投入すると埋め込み API が {len(chunks)} コール発生します。")
        return

    client = bigquery.Client(project=PROJECT_ID)
    delete_by_source(client, [SOURCE_NAME])
    insert_chunks(client, chunks)
    generate_embeddings(client, [SOURCE_NAME])
    print(f"\nDone. {len(chunks)} chunks ingested.")


if __name__ == "__main__":
    main()