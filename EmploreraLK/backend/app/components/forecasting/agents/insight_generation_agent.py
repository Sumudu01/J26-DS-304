from datetime import date, datetime, timezone
from typing import Any, Dict, List


class InsightGenerationAgent:
    """Turn observed job-posting skill counts into explainable demand insights."""

    MINIMUM_CURRENT_POSTINGS = 3
    SIGNIFICANT_CHANGE_PERCENT = 10.0
    MAX_ANNUAL_GROWTH_PERCENT = 200.0
    MAX_ANNUAL_DECLINE_PERCENT = -80.0
    MAX_REPORTED_GROWTH_PERCENT = 100.0
    MAX_REPORTED_DECLINE_PERCENT = -80.0

    @classmethod
    def generate(
        cls,
        skill_counts: Dict[str, Dict[str, int]],
        *,
        target_year: int,
        current_period_start: date,
        current_period_end: date,
        previous_period_start: date,
        previous_period_end: date,
        current_period_jobs: int,
        previous_period_jobs: int,
    ) -> Dict[str, Any]:
        """Classify skills using year-over-year posting counts and explain each signal."""
        years_ahead = max(1, target_year - current_period_end.year)
        trends: List[Dict[str, Any]] = []

        for skill, counts in skill_counts.items():
            current_count = counts["current"]
            previous_count = counts["previous"]
            if current_period_jobs == 0 or previous_period_jobs == 0:
                continue
            if (
                current_count < cls.MINIMUM_CURRENT_POSTINGS
                and previous_count < cls.MINIMUM_CURRENT_POSTINGS
            ):
                continue

            current_share = (
                current_count / current_period_jobs * 100
                if current_period_jobs
                else 0.0
            )
            previous_share = (
                previous_count / previous_period_jobs * 100
                if previous_period_jobs
                else 0.0
            )
            if previous_count == 0:
                change_percent = None
                annual_growth = None
                forecast_index = None
                classification = "emerging"
                explanation = "Appeared in recent postings, with no mentions in the comparison period."
                next_step = f"Explore {skill} and look for practical projects that use it."
            else:
                change_percent = round((current_share - previous_share) / previous_share * 100, 1) if previous_share else None
                if change_percent is None:
                    continue
                annual_growth = max(
                    cls.MAX_ANNUAL_DECLINE_PERCENT,
                    min(cls.MAX_ANNUAL_GROWTH_PERCENT, change_percent),
                )
                forecast_index = round(100 * (1 + annual_growth / 100) ** years_ahead)
                if change_percent >= cls.SIGNIFICANT_CHANGE_PERCENT:
                    classification = "emerging"
                    explanation = (
                        f"Share of postings mentioning this skill rose from {previous_share:.1f}% "
                        f"to {current_share:.1f}% across comparable 12-month periods."
                    )
                    next_step = f"Build or showcase hands-on experience with {skill}."
                elif change_percent <= -cls.SIGNIFICANT_CHANGE_PERCENT:
                    classification = "declining"
                    explanation = (
                        f"Share of postings mentioning this skill fell from {previous_share:.1f}% "
                        f"to {current_share:.1f}% across comparable 12-month periods."
                    )
                    next_step = f"Keep {skill} as a supporting skill and pair it with growing technologies."
                else:
                    classification = "steady"
                    explanation = "Demand mentions are broadly steady across comparable 12-month periods."
                    next_step = f"Maintain your {skill} skills while exploring adjacent growing areas."

            trends.append({
                "skill": skill,
                "current_postings": current_count,
                "previous_postings": previous_count,
                "current_share_percent": round(current_share, 1),
                "previous_share_percent": round(previous_share, 1),
                "change_percent": change_percent,
                "forecast_index": forecast_index,
                "classification": classification,
                "explanation": explanation,
                "recommendation": next_step,
            })

        emerging = sorted(
            (trend for trend in trends if trend["classification"] == "emerging"),
            key=lambda trend: (trend["change_percent"] is not None, trend["change_percent"] or 0, trend["current_postings"]),
            reverse=True,
        )
        declining = sorted(
            (trend for trend in trends if trend["classification"] == "declining"),
            key=lambda trend: trend["change_percent"],
        )
        steady = sorted(
            (trend for trend in trends if trend["classification"] == "steady"),
            key=lambda trend: trend["current_postings"],
            reverse=True,
        )
        enough_data = current_period_jobs >= 10 and previous_period_jobs >= 10

        if current_period_jobs == 0 and previous_period_jobs == 0:
            summary = "There are not enough recent dated job postings to produce a demand outlook yet."
        elif current_period_jobs == 0:
            summary = "There are no recent dated job postings to compare with the prior year."
        elif previous_period_jobs == 0:
            summary = (
                "Recent dated job postings are available, but the prior-year comparison period has no data; "
                "emerging and declining trends cannot yet be confirmed."
            )
        elif not enough_data:
            summary = (
                "Early market signals are available, but more dated job postings are needed "
                "for a reliable year-over-year outlook."
            )
        elif emerging and declining:
            summary = (
                f"{emerging[0]['skill']} is gaining traction while "
                f"{declining[0]['skill']} is appearing less often in recent postings."
            )
        elif emerging:
            summary = f"{emerging[0]['skill']} is one of the clearest rising skill signals in recent postings."
        elif declining:
            summary = f"{declining[0]['skill']} is appearing less often in recent postings."
        else:
            summary = "Tracked skill demand is mostly steady across the two comparison periods."

        return {
            "target_year": target_year,
            "generated_at": current_period_end.isoformat(),
            "summary": summary,
            "confidence": "moderate" if enough_data else "early signal",
            "data_window": {
                "current_start": current_period_start.isoformat(),
                "current_end": current_period_end.isoformat(),
                "previous_start": previous_period_start.isoformat(),
                "previous_end": previous_period_end.isoformat(),
                "current_postings": current_period_jobs,
                "previous_postings": previous_period_jobs,
            },
            "emerging_skills": emerging[:6],
            "declining_skills": declining[:6],
            "steady_skills": steady[:6],
        }

    @classmethod
    def generate_model_forecast(
        cls,
        series: List[Dict[str, Any]],
        *,
        horizon_months: int,
        source_postings: int,
        generated_at: datetime,
    ) -> Dict[str, Any]:
        """Explain model-selected monthly forecasts as emerging, declining, or steady."""
        trends: Dict[str, List[Dict[str, Any]]] = {
            "emerging_skills": [],
            "declining_skills": [],
            "steady_skills": [],
            "emerging_roles": [],
            "declining_roles": [],
            "steady_roles": [],
        }

        for item in series:
            change = item["expected_change_percent"]
            raw_change = change
            if change is not None:
                change = max(
                    cls.MAX_REPORTED_DECLINE_PERCENT,
                    min(cls.MAX_REPORTED_GROWTH_PERCENT, change),
                )
            kind = item["series_type"]
            if change is None:
                classification = "steady"
            elif change >= cls.SIGNIFICANT_CHANGE_PERCENT:
                classification = "emerging"
            elif change <= -cls.SIGNIFICANT_CHANGE_PERCENT:
                classification = "declining"
            else:
                classification = "steady"

            label = item["name"]
            bounded_note = ""
            if item.get("change_percent_capped"):
                limit = (
                    cls.MAX_REPORTED_GROWTH_PERCENT
                    if change >= 0
                    else abs(cls.MAX_REPORTED_DECLINE_PERCENT)
                )
                bounded_note = (
                    f" The displayed percentage is capped at {limit:.0f}% because the "
                    "projected change is unusually large relative to the recent baseline."
                )
            if classification == "emerging":
                explanation = (
                    "Average monthly demand is projected "
                    f"to increase by {change:.1f}% over the requested horizon."
                    f"{bounded_note}"
                )
                recommendation = f"Prioritize practical experience and portfolio work in {label}."
            elif classification == "declining":
                explanation = (
                    "Average monthly demand is projected "
                    f"to decrease by {abs(change):.1f}% over the requested horizon."
                    f"{bounded_note}"
                )
                recommendation = f"Keep {label} in context and pair it with growing adjacent skills or roles."
            else:
                explanation = (
                    "Demand is projected to remain broadly stable "
                    "over the requested horizon."
                )
                recommendation = f"Maintain relevant experience in {label} and monitor new market signals."

            report = {
                **item,
                "expected_change_percent": change,
                "change_percent_capped": change != raw_change,
                "classification": classification,
                "explanation": explanation,
                "recommendation": recommendation,
                "confidence": (
                    "moderate"
                    if item["observations"] >= 12 and source_postings >= 30
                    else "early signal"
                ),
            }
            trends[f"{classification}_{kind}"].append(report)

        for name in trends:
            trends[name].sort(
                key=lambda item: (
                    item["expected_change_percent"] or 0,
                    item["forecasted_monthly_average"],
                ),
                reverse=name.startswith("emerging") or name.startswith("steady"),
            )

        emerging = sorted(
            trends["emerging_skills"] + trends["emerging_roles"],
            key=lambda item: item["expected_change_percent"] or 0,
            reverse=True,
        )
        declining = sorted(
            trends["declining_skills"] + trends["declining_roles"],
            key=lambda item: item["expected_change_percent"] or 0,
        )
        if emerging and declining:
            summary = (
                f"Based on {source_postings} dated postings, over the next "
                f"{horizon_months} months demand for "
                f"{emerging[0]['name']} ({emerging[0]['series_type'][:-1]}) is projected to rise "
                f"{emerging[0]['expected_change_percent']:.1f}%, while demand for "
                f"{declining[0]['name']} ({declining[0]['series_type'][:-1]}) is projected to fall "
                f"{abs(declining[0]['expected_change_percent']):.1f}%."
            )
        elif emerging:
            summary = (
                f"Based on {source_postings} dated postings, over the next "
                f"{horizon_months} months {emerging[0]['name']} "
                f"({emerging[0]['series_type'][:-1]}) is the strongest growth signal, with "
                f"projected demand up {emerging[0]['expected_change_percent']:.1f}%."
            )
        elif declining:
            summary = (
                f"Based on {source_postings} dated postings, over the next "
                f"{horizon_months} months {declining[0]['name']} "
                f"({declining[0]['series_type'][:-1]}) is the clearest decline signal, with "
                f"projected demand down {abs(declining[0]['expected_change_percent']):.1f}%."
            )
        else:
            summary = (
                f"Based on {source_postings} dated postings, the selected models project broadly "
                f"stable demand for the tracked skills and roles over the next {horizon_months} months."
            )

        return {
            "generated_at": generated_at.astimezone(timezone.utc).isoformat(),
            "summary": summary,
            "confidence": (
                "moderate"
                if source_postings >= 30 and any(item["observations"] >= 12 for item in series)
                else "early signal"
            ),
            "source_postings": source_postings,
            "horizon_months": horizon_months,
            **trends,
        }