import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/app/dbt_project")
DBT_PROFILES_DIR = os.environ.get("DBT_PROFILES_DIR", "/app/dbt_project")
# dbt parse が生成する semantic manifest (metrics / dimensions の構造化定義)
SEMANTIC_MANIFEST_PATH = Path(DBT_PROJECT_DIR) / "target" / "semantic_manifest.json"


class QueryRequest(BaseModel):
    metrics: list[str]
    group_by: list[str] = []
    where: list[str] = []
    order_by: list[str] = []
    limit: int = 100


def _run_mf(args: list[str]) -> dict:
    """mf CLI を subprocess で呼び出すラッパー。"""
    cmd = ["mf"] + args
    env = {
        **os.environ,
        "DBT_PROJECT_DIR": DBT_PROJECT_DIR,
        "DBT_PROFILES_DIR": DBT_PROFILES_DIR,
    }
    result = subprocess.run(
        cmd,
        cwd=DBT_PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if result.returncode != 0:
        # 失敗時は Cloud Run logs に必ず詳細を残す (HTTPException 経由では response body
        # にしか入らずログには status だけ出るため、根本原因が見えない)。
        err_msg = (
            f"[mf-error] cmd={cmd!r} exit={result.returncode} "
            f"stderr={result.stderr!r} stdout={result.stdout!r}"
        )
        print(err_msg, flush=True)
        # stderr が空でも stdout に有用な情報が出ることがあるので両方を含める
        raise RuntimeError(
            f"mf {' '.join(args)} failed (exit={result.returncode}): "
            f"stderr={result.stderr!r} stdout={result.stdout!r}"
        )
    return {"stdout": result.stdout, "stderr": result.stderr}


def _run_mf_query(req: QueryRequest) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = tmp.name

    try:
        cmd = [
            "query",
            "--metrics", ",".join(req.metrics),
            "--csv", csv_path,
        ]
        if req.group_by:
            cmd += ["--group-by", ",".join(req.group_by)]
        # 複数 where を AND で連結し1つの --where に渡す（MetricFlow CLI は複数 --where を
        # 正しく AND 結合しないため、片方しか効かないケースが発生する）
        if req.where:
            combined_where = " AND ".join(f"({w})" for w in req.where)
            cmd += ["--where", combined_where]
        for o in req.order_by:
            cmd += ["--order", o]
        if req.limit:
            cmd += ["--limit", str(req.limit)]

        _run_mf(cmd)
        df = pd.read_csv(csv_path)
        return {"rows": df.to_dict(orient="records"), "columns": list(df.columns)}
    finally:
        Path(csv_path).unlink(missing_ok=True)


@app.on_event("startup")
async def startup():
    """コンテナ起動時に dbt parse して semantic manifest を生成する。"""
    print(f"[startup] DBT_PROJECT_DIR={DBT_PROJECT_DIR}, DBT_PROFILES_DIR={DBT_PROFILES_DIR}")
    result = subprocess.run(
        ["dbt", "parse", "--profiles-dir", DBT_PROFILES_DIR, "--project-dir", DBT_PROJECT_DIR],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        # stderr が空のことがあるので stdout も含める
        raise RuntimeError(
            f"dbt parse failed at startup (exit={result.returncode}): "
            f"stderr={result.stderr!r} stdout={result.stdout!r}"
        )
    print("[startup] dbt parse succeeded; semantic_manifest.json generated")

    # 生成された manifest の metric / dimension 名一覧を起動時に dump。
    # /_debug/manifest は Cloud Run IAM で叩けない環境向けの代替手段。
    try:
        manifest = _load_semantic_manifest()
        metric_names = sorted([m["name"] for m in manifest.get("metrics", []) if m.get("name")])
        dim_names = sorted({
            d["name"]
            for sm in manifest.get("semantic_models", [])
            for d in sm.get("dimensions", [])
            if d.get("name")
        })
        sm_names = sorted([sm["name"] for sm in manifest.get("semantic_models", []) if sm.get("name")])
        print(f"[startup-manifest] metric_count={len(metric_names)} metrics={metric_names}", flush=True)
        print(f"[startup-manifest] semantic_model_count={len(sm_names)} models={sm_names}", flush=True)
        print(f"[startup-manifest] dimension_count={len(dim_names)} dimensions={dim_names}", flush=True)
    except Exception as e:
        print(f"[startup-manifest] dump failed: {e}", flush=True)


@app.post("/query")
async def query_metrics(req: QueryRequest):
    try:
        return await asyncio.to_thread(_run_mf_query, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _load_semantic_manifest() -> dict:
    """dbt parse 生成済みの semantic_manifest.json を読む。CLI 装飾出力に依存せず、
    構造化データから metric/dimension 名を直接取得できる。"""
    if not SEMANTIC_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"semantic_manifest.json not found at {SEMANTIC_MANIFEST_PATH}. "
            f"Has `dbt parse` succeeded at startup?"
        )
    return json.loads(SEMANTIC_MANIFEST_PATH.read_text(encoding="utf-8"))


@app.get("/metrics")
async def list_metrics():
    try:
        manifest = await asyncio.to_thread(_load_semantic_manifest)
        # `fg_*` プレフィックスは FanGraphs 生スタッツの内部用 metric (49 件)。
        # LLM 経路では canonical (home_runs_total 等) を使わせたいため、vocab から除外。
        # alphabetical で fg_* が中盤を占有して LLM が canonical metric を見落とす
        # ("lost in the middle") のを回避する。
        names = sorted({
            m["name"]
            for m in manifest.get("metrics", [])
            if m.get("name") and not m["name"].startswith("fg_")
        })
        return {"metrics": names}
    except Exception as e:
        print(f"[manifest-error] /metrics failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dimensions")
async def list_dimensions():
    try:
        manifest = await asyncio.to_thread(_load_semantic_manifest)
        names = sorted({
            d["name"]
            for sm in manifest.get("semantic_models", [])
            for d in sm.get("dimensions", [])
            if d.get("name")
        })
        return {"dimensions": names}
    except Exception as e:
        print(f"[manifest-error] /dimensions failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/_debug/manifest")
async def debug_manifest():
    """semantic_manifest.json の中身を直接確認するデバッグ用 endpoint。
    vocab 不整合 (yml にあるのに bot が知らない 等) の切り分け用。"""
    try:
        manifest = await asyncio.to_thread(_load_semantic_manifest)
        metric_names = sorted([m["name"] for m in manifest.get("metrics", []) if m.get("name")])
        sm_names = sorted([sm["name"] for sm in manifest.get("semantic_models", []) if sm.get("name")])
        dim_names = sorted({
            d["name"]
            for sm in manifest.get("semantic_models", [])
            for d in sm.get("dimensions", [])
            if d.get("name")
        })
        return {
            "metric_count": len(metric_names),
            "metric_names": metric_names,
            "semantic_model_count": len(sm_names),
            "semantic_model_names": sm_names,
            "dimension_count": len(dim_names),
            "dimension_names": dim_names,
        }
    except Exception as e:
        print(f"[manifest-error] /_debug/manifest failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))
