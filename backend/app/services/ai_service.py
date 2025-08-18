# """
# AI/LLM関連の分析サービス
# Gemini APIを使用した選手パフォーマンス分析、比較分析、Q&A機能
# """
# import json
# import requests
# import pandas as pd
# import numpy as np
# from typing import Optional, Dict, List, Any
# from functools import lru_cache
# from datetime import datetime
# from google.cloud import bigquery
# from backend.app.api.schemas import *
# from .base import (
#     get_bq_client, logger,
#     GEMINI_API_KEY,
# )
# from .player_service import get_player_details, get_ohtani_two_way_stats
# from .statcast_service import get_batter_statcast_data
# from .leaderboard_service import (
#     get_batting_leaderboard,
#     get_batter_split_stats_leaderboard,
#     get_pitching_leaderboard
# )


# def get_ai_response_for_qna(query: str, season: Optional[int] = None) -> Optional[str]:
#     """
#     ユーザーの自然言語クエリに基づいて、打者・投手のリーダーボードデータを取得し、
#     LLMが回答を生成します。
#     ここではシンプルに、特定のシーズン（または最新シーズン）の打者・投手リーダーボードをLLMに渡します。
#     """
#     client = get_bq_client()

#     current_year = datetime.now().year
    
#     # # LLMに渡す格納するリスト
#     # all_batting_leaderboards_for_llm = []
#     # all_pitching_leaderboards_for_llm = []
#     # risp_batting_splits_leaderboards_for_llm = []
#     # bases_loaded_batting_splits_leaderboards_for_llm = []
#     # runner_on_first_batting_splits_leaderboards_for_llm = []
#     # ohtani_two_way_stats_for_llm = []

#     # LLMに渡すデータを格納する辞書
#     data_for_llm = {}

#     # どのリーダーボードが必要かを判断
#     fetch_batting_leaderboard = False
#     fetch_pitching_leaderboard = False
#     fetch_risp_splits = False
#     fetch_bases_loaded_splits = False
#     fetch_runner_on_1b_splits = False
#     fetch_ohtani_two_way = True

#     query_lower = query.lower()

#     if "打者" in query_lower or "ホームラン" in query_lower or "打率" in query_lower or "ops" in query_lower or "rbi" in query_lower or "sb" in query_lower:
#         fetch_batting_leaderboard = True
#     if "投手" in query_lower or "era" in query_lower or "奪三振" in query_lower or "whip" in query_lower or "fip" in query_lower:
#         fetch_pitching_leaderboard = True
#     if "risp" in query_lower or "得点圏" in query_lower or "チャンス" in query_lower:
#         fetch_risp_splits = True
#         fetch_batting_leaderboard = True # RISPなら打者も必要
#     if "満塁" in query_lower or "bases loaded" in query_lower or "チャンス" in query_lower:
#         fetch_bases_loaded_splits = True
#         fetch_batting_leaderboard = True # 満塁なら打者も必要
#     if "1塁" in query_lower or "runner on 1b" in query_lower:
#         fetch_runner_on_1b_splits = True
#         fetch_batting_leaderboard = True # 1塁なら打者も必要
#     # if ("Shohei Ohtani" in query_lower or "大谷翔平" in query_lower) and ("二刀流" in query_lower or "登板日" in query_lower or "翌試合" in query_lower):
#     #     fetch_ohtani_two_way = True

#     # # ★★★ 変更点1: seasonがNoneの場合、過去数年分のリーダーボードデータを取得 ★★★
#     # # 目的: LLMが複数年の質問に答えられるように、関連する複数年のデータを提供する
#     # seasons_to_fetch = []
#     # if season is None: # 「全シーズン」が選択された場合
#     #     # 例として、過去5年分のデータを取得
#     #     seasons_to_fetch = list(range(current_year, current_year - 5, -1))
#     # else: # 特定のシーズンが選択された場合
#     #     seasons_to_fetch = [season]

#     # ★★★ 変更点2: 必要なデータのみをフェッチし、data_for_llmに格納 ★★★
#     seasons_to_fetch_for_leaderboards = []
#     if season is None: # 「全シーズン」が選択された場合
#         seasons_to_fetch_for_leaderboards = list(range(current_year, current_year - 5, -1)) # 過去5年分
#     else:
#         seasons_to_fetch_for_leaderboards = [season]

#     # ========================== Season Batting and Pitching Leaderboards ==========================
#     if fetch_batting_leaderboard:
#         all_batting_leaderboards_for_llm = []
#         for s in seasons_to_fetch_for_leaderboards:
#     # for s in seasons_to_fetch:
#             # 打者リーダーボードの取得
#             batting_leaderboard = get_batting_leaderboard(
#                 season=s,
#                 league="MLB",
#                 min_pa=280, 
#                 metric_order="ops"
#             )
#             if batting_leaderboard:
#                 for player in batting_leaderboard:
#                     all_batting_leaderboards_for_llm.append({
#                         "name": player.name,
#                         "team": player.team,
#                         "season": player.season,
#                         "ops": player.ops,
#                         "hr": player.hr,
#                         "h": player.h,
#                         "r": player.r,
#                         "sb": player.sb,
#                         "bb": player.bb,
#                         "so": player.so,
#                         "avg": player.avg,
#                         "rbi": player.rbi,
#                         "wrcplus": player.wrcplus,
#                         "war": player.war,
#                         "woba": player.woba,
#                         "obp": player.obp,
#                         "slg": player.slg,
#                         "iso": player.iso,
#                         "batting_average_at_risp": player.batting_average_at_risp,
#                         "slugging_percentage_at_risp": player.slugging_percentage_at_risp,
#                         "home_runs_at_risp": player.home_runs_at_risp
#                     })
#         data_for_llm["batting_leaderboard"] = all_batting_leaderboards_for_llm

#     if fetch_pitching_leaderboard:
#         all_pitching_leaderboards_for_llm = []
#         for s in seasons_to_fetch_for_leaderboards:
#             # 投手リーダーボードの取得
#             pitching_leaderboard = get_pitching_leaderboard(
#                 season=s,
#                 league="MLB",
#                 min_ip=50,
#                 metric_order="era"
#             )
#             if pitching_leaderboard:
#                 for player in pitching_leaderboard:
#                     all_pitching_leaderboards_for_llm.append({
#                         "name": player.name,
#                         "team": player.team,
#                         "season": player.season,
#                         "era": player.era,
#                         "so": player.so,
#                         "whip": player.whip,
#                         "fip": player.fip,
#                         "k_9": player.k_9,
#                         "bb_9": player.bb_9,
#                         "k_bb": player.k_bb,
#                         "avg": player.avg,
#                         "war": player.war,
#                         "ip": player.ip,
#                         "hr": player.hr,
#                         "bb": player.bb,
#                         "sv": player.sv,
#                         "r": player.r,
#                         "w": player.w,
#                         "l": player.l,
#                         "h": player.h
#                     })
#         data_for_llm["pitching_leaderboard"] = all_pitching_leaderboards_for_llm

#     # batting_leaderboard_str = "打者リーダーボードデータはありません。"
#     # if all_batting_leaderboards_for_llm:
#     #     batting_leaderboard_str = f"打者リーダーボード:\n{json.dumps(all_batting_leaderboards_for_llm, indent=2, ensure_ascii=False)}"

#     # pitching_leaderboard_str = "投手リーダーボードデータはありません。"
#     # if all_pitching_leaderboards_for_llm:
#     #     pitching_leaderboard_str = f"投手リーダーボード:\n{json.dumps(all_pitching_leaderboards_for_llm, indent=2, ensure_ascii=False)}"
    
#     # ========================== Batting Splits Leaderboards [RISP] ===========================
#     if fetch_risp_splits:
#         risp_batting_splits_leaderboards_for_llm = []
#         for s in seasons_to_fetch_for_leaderboards:
#     # for s in seasons_to_fetch:
#             # 打者のスプリットデータを取得
#             batting_splits_leaderboards_risp = get_batter_split_stats_leaderboard(
#                 season=s,
#                 league="MLB",
#                 min_pa=280,  # 最低打席数を設定
#                 split_type="RISP"  # RISPスプリットを取得
#             )
#             if batting_splits_leaderboards_risp:
#                 for player in batting_splits_leaderboards_risp:
#                     risp_batting_splits_leaderboards_for_llm.append({
#                         "batter_name": player.batter_name,
#                         "game_year": player.game_year,
#                         "team": player.team,
#                         "league": player.league,
#                         "homeruns_at_risp": player.homeruns_at_risp,
#                         "triples_at_risp": player.triples_at_risp,
#                         "doubles_at_risp": player.doubles_at_risp,
#                         "singles_at_risp": player.singles_at_risp,
#                         "hits_at_risp": player.hits_at_risp,
#                         "bb_hbp_at_risp": player.bb_hbp_at_risp,
#                         "avg_at_risp": player.avg_at_risp,
#                         "obp_at_risp": player.obp_at_risp,
#                         "slg_at_risp": player.slg_at_risp,
#                         "ops_at_risp": player.ops_at_risp
#                     })
#         data_for_llm["risp_batting_splits_leaderboard"] = risp_batting_splits_leaderboards_for_llm
                
#     # batting_splits_leaderboard_risp_str = " No RISP batting splits leaderboard data available."
#     # if risp_batting_splits_leaderboards_for_llm:
#     #     batting_splits_leaderboard_risp_str = f"RISP打者スプリットリーダーボード:\n{json.dumps(risp_batting_splits_leaderboards_for_llm, indent=2, ensure_ascii=False)}"

#     # ========================== Batting Splits Leaderboards [Bases Loaded] ===========================
#     if fetch_bases_loaded_splits:
#         bases_loaded_batting_splits_leaderboards_for_llm = []
#         for s in seasons_to_fetch_for_leaderboards:
#     # for s in seasons_to_fetch:
#             # 打者のスプリットデータを取得
#             batting_splits_leaderboards_bases_loaded = get_batter_split_stats_leaderboard(
#                 season=s,
#                 league="MLB",
#                 min_pa=280,  # 最低打席数を設定
#                 split_type="Bases Loaded"  # Bases Loadedスプリットを取得
#             )
#             if batting_splits_leaderboards_bases_loaded:
#                 for player in batting_splits_leaderboards_bases_loaded:
#                     bases_loaded_batting_splits_leaderboards_for_llm.append({
#                         "batter_name": player.batter_name,
#                         "game_year": player.game_year,
#                         "team": player.team,
#                         "league": player.league,
#                         "grandslam": player.grandslam,
#                         "ab_at_bases_loaded": player.ab_at_bases_loaded,
#                         "hits_at_bases_loaded": player.hits_at_bases_loaded,
#                         "doubles_at_bases_loaded": player.doubles_at_bases_loaded,
#                         "triples_at_bases_loaded": player.triples_at_bases_loaded,
#                         "singles_at_bases_loaded": player.singles_at_bases_loaded,
#                         "bb_hbp_at_bases_loaded": player.bb_hbp_at_bases_loaded,
#                         "so_at_bases_loaded": player.so_at_bases_loaded,
#                         "avg_at_bases_loaded": player.avg_at_bases_loaded,
#                         "obp_at_bases_loaded": player.obp_at_bases_loaded,
#                         "slg_at_bases_loaded": player.slg_at_bases_loaded,
#                         "ops_at_bases_loaded": player.ops_at_bases_loaded
#                     })
#         data_for_llm["bases_loaded_batting_splits_leaderboard"] = bases_loaded_batting_splits_leaderboards_for_llm
                
#     # bases_loaded_batting_splits_leaderboard_str = " No Bases Loaded batting splits leaderboard data available."
#     # if bases_loaded_batting_splits_leaderboards_for_llm:
#     #     bases_loaded_batting_splits_leaderboard_str = f"Bases Loaded打者スプリットリーダーボード:\n{json.dumps(bases_loaded_batting_splits_leaderboards_for_llm, indent=2, ensure_ascii=False)}"

#     # ========================== Batting Splits Leaderboards [Runner only on 1st] ===========================
#     if fetch_runner_on_1b_splits:
#         runner_on_first_batting_splits_leaderboards_for_llm = []
#         for s in seasons_to_fetch_for_leaderboards:
#     # for s in seasons_to_fetch:
#             # 打者のスプリットデータを取得
#             batting_splits_leaderboards_1b_only = get_batter_split_stats_leaderboard(
#                 season=s,
#                 league="MLB",
#                 min_pa=280,  # 最低打席数を設定
#                 split_type="Runner on 1B"  # 1塁にランナーのみのスプリットを取得
#             )
#             if batting_splits_leaderboards_1b_only:
#                 for player in batting_splits_leaderboards_1b_only:
#                     runner_on_first_batting_splits_leaderboards_for_llm.append({
#                         "batter_name": player.batter_name,
#                         "game_year": player.game_year,
#                         "team": player.team,
#                         "league": player.league,
#                         "homeruns_at_runner_on_1b": player.homeruns_at_runner_on_1b,
#                         "triples_at_runner_on_1b": player.triples_at_runner_on_1b,
#                         "doubles_at_runner_on_1b": player.doubles_at_runner_on_1b,
#                         "singles_at_runner_on_1b": player.singles_at_runner_on_1b,
#                         "hits_at_runner_on_1b": player.hits_at_runner_on_1b,
#                         "ab_at_runner_on_1b": player.ab_at_runner_on_1b,
#                         "so_at_runner_on_1b": player.so_at_runner_on_1b,
#                         "bb_hbp_at_runner_on_1b": player.bb_hbp_at_runner_on_1b,
#                         "avg_at_runner_on_1b": player.avg_at_runner_on_1b,
#                         "obp_at_runner_on_1b": player.obp_at_runner_on_1b,
#                         "slg_at_runner_on_1b": player.slg_at_runner_on_1b,
#                         "ops_at_runner_on_1b": player.ops_at_runner_on_1b
#                     })
#         data_for_llm["runner_on_1b_batting_splits_leaderboard"] = runner_on_first_batting_splits_leaderboards_for_llm
    
#     # runner_on_first_batting_splits_leaderboard_str = " No Runner on 1B batting splits leaderboard data available."
#     # if runner_on_first_batting_splits_leaderboards_for_llm:
#     #     runner_on_first_batting_splits_leaderboard_str = f"Runner on 1B打者スプリットリーダーボード:\n{json.dumps(runner_on_first_batting_splits_leaderboards_for_llm, indent=2, ensure_ascii=False)}"


#     # ========================== Shohei Ohtani's Two-Way Player Stats ==========================
#     if fetch_ohtani_two_way:
#         ohtani_two_way_stats = get_ohtani_two_way_stats(season=season)
#         if ohtani_two_way_stats:
#             logger.debug(f"Fetched Ohtani two-way stats for season {season}: {ohtani_two_way_stats}")
#             ohtani_two_way_stats_for_llm_filtered = ohtani_two_way_stats # リストをそのまま代入
#             data_for_llm["shohei_ohtani_two_way_stats"] = ohtani_two_way_stats_for_llm_filtered
#         else:
#             ohtani_two_way_stats_for_llm_filtered = [] # データがない場合は空リスト
#             data_for_llm["shohei_ohtani_two_way_stats"] = ohtani_two_way_stats_for_llm_filtered
    
#     # Debugging: Log the data prepared for LLM
#     logger.debug(f"Data prepared for LLM: {json.dumps(data_for_llm, indent=2, ensure_ascii=False)}")

#     # # Debugging: Log the fetched Ohtani stats
#     # if ohtani_two_way_stats:
#     #     logger.debug(f"Fetched Ohtani two-way stats for season {season}: {ohtani_two_way_stats}")
#     #     ohtani_two_way_stats_for_llm = ohtani_two_way_stats # リストをそのまま代入
#     # else:
#     #     ohtani_two_way_stats_for_llm = [] # データがない場合は空リスト
    
#     # # # Debugging: Log the Ohtani two-way stats for LLM
#     # # logger.debug(f"Shohei Ohtani two-way stats for LLM: {ohtani_two_way_stats_for_llm}")

#     # ohtani_two_way_stats_str = "No Shohei Ohtani two-way player stats available."
#     # if ohtani_two_way_stats_for_llm:
#     #     ohtani_two_way_stats_str = f"Shohei Ohtani Two-Way Player Stats:\n{json.dumps(ohtani_two_way_stats_for_llm, indent=2, ensure_ascii=False)}"

#     # LLMへのプロンプト構築
#     prompt_data_str = json.dumps(data_for_llm, indent=2, ensure_ascii=False) # ★★★ 変更点3: 必要なデータのみをJSON文字列化 ★★★

#     # LLMへのプロンプト構築
#     prompt = f"""
#     あなたはMLBのデータアナリストです。以下のデータに基づいて、ユーザーの質問に回答してください。
#     質問の意図を理解し、提供されたデータから関連する情報を抽出し、簡潔に日本語で回答してください。
#     もし提供されたデータに質問の答えが見つからない場合、「提供されたデータからは回答できません」と明確に述べてください。

#     ---
#     ユーザーの質問: {query}

#     提供データ:
#     {prompt_data_str}
#     ---

#     回答:
#     """

#     if not GEMINI_API_KEY:
#         logger.error("GEMINI_API_KEY is not set. Please set it as an environment variable.")
#         return "APIキーが設定されていないため、AIによる分析はできません。"

#     GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

#     headers = {
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "contents": [
#             {
#                 "role": "user",
#                 "parts": [
#                     {"text": prompt}
#                 ]
#             }
#         ]
#     }

#     # 打者リーダーボードデータ:
#     # {batting_leaderboard_str}

#     # 投手リーダーボードデータ:
#     # {pitching_leaderboard_str}

#     # RISP打者スプリットリーダーボードデータ:
#     # {batting_splits_leaderboard_risp_str}

#     # Bases Loaded打者スプリットリーダーボードデータ:
#     # {bases_loaded_batting_splits_leaderboard_str}

#     # Runner on 1B打者スプリットリーダーボードデータ:
#     # {runner_on_first_batting_splits_leaderboard_str}

#     # Shohei Ohtaniの二刀流選手データ:
#     # {ohtani_two_way_stats_str}

#     try:
#         response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload))
#         response.raise_for_status()
#         result = response.json()

#         if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
#             generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
#             formatted_text = generated_text.replace('\n', '<br>')
#             return formatted_text
#         else:
#             logger.warning(f"Gemini API did not return expected content for query: {query}")
#             return "AIによる回答を取得できませんでした。"
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Error calling Gemini API for query {query}: {e}", exc_info=True)
#         return "AIによる回答中にエラーが発生しました。"
#     except Exception as e:
#         logger.error(f"An unexpected error occurred during AI response generation for query {query}: {e}", exc_info=True)
#         return "AIによる回答中に予期せぬエラーが発生しました。"

