from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from ..models import AIRecommendation, Expense
from ..services.analytics_service import dashboard_payload, month_range, selected_month


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    month = selected_month(request.args.get("month"))
    start, end = month_range(month)
    payload = dashboard_payload(current_user, month)
    recent = Expense.query.filter(Expense.user_id == current_user.id, Expense.date >= start, Expense.date < end).order_by(Expense.date.desc(), Expense.id.desc()).limit(8).all()
    latest_recommendation = AIRecommendation.query.filter_by(user_id=current_user.id, month=month).order_by(AIRecommendation.created_at.desc()).first()
    chart_data = {"categories": payload["categories"], "trend": payload["trend"]}
    return render_template("dashboard.html", month=month, payload=payload, chart_data=chart_data, recent=recent, latest_recommendation=latest_recommendation)
