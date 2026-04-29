{{ config(materialized='table', alias='dim_players_master') }}

WITH idfg_lookup AS (
  SELECT idfg, name FROM (
    SELECT idfg, name FROM {{ ref('fact_pitching_stats') }}
    WHERE idfg IS NOT NULL AND idfg > 0
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY season DESC) = 1
    UNION ALL
    SELECT idfg, name FROM {{ ref('fact_batting_stats_master') }}
    WHERE idfg IS NOT NULL AND idfg > 0
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY season DESC) = 1
  )
  QUALIFY COUNT(DISTINCT idfg) OVER (PARTITION BY name) = 1
      AND ROW_NUMBER() OVER (PARTITION BY name) = 1
),

base AS (
  SELECT
    COALESCE(n.mlbid, CAST(pb.mlb_id AS INT64))                  AS mlbid,
    COALESCE(n.full_name, CONCAT(pb.first_name,' ',pb.last_name)) AS full_name,
    COALESCE(n.first_name, pb.first_name)                        AS first_name,
    COALESCE(n.last_name,  pb.last_name)                         AS last_name,
    COALESCE(n.idfg, pb.fangraphs_id)                            AS idfg,
    pb.bbref_id, pb.mlb_debut_year, pb.mlb_last_year,
    n.birth_date, n.current_age, n.birth_country,
    n.height, n.weight, n.active, n.current_team_id,
    n.primary_position, n.mlb_debut_date, n.bat_side, n.pitch_hand
  FROM {{ source('mlb_raw_data', 'dim_players_latest') }} n
  FULL OUTER JOIN {{ source('mlb_raw_data', 'dim_players_pb') }} pb
    ON n.mlbid = CAST(pb.mlb_id AS INT64)
)

SELECT
  b.mlbid,
  b.full_name,
  b.first_name,
  b.last_name,
  CASE
    WHEN b.idfg IS NULL OR b.idfg = -1 THEN lkp.idfg
    ELSE b.idfg
  END AS idfg,
  b.bbref_id, b.mlb_debut_year, b.mlb_last_year,
  b.birth_date, b.current_age, b.birth_country,
  b.height, b.weight, b.active, b.current_team_id,
  b.primary_position, b.mlb_debut_date, b.bat_side, b.pitch_hand
FROM base b
LEFT JOIN idfg_lookup lkp ON b.full_name = lkp.name
