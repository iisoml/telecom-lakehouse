import hashlib

import numpy as np
import pandas as pd

NETWORK_TYPES = ["4G", "5G", "LTE"]       
CALL_TYPES = ["voice", "sms", "data"]
PEAK_HOURS = [9, 10, 11, 17, 18, 19, 20]


def _hash_id(i: int) -> str:
    return hashlib.sha256(f"CUST_{i:06d}".encode()).hexdigest()[:16]


def generate_towers(num_towers: int = 50, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "tower_id": [f"TWR_{i:04d}" for i in range(num_towers)],
        "lat": 24.7136 + rng.uniform(-0.5, 0.5, num_towers),
        "lon": 46.6753 + rng.uniform(-0.5, 0.5, num_towers),
        "tower_type": rng.choice(["macro", "micro", "pico"], num_towers, p=[0.5, 0.3, 0.2]),
    })


def generate_cdrs(
    n: int,
    towers: pd.DataFrame,
    seed: int = 42,
    chaos: float = 0.0,
    num_customers: int = 1000,
    days: int = 30,
    start: str = "2024-01-01",
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    call_type = rng.choice(CALL_TYPES, n, p=[0.5, 0.3, 0.2])

    hour_weights = np.where(np.isin(np.arange(24), PEAK_HOURS), 3.0, 1.0)
    hour_weights /= hour_weights.sum()
    day = rng.integers(0, days, n)
    hour = rng.choice(24, n, p=hour_weights)
    start_time = (
        pd.Timestamp(start)
        + pd.to_timedelta(day, unit="D")
        + pd.to_timedelta(hour, unit="h")
        + pd.to_timedelta(rng.integers(0, 3600, n), unit="s")
    )

    duration = np.where(
        call_type == "voice", rng.exponential(180, n),
        np.where(call_type == "data", rng.exponential(300, n), 0),
    ).astype(int)

    data_mb = np.where(call_type == "data", np.round(rng.exponential(50, n), 2), 0.0)

    caller = rng.integers(0, num_customers, n)
    callee = rng.integers(0, num_customers, n)

    df = pd.DataFrame({
        "call_sid": [f"CALL_{seed}_{i:08d}" for i in range(n)],   
        "caller_id": [_hash_id(i) for i in caller],
        "callee_id": [_hash_id(i) for i in callee],
        "start_time": start_time,
        "duration_seconds": duration,
        "cell_tower_id": rng.choice(towers["tower_id"].to_numpy(), n),
        "call_type": call_type,
        "roaming_flag": rng.random(n) < 0.05,
        "data_volume_mb": data_mb,
        "network_type": rng.choice(NETWORK_TYPES, n, p=[0.5, 0.2, 0.3]),
    })

    return inject_chaos(df, chaos, rng) if chaos > 0 else df


def inject_chaos(df: pd.DataFrame, rate: float, rng: np.random.Generator) -> pd.DataFrame:
    df = df.copy()
    k = max(1, int(len(df) * rate))
    idx = rng.choice(df.index.to_numpy(), size=3 * k, replace=False)
    neg, null, dup = idx[:k], idx[k:2 * k], idx[2 * k:]

    df.loc[neg, "duration_seconds"] = -rng.integers(1, 500, k)      
    df.loc[null, "cell_tower_id"] = None                             
    return pd.concat([df, df.loc[dup]], ignore_index=True)            