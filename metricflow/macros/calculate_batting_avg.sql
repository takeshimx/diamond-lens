{% macro calculate_batting_avg(suffix='') %}
    ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run')),
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS avg{{ suffix }}
{% endmacro %}
