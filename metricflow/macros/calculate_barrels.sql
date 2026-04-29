{% macro calculate_barrels(suffix='') %}
    COUNTIF(
        launch_speed IS NOT NULL
        AND launch_speed >= 98
        AND (
            (launch_speed = 98 AND launch_angle BETWEEN 26 AND 30) OR
            (launch_speed = 99 AND launch_angle BETWEEN 25 AND 31) OR
            (launch_speed = 100 AND launch_angle BETWEEN 25 AND 31) OR
            (launch_speed = 101 AND launch_angle BETWEEN 24 AND 32) OR
            (launch_speed = 102 AND launch_angle BETWEEN 24 AND 33) OR
            (launch_speed = 103 AND launch_angle BETWEEN 23 AND 34) OR
            (launch_speed = 104 AND launch_angle BETWEEN 23 AND 34) OR
            (launch_speed = 105 AND launch_angle BETWEEN 22 AND 35) OR
            (launch_speed >= 106 AND launch_angle BETWEEN 5 AND 50)
        )
    ) AS barrels_count{{ suffix }}
{% endmacro %}
