select
    call_sid, caller_id, callee_id, start_time,
    duration_seconds, cell_tower_id, call_type,
    roaming_flag, data_volume_mb, network_type
from delta_scan('data/silver/cdr')