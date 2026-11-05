import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src import replay
from src.predict import ROOT


class ReplayTests(unittest.TestCase):
    def test_separate_history_import_order_and_evaluation(self):
        original = replay.SOURCE.read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as folder:
            directory = Path(folder) / "demo"
            self.assertEqual(replay.initialize(directory)["history_through"], "2023-05-31")
            def forecast(store, date, history):
                self.assertLess(history.transaction_date.max(), pd.Timestamp(date))
                return {"forecasts": [{"hour": 10, "predicted_drinks": 0}]}
            with patch.object(replay, "predict_day", side_effect=forecast):
                first = replay.advance(directory)
                self.assertEqual(first["history_through"], "2023-06-01")
                self.assertEqual(first["days_imported"], 1)
                self.assertEqual(first["scored_hours"], 2)
                self.assertGreater(first["mae"], 0)
                second = replay.advance(directory)
                self.assertEqual(second["history_through"], "2023-06-02")
                self.assertEqual(second["days_imported"], 2)
            self.assertTrue((directory / "comparison.csv").exists())
            with self.assertRaises(ValueError):
                replay.initialize(directory)
        self.assertEqual(replay.SOURCE.read_bytes(), original)

    def test_metrics_use_matching_hours(self):
        self.assertEqual(replay.metrics([])["mae"], None)
        result = replay.metrics([{"predicted_drinks": 4, "actual_drinks": 1},
                                 {"predicted_drinks": 1, "actual_drinks": 5}])
        self.assertEqual(result["mae"], 3.5)
        self.assertAlmostEqual(result["rmse"], 3.5355)


if __name__ == "__main__":
    unittest.main()
