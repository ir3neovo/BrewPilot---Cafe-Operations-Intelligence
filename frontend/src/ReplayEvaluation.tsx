import { useEffect, useState } from "react";

type Scores = { scored_hours: number; mae: number | null; rmse: number | null };
type ReplayStatus = Scores & {
  enabled: boolean;
  history_through: string;
  next_import_date: string | null;
  days_imported: number;
  actual_hours: number;
  forecast_hours: number;
  by_store: (Scores & { store: string })[];
};

export default function ReplayEvaluation({ apiUrl }: { apiUrl: string }) {
  const [result, setResult] = useState<ReplayStatus | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/replay/status`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Replay evaluation could not be loaded.");
        return response.json() as Promise<ReplayStatus>;
      })
      .then((data) => { if (active) setResult(data); })
      .catch((err: Error) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [apiUrl]);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!result?.enabled) return null;
  return (
    <section className="panel">
      <h2>June Sales Replay</h2>
      <p>Historical demonstration · {result.days_imported} of 30 June days imported</p>
      <p>Sales through {result.history_through}. {result.next_import_date
        ? `Next import: ${result.next_import_date}.`
        : "June replay complete."}</p>
      <p>Each day was forecast before its actual sales were imported. Scores measure one-day forecasts on matched store-hours.</p>
      {result.scored_hours > 0 ? <>
        <p><strong>MAE: {result.mae?.toFixed(2)} drinks</strong> · RMSE: {result.rmse?.toFixed(2)} drinks</p>
        <p>{result.scored_hours} scored hours / {result.actual_hours} observed hours
          ({(100 * result.scored_hours / result.actual_hours).toFixed(1)}% coverage).
          {" "}{result.forecast_hours - result.scored_hours} forecast hours had no observed actual.</p>
        <div className="replay-table-wrapper">
          <table className="replay-table">
            <thead><tr><th>Café</th><th>Scored hours</th><th>MAE</th><th>RMSE</th></tr></thead>
            <tbody>{result.by_store.map((item) => <tr key={item.store}>
              <td>{item.store}</td><td>{item.scored_hours}</td>
              <td>{item.mae?.toFixed(2) ?? "—"}</td><td>{item.rmse?.toFixed(2) ?? "—"}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </> : <p>Import the first June day to see forecast accuracy.</p>}
      <p className="helper-text">The model stays fixed during replay. These results do not measure multi-day accuracy.</p>
    </section>
  );
}
