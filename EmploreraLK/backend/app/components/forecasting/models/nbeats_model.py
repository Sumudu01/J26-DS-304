from datetime import date
from typing import Sequence


def is_available() -> bool:
    try:
        import neuralforecast  # noqa: F401
    except ImportError:
        return False
    return True


def forecast(
    history: Sequence[float],
    horizon: int,
    start_date: date,
) -> list[float]:
    import pandas as pd
    from neuralforecast import NeuralForecast
    from neuralforecast.models import NBEATS

    frame = pd.DataFrame({
        "unique_id": "job_market",
        "ds": pd.date_range(start=start_date, periods=len(history), freq="MS"),
        "y": [float(value) for value in history],
    })
    model = NBEATS(
        h=horizon,
        input_size=min(12, max(4, len(history) // 2)),
        max_steps=20,
        batch_size=16,
        windows_batch_size=16,
        random_seed=42,
        logger=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        enable_checkpointing=False,
        val_check_steps=20,
        log_every_n_steps=20,
    )
    forecaster = NeuralForecast(models=[model], freq="MS")
    forecaster.fit(df=frame)
    predictions = forecaster.predict()["NBEATS"].tolist()
    return [float(value) for value in predictions]