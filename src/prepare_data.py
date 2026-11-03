
from pathlib import Path
import pandas as pd

from src.features import (
    build_hourly_sales,
    build_model_features
)

# find project root regardless of current working directory
ROOT = Path(__file__).resolve().parents[1]

RAW_PATH = ROOT / "data" / "raw" / "Coffee Shop Sales.xlsx"
PROCESSED = ROOT / "data" / "processed"


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_excel(RAW_PATH)

    # aggregate hourly sales
    hourly_df = build_hourly_sales(raw_df)

    hourly_df.to_csv(
        PROCESSED / "hourly_sales.csv",
        index=False
    )

    # generate model features
    model_df = build_model_features(hourly_df)

    model_df.to_csv(
        PROCESSED / "model_data_with_rolling.csv",
        index=False
    )

    print("Data preparation completed!")
    print("Raw records:", len(raw_df))
    print("Hourly observations:", len(hourly_df))
    print("Model-ready observations:", len(model_df))

    print("\nModel features:")
    print(model_df.columns.tolist())


if __name__ == "__main__":
    main()
