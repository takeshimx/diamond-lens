"""
Hot / Slump 打者ランキングサービス
view_tbl_batter_rolling_vs_season_stats_7_days / 15_days を使用して
直近スタッツ vs シーズン平均を比較し、ホット/スランプ打者Top Nを返す
"""
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

from backend.app.services.base import (
    client, logger,
    PROJECT_ID, DATASET_ID,
    BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID,
    BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID,
)

VALID_PERIODS = (7, 15)
VALID_METRICS = ('ba', 'ops', 'barrels', 'hard_hit')


def _table_id(period: int) -> str:
    return (
        BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID
        if period == 7
        else BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID
    )


def _metric_config(period: int) -> Dict[str, Dict[str, str]]:
    """period に応じたカラム名マッピングを返す"""
    s = f"{period}days"
    return {
        'ba': {
            'value_col': f'ba_{s}',
            'hot_flag': f'is_red_hot_ba_{s}',
            'slump_flag': f'is_slump_ba_{s}',
        },
        'ops': {
            'value_col': f'ops_{s}',
            'hot_flag': f'is_red_hot_ops_{s}',
            'slump_flag': f'is_slump_ops_{s}',
        },
        'barrels': {
            'value_col': f'barrels_percentage_{s}',
            'hot_flag': f'is_red_hot_barrels_{s}',
            'slump_flag': f'is_slump_barrels_{s}',
        },
        'hard_hit': {
            'value_col': f'hard_hit_percentage_{s}',
            'hot_flag': f'is_red_hot_hard_hit_{s}',
            'slump_flag': f'is_slump_hard_hit_{s}',
        },
    }


def _rows_to_list(df) -> List[Dict[str, Any]]:
    """DataFrameをdictのリストに変換（NaN・bool・date の型変換も行う）"""
    results = []
    bool_cols = [c for c in df.columns if c.startswith('is_')]
    for _, row in df.iterrows():
        row_dict = {
            k: (None if (isinstance(v, float) and v != v) else v)
            for k, v in row.to_dict().items()
        }
        for col in bool_cols:
            if row_dict.get(col) is not None:
                row_dict[col] = bool(row_dict[col])
        if 'game_date' in row_dict and row_dict['game_date'] is not None:
            row_dict['game_date'] = str(row_dict['game_date'])
        results.append(row_dict)
    return results


def get_hot_slump_batters(
    metric: str,
    period: int = 7,
    game_date: Optional[str] = None,
    top_n: int = 10,
) -> Optional[Dict[str, Any]]:
    """
    指定された指標・期間・日付に基づいてホット/スランプ打者ランキングを返す。

    Args:
        metric:    'ba' | 'ops' | 'barrels' | 'hard_hit'
        period:    7 または 15（日間）
        game_date: 'YYYY-MM-DD' 形式。省略時は最新日
        top_n:     取得件数（デフォルト10）

    Returns:
        {'hot': [...], 'slump': [...], 'game_date': 'YYYY-MM-DD'}
    """
    if metric not in VALID_METRICS:
        logger.error(f"Invalid metric: {metric}")
        return None
    if period not in VALID_PERIODS:
        logger.error(f"Invalid period: {period}")
        return None

    cfg = _metric_config(period)[metric]
    value_col = cfg['value_col']
    hot_flag = cfg['hot_flag']
    slump_flag = cfg['slump_flag']
    s = f"{period}days"
    table_full = f"`{PROJECT_ID}.{DATASET_ID}.{_table_id(period)}`"

    if game_date:
        date_clause = "AND game_date = @game_date"
        params = [bigquery.ScalarQueryParameter("game_date", "DATE", game_date)]
    else:
        date_clause = f"AND game_date = (SELECT MAX(game_date) FROM {table_full})"
        params = []

    base_select = f"""
        SELECT
            game_date,
            batter_name,
            batter_id,
            team,
            age,
            hrs_{s},
            abs_per_hr_{s},
            ba_{s},
            ops_{s},
            barrels_percentage_{s},
            hard_hit_percentage_{s},
            is_red_hot_hr_{s},
            is_slump_hr_{s},
            is_red_hot_ba_{s},
            is_slump_ba_{s},
            is_red_hot_ops_{s},
            is_slump_ops_{s},
            is_red_hot_barrels_{s},
            is_slump_barrels_{s},
            is_red_hot_hard_hit_{s},
            is_slump_hard_hit_{s}
        FROM {table_full}
        WHERE batter_name IS NOT NULL
        {date_clause}
    """

    hot_query = base_select + f"""
        AND {hot_flag} = TRUE
        AND {value_col} IS NOT NULL
        ORDER BY {value_col} DESC
        LIMIT {top_n}
    """

    slump_query = base_select + f"""
        AND {slump_flag} = TRUE
        AND {value_col} IS NOT NULL
        ORDER BY {value_col} ASC
        LIMIT {top_n}
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)

    try:
        hot_df = client.query(hot_query, job_config=job_config).to_dataframe()
        slump_df = client.query(slump_query, job_config=job_config).to_dataframe()

        hot_list = _rows_to_list(hot_df)
        slump_list = _rows_to_list(slump_df)

        resolved_date = (
            hot_list[0]['game_date'] if hot_list
            else slump_list[0]['game_date'] if slump_list
            else game_date
        )

        return {
            'hot': hot_list,
            'slump': slump_list,
            'game_date': resolved_date,
        }

    except GoogleCloudError as e:
        logger.error(f"BigQuery error in get_hot_slump_batters: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_hot_slump_batters: {e}", exc_info=True)
        return None


def get_available_dates(period: int = 7) -> Optional[List[str]]:
    """
    view から利用可能な game_date の一覧を返す（降順・最新30件）
    """
    if period not in VALID_PERIODS:
        logger.error(f"Invalid period: {period}")
        return None
    table_full = f"`{PROJECT_ID}.{DATASET_ID}.{_table_id(period)}`"
    query = f"""
        SELECT DISTINCT game_date
        FROM {table_full}
        WHERE game_date IS NOT NULL
        ORDER BY game_date DESC
        LIMIT 30
    """
    try:
        df = client.query(query).to_dataframe()
        if df.empty:
            return []
        return [str(d) for d in df['game_date'].tolist()]
    except Exception as e:
        logger.error(f"Error fetching available dates: {e}", exc_info=True)
        return None
