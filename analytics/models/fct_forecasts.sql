select p.cell, p.cycle, p.target_cycle, p.actual, p.prediction,
       p.persistence, p.linear_trend,
       c.capacity_ah as origin_capacity_ah,
       t.capacity_ah as target_capacity_ah,
       p.cell || ':' || cast(p.cycle as varchar) as forecast_id
from {{ ref('forecasts') }} p
left join {{ ref('stg_cycles') }} c on p.cell = c.cell and p.cycle = c.cycle
left join {{ ref('stg_cycles') }} t on p.cell = t.cell and p.target_cycle = t.cycle
