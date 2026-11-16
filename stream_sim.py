import time

from ingestion.generators import generate_cdrs, generate_towers
from lakehouse.bronze import land_bronze, read_table
from lakehouse.observability import run_step
from lakehouse.silver import build_silver_cdr

towers = generate_towers()
land_bronze(towers, "towers")

for i in range(5):
    with run_step(f"micro_batch_{i}", ["generator"], ["silver.cdr"]):
        land_bronze(generate_cdrs(500, towers, seed=100 + i, chaos=0.02), "cdr")
        stats = build_silver_cdr()
    silver = read_table("silver", "cdr")
    print(f"batch {i}: silver={len(silver)} rows, unique={silver.call_sid.nunique()}, rejected={stats['rejected_rows']}")
    time.sleep(2)