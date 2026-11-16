from ingestion.generators import generate_cdrs, generate_towers
from lakehouse.bronze import land_bronze, read_table
from lakehouse.silver import build_silver_cdr


def test_silver_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    towers = generate_towers()
    land_bronze(towers, "towers")
    land_bronze(generate_cdrs(1000, towers, chaos=0.02), "cdr")

    build_silver_cdr()
    n1 = len(read_table("silver", "cdr"))
    build_silver_cdr()                      
    n2 = len(read_table("silver", "cdr"))

    assert n1 == n2
    assert read_table("silver", "cdr").call_sid.is_unique
    assert len(read_table("quarantine", "cdr")) > 0