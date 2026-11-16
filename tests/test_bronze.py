from ingestion.generators import generate_cdrs, generate_towers
from lakehouse.bronze import land_bronze, read_table


def test_bronze_is_append_only(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    df = generate_cdrs(200, generate_towers(), chaos=0.0)

    land_bronze(df, "cdr")
    land_bronze(df, "cdr")         

    out = read_table("bronze", "cdr")
    assert len(out) == 400           
    assert out.call_sid.nunique() == 200
    assert out._batch_id.nunique() == 2
    assert {"_batch_id", "_ingested_at"} <= set(out.columns)