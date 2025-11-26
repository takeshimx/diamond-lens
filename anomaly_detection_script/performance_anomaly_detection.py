"""
Script to detect performance anomalies in MLB players using BigQuery data.
Specifically focuses on batters' performance flags over rolling periods, 7 and 15 days.
"""

from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import numpy as np
from functools import lru_cache
from dataclasses import dataclass
from backend.app.api.schemas import *
from backend.app.services.base import (
    get_bq_client, client, logger,
    PROJECT_ID, DATASET_ID,
    BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID,
    BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID,
)


# ============== Configuration ==============
@dataclass
class AnomalyConfig:
    """異常検知の設定"""
    z_score_threshold: float = 2.0 # Z-scoreの閾値（2σ = 上位2.5%
    top_n_players: int = 15
    enable_statistical_analysis: bool = True # Z-score分析を有効化

CONFIG = AnomalyConfig()

# =============== Step 1: Fetch data from BigQuery ===============
# Function to get batter performance flags by comparing rolling and season stats
@lru_cache(maxsize=128)
def get_batter_performance_flags(query_date: str, days: int) -> Optional[List[PlayerBatterPerformanceFlags]]:
    """
    指定された日付と日数に基づいて、打者のパフォーマンスフラグを取得します。
    """

    if days == 7:
        table_id = BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID
    elif days == 15:
        table_id = BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID
    

    query = f"""
        SELECT  
            game_date,
            batter_name,
            batter_id,
            team,
            age,
            hrs_{days}days,
            abs_per_hr_{days}days,
            is_red_hot_hr_{days}days,
            is_slump_hr_{days}days,
            ba_{days}days,
            is_red_hot_ba_{days}days,
            is_slump_ba_{days}days,
            ops_{days}days,
            is_red_hot_ops_{days}days,
            is_slump_ops_{days}days,
            barrels_percentage_{days}days,
            is_red_hot_barrels_{days}days,
            is_slump_barrels_{days}days,
            hard_hit_percentage_{days}days,
            is_red_hot_hard_hit_{days}days,
            is_slump_hard_hit_{days}days
        FROM
            `{PROJECT_ID}.{DATASET_ID}.{table_id}`
        WHERE
            game_date = @query_date
        ORDER BY
            game_date ASC
    """


    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_date", "DATE", query_date)
        ]
    )

    # Debugging: log the query and parameters
    logger.debug(f"Executing BigQuery query for batter performance flags for {days} days.")
    logger.debug(f"Query: {query}")
    logger.debug(f"Parameters: {job_config.query_parameters}")


    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # Debugging: log the DataFrame shape and columns
        logger.debug(f"DEBUG: Fetched batter performance flags DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
        logger.debug(f"DEBUG: First few rows of the DataFrame:\n{df.head()}")

        if df.empty:
            logger.warning(f"No data found for date: {query_date}, days: {days}")
            return []

        # Convert NaN to None and return as list of dictionaries
        df = df.replace({np.nan: None})

        logger.debug(f"DEBUG: Returning {len(df)} rows as list of dicts")
        return df.to_dict('records')
    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for batter performance flags failed: {e}")
        return None
    

# ============== Step 2: Statistical Anomaly Detection ==============
def calculate_z_scores(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """
    各統計指標のZ-scoreを計算します。
    集団全体の中で、どれだけ異常値かを統計的に評価します。
    
    Args:
        df: パフォーマンスデータのDataFrame
        days: ローリング期間
    
    Returns:
        Z-scoreカラムが追加されたDataFrame
    """
    df_with_z = df.copy()

    # 分析対象の統計カラム
    stat_columns = [
        f'ba_{days}days',
        f'ops_{days}days',
        f'barrels_percentage_{days}days',
        f'hard_hit_percentage_{days}days'
    ]

    for col in stat_columns:
        valid_data = df_with_z[col].dropna()

        if len(valid_data) > 1:
            mean = valid_data.mean()
            std = valid_data.std()

            if std > 0:
                z_score_col = f'{col}_z_score'
                df_with_z[z_score_col] = (df_with_z[col] - mean) / std
            else:
                df_with_z[f'{col}_z_score'] = None
        else:
            df_with_z[f'{col}_z_score'] = None
    
    return df_with_z


def identify_statistical_anomalies(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """
    Z-scoreベースで統計的異常を判定します。
    
    Args:
        df: Z-scoreが計算されたDataFrame
        days: ローリング期間
    
    Returns:
        統計的異常フラグが追加されたDataFrame
    """
    df_anomaly = df.copy()

    # BA（打率）のZ-scoreベースの異常判定
    ba_zscore_col = f'ba_{days}days_z_score'
    if ba_zscore_col in df_anomaly.columns:
        df_anomaly['is_statistical_red_hot_ba'] = (df_anomaly[ba_zscore_col] > CONFIG.z_score_threshold)
        df_anomaly['is_statistical_slump_ba'] = (df_anomaly[ba_zscore_col] < -CONFIG.z_score_threshold)

    # 統計的に正しい指標を計算
    zscores_cols = [col for col in df_anomaly.columns if col.endswith('_z_score')]

    if zscores_cols:
        # 最大絶対値Z-score（最も異常な指標）
        df_anomaly['max_abs_zscore'] = df_anomaly[zscores_cols].abs().max(axis=1)

        # どの指標が最大Z-scoreかを記録
        def get_max_zscore_column(row):
            abs_scores = {col: abs(row[col]) if pd.notna(row[col]) else 0 for col in zscores_cols}
            max_col = max(abs_scores, key=abs_scores.get)
            # カラム名を読みやすく変換 (例: ba_7days_z_score → BA)
            metric_name = max_col.replace(f'_{days}days_z_score', '').upper()
            return f"{metric_name} ({abs_scores[max_col]:.2f}σ)"

        df_anomaly['max_zscore_metric'] = df_anomaly.apply(get_max_zscore_column, axis=1)

        # 2σを超える指標の数
        df_anomaly['anomaly_indicator_count'] = (
            df_anomaly[zscores_cols].abs() > CONFIG.z_score_threshold
        ).sum(axis=1)

    return df_anomaly


def calculate_anomaly_composite_score(row: Dict[str, Any], days: int) -> int:
    """
    BigQueryのフラグベースの複合スコアを計算します。
    
    Args:
        row: 選手データの辞書
        days: ローリング期間
    
    Returns:
        複合スコア（0-5の整数）
    """
    score = 0
    flag_columns = [
        f'is_red_hot_ba_{days}days',
        f'is_red_hot_ops_{days}days',
        f'is_red_hot_hr_{days}days',
        f'is_red_hot_barrels_{days}days',
        f'is_red_hot_hard_hit_{days}days'
    ]

    for col in flag_columns:
        if row.get(col) is True:
            score += 1
    
    return score


def enhance_performance_data(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """
    BigQueryから取得したデータに追加の統計分析を実施します。
    
    処理内容:
    1. BigQueryフラグベースの複合スコア計算
    2. Z-scoreベースの統計分析
    3. 両方の結果を統合
    
    Args:
        df: BigQueryから取得したDataFrame
        days: ローリング期間
    
    Returns:
        拡張されたDataFrame
    """
    if df.empty:
        return df
    
    df_enhanced = df.copy()

    # 1. BigQueryフラグベースの複合スコア
    df_enhanced['bq_anomaly_score'] = df_enhanced.apply(
        lambda row: calculate_anomaly_composite_score(row, days), axis=1
    )

    # 2. Z-scoreベースの統計分析
    if CONFIG.enable_statistical_analysis:
        df_enhanced = calculate_z_scores(df_enhanced, days)
        df_enhanced = identify_statistical_anomalies(df_enhanced, days)
    
    # 3. 異常の理由を説明
    def generate_anomaly_explanation(row):
        reasons = []

        # BigQueryフラグによる判定理由
        if row.get(f'is_red_hot_ba_{days}days'):
            reasons.append(f"BA: {row[f'ba_{days}days']:.3f} (BQ flag)")
        if row.get(f'is_red_hot_ops_{days}days'):
            reasons.append(f"OPS: {row[f'ops_{days}days']:.3f} (BQ flag)")
        
        # Z-scoreによる統計的判定理由
        ba_zscore = row.get(f'ba_{days}days_z_score')
        if ba_zscore is not None and abs(ba_zscore) > CONFIG.z_score_threshold:
            reasons.append(f"BA Z-score: {ba_zscore:.2f}σ")
        
        ops_zscore = row.get(f'ops_{days}days_z_score')
        if ops_zscore is not None and abs(ops_zscore) > CONFIG.z_score_threshold:
            reasons.append(f"OPS Z-score: {ops_zscore:.2f}σ")
        
        return " | ".join(reasons) if reasons else "N/A"
    
    df_enhanced['anomaly_explanation'] = df_enhanced.apply(generate_anomaly_explanation, axis=1)

    return df_enhanced


# ============== Step 3: Identify anomalies on players performance ==============
def identify_performance_anomalies(query_date: str, days: int) -> Dict[str, Any]:
    """
    指定された日付に基づいて、打者のパフォーマンス異常を特定します。

    検知方法:
    1. BigQuery Viewのフラグ（±20%閾値）
    2. Z-scoreベースの統計的分析（2σ閾値）
    3. 両方を組み合わせた総合判定
    
    Args:
        query_date: クエリ対象の日付
        days: ローリング期間（7 or 15）
    
    Returns:
        異常検知結果の辞書
    """
    anomalies_data = get_batter_performance_flags(query_date, days=days)

    if not anomalies_data:
        logger.warning(f"No data found for {query_date}, {days} days")
        return {
            "red_hot_batters_summary": pd.DataFrame(),
            "slump_batters_summary": pd.DataFrame(),
            "metadata": {
                "query_date": query_date,
                "days": days,
                "total_players": 0
            }
        }
    
    df = pd.DataFrame(anomalies_data)

    # デバッグ: is_red_hot_ba_7days フラグの値を確認
    logger.debug(f"DEBUG: is_red_hot_ba_{days}days value counts:")
    logger.debug(f"{df[f'is_red_hot_ba_{days}days'].value_counts()}")
    logger.debug(f"DEBUG: is_red_hot_ba_{days}days dtype: {df[f'is_red_hot_ba_{days}days'].dtype}")

    df = enhance_performance_data(df, days)

    # ===== Red Hot選手の抽出 =====
    # BigQueryフラグ OR 統計的異常フラグで判定
    if CONFIG.enable_statistical_analysis and 'is_statistical_red_hot_ba' in df.columns:
        red_hot_mask = (
            (df[f'is_red_hot_ba_{days}days'] == True) |
            (df['is_statistical_red_hot_ba'] == True)
        )
    else:
        red_hot_mask = (df[f'is_red_hot_ba_{days}days'] == True)

    logger.debug(f"DEBUG: Red hot mask sum: {red_hot_mask.sum()}")

    red_hot_batters = df[red_hot_mask].copy()

    # 統計的指標とBQスコアで並び替え
    # 優先順位: 1) 異常指標の数 2) BQスコア 3) BA
    if not red_hot_batters.empty:
        sort_cols = []
        if 'anomaly_indicator_count' in red_hot_batters.columns:
            sort_cols.append('anomaly_indicator_count')
        sort_cols.append('bq_anomaly_score')
        sort_cols.append(f'ops_{days}days')

        red_hot_batters = red_hot_batters.sort_values(by=sort_cols, ascending=False).head(CONFIG.top_n_players)
    
    # ===== Slump選手の抽出 =====
    if CONFIG.enable_statistical_analysis and 'is_statistical_slump_ba' in df.columns:
        slump_mask = (
            (df[f'is_slump_ba_{days}days'] == True) | 
            (df['is_statistical_slump_ba'] == True)
        )
    else:
        slump_mask = df[f'is_slump_ba_{days}days'] == True
    
    slump_batters = df[slump_mask].copy()
    
    if not slump_batters.empty:
        slump_batters = slump_batters.sort_values(
            by=f'ba_{days}days',
            ascending=True
        ).head(CONFIG.top_n_players)

    # ===== 表示用カラムの選択 =====
    base_cols = [
        'batter_name', 'team', 'age',
        f'ba_{days}days', f'ops_{days}days', f'hrs_{days}days',
        f'barrels_percentage_{days}days', f'hard_hit_percentage_{days}days'
    ]

    enhanced_cols = ['bq_anomaly_score']

    if CONFIG.enable_statistical_analysis:
        stat_cols = [
            'max_zscore_metric',
            'anomaly_indicator_count',
            f'ba_{days}days_z_score',
            f'ops_{days}days_z_score',
            'anomaly_explanation'
        ]
        enhanced_cols.extend([col for col in stat_cols if col in df.columns])

    display_cols = base_cols + enhanced_cols

    # カラム名の変更
    rename_map = {
        'batter_name': 'Name',
        'team': 'Team',
        'age': 'Age',
        f'ba_{days}days': f'BA ({days}d)',
        f'ops_{days}days': f'OPS ({days}d)',
        f'hrs_{days}days': f'HR ({days}d)',
        f'barrels_percentage_{days}days': f'Barrels % ({days}d)',
        f'hard_hit_percentage_{days}days': f'Hard Hit % ({days}d)',
        'bq_anomaly_score': 'BQ Score',
        f'ba_{days}days_zscore': 'BA Z-score',
        f'ops_{days}days_zscore': 'OPS Z-score',
        'max_zscore_metric': 'Top Anomaly',
        'anomaly_indicator_count': 'Anomaly Count',
        'anomaly_explanation': 'Detection Reason'
    }

    red_hot_summary = red_hot_batters[[col for col in display_cols if col in red_hot_batters.columns]]\
        .rename(columns=rename_map).reset_index(drop=True)
    
    slump_summary = slump_batters[[col for col in display_cols if col in slump_batters.columns]]\
        .rename(columns=rename_map).reset_index(drop=True)
    
    return {
        "red_hot_batters_summary": red_hot_summary,
        "slump_batters_summary": slump_summary,
        "metadata": {
            "query_date": query_date,
            "days": days,
            "total_players": len(df),
            "total_red_hot": len(red_hot_batters),
            "total_slump": len(slump_batters),
            "detection_method": [
                'BigQuery View (20% threshold)',
                f'Z-score Statistical Analysis ({CONFIG.z_score_threshold}sigma)' if CONFIG.enable_statistical_analysis else None
            ]
        }
    }


# ============== Step 4: Display summaries and insights ==============
def display_performance_insights(performace_data: Dict[str, Any]) -> None:
    """
    パフォーマンス異常の概要を表示します。
    """
    red_hot_summary = performance_data.get("red_hot_batters_summary")
    slump_summary = performance_data.get("slump_batters_summary")
    metadata = performance_data.get("metadata", {})
    
    print("\n" + "="*120)
    print(f"Performance Anomaly Detection Report")
    print(f"Date: {metadata.get('query_date')}, Rolling Period: {metadata.get('days')} days")
    print(f"Total Players: {metadata.get('total_players')}")
    print(f"Detection Methods: {', '.join([m for m in metadata.get('detection_method', []) if m])}")
    print("="*120)

    print("\n" + "="*120)
    print(f"=== Red Hot Batters (Total: {metadata.get('total_red_hot', 0)}) ===")
    print("="*120)
    if not red_hot_summary.empty:
        print(red_hot_summary.to_string(index=False))
    else:
        print("No red hot batters found.")

    print("\n" + "="*120)
    print(f"=== Slumping Batters (Total: {metadata.get('total_slump', 0)}) ===")
    print("="*120)
    if not slump_summary.empty:
        print(slump_summary.to_string(index=False))
    else:
        print("No slumping batters found.")
    
    print("\n" + "="*120 + "\n")

# ============== Main Execution ==============
if __name__ == "__main__":
    query_date = "2025-09-01"  # Example date, replace with desired date
    days = 7  # or 15 for 15-day analysis

    performance_data = identify_performance_anomalies(query_date, days)
    display_performance_insights(performance_data)