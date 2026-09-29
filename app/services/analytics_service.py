from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func

from ..extensions import db
from ..models import Budget, Expense, ExpenseCategory, Income, SavingsGoal


def selected_month(value=None):
    if value:
        try:
            datetime.strptime(value, "%Y-%m")
            return value
        except ValueError:
            pass
    return date.today().strftime("%Y-%m")


def month_range(month):
    start = datetime.strptime(month + "-01", "%Y-%m-%d").date()
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, end


def month_summary(user, month):
    start, end = month_range(month)
    income = db.session.query(func.coalesce(func.sum(Income.amount), 0)).filter(Income.user_id == user.id, Income.date >= start, Income.date < end).scalar() or 0
    expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.user_id == user.id, Expense.date >= start, Expense.date < end).scalar() or 0
    income = Decimal(str(income))
    expenses = Decimal(str(expenses))
    net = income - expenses
    savings_rate = float((net / income) * 100) if income else 0
    return {"month": month, "income": income, "expenses": expenses, "net": net, "savings_rate": round(savings_rate, 1)}


def category_rollup(user, month):
    start, end = month_range(month)
    rows = db.session.query(ExpenseCategory.name, func.coalesce(func.sum(Expense.amount), 0), ExpenseCategory.color).join(Expense, Expense.category_id == ExpenseCategory.id).filter(Expense.user_id == user.id, Expense.date >= start, Expense.date < end).group_by(ExpenseCategory.id).order_by(func.sum(Expense.amount).desc()).all()
    return [{"name": name, "amount": float(amount), "color": color} for name, amount, color in rows]


def budget_status(user, month):
    start, end = month_range(month)
    categories = ExpenseCategory.query.filter_by(user_id=user.id).order_by(ExpenseCategory.name).all()
    result = []
    for category in categories:
        budget = Budget.query.filter_by(user_id=user.id, category_id=category.id, month=month).first()
        actual = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.user_id == user.id, Expense.category_id == category.id, Expense.date >= start, Expense.date < end).scalar() or 0
        limit = Decimal(str(budget.limit_amount)) if budget else Decimal("0")
        actual = Decimal(str(actual))
        ratio = float(actual / limit * 100) if limit else 0
        status = "No limit" if not limit else "Exceeded" if actual > limit else "Warning" if ratio >= 80 else "Safe"
        result.append({"category": category, "limit": limit, "actual": actual, "ratio": min(100, ratio), "status": status})
    return result


def trend_series(user, months=6):
    today = date.today().replace(day=1)
    output = []
    for offset in range(months - 1, -1, -1):
        year = today.year + (today.month - 1 - offset) // 12
        month_num = (today.month - 1 - offset) % 12 + 1
        month = f"{year:04d}-{month_num:02d}"
        summary = month_summary(user, month)
        output.append({"month": month, "income": float(summary["income"]), "expenses": float(summary["expenses"])})
    return output


def savings_progress(user):
    goals = SavingsGoal.query.filter_by(user_id=user.id).order_by(SavingsGoal.deadline.asc().nullslast()).all()
    return [{"goal": goal, "contributed": goal.contributed, "progress": goal.progress_percent} for goal in goals]


def emergency_fund_progress(user, month):
    summary = month_summary(user, month)
    expenses = summary["expenses"] or Decimal(str(user.monthly_income_baseline or 0)) * Decimal("0.7")
    target = expenses * 3
    saved = sum((item["contributed"] for item in savings_progress(user)), Decimal("0"))
    return {"monthly_expenses": expenses, "target": target, "saved": saved, "progress": min(100, float(saved / target * 100)) if target else 0}


def dashboard_payload(user, month):
    summary = month_summary(user, month)
    categories = category_rollup(user, month)
    return {"summary": summary, "categories": categories, "trend": trend_series(user), "budgets": budget_status(user, month), "goals": savings_progress(user), "emergency": emergency_fund_progress(user, month)}
