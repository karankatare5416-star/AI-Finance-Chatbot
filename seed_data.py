from datetime import date, timedelta
from decimal import Decimal

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import DEFAULT_CATEGORIES, Expense, ExpenseCategory, Income, SavingsContribution, SavingsGoal, User


def seed():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=app.config["DEMO_EMAIL"]).first()
        if not user:
            user = User(name="Demo Finance User", email=app.config["DEMO_EMAIL"], currency="INR", monthly_income_baseline=Decimal("85000"), financial_goals="Build an emergency fund and save for a home down payment.", occupation_type="Salaried")
            user.set_password(app.config["DEMO_PASSWORD"])
            db.session.add(user)
            db.session.flush()
        for index, name in enumerate(DEFAULT_CATEGORIES):
            if not ExpenseCategory.query.filter_by(user_id=user.id, name=name).first():
                db.session.add(ExpenseCategory(user_id=user.id, name=name, is_default=True, color=["#0F766E", "#2563EB", "#F59E0B", "#7C3AED", "#DC5A5A"][index % 5]))
        db.session.flush()
        month_start = date.today().replace(day=1)
        if not Income.query.filter_by(user_id=user.id).first():
            db.session.add_all([Income(user_id=user.id, source="Primary salary", amount=Decimal("85000"), date=month_start + timedelta(days=2), recurring=True), Income(user_id=user.id, source="Freelance project", amount=Decimal("12000"), date=month_start + timedelta(days=8), recurring=False)])
        if not Expense.query.filter_by(user_id=user.id).first():
            categories = {c.name: c for c in ExpenseCategory.query.filter_by(user_id=user.id).all()}
            sample = [("Rent", 24000, "Home rent", "Bank transfer"), ("Groceries", 8500, "Monthly groceries", "Card"), ("Transport", 3600, "Commute and rides", "UPI"), ("Utilities", 4200, "Electricity and internet", "UPI"), ("Entertainment", 2200, "Streaming and dining", "Card"), ("Savings", 15000, "Automated savings", "Bank transfer")]
            db.session.add_all([Expense(user_id=user.id, category_id=categories[name].id, amount=Decimal(str(amount)), date=month_start + timedelta(days=10 + idx), description=description, payment_method=method) for idx, (name, amount, description, method) in enumerate(sample)])
        goal = SavingsGoal.query.filter_by(user_id=user.id, name="Emergency fund").first()
        if not goal:
            goal = SavingsGoal(user_id=user.id, name="Emergency fund", target_amount=Decimal("255000"), deadline=date.today() + timedelta(days=180))
            db.session.add(goal)
            db.session.flush()
            db.session.add(SavingsContribution(goal_id=goal.id, amount=Decimal("90000"), date=date.today(), note="Starting balance"))
        db.session.commit()
        print(f"Demo account ready: {user.email} / {app.config['DEMO_PASSWORD']}")


if __name__ == "__main__":
    seed()
