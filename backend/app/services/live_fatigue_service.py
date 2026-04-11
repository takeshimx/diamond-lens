from datetime import datetime
from google.cloud import bigquery
from backend.app.config.settings import get_settings

settings = get_settings()


def _to_bq_name(name: str) -> str:
    """MLB API形式 "Gerrit Cole" → BQ形式 "Cole, Gerrit" に変換"""
    if ',' not in name and ' ' in name:
        parts = name.strip().split()
        if len(parts) == 2:
            return f"{parts[1]}, {parts[0]}"
    return name


class LiveFatigueService:
    def __init__(self):
        self.client = bigquery.Client()

    def get_pitcher_baselines(self, pitcher_names: list[str], season: int = None) -> dict:
        if season is None:
            season = datetime.now().year
        """
        投手リストのシーズン平均球速・スピンレートを球種毎に一括取得。

        Returns:
            {
              "Gerrit Cole": {
                "4-Seam Fastball": {"speed": 95.2, "spin": 2370},
                "Slider":          {"speed": 87.5, "spin": 2610},
                ...
              },
              ...
            }
        """
        if not pitcher_names:
            return {}

        name_map = {_to_bq_name(n): n for n in pitcher_names}
        bq_names = list(name_map.keys())
        names_sql = ", ".join(f"'{n}'" for n in bq_names)

        query = f"""
        SELECT
            pitcher_name,
            pitch_name,
            AVG(avg_release_speed) AS baseline_speed,
            AVG(avg_spin_rate)     AS baseline_spin
        FROM `{settings.get_table_full_name('view_pitch_type_quality_by_inning')}`
        WHERE pitcher_name IN ({names_sql})
          AND game_year = {season}
        GROUP BY pitcher_name, pitch_name
        """

        try:
            df = self.client.query(query).to_dataframe()
            result = {}
            for _, row in df.iterrows():
                original_name = name_map.get(row["pitcher_name"])
                if not original_name:
                    continue
                if original_name not in result:
                    result[original_name] = {}
                result[original_name][row["pitch_name"]] = {
                    "speed": round(float(row["baseline_speed"]), 1) if row["baseline_speed"] else None,
                    "spin":  round(float(row["baseline_spin"]))      if row["baseline_spin"]  else None,
                }
            return result
        except Exception:
            return {}
