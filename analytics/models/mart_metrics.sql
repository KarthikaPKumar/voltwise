select coalesce(cell, '__all__') as cell
{% for name, metric in var('semantic_metrics').items() %}
 , {{ metric.expression }} as {{ name }}
{% endfor %}
from {{ ref('fct_forecasts') }}
group by grouping sets ((cell), ())
