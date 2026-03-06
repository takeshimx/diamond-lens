"""
Model Registry API Endpoints
モデルの学習・登録・バージョン管理エンドポイント
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.app.services.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/model-registry", tags=["Model Registry"])
registry = ModelRegistryService()


# ============================================================
# リクエスト / レスポンスモデル
# ============================================================

class TrainRequest(BaseModel):
    model_type: str
    season: int


class PromoteRequest(BaseModel):
    model_type: str
    version: str


# ============================================================
# エンドポイント
# ============================================================

@router.post("/train")
async def train_and_register(request: TrainRequest):
    """モデルを学習し、GCS に保存 & BigQuery にメタデータ登録"""
    try:
        version = registry.train_and_register(
            model_type=request.model_type,
            season=request.season,
        )
        return {
            "message": f"Model trained and registered: {version.version}",
            "version": version.to_bq_row(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions")
async def list_versions(
    model_type: str = Query(..., description="Model type to query"),
):
    """登録済みバージョンの一覧を取得"""
    versions = registry.list_versions(model_type)
    return {"model_type": model_type, "versions": versions}


@router.post("/promote")
async def promote_version(request: PromoteRequest):
    """指定バージョンを active に昇格"""
    try:
        registry.promote_version(
            model_type=request.model_type,
            version=request.version,
        )
        return {
            "message": f"Promoted {request.model_type} to {request.version}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_version(
    model_type: str = Query(..., description="Model type to query"),
):
    """現在の active バージョンを取得"""
    active = registry.get_active_version(model_type)
    if not active:
        return {
            "model_type": model_type,
            "message": "No active version found.",
        }
    return active.to_bq_row()
