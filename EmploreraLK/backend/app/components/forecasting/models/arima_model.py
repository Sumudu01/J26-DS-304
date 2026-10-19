import logging
import warnings
from typing import Sequence

logger = logging.getLogger("emploreralk.forecasting.arima")


def is_available() -> bool:
    try:
        import statsmodels  # noqa: F401
    except ImportError:
        return False
    return True


def forecast(history: Sequence[float], horizon: int) -> list[float]:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tools.sm_exceptions import ConvergenceWarning

    values = [float(value) for value in history]
    if len(values) < 6:
        raise ValueError("ARIMA requires at least 6 monthly observations")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            fitted = ARIMA(
                values,
                order=(1, 1, 1),
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit()
    except ConvergenceWarning:
        logger.warning("ARIMA(1,1,1) did not converge; using a random-walk ARIMA fallback")
        # Zero-drift ARIMA(0,1,0) forecasts the latest level without optimization.
        return [values[-1]] * horizon
    return [float(value) for value in fitted.forecast(steps=horizon)]