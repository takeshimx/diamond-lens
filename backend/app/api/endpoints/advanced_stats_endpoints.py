"""
Advanced Stats Ranking API エンドポイント
Statcast ベースの高度指標ランキング (P1-P7, B1-B7)
"""
from fastapi import APIRouter, Query, HTTPException

from backend.app.services.advanced_stats_service import AdvancedStatsService

router = APIRouter(tags=["Advanced Stats"])
service = AdvancedStatsService()


# ==============================================================
# P2: Pressure Dominance Index
# ==============================================================
@router.get("/advanced-stats/pitching/pressure-dominance/rankings")
async def get_pressure_rankings(
    season: int = Query(2025, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    P2 Pressure Dominance Index ランキング（先発投手限定）

    高レバレッジ状況(LI上位25%)での delta_pitcher_run_exp と
    低LI時との差分を合成したZスコア。
    - score > 0: プレッシャー下でリーグ平均より強い
    - 先発投手のみ対象（月単位SP判定でフィルタ済み）
    """
    try:
        return await service.get_pressure_rankings(
            season=season,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# P1: Pitch Tunnel Score
# ==============================================================
@router.get("/advanced-stats/pitching/pitch-tunnel/rankings")
async def get_pitch_tunnel_rankings(
    season: int = Query(2025, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    P1 Pitch Tunnel Score ランキング

    速球→変化球シーケンスで打者を騙せた割合（deception_rate）の
    リーグ平均対比 z-score。
    - deception = swinging_strike + called_strike
    - score > 0: リーグ平均より騙し力が高い
    """
    try:
        return await service.get_pitch_tunnel_rankings(
            season=season,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# P3: Stamina Score
# ==============================================================
@router.get("/advanced-stats/pitching/stamina/rankings")
async def get_stamina_rankings(
    season: int = Query(2025, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    P3 Stamina Score ランキング

    球速・回転数の投球数に対する減衰スロープ（40%+30%）と
    打順巡目別 run expectancy 差分（30%）の合成スコア。
    """
    try:
        return await service.get_stamina_rankings(
            season=season,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# P4: Two-Strike Finisher Score
# ==============================================================
@router.get("/advanced-stats/pitching/finisher/rankings")
async def get_finisher_rankings(
    season: int = Query(2025, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    P4 Two-Strike Finisher Score ランキング

    2ストライク時の whiff_rate と被 wOBA から算出した合成スコア。
    """
    try:
        return await service.get_finisher_rankings(
            season=season,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# P6: Pitch Arsenal Effectiveness
# ==============================================================
@router.get("/advanced-stats/pitching/arsenal/rankings")
async def get_arsenal_rankings(
    season: int = Query(2024, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
    team: str = Query("All", description="チーム略称フィルタ (All = 全チーム)"),
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
# B2: Plate Discipline Score
# ==============================================================
@router.get("/advanced-stats/batting/plate-discipline/rankings")
async def get_plate_discipline_rankings(
    season: int = Query(2025, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    B2 Plate Discipline Score ランキング

    O-Swing%(ゾーン外スイング率) × Z-Swing%(ゾーン内スイング率) ×
    avg_decision_value(判断価値) の合成Zスコア。
    - score > 0: リーグ平均より選球眼が良い
    """
    try:
        return await service.get_plate_discipline_rankings(
            season=season,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# B3: Clutch Hitting Index
# ==============================================================
@router.get("/advanced-stats/batting/clutch/rankings")
async def get_clutch_rankings(
    season: int = Query(2025, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    B3 Clutch Hitting Index ランキング

    高レバレッジ(LI上位25%)時の wOBA と全体wOBAの差分を合成Zスコア化。
    - score > 100: チャンスに強い
    - score < 100: チャンスに弱い
    """
    try:
        return await service.get_clutch_rankings(
            season=season,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================
# B4: Contact Consistency Score
# ==============================================================
@router.get("/advanced-stats/batting/contact-consistency/rankings")
async def get_contact_consistency_rankings(
    season: int = Query(2025, ge=2020, le=2027),
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    B4 Contact Consistency Score ランキング

    xwOBAの変動係数(CV)逆転(35%) + 平均xwOBA(35%) +
    ハードヒット率(20%) + スウィートスポット率(10%) の合成Zスコア。
    再Zスコア化済み: 100 + Z*15 (OPS+/wRC+と同等スケール)
    """
    try:
        return await service.get_contact_consistency_rankings(
            season=season,
            limit=limit,
            offset=offset,
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
