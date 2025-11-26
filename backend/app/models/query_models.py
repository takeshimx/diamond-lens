"""
クエリ関連のデータモデル
型安全性を向上させ、バリデーションを一元化する
"""
from dataclasses import dataclass, field
from typing import List, Optional, Literal
from enum import Enum

class QueryType(str, Enum):
    """クエリタイプの列挙型（タイポ防止）"""
    SEASON_BATTING = "season_batting"
    SEASON_PITCHING = "season_pitching"
    BATTING_SPLITS = "batting_splits"
    CAREER_BATTING = "career_batting"


class SplitType(str, Enum):
    """状況別分類の列挙型（タイポ防止）"""
    RISP = "risp"
    BASES_LOADED = "bases_loaded"
    RUNNER_ON_1B = "runner_on_1b"
    INNING = "inning"
    PITCHER_THROWS = "pitcher_throws"
    PITCH_TYPE = "pitch_type"
    GAME_SCORE_SITUATION = "game_score_situation"
    MONTHLY = "monthly"


class OutputFormat(str, Enum):
    """出力形式の列挙型"""
    SENTENCE = "sentence"
    TABLE = "table"

@dataclass
class QueryParams:
    """
    LLMから抽出されたクエリパラメータ
    
    デフォルト値とバリデーションを一元管理することで、
    関数間での値の受け渡しが型安全になる
    """
    query_type: Optional[QueryType] = None
    metrics: List[str] = field(default_factory=list)
    season: Optional[int] = None
    name: Optional[str] = None
    split_type: Optional[SplitType] = None
    inning: Optional[List[int]] = None
    strikes: Optional[int] = None
    balls: Optional[int] = None
    game_score: Optional[str] = None
    pitcher_throws: Optional[str] = None
    pitch_type: Optional[List[str]] = None
    order_by: Optional[str] = None
    limit: Optional[int] = None
    output_format: OutputFormat = OutputFormat.SENTENCE

    @classmethod
    def from_dict(cls, data: dict) -> "QueryParams":
        """
        辞書からQueryParamsインスタンスを生成
        LLMのJSON出力を直接変換するためのヘルパーメソッド
        """
        # Enumへの変換処理
        if "query_type" in data and data["query_type"]:
            data["query_type"] = QueryType(data["query_type"])
        
        if "split_type" in data and data["split_type"]:
            data["split_type"] = SplitType(data["split_type"])
        
        if "output_format" in data and data["output_format"]:
            data["output_format"] = OutputFormat(data["output_format"])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class QueryResponse:
    """
    クエリレスポンスの統一モデル
    """
    answer: str
    is_table: bool
    table_data: Optional[List[dict]] = None
    columns: Optional[List[dict]] = None
    decimal_columns: Optional[List[str]] = None
    is_transposed: bool = False
    grouping: Optional[dict] = None
    chart_data: Optional[dict] = None