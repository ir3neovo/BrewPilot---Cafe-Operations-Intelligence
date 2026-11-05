# BrewPilot — Café Operations Intelligence

A full-stack machine learning application that forecasts hourly beverage demand for three café locations and evaluates predictions as new sales data arrives.

**[Live Demo](https://cafe-demand-dashboard.onrender.com/)** · **[Dataset](https://mavenanalytics.io/data-playground/coffee-shop-sales)**

The updates described below are running locally. The hosted demo may run an earlier version until redeployed.

## Features

- Forecast demand for Astoria, Hell's Kitchen, and Lower Manhattan.
- Choose dates 1–30 days after each café's latest recorded sales.
- Visualize hourly demand, predicted totals, peak hours, and coverage.
- Replay June actuals one day at a time using a separate demo history.
- Compare forecasts with actuals using MAE, RMSE, coverage, and per-café results.
- Export hourly comparisons and daily evaluation reports.

## Dataset

BrewPilot uses [Coffee Shop Sales from Maven Analytics](https://mavenanalytics.io/data-playground/coffee-shop-sales), containing historical transactions from three fictional New York City cafés during January–June 2023.

Coffee, tea, and drinking chocolate transactions are aggregated into quantities per date, café, and hour. Forecasts measure drinks sold, not revenue. This historical dataset is not a live POS feed. Regular updates are demonstrated through historical replay.

## Forecasting approach

Linear Regression with a 7-day rolling average was selected after comparisons with historical baselines, original Linear Regression, Random Forest, and XGBoost.

Inputs include café location, hour, day of week, month, previous-day sales, previous-week sales, and the mean over the preceding seven calendar days for the same café-hour.

Required day-1 and day-7 observations must be present. Hours without required history are excluded rather than filled with zero. Later forecast dates use earlier predictions recursively to construct lag and rolling inputs. Predictions are never saved as actual sales. Importing new actuals updates inputs without retraining the model.

## Evaluation

### Original held-out comparison

Evaluated on June 2023 observations:

| Model | MAE | RMSE |
|---|---:|---:|
| Weighted Historical Baseline | 11.67 | 16.11 |
| Original Linear Regression | 11.02 | 14.91 |
| **Linear Regression + Rolling Average** | **10.90** | **14.78** |

### June replay results

Starting with history through May 31, each June day is forecast before its actuals are imported. The fitted model remains fixed.

| Metric | Result |
|---|---:|
| Days imported | 30 |
| MAE | 10.90 |
| RMSE | 14.78 |
| Scored café-hours | 1,060 |
| Observed café-hours | 1,138 |
| Scored coverage | 93.1% |

| Café | Scored hours | MAE | RMSE |
|---|---:|---:|---:|
| Astoria | 333 | 11.59 | 14.80 |
| Hell's Kitchen | 378 | 11.14 | 16.05 |
| Lower Manhattan | 349 | 9.98 | 13.25 |

Errors are **drinks per matched café-hour**, not daily-total errors. Missing actuals are not counted as zero; 15 additional forecast hours had no observed actual and were excluded from scoring. This replay reproduces the original one-day evaluation. It is not a new independent test or validation of multi-day accuracy.

## Tech stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Recharts |
| Backend | Python, FastAPI, Uvicorn |
| Data and serving | pandas, NumPy, scikit-learn, joblib |
| Deployment | Render, GitHub |

The saved model uses scikit-learn **1.8.0**, pinned in `requirements.txt`.

## Limitations and next steps

- Backtest multi-day forecasts: recursive errors can compound.
- Add model drift monitoring and retraining; imports currently update inputs only.
- Improve coverage where required historical lags are missing.
- Explore staffing and inventory recommendations and peak-hour accuracy improvements.
