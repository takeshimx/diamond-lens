from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List, Any, Dict
import logging

# サービス層とスキーマをインポート
from app.services.player_service import get_players_by_name
from app.api.schemas import (
    PlayerSearchResults, 
    PlayerDetailsResponse
)

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