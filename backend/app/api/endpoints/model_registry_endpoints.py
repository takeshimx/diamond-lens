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


# ============================================================
# Retrain: 全モデル再学習 & 品質ベース auto-promote
# ============================================================

class RetrainRequest(BaseModel):
    season: int
    model_types: list[str] = ["batter_segmentation", "pitcher_segmentation"]


@router.post("/retrain")
async def retrain_all(request: RetrainRequest):
    """
    Retrain all models and promote if model quality is higher than active version.
    Will be called weekly from Cloud Workflows
    """
    results = []

    for model_type in request.model_types:
        result = {
            "model_type": model_type,
            "action": "skipped",
            "reason": ""
        }

        try:
            # 1. Get current active version
            active = registry.get_active_version(model_type)

            if active and active.training_season == request.season:
                # retrain with same season -> inertia-based promotion
                pass # retrain later
            elif active and active.training_season > request.season:
                result["reason"] = (
                    f"Active model trained on newer season "
                    f"({active.training_season} > {request.season})"
                )
                results.append(result)
                continue

            # 2. Retrain model
            new_version = registry.train_and_register(
                model_type=model_type,
                season=request.season,
            )
            result["new_version"] = new_version.version
            result["new_inertia"] = new_version.model_params.get("inertia")
            result["n_samples"] = new_version.n_samples

            # 3. Compare quality -> auto-promote
            if active:
                active_inertia = active.model_params.get("inertia", float("inf"))
                new_inertia = new_version.model_params.get("inertia", float("inf"))

                if new_inertia <= active_inertia:
                    registry.promote_version(model_type, new_version.version)
                    result["action"] = "promoted"
                    result["reason"] = (
                        f"inertia improved: {active_inertia:.2f} → {new_inertia:.2f}"
                    )
                else:
                    result["action"] = "trained_not_promoted"
                    result["reason"] = (
                        f"inertia worse: {active_inertia:.2f} → {new_inertia:.2f}"
                    )
            else:
                # First model -> auto-promote
                registry.promote_version(model_type, new_version.version)
                result["action"] = "promoted"
                result["reason"] = "First model — auto-promoted"
        
        except Exception as e:
            result["action"] = "error"
            result["reason"] = str(e)
        
        results.append(result)
    
    return {"season": request.season, "results": results}
                

