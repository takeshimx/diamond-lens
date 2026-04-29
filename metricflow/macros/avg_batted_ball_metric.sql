{% macro avg_batted_ball_metric(column, alias) %}
ROUND(SAFE_DIVIDE(
    SUM(CASE WHEN events NOT IN (
        'hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt',
        'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'
    ) THEN {{ column }} ELSE NULL END),
    COUNTIF(events NOT IN (
        'hit_by_pitch', 'walk', 'intent_walk', 'sac_bunt',
        'catcher_interf', 'strikeout', 'strikeout_double_play', 'truncated_pa'
    ))
), 3) AS {{ alias }}
{% endmacro %}
