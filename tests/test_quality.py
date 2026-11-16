from ingestion.generators import generate_cdrs, generate_towers
from lakehouse.quality import apply_contracts


def test_contracts_catch_chaos():
    towers = generate_towers()
    df = generate_cdrs(5000, towers, chaos=0.02)
    clean, rejected = apply_contracts(df, set(towers.tower_id))

    assert clean.call_sid.is_unique
    assert (clean.duration_seconds >= 0).all()
    assert clean.cell_tower_id.notna().all()
    assert set(clean.network_type) <= {"4G", "5G"}         
    assert len(rejected) >= 100                              
    assert {"negative_duration", "null_tower"} <= set(rejected.reject_reason)


def test_clean_data_has_no_rejects():
    towers = generate_towers()
    df = generate_cdrs(1000, towers, chaos=0.0)
    clean, rejected = apply_contracts(df, set(towers.tower_id))
    assert len(rejected) == 0 and len(clean) == 1000