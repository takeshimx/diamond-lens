"""
Advanced Stats Ranking API エンドポイント
Statcast ベースの高度指標ランキング (P1-P7, B1-B7)
"""
from fastapi import APIRouter, Query, HTTPException

from backend.app.services.advanced_stats_service import AdvancedStatsService

router = APIRouter(tags=["Advanced Stats"])
service = AdvancedStatsService()


# ==============================================================
# P6: Pitch Arsenal Effectiveness
# ==============================================================
@router.get("/advanced-stats/pitching/arsenal/rankings")
async def get_arsenal_rankings(
    season: int = Query(2024, ge=2020, le=2027),
    min_pitches: int = Query(100, ge=0, le=5000, description="最低投球数フィルタ"),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
    team: str = Query("All", description="チーム名フィルタ (All = 全チーム)"),
):
    """
    P6 Pitch Arsenal Effectiveness ランキング

    Shannon entropy (多様性) × 球種別得点抑止力 (効果) の合成スコアでランキング化。
    - diversity_score: 球種使用率のシャノンエントロピー (高い = 多彩)
    - effectiveness_score: 全球種の合計 delta_pitcher_run_exp (高い = 抑止力が高い)
    - synthetic_score: diversity × effectiveness
    """
    try:
        return await service.get_arsenal_rankings(
            season=season,
            min_pitches=min_pitches,
            limit=limit,
            offset=offset,
            team=team,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced-stats/pitching/arsenal/pitch-mix/{pitcher_id}")
async def get_arsenal_pitch_mix(
    pitcher_id: int,
    season: int = Query(2024, ge=2020, le=2027),
):
    """
    特定投手の球種ミックス詳細

    各球種の使用率 (%) と平均得点抑止力 (avg delta_pitcher_run_exp)
    """
    try:
        return await service.get_arsenal_pitch_mix(
            pitcher_id=pitcher_id,
            season=season,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# 共通: 投手検索 (オートコンプリート)
# ==============================================================
@router.get("/advanced-stats/pitching/search")
async def search_pitchers(
    name: str = Query(..., min_length=2, description="検索する選手名（部分一致）"),
    season: int = Query(2024, ge=2020, le=2027),
    limit: int = Query(10, ge=1, le=50),
):
    """投手名で検索（オートコンプリート用）"""
    try:
        return await service.search_pitchers(
            name=name,
            season=season,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
