import os
from pathlib import Path


def is_azure() -> bool:
    return os.environ.get("LAKE_BACKEND") == "azure"


def table_path(layer: str, table: str) -> str:
    assert layer in {"bronze", "silver", "gold", "quarantine"}, f"unknown layer: {layer}"
    if is_azure():
        account = os.environ["AZURE_STORAGE_ACCOUNT"]
        return f"abfss://{layer}@{account}.dfs.core.windows.net/{table}"
    return str(Path(os.environ.get("LAKE_ROOT", "data")) / layer / table)


def storage_options() -> dict | None:
    if is_azure():
        return {
            "azure_storage_account_name": os.environ["AZURE_STORAGE_ACCOUNT"],
            "azure_use_azure_cli": "true",
        }
    return None