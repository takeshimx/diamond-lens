
QUERY_TYPE_CONFIG = {
    "season_batting" :{
        "table_id": "fact_batting_stats_with_risp",
        "year_col": "season",
        "player_col": "name",
        "available_metrics": ["hr", "avg", "ops", "rbi", "sb", "obp", "slg", "so"]
    },
    "season_pitching": {
        "table_id": "fact_pitching_stats",
        "year_col": "season",
        "player_col": "name",
        "available_metrics": ["era", "whip", "so", "fip", "w", "ip", "gs", "h", "r", "er", "bb", "avg"]
    },
    "career_batting": {
        "table_id": "tbl_batter_career_stats",
        "year_col": "",
        "player_col": "batter_name",
        "available_metrics": ["career_homeruns", "career_batting_average", "career_on_base_percentage", "career_slugging_percentage", "career_on_base_plus_slugging", "career_at_bats"]
    },
    "batting_splits": {
        "risp": {
            "table_id": "tbl_batter_clutch_risp",
            "year_col": "game_year",
            "player_col": "batter_name",
            "available_metrics": ["ab_at_risp", "avg_at_risp", "obp_at_risp", "slg_at_risp", "homeruns_at_risp"]
        },
        "bases_loaded": {
            "table_id": "tbl_batter_clutch_bases_loaded",
            "year_col": "game_year",
            "player_col": "batter_name",
            "available_metrics": ["ab_at_bases_loaded", "avg_at_bases_loaded", "obp_at_bases_loaded", "slg_at_bases_loaded", "grandslam"]
        },
        "runner_on_1b": {
            "table_id": "tbl_batter_clutch_runner_on_1b",
            "year_col": "game_year",
            "player_col": "batter_name",
            "available_metrics": ["ab_at_runner_on_1b", "avg_at_runner_on_1b", "obp_at_runner_on_1b", "slg_at_runner_on_1b", "homeruns_at_runner_on_1b"]
        },
        "inning": {
            "table_id": "tbl_batter_inning_stats",
            "year_col": "game_year",
            "player_col": "batter_name",
            "available_metrics": ["ab_by_inning", "avg_by_inning", "obp_by_inning", "slg_by_inning", "homeruns_by_inning", "ops_by_inning"]
        },
        "pitcher_throws": {
            "table_id": "tbl_batter_pitcher_throws_stats",
            "year_col": "game_year",
            "player_col": "batter_name",
            "available_metrics": ["ab_by_p_throws", "avg_by_p_throws", "obp_by_p_throws", "slg_by_p_throws", "homeruns_by_p_throws", "ops_by_p_throws"]
        },
        "pitch_type": {
            "table_id": "tbl_batter_pitch_type_stats",
            "year_col": "game_year",
            "player_col": "batter_name",
            "available_metrics": ["ab_by_pitch_type", "avg_by_pitch_type", "obp_by_pitch_type", "slg_by_pitch_type", "homeruns_by_pitch_type", "ops_by_pitch_type"]
        }
    }
}

KEY_BASE_BATTING_STATS = ["homerun", "batting_average", "on_base_percentage", "slugging_percentage", "on_base_plus_slugging", "at_bats"]

MAIN_PITCHING_STATS = ["era", "whip", "strikeouts", "fip", "wins", "innings_pitched", "games_started", "hits_allowed", "runs", "earned_runs", 
                       "base_on_balls", "batting_average_against"]
MAIN_BATTING_STATS = KEY_BASE_BATTING_STATS + ["runs_batted_in", "stolen_bases", "strikeouts"]
MAIN_CAREER_BATTING_STATS = KEY_BASE_BATTING_STATS + ["runs_batted_in", "runs", "stolen_bases", "strikeouts", "games", "war"]
MAIN_RISP_BATTING_STATS = KEY_BASE_BATTING_STATS
MAIN_BASES_LOADED_BATTING_STATS = KEY_BASE_BATTING_STATS
MAIN_RUNNER_ON_1B_BATTING_STATS = KEY_BASE_BATTING_STATS
MAIN_INNING_BATTING_STATS = KEY_BASE_BATTING_STATS
MAIN_BATTING_BY_PITCHING_THROWS_STATS = KEY_BASE_BATTING_STATS
MAIN_BATTING_BY_PITCH_TYPE_STATS = KEY_BASE_BATTING_STATS

# Define all column names that should be formatted as decimals (3 decimal places)
DECIMAL_FORMAT_COLUMNS = [
    # Career batting averages/percentages/rates
    'career_batting_average', 'career_on_base_percentage', 'career_slugging_percentage',
    'career_on_base_plus_slugging', 'career_launch_angle', 'career_exit_velocity',
    'career_bat_speed', 'career_swing_length', 'career_hard_hit_rate', 'career_barrels_rate',
    'career_strikeout_rate', 'career_swinging_strike_rate',
    
    # Season batting averages/percentages
    'avg', 'obp', 'slg', 'ops', 'batting_average', 'on_base_percentage', 
    'slugging_percentage', 'on_base_plus_slugging',
    
    # RISP stats
    'avg_at_risp', 'obp_at_risp', 'slg_at_risp', 'ops_at_risp',
    
    # Bases loaded stats
    'avg_at_bases_loaded', 'obp_at_bases_loaded', 'slg_at_bases_loaded', 'ops_at_bases_loaded',
    
    # Runner on 1B stats
    'avg_at_runner_on_1b', 'obp_at_runner_on_1b', 'slg_at_runner_on_1b', 'ops_at_runner_on_1b',
    
    # Inning stats
    'avg_by_inning', 'obp_by_inning', 'slg_by_inning', 'ops_by_inning',
    
    # Pitcher throws stats
    'avg_by_p_throws', 'obp_by_p_throws', 'slg_by_p_throws', 'ops_by_p_throws',
    
    # Pitch type stats  
    'avg_by_pitch_type', 'obp_by_pitch_type', 'slg_by_pitch_type', 'ops_by_pitch_type',
    
    # Pitching stats
    'era', 'whip', 'fip'
]

METRIC_MAP = {
    # Batting stats
    "homerun": {
        "season_batting": "hr",
        "career_batting": "career_homeruns",
        "batting_splits_risp": "homeruns_at_risp",
        "batting_splits_bases_loaded": "grandslam",
        "batting_splits_runner_on_1b": "homeruns_at_runner_on_1b",
        "batting_splits_inning": "homeruns_by_inning",
        "batting_splits_pitcher_throws": "homeruns_by_p_throws",
        "batting_splits_pitch_type": "homeruns_by_pitch_type"
    },
    "batting_average": {
        "season_batting": "avg",
        "career_batting": "career_batting_average",
        "batting_splits_risp": "avg_at_risp",
        "batting_splits_bases_loaded": "avg_at_bases_loaded",
        "batting_splits_runner_on_1b": "avg_at_runner_on_1b",
        "batting_splits_inning": "avg_by_inning",
        "batting_splits_pitcher_throws": "avg_by_p_throws",
        "batting_splits_pitch_type": "avg_by_pitch_type"
    },
    "on_base_percentage": {
        "season_batting": "obp",
        "career_batting": "career_on_base_percentage",
        "batting_splits_risp": "obp_at_risp",
        "batting_splits_bases_loaded": "obp_at_bases_loaded",
        "batting_splits_runner_on_1b": "obp_at_runner_on_1b",
        "batting_splits_inning": "obp_by_inning",
        "batting_splits_pitcher_throws": "obp_by_p_throws",
        "batting_splits_pitch_type": "obp_by_pitch_type"
    },
    "slugging_percentage": {
        "season_batting": "slg",
        "career_batting": "career_slugging_percentage",
        "batting_splits_risp": "slg_at_risp",
        "batting_splits_bases_loaded": "slg_at_bases_loaded",
        "batting_splits_runner_on_1b": "slg_at_runner_on_1b",
        "batting_splits_inning": "slg_by_inning",
        "batting_splits_pitcher_throws": "slg_by_p_throws",
        "batting_splits_pitch_type": "slg_by_pitch_type"
    },
    "on_base_plus_slugging": {
        "season_batting": "ops",
        "career_batting": "career_on_base_plus_slugging",
        "batting_splits_risp": "ops_at_risp",
        "batting_splits_bases_loaded": "ops_at_bases_loaded",
        "batting_splits_runner_on_1b": "ops_at_runner_on_1b",
        "batting_splits_inning": "ops_by_inning",
        "batting_splits_pitcher_throws": "ops_by_p_throws",
        "batting_splits_pitch_type": "ops_by_pitch_type"
    },
    "at_bats": {
        "season_batting": "ab",
        "career_batting": "career_ab",
        "batting_splits_risp": "ab_at_risp",
        "batting_splits_bases_loaded": "ab_at_bases_loaded",
        "batting_splits_runner_on_1b": "ab_at_runner_on_1b",
        "batting_splits_inning": "ab_by_inning",
        "batting_splits_pitcher_throws": "ab_by_p_throws",
        "batting_splits_pitch_type": "ab_by_pitch_type"
    },
    "hits": {
        "season_batting": "h",
        "career_batting": "career_hits"
    },
    "runs_batted_in": {
        "season_batting": "rbi",
        "career_batting": "career_rbi"
    },
    "stolen_bases": {
        "season_batting": "sb",
        "career_batting": "career_stolen_bases"
    },
    "strikeouts": {
        "season_batting": "so",
        "career_batting": "career_so",
        "batting_splits_risp": "so_at_risp",
        "batting_splits_bases_loaded": "so_at_bases_loaded",
        "batting_splits_runner_on_1b": "so_at_runner_on_1b",
        "batting_splits_inning": "so_by_inning",
        "batting_splits_pitcher_throws": "so_by_p_throws",
        "batting_splits_pitch_type": "so_by_pitch_type"
    },
    "games": {
        "season_batting": "g",
        "career_batting": "career_games"
    },
    "war": {
        "season_batting": "war",
        "career_batting": "career_war"
    },
    # Pitching stats
    "era": {
        "season_pitching": "era"
    },
    "whip": {
        "season_pitching": "whip"
    },
    "strikeouts": {
        "season_pitching": "so"
    },
    "fip": {
        "season_pitching": "fip"
    },
    "wins": {
        "season_pitching": "w"
    },
    "innings_pitched": {
        "season_pitching": "ip"
    },
    "games_started": {
        "season_pitching": "gs"
    },
    "hits_allowed": {
        "season_pitching": "h"
    },
    "runs": {
        "season_pitching": "r"
    },
    "earned_runs": {
        "season_pitching": "er"
    },
    "base_on_balls": {
        "season_pitching": "bb"
    },
    "batting_average_against": {
        "season_pitching": "avg"
    }
}