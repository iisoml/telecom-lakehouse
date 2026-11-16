import uuid
from datetime import UTC, datetime

import pandas as pd
from deltalake import DeltaTable, write_deltalake

from lakehouse.storage import storage_options, table_path


def new_batch_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]


def land_bronze(df: pd.DataFrame, table: str, batch_id: str | None = None) -> str:
    """Append df to bronze/<table> as a Delta table. Returns the batch id."""
    batch_id = batch_id or new_batch_id()
    out = df.copy()
    out["_batch_id"] = batch_id
    out["_ingested_at"] = pd.Timestamp.now(tz="UTC")
    out["_ingested_at"] = out["_ingested_at"].astype("datetime64[us, UTC]")
    write_deltalake(
        table_path("bronze", table), out, mode="append", storage_options=storage_options()
    )
    return batch_id


def read_table(layer: str, table: str) -> pd.DataFrame:
    return DeltaTable(table_path(layer, table), storage_options=storage_options()).to_pandas()