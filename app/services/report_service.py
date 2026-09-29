import csv
import io

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import MonthlyReport
from .analytics_service import budget_status, category_rollup, month_summary, savings_progress
from .ai_service import generate_advice


def build_report(user, month):
    summary = month_summary(user, month)
    categories = category_rollup(user, month)
    budgets = budget_status(user, month)
    report = {
        "month": month,
        "summary": {key: float(value) if hasattr(value, "as_tuple") else value for key, value in summary.items()},
        "top_categories": categories[:5],
        "budget_adherence": [{"category": item["category"].name, "limit": float(item["limit"]), "actual": float(item["actual"]), "status": item["status"]} for item in budgets],
        "savings_goals": [{"name": item["goal"].name, "target": float(item["goal"].target_amount), "contributed": float(item["contributed"]), "progress": item["progress"]} for item in savings_progress(user)],
        "next_month_goals": ["Review any exceeded category before the next month begins.", "Keep a recurring savings transfer active, even during variable-income months."],
    }
    return report


def generate_monthly_report(user, month):
    summary = build_report(user, month)
    recommendation = generate_advice(user, month, kind="monthly_report")
    summary["ai_insights"] = recommendation.content_json
    report = MonthlyReport.query.filter_by(user_id=user.id, month=month).first()
    if report:
        report.summary_json = summary
    else:
        report = MonthlyReport(user_id=user.id, month=month, summary_json=summary)
        db.session.add(report)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        report = MonthlyReport.query.filter_by(user_id=user.id, month=month).first()
    return report


def csv_bytes(report):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Personal Finance Advisor Bot", report.month])
    writer.writerow(["Metric", "Value"])
    for key, value in report.summary_json.get("summary", {}).items():
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(["Top category", "Amount"])
    for item in report.summary_json.get("top_categories", []):
        writer.writerow([item["name"], item["amount"]])
    return output.getvalue().encode("utf-8")
