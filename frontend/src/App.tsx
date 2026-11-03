
import { useState } from "react";
import ModelPerformance from "./ModelPerformance";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

import "./App.css";

type HourlyForecast = {
  hour: number;
  predicted_drinks: number;
};

type SkippedHour = {
  hour: number;
  reason: string;
};

type ForecastResponse = {
  store: string;
  date: string;
  forecasts: HourlyForecast[];
  skipped_hours: SkippedHour[];
};


const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const FORECAST_DATE = "2023-07-01";

const stores = [
  "Astoria",
  "Hell's Kitchen",
  "Lower Manhattan",
];

function formatHour(hour: number): string {
  const suffix = hour >= 12 ? "PM" : "AM";
  const formatted = hour % 12 || 12;
  return `${formatted} ${suffix}`;
}

function App() {
  const [store, setStore] = useState("Astoria");

  const [result, setResult] =
    useState<ForecastResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handlePredict() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        `${API_URL}/predict/day`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            store: store,
            date: FORECAST_DATE,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to generate forecast."
        );
      }

      setResult(data as ForecastResponse);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred."
      );
    } finally {
      setLoading(false);
    }
  }

  const peak = result
    ? result.forecasts.reduce<HourlyForecast | null>(
        (best, point) =>
          !best ||
          point.predicted_drinks > best.predicted_drinks
            ? point
            : best,
        null
      )
    : null;

  const totalDemand = result
  ? result.forecasts.reduce(
      (sum, item) => sum + item.predicted_drinks,
      0
    )
  : 0;

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <span className="eyebrow">
          MACHINE LEARNING PROJECT
        </span>
        <h1>☕ Café Demand Forecasting</h1>
        <p>
          Forecast hourly beverage demand using historical
          sales and machine learning.
        </p>
      </header>

      <section className="panel">
        <h2>Generate a Forecast</h2>

        <div className="controls">
          <div className="field">
            <label htmlFor="store">
              Café Location
            </label>

            <select
              id="store"
              value={store}
              onChange={(e) => setStore(e.target.value)}
            >
              {stores.map((location) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label>Forecast Date</label>
            <div className="read-only-date">
              July 1, 2023
            </div>
          </div>

          <button
            type="button"
            onClick={handlePredict}
            disabled={loading}
          >
            {loading
              ? "Predicting..."
              : "Generate Forecast"}
          </button>
        </div>

        <p className="helper-text">
          Historical demonstration: forecasts the day
          immediately after the available sales data.
        </p>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </section>

      {result && (
        <>
          <section className="stats">

            <div className="stat-card">
              <span>Forecasted Beverage Sales</span>
              <strong>{Math.round(totalDemand)}</strong>
              <small>Drinks across forecasted hours</small>
            </div>
            <div className="stat-card">
              <span>Predicted Peak Hour</span>
              <strong>
                {peak ? formatHour(peak.hour) : "N/A"}
              </strong>
            </div>

            <div className="stat-card">
              <span>Peak Hour Demand</span>
              <strong>
                {peak
                  ? peak.predicted_drinks.toFixed(1)
                  : "N/A"}
              </strong>
              <small>Drinks per hour</small>
            </div>

            <div className="stat-card">
              <span>Forecast Coverage</span>
              <strong>{result.forecasts.length}</strong>
              <small>Hours with predictions</small>
            </div>
          </section>

          <section className="panel">
            <h2>Hourly Demand Forecast</h2>
            <p className="chart-description">
              {result.store} · July 1, 2023
            </p>

            <div className="chart-container">
              <ResponsiveContainer width="100%" height={330}>
                <LineChart data={result.forecasts}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#dce3d5"
                  />

                  <XAxis
                    dataKey="hour"
                    tickFormatter={(hour) =>
                      formatHour(Number(hour))
                    }
                  />

                  <YAxis
                    allowDecimals={false}
                  />

                  <Tooltip
                    labelFormatter={(hour) =>
                      formatHour(Number(hour))
                    }
                    formatter={(value) => [
                      `${Number(value).toFixed(1)} drinks`,
                      "Predicted demand",
                    ]}
                  />

                  <Line
                    type="monotone"
                    dataKey="predicted_drinks"
                    stroke="#788832"
                    strokeWidth={3}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {result.skipped_hours.length > 0 && (
              <div className="notice">
                <strong>Unavailable hours</strong>
                <p>
                  {result.skipped_hours
                    .map((item) => formatHour(item.hour))
                    .join(", ")}
                </p>
                <small>
                  These hours were skipped because the
                  required historical sales were unavailable.
                </small>
              </div>
            )}
          </section>
        </>
      )}
      <ModelPerformance />
    </main>
  );
}

export default App;
