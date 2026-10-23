import json
import logging
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base

logger = logging.getLogger("emploreralk.models.forecast_run")


class ForecastRun(Base):
    """Persisted model evaluations, selected forecasts, and generated insights."""

    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    horizon_months = Column(Integer, nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def get_result(self) -> Dict[str, Any]:
        try:
            result = json.loads(self.result_json)
        except (TypeError, ValueError):
            logger.exception("Stored forecast run %s contains invalid JSON", self.run_id)
            raise
        if not isinstance(result, dict):
            raise ValueError(f"Stored forecast run {self.run_id} is not an object")
        return result

    def set_result(self, result: Dict[str, Any]) -> None:
        self.result_json = json.dumps(result, allow_nan=False)
