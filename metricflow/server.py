import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/app")
DBT_PROFILES_DIR = os.environ.get("DBT_PROFILES_DIR", "/app")


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
        raise RuntimeError(f"mf {' '.join(args)} failed: {result.stderr}")
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
        for w in req.where:
            cmd += ["--where", w]
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
    result = subprocess.run(
        ["dbt", "parse", "--profiles-dir", DBT_PROFILES_DIR, "--project-dir", DBT_PROJECT_DIR],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt parse failed at startup: {result.stderr}")


@app.post("/query")
async def query_metrics(req: QueryRequest):
    try:
        return await asyncio.to_thread(_run_mf_query, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def list_metrics():
    try:
        out = await asyncio.to_thread(_run_mf, ["list", "metrics"])
        lines = [l.strip() for l in out["stdout"].splitlines() if l.strip()]
        return {"metrics": lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dimensions")
async def list_dimensions():
    try:
        out = await asyncio.to_thread(_run_mf, ["list", "dimensions"])
        lines = [l.strip() for l in out["stdout"].splitlines() if l.strip()]
        return {"dimensions": lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
