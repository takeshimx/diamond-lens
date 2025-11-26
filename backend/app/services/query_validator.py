"""
クエリパラメータのバリデーションとセキュリティチェック
SQLインジェクション対策などを一元管理
"""
import re
import logging
from typing import Dict, Any
from backend.app.config.query_maps import METRIC_MAP

logger = logging.getLogger(__name__)


class QueryValidator:
    """クエリパラメータのバリデーター"""

    # クラス変数として定数を定義
    VALID_QUERY_TYPES = ["season_batting", "season_pitching", "batting_splits", "career_batting"]
    VALID_SPLIT_TYPES = [
        "risp", "bases_loaded", "runner_on_1b", "inning",
        "pitcher_throws", "pitch_type", "game_score_situation", "monthly"
    ]
    VALID_PITCHER_THROWS = ["RHP", "LHP"]
    VALID_OUTPUT_FORMATS = ["sentence", "table"]

    # SQLインジェクション検出用キーワード
    SQL_KEYWORDS = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'UNION', 'WHERE', 'OR', 'AND', '--', '/*', '*/',
        'EXEC', 'EXECUTE', 'SCRIPT', 'JAVASCRIPT', 'EVAL'
    ]

    def __init__(self):
        """バリデーターの初期化"""
        pass

    def validate(self, params: Dict[str, Any]) -> bool:
        """
        パラメータの包括的なバリデーション
        
        Args:
            params: 検証するパラメータ辞書
        
        Returns:
            全てのバリデーションに合格した場合True
        """
        validators = [
            self._validate_name,
            self._validate_season,
            self._validate_query_type,
            self._validate_split_type,
            self._validate_metrics,
            self._validate_order_by,
            self._validate_pitcher_throws,
            self._validate_inning,
            self._validate_strikes_balls,
            self._validate_pitch_type,
            self._validate_game_score,
            self._validate_limit,
            self._validate_output_format,
        ]

        for validator in validators:
            if not validator(params):
                return False
        
        logger.info("✅ Query parameters validation passed")
        return True
    
    def _validate_name(self, params: Dict[str, Any]) -> bool:
        """選手名のバリデーション"""
        if not params.get("name"):
            return True
        
        name = params["name"]
        
        # 英字、スペース、ピリオド、ハイフン、アポストロフィのみ許可
        if not re.match(r"^[A-Za-z\s\.\-']+$", name):
            logger.warning(f"⚠️ Invalid name format: {name}")
            return False
        
        # 長さ制限
        if len(name) > 100:
            logger.warning(f"⚠️ Name too long: {len(name)} characters")
            return False
        
        # SQLキーワード検出
        name_upper = name.upper()
        for keyword in self.SQL_KEYWORDS:
            if keyword in name_upper:
                logger.warning(f"⚠️ SQL keyword detected in name: {name}")
                return False
        
        return True
    
    def _validate_season(self, params: Dict[str, Any]) -> bool:
        """シーズンのバリデーション"""
        if params.get("season") is None:
            return True
        
        season = params["season"]
        
        if not isinstance(season, int):
            logger.warning(f"⚠️ Season must be integer: {season}")
            return False
        
        if not (1900 <= season <= 2100):
            logger.warning(f"⚠️ Invalid season range: {season}")
            return False
        
        return True
    
    def _validate_query_type(self, params: Dict[str, Any]) -> bool:
        """クエリタイプのバリデーション"""
        if not params.get("query_type"):
            return True
        
        if params["query_type"] not in self.VALID_QUERY_TYPES:
            logger.warning(f"⚠️ Invalid query_type: {params['query_type']}")
            return False
        
        return True
    
    def _validate_split_type(self, params: Dict[str, Any]) -> bool:
        """split_typeのバリデーション"""
        if not params.get("split_type"):
            return True
        
        if params["split_type"] not in self.VALID_SPLIT_TYPES:
            logger.warning(f"⚠️ Invalid split_type: {params['split_type']}")
            return False
        
        return True
    
    def _validate_metrics(self, params: Dict[str, Any]) -> bool:
        """メトリクスのバリデーション"""
        if not params.get("metrics"):
            return True
        
        metrics = params["metrics"]
        
        if not isinstance(metrics, list):
            logger.warning(f"⚠️ Metrics must be list: {metrics}")
            return False
        
        # "main_stats"は特殊キーワードなので許可
        if metrics == ["main_stats"]:
            return True
        
        # 各メトリックがMETRIC_MAPに存在するかチェック
        for metric in metrics:
            if metric not in METRIC_MAP and metric != "main_stats":
                logger.warning(f"⚠️ Invalid metric: {metric}")
                return False
        
        return True
    
    def _validate_order_by(self, params: Dict[str, Any]) -> bool:
        """order_byのバリデーション"""
        if not params.get("order_by"):
            return True
        
        order_by = params["order_by"]
        
        if order_by not in METRIC_MAP:
            logger.warning(f"⚠️ Invalid order_by: {order_by}")
            return False
        
        return True
    
    def _validate_pitcher_throws(self, params: Dict[str, Any]) -> bool:
        """pitcher_throwsのバリデーション"""
        if not params.get("pitcher_throws"):
            return True
        
        pitcher_throws = params["pitcher_throws"]
        
        if pitcher_throws not in self.VALID_PITCHER_THROWS:
            logger.warning(f"⚠️ Invalid pitcher_throws: {pitcher_throws}")
            return False
        
        return True
    
    def _validate_inning(self, params: Dict[str, Any]) -> bool:
        """イニングのバリデーション"""
        if params.get("inning") is None:
            return True
        
        inning = params["inning"]
        
        # リストまたは整数
        if isinstance(inning, list):
            for inn in inning:
                if not isinstance(inn, int) or not (1 <= inn <= 9):
                    logger.warning(f"⚠️ Invalid inning in list: {inn}")
                    return False
        elif isinstance(inning, int):
            if not (1 <= inning <= 9):
                logger.warning(f"⚠️ Invalid inning: {inning}")
                return False
        else:
            logger.warning(f"⚠️ Inning must be int or list: {inning}")
            return False
        
        return True
    
    def _validate_strikes_balls(self, params: Dict[str, Any]) -> bool:
        """ストライク・ボールカウントのバリデーション"""
        if params.get("strikes") is not None:
            strikes = params["strikes"]
            if not isinstance(strikes, int) or not (0 <= strikes <= 3):
                logger.warning(f"⚠️ Invalid strikes: {strikes}")
                return False
        
        if params.get("balls") is not None:
            balls = params["balls"]
            if not isinstance(balls, int) or not (0 <= balls <= 3):
                logger.warning(f"⚠️ Invalid balls: {balls}")
                return False
        
        return True
    
    def _validate_pitch_type(self, params: Dict[str, Any]) -> bool:
        """球種のバリデーション"""
        if not params.get("pitch_type"):
            return True
        
        pitch_types = params["pitch_type"]
        
        if not isinstance(pitch_types, list):
            logger.warning(f"⚠️ pitch_type must be list: {pitch_types}")
            return False
        
        for pt in pitch_types:
            if not isinstance(pt, str) or not re.match(r"^[A-Za-z\s\-]+$", pt):
                logger.warning(f"⚠️ Invalid pitch_type: {pt}")
                return False
            
            if len(pt) > 50:
                logger.warning(f"⚠️ pitch_type too long: {pt}")
                return False
        
        return True
    
    def _validate_game_score(self, params: Dict[str, Any]) -> bool:
        """ゲームスコアのバリデーション"""
        if not params.get("game_score"):
            return True
        
        valid_game_scores = [
            'one_run_game', 'one_run_lead', 'one_run_trail',
            'two_run_game', 'two_run_lead', 'two_run_trail',
            'three_run_game', 'three_run_lead', 'three_run_trail',
            'four_plus_run_game', 'four_plus_run_lead', 'four_plus_run_trail',
            'tie_game'
        ]
        
        if params["game_score"] not in valid_game_scores:
            logger.warning(f"⚠️ Invalid game_score: {params['game_score']}")
            return False
        
        return True
    
    def _validate_limit(self, params: Dict[str, Any]) -> bool:
        """LIMIT句のバリデーション"""
        if params.get("limit") is None:
            return True
        
        limit = params["limit"]
        
        if not isinstance(limit, int):
            logger.warning(f"⚠️ limit must be integer: {limit}")
            return False
        
        if not (1 <= limit <= 1000):
            logger.warning(f"⚠️ Invalid limit range: {limit}")
            return False
        
        return True
    
    def _validate_output_format(self, params: Dict[str, Any]) -> bool:
        """出力形式のバリデーション"""
        if not params.get("output_format"):
            return True
        
        if params["output_format"] not in self.VALID_OUTPUT_FORMATS:
            logger.warning(f"⚠️ Invalid output_format: {params['output_format']}")
            return False
        
        return True