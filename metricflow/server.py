from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from metricflow.cli.cli_context import CLIContext
import asyncio, os

app = FastAPI()
_mf_context: CLIContext | None = None

@app.on_event("startup")
async def startup():
    global _mf_context
    _mf_context = CLIContext(config_dir=os.environ["DBT_PROJECT_DIR"])

class QueryRequest(BaseModel):
    metrics: list[str]
    group_by: list[str] = []
    where: list[str] = []
    order_by: list[str] = []
    limit: int = 100

class MetaRequest(BaseModel):
    pass  # 引数なし

@app.post("/query")
async def query_metrics(req: QueryRequest):
    try:
        result = await asyncio.to_thread(
            _mf_context.get_dataframe,
            metrics=req.metrics,
            group_by=req.group_by,
            where_constraints=req.where,
            order_by=req.order_by,
            limit=req.limit,
        )
        return {"rows": result.to_dict(orient="records"), "columns": list(result.columns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def list_metrics():
    metrics = await asyncio.to_thread(_mf_context.list_metrics)
    return {"metrics": [m.name for m in metrics]}

@app.get("/dimensions")
async def list_dimensions():
    dims = await asyncio.to_thread(_mf_context.list_dimensions)
    return {"dimensions": [d.name for d in dims]}

@app.get("/health")
async def health():
    return {"status": "ok"}