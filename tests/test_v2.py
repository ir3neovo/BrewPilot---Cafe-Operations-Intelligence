import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src import api, predict, sales_store


class ConstantModel:
    def predict(self, frame):
        return [14.5] * len(frame)


@pytest.fixture
def demo_database(tmp_path, monkeypatch):
    days = pd.date_range("2023-06-01", "2023-06-30", freq="D")
    rows = [
        {"transaction_date": d, "store_location": store, "hour": hour, "drinks_sold": 12}
        for d in days for store in ("Astoria", "Hell's Kitchen", "Lower Manhattan")
        for hour in (10, 11)
    ]
    baseline = tmp_path / "hourly_sales.csv"
    pd.DataFrame(rows).to_csv(baseline, index=False)
    monkeypatch.setattr(sales_store, "BASELINE", baseline)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sales.db'}")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setattr(predict, "load_model", lambda: ConstantModel())
    sales_store.read_baseline.cache_clear()
    sales_store.engine.cache_clear()
    yield
    sales_store.read_baseline.cache_clear()
    sales_store.engine.cache_clear()


def test_initial_forecast_bounds(demo_database):
    status = sales_store.data_status()
    assert status["stores"][0]["min_forecast_date"] == "2023-07-01"
    assert status["stores"][0]["max_forecast_date"] == "2023-07-07"


def test_recursive_forecasting_and_horizon(demo_database):
    assert predict.predict_demand("Astoria", "2023-07-01", 10) == 14.5
    assert predict.predict_demand("Astoria", "2023-07-07", 10) == 14.5
    with pytest.raises(ValueError, match="1–7 days"):
        predict.predict_demand("Astoria", "2023-07-08", 10)


def test_csv_import_is_idempotent(demo_database):
    csv = b"transaction_id,transaction_date,transaction_time,store_location,product_category,transaction_qty\nT101,2023-07-01,10:05:00,Astoria,Coffee,3\n"
    assert sales_store.import_transactions(csv)["processed_records"] == 1
    assert sales_store.import_transactions(csv)["processed_records"] == 1
    hist = sales_store.get_history()
    updated = hist[(hist["store_location"] == "Astoria") & (hist["transaction_date"] == pd.Timestamp("2023-07-01"))]
    assert len(updated) == 1
    assert int(updated.iloc[0]["drinks_sold"]) == 3
    assert predict.predict_demand("Astoria", "2023-07-02", 10) == 14.5


def test_baseline_overlap_rejected(demo_database):
    csv = b"transaction_id,transaction_date,transaction_time,store_location,product_category,transaction_qty\nT100,2023-06-30,10:05:00,Astoria,Coffee,3\n"
    with pytest.raises(ValueError, match="double-counted"):
        sales_store.import_transactions(csv)


def test_upload_requires_token(demo_database, monkeypatch):
    monkeypatch.setenv("API_ADMIN_TOKEN", "test-secret")
    client = TestClient(api.app)
    response = client.post(
        "/sales/upload",
        files={"file": ("sales.csv", b"transaction_id,transaction_date\n", "text/csv")},
    )
    assert response.status_code == 403
