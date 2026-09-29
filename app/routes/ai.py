from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..forms import AdvisorQuestionForm
from ..models import AIRecommendation
from ..services.ai_service import answer_question, generate_advice
from ..services.analytics_service import selected_month

ai_bp = Blueprint("ai", __name__)


@ai_bp.get("/advisor")
@login_required
def advisor():
    month = selected_month(request.args.get("month"))
    history = AIRecommendation.query.filter_by(user_id=current_user.id).order_by(AIRecommendation.created_at.desc()).limit(10).all()
    return render_template("advisor.html", month=month, history=history, form=AdvisorQuestionForm())


@ai_bp.post("/advisor/generate")
@login_required
def generate():
    month = selected_month(request.form.get("month"))
    recommendation = generate_advice(current_user, month)
    flash(f"Your financial snapshot is ready ({recommendation.provider} analysis).", "success")
    return redirect(url_for("ai.advisor", month=month))


@ai_bp.post("/advisor/chat")
@login_required
def chat():
    month = selected_month(request.form.get("month"))
    form = AdvisorQuestionForm()
    if form.validate_on_submit():
        response = answer_question(current_user, month, form.question.data.strip())
        flash("Your advisor answered using your saved records.", "success")
        return render_template("advisor.html", month=month, history=AIRecommendation.query.filter_by(user_id=current_user.id).order_by(AIRecommendation.created_at.desc()).limit(10).all(), form=AdvisorQuestionForm(), answer=response)
    flash("Please ask a little more detail so the advisor can help.", "warning")
    return redirect(url_for("ai.advisor", month=month))
