from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
import logging
import time

# サービス層とスキーマをインポート
from backend.app.services.player_service import get_players_by_name
from backend.app.services.player_profile_service import get_player_profile
from backend.app.api.schemas import (
    PlayerSearchResults,
    PlayerProfileResponse,
    AutocompleteResponse,
    AutocompletePlayerItem,
)
from backend.app.utils.structured_logger import get_logger

structured_logger = get_logger("diamond-lens")

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouterインスタンスを作成
router = APIRouter(tags=["Players"])

@router.get(
    "/players/search",
    response_model=PlayerSearchResults,
    summary="選手名を検索",
    description="入力されたクエリ文字列に部分一致する選手名を検索し、選手IDと名前のリストを返します。",
    tags=["players"]
)
async def search_players_endpoint(
    # QueryはURLクエリパラメータから値を取得するためのFastAPIの依存性注入機能
    # min_length=2 は、検索クエリの最小文字数を指定するバリデーションルール
    q: Optional[str] = Query(None, description="検索クエリ（選手名の一部）")
):
    """
    選手名で部分一致検索を行い、結果を返します。
    クエリ文字列が短い場合や結果がない場合は、空のリストを返します。
    """
    # サービス層の検索関数を呼び出す
    # player_service.get_players_by_name は Optional[List[PlayerSearchItem]] を返す想定
    search_query = q if q is not None else ""
    search_results_list = get_players_by_name(search_query)

    # サービス層でエラーが発生した場合など、Noneが返された場合のハンドリング
    if search_results_list is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve search results due to an internal error.")

    # PlayerSearchResultsモデルのインスタンスを構築して返す
    # search_results_listは既にPlayerSearchItemのリストなので、そのままresultsに渡す
    return PlayerSearchResults(query=q, results=search_results_list)


@router.get(
    "/players/autocomplete",
    response_model=AutocompleteResponse,
    summary="選手名オートコンプリート（統合版）",
    description=(
        "メモリ常駐の Trie から候補上位 N 件を返す。"
        "context により候補プールを切り替える: "
        "all / statcast_pitcher / statcast_batter / stuffplus。"
        "Trie 構築未完了 / 失敗時は /players/search へフォールバック。"
    ),
    tags=["players"],
)
async def autocomplete_players_endpoint(
    request: Request,
    q: str = Query(..., min_length=1, max_length=64, description="検索プレフィックス"),
    context: str = Query("all", description="all / statcast_pitcher / statcast_batter / stuffplus"),
    season: Optional[int] = Query(None, ge=2000, le=2100, description="context!=all のとき必須"),
    limit: int = Query(10, ge=1, le=50, description="返却件数の上限"),
):
    """選手名オートコンプリート用の統合エンドポイント。"""
    valid_contexts = {"all", "statcast_pitcher", "statcast_batter", "stuffplus"}
    if context not in valid_contexts:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid context. Must be one of {sorted(valid_contexts)}.",
        )
    if context != "all" and season is None:
        raise HTTPException(
            status_code=400,
            detail=f"season is required when context='{context}'.",
        )

    service = getattr(request.app.state, "autocomplete_service", None)
    is_ready = bool(getattr(request.app.state, "autocomplete_ready", False))
    started = time.monotonic()

    # Trie 構築完了 → 通常パス
    if service is not None and is_ready:
        try:
            entries, served_from = service.query(
                prefix=q, context=context, season=season, limit=limit
            )
            results = [
                AutocompletePlayerItem(
                    mlbid=e.mlbid,
                    full_name=e.full_name,
                    team=e.team,
                    primary_position=e.primary_position,
                    bat_side=e.bat_side,
                    pitch_hand=e.pitch_hand,
                    active=e.active,
                    score=e.popularity_score,
                )
                for e in entries
            ]
            structured_logger.info(
                "autocomplete_request",
                prefix=q,
                context=context,
                season=season,
                served_from=served_from,
                latency_ms=int((time.monotonic() - started) * 1000),
                result_count=len(results),
            )
            return AutocompleteResponse(
                query=q,
                context=context,
                season=season,
                served_from=served_from,
                results=results,
            )
        except Exception as e:
            logger.error(f"Autocomplete trie query failed: {e}", exc_info=True)
            # 例外時は fallback に落とす

    # フォールバック: 既存 /players/search 相当のロジックで候補を返す
    # （context によるサブセット絞り込みは Vol.1 の fallback ではスキップ）
    fallback_results_raw = get_players_by_name(q) or []
    fallback_results = [
        AutocompletePlayerItem(
            mlbid=item.mlbid if item.mlbid is not None else 0,
            full_name=item.player_name,
            team=item.team,
            primary_position=None,
            bat_side=None,
            pitch_hand=None,
            active=False,
            score=0.0,
        )
        for item in fallback_results_raw
        if item.mlbid is not None
    ][:limit]
    structured_logger.info(
        "autocomplete_request",
        prefix=q,
        context=context,
        season=season,
        served_from="fallback",
        latency_ms=int((time.monotonic() - started) * 1000),
        result_count=len(fallback_results),
    )
    return AutocompleteResponse(
        query=q,
        context=context,
        season=season,
        served_from="fallback",
        results=fallback_results,
    )


@router.get(
    "/players/{mlbid}/profile",
    response_model=PlayerProfileResponse,
    summary="選手プロフィール取得",
    description="MLB ID (mlbid) から選手のBio情報とKPIを取得します。season を指定しない場合は最新シーズンを返します。",
    tags=["players"]
)
async def get_player_profile_endpoint(
    mlbid: int,
    season: Optional[int] = Query(None, description="取得するシーズン (例: 2024)。省略時は最新シーズン。"),
):
    """
    指定された mlbid の選手プロフィール（Bio + 打者/投手KPI + 月別成績）を返します。
    """
    profile = get_player_profile(mlbid, season=season)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Player with mlbid={mlbid} not found.")
    return profile


# # Router for Shohei Ohtani's two-way player stats
# @router.get(
#     "/players/ohtani/two-way-stats",
#     response_model=List[Dict[str, Any]],  # Ohtaniの二刀流選手統計は辞書のリストで返す
#     summary="Shohei Ohtaniの二刀流選手統計を取得",
#     description="Shohei Ohtaniの二刀流選手統計を取得します。",
#     tags=["players"]
# )
# async def get_ohtani_two_way_stats_endpoint(
#     season: Optional[int] = None
# ) -> List[Dict[str, Any]]:
#     """
#     Shohei Ohtaniの二刀流選手統計を取得します。
#     """
#     ohtani_stats = get_ohtani_two_way_stats(season=season)

#     if ohtani_stats is None:
#         raise HTTPException(status_code=404, detail="Ohtani's two-way stats not found.")
#     return ohtani_stats


# @router.get(
#     "/players/{player_id}",
#     response_model=PlayerDetailsResponse,
#     summary="選手の詳細情報と年度別成績を取得",
#     description="指定されたFanGraphs選手ID (idfg) に基づいて、選手の基本情報、年度別打撃成績、年度別投球成績を取得します。",
#     tags=["players"] # OpenAPIドキュメントでのグルーピング用タグ
# )
# async def get_player_details_endpoint(
#     # PathはURLパスから値を取得するためのFastAPIの依存性注入機能
#     player_id: int = Path(..., description="取得したい選手のFanGraphs ID (idfg)")):
#     """
#     指定された選手IDの選手詳細情報と年度別成績を返します。
#     選手が見つからない場合は404エラーを返します。
#     """
#     # サービス層の関数を呼び出してデータを取得
#     player_details = get_player_details(player_id)

#     # サービス層からNoneが返された場合（選手が見つからない、エラーなど）はHTTP 404を返す
#     if player_details is None:
#         raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found.")

#     # 取得したPydanticモデルのインスタンスを返す。FastAPIが自動的にJSONにシリアライズする。
#     return player_details