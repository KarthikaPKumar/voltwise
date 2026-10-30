select * from {{ ref('fct_forecasts') }}
where target_cycle != cycle + 10 or cycle < 10
   or abs(actual - target_capacity_ah) > 1e-10
   or abs(persistence - origin_capacity_ah) > 1e-10
   or not isfinite(prediction) or prediction <= 0
   or not isfinite(actual) or actual <= 0
