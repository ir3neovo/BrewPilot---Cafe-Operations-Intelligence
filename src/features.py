
import pandas as pd

BEVERAGE_CATEGORIES = [
    "Coffee",
    "Tea",
    "Drinking Chocolate"
]

# Aggregate beverage transactions into hourly sales
def build_hourly_sales(df):

    data = df[
        df["product_category"].isin(BEVERAGE_CATEGORIES)
    ].copy()

    data["transaction_date"] = pd.to_datetime(
        data["transaction_date"]
    )

    data["hour"] = pd.to_timedelta(
        data["transaction_time"].astype(str)
    ).dt.components.hours

    hourly = (
        data.groupby(
            ["transaction_date", "store_location", "hour"],
            as_index=False
        )["transaction_qty"]
        .sum()
        .rename(columns={
            "transaction_qty": "drinks_sold"
        })
    )

    return hourly.sort_values(
        ["transaction_date", "store_location", "hour"]
    ).reset_index(drop=True)


# Generate features using historical hourly sales
def build_model_features(hourly):

    features = hourly[
        ["transaction_date", "store_location", "hour",
         "drinks_sold"]
    ].copy()

    features["day_of_week"] = (
        features["transaction_date"].dt.dayofweek
    )

    features["is_weekend"] = (
        features["day_of_week"] >= 5
    ).astype(int)

    features["month"] = (
        features["transaction_date"].dt.month
    )

    # match sales from previous calendar days
    for days in range(1, 8):
        previous = hourly[
            ["transaction_date", "store_location",
             "hour", "drinks_sold"]
        ].copy()

        previous["transaction_date"] += pd.Timedelta(
            days=days
        )

        previous = previous.rename(
            columns={"drinks_sold": f"lag_{days}"}
        )

        features = features.merge(
            previous,
            on=["transaction_date", "store_location", "hour"],
            how="left",
            validate="one_to_one"
        )

    lag_columns = [f"lag_{d}" for d in range(1, 8)]

    features["sales_lag_1d"] = features["lag_1"]
    features["sales_lag_7d"] = features["lag_7"]

    features["rolling_mean_7d"] = (
        features[lag_columns].mean(axis=1)
    )

    features["rolling_count_7d"] = (
        features[lag_columns].notna().sum(axis=1)
    )

    # same complete-case rule as the original experiment
    features = features.dropna(
        subset=["sales_lag_1d", "sales_lag_7d"]
    ).copy()

    return features.drop(
        columns=lag_columns
    ).reset_index(drop=True)
