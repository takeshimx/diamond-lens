"""
Advanced Stats Ranking サービス
Statcast pitch-level データから投手・打者の高度指標を算出
"""
import asyncio
import logging
from typing import Dict, List

from backend.app.services.base import get_bq_client
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STATCAST_TABLE = settings.get_table_full_name("statcast_master")
DIM_PLAYERS_TABLE = settings.get_table_full_name("dim_players_latest")
DIM_TEAMS_TABLE = settings.get_table_full_name("dim_teams")
TUNNEL_VIEW   = settings.get_table_full_name("view_pitch_tunnel_stats")
FINISHER_VIEW = settings.get_table_full_name("view_pitch_2strikes_finisher_score")
STAMINA_VIEW  = settings.get_table_full_name("view_pitch_stamina_score")
ARSENAL_VIEW  = settings.get_table_full_name("view_pitch_arsenal_effectiveness")
PRESSURE_VIEW          = settings.get_table_full_name("view_pitch_pressure_dominance_sp")
PLATE_DISCIPLINE_VIEW      = settings.get_table_full_name("view_batter_plate_discipline_score")
CLUTCH_HITTING_VIEW        = settings.get_table_full_name("view_batter_clutch_hitting")
CONTACT_CONSISTENCY_VIEW   = settings.get_table_full_name("view_batter_contact_consistency")


class AdvancedStatsService:
    """Advanced Stats 指標の算出・ランキング取得"""

    def __init__(self):
        self.client = get_bq_client()

    # ----------------------------------------------------------
    # P1: Pitch Tunnel Score
    # ----------------------------------------------------------
    async def get_pitch_tunnel_rankings(
        self,
        season: int = 2025,
        limit: int = 40,
        offset: int = 0,
    ) -> Dict:
        """
        P1 Pitch Tunnel Score ランキング

        BQ View `view_pitch_tunnel_stats` を参照。
        z-score・集計はView側で完結。サービスはseason絞り込みとページネーションのみ。
        """
        query = f"""
            SELECT
                pitcher,
                player_name,
                team_abbr,
                total_sequences,
                total_deceived,
                whiffs,
                called_strikes,
                deception_rate_pct,
                avg_release_diff,
                avg_velocity_diff,
                avg_plate_diff,
                pitch_tunnel_score
            FROM `{TUNNEL_VIEW}`
            WHERE game_year = @season
            ORDER BY pitch_tunnel_score DESC
            LIMIT @limit OFFSET @offset
        """

        # scatter: リリース収束度 vs プレート発散度（トンネリングの本質的可視化）
        scatter_query = f"""
            SELECT
                player_name,
                avg_release_diff,
                avg_plate_diff,
                deception_rate_pct,
                pitch_tunnel_score
            FROM `{TUNNEL_VIEW}`
            WHERE game_year = @season
            ORDER BY pitch_tunnel_score DESC
            LIMIT 300
        """

        params = [
            ("season", "INT64", season),
            ("limit", "INT64", limit),
            ("offset", "INT64", offset),
        ]
        scatter_params = [
            ("season", "INT64", season),
        ]

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )
            scatter_all = [
                {
                    "player_name": row.get("player_name") or "",
                    "avg_release_diff": float(row["avg_release_diff"]),
                    "avg_plate_diff": float(row["avg_plate_diff"]),
                    "deception_rate_pct": float(row["deception_rate_pct"]),
                    "pitch_tunnel_score": float(row["pitch_tunnel_score"]),
                }
                for _, row in scatter_df.iterrows()
            ]
            total = len(scatter_all)

            rankings = [
                {
                    "pitcher_id": int(row["pitcher"]),
                    "player_name": row.get("player_name") or "",
                    "team": row.get("team_abbr") or "",
                    "total_sequences": int(row["total_sequences"]),
                    "total_deceived": int(row["total_deceived"]),
                    "whiffs": int(row["whiffs"]),
                    "called_strikes": int(row["called_strikes"]),
                    "deception_rate_pct": float(row["deception_rate_pct"]),
                    "avg_release_diff": float(row["avg_release_diff"]),
                    "avg_velocity_diff": float(row["avg_velocity_diff"]),
                    "avg_plate_diff": float(row["avg_plate_diff"]),
                    "pitch_tunnel_score": float(row["pitch_tunnel_score"]),
                }
                for _, row in df.iterrows()
            ]

            return {
                "rankings": rankings,
                "scatter_all": scatter_all,
                "total": total,
                "metric": "P1_pitch_tunnel",
                "season": season,
            }

        except Exception as e:
            logger.error(f"Failed to get pitch tunnel rankings: {e}")
            raise

    # ----------------------------------------------------------
    # P2: Pressure Dominance Index
    # ----------------------------------------------------------
    async def get_pressure_rankings(
        self,
        season: int = 2025,
        limit: int = 40,
        offset: int = 0,
    ) -> Dict:
        """
        P2 Pressure Dominance Index ランキング（先発投手限定）

        BQ View `view_pitch_pressure_dominance_sp` を参照。
        高LI(上位25%)時と低LI時の delta_pitcher_run_exp を比較し、
        プレッシャー下での投球パフォーマンスをZスコアで合成。
        """
        query = f"""
            SELECT
                pitcher,
                player_name,
                team,
                total_pitches,
                high_li_pitches,
                high_li_run_exp,
                low_li_run_exp,
                pressure_delta,
                pressure_dominance_index
            FROM `{PRESSURE_VIEW}`
            WHERE game_year = @season
            ORDER BY pressure_dominance_index DESC
            LIMIT @limit OFFSET @offset
        """

        scatter_query = f"""
            SELECT
                player_name,
                high_li_run_exp,
                pressure_delta,
                pressure_dominance_index
            FROM `{PRESSURE_VIEW}`
            WHERE game_year = @season
            ORDER BY pressure_dominance_index DESC
            LIMIT 200
        """

        params = [
            ("season", "INT64", season),
            ("limit",  "INT64", limit),
            ("offset", "INT64", offset),
        ]
        scatter_params = [("season", "INT64", season)]

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )
            scatter_all = [
                {
                    "player_name":              row.get("player_name") or "",
                    "high_li_run_exp":          float(row["high_li_run_exp"]),
                    "pressure_delta":           float(row["pressure_delta"]),
                    "pressure_dominance_index": float(row["pressure_dominance_index"]),
                }
                for _, row in scatter_df.iterrows()
            ]
            total = len(scatter_all)

            rankings = [
                {
                    "pitcher_id":               int(row["pitcher"]),
                    "player_name":              row.get("player_name") or "",
                    "team":                     row.get("team") or "",
                    "total_pitches":            int(row["total_pitches"]),
                    "high_li_pitches":          int(row["high_li_pitches"]),
                    "high_li_run_exp":          float(row["high_li_run_exp"]),
                    "low_li_run_exp":           float(row["low_li_run_exp"]),
                    "pressure_delta":           float(row["pressure_delta"]),
                    "pressure_dominance_index": float(row["pressure_dominance_index"]),
                }
                for _, row in df.iterrows()
            ]

            return {
                "rankings":   rankings,
                "scatter_all": scatter_all,
                "total":      total,
                "metric":     "P2_pressure_dominance",
                "season":     season,
            }

        except Exception as e:
            logger.error(f"Failed to get pressure dominance rankings: {e}")
            raise

    # ----------------------------------------------------------
    # P4: Two-Strike Finisher Score
    # ----------------------------------------------------------
    async def get_finisher_rankings(
        self,
        season: int = 2025,
        limit: int = 40,
        offset: int = 0,
    ) -> Dict:
        """
        P4 Two-Strike Finisher Score ランキング

        BQ View `view_pitch_2strikes_finisher_score` を参照。
        view 側で dim_players_latest・dim_teams と JOIN 済みのため、
        サービス側は season 絞り込みとページネーションのみ。
        """
        query = f"""
            SELECT
                pitcher,
                player_name,
                team_abbr,
                total_2_strike_pitches,
                primary_finishing_pitch,
                whiff_rate,
                put_away_woba,
                finisher_score
            FROM `{FINISHER_VIEW}`
            WHERE game_year = @season
            ORDER BY finisher_score DESC
            LIMIT @limit OFFSET @offset
        """

        scatter_query = f"""
            SELECT
                player_name,
                whiff_rate,
                put_away_woba,
                finisher_score
            FROM `{FINISHER_VIEW}`
            WHERE game_year = @season
            ORDER BY finisher_score DESC
            LIMIT 200
        """

        params = [
            ("season", "INT64", season),
            ("limit", "INT64", limit),
            ("offset", "INT64", offset),
        ]
        scatter_params = [("season", "INT64", season)]

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )
            scatter_all = [
                {
                    "player_name": row.get("player_name") or "",
                    "whiff_rate": float(row["whiff_rate"]),
                    "put_away_woba": float(row["put_away_woba"]),
                    "finisher_score": float(row["finisher_score"]),
                }
                for _, row in scatter_df.iterrows()
            ]
            total = len(scatter_all)

            rankings = [
                {
                    "pitcher_id": int(row["pitcher"]),
                    "player_name": row.get("player_name") or "",
                    "team": row.get("team_abbr") or "",
                    "total_2_strike_pitches": int(row["total_2_strike_pitches"]),
                    "primary_finishing_pitch": row.get("primary_finishing_pitch") or "",
                    "whiff_rate": float(row["whiff_rate"]),
                    "put_away_woba": float(row["put_away_woba"]),
                    "finisher_score": float(row["finisher_score"]),
                }
                for _, row in df.iterrows()
            ]

            return {
                "rankings": rankings,
                "scatter_all": scatter_all,
                "total": total,
                "metric": "P4_two_strike_finisher",
                "season": season,
            }

        except Exception as e:
            logger.error(f"Failed to get finisher rankings: {e}")
            raise

    # ----------------------------------------------------------
    # P3: Stamina Score
    # ----------------------------------------------------------
    async def get_stamina_rankings(
        self,
        season: int = 2025,
        limit: int = 40,
        offset: int = 0,
    ) -> Dict:
        """
        P3 Stamina Score ランキング

        BQ View `view_pitch_stamina_score` を参照。
        view 側で dim_players_master・dim_teams と JOIN 済み。
        """
        query = f"""
            SELECT
                pitcher,
                player_name,
                team_abbr,
                games,
                ip,
                avg_speed_slope,
                avg_spin_slope,
                run_exp_1st,
                run_exp_3rd_plus,
                tto_delta,
                stamina_score
            FROM `{STAMINA_VIEW}`
            WHERE game_year = @season
            ORDER BY stamina_score DESC
            LIMIT @limit OFFSET @offset
        """

        scatter_query = f"""
            SELECT
                player_name,
                avg_speed_slope,
                tto_delta,
                stamina_score
            FROM `{STAMINA_VIEW}`
            WHERE game_year = @season
            ORDER BY stamina_score DESC
            LIMIT 200
        """

        params = [
            ("season", "INT64", season),
            ("limit",  "INT64", limit),
            ("offset", "INT64", offset),
        ]
        scatter_params = [("season", "INT64", season)]

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )
            scatter_all = [
                {
                    "player_name":    row.get("player_name") or "",
                    "avg_speed_slope": float(row["avg_speed_slope"]),
                    "tto_delta":       float(row["tto_delta"]),
                    "stamina_score":   float(row["stamina_score"]),
                }
                for _, row in scatter_df.iterrows()
            ]
            total = len(scatter_all)

            rankings = [
                {
                    "pitcher_id":      int(row["pitcher"]),
                    "player_name":     row.get("player_name") or "",
                    "team":            row.get("team_abbr") or "",
                    "games":           int(row["games"]),
                    "ip":              float(row["ip"]),
                    "avg_speed_slope": float(row["avg_speed_slope"]),
                    "avg_spin_slope":  float(row["avg_spin_slope"]),
                    "run_exp_1st":     float(row["run_exp_1st"]),
                    "run_exp_3rd_plus":float(row["run_exp_3rd_plus"]),
                    "tto_delta":       float(row["tto_delta"]),
                    "stamina_score":   float(row["stamina_score"]),
                }
                for _, row in df.iterrows()
            ]

            return {
                "rankings":   rankings,
                "scatter_all": scatter_all,
                "total":      total,
                "metric":     "P3_stamina",
                "season":     season,
            }

        except Exception as e:
            logger.error(f"Failed to get stamina rankings: {e}")
            raise

    # ----------------------------------------------------------
    # P6: Pitch Arsenal Effectiveness
    # ----------------------------------------------------------
    async def get_arsenal_rankings(
        self,
        season: int = 2024,
        limit: int = 50,
        offset: int = 0,
        team: str = "All",
    ) -> Dict:
        """
        P6 Pitch Arsenal Effectiveness ランキング

        BQ View `view_pitch_arsenal_effectiveness` を参照。
        Shannon entropy・集計・dim joinはView側で完結。
        """
        team_filter = "AND team_abbr = @team" if team != "All" else ""

        query = f"""
            SELECT
                pitcher,
                player_name,
                team_abbr,
                diversity_score,
                effectiveness_score,
                synthetic_score
            FROM `{ARSENAL_VIEW}`
            WHERE game_year = @season
            {team_filter}
            ORDER BY synthetic_score DESC
            LIMIT @limit OFFSET @offset
        """

        params = [
            ("season", "INT64", season),
            ("limit", "INT64", limit),
            ("offset", "INT64", offset),
        ]
        if team != "All":
            params.append(("team", "STRING", team))

        scatter_query = f"""
            SELECT
                player_name,
                diversity_score,
                effectiveness_score,
                synthetic_score
            FROM `{ARSENAL_VIEW}`
            WHERE game_year = @season
            {team_filter}
            ORDER BY synthetic_score DESC
            LIMIT 100
        """

        scatter_params = [("season", "INT64", season)]
        if team != "All":
            scatter_params.append(("team", "STRING", team))

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            # scatter と ranking を並列実行
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )

            scatter_all = []
            for _, row in scatter_df.iterrows():
                scatter_all.append({
                    "player_name": row.get("player_name") or "",
                    "diversity_score": float(row["diversity_score"]),
                    "effectiveness_score": float(row["effectiveness_score"]),
                    "synthetic_score": float(row["synthetic_score"]),
                })
            total = len(scatter_all)

            rankings = []
            pitcher_ids = []
            for _, row in df.iterrows():
                pid = int(row["pitcher"])
                pitcher_ids.append(pid)
                rankings.append({
                    "pitcher_id": pid,
                    "player_name": row.get("player_name") or "",
                    "team": row.get("team_abbr") or row.get("team_name") or "",
                    "diversity_score": float(row["diversity_score"]),
                    "effectiveness_score": float(row["effectiveness_score"]),
                    "synthetic_score": float(row["synthetic_score"]),
                    "pitch_mix": [],  # populated below
                })

            # --- Batch fetch pitch mix for all ranked pitchers (single query) ---
            if pitcher_ids:
                pitch_mix_map = await asyncio.to_thread(self._fetch_batch_pitch_mix, pitcher_ids, season)
                for r in rankings:
                    r["pitch_mix"] = pitch_mix_map.get(r["pitcher_id"], [])

            return {
                "rankings": rankings,
                "scatter_all": scatter_all,
                "total": total,
                "metric": "P6_arsenal_effectiveness",
                "season": season,
            }

        except Exception as e:
            logger.error(f"Failed to get arsenal rankings: {e}")
            raise

    # ----------------------------------------------------------
    # P6: 球種内訳データ（ランキング上の各投手用）
    # ----------------------------------------------------------
    async def get_arsenal_pitch_mix(
        self,
        pitcher_id: int,
        season: int = 2024,
    ) -> Dict:
        """
        特定投手の球種ミックス詳細
        各球種の使用率 + 得点抑止力 (avg delta_pitcher_run_exp)
        """
        query = f"""
            WITH totals AS (
                SELECT COUNT(*) AS total_pitches
                FROM `{STATCAST_TABLE}`
                WHERE pitcher = @pitcher_id
                    AND game_year = @season
                    AND pitch_type IS NOT NULL
            )
            SELECT
                s.pitch_name,
                COUNT(*) AS pitch_count,
                ROUND(SAFE_DIVIDE(COUNT(*), t.total_pitches), 4) AS usage_pct,
                ROUND(AVG(s.delta_pitcher_run_exp), 6) AS avg_run_exp
            FROM `{STATCAST_TABLE}` s
            CROSS JOIN totals t
            WHERE s.pitcher = @pitcher_id
                AND s.game_year = @season
                AND s.pitch_type IS NOT NULL
                AND s.delta_pitcher_run_exp IS NOT NULL
            GROUP BY s.pitch_name, t.total_pitches
            ORDER BY pitch_count DESC
        """

        job_config = self._make_job_config([
            ("pitcher_id", "INT64", pitcher_id),
            ("season", "INT64", season),
        ])

        try:
            df = self.client.query(query, job_config=job_config).to_dataframe()
            pitch_mix = []
            for _, row in df.iterrows():
                pitch_mix.append({
                    "pitch_name": row["pitch_name"],
                    "pitch_count": int(row["pitch_count"]),
                    "usage_pct": float(row["usage_pct"]),
                    "avg_run_exp": float(row["avg_run_exp"]),
                })

            return {"pitcher_id": pitcher_id, "season": season, "pitch_mix": pitch_mix}

        except Exception as e:
            logger.error(f"Failed to get pitch mix for pitcher {pitcher_id}: {e}")
            raise

    # ----------------------------------------------------------
    # B2: Plate Discipline Score
    # ----------------------------------------------------------
    async def get_plate_discipline_rankings(
        self,
        season: int = 2025,
        limit: int = 40,
        offset: int = 0,
    ) -> Dict:
        """
        B2 Plate Discipline Score ランキング

        BQ View `view_batter_plate_discipline_score` を参照。
        O-Swing%(35%) + Z-Swing%(35%) + avg_decision_value(30%) の合成Zスコア。
        """
        query = f"""
            SELECT
                batter,
                player_name,
                team,
                total_pitches,
                o_swing_pct,
                z_swing_pct,
                o_take_pct,
                z_take_pct,
                avg_decision_value,
                plate_discipline_score
            FROM `{PLATE_DISCIPLINE_VIEW}`
            WHERE game_year = @season
            ORDER BY plate_discipline_score DESC
            LIMIT @limit OFFSET @offset
        """

        scatter_query = f"""
            SELECT
                player_name,
                o_swing_pct,
                z_swing_pct,
                plate_discipline_score
            FROM `{PLATE_DISCIPLINE_VIEW}`
            WHERE game_year = @season
            ORDER BY plate_discipline_score DESC
            LIMIT 300
        """

        params = [
            ("season", "INT64", season),
            ("limit",  "INT64", limit),
            ("offset", "INT64", offset),
        ]
        scatter_params = [("season", "INT64", season)]

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )
            scatter_all = [
                {
                    "player_name":           row.get("player_name") or "",
                    "o_swing_pct":           float(row["o_swing_pct"]),
                    "z_swing_pct":           float(row["z_swing_pct"]),
                    "plate_discipline_score": float(row["plate_discipline_score"]),
                }
                for _, row in scatter_df.iterrows()
            ]
            total = len(scatter_all)

            rankings = [
                {
                    "batter_id":             int(row["batter"]),
                    "player_name":           row.get("player_name") or "",
                    "team":                  row.get("team") or "",
                    "total_pitches":         int(row["total_pitches"]),
                    "o_swing_pct":           float(row["o_swing_pct"]),
                    "z_swing_pct":           float(row["z_swing_pct"]),
                    "o_take_pct":            float(row["o_take_pct"]),
                    "z_take_pct":            float(row["z_take_pct"]),
                    "avg_decision_value":    float(row["avg_decision_value"]),
                    "plate_discipline_score": float(row["plate_discipline_score"]),
                }
                for _, row in df.iterrows()
            ]

            return {
                "rankings":    rankings,
                "scatter_all": scatter_all,
                "total":       total,
                "metric":      "B2_plate_discipline",
                "season":      season,
            }

        except Exception as e:
            logger.error(f"Failed to get plate discipline rankings: {e}")
            raise

    # ----------------------------------------------------------
    # B3: Clutch Hitting Index
    # ----------------------------------------------------------
    async def get_clutch_rankings(
        self,
        season: int = 2025,
        limit: int = 40,
        offset: int = 0,
    ) -> Dict:
        """
        B3 Clutch Hitting Index ランキング

        BQ View `view_batter_clutch_hitting` を参照。
        高LI(上位25%)時の wOBA - 全体wOBA = clutch_index の合成Zスコア。
        """
        query = f"""
            SELECT
                batter,
                player_name,
                team,
                total_pa,
                high_li_pa,
                woba_overall,
                woba_high_li,
                ba_overall,
                ba_high_li,
                clutch_index,
                clutch_hitting_score
            FROM `{CLUTCH_HITTING_VIEW}`
            WHERE game_year = @season
            ORDER BY clutch_hitting_score DESC
            LIMIT @limit OFFSET @offset
        """

        scatter_query = f"""
            SELECT
                player_name,
                woba_overall,
                woba_high_li,
                clutch_index,
                clutch_hitting_score
            FROM `{CLUTCH_HITTING_VIEW}`
            WHERE game_year = @season
            ORDER BY clutch_hitting_score DESC
            LIMIT 300
        """

        params = [
            ("season", "INT64", season),
            ("limit",  "INT64", limit),
            ("offset", "INT64", offset),
        ]
        scatter_params = [("season", "INT64", season)]

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )
            scatter_all = [
                {
                    "player_name":          row.get("player_name") or "",
                    "woba_overall":         float(row["woba_overall"]),
                    "woba_high_li":         float(row["woba_high_li"]),
                    "clutch_index":         float(row["clutch_index"]),
                    "clutch_hitting_score": float(row["clutch_hitting_score"]),
                }
                for _, row in scatter_df.iterrows()
            ]
            total = len(scatter_all)

            rankings = [
                {
                    "batter_id":            int(row["batter"]),
                    "player_name":          row.get("player_name") or "",
                    "team":                 row.get("team") or "",
                    "total_pa":             int(row["total_pa"]),
                    "high_li_pa":           int(row["high_li_pa"]),
                    "woba_overall":         float(row["woba_overall"]),
                    "woba_high_li":         float(row["woba_high_li"]),
                    "ba_overall":           float(row["ba_overall"]) if row["ba_overall"] is not None else None,
                    "ba_high_li":           float(row["ba_high_li"]) if row["ba_high_li"] is not None else None,
                    "clutch_index":         float(row["clutch_index"]),
                    "clutch_hitting_score": float(row["clutch_hitting_score"]),
                }
                for _, row in df.iterrows()
            ]

            return {
                "rankings":    rankings,
                "scatter_all": scatter_all,
                "total":       total,
                "metric":      "B3_clutch_hitting",
                "season":      season,
            }

        except Exception as e:
            logger.error(f"Failed to get clutch rankings: {e}")
            raise

    # ----------------------------------------------------------
    # B4: Contact Consistency Score
    # ----------------------------------------------------------
    async def get_contact_consistency_rankings(
        self,
        season: int = 2025,
        limit: int = 40,
        offset: int = 0,
    ) -> Dict:
        """
        B4 Contact Consistency Score ランキング

        BQ View `view_batter_contact_consistency` を参照。
        xwOBAのCV(変動係数)逆転(35%) + 平均xwOBA(35%) +
        ハードヒット率(20%) + スウィートスポット率(10%) の合成Zスコア。
        再Zスコア化済み: 100 + Z*15 (OPS+/wRC+と同等スケール)
        """
        query = f"""
            SELECT
                batter,
                player_name,
                team,
                bbip,
                avg_xwoba,
                stddev_xwoba,
                cv_xwoba,
                hard_hit_pct,
                sweet_spot_pct,
                contact_consistency_score
            FROM `{CONTACT_CONSISTENCY_VIEW}`
            WHERE game_year = @season
            ORDER BY contact_consistency_score DESC
            LIMIT @limit OFFSET @offset
        """

        scatter_query = f"""
            SELECT
                player_name,
                avg_xwoba,
                cv_xwoba,
                contact_consistency_score
            FROM `{CONTACT_CONSISTENCY_VIEW}`
            WHERE game_year = @season
            ORDER BY contact_consistency_score DESC
            LIMIT 300
        """

        params = [
            ("season", "INT64", season),
            ("limit",  "INT64", limit),
            ("offset", "INT64", offset),
        ]
        scatter_params = [("season", "INT64", season)]

        try:
            scatter_config = self._make_job_config(scatter_params)
            job_config = self._make_job_config(params)
            scatter_df, df = await asyncio.gather(
                asyncio.to_thread(lambda: self.client.query(scatter_query, job_config=scatter_config).to_dataframe()),
                asyncio.to_thread(lambda: self.client.query(query, job_config=job_config).to_dataframe()),
            )
            scatter_all = [
                {
                    "player_name":               row.get("player_name") or "",
                    "avg_xwoba":                 float(row["avg_xwoba"]),
                    "cv_xwoba":                  float(row["cv_xwoba"]),
                    "contact_consistency_score": float(row["contact_consistency_score"]),
                }
                for _, row in scatter_df.iterrows()
            ]
            total = len(scatter_all)

            rankings = [
                {
                    "batter_id":                 int(row["batter"]),
                    "player_name":               row.get("player_name") or "",
                    "team":                      row.get("team") or "",
                    "bbip":                      int(row["bbip"]),
                    "avg_xwoba":                 float(row["avg_xwoba"]),
                    "stddev_xwoba":              float(row["stddev_xwoba"]),
                    "cv_xwoba":                  float(row["cv_xwoba"]),
                    "hard_hit_pct":              float(row["hard_hit_pct"]),
                    "sweet_spot_pct":            float(row["sweet_spot_pct"]),
                    "contact_consistency_score": float(row["contact_consistency_score"]),
                }
                for _, row in df.iterrows()
            ]

            return {
                "rankings":    rankings,
                "scatter_all": scatter_all,
                "total":       total,
                "metric":      "B4_contact_consistency",
                "season":      season,
            }

        except Exception as e:
            logger.error(f"Failed to get contact consistency rankings: {e}")
            raise

    # ----------------------------------------------------------
    # 検索（投手名オートコンプリート）— dim_players_latest 使用
    # ----------------------------------------------------------
    async def search_pitchers(
        self,
        name: str,
        season: int = 2024,
        limit: int = 10,
    ) -> List[Dict]:
        """投手名で検索（部分一致）"""
        query = f"""
            SELECT DISTINCT
                s.pitcher AS pitcher_id,
                p.full_name AS player_name,
                tm.abbreviation AS team_abbr
            FROM `{STATCAST_TABLE}` s
            JOIN `{DIM_PLAYERS_TABLE}` p ON s.pitcher = p.mlbid
            LEFT JOIN `{DIM_TEAMS_TABLE}` tm ON p.current_team_id = tm.team_id
            WHERE s.game_year = @season
                AND LOWER(p.full_name) LIKE LOWER(@name_pattern)
                AND s.pitch_type IS NOT NULL
            LIMIT @limit
        """

        job_config = self._make_job_config([
            ("season", "INT64", season),
            ("name_pattern", "STRING", f"%{name}%"),
            ("limit", "INT64", limit),
        ])

        try:
            df = await asyncio.to_thread(
                lambda: self.client.query(query, job_config=job_config).to_dataframe()
            )
            results = []
            seen = set()
            for _, row in df.iterrows():
                pid = int(row["pitcher_id"])
                if pid in seen:
                    continue
                seen.add(pid)
                results.append({
                    "pitcher_id": pid,
                    "player_name": row.get("player_name") or "",
                    "team": row.get("team_abbr") or "",
                })
            return results

        except Exception as e:
            logger.error(f"Failed to search pitchers: {e}")
            raise

    # ----------------------------------------------------------
    # Batch pitch mix (ランキング一括取得用)
    # ----------------------------------------------------------
    def _fetch_batch_pitch_mix(
        self,
        pitcher_ids: List[int],
        season: int,
    ) -> Dict[int, List[Dict]]:
        """
        複数投手の球種ミックスを 1 回のクエリで取得。
        pitcher_id リストを UNNEST で渡し IN フィルタする。
        """
        query = f"""
            WITH targets AS (
                SELECT pitcher_id
                FROM UNNEST(@pitcher_ids) AS pitcher_id
            ),
            totals AS (
                SELECT s.pitcher AS pitcher_id, COUNT(*) AS total_pitches
                FROM `{STATCAST_TABLE}` s
                JOIN targets t ON s.pitcher = t.pitcher_id
                WHERE s.game_year = @season
                    AND s.pitch_type IS NOT NULL
                GROUP BY 1
            )
            SELECT
                s.pitcher AS pitcher_id,
                s.pitch_name,
                COUNT(*) AS pitch_count,
                ROUND(SAFE_DIVIDE(COUNT(*), t.total_pitches), 4) AS usage_pct,
                ROUND(AVG(s.delta_pitcher_run_exp), 6) AS avg_run_exp
            FROM `{STATCAST_TABLE}` s
            JOIN totals t ON s.pitcher = t.pitcher_id
            WHERE s.game_year = @season
                AND s.pitch_type IS NOT NULL
                AND s.delta_pitcher_run_exp IS NOT NULL
            GROUP BY s.pitcher, s.pitch_name, t.total_pitches
            ORDER BY s.pitcher, pitch_count DESC
        """

        from google.cloud import bigquery as bq
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ArrayQueryParameter("pitcher_ids", "INT64", pitcher_ids),
                bq.ScalarQueryParameter("season", "INT64", season),
            ]
        )

        df = self.client.query(query, job_config=job_config).to_dataframe()

        result: Dict[int, List[Dict]] = {}
        for _, row in df.iterrows():
            pid = int(row["pitcher_id"])
            if pid not in result:
                result[pid] = []
            result[pid].append({
                "pitch_name": row["pitch_name"],
                "pitch_count": int(row["pitch_count"]),
                "usage_pct": float(row["usage_pct"]),
                "avg_run_exp": float(row["avg_run_exp"]),
            })
        return result

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    @staticmethod
    def _make_job_config(params: List[tuple]):
        from google.cloud import bigquery as bq
        return bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter(name, type_, value)
                for name, type_, value in params
            ]
        )
