"""Four models, deliberately ordered from dumbest to most sophisticated.
The naive baselines are not filler -- if SARIMA/Prophet can't beat them,
that is the actual finding, not a failed experiment.
"""
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX


def naive(train, h):
    return np.repeat(train.iloc[-1], h)


def seasonal_naive(train, h, m=12):
    return np.array([train.iloc[-m + (i % m)] for i in range(h)])


def sarima(train, h, order=(1, 1, 1), seasonal=(1, 1, 1, 12)):
    fit = SARIMAX(train, order=order, seasonal_order=seasonal,
                  enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
    return fit.forecast(h).values


def prophet_fp(train, h):
    from prophet import Prophet
    import pandas as pd
    df = pd.DataFrame({"ds": train.index.to_timestamp() if hasattr(train.index, "to_timestamp")
                        else train.index, "y": train.values})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(df)
    fut = m.make_future_dataframe(periods=h, freq="MS")
    return m.predict(fut)["yhat"].tail(h).values
