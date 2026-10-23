from datetime import date
from typing import Sequence


def is_available() -> bool:
    try:
        import prophet  # noqa: F401
    except ImportError:
        return False
    return True


def forecast(
    history: Sequence[float],
    horizon: int,
    start_date: date,
) -> list[float]:
    import pandas as pd
    from prophet import Prophet

    frame = pd.DataFrame({
        "ds": pd.date_range(start=start_date, periods=len(history), freq="MS"),
        "y": [float(value) for value in history],
    })
    model = Prophet(
        yearly_seasonality=len(history) >= 24,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="additive",
    )
    model.fit(frame)
    future = model.make_future_dataframe(
        periods=horizon,
        freq="MS",
        include_history=False,
    )
    predictions = model.predict(future)["yhat"].tolist()
    return [float(value) for value in predictions]