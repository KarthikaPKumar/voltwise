select 1 as invalid_population
where (select count(*) from {{ ref('stg_cycles') }}) != 636
   or (select count(*) from {{ ref('fct_forecasts') }}) != 560
   or (select count(distinct cell) from {{ ref('stg_cycles') }}) != 4
