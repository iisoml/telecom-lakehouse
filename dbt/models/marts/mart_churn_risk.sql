with bounds as (select max(start_time) as max_ts from {{ ref('stg_cdr') }}),
weekly as (
    select
        c.caller_id as customer_id,
        count(*) filter (where c.start_time >= b.max_ts - interval 7 day) as last_7d,
        count(*) filter (where c.start_time <  b.max_ts - interval 7 day) / 3.3 as prev_weekly_avg
    from {{ ref('stg_cdr') }} c cross join bounds b
    group by 1
)
select
    customer_id, last_7d, round(prev_weekly_avg, 1) as prev_weekly_avg,
    case
        when prev_weekly_avg > 0 and last_7d < 0.5 * prev_weekly_avg then 'high'
        when prev_weekly_avg > 0 and last_7d < 0.8 * prev_weekly_avg then 'medium'
        else 'low'
    end as churn_risk
from weekly