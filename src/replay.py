"""Replay June actual sales, forecasting each day before importing its actuals."""
import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd

from src.predict import predict_day
from src.sales import ROOT, import_sales, validate_sales

DEFAULT_DIRECTORY = ROOT / "data/demo"
SOURCE = ROOT / "data/processed/hourly_sales.csv"
START = pd.Timestamp("2023-06-01")
END = pd.Timestamp("2023-06-30")


def write_json(path, value):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def initialize(directory=DEFAULT_DIRECTORY, source=SOURCE):
    directory, source = Path(directory).resolve(), Path(source).resolve()
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Demo directory is not empty. Choose a new --directory to start another replay.")
    data = validate_sales(pd.read_csv(source))
    initial = data[data.transaction_date < START]
    june = data[data.transaction_date.between(START, END)]
    if initial.empty or set(june.transaction_date) != set(pd.date_range(START, END)):
        raise ValueError("Source must include pre-June history and actuals for every June 2023 date")
    for store, group in initial.groupby("store_location"):
        if group.transaction_date.max() != START - pd.Timedelta(days=1):
            raise ValueError(f"{store} must have sales through May 31")
    directory.mkdir(parents=True, exist_ok=True)
    initial.to_csv(directory / "history.csv", index=False, date_format="%Y-%m-%d")
    june.to_csv(directory / "june_actuals.csv", index=False, date_format="%Y-%m-%d")
    write_json(directory / "replay.json", {"description": "Maven historical replay", "start": "2023-06-01", "end": "2023-06-30"})
    return status(directory)


def metrics(rows):
    if not rows:
        return {"scored_hours": 0, "mae": None, "rmse": None}
    errors = np.array([row["predicted_drinks"] - row["actual_drinks"] for row in rows])
    return {"scored_hours": len(rows), "mae": round(float(np.abs(errors).mean()), 4),
            "rmse": round(float(np.sqrt((errors ** 2).mean())), 4)}


def status(directory=DEFAULT_DIRECTORY):
    directory = Path(directory)
    if not (directory / "replay.json").exists():
        raise ValueError("Initialize this replay directory first")
    history = validate_sales(pd.read_csv(directory / "history.csv"))
    through = history.transaction_date.max()
    days, rows = [], []
    for path in sorted(directory.glob("forecast-*.json")):
        day = json.loads(path.read_text(encoding="utf-8"))
        # A forecast saved before an interrupted import is not scored yet.
        if pd.Timestamp(day["date"]) <= through:
            days.append({"date": day["date"], "actual_hours": day["actual_hours"],
                         "forecast_hours": day["forecast_hours"], **metrics(day["rows"])})
            rows.extend(day["rows"])
    next_date = through + pd.Timedelta(days=1)
    return {"enabled": True, "history_through": str(through.date()),
            "next_import_date": str(next_date.date()) if next_date <= END else None,
            "days_imported": len(days), "actual_hours": sum(day["actual_hours"] for day in days),
            "forecast_hours": sum(day["forecast_hours"] for day in days),
            **metrics(rows), "daily": days,
            "by_store": [{"store": store, **metrics([row for row in rows if row["store"] == store])}
                         for store in sorted(history.store_location.unique())]}


def advance(directory=DEFAULT_DIRECTORY):
    directory = Path(directory).resolve()
    current = status(directory)
    if current["next_import_date"] is None:
        return current
    date = current["next_import_date"]
    june = validate_sales(pd.read_csv(directory / "june_actuals.csv"))
    actuals = june[june.transaction_date == pd.Timestamp(date)]
    if actuals.empty:
        raise ValueError(f"No actual sales available for {date}")
    history = validate_sales(pd.read_csv(directory / "history.csv"))
    rows, forecast_hours, unavailable = [], 0, []
    # Supply the isolated history explicitly. This also avoids reading future actuals.
    for store in sorted(history.store_location.unique()):
        try:
            forecast = predict_day(store, date, history=history)
        except ValueError as error:
            unavailable.append({"store": store, "reason": str(error)})
            continue
        forecast_hours += len(forecast["forecasts"])
        for point in forecast["forecasts"]:
            actual = actuals[(actuals.store_location == store) & (actuals.hour == point["hour"])]
            if not actual.empty:
                rows.append({"date": date, "store": store, "hour": point["hour"],
                             "predicted_drinks": point["predicted_drinks"],
                             "actual_drinks": float(actual.iloc[0].drinks_sold)})
    # Save predictions before importing actuals. A retry safely recomputes an unimported day.
    write_json(directory / f"forecast-{date}.json", {"date": date, "rows": rows,
               "actual_hours": len(actuals), "forecast_hours": forecast_hours, "unavailable": unavailable})
    batch = directory / "pending-import.csv"
    actuals.to_csv(batch, index=False, date_format="%Y-%m-%d")
    import_sales(batch, directory / "history.csv")
    batch.unlink()
    export_reports(directory)
    return status(directory)


def export_reports(directory=DEFAULT_DIRECTORY):
    directory = Path(directory)
    result = status(directory)
    rows = []
    for path in sorted(directory.glob("forecast-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["date"] <= result["history_through"]:
            rows.extend(record["rows"])
    pd.DataFrame(rows, columns=["date", "store", "hour", "predicted_drinks", "actual_drinks"]).to_csv(directory / "comparison.csv", index=False)
    pd.DataFrame(result["daily"]).to_csv(directory / "daily_metrics.csv", index=False)
    write_json(directory / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "next", "run", "status", "report"])
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--source", type=Path, default=SOURCE, help="Original hourly sales CSV for init")
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(args.directory, args.source)
        elif args.command == "next":
            result = advance(args.directory)
        elif args.command == "run":
            result = status(args.directory)
            while result["next_import_date"]:
                result = advance(args.directory)
                print(f"Imported through {result['history_through']}; MAE={result['mae']}")
        elif args.command == "report":
            result = export_reports(args.directory)
        else:
            result = status(args.directory)
        print(json.dumps(result, indent=2))
    except ValueError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
