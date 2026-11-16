from ingestion.generators import generate_cdrs, generate_towers


def test_towers_are_unique():
    t = generate_towers(20)
    assert t.tower_id.is_unique and len(t) == 20


def test_clean_cdrs_are_clean():
    df = generate_cdrs(1000, generate_towers(), chaos=0.0)
    assert len(df) == 1000
    assert df.call_sid.is_unique
    assert (df.duration_seconds >= 0).all()
    assert df.cell_tower_id.notna().all()


def test_chaos_corrupts_all_three_ways():
    df = generate_cdrs(5000, generate_towers(), chaos=0.02)
    assert (df.duration_seconds < 0).any()
    assert df.cell_tower_id.isna().any()
    assert df.call_sid.duplicated().any()


def test_towers_come_from_shared_registry():
    t = generate_towers()
    df = generate_cdrs(1000, t, chaos=0.0)
    assert set(df.cell_tower_id) <= set(t.tower_id)


def test_same_seed_same_data():
    t = generate_towers()
    a = generate_cdrs(500, t, seed=7)
    b = generate_cdrs(500, t, seed=7)
    assert a.equals(b)