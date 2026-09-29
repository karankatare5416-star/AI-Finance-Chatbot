import json
import re
from decimal import Decimal

from flask import current_app

from ..extensions import db
from ..models import AIRecommendation, Expense
from .analytics_service import budget_status, category_rollup, emergency_fund_progress, month_summary, savings_progress


def _json_from_text(text):
    if isinstance(text, dict):
        return text
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        raise ValueError("No JSON object in provider response")
    return json.loads(match.group(0))


def _as_text_list(value, field):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be an array of strings")
    return value


def _normalize_advice(data):
    if not isinstance(data, dict):
        raise ValueError("AI response must be an object")
    score = data.get("health_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
        raise ValueError("health_score must be a number from 0 to 100")
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("summary must be a non-empty string")
    insights = _as_text_list(data.get("insights"), "insights")
    overspending = _as_text_list(data.get("overspending"), "overspending")
    savings = _as_text_list(data.get("savings_recommendations"), "savings_recommendations")
    budget = data.get("budget")
    if not isinstance(budget, list):
        raise ValueError("budget must be an array")
    normalized_budget = []
    for row in budget:
        if not isinstance(row, dict) or not isinstance(row.get("category"), str) or isinstance(row.get("amount"), bool):
            raise ValueError("budget rows must include category and amount")
        try:
            amount = float(row["amount"])
        except (TypeError, ValueError):
            raise ValueError("budget amounts must be numeric")
        if amount < 0:
            raise ValueError("budget amounts cannot be negative")
        normalized_budget.append({"category": row["category"], "amount": round(amount, 2)})
    emergency = data.get("emergency_fund")
    if not isinstance(emergency, dict):
        raise ValueError("emergency_fund must be an object")
    return {"health_score": int(round(score)), "summary": summary.strip(), "insights": insights, "overspending": overspending, "budget": normalized_budget, "savings_recommendations": savings, "emergency_fund": emergency}


def _normalize_chat(data):
    if not isinstance(data, dict) or not isinstance(data.get("answer"), str) or not data["answer"].strip():
        raise ValueError("AI chat response must include a non-empty answer")
    next_steps = data.get("next_steps", [])
    if not isinstance(next_steps, list) or not all(isinstance(item, str) for item in next_steps):
        raise ValueError("next_steps must be an array of strings")
    return {"answer": data["answer"].strip(), "next_steps": next_steps}


def _context(user, month):
    return {"month": month, "occupation_type": user.occupation_type, "monthly_income_baseline": float(user.monthly_income_baseline or 0), "financial_goals": user.financial_goals or "", "summary": {k: float(v) if isinstance(v, Decimal) else v for k, v in month_summary(user, month).items()}, "categories": category_rollup(user, month), "budgets": [{"category": row["category"].name, "limit": float(row["limit"]), "actual": float(row["actual"]), "status": row["status"]} for row in budget_status(user, month)], "goals": [{"name": row["goal"].name, "target": float(row["goal"].target_amount), "contributed": float(row["contributed"])} for row in savings_progress(user)], "emergency": {k: float(v) if isinstance(v, Decimal) else v for k, v in emergency_fund_progress(user, month).items()}}


def _fallback(user, month):
    context = _context(user, month)
    summary = context["summary"]
    income = Decimal(str(summary["income"]))
    expenses = Decimal(str(summary["expenses"]))
    net = Decimal(str(summary["net"]))
    score = 78
    if income and expenses > income:
        score = 38
    elif income and expenses > income * Decimal("0.8"):
        score = 58
    elif income and net > income * Decimal("0.25"):
        score = 88
    overspending = [row["category"] for row in context["budgets"] if row["status"] == "Exceeded"]
    top = context["categories"][0]["name"] if context["categories"] else "your largest spending category"
    advice = []
    if overspending:
        advice.append(f"Review {', '.join(overspending[:3])}; spending is above the saved limit.")
    if net > 0:
        advice.append(f"Protect your {float(net):,.0f} monthly surplus by automating a transfer toward your goals.")
    else:
        advice.append("Start with one small cut in discretionary spending and protect essential payments first.")
    advice.append(f"Your largest tracked category is {top}; compare it with the value it provides before reducing essentials.")
    return {"provider": "fallback", "health_score": max(0, min(100, score)), "summary": "A practical baseline built from your current records. Add a provider key for richer personalized language.", "insights": advice, "overspending": overspending, "budget": [{"category": row["category"].name, "amount": round(float((income * Decimal("0.5")) / max(1, len(context["categories"]))), 2)} for row in budget_status(user, month) if row["category"].name not in {"Savings"}], "savings_recommendations": ["Build a 3-month emergency reserve before taking on new discretionary commitments.", "Schedule a recurring transfer on payday, even if the amount is modest."], "emergency_fund": context["emergency"], "context": context}


def _provider_json(user, month, prompt):
    provider = current_app.config.get("AI_PROVIDER", "auto")
    if provider in {"auto", "gemini"} and current_app.config.get("GEMINI_API_KEY"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=current_app.config["GEMINI_API_KEY"])
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return _json_from_text(response.text), "gemini"
        except Exception:
            if provider == "gemini":
                raise
    if provider in {"auto", "openai"} and current_app.config.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=current_app.config["OPENAI_API_KEY"], timeout=20)
            response = client.chat.completions.create(model=current_app.config.get("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.2, response_format={"type": "json_object"}, messages=[{"role": "system", "content": "Return valid JSON only. You provide educational personal finance guidance, not regulated advice."}, {"role": "user", "content": prompt}])
            return _json_from_text(response.choices[0].message.content), "openai"
        except Exception:
            if provider == "openai":
                raise
    raise RuntimeError("No AI provider configured")


def generate_advice(user, month, kind="full"):
    context = _context(user, month)
    fallback = _fallback(user, month)
    prompt = f"You are a careful personal finance coach. Use this user-owned JSON context: {json.dumps(context)}. Return JSON with keys health_score (0-100 integer), summary (string), insights (array of strings), overspending (array of category names), budget (array of objects with category and amount), savings_recommendations (array of strings), emergency_fund (object). Adapt advice to occupation type {user.occupation_type}. Do not invent transactions."
    try:
        data, provider = _provider_json(user, month, prompt)
        data = {**fallback, **_normalize_advice(data), "provider": provider, "context": context}
    except Exception:
        data = fallback
    recommendation = AIRecommendation(user_id=user.id, month=month, kind=kind, title="Your personalized finance snapshot", content_json=data, provider=data.get("provider", "fallback"), health_score=int(data.get("health_score", 0)))
    db.session.add(recommendation)
    db.session.commit()
    return recommendation


def answer_question(user, month, question):
    context = _context(user, month)
    fallback = {"provider": "fallback", "answer": f"Based on {month}, your income is {user.symbol}{context['summary']['income']:,.0f}, expenses are {user.symbol}{context['summary']['expenses']:,.0f}, and net savings are {user.symbol}{context['summary']['net']:,.0f}. For your question, start with the highest-impact category and keep an emergency buffer of 3–6 months of expenses.", "next_steps": [], "context": context}
    prompt = f"Answer this personal finance question using only the user's data. Question: {question}. User data: {json.dumps(context)}. Return JSON with an answer string and two short next_steps strings. Be concise, educational, and avoid regulated advice."
    try:
        data, provider = _provider_json(user, month, prompt)
        response = {**fallback, **_normalize_chat(data), "provider": provider}
    except Exception:
        response = fallback
    recommendation = AIRecommendation(user_id=user.id, month=month, kind="chat", title="Advisor answer", content_json=response, provider=response.get("provider", "fallback"), health_score=None)
    db.session.add(recommendation)
    db.session.commit()
    return response
