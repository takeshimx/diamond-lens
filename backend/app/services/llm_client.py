"""
LLM（Gemini）とのやり取りを担当するクライアント
AI処理を独立させることで、将来的にLLMを変更しやすくする
1つのクラスが1つの責務（LLMとの通信）だけを持つように設計
"""
import json
import logging
import requests
from typing import Optional, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini APIとの通信を抽象化するクライアント"""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Args:
            api_key: Gemini APIキー
            model: 使用するモデル名（デフォルトは gemini-2.5-flash）
        """
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    
    def _build_url(self) -> str:
        """API URLを構築
        Helper method to build the full API URL.
        """
        return f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
    
    def _make_request(
            self,
            prompt: str,
            response_mime_type: str = "text/plain",
    ) -> Optional[str]:
        """
        Gemini APIにリクエストを送信。
        Helper method to send a request to the Gemini API.
        
        Args:
            prompt: LLMへのプロンプト
            response_mime_type: レスポンスのMIMEタイプ
        
        Returns:
            LLMからのレスポンステキスト（失敗時はNone）
        """
        url = self._build_url()
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": response_mime_type}
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()

            result = response.json()
            if result.get("candidates"):
                return result["candidates"][0]["content"]["parts"][0]["text"]
            
            logger.warning("No candidates in Gemini response")
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API request failed: {e}", exc_info=True)
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse Gemini response: {e}", exc_info=True)
            return None
    
    def parse_query(self, query: str, season: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        自然言語クエリをパラメータに変換
        
        Args:
            query: ユーザーの質問（例: "2024年のホームラン王は誰？"）
            season: オプションのシーズン指定
        
        Returns:
            抽出されたパラメータの辞書（失敗時はNone）
        """
        prompt = self._build_query_parsing_prompt(query)
        
        json_string = self._make_request(prompt, response_mime_type="application/json")
        if not json_string:
            return None
        
        try:
            params = json.loads(json_string)
            
            # seasonの後処理
            if season and 'season' not in params:
                params['season'] = season
            
            logger.info(f"Parsed parameters: {params}")
            return params
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON output: {e}", exc_info=True)
            return None
    
    def _build_query_parsing_prompt(self, query: str) -> str:
        """
        クエリパース用のプロンプトを構築
        
        Note: 元のai_service.pyの巨大なプロンプトをここに移動
              将来的にはプロンプトテンプレートファイルに外部化することも検討
        """
        return f"""
        あなたはMLBのデータアナリストです。ユーザーからの"打撃成績のランキング"、"投手成績のランキング"、または"選手成績"に関する以下の質問を解析し、
        データベースで検索するためのパラメータをJSON形式で抽出してください。

        # 指示
        - 選手名は英語表記（フルネーム）に正規化してください。例：「大谷さん」 -> "Shohei Ohtani"
        - `season`は、ユーザーの質問から年を抽出してください。`season`が指定されていない場合、または「キャリア」や「通算」などの表現があれば、`season`はnullにしてください。
        - `query_type`は "season_batting"、"season_pitching"、 "batting_splits"、または "career_batting" のいずれかを選択してください。
        - `metrics`には、ユーザーが知りたい指標をリスト形式で格納してください。例えば、ホームラン数を知りたい場合は ["homerun"] とします。打率の場合は ["batting_average"] とし、単語と単語の間にアンダースコアを使用してください。
        - `split_type`は、「得点圏（RISP）」「満塁」「ランナー1類」「イニング別」「投手が左投げか右投げか」「球種別」「ゲームスコア状況別」などの特定の状況を示します。該当しない場合はnullにしてください。
        - `split_type`で、game_score_situation (ゲームスコア状況別) を選択した場合、`game_score`に具体的なスコア状況（例：1点リード、2点ビハインドなど）を示す必要があります。
            例えば、「1点差ゲーム、1点リード、1点ビハインド」は、'one_run_game'、'one_run_lead'、'one_run_trail'のように表現します。4点以上の差は'four_plus_run_lead'や'four_plus_run_trail'としてください。該当しない場合はnullにしてください。
        - `split_type`で、inning (イニング別) を選択した場合、`inning`に具体的なイニング数をリスト形式で示してください。レギュラーイニング数は1~9イニングまで。例：1イニング目なら [1]、7イニング目以降なら [7, 8, 9] とします。
        - `strikes`は、特定のストライク数を指定します。該当しない場合はnullにしてください。`balls`は、特定のボール数を指定します。該当しない場合はnullにしてください。
        - 例えば、「フルカウント」は、 `strikes`を2、`balls`を3としてください。「初球」は、`strikes`を0、`balls`を0とします。該当しない場合はnullにしてください。
        - `pitcher_throws`は、投手の投げ方（右投げまたは左投げ）を示します。右投げはRHP、左投げはLHPとし、該当しない場合はnullにしてください。
        - ユーザーが「主要スタッツ」や「主な成績」のような曖昧な表現を使った場合、metricsには ["main_stats"] というキーワードを一つだけ格納してください。
        - `order_by`には、ランキングの基準となる指標を一つだけ設定してください。
        - `output_format`では、デフォルトは "sentence" です。もしユーザーの質問に『表で』『一覧で』『まとめて』といったような言葉が含まれていたら、output_formatをtableに設定してください。そうでなければsentenceにしてください。

        # JSONスキーマ
        {{
            "query_type": "season_batting" | "season_pitching" | "batting_splits" | "career_batting" | null,
            "metrics": ["string"],
            "split_type": "risp" | "bases_loaded" | "runner_on_1b" | "inning" | "pitcher_throws" | "pitch_type" | "game_score_situation" | "monthly" | null,
            "inning": ["integer"] | null,
            "strikes": "integer | null",
            "balls": "integer | null",
            "game_score": "string | null",
            "pitcher_throws": "string | null",
            "pitch_type": ["string"] | null,
            "name": "string | null",
            "season": "integer | null",
            "order_by": "string",
            "limit": "integer | null",
            "output_format": "sentence" | "table"
        }}

        # 質問の例
        質問: 「2023年のホームラン王は誰？」
        JSON: {{ "query_type": "season_batting", "season": 2023, "metrics": ["homerun"],  "order_by": "homerun", "limit": 1 }}

        質問: 「大谷さんの2024年のRISP時の主要スタッツは？」
        JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "risp", "order_by": null, "limit": 1 }}

        質問: 「大谷さんのの2024年の1イニング目のホームラン数とOPSを教えて」
        JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["homerun", "on_base_plus_slugging"], "split_type": "inning", "inning": 1, "order_by": null, "limit": 1 }}

        質問: 「大谷さんの2024年の左投手に対する主要スタッツを一覧で教えて？」
        JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "pitcher_throws", "pitcher_throws": "LHP", "order_by": null, "limit": 1, "output_format": "table" }}

        質問: 「大谷さんの2024年のスライダーに対する主要スタッツは？」
        JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "pitch_type", "pitch_type": "Slider", "order_by": null }}

        質問: 「大谷さんのキャリア主要打撃成績を一覧で教えて」
        JSON: {{ "query_type": "career_batting", "name": "Shohei Ohtani", "metrics": ["main_stats"], "order_by": null, "limit": 1, "output_format": "table" }}

        質問: 「大谷さんの2024年の、1点ビハインドでの主要スタッツは？」
        JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "game_score_situation", "game_score": "one_run_trail", "order_by": null, "limit": 1 }}

        質問: 「大谷さんの2024年の打率を月毎の推移をチャートで教えて」
        JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["batting_average"], "split_type": "monthly", "order_by": null }}

        # 複合質問の例
        質問: 「大谷さんの2024年の7イニング目以降、フルカウントでの、RISP時の主要スタッツは？」
        JSON: {{ "query_type": "batting_splits", "name": "Shohei Ohtani", "season": 2024,  "metrics": ["main_stats"], "split_type": "risp", "inning": [7, 8, 9], "strikes": 2, "balls": 3, "order_by": null, "limit": 1 }}

        # 本番
        質問: 「{query}」
        JSON:
        """
    
    def generate_narrative_response(
        self, 
        original_query: str, 
        data_df: pd.DataFrame
    ) -> str:
        """
        データフレームから自然言語の回答を生成
        
        Args:
            original_query: 元のユーザー質問
            data_df: BigQueryから取得したデータ
        
        Returns:
            自然言語の回答文
        """
        data_json_str = data_df.to_json(orient='records', indent=2, force_ascii=False)
        
        prompt = f"""
        あなたはMLBのデータアナリストです。以下のデータに基づいて、ユーザーの質問に簡潔に日本語で回答してください。
        データは表形式で提示するのではなく、自然な文章で説明してください。

        ---
        ユーザーの質問: {original_query}
        提供データ (JSON形式):
        {data_json_str}
        ---
        回答:
        """
        
        response = self._make_request(prompt)
        if not response:
            return "AIによる回答を生成できませんでした。"
        
        # 改行をHTMLのbrタグに変換
        return response.replace('\n', '<br>')
