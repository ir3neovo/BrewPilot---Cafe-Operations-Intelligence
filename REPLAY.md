# Historical sales replay

The demo history is separate from the original data. Run all commands in the project root.

1. Initialize once: `py -m src.replay init`. This copies sales through May 31 into
   `data/demo/history.csv` and June actuals into a separate replay input. Reinitializing
   a nonempty folder is rejected. Use `--directory data/another-demo` for another run.
2. Stop the API using Ctrl+C, then in the same PowerShell terminal run:

```powershell
$env:BREWPILOT_HISTORY_PATH = (Resolve-Path .\data\demo\history.csv).Path
py -m uvicorn src.api:app --reload
```

3. Keep the frontend running. Refresh the dashboard. History should end May 31 and
   June 1 should be the default forecast date. Generate that forecast.
4. In another terminal at the project root, run `py -m src.replay next`.
   This forecasts June 1 from May history, saves those predictions, then imports June 1 actuals.
5. Click **Refresh sales data** in the dashboard. History advances to June 1 and the
   default forecast date becomes June 2. The June Sales Replay panel shows cumulative
   accuracy and coverage. Repeat `py -m src.replay next` to import another day.
6. Optional: `py -m src.replay run` imports every remaining June date sequentially.
   `py -m src.replay status` prints progress. `py -m src.replay report` regenerates reports.

Reports in `data/demo/`:
- `comparison.csv`: hourly predictions and observed actuals for matched store-hours.
- `daily_metrics.csv`: per-day MAE, RMSE, and coverage counts.
- `summary.json`: aggregate and per-store results.

The fitted model stays fixed. Forecasts use only earlier actuals; June sales are imported
only after that day's forecast is saved. Missing actuals are not treated as zero.
MAE/RMSE are drinks per matched store-hour, not daily-total errors. Unscored observed
hours and forecasts without actuals are reflected in coverage. Run one replay process
at a time. Do not manually edit demo history or add ordinary sales imports to it.

Validated full June result (rounded predictions): MAE 10.8966, RMSE 14.7845,
1,060 scored hours / 1,138 observed hours (93.15%). There were 1,075 forecast hours,
including 15 with no observed actual. These are one-day replay scores, not multi-day validation.

To return to the original history, stop the API and run:

```powershell
Remove-Item Env:BREWPILOT_HISTORY_PATH -ErrorAction SilentlyContinue
py -m uvicorn src.api:app --reload
```
