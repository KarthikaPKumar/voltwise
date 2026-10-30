select cell, cast(cycle as integer) as cycle,
       cast(capacity as double) as capacity_ah,
       cast(mean_temperature as double) as mean_temperature_c,
       cast(peak_temperature as double) as peak_temperature_c,
       cell || ':' || cast(cycle as varchar) as cycle_id
from {{ ref('cycles') }}
