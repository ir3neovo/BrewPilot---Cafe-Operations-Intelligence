"""Persistence for incremental sales imports, layered on the original hourly CSV.

Set DATABASE_URL to persistent PostgreSQL on a deployed app. Local SQLite is
for development only; free Render instances do NOT preserve local SQLite data.
"""
from __future__ import annotations

import io
import os
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Column, Date, Integer, MetaData, String, Table, create_engine, select
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "processed" / "hourly_sales.csv"
BEVERAGE_CATEGORIES = {"Coffee", "Tea", "Drinking Chocolate"}
REQUIRED = {
    "transaction_id", "transaction_date", "transaction_time",
    "store_location", "product_category", "transaction_qty",
}

metadata = MetaData()
transactions = Table(
    "sales_transactions", metadata,
    Column("transaction_id", String(100), primary_key=True),
    Column("transaction_date", Date, nullable=False, index=True),
    Column("transaction_time", String(12), nullable=False),
    Column("store_location", String(120), primary_key=True, index=True),
    Column("product_category", String(120), nullable=False),
    Column("transaction_qty", Integer, nullable=False),
)


@lru_cache(maxsize=1)
def engine():
    default = f"sqlite:///{(ROOT / 'data' / 'sales_updates.db').as_posix()}"
    if os.getenv("RENDER") and not os.getenv("DATABASE_URL"):
        raise RuntimeError("Render deployment requires persistent DATABASE_URL; local SQLite would be lost")
    url = os.getenv("DATABASE_URL", default)
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    db = create_engine(url, pool_pre_ping=True)
    metadata.create_all(db)
    return db


@lru_cache(maxsize=1)
def read_baseline() -> pd.DataFrame:
    df = pd.read_csv(BASELINE, parse_dates=["transaction_date"])
    required = {"transaction_date", "store_location", "hour", "drinks_sold"}
    if not required.issubset(df.columns):
        raise ValueError(f"Baseline CSV must contain {sorted(required)}")
    df = df[list(required)].copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.normalize()
    return df


def latest_baseline_date():
    return read_baseline()["transaction_date"].max().date()


def import_transactions(csv_bytes: bytes) -> dict:
    """Upsert distinct (store, transaction line ID) pairs. Uploaded rows must be AFTER baseline.

    Each CSV must contain individual transaction line IDs (not daily summaries).
    Repeated uploads are idempotent and corrected transaction line IDs are updated.
    """
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes), dtype={"transaction_id": "string"})
    except Exception as exc:
        raise ValueError(f"Cannot parse CSV: {exc}") from exc
    missing = REQUIRED.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")
    if df.empty:
        raise ValueError("CSV contains no transactions")
    df = df[list(REQUIRED)].copy()
    if df.isna().any().any():
        raise ValueError("Required sales columns cannot have empty values")
    df["transaction_id"] = df["transaction_id"].astype(str).str.strip()
    df["store_location"] = df["store_location"].astype(str).str.strip()
    df["product_category"] = df["product_category"].astype(str).str.strip()
    if (df["transaction_id"] == "").any() or (df["store_location"] == "").any():
        raise ValueError("Transaction IDs and stores must not be blank")
    if df["transaction_id"].str.len().gt(100).any() or df["store_location"].str.len().gt(120).any():
        raise ValueError("Transaction ID or store name is too long")
    try:
        dates = pd.to_datetime(df["transaction_date"], format="%Y-%m-%d", errors="raise")
        timedeltas = pd.to_timedelta(df["transaction_time"].astype(str), errors="raise")
        qty = pd.to_numeric(df["transaction_qty"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid date, time or quantity: {exc}") from exc
    if ((timedeltas < pd.Timedelta(0)) | (timedeltas >= pd.Timedelta(days=1))).any():
        raise ValueError("Transaction time must be within 00:00–23:59")
    if ((qty <= 0) | (qty % 1 != 0)).any():
        raise ValueError("Transaction quantities must be positive whole numbers")
    if (dates.dt.date <= latest_baseline_date()).any():
        raise ValueError(
            f"Uploaded transactions must be dated after the original baseline "
            f"({latest_baseline_date()}); otherwise sales would be double-counted"
        )
    if df["product_category"].str.len().gt(120).any():
        raise ValueError("Product category is too long")
    df["transaction_date"] = dates.dt.date
    df["transaction_time"] = timedeltas.astype(str)
    df["transaction_qty"] = qty.astype(int)
    df = df.drop_duplicates(subset=["store_location", "transaction_id"], keep="last")
    records = df.to_dict(orient="records")
    db = engine()
    with db.begin() as conn:
        dialect = conn.dialect.name
        if dialect not in {"sqlite", "postgresql"}:
            raise ValueError("Only SQLite and PostgreSQL are supported")
        builder = sqlite_insert if dialect == "sqlite" else pg_insert
        for offset in range(0, len(records), 500):
            batch = records[offset:offset + 500]
            stmt = builder(transactions).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["store_location", "transaction_id"],
                set_={c: getattr(stmt.excluded, c) for c in REQUIRED if c not in {"store_location", "transaction_id"}},
            )
            conn.execute(stmt)
    return {"processed_records": len(records), "latest_uploaded_date": str(max(df["transaction_date"]))}


def get_history() -> pd.DataFrame:
    """Original hourly history + newly imported transaction aggregates."""
    baseline = read_baseline().copy()
    with engine().connect() as conn:
        rows = conn.execute(select(
            transactions.c.transaction_date, transactions.c.transaction_time,
            transactions.c.store_location, transactions.c.product_category,
            transactions.c.transaction_qty,
        )).fetchall()
    if not rows:
        return baseline
    new = pd.DataFrame(rows, columns=[
        "transaction_date", "transaction_time", "store_location",
        "product_category", "transaction_qty",
    ])
    new = new[new["product_category"].isin(BEVERAGE_CATEGORIES)].copy()
    if new.empty:
        return baseline
    new["transaction_date"] = pd.to_datetime(new["transaction_date"])
    new["hour"] = pd.to_timedelta(new["transaction_time"]).dt.components.hours
    aggregated = (new.groupby(["transaction_date", "store_location", "hour"], as_index=False)
                  ["transaction_qty"].sum().rename(columns={"transaction_qty": "drinks_sold"}))
    return pd.concat([baseline, aggregated], ignore_index=True).sort_values(
        ["transaction_date", "store_location", "hour"]
    ).reset_index(drop=True)


def data_status() -> dict:
    history = get_history()
    stores = []
    for name, group in history.groupby("store_location"):
        latest = group["transaction_date"].max().date()
        stores.append({
            "name": name,
            "latest_sale_date": str(latest),
            "min_forecast_date": str(latest + timedelta(days=1)),
            "max_forecast_date": str(latest + timedelta(days=7)),
        })
    return {"stores": stores, "baseline_latest_date": str(latest_baseline_date())}
