import { useEffect, useState } from "react";

import { Panel } from "./Panels";

interface Desk {
  desk: string; n: number; hit_rate: number; brier: number;
  beats_coin_flip: boolean; bull: number; bear: number;
  bear_share: number; one_sided: boolean;
}
interface Calibration {
  desks: Desk[]; total_scored: number; unresolved: number;
  neutral_brier: number; bear_share: number; systematic_bias: boolean;
  sample_warning: boolean; caveat: string;
}

/** Were the desks right? Scored against realised forward returns.
 *
 *  This panel exists to report a result, not to flatter one. The desks currently score
 *  WORSE than a coin flip, and showing that plainly is the point — it is the evidence
 *  that the deterministic firewall is load-bearing rather than decorative.
 */
export function CalibrationPanel() {
  const [data, setData] = useState<Calibration | null>(null);

  useEffect(() => {
    fetch("/calibration").then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data || !data.desks.length) return null;
  const anyGood = data.desks.some((d) => d.beats_coin_flip);

  return (
    <Panel title="Desk Calibration" tone={anyGood ? undefined : "alert"}>
      <div className="calib-head">
        <span>{data.total_scored} directional claims scored</span>
        <span>vs realised 7d / 30d returns</span>
      </div>

      <table className="calib">
        <thead>
          <tr><th>Desk</th><th>N</th><th>Hit</th><th>Brier</th><th>Bias</th></tr>
        </thead>
        <tbody>
          {data.desks.map((d) => (
            <tr key={d.desk} className={d.beats_coin_flip ? "good" : "bad"}>
              <td>{d.desk}</td>
              <td className="num">{d.n}</td>
              <td className="num">{(d.hit_rate * 100).toFixed(0)}%</td>
              <td className="num" title={`${data.neutral_brier} = always guessing`}>
                {d.brier.toFixed(3)}
              </td>
              <td>
                <span className="split" title={`${d.bull} bull / ${d.bear} bear`}>
                  <span className="bull" style={{ width: `${(1 - d.bear_share) * 100}%` }} />
                  <span className="bear" style={{ width: `${d.bear_share * 100}%` }} />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {!anyGood && (
        <div className="calib-verdict">
          <b>No desk beats a coin flip</b>
          A Brier score above {data.neutral_brier} is worse than always saying 50/50.
          This is why the firewall is deterministic code and not another model — the
          governance layer is doing the work, and it is measurable.
        </div>
      )}

      {data.systematic_bias && (
        <div className="groupthink" style={{ marginTop: 8 }}>
          <b>Directional bias — {(data.bear_share * 100).toFixed(0)}% bearish</b>
          The desks read almost any evidence pack as concerning. A desk that nearly
          always says the same thing carries no information, however often it happens
          to land on the right side.
        </div>
      )}

      {data.sample_warning && (
        <div className="tiny" style={{ marginTop: 8 }}>
          Small sample — indicative, not established.
        </div>
      )}

      <div className="calib-caveat">{data.caveat}</div>
    </Panel>
  );
}
