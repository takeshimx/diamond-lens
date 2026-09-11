"""
Golden PR Service (HITL フライホイール Phase 5)

Trace Viewer で「承認」された期待値を golden_dataset.json に取り込み、
GitHub に PR を作るところまでを自動化する。

設計判断:
- **golden の正は git であって BigQuery ではない**。golden は CI の合格ライン
  そのものであり、UI から直接書き換わると「誰がいつ基準を変えたか」が追えない。
  承認の出口を PR にすることで、変更履歴とレビューを必ず通す。
- ファイルは **必ず GitHub から読む**。Cloud Run のコンテナに焼かれた
  golden_dataset.json はビルド時点のもので、他の PR がマージされていれば古い。
  古い内容で PUT すると、その間の変更を巻き戻してしまう。
- 認証情報は環境変数から読む。未設定でもアプリは起動し、この機能を呼んだ時に
  だけ明示的に失敗する（起動を落とさない）。

必要な環境変数:
    GITHUB_TOKEN        fine-grained PAT。Contents: RW / Pull requests: RW
    GITHUB_REPO         "owner/repo" 形式
    GITHUB_BASE_BRANCH  省略時 "main"
"""

import base64
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from backend.app.config.settings import get_settings
from backend.app.services.golden_promotion_service import build_promotion
from backend.app.services.trace_expectation_service import list_expectations

logger = logging.getLogger(__name__)

API_ROOT = "https://api.github.com"
GOLDEN_PATH = "backend/tests/golden_dataset.json"
_TIMEOUT = 20


class GoldenPRError(RuntimeError):
    """PR 作成に失敗した。呼び出し元が利用者に見せる前提のメッセージを持つ。"""


def _creds() -> Dict[str, Optional[str]]:
    """認証情報を取り出す。

    .env は pydantic-settings が Settings オブジェクトに読み込むだけで、
    os.environ には入らない。したがって os.getenv だけでは .env の値を
    取りこぼす。Cloud Run のように環境変数で直接渡される場合もあるため、
    settings → 環境変数 の順に見る。
    """
    s = get_settings()
    return {
        "token": s.github_token or os.getenv("GITHUB_TOKEN"),
        "repo": s.github_repo or os.getenv("GITHUB_REPO"),
        "base": s.github_base_branch or os.getenv("GITHUB_BASE_BRANCH") or "main",
    }


def _config() -> Dict[str, str]:
    c = _creds()
    if not c["token"] or not c["repo"]:
        raise GoldenPRError(
            "GitHub 連携が未設定です。GITHUB_TOKEN と GITHUB_REPO "
            "(owner/repo 形式) を設定してください。"
        )
    return {"token": c["token"], "repo": c["repo"], "base": c["base"]}


def is_configured() -> bool:
    """UI が「PR 作成」ボタンを出してよいかの判定に使う。"""
    c = _creds()
    return bool(c["token"] and c["repo"])


def _request(method: str, url: str, cfg: Dict[str, str], **kwargs) -> Any:
    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    res = requests.request(method, url, headers=headers, timeout=_TIMEOUT, **kwargs)
    if res.status_code >= 400:
        # トークンそのものは絶対にログへ出さない
        logger.error(f"GitHub API {method} {url} -> {res.status_code}: {res.text[:400]}")
        raise GoldenPRError(
            f"GitHub API が {res.status_code} を返しました: "
            f"{res.json().get('message', '') if res.text else ''}"
        )
    return res.json() if res.text else None


def _fetch_golden(cfg: Dict[str, str]) -> Dict[str, Any]:
    """base ブランチの golden_dataset.json を内容と sha 付きで取得する。"""
    data = _request(
        "GET",
        f"{API_ROOT}/repos/{cfg['repo']}/contents/{GOLDEN_PATH}",
        cfg,
        params={"ref": cfg["base"]},
    )
    content = base64.b64decode(data["content"]).decode("utf-8")
    return {"golden": json.loads(content), "sha": data["sha"]}


def _create_branch(cfg: Dict[str, str], branch: str) -> None:
    ref = _request(
        "GET", f"{API_ROOT}/repos/{cfg['repo']}/git/ref/heads/{cfg['base']}", cfg
    )
    _request(
        "POST",
        f"{API_ROOT}/repos/{cfg['repo']}/git/refs",
        cfg,
        json={"ref": f"refs/heads/{branch}", "sha": ref["object"]["sha"]},
    )


def _commit_golden(
    cfg: Dict[str, str], branch: str, golden: Dict[str, Any], sha: str, message: str
) -> None:
    body = json.dumps(golden, indent=4, ensure_ascii=False) + "\n"
    _request(
        "PUT",
        f"{API_ROOT}/repos/{cfg['repo']}/contents/{GOLDEN_PATH}",
        cfg,
        json={
            "message": message,
            "content": base64.b64encode(body.encode("utf-8")).decode("ascii"),
            "sha": sha,
            "branch": branch,
        },
    )


def _pr_body(added: List[Dict[str, Any]], held: Dict[str, str]) -> str:
    lines = [
        "## Summary",
        "- Promote user-feedback-derived cases into `backend/tests/golden_dataset.json`",
        "",
        "## Background",
        "These cases originate from 👎 feedback in the chat UI. A reviewer labeled "
        "each trace in the Trace Viewer and recorded what the parsed arguments "
        "should have been. This PR turns those judgements into regression tests.",
        "",
        "## Added cases",
    ]
    for case in added:
        expected = json.dumps(case["expected"], ensure_ascii=False)
        lines.append(f"- `{case['id']}` — {case['query']}")
        lines.append(f"  - expected: `{expected}`")
        lines.append(f"  - source trace: `{case['source_trace_id']}`")

    if held:
        lines += ["", "## Held (not promoted)"]
        lines += [f"- `{tid}` — {reason}" for tid, reason in held.items()]

    lines += [
        "",
        "## Test Plan",
        "- [ ] `pytest backend/tests/test_llm_evaluation.py` — golden structure holds",
        "- [ ] `python backend/scripts/evaluate_llm_accuracy.py` — accuracy gate",
        "",
        "> Note: a newly added case may fail the accuracy gate. That is not a "
        "defect in this PR — it means the underlying bug is still unfixed. "
        "Keep this PR open until it is.",
        "",
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)",
    ]
    return "\n".join(lines)


def create_golden_pr(days: int = 90) -> Dict[str, Any]:
    """未昇格の期待値を golden に取り込む PR を作る。

    Returns:
        {"created": bool, "pr_url": str|None, "added": [...], "held": {...}}
        昇格できるものが無ければ created=False で返す（PR は作らない）。

    Raises:
        GoldenPRError: 設定不足、または GitHub API の失敗
    """
    cfg = _config()

    expectations = list_expectations(days=days)
    current = _fetch_golden(cfg)
    updated, added, held = build_promotion(current["golden"], expectations)

    if not added:
        logger.info(f"nothing to promote (held={len(held)})")
        return {"created": False, "pr_url": None, "added": [], "held": held}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch = f"chore/golden-from-feedback-{stamp}"
    title = f"test: promote {len(added)} golden case(s) from user feedback"

    _create_branch(cfg, branch)
    _commit_golden(cfg, branch, updated, current["sha"], title)
    pr = _request(
        "POST",
        f"{API_ROOT}/repos/{cfg['repo']}/pulls",
        cfg,
        json={
            "title": title,
            "head": branch,
            "base": cfg["base"],
            "body": _pr_body(added, held),
        },
    )

    logger.info(f"golden PR created: {pr['html_url']}")
    return {
        "created": True,
        "pr_url": pr["html_url"],
        "branch": branch,
        "added": added,
        "held": held,
    }


def preview_promotion(days: int = 90) -> Dict[str, Any]:
    """PR を作らずに、何が昇格され何が保留されるかだけ返す。"""
    cfg: Optional[Dict[str, str]] = None
    try:
        cfg = _config()
    except GoldenPRError:
        cfg = None

    expectations = list_expectations(days=days)
    golden = _fetch_golden(cfg)["golden"] if cfg else {"test_cases": []}
    _, added, held = build_promotion(golden, expectations)
    return {"added": added, "held": held, "configured": cfg is not None}
