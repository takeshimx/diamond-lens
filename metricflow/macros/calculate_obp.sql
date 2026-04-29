{% macro calculate_obp(suffix='') %}
    ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('single', 'double', 'triple', 'home_run', 'walk', 'hit_by_pitch', 'intent_walk')),
        COUNTIF(events NOT IN ('sac_fly', 'sac_bunt', 'catcher_interf'))
    ), 3) AS obp{{ suffix }}
{% endmacro %}
