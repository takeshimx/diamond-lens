{% macro calculate_hard_hit_rate(suffix='') %}
    ROUND(SAFE_DIVIDE(
        COUNTIF(launch_speed IS NOT NULL AND launch_speed >= 95),
        COUNTIF(events NOT IN ('hit_by_pitch', 'walk', 'intent_walk', 'catcher_interf', 'strikeout'))
    ), 3) AS hard_hit_rate{{ suffix }}
{% endmacro %}
