"""Explicit retraining after imports, with a temporal holdout evaluation.

Run `python -m src.retrain --save` locally or in a controlled CI job. Do not
retrain on every forecast request. Saving updates the model used on next API
restart; preserve previous version and compare newly reported metrics first.
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.features import build_model_features
from src.sales_store import get_history

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "cafe_demand_model.joblib"
FEATURES = [
    "store_location", "hour", "day_of_week", "month",
    "sales_lag_1d", "sales_lag_7d", "rolling_mean_7d",
]


def train(save: bool = False) -> dict:
    features = build_model_features(get_history()).sort_values("transaction_date")
    if features.empty:
        raise ValueError("No training rows with day-1 and day-7 history")
    cutoff = features["transaction_date"].max() - pd.Timedelta(days=13)
    train_set = features[features["transaction_date"] < cutoff]
    validation = features[features["transaction_date"] >= cutoff]
    if len(train_set) < 100 or len(validation) < 10:
        raise ValueError("Not enough data for a 14-day temporal holdout")

    pipeline = Pipeline([
        ("preprocess", ColumnTransformer([
            ("store", OneHotEncoder(handle_unknown="ignore"), ["store_location"]),
            ("numeric", "passthrough", [c for c in FEATURES if c != "store_location"]),
        ])),
        ("model", LinearRegression()),
    ])
    pipeline.fit(train_set[FEATURES], train_set["drinks_sold"])
    y_pred = pipeline.predict(validation[FEATURES]).clip(min=0)
    result = {
        "validation_start_date": str(cutoff.date()),
        "validation_end_date": str(features["transaction_date"].max().date()),
        "validation_rows": int(len(validation)),
        "mae": round(float(mean_absolute_error(validation["drinks_sold"], y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(validation["drinks_sold"], y_pred))), 4),
        "saved": bool(save),
    }
    if save:
        pipeline.fit(features[FEATURES], features["drinks_sold"])
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp_file = MODEL_PATH.with_suffix(".tmp.joblib")
        joblib.dump(pipeline, temp_file)
        os.replace(temp_file, MODEL_PATH)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="Replace saved model after validation")
    args = parser.parse_args()
    print(json.dumps(train(args.save), indent=2))
