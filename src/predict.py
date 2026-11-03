
from pathlib import Path
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = ROOT / "models" / "cafe_demand_model.joblib"
DATA_PATH = ROOT / "data" / "processed" / "hourly_sales.csv"


def predict_demand(store, date, hour):
    """Predict next-day hourly beverage sales."""

    model = joblib.load(MODEL_PATH)

    history = pd.read_csv(
        DATA_PATH,
        parse_dates=["transaction_date"]
    )

    forecast_date = pd.Timestamp(date)

    if store not in history["store_location"].unique():
        raise ValueError("Unknown store location")

    if not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23")

    # only support the next day after available history
    last_date = history["transaction_date"].max()

    if forecast_date != last_date + pd.Timedelta(days=1):
        raise ValueError(
            "Forecast date must be the day after "
            f"the latest recorded date ({last_date.date()})"
        )

    store_history = history[
        (history["store_location"] == store) &
        (history["hour"] == hour) &
        (history["transaction_date"] < forecast_date)
    ]

    sales_by_date = store_history.set_index(
        "transaction_date"
    )["drinks_sold"]

    # collect previous 7 calendar days
    previous_sales = []

    for days in range(1, 8):
        previous_date = (
            forecast_date - pd.Timedelta(days=days)
        )

        sales = sales_by_date.get(previous_date, float("nan"))
        previous_sales.append(sales)

    # match the complete-case rule used in training
    if pd.isna(previous_sales[0]) or pd.isna(previous_sales[6]):
        raise ValueError(
            "Insufficient history: day-1 and day-7 "
            "sales are required for this store-hour."
        )

    # construct model features
    features = pd.DataFrame([{
        "store_location": store,
        "hour": hour,
        "day_of_week": forecast_date.dayofweek,
        "month": forecast_date.month,
        "sales_lag_1d": previous_sales[0],
        "sales_lag_7d": previous_sales[6],
        "rolling_mean_7d": pd.Series(previous_sales).mean()
    }])

    # generate prediction
    prediction = model.predict(features)[0]

    return round(max(0, float(prediction)), 2)


if __name__ == "__main__":
    result = predict_demand(
        store="Astoria",
        date="2023-07-01",
        hour=10
    )

    print(f"Predicted demand: {result} drinks")
