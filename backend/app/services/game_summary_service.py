"""
LAD試合終了サマリー自動生成・Discord投稿サービス

フロー:
  1. /live/games/today の final リストから LAD 試合を検出
  2. GCS で投稿済み game_pk をチェック（重複防止）
  3. boxscore を取得して Gemini でサマリー生成
  4. Discord Webhook に投稿
  5. GCS に投稿済みマーカーを保存
"""

import json
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from google.cloud import storage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.app.config.settings import get_settings
from backend.app.services.live_game_service import LiveGameService

settings = get_settings()

LAD_TEAM_NAME = "Dodgers"
GCS_PREFIX = "lad_game_summaries"


class GameSummaryService:
    def __init__(self):
        self.live_service = LiveGameService()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.7,
        )
        self.gcs_client = storage.Client()
        self.bucket = self.gcs_client.bucket(settings.gcs_bucket_name)

    # ===== GCS 重複投稿防止 =====

    def _is_posted(self, game_pk: int) -> bool:
        blob = self.bucket.blob(f"{GCS_PREFIX}/{game_pk}.done")
        return blob.exists()

    def _mark_posted(self, game_pk: int, summary: str):
        blob = self.bucket.blob(f"{GCS_PREFIX}/{game_pk}.done")
        blob.upload_from_string(
            json.dumps({"game_pk": game_pk, "summary": summary}),
            content_type="application/json",
        )

    # ===== LAD 試合検出 =====

    async def _find_lad_final_games(self, date: str = None) -> list:
        if date:
            all_games = await self.live_service.get_final_games_by_date(date)
        else:
            data = await self.live_service.get_today_live_games()
            all_games = data.get("final", [])
        return [
            g for g in all_games
            if LAD_TEAM_NAME in g.get("home_team", "")
            or LAD_TEAM_NAME in g.get("away_team", "")
        ]

    # ===== Gemini サマリー生成 =====

    async def _generate_summary(self, game: dict, boxscore: dict) -> str:
        lad_side = "home" if LAD_TEAM_NAME in game.get("home_team", "") else "away"
        opp_side = "away" if lad_side == "home" else "home"

        lad_score = game["home_score"] if lad_side == "home" else game["away_score"]
        opp_score = game["away_score"] if lad_side == "home" else game["home_score"]
        opp_team  = game["away_team"]  if lad_side == "home" else game["home_team"]

        lad_data = boxscore.get(lad_side, {})
        opp_data = boxscore.get(opp_side, {})

        # 先発投手（リストの先頭）
        lad_sp = lad_data.get("pitchers", [{}])[0] if lad_data.get("pitchers") else {}
        opp_sp = opp_data.get("pitchers", [{}])[0] if opp_data.get("pitchers") else {}

        # HR打者
        hr_batters = [b for b in lad_data.get("batters", []) if (b.get("hr") or 0) > 0]
        hr_text = ", ".join(f"{b['name']}({b['hr']}HR)" for b in hr_batters) or "なし"

        # マルチヒット打者（上位3名）
        multi_hit = [b for b in lad_data.get("batters", []) if (b.get("h") or 0) >= 2]
        multi_text = ", ".join(f"{b['name']}({b['h']}H {b.get('rbi',0)}RBI)" for b in multi_hit[:3]) or "なし"

        result = "勝利 🎉" if lad_score > opp_score else "敗北 😢"

        prompt = f"""以下のLADの試合結果を、スポーツニュース風の簡潔な日本語サマリー（3行以内）にしてください。
過剰な絵文字・応援コメント・次戦への一言は不要です。事実を淡々と伝えてください。

【結果】LAD {result} {lad_score} - {opp_score} vs {opp_team}
【LAD先発】{lad_sp.get('name','N/A')} {lad_sp.get('ip','?')}IP {lad_sp.get('k',0)}K {lad_sp.get('er',0)}ER
【相手先発】{opp_sp.get('name','N/A')} {opp_sp.get('ip','?')}IP {opp_sp.get('k',0)}K {opp_sp.get('er',0)}ER
【HR】{hr_text}
【マルチヒット】{multi_text}"""

        response = self.llm.invoke(prompt)
        return response.content

    # ===== Discord 投稿 =====

    async def _post_to_discord(self, summary: str, game: dict):
        if not settings.discord_webhook_url_lad:
            return

        lad_side  = "home" if LAD_TEAM_NAME in game.get("home_team", "") else "away"
        lad_score = game["home_score"] if lad_side == "home" else game["away_score"]
        opp_score = game["away_score"] if lad_side == "home" else game["home_score"]
        opp_team  = game["away_team"]  if lad_side == "home" else game["home_team"]
        won = lad_score > opp_score

        jst_now = datetime.now(ZoneInfo("Asia/Tokyo"))
        jst_str = jst_now.strftime("%Y/%m/%d %H:%M JST")

        payload = {
            "username": "Diamond Lens ⚾",
            "embeds": [{
                "title": f"{'✅' if won else '❌'} LAD {lad_score} - {opp_score} {opp_team} | 試合終了",
                "description": summary,
                "color": 0x005A9C,  # Dodger Blue
                "footer": {"text": f"Diamond Lens | Powered by Gemini | {jst_str}"},
            }],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.discord_webhook_url_lad, json=payload)
            resp.raise_for_status()

    # ===== メイン実行 =====

    async def run(self, date: str = None) -> dict:
        """LAD終了試合を検知し、未投稿のものだけサマリーをDiscordへ投稿"""
        lad_games = await self._find_lad_final_games(date)

        if not lad_games:
            return {"processed": 0, "results": [], "message": "No LAD final games today"}

        results = []
        for game in lad_games:
            game_pk = game["gamePk"]

            if self._is_posted(game_pk):
                results.append({"game_pk": game_pk, "status": "skipped (already posted)"})
                continue

            try:
                boxscore = await self.live_service.get_boxscore(game_pk)
                summary  = await self._generate_summary(game, boxscore)
                await self._post_to_discord(summary, game)
                self._mark_posted(game_pk, summary)
                results.append({"game_pk": game_pk, "status": "posted", "summary": summary})
            except Exception as e:
                results.append({"game_pk": game_pk, "status": "error", "detail": str(e)})

        return {"processed": len(results), "results": results}
