"""
リファクタリング版AIサービス
元のai_service.pyと同じ機能を、クラスベースで再構成
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd
from google.cloud.exceptions import GoogleCloudError

# 新しく作成したクラスをインポート
from backend.app.models.query_models import QueryParams, QueryResponse
from backend.app.services.llm_client import GeminiClient
from backend.app.services.query_validator import QueryValidator
from backend.app.services.query_builder import QueryBuilder
from backend.app.config.query_maps import DECIMAL_FORMAT_COLUMNS

logger = logging.getLogger(__name__)


class AIService:
    """
    LLMベースのクエリ処理サービス
    
    元の get_ai_response_for_qna_enhanced 関数の機能を
    クラスベースで再構成し、テスト容易性と保守性を向上
    """
    def __init__(
        self,
        gemini_api_key: str,
        bigquery_client,
        project_id: str,
        dataset_id: str
    ):
        """
        Args:
            gemini_api_key: Gemini APIキー
            bigquery_client: BigQueryクライアント
            project_id: GCPプロジェクトID
            dataset_id: BigQueryデータセットID
        """
        self.bq_client = bigquery_client
        self.project_id = project_id
        self.dataset_id = dataset_id

        # 各コンポーネントを初期化
        self.llm_client = GeminiClient(gemini_api_key)
        self.validator = QueryValidator()
        self.query_builder = QueryBuilder(project_id, dataset_id)
    
    def process_query(
        self,
        query: str,
        season: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        ユーザークエリを処理してレスポンスを生成
        
        元の get_ai_response_for_qna_enhanced と同じ処理フロー:
        1. LLMでクエリをパース
        2. パラメータをバリデーション
        3. SQLクエリを構築
        4. BigQueryでデータ取得
        5. レスポンスをフォーマット
        
        Args:
            query: ユーザーの自然言語クエリ
            season: オプションのシーズン指定
        
        Returns:
            レスポンス辞書（answer, isTable, tableDataなど）
        """
        # Step 1: LLMでクエリをパース
        params_dict = self.llm_client.parse_query(query, season)
        if not params_dict:
            logger.warning("Could not extract parameters from the query.")
            return {
                "answer": "質問を理解できませんでした。打撃成績のランキングについて質問してください。（例：2024年のホームラン王は誰？）",
                "isTable": False
            }
        
        logger.info(f"Parsed query parameters: {params_dict}")

        # パラメータをデータクラスに変換
        try:
            query_params = QueryParams.from_dict(params_dict)
        except Exception as e:
            logger.error(f"Failed to convert params to QueryParams: {e}")
            return {
                "answer": "クエリパラメータの変換に失敗しました。",
                "isTable": False
            }
        
        # Step 2: セキュリティバリデーション
        if not self.validator.validate(params_dict):
            logger.error(f"Security validation failed for parameters: {params_dict}")
            return {
                "answer": "不正な入力を検出しました。正しい形式で質問してください。",
                "isTable": False
            }
        
        # Step 3: SQLクエリを構築
        sql_query, sql_parameters = self.query_builder.build_query(params_dict)
        if not sql_query:
            logger.warning("Failed to build SQL query.")
            return {
                "answer": "この質問に対応するデータの検索クエリを構築できませんでした。",
                "isTable": False
            }
        
        logger.info(f"Generated SQL query:\n{sql_query}")
        logger.info(f"Query parameters: {sql_parameters}")

        # Step 4: BigQueryでデータ取得
        try:
            results_df = self._execute_bigquery(sql_query, sql_parameters)
        except GoogleCloudError as e:
            logger.error(f"BigQuery query failed: {e}", exc_info=True)
            error_message = self._format_bigquery_error(e)
            return {
                "answer": error_message,
                "isTable": False
            }
        
        if results_df.empty:
            return {
                "answer": "指定された条件に一致するデータが見つかりませんでした。条件を変更して再試行してください。",
                "isTable": False
            }
        
        # Step 5: レスポンスをフォーマット
        return self._format_response(params_dict, results_df, query)
    
    def _execute_bigquery(
        self,
        sql_query: str,
        sql_parameters: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        BigQueryクエリを実行してDataFrameを返す
        
        元のコードの Step 3 部分に対応
        
        Args:
            sql_query: パラメータ化されたSQL文字列
            sql_parameters: クエリパラメータ
        
        Returns:
            クエリ結果のDataFrame
        
        Raises:
            GoogleCloudError: BigQuery実行エラー
        """
        # BigQuery用のJobConfigを構築
        job_config = self.query_builder.build_job_config(sql_parameters)
        
        # クエリ実行
        query_start = datetime.now()
        results_df = self.bq_client.query(sql_query, job_config=job_config).to_dataframe()
        query_duration = (datetime.now() - query_start).total_seconds()
        
        logger.info(f"Query completed in {query_duration:.2f}s, fetched {len(results_df)} rows")
        
        # パフォーマンス警告
        if query_duration > 10:
            logger.warning(f"Slow query detected: {query_duration:.2f}s")
        
        return results_df
    
    def _format_bigquery_error(self, error: GoogleCloudError) -> str:
        """
        BigQueryエラーをユーザーフレンドリーなメッセージに変換
        
        Args:
            error: BigQueryエラーオブジェクト
        
        Returns:
            ユーザー向けエラーメッセージ
        """
        error_message = "データベースからのデータ取得中にエラーが発生しました。"
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            error_message += "クエリがタイムアウトしました。条件を絞って再試行してください。"
        elif "quota" in error_str:
            error_message += "利用制限に達しました。しばらくしてから再試行してください。"
        
        return error_message
    
    def _format_response(
        self,
        params: Dict[str, Any],
        results_df: pd.DataFrame,
        original_query: str
    ) -> Dict[str, Any]:
        """
        DataFrameをレスポンス形式に変換
        
        元のコードの Step 4 部分に対応
        
        Args:
            params: クエリパラメータ
            results_df: BigQuery結果
            original_query: 元のユーザークエリ
        
        Returns:
            フォーマット済みレスポンス辞書
        """
        output_format = params.get("output_format", "sentence")
        
        # テーブル形式の場合
        if output_format == "table":
            return self._format_table_response(params, results_df)
        
        # 文章形式の場合
        else:
            return self._format_sentence_response(params, results_df, original_query)
    
    def _format_table_response(
        self,
        params: Dict[str, Any],
        results_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        テーブル形式のレスポンスを生成
        
        元のコードの output_format == "table" 部分に対応
        
        Args:
            params: クエリパラメータ
            results_df: BigQuery結果
        
        Returns:
            テーブル形式のレスポンス辞書
        """
        logger.info(f"DataFrame columns: {results_df.columns.tolist()}")
        logger.info(f"DataFrame dtypes: {results_df.dtypes.to_dict()}")
        
        # 小数点カラムの型変換
        decimal_columns = DECIMAL_FORMAT_COLUMNS
        for col in decimal_columns:
            if col in results_df.columns:
                results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
                results_df[col] = results_df[col].where(pd.notnull(results_df[col]), None)
        
        # 辞書に変換
        table_data = results_df.to_dict('records')
        
        # 小数点フォーマット処理
        for row in table_data:
            for col in decimal_columns:
                if col in row and row[col] is not None:
                    try:
                        value = float(row[col])
                        if not pd.isna(value):
                            row[col] = round(value, 3)
                        else:
                            row[col] = None
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert {col} value {row[col]} to float: {e}")
        
        logger.info(f"Final table_data sample: {table_data[0] if table_data else 'No data'}")
        
        # カラム定義
        columns = [
            {"key": col, "label": col.replace('_', ' ').title()} 
            for col in results_df.columns
        ]
        
        # 単一行の場合は転置表示
        is_single_row = len(results_df) == 1
        
        # キャリア打撃の場合はグルーピング情報を追加
        grouping_info = None
        if params.get("query_type") == "career_batting":
            grouping_info = self._build_career_batting_grouping(results_df)
        
        return {
            "answer": f"以下は{len(results_df)}件の結果です：",
            "isTable": True,
            "isTransposed": is_single_row,
            "tableData": table_data,
            "columns": columns,
            "decimalColumns": [col for col in results_df.columns if col in DECIMAL_FORMAT_COLUMNS],
            "grouping": grouping_info
        }
    
    def _build_career_batting_grouping(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        キャリア打撃成績のグルーピング情報を構築
        
        Args:
            results_df: 結果DataFrame
        
        Returns:
            グルーピング情報辞書
        """
        base_columns = [
            col for col in results_df.columns 
            if col in ['name', 'batter_name', 'career_last_team']
        ]
        career_base_columns = [
            col for col in results_df.columns 
            if col.startswith('career_') and '_at_' not in col and '_by_' not in col
        ]
        risp_columns = [
            col for col in results_df.columns 
            if '_at_risp' in col
        ]
        bases_loaded_columns = [
            col for col in results_df.columns 
            if '_at_bases_loaded' in col
        ]
        
        return {
            "type": "career_batting_chunks",
            "groups": [
                {
                    "name": "Career Stats",
                    "columns": base_columns + career_base_columns
                },
                {
                    "name": "Career RISP Stats",
                    "columns": risp_columns
                },
                {
                    "name": "Career Bases Loaded Stats",
                    "columns": bases_loaded_columns
                }
            ]
        }
    
    def _format_sentence_response(
        self,
        params: Dict[str, Any],
        results_df: pd.DataFrame,
        original_query: str
    ) -> Dict[str, Any]:
        """
        文章形式のレスポンスを生成
        
        元のコードの output_format == "sentence" 部分に対応
        
        Args:
            params: クエリパラメータ
            results_df: BigQuery結果
            original_query: 元のユーザークエリ
        
        Returns:
            文章形式のレスポンス辞書
        """
        logger.info("Generating narrative response with LLM.")
        final_response = self.llm_client.generate_narrative_response(
            original_query, 
            results_df
        )
        
        # チャート機能との統合（既存のsimple_chart_serviceを利用）
        try:
            from backend.app.services.simple_chart_service import enhance_response_with_simple_chart
            
            chart_data = enhance_response_with_simple_chart(
                original_query, 
                params, 
                results_df, 
                params.get("season")
            )
            
            if chart_data:
                response = {
                    "answer": "📈",  # チャート表示用
                    "isTable": False
                }
                response.update(chart_data)
                return response
        except Exception as e:
            logger.warning(f"Chart enhancement failed: {e}")
        
        # 通常のテキストレスポンス
        return {
            "answer": final_response,
            "isTable": False
        }
    
# ============================================================
# 後方互換性のためのラッパー関数
# 既存のエンドポイントコードを変更せずに使用できるようにする
# ============================================================

def get_ai_response_for_qna_enhanced(
    query: str, 
    season: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    後方互換性のためのラッパー関数
    
    元のai_service.pyの関数と同じシグネチャを維持しつつ、
    内部では新しいAIServiceクラスを使用する
    
    Args:
        query: ユーザーの自然言語クエリ
        season: オプションのシーズン指定
    
    Returns:
        レスポンス辞書
    """
    from backend.app.config.settings import get_settings
    from backend.app.services.base import get_bq_client

    # 設定を取得
    settings = get_settings()
    
    # AIServiceのインスタンスを作成
    ai_service = AIService(
        gemini_api_key=settings.gemini_api_key,
        bigquery_client=get_bq_client(),
        project_id=settings.gcp_project_id,
        dataset_id=settings.bigquery_dataset_id
    )
    
    # 処理を実行
    return ai_service.process_query(query, season)


def get_ai_response_with_simple_chart(
    query: str, 
    season: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    チャート対応版の後方互換ラッパー関数
    
    Args:
        query: ユーザーの自然言語クエリ
        season: オプションのシーズン指定
    
    Returns:
        レスポンス辞書
    """
    # 現在の実装では process_query 内でチャート統合を行っているため、
    # 同じ関数を呼び出すだけ
    return get_ai_response_for_qna_enhanced(query, season)