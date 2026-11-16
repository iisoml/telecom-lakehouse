import pandas as pd

SYNONYMS = {"LTE": "4G"}
VALID_CALL_TYPES = {"voice", "sms", "data"}
VALID_NETWORKS = {"4G", "5G"}


def standardise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["network_type"] = df["network_type"].replace(SYNONYMS)
    return df


def apply_contracts(df: pd.DataFrame, valid_towers: set[str]):
    df = standardise(df)

    rules = {
        "negative_duration": df["duration_seconds"] < 0,
        "null_tower": df["cell_tower_id"].isna(),
        "unknown_tower": df["cell_tower_id"].notna() & ~df["cell_tower_id"].isin(valid_towers),
        "bad_call_type": ~df["call_type"].isin(VALID_CALL_TYPES),
        "bad_network": ~df["network_type"].isin(VALID_NETWORKS),
        "null_start_time": df["start_time"].isna(),
        "sms_with_duration": (df["call_type"] == "sms") & (df["duration_seconds"] != 0),
    }

    reason = pd.Series("", index=df.index)
    for name, failed in rules.items():
        reason = reason.where(~failed, reason + name + ";")

    bad = reason != ""
    rejected = df[bad].copy()
    rejected["reject_reason"] = reason[bad].str.rstrip(";")

    good = df[~bad]
    if "_ingested_at" in good.columns:
        good = good.sort_values("_ingested_at")
    clean = good.drop_duplicates(subset="call_sid", keep="last").reset_index(drop=True)
    return clean, rejected.reset_index(drop=True)