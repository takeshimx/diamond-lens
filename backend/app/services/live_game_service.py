import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

MLB_BASE = "https://statsapi.mlb.com"


class LiveGameService:

    async def get_today_live_games(self) -> Dict:
        """
        本日の試合情報を返す
        - live: 進行中試合の詳細（投手・打者・カウント・走者・投球シーケンス）
        - final: 終了試合のスコアサマリー
        """
        today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        live_pks, final_games = await self._get_schedule(today)

        if live_pks:
            tasks = [self._fetch_game_state(pk) for pk in live_pks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            live_games = [r for r in results if not isinstance(r, Exception) and r]
        else:
            live_games = []

        return {"live": live_games, "final": final_games}

    async def _get_schedule(self, date: str) -> Tuple[List[int], List[Dict]]:
        """指定日のスケジュールから Live の gamePk リストと Final のサマリーを返す"""
        url = f"{MLB_BASE}/api/v1/schedule"
        params = {"sportId": 1, "date": date, "hydrate": "linescore"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        live_pks = []
        final_games = []
        for date_obj in data.get("dates", []):
            for game in date_obj.get("games", []):
                state = game.get("status", {}).get("abstractGameState", "")
                away = game.get("teams", {}).get("away", {})
                home = game.get("teams", {}).get("home", {})
                if state == "Live":
                    live_pks.append(game["gamePk"])
                elif state == "Final":
                    final_games.append({
                        "gamePk": game["gamePk"],
                        "away_team": away.get("team", {}).get("name", ""),
                        "home_team": home.get("team", {}).get("name", ""),
                        "away_score": away.get("score", 0),
                        "home_score": home.get("score", 0),
                    })
        return live_pks, final_games

    async def _fetch_game_state(self, game_pk: int) -> Optional[Dict]:
        """単一試合のライブフィードから現在状態を整形して返す"""
        url = f"{MLB_BASE}/api/v1.1/game/{game_pk}/feed/live"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        game_data = data.get("gameData", {})
        live_data = data.get("liveData", {})
        # チーム情報
        teams = game_data.get("teams", {})
        home_team = teams.get("home", {}).get("teamName", "")
        away_team = teams.get("away", {}).get("teamName", "")
        # ラインスコア（スコア・イニング・カウント）
        linescore = live_data.get("linescore", {})
        home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
        away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)
        inning = linescore.get("currentInning", 0)
        inning_half = linescore.get("inningHalf", "")
        outs = linescore.get("outs", 0)
        balls = linescore.get("balls", 0)
        strikes = linescore.get("strikes", 0)
        # 現在のプレイ（投手・打者）
        current_play = live_data.get("plays", {}).get("currentPlay", {})
        matchup = current_play.get("matchup", {})
        pitcher_name = matchup.get("pitcher", {}).get("fullName", "N/A")
        batter_name = matchup.get("batter", {}).get("fullName", "N/A")
        # 現在の投球結果テキスト
        play_result = current_play.get("result", {})
        last_event = play_result.get("event", "")
        last_description = play_result.get("description", "")
        # 走者情報（塁上の走者名）
        offense = linescore.get("offense", {})
        runners = {
            "first": offense.get("first", {}).get("fullName"),
            "second": offense.get("second", {}).get("fullName"),
            "third": offense.get("third", {}).get("fullName"),
        }
        # 打席内の全投球シーケンス（投球のみ抽出、古い順）
        play_events = current_play.get("playEvents", [])
        pitch_sequence = []
        pitch_num = 1
        for event in play_events:
            if not event.get("isPitch", False):
                continue
            pitch_data = event.get("pitchData", {})
            details = event.get("details", {})
            speed = pitch_data.get("startSpeed")
            pitch_sequence.append({
                "num": pitch_num,
                "pitch_type": details.get("type", {}).get("description"),
                "pitch_call": details.get("description"),
                "speed": round(speed, 1) if speed is not None else None,
            })
            pitch_num += 1
        last_pitch = pitch_sequence[-1] if pitch_sequence else {}
        return {
            "gamePk": game_pk,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "inning": inning,
            "inning_half": inning_half,
            "outs": outs,
            "balls": balls,
            "strikes": strikes,
            "pitcher": pitcher_name,
            "batter": batter_name,
            "last_event": last_event,
            "last_description": last_description,
            "runners": runners,
            "last_pitch": last_pitch,
            "pitch_sequence": pitch_sequence,
            "abstract_game_state": "Live",
        }
