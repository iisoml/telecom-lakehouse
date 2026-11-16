import subprocess
import sys

from ingestion.generators import generate_cdrs, generate_towers
from lakehouse.bronze import land_bronze
from lakehouse.observability import run_step
from lakehouse.silver import build_silver_cdr

MAX_REJECT_RATE = 0.05  

def main(n: int = 5000, chaos: float = 0.02) -> int:
    towers = generate_towers()
    cdrs = generate_cdrs(n, towers, chaos=chaos)

    with run_step("bronze", ["generator"], ["bronze.cdr"]):
        land_bronze(towers, "towers")
        land_bronze(cdrs, "cdr")

    with run_step("silver", ["bronze.cdr"], ["silver.cdr", "quarantine.cdr"]) as span:
        stats = build_silver_cdr()
        span.set_attributes({k: v for k, v in stats.items() if k != "ts"})
    print("silver stats:", stats)

    if stats["reject_rate"] > MAX_REJECT_RATE:
        print(f"GATE FAILED: reject rate {stats['reject_rate']:.1%} > {MAX_REJECT_RATE:.0%}. Gold NOT published.")
        return 1

    with run_step("gold_dbt", ["silver.cdr"], ["gold.customer_360", "gold.mart_churn_risk"]):
        r = subprocess.run(
            ["dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"],
            check=False,
        )
    if r.returncode != 0:
        print("GATE FAILED: dbt tests failed.")
        return 1

    print("Pipeline OK, gold published.")
    return 0


if __name__ == "__main__":
    sys.exit(main(chaos=float(sys.argv[1]) if len(sys.argv) > 1 else 0.02))