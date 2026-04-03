"""
Advanced Stats Ranking サービス
Statcast pitch-level データから投手・打者の高度指標を算出
"""
import logging
from typing import Dict, List

from backend.app.services.base import get_bq_client
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STATCAST_TABLE = settings.get_table_full_name("statcast_master")
DIM_PLAYERS_TABLE = settings.get_table_full_name("dim_players_latest")
DIM_TEAMS_TABLE = settings.get_table_full_name("dim_teams")
TUNNEL_VIEW = settings.get_table_full_name("view_pitch_tunnel_stats")


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
        # pitcher_id を statcast_master から取得し team を JOIN
        query = f"""
            WITH base AS (
                SELECT v.*,
                    MIN(s.pitcher) AS pitcher_id
                FROM `{TUNNEL_VIEW}` v
                JOIN `{STATCAST_TABLE}` s
                    ON v.player_name = s.player_name AND s.game_year = @season
                WHERE v.game_year = @season
                GROUP BY
                    v.game_year, v.player_name, v.total_sequences, v.total_deceived,
                    v.whiffs, v.called_strikes, v.deception_rate_pct,
                    v.avg_release_diff, v.avg_velocity_diff, v.avg_plate_diff,
                    v.pitch_tunnel_score
            )
            SELECT
                b.*,
                tm.abbreviation AS team_abbr
            FROM base b
            LEFT JOIN `{DIM_PLAYERS_TABLE}` p ON b.pitcher_id = p.mlbid
            LEFT JOIN `{DIM_TEAMS_TABLE}` tm ON p.current_team_id = tm.team_id
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
            scatter_df = self.client.query(scatter_query, job_config=scatter_config).to_dataframe()
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

            job_config = self._make_job_config(params)
            df = self.client.query(query, job_config=job_config).to_dataframe()
            rankings = [
                {
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
    # P6: Pitch Arsenal Effectiveness
    # ----------------------------------------------------------
    async def get_arsenal_rankings(
        self,
        season: int = 2024,
        min_pitches: int = 100,
        limit: int = 50,
        offset: int = 0,
        team: str = "All",
    ) -> Dict:
        """
        P6 Pitch Arsenal Effectiveness ランキング

        Shannon entropy (多様性) × 球種別 delta_pitcher_run_exp (効果)
        """
        team_filter = "AND tm.team_name = @team" if team != "All" else ""

        query = f"""
            WITH pitcher_totals AS (
                SELECT
                    pitcher AS pitcher_id,
                    COUNT(*) AS total_pitches
                FROM `{STATCAST_TABLE}`
                WHERE game_year = @season
                    AND pitch_type IS NOT NULL
                    AND delta_pitcher_run_exp IS NOT NULL
                GROUP BY 1
                HAVING total_pitches >= @min_pitches
            ),
            pitch_type_stats AS (
                SELECT
                    t.pitcher_id,
                    s.pitch_name,
                    COUNT(*) AS type_count,
                    SAFE_DIVIDE(COUNT(*), t.total_pitches) AS p_i,
                    AVG(s.delta_pitcher_run_exp) AS avg_pitch_run_exp,
                    SUM(s.delta_pitcher_run_exp) AS total_pitch_run_exp
                FROM `{STATCAST_TABLE}` s
                JOIN pitcher_totals t ON s.pitcher = t.pitcher_id
                WHERE s.game_year = @season
                    AND s.pitch_type IS NOT NULL
                    AND s.delta_pitcher_run_exp IS NOT NULL
                GROUP BY t.pitcher_id, s.pitch_name, t.total_pitches
            ),
            entropy_calc AS (
                SELECT
                    pitcher_id,
                    SUM(-(p_i * LN(p_i))) AS diversity_score,
                    SUM(total_pitch_run_exp) AS total_effectiveness
                FROM pitch_type_stats
                GROUP BY 1
            )
            SELECT
                e.pitcher_id AS pitcher,
                p.full_name AS player_name,
                tm.abbreviation AS team_abbr,
                tm.team_name,
                ROUND(e.diversity_score, 4) AS diversity_score,
                ROUND(e.total_effectiveness, 4) AS effectiveness_score,
                ROUND(e.diversity_score * e.total_effectiveness, 4) AS synthetic_score
            FROM entropy_calc e
            LEFT JOIN `{DIM_PLAYERS_TABLE}` p ON e.pitcher_id = p.mlbid
            LEFT JOIN `{DIM_TEAMS_TABLE}` tm ON p.current_team_id = tm.team_id
            WHERE e.total_effectiveness > 0
            {team_filter}
            ORDER BY synthetic_score DESC
            LIMIT @limit OFFSET @offset
        """

        params = [
            ("season", "INT64", season),
            ("min_pitches", "INT64", min_pitches),
            ("limit", "INT64", limit),
            ("offset", "INT64", offset),
        ]
        if team != "All":
            params.append(("team", "STRING", team))

        # Scatter query — returns ALL qualifying pitchers (no LIMIT)
        # Also used for total count
        scatter_query = f"""
            WITH pitcher_totals AS (
                SELECT pitcher AS pitcher_id, COUNT(*) AS total_pitches
                FROM `{STATCAST_TABLE}`
                WHERE game_year = @season
                    AND pitch_type IS NOT NULL
                    AND delta_pitcher_run_exp IS NOT NULL
                GROUP BY 1
                HAVING total_pitches >= @min_pitches
            ),
            pitch_type_stats AS (
                SELECT t.pitcher_id,
                    SAFE_DIVIDE(COUNT(*), t.total_pitches) AS p_i,
                    SUM(s.delta_pitcher_run_exp) AS total_pitch_run_exp
                FROM `{STATCAST_TABLE}` s
                JOIN pitcher_totals t ON s.pitcher = t.pitcher_id
                WHERE s.game_year = @season
                    AND s.pitch_type IS NOT NULL
                    AND s.delta_pitcher_run_exp IS NOT NULL
                GROUP BY t.pitcher_id, s.pitch_name, t.total_pitches
            ),
            entropy_calc AS (
                SELECT pitcher_id,
                    SUM(-(p_i * LN(p_i))) AS diversity_score,
                    SUM(total_pitch_run_exp) AS total_effectiveness
                FROM pitch_type_stats
                GROUP BY 1
            )
            SELECT
                e.pitcher_id,
                p.full_name AS player_name,
                ROUND(e.diversity_score, 4) AS diversity_score,
                ROUND(e.total_effectiveness, 4) AS effectiveness_score,
                ROUND(e.diversity_score * e.total_effectiveness, 4) AS synthetic_score
            FROM entropy_calc e
            LEFT JOIN `{DIM_PLAYERS_TABLE}` p ON e.pitcher_id = p.mlbid
            {"LEFT JOIN `" + DIM_TEAMS_TABLE + "` tm ON p.current_team_id = tm.team_id" if team != "All" else ""}
            WHERE e.total_effectiveness > 0
            {team_filter}
            ORDER BY synthetic_score DESC
            LIMIT 100
        """

        scatter_params = [
            ("season", "INT64", season),
            ("min_pitches", "INT64", min_pitches),
        ]
        if team != "All":
            scatter_params.append(("team", "STRING", team))

        try:
            # Fetch scatter (all qualifying pitchers) + derive total
            scatter_config = self._make_job_config(scatter_params)
            scatter_df = self.client.query(scatter_query, job_config=scatter_config).to_dataframe()

            scatter_all = []
            for _, row in scatter_df.iterrows():
                scatter_all.append({
                    "player_name": row.get("player_name") or "",
                    "diversity_score": float(row["diversity_score"]),
                    "effectiveness_score": float(row["effectiveness_score"]),
                    "synthetic_score": float(row["synthetic_score"]),
                })
            total = len(scatter_all)

            # Fetch top-N rankings (with player name, team, pitch_mix)
            job_config = self._make_job_config(params)
            df = self.client.query(query, job_config=job_config).to_dataframe()

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
                pitch_mix_map = self._fetch_batch_pitch_mix(pitcher_ids, season)
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
            df = self.client.query(query, job_config=job_config).to_dataframe()
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
