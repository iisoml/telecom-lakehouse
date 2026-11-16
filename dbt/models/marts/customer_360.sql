select
    caller_id                                              as customer_id,
    count(*)                                               as total_events,
    count(*) filter (where call_type = 'voice')            as voice_calls,
    count(*) filter (where call_type = 'sms')              as sms_count,
    count(*) filter (where call_type = 'data')             as data_sessions,
    sum(duration_seconds) / 60.0                           as total_minutes,
    sum(data_volume_mb)                                    as total_data_mb,
    avg(case when roaming_flag then 1.0 else 0 end)        as roaming_share,
    min(start_time)                                        as first_seen,
    max(start_time)                                        as last_seen
from {{ ref('stg_cdr') }}
group by 1