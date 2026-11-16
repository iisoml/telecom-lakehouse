from ingestion.generators import generate_cdrs, generate_towers
from lakehouse.bronze import land_bronze, read_table

towers = generate_towers()
cdrs = generate_cdrs(5000, towers, chaos=0.02)

land_bronze(towers, "towers")
batch = land_bronze(cdrs, "cdr")

bronze = read_table("bronze", "cdr")
print(f"batch {batch}: wrote {len(cdrs)} rows")
print(f"bronze.cdr now has {len(bronze)} rows, {bronze.call_sid.nunique()} distinct call_sid")
print(bronze.groupby("_batch_id").size())