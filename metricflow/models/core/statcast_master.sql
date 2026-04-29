-- dbt model for statcast data 2025 season master
{{ config(
    materialized='incremental',
    unique_key=['game_pk', 'pitch_number', 'at_bat_number'],
    incremental_strategy='merge',
    cluster_by=['game_pk'],
    partition_by={
        'field': 'game_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    alias='statcast_master',
    description='Statcast data for all MLB seasons since 2021, after merging incremental updates from the staging model',
    enabled=True
)}}

SELECT
    * EXCEPT(rn) -- exclude the row number column
FROM 
    (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY game_pk, pitch_number, at_bat_number 
                ORDER BY game_date DESC, sv_id DESC
            ) AS rn -- row number to filter duplicates
        FROM {{ source('mlb_raw_data', 'statcast_staging') }} -- Load the staging table for Statcast data from the source table
        {% if is_incremental() %}
            WHERE game_date > (SELECT MAX(game_date) FROM {{ this }}) -- filter for incremental updates
        {% endif %}
    ) AS deduplicated
WHERE rn = 1 -- keep only the latest record for each game_pk, pitch_number, at_bat_number combination