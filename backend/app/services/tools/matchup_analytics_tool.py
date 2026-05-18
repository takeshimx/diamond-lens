from langchain_core.tools import tool
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

from backend.app.utils.structured_logger import get_logger
from ..bigquery_service import client

logger = get_logger("tools.matchup_analytics")


@tool
def mlb_matchup_analytics_tool(batter_name: str, pitcher_name: str):
    """
    特定の打者と投手の『球種別の対戦相性サマリー』を取得する分析ツール。
    打率、OPSなどの結果だけでなく、空振り率、球速、平均回転数などの球のクオリティも取得できます。
    batter_name: 打者のフルネーム（例: 'Shohei Ohtani'）
    pitcher_name: 投手のフルネーム（例: 'Yu Darvish'）
    """
    query = f"""
    SELECT *
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_matchup_pitch_analytics`
    WHERE (
        (UPPER(batter_name) = UPPER(@batter_name)) OR
        (UPPER(batter_name) = UPPER(@batter_reversed)) OR
        (UPPER(batter_name) LIKE UPPER(@batter_part))
    ) AND (
        (UPPER(pitcher_name) = UPPER(@pitcher_name)) OR
        (UPPER(pitcher_name) = UPPER(@pitcher_reversed)) OR
        (UPPER(pitcher_name) LIKE UPPER(@pitcher_part))
    )
    ORDER BY pitch_count DESC
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

    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error in mlb_matchup_analytics_tool: {e}")
        return []