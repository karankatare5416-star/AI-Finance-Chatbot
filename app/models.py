from datetime import date, datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


DEFAULT_CATEGORIES = [
    "Rent", "Food", "Transport", "Utilities", "Education", "Healthcare",
    "Entertainment", "Groceries", "Savings", "Misc",
]
OCCUPATIONS = {"Salaried", "Student", "Freelancer", "Household"}


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    currency = db.Column(db.String(8), default="INR", nullable=False)
    monthly_income_baseline = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    financial_goals = db.Column(db.Text, default="", nullable=False)
    occupation_type = db.Column(db.String(30), default="Salaried", nullable=False)

    incomes = db.relationship("Income", back_populates="user", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    categories = db.relationship("ExpenseCategory", back_populates="user", cascade="all, delete-orphan")
    budgets = db.relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    savings_goals = db.relationship("SavingsGoal", back_populates="user", cascade="all, delete-orphan")
    reports = db.relationship("MonthlyReport", back_populates="user", cascade="all, delete-orphan")
    recommendations = db.relationship("AIRecommendation", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def symbol(self):
        return {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(self.currency, self.currency + " ")


class Income(TimestampMixin, db.Model):
    __tablename__ = "incomes"
    __table_args__ = (db.Index("ix_income_user_date", "user_id", "date"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    recurring = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship("User", back_populates="incomes")


class ExpenseCategory(TimestampMixin, db.Model):
    __tablename__ = "expense_categories"
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_category_user_name"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    color = db.Column(db.String(12), default="#0F766E", nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship("User", back_populates="categories")
    expenses = db.relationship("Expense", back_populates="category")
    budgets = db.relationship("Budget", back_populates="category")


class Expense(TimestampMixin, db.Model):
    __tablename__ = "expenses"
    __table_args__ = (db.Index("ix_expense_user_date_category", "user_id", "date", "category_id"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    description = db.Column(db.String(255), default="", nullable=False)
    payment_method = db.Column(db.String(60), default="UPI", nullable=False)
    user = db.relationship("User", back_populates="expenses")
    category = db.relationship("ExpenseCategory", back_populates="expenses")


class Budget(TimestampMixin, db.Model):
    __tablename__ = "budgets"
    __table_args__ = (db.UniqueConstraint("user_id", "category_id", "month", name="uq_budget_user_category_month"), db.Index("ix_budget_user_month", "user_id", "month"))
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("expense_categories.id", ondelete="CASCADE"), nullable=False)
    month = db.Column(db.String(7), nullable=False)
    limit_amount = db.Column(db.Numeric(12, 2), nullable=False)
    user = db.relationship("User", back_populates="budgets")
    category = db.relationship("ExpenseCategory", back_populates="budgets")


class SavingsGoal(TimestampMixin, db.Model):
    __tablename__ = "savings_goals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    user = db.relationship("User", back_populates="savings_goals")
    contributions = db.relationship("SavingsContribution", back_populates="goal", cascade="all, delete-orphan")

    @property
    def contributed(self):
        return sum((Decimal(str(c.amount)) for c in self.contributions), Decimal("0"))

    @property
    def progress_percent(self):
        if not self.target_amount:
            return 0
        return min(100, float(self.contributed / Decimal(str(self.target_amount)) * 100))


class SavingsContribution(TimestampMixin, db.Model):
    __tablename__ = "savings_contributions"
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    note = db.Column(db.String(255), default="", nullable=False)
    goal = db.relationship("SavingsGoal", back_populates="contributions")


class MonthlyReport(TimestampMixin, db.Model):
    __tablename__ = "monthly_reports"
    __table_args__ = (db.UniqueConstraint("user_id", "month", name="uq_report_user_month"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)
    summary_json = db.Column(db.JSON, nullable=False, default=dict)
    user = db.relationship("User", back_populates="reports")


class AIRecommendation(TimestampMixin, db.Model):
    __tablename__ = "ai_recommendations"
    __table_args__ = (db.Index("ix_recommendation_user_month", "user_id", "month"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)
    kind = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    content_json = db.Column(db.JSON, nullable=False, default=dict)
    provider = db.Column(db.String(40), default="fallback", nullable=False)
    health_score = db.Column(db.Integer, nullable=True)
    user = db.relationship("User", back_populates="recommendations")
