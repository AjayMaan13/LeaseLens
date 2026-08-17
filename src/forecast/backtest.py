"""Rolling-origin cross-validation. Never shuffle a time series: that lets
a model train on the future to predict the past (leakage), and produces
fake-looking accuracy. Instead the origin walks forward -- every
prediction only ever sees data that would actually have existed at that
point in real time.
"""
import numpy as np
import pandas as pd


def rolling_origin(series: pd.Series, fit_predict, initial=60, horizon=12, step=6):
    """fit_predict(train: pd.Series, h: int) -> array of length h"""
    rows, origin = [], initial
    while origin + horizon <= len(series):
        train, test = series.iloc[:origin], series.iloc[origin:origin + horizon]
        yhat = np.asarray(fit_predict(train, horizon), dtype=float)
        err = test.values - yhat
        rows.append({
            "origin": str(series.index[origin]),
            "mae": float(np.mean(np.abs(err))),
            "rmse": float(np.sqrt(np.mean(err ** 2))),
            "mape": float(np.mean(np.abs(err / test.values)) * 100),
        })
        origin += step
    df = pd.DataFrame(rows)
    return df, df[["mae", "rmse", "mape"]].mean().to_dict()
