import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from src import predict
from src.api import app
from src.sales import import_sales, validate_sales


class EchoModel:
    def predict(self, features):
        return features.sales_lag_1d + 1


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame({
            "transaction_date": pd.date_range("2023-06-24", periods=7),
            "store_location": "Astoria", "hour": 10, "drinks_sold": 20,
        })
        self.real_loader = predict.load_history
        self.history_patch = patch.object(predict, "load_history", return_value=self.history)
        self.model_patch = patch.object(predict, "load_model", return_value=EchoModel())
        self.history_patch.start()
        self.model_patch.start()
        self.addCleanup(self.history_patch.stop)
        self.addCleanup(self.model_patch.stop)

    def test_recursive_forecast_and_actuals_unchanged(self):
        result = predict.predict_day("Astoria", "2023-07-08")
        self.assertEqual(result["forecasts"][0]["predicted_drinks"], 28)
        self.assertTrue(result["uses_recursive_predictions"])
        self.assertEqual(len(self.history), 7)
        self.assertEqual(predict.predict_demand("Astoria", "2023-07-30", 10), 50)

    def test_boundaries_and_unknown_store(self):
        for store, day in [("Astoria", "2023-06-30"), ("Astoria", "2023-07-31"), ("unknown", "2023-07-01")]:
            with self.assertRaises(ValueError):
                predict.predict_day(store, day)

    def test_missing_lag_is_not_zero_filled(self):
        self.history.drop(index=0, inplace=True)
        with self.assertRaises(ValueError):
            predict.predict_day("Astoria", "2023-07-01")

    def test_store_specific_dates_and_api(self):
        other = self.history.copy()
        other["store_location"] = "Other"
        other["transaction_date"] += pd.Timedelta(days=2)
        self.history = pd.concat([self.history, other])
        with patch.object(predict, "load_history", return_value=self.history):
            client = TestClient(app)
            self.assertEqual(client.get("/forecast/options").json()["stores"][0]["min_date"], "2023-07-01")
            response = client.post("/predict/day", json={"store": "Astoria", "date": "2023-07-02"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["horizon_days"], 2)
            self.assertEqual(client.post("/predict/day", json={"store": "Astoria", "date": "2023-07-31"}).status_code, 400)

    def test_idempotent_import_and_live_reload(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as folder:
            destination, source = Path(folder) / "history.csv", Path(folder) / "update.csv"
            self.history.to_csv(destination, index=False)
            update = self.history.iloc[[-1]].copy()
            update["drinks_sold"] = 99
            update.to_csv(source, index=False)
            import_sales(source, destination)
            import_sales(source, destination)
            loaded = pd.read_csv(destination)
            self.assertEqual(len(loaded), 7)
            self.assertEqual(loaded.iloc[-1].drinks_sold, 99)
            with patch.object(predict, "DATA_PATH", destination):
                # Call the real loader despite the forecast fixture patch.
                self.assertEqual(self.real_loader().iloc[-1].drinks_sold, 99)
                update["drinks_sold"] = 101
                update.to_csv(source, index=False)
                import_sales(source, destination)
                self.assertEqual(self.real_loader().iloc[-1].drinks_sold, 101)
            update["drinks_sold"] = -1
            update.to_csv(source, index=False)
            before = destination.read_bytes()
            with self.assertRaises(ValueError):
                import_sales(source, destination)
            self.assertEqual(destination.read_bytes(), before)

    def test_reject_duplicate_and_invalid_rows(self):
        for data in [pd.concat([self.history, self.history]), self.history.assign(hour=24), self.history.assign(drinks_sold=float("inf"))]:
            with self.assertRaises(ValueError):
                validate_sales(data)


if __name__ == "__main__":
    unittest.main()
