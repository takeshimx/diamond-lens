"""
Platoon Advantage Mismatch Detection Script

対左右投手別のパフォーマンス差を統計的に検出し、
極端なプラトーン効果（Contextual Mismatch）を特定します。

分析内容:
1. 対右投手(RHP) vs 対左投手(LHP)のwOBA差を計算
2. Z-scoreでリーグ平均との乖離を評価
3. 統計的に有意な不一致を検出
"""

from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import numpy as np
from dataclasses import dataclass
from backend.app.services.base import (
        client, logger,
        PROJECT_ID, DATASET_ID
    )


# =============== Configuration ===============
@dataclass
class PlatoonConfig:
    """プラトーンミスマッチ検出の設定"""
    z_score_threshold: float = 1.5  # Zスコアの閾値
    min_pa: int = 30  # 最小打席数（対RHP/LHP別）
    top_n_players: int = 10 # 上位N選手を抽出

CONFIG = PlatoonConfig()


# =============== Step 1: Fetch Platoon Data from BigQuery ===============
def get_platoon_splits_data(season: int) -> Optional[pd.DataFrame]:
    """
    対左右投手別のパフォーマンスデータをBigQueryから取得します。
    
    Args:
        season: 対象シーズン（例: 2025）
    
    Returns:
        プラトーン統計のDataFrame、エラー時はNone
    """
    query = f"""
    WITH batter_matchups AS (
      SELECT
        batter,
        stand,
        p_throws,
        COUNT(*) AS pa_count,
        AVG(woba_value) AS avg_woba
      FROM `{PROJECT_ID}.{DATASET_ID}.statcast_{season}`
      WHERE events IS NOT NULL
        AND woba_value IS NOT NULL
      GROUP BY batter, stand, p_throws
      HAVING pa_count >= {CONFIG.min_pa}
    ),
    platoon_comparison AS (
        SELECT
            advantagous.batter,
            CONCAT(dim.first_name, ' ', dim.last_name) AS batter_name,
            advantagous.stand AS batter_stand,
            advantagous.avg_woba AS advantagous_woba,
            advantagous.pa_count AS advantagous_pa,
            disadvantagous.avg_woba AS disadvantagous_woba,
            disadvantagous.pa_count AS disadvantagous_pa,
            advantagous.avg_woba - disadvantagous.avg_woba AS platoon_advantage
        FROM batter_matchups AS advantagous
        INNER JOIN batter_matchups AS disadvantagous
            ON advantagous.batter = disadvantagous.batter
            AND advantagous.stand = disadvantagous.stand
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.dim_players` dim
            ON advantagous.batter = dim.mlb_id
        WHERE
            -- advantagous matchups
            (advantagous.stand = 'L' AND advantagous.p_throws = 'R'
            OR advantagous.stand = 'R' AND advantagous.p_throws = 'L')

            -- disadvantagous matchups
            AND (disadvantagous.stand = 'L' AND disadvantagous.p_throws = 'L'
            OR disadvantagous.stand = 'R' AND disadvantagous.p_throws = 'R')
    )
    SELECT *
    FROM platoon_comparison
    WHERE batter_name IS NOT NULL
    ORDER BY platoon_advantage DESC
    """

    logger.debug(f"Executing Platoon Splits Query for season {season}")

    try:
        df = client.query(query).to_dataframe()
        logger.debug(f"Fetcheed {len(df)} records (batter x pitcher_hand combinations)")

        if df.empty:
            logger.warning(f"No platoon data found for season {season}")
            return None
        
        return df
    
    except GoogleCloudError as e:
        logger.error(f"BigQuery query failed: {e}")
        return None


# =============== Step 2: Pivot Data (RHP vs LHP) ===============
def pivot_platoon_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    対RHP/LHP別にデータを横展開します。
    
    Args:
        df: BigQueryから取得した縦持ちデータ
    
    Returns:
        横展開されたDataFrame（1選手1行）
    """
    # 対RHPと対LHPのデータを分離
    df_rhp = df[df['p_throws'] == 'R'][['batter_id', 'batter_name', 'batter_stand', 'pa', 'woba']].copy()
    df_rhp.columns = ['batter_id', 'batter_name', 'batter_stand', 'pa_vs_rhp', 'woba_vs_rhp']

    df_lhp = df[df['p_throws'] == 'L'][['batter_id', 'batter_name', 'batter_stand', 'pa', 'woba']].copy()
    df_lhp.columns = ['batter_id', 'batter_name', 'batter_stand', 'pa_vs_lhp', 'woba_vs_lhp']

    # merge
    df_merged = pd.merge(df_rhp, df_lhp, on=['batter_id', 'batter_name', 'batter_stand'], how='inner')

    logger.debug(f"After pivot: {len(df_merged)} players with data vs both RHP and LHP")
    
    return df_merged


# =============== Step 3: Calculate Platoon Advantage ===============
def calculate_platoon_advantage(df: pd.DataFrame) -> pd.DataFrame:
    """
    プラトーンアドバンテージを計算します。
    
    Args:
        df: ピボット済みのDataFrame
    
    Returns:
        プラトーンアドバンテージが追加されたDataFrame
    """
    df_platoon = df.copy()

    # wOBA差の絶対値
    df_platoon['woba_diff_abs'] = abs(df_platoon['woba_vs_rhp'] - df_platoon['woba_vs_lhp'])

    # プラトーンアドバンテージ（有利な対戦 - 不利な対戦）
    def calc_advantage(row):
        if row['batter_stand'] == 'R': # 右打者: 有利なのは対LHP
            return row['woba_vs_lhp'] - row['woba_vs_rhp']
        elif row['batter_stand'] == 'L': # 左打者: 有利なのは対RHP
            return row['woba_vs_rhp'] - row['woba_vs_lhp']
        else: # スイッチヒッター等
            return max(row['woba_vs_rhp'], row['woba_vs_lhp']) - min(row['woba_vs_rhp'], row['woba_vs_lhp'])
    
    df_platoon['platoon_advantage'] = df_platoon.apply(calc_advantage, axis=1)

    return df_platoon


# =============== Step 4: Statistical Analysis (Z-score) ===============
def calculate_platoon_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """
    プラトーンアドバンテージのZ-scoreを計算します。
    
    Args:
        df: プラトーンアドバンテージが計算済みのDataFrame
    
    Returns:
        Z-scoreが追加されたDataFrame
    """
    df_zscore = df.copy()

    # プラトーンアドバンテージのZ-score
    valid_data = df_zscore['platoon_advantage'].dropna()

    if len(valid_data) > 1:
        mean_adv = valid_data.mean()
        std_adv = valid_data.std()

        if std_adv > 0:
            df_zscore['platoon_advantage_zscore'] = (df_zscore['platoon_advantage'] - mean_adv) / std_adv
        else:
            df_zscore['platoon_advantage_zscore'] = 0
    else:
        df_zscore['platoon_advantage_zscore'] = 0
    
    # Mismatch Flag
    df_zscore['is_extreme_platoon'] = df_zscore['platoon_advantage_zscore'].abs() > CONFIG.z_score_threshold

    return df_zscore


# =============== Step 5: Identify Mismatches ===============
def identify_platoon_mismatches(season: int) -> Dict[str, Any]:
    """
    プラトーンミスマッチを特定します。
    
    Args:
        season: 対象シーズン
    
    Returns:
        ミスマッチ検出結果の辞書
    """

    df = get_platoon_splits_data(season)

    if df is None or df.empty:
        return {
            'extreme_platoon_summary': pd.DataFrame(),
            'balanced_hitters_summary': pd.DataFrame(),
            'metadata': {
                'season': season,
                'total_players': 0
            }
        }
    
    # Calculate Z-scores (platoon_advantageは既にSQLで計算済み)
    df = calculate_platoon_zscore(df)

    # デバッグ: データ件数確認
    logger.info(f"Total players after Z-score calculation: {len(df)}")
    logger.info(f"Players with is_extreme_platoon=True: {len(df[df['is_extreme_platoon'] == True])}")
    logger.info(f"Z-score > 2.0: {len(df[df['platoon_advantage_zscore'].abs() > 2.0])}")

    # ビジネス視点でのグルーピング
    # 1. セオリー通り極端グループ (platoon_advantage > 0)
    extreme_favorable = df[
        (df['is_extreme_platoon'] == True) & (df['platoon_advantage'] > 0)
    ].copy()

    # 2. 逆セオリーグループ (platoon_advantage < 0)
    extreme_unfavorable = df[
        (df['is_extreme_platoon'] == True) & (df['platoon_advantage'] < 0)
    ].copy()

    logger.info(f"Extreme favorable count: {len(extreme_favorable)}")
    logger.info(f"Extreme unfavorable count: {len(extreme_unfavorable)}")

    # 3. バランスグループ
    balanced = df[
        (df['is_extreme_platoon'] == False) & (df['platoon_advantage'].abs() < 0.050)
    ].copy()

    if not extreme_favorable.empty:
        extreme_favorable = extreme_favorable.sort_values(
            by='platoon_advantage_zscore',
            ascending=False
        ).head(10)

    if not extreme_unfavorable.empty:
        extreme_unfavorable = extreme_unfavorable.sort_values(
            by='platoon_advantage_zscore',
            ascending=True
        ).head(10)

    if not balanced.empty:
        balanced = balanced.sort_values(
            by='platoon_advantage',
            ascending=True,
            key=abs
        ).head(10)

    # カラム表示設定
    display_cols = [
        'batter_name', 'batter_stand',
        'advantagous_pa', 'advantagous_woba',
        'disadvantagous_pa', 'disadvantagous_woba',
        'platoon_advantage', 'platoon_advantage_zscore'
    ]

    rename_map = {
        'batter_name': 'Name',
        'batter_stand': 'Bats',
        'advantagous_pa': 'PA (Favorable)',
        'advantagous_woba': 'wOBA (Favorable)',
        'disadvantagous_pa': 'PA (Unfavorable)',
        'disadvantagous_woba': 'wOBA (Unfavorable)',
        'platoon_advantage': 'Platoon Adv',
        'platoon_advantage_zscore': 'Z-score'
    }

    extreme_favorable_summary = extreme_favorable[display_cols].rename(columns=rename_map).reset_index(drop=True)
    extreme_unfavorable_summary = extreme_unfavorable[display_cols].rename(columns=rename_map).reset_index(drop=True)
    balanced_summary = balanced[display_cols].rename(columns=rename_map).reset_index(drop=True)

    return {
        'extreme_favorable_summary': extreme_favorable_summary,
        'extreme_unfavorable_summary': extreme_unfavorable_summary,
        'balanced_hitters_summary': balanced_summary,
        'metadata': {
            'season': season,
            'total_players': len(df),
            'extreme_favorable_count': len(extreme_favorable),
            'extreme_unfavorable_count': len(extreme_unfavorable),
            'balanced_count': len(balanced),
            'z_score_threshold': CONFIG.z_score_threshold
        }
    }

# =============== Step 6: Display Results ===============
def display_platoon_mismatch_insights(results: Dict[str, Any]) -> None:
    """
    プラトーンミスマッチの分析結果を表示します。
    """
    extreme_favorable = results['extreme_favorable_summary']
    extreme_unfavorable = results['extreme_unfavorable_summary']
    balanced = results['balanced_hitters_summary']
    metadata = results.get('metadata', {})

    print("\n" + "="*120)
    print("Platoon Advantage Mismatch Detection Report")
    print(f"Season: {metadata.get('season')}, Total Players: {metadata.get('total_players')}")
    print(f"Z-score Threshold: {metadata.get('z_score_threshold')}σ")
    print("="*120)

    print("\n" + "="*120)
    print(f"=== Extreme Platoon (Theory-Consistent) - Total: {metadata.get('extreme_favorable_count', 0)} ===")
    print("Strong vs opposite-handed pitchers, weak vs same-handed pitchers")
    print("="*120)
    if not extreme_favorable.empty:
        print(extreme_favorable.to_string(index=False))
    else:
        print("No extreme platoon players found.")

    print("\n" + "="*120)
    print(f"=== Reverse Platoon (Theory-Inconsistent) - Total: {metadata.get('extreme_unfavorable_count', 0)} ===")
    print("Strong vs same-handed pitchers, weak vs opposite-handed pitchers")
    print("="*120)
    if not extreme_unfavorable.empty:
        print(extreme_unfavorable.to_string(index=False))
    else:
        print("No reverse platoon players found.")

    print("\n" + "="*120)
    print(f"=== Balanced Hitters (No Mismatch) - Top 10 ===")
    print("="*120)
    if not balanced.empty:
        print(balanced.to_string(index=False))
    else:
        print("No balanced hitters found.")

    print("\n" + "="*120 + "\n")


# =============== Main Execution ===============
if __name__ == "__main__":

    season = 2025

    results = identify_platoon_mismatches(season)
    display_platoon_mismatch_insights(results)
