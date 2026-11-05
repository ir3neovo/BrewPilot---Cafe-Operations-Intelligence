"""Validated, idempotent imports of complete hourly beverage totals."""
import argparse
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(os.getenv("BREWPILOT_HISTORY_PATH", str(ROOT / "data/processed/hourly_sales.csv")))
KEYS = ["transaction_date", "store_location", "hour"]
COLUMNS = KEYS + ["drinks_sold"]


def validate_sales(frame):
    if not set(COLUMNS).issubset(frame.columns) or frame.empty:
        raise ValueError(f"Sales must contain rows with columns: {', '.join(COLUMNS)}")
    data = frame[COLUMNS].copy()
    data["transaction_date"] = pd.to_datetime(data["transaction_date"], errors="raise")
    if data["transaction_date"].isna().any() or (data["transaction_date"] != data["transaction_date"].dt.normalize()).any():
        raise ValueError("transaction_date must contain dates without times")
    if data["transaction_date"].dt.tz is not None:
        raise ValueError("transaction_date must not include a timezone")
    if data["store_location"].isna().any() or not data["store_location"].map(lambda s: isinstance(s, str) and bool(s.strip())).all():
        raise ValueError("store_location must be nonempty")
    for column in ["hour", "drinks_sold"]:
        data[column] = pd.to_numeric(data[column], errors="raise")
        if not np.isfinite(data[column]).all():
            raise ValueError(f"{column} must be finite")
    if not ((data.hour >= 0) & (data.hour <= 23) & (data.hour % 1 == 0)).all():
        raise ValueError("hour must be an integer between 0 and 23")
    if (data.drinks_sold < 0).any():
        raise ValueError("drinks_sold must be nonnegative")
    if data.duplicated(KEYS).any():
        raise ValueError("Duplicate store/date/hour rows are not allowed")
    return data


def import_sales(source, destination=DATA_PATH):
    incoming = validate_sales(pd.read_csv(source))
    destination = Path(destination)
    existing = validate_sales(pd.read_csv(destination))
    if not set(incoming.store_location).issubset(set(existing.store_location)):
        raise ValueError("Unknown store location; retrain the model before adding stores")
    merged = pd.concat([existing, incoming]).drop_duplicates(KEYS, keep="last").sort_values(KEYS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", suffix=".csv", dir=destination.parent, delete=False, newline="") as handle:
            temporary = Path(handle.name)
            merged.to_csv(handle, index=False, date_format="%Y-%m-%d")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"imported_rows": len(incoming), "total_rows": len(merged)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="Complete hourly totals, not incremental transactions")
    args = parser.parse_args()
    print(import_sales(args.csv))


if __name__ == "__main__":
    main()
