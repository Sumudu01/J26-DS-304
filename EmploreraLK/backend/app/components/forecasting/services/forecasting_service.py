import logging
import csv
import math
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.components.forecasting.agents.insight_generation_agent import InsightGenerationAgent
from app.components.forecasting.models import (
    arima_model,
    nbeats_model,
    prophet_model,
    tft_model,
)
from app.models.forecast_run import ForecastRun
from app.models.job_posting import JobPosting

logger = logging.getLogger("emploreralk.services.forecasting")
MODEL_ADAPTERS = {
    "ARIMA": arima_model,
    "Prophet": prophet_model,
    "N-BEATS": nbeats_model,
    "TFT": tft_model,
}
MODEL_METRICS = ("mape", "rmse", "mae")
MAX_SERIES_PER_TYPE = 8
MAX_HISTORY_MONTHS = 60


class ForecastingService:
    """Build skill-demand forecasts from the dated job postings in the database."""

    @classmethod
    def get_demand_insights(
        cls,
        db: Session,
        target_year: int,
        *,
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        current_day = today or datetime.now(timezone.utc).date()
        current_period_start = current_day - timedelta(days=364)
        previous_period_end = current_period_start - timedelta(days=1)
        previous_period_start = current_day - timedelta(days=729)

        rows = (
            db.query(
                JobPosting.skills_extracted,
                JobPosting.skills_processed,
                JobPosting.posted_timestamp,
            )
            .filter(JobPosting.status.in_(["extracted", "processed"]))
            .all()
        )

        current_counts: Counter[str] = Counter()
        previous_counts: Counter[str] = Counter()
        current_job_ids = set()
        previous_job_ids = set()

        for row_index, row in enumerate(rows):
            posted_date = row.posted_timestamp
            if posted_date is None:
                continue
            if isinstance(posted_date, datetime):
                if posted_date.tzinfo is not None:
                    posted_date = posted_date.astimezone(timezone.utc).date()
                else:
                    posted_date = posted_date.date()
            elif not isinstance(posted_date, date):
                continue

            if current_period_start <= posted_date <= current_day:
                counts = current_counts
                job_ids = current_job_ids
            elif previous_period_start <= posted_date <= previous_period_end:
                counts = previous_counts
                job_ids = previous_job_ids
            else:
                continue

            skills = cls._extract_skills(row.skills_extracted, row.skills_processed)
            if not skills:
                continue
            job_ids.add(row_index)
            counts.update(skills)

        skill_names = current_counts.keys() | previous_counts.keys()
        comparison_counts = {
            skill: {
                "current": current_counts.get(skill, 0),
                "previous": previous_counts.get(skill, 0),
            }
            for skill in skill_names
        }
        return InsightGenerationAgent.generate(
            comparison_counts,
            target_year=target_year,
            current_period_start=current_period_start,
            current_period_end=current_day,
            previous_period_start=previous_period_start,
            previous_period_end=previous_period_end,
            current_period_jobs=len(current_job_ids),
            previous_period_jobs=len(previous_job_ids),
        )

    @classmethod
    def train_and_store(
        cls,
        db: Session,
        *,
        horizon_months: int = 36,
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        if not 1 <= horizon_months <= 36:
            raise ValueError("horizon_months must be between 1 and 36")

        generated_at = datetime.now(timezone.utc)
        current_month = (today or generated_at.date()).replace(day=1)
        records = cls._load_training_records(db, current_month)
        if not records:
            raise ValueError("No dated job-posting dataset is available for training")

        start_month = max(
            min(record["posted_date"].replace(day=1) for record in records),
            cls._shift_month(current_month, -(MAX_HISTORY_MONTHS - 1)),
        )
        months = cls._month_range(start_month, current_month)
        if len(months) < 15:
            raise ValueError("At least 15 months of dated job-posting history are required")

        skills: Dict[str, Counter] = defaultdict(Counter)
        roles: Dict[str, Counter] = defaultdict(Counter)
        skill_labels: Counter = Counter()
        role_labels: Counter = Counter()
        for record in records:
            bucket = record["posted_date"].replace(day=1)
            if bucket < start_month or bucket > current_month:
                continue
            for skill in record["skills"]:
                key = skill.casefold()
                skills[key][bucket] += 1
                skill_labels[(key, skill)] += 1
            title = record["title"].strip()
            if title:
                key = title.casefold()
                roles[key][bucket] += 1
                role_labels[(key, title)] += 1

        latest = (
            db.query(ForecastRun)
            .order_by(ForecastRun.created_at.desc())
            .first()
        )
        previous_result = latest.get_result() if latest else {}
        previous_winners = {
            (
                item.get("series_type", "").rstrip("s"),
                item.get("name", "").casefold(),
            ): item.get("selected_model")
            for item in previous_result.get("series", [])
        }

        series_reports: List[Dict[str, Any]] = []
        for kind, values, labels in (
            ("skill", skills, skill_labels),
            ("role", roles, role_labels),
        ):
            ranked = sorted(
                (
                    (key, counts)
                    for key, counts in values.items()
                    if sum(counts.values()) >= 3
                ),
                key=lambda entry: sum(entry[1].values()),
                reverse=True,
            )[:MAX_SERIES_PER_TYPE]
            for key, counts in ranked:
                label = max(
                    (name for item_key, name in labels if item_key == key),
                    key=lambda name: labels[(key, name)],
                )
                values_by_month = [float(counts.get(month, 0)) for month in months]
                winner = cls._train_series(
                    kind=kind,
                    name=label,
                    values=values_by_month,
                    months=months,
                    horizon_months=horizon_months,
                    previous_winner=previous_winners.get((kind, label.casefold())),
                )
                if winner:
                    series_reports.append(winner)

        if not series_reports:
            raise RuntimeError(
                "No forecasting model could be trained; check model dependencies and posting history"
            )

        model_metrics = cls._aggregate_model_metrics(series_reports)
        global_best = cls._select_best_model(model_metrics)
        insights = InsightGenerationAgent.generate_model_forecast(
            series_reports,
            horizon_months=horizon_months,
            source_postings=len(records),
            generated_at=generated_at,
        )
        series_reports = cls._apply_interpretations(series_reports, insights)
        result = {
            **insights,
            "run_id": str(uuid.uuid4()),
            "forecast_horizon_months": horizon_months,
            "data_window": {
                "start": months[0].isoformat(),
                "end": months[-1].isoformat(),
                "months": len(months),
            },
            "best_model": global_best,
            "model_metrics": model_metrics,
            "historical_knowledge": {
                "previous_run_id": latest.run_id if latest else None,
                "previous_generated_at": (
                    previous_result.get("generated_at") if previous_result else None
                ),
                "previous_run_used_for_tie_breaking": bool(previous_winners),
            },
            "series": series_reports,
        }
        stored = ForecastRun(
            run_id=result["run_id"],
            horizon_months=horizon_months,
        )
        stored.set_result(result)
        db.add(stored)
        db.commit()
        return result

    @classmethod
    def get_latest_forecast(
        cls,
        db: Session,
        *,
        horizon_months: int = 36,
    ) -> Optional[Dict[str, Any]]:
        if not 1 <= horizon_months <= 36:
            raise ValueError("horizon_months must be between 1 and 36")
        latest = db.query(ForecastRun).order_by(ForecastRun.created_at.desc()).first()
        if latest is None:
            return None
        result = latest.get_result()
        if not isinstance(result.get("series"), list):
            raise ValueError(f"Stored forecast run {latest.run_id} has no forecast series")
        series = cls._trim_forecasts(result.get("series", []), horizon_months)
        for item in series:
            baseline = item["current_monthly_average"]
            projected = item["forecasted_monthly_average"]
            item["expected_change_percent"] = round(
                ((projected - baseline) / baseline * 100) if baseline else (
                    100.0 if projected else 0.0
                ),
                1,
            )
        created_at = datetime.fromisoformat(
            result["generated_at"].replace("Z", "+00:00")
        )
        insights = InsightGenerationAgent.generate_model_forecast(
            series,
            horizon_months=horizon_months,
            source_postings=result["source_postings"],
            generated_at=created_at,
        )
        result.update(insights)
        result["series"] = cls._apply_interpretations(series, insights)
        result["forecast_horizon_months"] = result.get("forecast_horizon_months", 36)
        result["requested_horizon_months"] = horizon_months
        return result

    @staticmethod
    def _apply_interpretations(
        series: List[Dict[str, Any]],
        insights: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        interpreted = {
            (item["series_type"], item["name"]): item
            for category in (
                "emerging_skills",
                "declining_skills",
                "steady_skills",
                "emerging_roles",
                "declining_roles",
                "steady_roles",
            )
            for item in insights[category]
        }
        return [
            {**item, **interpreted[(item["series_type"], item["name"])]}
            for item in series
        ]

    @staticmethod
    def get_forecast_history(db: Session, *, limit: int = 20) -> List[Dict[str, Any]]:
        runs = (
            db.query(ForecastRun)
            .order_by(ForecastRun.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "run_id": run.run_id,
                "generated_at": run.get_result().get("generated_at"),
                "horizon_months": run.horizon_months,
                "best_model": run.get_result().get("best_model"),
                "summary": run.get_result().get("summary"),
            }
            for run in runs
        ]

    @classmethod
    def _load_training_records(
        cls,
        db: Session,
        current_month: date,
    ) -> List[Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}
        dataset_path = Path(__file__).resolve().parents[1] / "models" / "job_postings.csv"
        try:
            with dataset_path.open("r", newline="", encoding="utf-8-sig") as dataset:
                for row in csv.DictReader(dataset):
                    job_id = row.get("job_id", "").strip()
                    posted = cls._parse_posted_date(row.get("posted_timestamp"))
                    if not job_id or posted is None or posted.replace(day=1) > current_month:
                        continue
                    records[job_id] = {
                        "title": (row.get("title") or "").strip(),
                        "posted_date": posted,
                        "skills": cls._extract_skills(
                            row.get("skills_extracted"),
                            row.get("skills_processed"),
                        ),
                    }
        except FileNotFoundError:
            logger.warning("Forecast training CSV is missing: %s", dataset_path)
        except (OSError, csv.Error):
            logger.exception("Could not read the forecast training CSV: %s", dataset_path)
            raise

        postings = (
            db.query(
                JobPosting.job_id,
                JobPosting.title,
                JobPosting.posted_timestamp,
                JobPosting.skills_extracted,
                JobPosting.skills_processed,
            )
            .filter(JobPosting.posted_timestamp.isnot(None))
            .all()
        )
        for posting in postings:
            posted = cls._parse_posted_date(posting.posted_timestamp)
            if posted is None or posted.replace(day=1) > current_month:
                continue
            previous = records.get(posting.job_id, {})
            records[posting.job_id] = {
                "title": (posting.title or previous.get("title") or "").strip(),
                "posted_date": posted,
                "skills": set(previous.get("skills", set()))
                | cls._extract_skills(
                    posting.skills_extracted,
                    posting.skills_processed,
                ),
            }
        return list(records.values())

    @staticmethod
    def _parse_posted_date(value: Any) -> Optional[date]:
        if isinstance(value, datetime):
            return (
                value.astimezone(timezone.utc).date()
                if value.tzinfo
                else value.date()
            )
        if isinstance(value, date):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(
                    value.strip().replace("Z", "+00:00")
                ).date()
            except ValueError:
                logger.warning("Ignoring unparseable posting date in forecast data")
        return None

    @staticmethod
    def _month_range(start: date, end: date) -> List[date]:
        months: List[date] = []
        cursor = start.replace(day=1)
        while cursor <= end:
            months.append(cursor)
            cursor = ForecastingService._shift_month(cursor, 1)
        return months

    @staticmethod
    def _shift_month(value: date, amount: int) -> date:
        index = value.year * 12 + value.month - 1 + amount
        return date(index // 12, index % 12 + 1, 1)

    @classmethod
    def _train_series(
        cls,
        *,
        kind: str,
        name: str,
        values: List[float],
        months: List[date],
        horizon_months: int,
        previous_winner: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        validation_size = min(3, max(1, len(values) // 6))
        training_values = values[:-validation_size]
        actual = values[-validation_size:]
        validation_start = months[0]
        model_reports: Dict[str, Dict[str, Any]] = {}

        for model_name, adapter in MODEL_ADAPTERS.items():
            try:
                if not adapter.is_available():
                    model_reports[model_name] = {
                        "status": "unavailable",
                        "error": cls._missing_model_dependency(model_name),
                        **{metric: None for metric in MODEL_METRICS},
                    }
                    continue
                validation_forecast = cls._run_model(
                    model_name,
                    adapter,
                    training_values,
                    validation_size,
                    validation_start,
                )
                metrics = cls._calculate_metrics(actual, validation_forecast)
                model_reports[model_name] = {"status": "trained", **metrics}
            except Exception as exc:
                logger.exception(
                    "%s forecasting failed for %s %r",
                    model_name,
                    kind,
                    name,
                )
                model_reports[model_name] = {
                    "status": "failed",
                    "error": str(exc)[:300],
                    **{metric: None for metric in MODEL_METRICS},
                }

        forecast_values = None
        selected = None
        for candidate in cls._rank_models(
            model_reports,
            previous_winner=previous_winner,
        ):
            try:
                forecast_values = cls._run_model(
                    candidate,
                    MODEL_ADAPTERS[candidate],
                    values,
                    horizon_months,
                    validation_start,
                )
                selected = candidate
                break
            except Exception as exc:
                logger.exception(
                    "%s final forecast failed for %s %r",
                    candidate,
                    kind,
                    name,
                )
                model_reports[candidate].update({
                    "status": "failed",
                    "error": str(exc)[:300],
                })
        if selected is None or forecast_values is None:
            return None

        next_month = cls._shift_month(months[-1], 1)
        forecast_rows = [
            {
                "period": cls._shift_month(next_month, index).isoformat(),
                "demand": round(value, 1),
            }
            for index, value in enumerate(forecast_values)
        ]
        recent_average = sum(values[-min(12, len(values)):]) / min(12, len(values))
        forecast_average = sum(row["demand"] for row in forecast_rows[-min(12, len(forecast_rows)):]) / min(
            12, len(forecast_rows)
        )
        change = (
            ((forecast_average - recent_average) / recent_average) * 100
            if recent_average
            else (100.0 if forecast_average else 0.0)
        )
        return {
            "series_type": f"{kind}s",
            "name": name,
            "observations": int(sum(values)),
            "history": [
                {
                    "period": month.isoformat(),
                    "demand": round(value, 1),
                }
                for month, value in zip(months, values)
            ],
            "current_monthly_average": round(recent_average, 2),
            "forecasted_monthly_average": round(forecast_average, 2),
            "expected_change_percent": round(change, 1),
            "selected_model": selected,
            "model_metrics": model_reports,
            "forecast": forecast_rows,
        }

    @staticmethod
    def _run_model(
        model_name: str,
        adapter: Any,
        history: Sequence[float],
        horizon: int,
        start_date: date,
    ) -> List[float]:
        if model_name == "ARIMA":
            raw_forecast = adapter.forecast(history, horizon)
        else:
            raw_forecast = adapter.forecast(history, horizon, start_date)
        if len(raw_forecast) != horizon:
            raise ValueError(
                f"Expected {horizon} forecast points, received {len(raw_forecast)}"
            )
        values = [float(value) for value in raw_forecast]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Model returned a non-finite forecast")
        return [max(0.0, value) for value in values]

    @staticmethod
    def _calculate_metrics(actual: Sequence[float], predicted: Sequence[float]) -> Dict[str, Optional[float]]:
        errors = [float(expected) - float(estimate) for expected, estimate in zip(actual, predicted)]
        non_zero_pairs = [
            (float(expected), float(estimate))
            for expected, estimate in zip(actual, predicted)
            if float(expected) != 0
        ]
        mape = (
            sum(abs(expected - estimate) / abs(expected) for expected, estimate in non_zero_pairs)
            / len(non_zero_pairs)
            * 100
            if non_zero_pairs
            else None
        )
        return {
            "mape": round(mape, 2) if mape is not None else None,
            "rmse": round(math.sqrt(sum(error * error for error in errors) / len(errors)), 2),
            "mae": round(sum(abs(error) for error in errors) / len(errors), 2),
        }

    @staticmethod
    def _select_best_model(
        reports: Dict[str, Dict[str, Any]],
        *,
        previous_winner: Optional[str] = None,
    ) -> Optional[str]:
        ranked = ForecastingService._rank_models(
            reports,
            previous_winner=previous_winner,
        )
        return ranked[0] if ranked else None

    @staticmethod
    def _rank_models(
        reports: Dict[str, Dict[str, Any]],
        *,
        previous_winner: Optional[str] = None,
    ) -> List[str]:
        model_names = [
            name for name, report in reports.items()
            if report.get("status") in {"trained", "partial"}
        ]
        if not model_names:
            return []
        rank_totals = Counter()
        rank_counts = Counter()
        for metric in MODEL_METRICS:
            ranked = sorted(
                (
                    (name, reports[name].get(metric))
                    for name in model_names
                    if reports[name].get(metric) is not None
                ),
                key=lambda pair: pair[1],
            )
            previous_score = None
            rank = 0
            for index, (name, score) in enumerate(ranked):
                if index and score != previous_score:
                    rank = index
                rank_totals[name] += rank
                rank_counts[name] += 1
                previous_score = score
        if not rank_counts:
            return []
        return sorted(
            rank_counts,
            key=lambda name: (
                rank_totals[name] / rank_counts[name],
                name != previous_winner,
                name,
            ),
        )

    @classmethod
    def _aggregate_model_metrics(
        cls,
        series: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        aggregated: Dict[str, Dict[str, Any]] = {}
        for model_name in MODEL_ADAPTERS:
            reports = [
                item["model_metrics"][model_name]
                for item in series
                if model_name in item["model_metrics"]
            ]
            trained = [report for report in reports if report["status"] == "trained"]
            aggregated[model_name] = {
                "status": (
                    "trained" if len(trained) == len(series)
                    else "partial" if trained
                    else reports[0]["status"] if reports
                    else "unavailable"
                ),
                "series_count": len(trained),
                **{
                    metric: (
                        round(
                            sum(report[metric] for report in trained if report[metric] is not None)
                            / len([report for report in trained if report[metric] is not None]),
                            2,
                        )
                        if any(report[metric] is not None for report in trained)
                        else None
                    )
                    for metric in MODEL_METRICS
                },
            }
            if not trained and reports:
                aggregated[model_name]["error"] = reports[0].get("error")
            elif len(trained) < len(reports):
                aggregated[model_name]["error"] = next(
                    report.get("error")
                    for report in reports
                    if report["status"] != "trained" and report.get("error")
                )
        return aggregated

    @staticmethod
    def _missing_model_dependency(model_name: str) -> str:
        if model_name == "ARIMA":
            return "Install statsmodels to enable ARIMA."
        if model_name == "Prophet":
            return "Install prophet to enable Prophet."
        return "Install neuralforecast with its PyTorch dependencies to enable this model."

    @staticmethod
    def _trim_forecasts(items: List[Dict[str, Any]], horizon_months: int) -> List[Dict[str, Any]]:
        trimmed = []
        for item in items:
            copy = dict(item)
            copy["forecast"] = item.get("forecast", [])[:horizon_months]
            if copy["forecast"]:
                copy["forecasted_monthly_average"] = round(
                    sum(point["demand"] for point in copy["forecast"]) / len(copy["forecast"]),
                    2,
                )
            trimmed.append(copy)
        return trimmed

    @staticmethod
    def _extract_skills(extracted_json: Optional[str], processed_json: Optional[str]) -> set[str]:
        import json

        skills: set[str] = set()
        if extracted_json:
            try:
                extracted = json.loads(extracted_json)
            except (TypeError, ValueError):
                logger.warning("Skipping malformed extracted skills JSON in demand forecast")
                extracted = []
            if isinstance(extracted, list):
                skills.update(
                    skill.strip()
                    for skill in extracted
                    if isinstance(skill, str) and skill.strip()
                )

        if processed_json:
            try:
                processed = json.loads(processed_json)
            except (TypeError, ValueError):
                logger.warning("Skipping malformed processed skills JSON in demand forecast")
                processed = {}
            if isinstance(processed, dict):
                normalized = processed.get("canonical_skills", [])
                if isinstance(normalized, list):
                    skills.update(
                        skill.strip()
                        for skill in normalized
                        if isinstance(skill, str) and skill.strip()
                    )
                normalized_items = processed.get("normalized_items", [])
                if isinstance(normalized_items, list):
                    skills.update(
                        item["canonical_name"].strip()
                        for item in normalized_items
                        if isinstance(item, dict)
                        and isinstance(item.get("canonical_name"), str)
                        and item["canonical_name"].strip()
                    )
        return skills