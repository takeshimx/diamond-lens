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
        from datetime import timedelta
        # JST基準: JST日付 - 1日 = MLBのET日付（全試合がJST翌朝に開始するため）
        mlb_date = (datetime.now(ZoneInfo("Asia/Tokyo")) - timedelta(days=1)).strftime("%Y-%m-%d")
        live_pks, final_games, preview_games = await self._get_schedule(mlb_date)

        if live_pks:
            tasks = [self._fetch_game_state(pk) for pk in live_pks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            live_games = [r for r in results if not isinstance(r, Exception) and r]
        else:
            live_games = []

        return {"live": live_games, "final": final_games, "preview": preview_games}

    async def _get_schedule(self, date: str) -> Tuple[List[int], List[Dict], List[Dict]]:
        """指定日のスケジュールから Live の gamePk リスト、Final、Preview のサマリーを返す"""
        url = f"{MLB_BASE}/api/v1/schedule"
        params = {"sportId": 1, "date": date, "hydrate": "linescore"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        jst = ZoneInfo("Asia/Tokyo")
        live_pks = []
        final_games = []
        preview_games = []
        for date_obj in data.get("dates", []):
            for game in date_obj.get("games", []):
                state = game.get("status", {}).get("abstractGameState", "")
                away = game.get("teams", {}).get("away", {})
                home = game.get("teams", {}).get("home", {})
                if state == "Live":
                    live_pks.append(game["gamePk"])
                elif state == "Preview":
                    away_rec = away.get("leagueRecord", {})
                    home_rec = home.get("leagueRecord", {})
                    game_date_str = game.get("gameDate", "")
                    try:
                        from datetime import timezone as tz
                        utc_dt = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                        jst_dt = utc_dt.astimezone(jst)
                        start_time = jst_dt.strftime("%H:%M")
                    except Exception:
                        start_time = "--:--"
                    preview_games.append({
                        "gamePk": game["gamePk"],
                        "away_team": away.get("team", {}).get("name", ""),
                        "home_team": home.get("team", {}).get("name", ""),
                        "away_wins": away_rec.get("wins"),
                        "away_losses": away_rec.get("losses"),
                        "home_wins": home_rec.get("wins"),
                        "home_losses": home_rec.get("losses"),
                        "start_time_jst": start_time,
                    })
                elif state == "Final":
                    away_rec = away.get("leagueRecord", {})
                    home_rec = home.get("leagueRecord", {})
                    final_games.append({
                        "gamePk": game["gamePk"],
                        "away_team": away.get("team", {}).get("name", ""),
                        "home_team": home.get("team", {}).get("name", ""),
                        "away_team_id": away.get("team", {}).get("id"),
                        "home_team_id": home.get("team", {}).get("id"),
                        "away_score": away.get("score", 0),
                        "home_score": home.get("score", 0),
                        "away_wins": away_rec.get("wins"),
                        "away_losses": away_rec.get("losses"),
                        "home_wins": home_rec.get("wins"),
                        "home_losses": home_rec.get("losses"),
                    })
        return live_pks, final_games, preview_games

    async def get_scheduled_games(self, date: str) -> list:
        """指定日（JST）の予定試合一覧（開始時刻JST付き）を返す"""
        from datetime import timedelta
        # date はフロントエンドからのJST日付。MLBのET日付に変換するため -1日
        mlb_date = (datetime.fromisoformat(date) - timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"{MLB_BASE}/api/v1/schedule"
        params = {"sportId": 1, "date": mlb_date}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        jst = ZoneInfo("Asia/Tokyo")
        games = []
        for date_obj in data.get("dates", []):
            for game in date_obj.get("games", []):
                away = game.get("teams", {}).get("away", {})
                home = game.get("teams", {}).get("home", {})
                game_date_str = game.get("gameDate", "")
                # UTC → JST変換
                try:
                    from datetime import timezone
                    utc_dt = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                    jst_dt = utc_dt.astimezone(jst)
                    start_time = jst_dt.strftime("%H:%M")
                except Exception:
                    start_time = "--:--"

                away_rec = away.get("leagueRecord", {})
                home_rec = home.get("leagueRecord", {})
                games.append({
                    "gamePk": game["gamePk"],
                    "away_team": away.get("team", {}).get("name", ""),
                    "home_team": home.get("team", {}).get("name", ""),
                    "away_team_id": away.get("team", {}).get("id"),
                    "home_team_id": home.get("team", {}).get("id"),
                    "away_score": away.get("score", 0),
                    "home_score": home.get("score", 0),
                    "away_wins": away_rec.get("wins"),
                    "away_losses": away_rec.get("losses"),
                    "home_wins": home_rec.get("wins"),
                    "home_losses": home_rec.get("losses"),
                    "start_time_jst": start_time,
                    "status": game.get("status", {}).get("abstractGameState", ""),
                })
        return games

    async def get_daily_highlights(self, date: str) -> List[Dict]:
        """指定日（JST）の全試合からハイライトを抽出して返す"""
        from datetime import timedelta
        mlb_date = (datetime.fromisoformat(date) - timedelta(days=1)).strftime("%Y-%m-%d")

        url = f"{MLB_BASE}/api/v1/schedule"
        params = {"sportId": 1, "date": mlb_date}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        final_pks = []
        for date_obj in data.get("dates", []):
            for game in date_obj.get("games", []):
                state = game.get("status", {}).get("abstractGameState", "")
                if state == "Final":
                    final_pks.append(game["gamePk"])

        if not final_pks:
            return []

        tasks = [self._fetch_boxscore_highlights(pk) for pk in final_pks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        highlights = []
        for r in results:
            if not isinstance(r, Exception) and r:
                highlights.extend(r)

        highlights.sort(key=lambda h: h["priority"], reverse=True)
        return [{"text": h["text"]} for h in highlights]

    async def _fetch_boxscore_highlights(self, game_pk: int) -> List[Dict]:
        """単一試合のboxscoreからハイライト条件に合う記録を抽出する"""
        url = f"{MLB_BASE}/api/v1/game/{game_pk}/boxscore"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        highlights = []
        teams = data.get("teams", {})

        for side in ("away", "home"):
            team_data = teams.get(side, {})
            abbr = team_data.get("team", {}).get("abbreviation", "")
            players = team_data.get("players", {})

            # 打者ルール
            for pid in team_data.get("batters", []):
                p = players.get(f"ID{pid}", {})
                stats = p.get("stats", {}).get("batting", {})
                name = p.get("person", {}).get("fullName", "")
                hr = stats.get("homeRuns", 0)
                rbi = stats.get("rbi", 0)
                if hr >= 3:
                    highlights.append({"text": f"{hr} HR game — {name} ({abbr})", "priority": 100})
                elif rbi >= 4:
                    highlights.append({"text": f"{rbi} RBI — {name} ({abbr})", "priority": 80})

            # 投手ルール
            for pid in team_data.get("pitchers", []):
                p = players.get(f"ID{pid}", {})
                stats = p.get("stats", {}).get("pitching", {})
                name = p.get("person", {}).get("fullName", "")
                ip_str = stats.get("inningsPitched", "0.0")
                k = stats.get("strikeOuts", 0)
                er = stats.get("earnedRuns", 0)
                try:
                    ip = float(ip_str)
                except (ValueError, TypeError):
                    ip = 0.0

                if ip >= 9.0:
                    label = f"Complete Game Shutout — {name} ({abbr})" if er == 0 else f"Complete Game — {name} ({abbr})"
                    highlights.append({"text": label, "priority": 95 if er == 0 else 90})
                elif ip >= 7.0 and er == 0:
                    highlights.append({"text": f"Shutout ({ip_str} IP) — {name} ({abbr})", "priority": 85})
                if k >= 10:
                    highlights.append({"text": f"{k} K — {name} ({abbr})", "priority": 75})

        return highlights

    async def get_boxscore(self, game_pk: int) -> Dict:
        """終了試合のボックススコア（投手・野手スタッツ）を返す"""
        url = f"{MLB_BASE}/api/v1/game/{game_pk}/boxscore"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        teams = data.get("teams", {})
        result = {}
        for side in ("away", "home"):
            team_data = teams.get(side, {})
            team_name = team_data.get("team", {}).get("name", "")
            players = team_data.get("players", {})
            pitchers_ids = team_data.get("pitchers", [])
            batters_ids = team_data.get("batters", [])

            def get_player(pid):
                return players.get(f"ID{pid}", {})

            pitchers = []
            for pid in pitchers_ids:
                p = get_player(pid)
                stats = p.get("stats", {}).get("pitching", {})
                season = p.get("seasonStats", {}).get("pitching", {})
                pitchers.append({
                    "name": p.get("person", {}).get("fullName", ""),
                    "jersey": p.get("jerseyNumber", ""),
                    "note": p.get("gameStatus", {}).get("note", ""),
                    "era": season.get("era", "-"),
                    "ip": stats.get("inningsPitched", "-"),
                    "h": stats.get("hits", 0),
                    "r": stats.get("runs", 0),
                    "er": stats.get("earnedRuns", 0),
                    "hr": stats.get("homeRuns", 0),
                    "k": stats.get("strikeOuts", 0),
                    "bb": stats.get("baseOnBalls", 0),
                    "pitches": stats.get("numberOfPitches", 0),
                    "strikes": stats.get("strikes", 0),
                })

            batters = []
            for pid in batters_ids:
                p = get_player(pid)
                stats = p.get("stats", {}).get("batting", {})
                season = p.get("seasonStats", {}).get("batting", {})
                pos = p.get("position", {}).get("abbreviation", "")
                batters.append({
                    "name": p.get("person", {}).get("fullName", ""),
                    "jersey": p.get("jerseyNumber", ""),
                    "position": pos,
                    "avg": season.get("avg", "-"),
                    "obp": season.get("obp", "-"),
                    "slg": season.get("slg", "-"),
                    "ops": season.get("ops", "-"),
                    "ab": stats.get("atBats", 0),
                    "h": stats.get("hits", 0),
                    "r": stats.get("runs", 0),
                    "rbi": stats.get("rbi", 0),
                    "hr": stats.get("homeRuns", 0),
                    "sb": stats.get("stolenBases", 0),
                    "doubles": stats.get("doubles", 0),
                    "triples": stats.get("triples", 0),
                    "bb": stats.get("baseOnBalls", 0),
                    "k": stats.get("strikeOuts", 0),
                })

            result[side] = {"team": team_name, "pitchers": pitchers, "batters": batters}

        return result

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
        pitcher_info = matchup.get("pitcher", {})
        pitcher_name = pitcher_info.get("fullName", "N/A")
        pitcher_id = pitcher_info.get("id")
        batter_info = matchup.get("batter", {})
        batter_name = batter_info.get("fullName", "N/A")
        batter_id = batter_info.get("id")
        # boxscoreのplayersを取得（投手・打者共通で使う）
        bs_teams = live_data.get("boxscore", {}).get("teams", {})
        defense_side = "home" if inning_half == "Top" else "away"
        offense_side = "away" if inning_half == "Top" else "home"

        # 現在の投手のゲームスタッツ
        pitcher_stats = {}
        if pitcher_id:
            bs_players = bs_teams.get(defense_side, {}).get("players", {})
            ps = bs_players.get(f"ID{pitcher_id}", {}).get("stats", {}).get("pitching", {})
            pitcher_stats = {
                "pitches": ps.get("numberOfPitches", 0),
                "ip": ps.get("inningsPitched", "0.0"),
                "k": ps.get("strikeOuts", 0),
                "er": ps.get("earnedRuns", 0),
            }

        # 現在の打者のゲームスタッツ
        batter_stats = {}
        if batter_id:
            bs_players = bs_teams.get(offense_side, {}).get("players", {})
            bs = bs_players.get(f"ID{batter_id}", {}).get("stats", {}).get("batting", {})
            batter_stats = {
                "ab": bs.get("atBats", 0),
                "h": bs.get("hits", 0),
                "rbi": bs.get("rbi", 0),
                "hr": bs.get("homeRuns", 0),
                "sb": bs.get("stolenBases", 0),
                "k": bs.get("strikeOuts", 0),
                "bb": bs.get("baseOnBalls", 0),
            }
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
        # 現投手の今試合の全投球ログ（球種・速度・スピンレート・イニング）
        pitcher_pitch_log = []
        if pitcher_id:
            for play in live_data.get("plays", {}).get("allPlays", []):
                if play.get("matchup", {}).get("pitcher", {}).get("id") != pitcher_id:
                    continue
                play_inning = play.get("about", {}).get("inning", 0)
                for event in play.get("playEvents", []):
                    if not event.get("isPitch", False):
                        continue
                    pd_ = event.get("pitchData", {})
                    det = event.get("details", {})
                    speed = pd_.get("startSpeed")
                    spin  = pd_.get("breaks", {}).get("spinRate")
                    ptype = det.get("type", {}).get("description")
                    if speed and ptype:
                        pitcher_pitch_log.append({
                            "inning":     play_inning,
                            "pitch_type": ptype,
                            "speed":      round(speed, 1),
                            "spin_rate":  round(spin) if spin else None,
                        })

        # この試合のHR情報（打者名 + シーズン本数）
        hr_list = []
        boxscore_teams = live_data.get("boxscore", {}).get("teams", {})
        all_players = {}
        for side in ("home", "away"):
            for pid, pdata in boxscore_teams.get(side, {}).get("players", {}).items():
                all_players[pid] = pdata
        for play in live_data.get("plays", {}).get("allPlays", []):
            if play.get("result", {}).get("event", "") == "Home Run":
                batter = play.get("matchup", {}).get("batter", {})
                batter_id = batter.get("id")
                batter_full = batter.get("fullName", "")
                season_hr = None
                if batter_id:
                    pdata = all_players.get(f"ID{batter_id}", {})
                    season_hr = pdata.get("seasonStats", {}).get("batting", {}).get("homeRuns")
                hr_list.append({
                    "name": batter_full,
                    "season_hr": season_hr,
                })
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
            "pitcher_stats": pitcher_stats,
            "batter": batter_name,
            "batter_stats": batter_stats,
            "last_event": last_event,
            "last_description": last_description,
            "runners": runners,
            "last_pitch": last_pitch,
            "pitch_sequence": pitch_sequence,
            "pitcher_pitch_log": pitcher_pitch_log,
            "hr_list": hr_list,
            "abstract_game_state": "Live",
        }

    async def get_standings(self, season: Optional[int] = None) -> Dict:
        """MLB順位表を返す（AL/NL 各ディビジョン別）"""
        from datetime import date as date_cls
        if season is None:
            season = date_cls.today().year
        url = f"{MLB_BASE}/api/v1/standings"
        params = {
            "leagueId": "103,104",
            "season": season,
            "standingsTypes": "regularSeason",
            "hydrate": "team,league,division,record(splits=[H,A,lastTen])",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        standings = []
        for record in data.get("records", []):
            division_name = record.get("division", {}).get("name", "")
            league_id = record.get("league", {}).get("id")
            league_name = record.get("league", {}).get("name", "")
            teams = []
            for tr in record.get("teamRecords", []):
                splits = {s.get("type", ""): s for s in tr.get("records", {}).get("splitRecords", [])}
                home = splits.get("home", {})
                away = splits.get("away", {})
                last_ten = splits.get("lastTen", {})
                teams.append({
                    "team_name": tr.get("team", {}).get("name", ""),
                    "team_abbrev": tr.get("team", {}).get("abbreviation", ""),
                    "team_id": tr.get("team", {}).get("id"),
                    "wins": tr.get("wins", 0),
                    "losses": tr.get("losses", 0),
                    "win_pct": tr.get("winningPercentage", ".000"),
                    "games_back": tr.get("divisionGamesBack", "-"),
                    "league_games_back": tr.get("leagueGamesBack", "-"),
                    "home_wins": home.get("wins", 0),
                    "home_losses": home.get("losses", 0),
                    "away_wins": away.get("wins", 0),
                    "away_losses": away.get("losses", 0),
                    "last_ten_wins": last_ten.get("wins", 0),
                    "last_ten_losses": last_ten.get("losses", 0),
                    "streak": tr.get("streak", {}).get("streakCode", "-"),
                    "division_rank": tr.get("divisionRank", "-"),
                    "league_rank": tr.get("leagueRank", "-"),
                    "wildcard_rank": tr.get("wildCardRank", "-"),
                    "elimination_number": tr.get("eliminationNumber", "-"),
                    "magic_number": tr.get("magicNumber", "-"),
                })
            standings.append({
                "division_name": division_name,
                "league_id": league_id,
                "league_name": league_name,
                "teams": teams,
            })
        return {"standings": standings, "season": season}
