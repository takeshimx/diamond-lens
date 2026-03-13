"""
Stuff+ / Pitching+ API エンドポイント
球質評価（Stuff+）と総合投球評価（Pitching+）のランキング・推論・比較
"""
from fastapi import APIRouter, Query, HTTPException, Path

from backend.app.services.stuff_plus_service import StuffPlusService

router = APIRouter(tags=["Stuff+"])
service = StuffPlusService()


@router.get("/stuff-plus/rankings")
async def get_rankings(
    model_type: str = Query(
        "stuff_plus",
        description="stuff_plus（球質のみ）or pitching_plus（球質+制球）",
        pattern="^(stuff_plus|pitching_plus)$",
    ),
    season: int = Query(2025, ge=2020, le=2026),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    min_pitches: int = Query(0, ge=0, le=5000, description="球種別最低投球数フィルタ"),
):
    """
    Stuff+ or Pitching+ ランキングを取得

    - **stuff_plus**: 球質のみ（速度、回転、変化量、リリース、arm angle）
    - **pitching_plus**: 球質 + 投球位置（plate_x/plate_z）
    """
    try:
        return await service.get_rankings(
            model_type=model_type,
            season=season,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
            min_pitches=min_pitches,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stuff-plus/search")
async def search_pitchers(
    name: str = Query(..., min_length=2, description="検索する選手名（部分一致）"),
    season: int = Query(2025, ge=2020, le=2026),
    limit: int = Query(10, ge=1, le=50),
):
    """
    選手名で投手を検索（オートコンプリート用）
    """
    try:
        return await service.search_pitchers(
            name=name,
            season=season,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stuff-plus/pitcher/{pitcher_id}")
async def get_pitcher_detail(
    pitcher_id: int = Path(..., description="MLB pitcher ID"),
    model_type: str = Query(
        "stuff_plus",
        pattern="^(stuff_plus|pitching_plus)$",
    ),
    season: int = Query(2025, ge=2020, le=2026),
):
    """
    特定投手の球種別 Stuff+ / Pitching+ スコアをリアルタイム推論
    """
    try:
        return await service.predict_single_pitcher(
            pitcher_id=pitcher_id,
            model_type=model_type,
            season=season,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stuff-plus/pitcher/{pitcher_id}/compare")
async def compare_models(
    pitcher_id: int = Path(..., description="MLB pitcher ID"),
    season: int = Query(2025, ge=2020, le=2026),
):
    """
    Stuff+ vs Pitching+ 比較（gap分析）

    - **gap > 0**: 球質型（球質は elite だが制球パターンで損している）
    - **gap < 0**: 制球型（球質は平凡だが制球で稼いでいる）
    - **gap ≈ 0**: バランス型
    """
    try:
        return await service.compare_stuff_pitching(
            pitcher_id=pitcher_id,
            season=season,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
