{% macro calculate_ops(suffix='') %}
    ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
        COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) +
    ROUND(SAFE_DIVIDE(
        (COUNTIF(events = 'single') * 1) +
        (COUNTIF(events = 'double') * 2) +
        (COUNTIF(events = 'triple') * 3) +
        (COUNTIF(events = 'home_run') * 4),
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS ops{{ suffix }}
{% endmacro %}
