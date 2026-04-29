{% macro calculate_slg(suffix='') %}
    ROUND(SAFE_DIVIDE(
        (COUNTIF(events = 'single') * 1) +
        (COUNTIF(events = 'double') * 2) +
        (COUNTIF(events = 'triple') * 3) +
        (COUNTIF(events = 'home_run') * 4),
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS slg{{ suffix }}
{% endmacro %}
