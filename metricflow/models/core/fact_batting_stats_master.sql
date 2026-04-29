-- dbt model to merge weekly batting stats into the master fact table
-- NOTE: DO NOT ADD COMMENTS in config block, it will cause dbt to fail
{{ 
    config(
        materialized = 'incremental',
        unique_key=['idfg', 'season'],
        incremental_strategy='insert_overwrite',
        partition_by={
            'field': 'season',
            'data_type': 'int64',
            'range': {
                'start': 2021,
                'end': run_started_at.year + 1,
                'interval': 1
            }
        },
        alias='fact_batting_stats_master'
)}}
-- This model merges weekly batting stats into the master fact table
SELECT *
FROM {{ source('mlb_raw_data', 'fact_batting_stats_weekly_staging')}} -- Load weekly batting stats from the source table
-- WHERE season = {{ var('target_season') }} -- Filter by the target season

{% if is_incremental() %}
    WHERE 
        season = {{ var('target_season') }}
{% endif %}

