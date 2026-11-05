import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const modelResults = [
  {
    name: "Weighted Avg",
    MAE: 11.67,
    RMSE: 16.11,
  },
  {
    name: "Original Linear",
    MAE: 11.02,
    RMSE: 14.91,
  },
  {
    name: "Rolling Linear",
    MAE: 10.90,
    RMSE: 14.78,
  },
];

function ModelPerformance() {
  return (
    <section className="panel performance-section">
      <h2>Model Performance</h2>

      <p className="chart-description">
        Final evaluation on 1,060 hourly observations
        from June 2023. These one-day results do not measure multi-day forecast accuracy.
      </p>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height={330}>
          <BarChart data={modelResults}>
            <CartesianGrid strokeDasharray="3 3" />

            <XAxis dataKey="name" />
            <YAxis />

            <Tooltip />
            <Legend />

            <Bar
              dataKey="MAE"
              fill="#788832"
              radius={[5, 5, 0, 0]}
            />

            <Bar
              dataKey="RMSE"
              fill="#c9a77b"
              radius={[5, 5, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="model-insight">
        <h3>Key Findings</h3>
        <p>
          Linear Regression with a seven-day rolling
          average achieved the lowest overall test error,
          outperforming both the original Linear Regression
          and weighted historical-sales baseline.
        </p>
        <p>
          The selected model achieved a test MAE of
          10.90 drinks per hour. Morning demand remains
          more difficult to predict, with an MAE of 15.73
          during 7–10 AM.
        </p>
      </div>
    </section>
  );
}

export default ModelPerformance;
