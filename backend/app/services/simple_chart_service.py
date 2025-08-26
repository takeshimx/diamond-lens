from typing import Dict, Any, List, Optional
import pandas as pd
from .bigquery_service import client
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 環境変数から設定を読み込む
load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID")


class SimpleChartService:
    """シンプルなチャート用データを準備するサービス"""

    @staticmethod
    def prepare_monthly_chart_from_data(data_df: pd.DataFrame, player_name: str, season: int, metric: str = "batting_average") -> Dict[str, Any]:
        """
        既存のデータフレームから月別チャート用のデータを準備します。

        Args:
            data_df (pd.DataFrame): 既存の月別データ
            player_name (str): 選手の名前  
            season (int): シーズン年
            metric (str): 表示するメトリクス

        Returns:
            Dict[str, Any]: チャート用のデータ辞書
        """
        try:
            if data_df.empty:
                logger.warning(f"No monthly data provided for {player_name} in {season}")
                return None

            # Convert to month names
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            # Convert to chart data format
            chart_data = []
            for _, row in data_df.iterrows():
                month_num = row.get('month', row.get('game_month', 1))
                month_name = month_names[int(month_num) - 1] if pd.notna(month_num) and 1 <= int(month_num) <= 12 else f"Month {int(month_num)}"
                
                metric_value = row.get(metric, 0)
                if pd.notna(metric_value):
                    chart_data.append({
                        "month": month_name,
                        metric: round(float(metric_value), 3)
                    })
            
            # Sort by month order
            month_order = {month: i for i, month in enumerate(month_names)}
            chart_data.sort(key=lambda x: month_order.get(x["month"], 12))
            
            # Configure chart based on metric
            metric_configs = {
                "batting_average": {
                    "title": f"{player_name} Monthly Batting Average in {season}",
                    "lineName": "Batting Average",
                    "lineColor": "#3B82F6",
                    "yDomain": [0, 0.600]
                },
                "homerun": {
                    "title": f"{player_name} Monthly Home Runs in {season}", 
                    "lineName": "Home Runs",
                    "lineColor": "#EF4444",
                    "yDomain": [0, "auto"]
                },
                "rbi": {
                    "title": f"{player_name} Monthly RBIs in {season}",
                    "lineName": "RBIs", 
                    "lineColor": "#10B981",
                    "yDomain": [0, "auto"]
                }
            }
            
            config = metric_configs.get(metric, metric_configs["batting_average"])
            
            chart_config = {
                "title": config["title"],
                "xAxis": "month",
                "dataKey": metric,
                "lineName": config["lineName"],
                "lineColor": config["lineColor"],
                "yDomain": config["yDomain"]
            }

            return {
                "isChart": True,
                "chartType": "line", 
                "chartData": chart_data,
                "chartConfig": chart_config
            }
        
        except Exception as e:
            logger.error(f"Error preparing monthly chart from data: {e}")
            return None

def should_show_simple_chart(query: str) -> bool:
    """シンプルなチャート表示が適切かどうか判断"""
    chart_keywords = ["推移", "チャート", "グラフ", "月別", "月ごと", "月次", "月間"]
    batting_keywords = ["打率", "ホームラン", "打点", "出塁率", "OBP", "長打率", "SLG", "OPS"]

    # boolean flags
    has_chart_keyword = any(keyword in query for keyword in chart_keywords)
    has_batting_keyword = any(keyword in query for keyword in batting_keywords)

    return has_chart_keyword and has_batting_keyword


def enhance_response_with_simple_chart(
        query: str,
        query_params: Dict[str, Any],
        data_df: Optional[pd.DataFrame] = None,
        season: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """既存のレスポンスにシンプルなチャートデータを追加"""
    
    # チャート表示判定
    if not should_show_simple_chart(query):
        return None
    
    player_name = query_params.get("name")
    if not player_name or data_df is None or data_df.empty:
        return None
    
    # Check if this is monthly data (split_type should be "monthly")
    split_type = query_params.get("split_type")
    if split_type != "monthly":
        return None
    
    # Determine the metric from the query
    metric = "batting_average"  # default
    if "ホームラン" in query or "homerun" in str(query_params.get("metrics", [])):
        metric = "homerun"
    elif "打点" in query or "rbi" in str(query_params.get("metrics", [])):
        metric = "rbi"
    elif "打率" in query or "batting_average" in str(query_params.get("metrics", [])):
        metric = "batting_average"
    
    # Generate chart data from existing dataframe
    chart_result = SimpleChartService.prepare_monthly_chart_from_data(
        data_df, player_name, season or 2024, metric
    )
    
    return chart_result









