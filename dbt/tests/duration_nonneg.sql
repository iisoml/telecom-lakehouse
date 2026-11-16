select *
from {{ ref('stg_cdr') }}
where duration_seconds < 0