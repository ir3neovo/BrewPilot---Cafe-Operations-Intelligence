from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from src.sales import DATA_PATH, validate_sales

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models/cafe_demand_model.joblib"
MAX_FORECAST_DAYS = 30


@lru_cache(maxsize=1)
def load_model():
    return joblib.load(MODEL_PATH)


def load_history():
    # Read one consistent snapshot per request; atomic imports need no restart.
    return validate_sales(pd.read_csv(DATA_PATH))


def forecast_options(history=None):
    history = load_history() if history is None else history
    return {"stores": [
        {"store": store, "latest_date": str(group.transaction_date.max().date()),
         "min_date": str((group.transaction_date.max() + pd.Timedelta(days=1)).date()),
         "max_date": str((group.transaction_date.max() + pd.Timedelta(days=MAX_FORECAST_DAYS)).date())}
        for store, group in history.groupby("store_location")
    ], "max_forecast_days": MAX_FORECAST_DAYS}


def predict_day(store, date, hours=None, history=None):
    history = load_history() if history is None else history
    subset = history[history.store_location == store]
    if subset.empty:
        raise ValueError("Unknown store location")
    target = pd.Timestamp(date)
    last_date = subset.transaction_date.max()
    if pd.isna(target) or target.tz is not None or target != target.normalize():
        raise ValueError("Forecast date must be a calendar date")
    if not last_date < target <= last_date + pd.Timedelta(days=MAX_FORECAST_DAYS):
        raise ValueError(f"Forecast date must be 1–{MAX_FORECAST_DAYS} days after this store's latest recorded date ({last_date.date()})")
    requested_hours = sorted(int(h) for h in subset.hour.unique()) if hours is None else hours
    if any(not isinstance(h, int) or not 0 <= h <= 23 for h in requested_hours):
        raise ValueError("Hour must be between 0 and 23")
    model = load_model()
    forecasts, skipped = [], []
    for hour in requested_hours:
        series = subset[subset.hour == hour].set_index("transaction_date").drinks_sold.to_dict()
        prediction = None
        for day in pd.date_range(last_date + pd.Timedelta(days=1), target):
            previous = [series.get(day - pd.Timedelta(days=d), float("nan")) for d in range(1, 8)]
            if pd.isna(previous[0]) or pd.isna(previous[6]):
                prediction = None
                break
            features = pd.DataFrame([{
                "store_location": store, "hour": hour, "day_of_week": day.dayofweek,
                "month": day.month, "sales_lag_1d": previous[0],
                "sales_lag_7d": previous[6], "rolling_mean_7d": pd.Series(previous).mean(),
            }])
            prediction = round(max(0, float(model.predict(features)[0])), 2)
            series[day] = prediction
        if prediction is None:
            skipped.append({"hour": int(hour), "reason": "Insufficient history: day-1 and day-7 sales are required for each forecast step."})
        else:
            forecasts.append({"hour": int(hour), "predicted_drinks": prediction})
    if not forecasts:
        raise ValueError("Insufficient history for the requested store and date")
    return {"store": store, "date": str(target.date()), "forecasts": forecasts,
            "skipped_hours": skipped, "history_through": str(last_date.date()),
            "horizon_days": (target - last_date).days,
            "uses_recursive_predictions": (target - last_date).days > 1}


def predict_demand(store, date, hour):
    return predict_day(store, date, hours=[hour])["forecasts"][0]["predicted_drinks"]
