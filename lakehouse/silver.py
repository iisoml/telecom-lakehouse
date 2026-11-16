from datetime import UTC, datetime

import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from lakehouse.bronze import read_table
from lakehouse.quality import apply_contracts
from lakehouse.storage import storage_options, table_path


def _to_arrow(df: pd.DataFrame) -> pa.Table:
    df = df.copy()
    for c in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        df[c] = df[c].astype("datetime64[us]") if df[c].dt.tz is None else df[c].astype("datetime64[us, UTC]")
    return pa.Table.from_pandas(df, preserve_index=False)


def _exists(path: str) -> bool:
    return DeltaTable.is_deltatable(path, storage_options=storage_options())


def build_silver_cdr() -> dict:
    bronze = read_table("bronze", "cdr")
    towers = read_table("bronze", "towers").drop_duplicates("tower_id")
    clean, rejected = apply_contracts(bronze, set(towers.tower_id))

    if len(rejected):
        rejected["_quarantined_at"] = pd.Timestamp.now(tz="UTC").floor("us")
        write_deltalake(table_path("quarantine", "cdr"), _to_arrow(rejected), mode="append", storage_options=storage_options())

    path = table_path("silver", "cdr")
    src = _to_arrow(clean)
    if not _exists(path):
        write_deltalake(path, src, storage_options=storage_options())
    else:
        (
            DeltaTable(path, storage_options=storage_options())
            .merge(src, predicate="t.call_sid = s.call_sid", source_alias="s", target_alias="t")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute()
        )

    stats = {
        "bronze_rows": len(bronze),
        "clean_rows": len(clean),
        "rejected_rows": len(rejected),
        "reject_rate": round(len(rejected) / max(len(bronze), 1), 4),
        "ts": datetime.now(UTC).isoformat(),
    }
    return stats