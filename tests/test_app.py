from datetime import date
from decimal import Decimal
import re

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Expense, ExpenseCategory, Income, MonthlyReport, User
import app.services.ai_service as ai_service
from app.services.ai_service import generate_advice


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email="demo@example.com", password="Password123!"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def register(client, email="demo@example.com", occupation="Salaried"):
    return client.post("/register", data={"name": "Demo User", "email": email, "password": "Password123!", "confirm_password": "Password123!", "occupation_type": occupation}, follow_redirects=True)


def test_authentication_and_protected_routes(client):
    assert client.get("/dashboard").status_code == 302
    response = register(client)
    assert response.status_code == 200
    assert b"Good morning" in response.data
    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert client.get("/income").status_code == 302
    assert login(client).status_code == 200
    assert b"Good morning" in client.get("/dashboard").data


def test_preview_https_cookie_policy_preserves_csrf_session(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.get("/register", headers={"X-Forwarded-Proto": "https"})
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any("SameSite=None" in header and "Secure" in header for header in set_cookie_headers)
    token = re.search(r'name="csrf_token"[^>]+value="([^"]+)"', response.text).group(1)
    response = client.post("/register", headers={"X-Forwarded-Proto": "https"}, data={"csrf_token": token, "name": "Preview User", "email": "preview@example.com", "password": "Password123!", "confirm_password": "Password123!", "occupation_type": "Salaried"}, follow_redirects=True)
    assert response.status_code == 200 and b"Good morning" in response.data


def test_income_expense_crud_and_user_isolation(app, client):
    register(client)
    with app.app_context():
        user = User.query.filter_by(email="demo@example.com").first()
        category = ExpenseCategory.query.filter_by(user_id=user.id, name="Food").first()
        category_id = category.id
    response = client.post("/income/new", data={"source": "Salary", "amount": "50000", "date": "2026-09-01", "recurring": "y"}, follow_redirects=True)
    assert response.status_code == 200 and b"Salary" in response.data
    response = client.post("/expenses/new", data={"amount": "1200", "category_id": str(category_id), "date": "2026-09-02", "description": "Lunch", "payment_method": "UPI"}, follow_redirects=True)
    assert response.status_code == 200 and b"Lunch" in response.data
    with app.app_context():
        expense = Expense.query.filter_by(description="Lunch").first()
        expense_id = expense.id
        assert Income.query.filter_by(source="Salary").count() == 1
    assert client.post(f"/expenses/{expense_id}/edit", data={"amount": "1400", "category_id": str(category_id), "date": "2026-09-02", "description": "Team lunch", "payment_method": "Card"}, follow_redirects=True).status_code == 200
    assert client.post(f"/expenses/{expense_id}/delete", data={}, follow_redirects=True).status_code == 200
    assert b"Team lunch" not in client.get("/expenses?month=2026-09").data
    register(client, email="second@example.com")
    assert client.get(f"/expenses/{expense_id}/edit").status_code == 404


def test_budget_ai_fallback_reports_and_chart_payload(app, client):
    register(client, occupation="Freelancer")
    with app.app_context():
        user = User.query.filter_by(email="demo@example.com").first()
        category = ExpenseCategory.query.filter_by(user_id=user.id, name="Food").first()
        user_id = user.id
        category_id = category.id
    client.post("/income/new", data={"source": "Project", "amount": "60000", "date": "2026-09-03"})
    client.post("/expenses/new", data={"amount": "3500", "category_id": str(category_id), "date": "2026-09-04", "description": "Groceries", "payment_method": "Card"})
    response = client.post("/advisor/generate", data={"month": "2026-09"}, follow_redirects=True)
    assert response.status_code == 200 and (b"fallback" in response.data or b"Fallback" in response.data)
    response = client.post("/budget/generate", data={"month": "2026-09"}, follow_redirects=True)
    assert response.status_code == 200 and b"CATEGORY LIMITS" in response.data
    response = client.post("/reports/generate", data={"month": "2026-09"}, follow_redirects=True)
    assert response.status_code == 200 and b"2026-09 report" in response.data
    with app.app_context():
        assert MonthlyReport.query.filter_by(user_id=user_id, month="2026-09").count() == 1
        recommendation = generate_advice(db.session.get(User, user_id), "2026-09")
        assert recommendation.provider == "fallback"
    dashboard = client.get("/dashboard?month=2026-09")
    assert dashboard.status_code == 200 and b"expenseChart" in dashboard.data and b"trendChart" in dashboard.data


def test_all_personas_have_rule_based_advice(app):
    with app.app_context():
        for index, occupation in enumerate(["Salaried", "Student", "Freelancer", "Household"]):
            user = User(name=f"Persona {index}", email=f"persona{index}@example.com", occupation_type=occupation, monthly_income_baseline=Decimal("30000"))
            user.set_password("Password123!")
            db.session.add(user)
            db.session.flush()
            category = ExpenseCategory(user_id=user.id, name="Food", is_default=True)
            db.session.add(category)
            db.session.flush()
            db.session.add(Income(user_id=user.id, source="Baseline", amount=Decimal("30000"), date=date(2026, 9, 1)))
            db.session.add(Expense(user_id=user.id, category_id=category.id, amount=Decimal("5000"), date=date(2026, 9, 2), description="Food", payment_method="Cash"))
        db.session.commit()
        users = User.query.filter(User.email.like("persona%@example.com")).all()
        for user in users:
            recommendation = generate_advice(user, "2026-09")
            assert recommendation.provider == "fallback"
            assert 0 <= recommendation.health_score <= 100


def test_malformed_provider_payload_falls_back_safely(app, client, monkeypatch):
    register(client)
    with app.app_context():
        user = User.query.filter_by(email="demo@example.com").first()
        monkeypatch.setattr(ai_service, "_provider_json", lambda *_args: ({"health_score": "bad"}, "gemini"))
        recommendation = generate_advice(user, "2026-09")
        assert recommendation.provider == "fallback"
        assert recommendation.health_score == 78


def test_income_and_dashboard_activity_use_selected_month(app, client):
    register(client)
    with app.app_context():
        user = User.query.filter_by(email="demo@example.com").first()
        category = ExpenseCategory.query.filter_by(user_id=user.id, name="Food").first()
        category_id = category.id
    client.post("/income/new", data={"source": "September salary", "amount": "40000", "date": "2026-09-01"})
    client.post("/income/new", data={"source": "October salary", "amount": "41000", "date": "2026-10-01"})
    client.post("/expenses/new", data={"amount": "1000", "category_id": str(category_id), "date": "2026-09-05", "description": "September lunch", "payment_method": "Cash"})
    client.post("/expenses/new", data={"amount": "1100", "category_id": str(category_id), "date": "2026-10-05", "description": "October lunch", "payment_method": "Cash"})
    income = client.get("/income?month=2026-09")
    dashboard = client.get("/dashboard?month=2026-09")
    assert b"September salary" in income.data and b"October salary" not in income.data
    assert b"September lunch" in dashboard.data and b"October lunch" not in dashboard.data
