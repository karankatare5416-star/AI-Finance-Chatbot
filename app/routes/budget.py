from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import BudgetSaveForm
from ..models import Budget, ExpenseCategory
from ..services.ai_service import generate_advice
from ..services.analytics_service import budget_status, month_summary, selected_month

budget_bp = Blueprint("budget", __name__)


@budget_bp.get("/budget")
@login_required
def budget():
    month = selected_month(request.args.get("month"))
    rows = budget_status(current_user, month)
    alerts = [row for row in rows if row["status"] in {"Warning", "Exceeded"}]
    return render_template("budget.html", month=month, rows=rows, alerts=alerts, summary=month_summary(current_user, month), form=BudgetSaveForm())


@budget_bp.post("/budget/save")
@login_required
def save_budget():
    month = selected_month(request.form.get("month"))
    form = BudgetSaveForm()
    if form.validate_on_submit():
        for key, value in request.form.items():
            if not key.startswith("limit_"):
                continue
            try:
                category_id = int(key.split("_", 1)[1])
                category = ExpenseCategory.query.filter_by(id=category_id, user_id=current_user.id).first()
                if not category:
                    continue
                amount = float(value or 0)
                budget = Budget.query.filter_by(user_id=current_user.id, category_id=category_id, month=month).first()
                if amount <= 0:
                    if budget:
                        db.session.delete(budget)
                elif budget:
                    budget.limit_amount = amount
                else:
                    db.session.add(Budget(user_id=current_user.id, category_id=category_id, month=month, limit_amount=amount))
            except (TypeError, ValueError):
                continue
        db.session.commit()
        flash("Budget limits saved.", "success")
    return redirect(url_for("budget.budget", month=month))


@budget_bp.post("/budget/generate")
@login_required
def generate_budget():
    month = selected_month(request.form.get("month"))
    recommendation = generate_advice(current_user, month, kind="budget")
    for item in recommendation.content_json.get("budget", []):
        category = ExpenseCategory.query.filter_by(user_id=current_user.id, name=item.get("category", "")).first()
        try:
            amount = float(item.get("amount", 0))
        except (TypeError, ValueError):
            continue
        if category and amount > 0:
            budget = Budget.query.filter_by(user_id=current_user.id, category_id=category.id, month=month).first()
            if budget:
                budget.limit_amount = amount
            else:
                db.session.add(Budget(user_id=current_user.id, category_id=category.id, month=month, limit_amount=amount))
    db.session.commit()
    flash("Your personalized budget is ready. Review and adjust the limits before relying on them.", "success")
    return redirect(url_for("budget.budget", month=month))
