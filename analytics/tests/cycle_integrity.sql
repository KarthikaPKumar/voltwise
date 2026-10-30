select * from {{ ref('stg_cycles') }}
where capacity_ah <= 0 or not isfinite(capacity_ah) or cycle < 1
   or not isfinite(mean_temperature_c) or not isfinite(peak_temperature_c)
   or mean_temperature_c > peak_temperature_c
