from langchain_core.tools import tool
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

from backend.app.core.exceptions import DataFetchError
from backend.app.utils.structured_logger import get_logger
from ..bigquery_service import client
from ..cache_service import StatsCache

logger = get_logger("tools.matchup_history")


@tool
def mlb_matchup_history_tool(batter_name: str, pitcher_name: str):
    """
    特定の打者と投手の『過去の全対決履歴』を取得するツール。
    打席ごとの配球（球種の流れ）や、結果、コースなどの詳細なプロセスを取得できます。
    batter_name: 打者のフルネーム（例: 'Shohei Ohtani'）
    pitcher_name: 投手のフルネーム（例: 'Yu Darvish'）
    """
    logger.info(f"🔍 DEBUG: mlb_matchup_history_tool called with batter='{batter_name}', pitcher='{pitcher_name}'")
    batter_name = batter_name.strip()
    pitcher_name = pitcher_name.strip()

    query = f"""
    SELECT *
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_matchup_specific_history`
    WHERE (
        (UPPER(batter_name) = UPPER(@batter_name)) OR
        (UPPER(batter_name) = UPPER(@batter_reversed)) OR
        (UPPER(batter_name) LIKE UPPER(@batter_part))
    ) AND (
        (UPPER(pitcher_name) = UPPER(@pitcher_name)) OR
        (UPPER(pitcher_name) = UPPER(@pitcher_reversed)) OR
        (UPPER(pitcher_name) LIKE UPPER(@pitcher_part))
    )
    ORDER BY game_date DESC, at_bat_number DESC
    LIMIT 30
    """

    def reverse_name(name):
        parts = name.split()
        return f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else name

    b_rev = reverse_name(batter_name)
    p_rev = reverse_name(pitcher_name)
    b_part = f"%{batter_name.split()[-1]}%" if len(batter_name.split()) > 0 else "%"
    p_part = f"%{pitcher_name.split()[-1]}%" if len(pitcher_name.split()) > 0 else "%"

    query_parameters = [
        ScalarQueryParameter("batter_name", "STRING", batter_name),
        ScalarQueryParameter("batter_reversed", "STRING", b_rev),
        ScalarQueryParameter("batter_part", "STRING", b_part),
        ScalarQueryParameter("pitcher_name", "STRING", pitcher_name),
        ScalarQueryParameter("pitcher_reversed", "STRING", p_rev),
        ScalarQueryParameter("pitcher_part", "STRING", p_part)
    ]

    job_config = QueryJobConfig(query_parameters=query_parameters)

    # Check cache first
    cache = StatsCache()
    cached_data = cache.get_player_stats(player_name=batter_name, season=2024, query_type=f"matchup_{pitcher_name}")
    if cached_data:
        logger.info("Cache HIT")
        return cached_data
    
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        logger.info(f"✅ Matchup history found", row_count=len(df), batter_name=batter_name, pitcher_name=pitcher_name)
        result = df.to_dict(orient='records')
        # Save to Redis
        cache.set_player_stats(player_name=batter_name, season=2024, query_type=f"matchup_{pitcher_name}", data=result)
        return result
    except Exception as e:
        raise DataFetchError("対戦履歴の取得に失敗しました", original_error=e) from e