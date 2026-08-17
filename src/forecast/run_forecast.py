"""Backtest naive / seasonal-naive / SARIMA / Prophet on Toronto's StatCan
CPI rented-accommodation series (666 months, 1971-01 to 2026-06), via
rolling-origin CV. Prophet is optional -- skipped gracefully if it fails
to fit (a real risk per 00-BEFORE-YOU-START.md Part C's known install
issues), since baselines + SARIMA already form a complete forecasting
story on their own.
"""
import pathlib
import pandas as pd

from src.forecast.backtest import rolling_origin
from src.forecast.models import naive, seasonal_naive, sarima, prophet_fp

SERIES_PATH = pathlib.Path("data/series/rent_by_area.csv")
RESULTS = pathlib.Path("results"); RESULTS.mkdir(exist_ok=True)

# 40 years of history before the first fold, 12-month-ahead forecasts,
# stepping the origin forward 24 months between folds -- keeps SARIMA/
# Prophet's repeated re-fitting to a manageable number of folds (~8)
# while still covering multiple distinct time periods, not just one.
INITIAL, HORIZON, STEP = 480, 12, 24


def load_toronto_series() -> pd.Series:
    df = pd.read_csv(SERIES_PATH)
    tor = df[df["area_name"] == "Toronto, Ontario"].sort_values("period")
    idx = pd.PeriodIndex(tor["period"], freq="M")
    return pd.Series(tor["value"].values, index=idx, name="cpi_rented_accommodation")


def run():
    series = load_toronto_series()
    print(f"Toronto series: {len(series)} months, {series.index[0]} to {series.index[-1]}")

    models = {
        "naive": naive,
        "seasonal_naive": seasonal_naive,
        "sarima": sarima,
    }

    fold_results, summary_rows = {}, []
    for name, fn in models.items():
        print(f"backtesting {name} ...")
        folds, summary = rolling_origin(series, fn, initial=INITIAL, horizon=HORIZON, step=STEP)
        fold_results[name] = folds
        summary_rows.append({"model": name, "folds": len(folds), **summary})
        print(f"  {name}: MAE={summary['mae']:.3f} RMSE={summary['rmse']:.3f} MAPE={summary['mape']:.2f}%")

    try:
        print("backtesting prophet ...")
        folds, summary = rolling_origin(series, prophet_fp, initial=INITIAL, horizon=HORIZON, step=STEP)
        fold_results["prophet"] = folds
        summary_rows.append({"model": "prophet", "folds": len(folds), **summary})
        print(f"  prophet: MAE={summary['mae']:.3f} RMSE={summary['rmse']:.3f} MAPE={summary['mape']:.2f}%")
    except Exception as e:
        print(f"  prophet failed to fit ({e}) -- skipped, per the plan's guidance that this is a "
              f"stretch goal and baselines+SARIMA already form a complete story")

    summary_df = pd.DataFrame(summary_rows).sort_values("mae")
    baseline_mae = summary_df[summary_df["model"] == "seasonal_naive"]["mae"].iloc[0]
    summary_df["vs_seasonal_naive"] = summary_df["mae"].apply(
        lambda m: f"{(baseline_mae - m) / baseline_mae:+.1%}")

    md = ["# Forecast Results — Toronto CPI Rented Accommodation", "",
          f"Series: {len(series)} months ({series.index[0]}–{series.index[-1]}), "
          f"StatCan table 18-10-0004-01. Rolling-origin CV: {INITIAL}-month initial window, "
          f"{HORIZON}-month horizon, {STEP}-month step between folds "
          f"({summary_rows[0]['folds']} folds).",
          "",
          "| Model | Folds | MAE | RMSE | MAPE | vs seasonal-naive |",
          "|---|---|---|---|---|---|"]
    for _, r in summary_df.iterrows():
        md.append(f"| {r['model']} | {r['folds']} | {r['mae']:.3f} | {r['rmse']:.3f} | "
                   f"{r['mape']:.2f}% | {r['vs_seasonal_naive']} |")

    md += ["", "## Fold-level detail (variance, not just the mean)", ""]
    for name, folds in fold_results.items():
        md.append(f"### {name}")
        md.append("| origin | MAE | RMSE | MAPE |")
        md.append("|---|---|---|---|")
        for _, f in folds.iterrows():
            md.append(f"| {f['origin']} | {f['mae']:.3f} | {f['rmse']:.3f} | {f['mape']:.2f}% |")
        md.append("")

    (RESULTS / "forecast_results.md").write_text("\n".join(md))
    print("\n" + "\n".join(md[:12]))
    print(f"\nFull results written to {RESULTS / 'forecast_results.md'}")


if __name__ == "__main__":
    run()
