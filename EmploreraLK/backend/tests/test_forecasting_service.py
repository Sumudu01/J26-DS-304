import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.components.forecasting.agents.insight_generation_agent import InsightGenerationAgent
from app.components.forecasting.services import forecasting_service
from app.components.forecasting.services.forecasting_service import ForecastingService


class ForecastingServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_compares_models_persists_best_skill_and_role_forecasts(self):
        today = date.today().replace(day=1)
        records = []
        for month_index in range(36):
            month = ForecastingService._shift_month(today, month_index - 35)
            for posting_index in range(month_index + 1):
                records.append({
                    "title": "Data Engineer",
                    "posted_date": month,
                    "skills": {"Python"},
                })

        def perfect_trend(history, horizon, *args):
            return [history[-1] + step for step in range(1, horizon + 1)]

        def zero_forecast(history, horizon, *args):
            return [0.0] * horizon

        adapters = {
            "ARIMA": SimpleNamespace(is_available=lambda: True, forecast=perfect_trend),
            "Prophet": SimpleNamespace(is_available=lambda: True, forecast=zero_forecast),
            "N-BEATS": SimpleNamespace(is_available=lambda: True, forecast=zero_forecast),
            "TFT": SimpleNamespace(is_available=lambda: True, forecast=zero_forecast),
        }
        with (
            patch.object(forecasting_service, "MODEL_ADAPTERS", adapters),
            patch.object(ForecastingService, "_load_training_records", return_value=records),
        ):
            result = ForecastingService.train_and_store(
                self.db,
                horizon_months=36,
                today=today,
            )
            saved = ForecastingService.get_latest_forecast(
                self.db,
                horizon_months=3,
            )

        self.assertEqual(result["best_model"], "ARIMA")
        self.assertEqual(result["source_postings"], len(records))
        self.assertEqual(len(result["series"]), 2)
        self.assertTrue(all(item["selected_model"] == "ARIMA" for item in result["series"]))
        self.assertTrue(all(item["model_metrics"]["ARIMA"]["mae"] == 0 for item in result["series"]))
        self.assertEqual(len(result["series"][0]["history"]), 36)
        self.assertEqual(result["series"][0]["history"][-1]["period"], today.isoformat())
        self.assertEqual(result["series"][0]["history"][-1]["demand"], 36.0)
        self.assertEqual(len(saved["series"][0]["forecast"]), 3)
        self.assertEqual(len(saved["series"][0]["history"]), 36)
        self.assertEqual(saved["requested_horizon_months"], 3)
        self.assertEqual(len(ForecastingService.get_forecast_history(self.db)), 1)

    def test_mape_excludes_zero_actual_months(self):
        metrics = ForecastingService._calculate_metrics(
            [0, 2, 4],
            [100, 1, 6],
        )

        self.assertEqual(metrics["mape"], 50.0)
        self.assertEqual(metrics["mae"], 34.33)

    def test_prior_model_wins_metric_ties(self):
        reports = {
            name: {
                "status": "trained",
                "mape": 10,
                "rmse": 2,
                "mae": 1,
            }
            for name in ("ARIMA", "Prophet", "N-BEATS", "TFT")
        }

        self.assertEqual(
            ForecastingService._select_best_model(
                reports,
                previous_winner="TFT",
            ),
            "TFT",
        )

    def test_insight_generation_explains_role_and_skill_outlook(self):
        insights = InsightGenerationAgent.generate_model_forecast(
            [
                {
                    "series_type": "skills",
                    "name": "Python",
                    "selected_model": "ARIMA",
                    "expected_change_percent": 25.0,
                    "observations": 40,
                    "forecasted_monthly_average": 12.0,
                },
                {
                    "series_type": "roles",
                    "name": "Legacy Developer",
                    "selected_model": "Prophet",
                    "expected_change_percent": -20.0,
                    "observations": 24,
                    "forecasted_monthly_average": 2.0,
                },
            ],
            horizon_months=36,
            source_postings=285,
            generated_at=datetime.now(timezone.utc),
        )

        self.assertIn("next 36 months", insights["summary"])
        self.assertIn("Python (skill)", insights["summary"])
        self.assertIn("Legacy Developer (role)", insights["summary"])
        self.assertEqual(insights["emerging_skills"][0]["classification"], "emerging")
        self.assertEqual(insights["declining_roles"][0]["classification"], "declining")
        self.assertNotIn("ARIMA model", insights["emerging_skills"][0]["explanation"])
        self.assertNotIn("Prophet model", insights["declining_roles"][0]["explanation"])

    def test_bounds_growth_signals_with_tiny_baselines(self):
        series = [{
            "series_type": "skills",
            "name": "RareSkill",
            "selected_model": "ARIMA",
            "expected_change_percent": 2879.3,
            "observations": 3,
            "forecasted_monthly_average": 1.0,
        }]
        insights = InsightGenerationAgent.generate_model_forecast(
            series,
            horizon_months=36,
            source_postings=30,
            generated_at=datetime.now(timezone.utc),
        )
        normalized_series = ForecastingService._apply_interpretations(series, insights)

        signal = insights["emerging_skills"][0]
        self.assertEqual(signal["expected_change_percent"], 100.0)
        self.assertTrue(signal["change_percent_capped"])
        self.assertEqual(normalized_series[0]["expected_change_percent"], 100.0)
        self.assertTrue(normalized_series[0]["change_percent_capped"])
        self.assertIn("Based on 30 dated postings", insights["summary"])

    def test_rejects_forecast_horizon_over_three_years(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 36"):
            ForecastingService.train_and_store(self.db, horizon_months=37)


if __name__ == "__main__":
    unittest.main()
