
import { useEffect, useState } from "react";
import ModelPerformance from "./ModelPerformance";
import ReplayEvaluation from "./ReplayEvaluation";
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
type StoreOptions = { store: string; latest_date: string; min_date: string; max_date: string };



function formatHour(hour: number): string {
  const suffix = hour >= 12 ? "PM" : "AM";
  const formatted = hour % 12 || 12;
  return `${formatted} ${suffix}`;
}

function App() {
  const [store, setStore] = useState("");
  const [options, setOptions] = useState<StoreOptions[]>([]);
  const [forecastDate, setForecastDate] = useState("");
  const selected = options.find((item) => item.store === store);

  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetch(API_URL + "/forecast/options")
      .then(async (response) => {
        if (!response.ok) throw new Error("Unable to load available forecast dates.");
        return response.json();
      })
      .then((data: { stores: StoreOptions[] }) => {
        if (!active) return;
        if (!data.stores.length) throw new Error("No sales history is available.");
        setOptions(data.stores);
        setStore(data.stores[0].store);
        setForecastDate(data.stores[0].min_date);
      })
      .catch((err: Error) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  const [result, setResult] =
    useState<ForecastResponse | null>(null);

  const [loading, setLoading] = useState(false);


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
            date: forecastDate,
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
        <button type="button" disabled={loading} onClick={() => window.location.reload()}>Refresh sales data</button>

        <div className="controls">
          <div className="field">
            <label htmlFor="store">
              Café Location
            </label>

            <select
              id="store"
              value={store}
              disabled={loading}
              onChange={(e) => {
                setStore(e.target.value);
                setForecastDate(options.find((item) => item.store === e.target.value)?.min_date || "");
                setResult(null);
              }}
            >
              {options.map(({ store: location }) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="forecast-date">Forecast Date</label>
            <input id="forecast-date" type="date" value={forecastDate}
              min={selected?.min_date} max={selected?.max_date} disabled={loading || !selected}
              onChange={(e) => { setForecastDate(e.target.value); setResult(null); }} />
          </div>

          <button
            type="button"
            onClick={handlePredict}
            disabled={loading || !selected || !forecastDate || forecastDate < selected.min_date || forecastDate > selected.max_date}
          >
            {loading
              ? "Predicting..."
              : "Generate Forecast"}
          </button>
        </div>

        <p className="helper-text">
          Sales history through {selected?.latest_date || "loading…"}. Choose up to 30 days ahead.
          Later dates use earlier predictions; uncertainty increases with the forecast horizon.
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
              {result.store} · {result.date}
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
      <ReplayEvaluation apiUrl={API_URL} />
      <ModelPerformance />
    </main>
  );
}

export default App;
