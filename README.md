
# ☕ Café Demand Forecasting - BrewPilot

A full-stack machine learning application that predicts hourly beverage sales for coffee shops using historical transaction data.

**[🚀 Live Demo](https://cafe-demand-dashboard.onrender.com/)** | **[📊 Dataset](https://mavenanalytics.io/data-playground/coffee-shop-sales)**

## Overview

This project explores how machine learning can help cafés anticipate beverage demand and support inventory and staffing decisions.

The interactive dashboard allows users to:
- Select between three café locations.
- Generate hourly beverage sales forecasts.
- Visualize demand patterns and identify peak hours.
- View predicted sales totals and model performance.

## Dataset

**Source:** [Coffee Shop Sales — Maven Analytics](https://mavenanalytics.io/data-playground/coffee-shop-sales)

The dataset contains historical transactions from three fictional coffee shops in New York City, covering January–June 2023.

The project focuses on coffee, tea, and drinking chocolate sales.

## Machine Learning Approach

**Feature Engineering**
- Time features: hour, day of week, and month.
- Historical sales: previous-day and previous-week demand.
- Rolling average: sales over the preceding seven days.

**Model Development**

Compared historical baselines, Linear Regression, Random Forest, and XGBoost. Linear Regression with a seven-day rolling average was selected based on validation performance.

### Final Model Performance

Evaluated on a held-out June 2023 test set.

| Model | MAE | RMSE |
|---|---:|---:|
| Weighted Historical Baseline | 11.67 | 16.11 |
| Original Linear Regression | 11.02 | 14.91 |
| **Linear Regression + Rolling Average** | **10.90** | **14.78** |

*Errors are measured in drinks per observed store-hour.*

## Tech Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Recharts |
| Backend | Python, FastAPI |
| Machine Learning | pandas, NumPy, scikit-learn, XGBoost |
| Deployment | Render, GitHub |

## Deployment

The application is deployed on Render using two services:

- **Frontend:** React static site
- **Backend:** FastAPI web service serving ML predictions

**[View Live Application](https://cafe-demand-dashboard.onrender.com/)**

## Limitations & Future Improvements

The current application demonstrates next-day forecasting for July 1, 2023, using the historical dataset. Hours without sufficient historical data are excluded.

Future improvements include:
- Integrating regularly updated sales data.
- Supporting forecasts for additional dates.
- Generating staffing and inventory recommendations.
- Improving prediction accuracy during peak hours.
