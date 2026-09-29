from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import ContributionForm, DeleteForm, SavingsGoalForm
from ..models import SavingsContribution, SavingsGoal

savings_bp = Blueprint("savings", __name__)


@savings_bp.get("/savings")
@login_required
def list_goals():
    goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.deadline.asc().nullslast()).all()
    return render_template("savings/list.html", goals=goals, delete_form=DeleteForm())


@savings_bp.route("/savings/new", methods=["GET", "POST"])
@login_required
def new_goal():
    form = SavingsGoalForm()
    if form.validate_on_submit():
        db.session.add(SavingsGoal(user_id=current_user.id, name=form.name.data.strip(), target_amount=form.target_amount.data, deadline=form.deadline.data))
        db.session.commit()
        flash("Savings goal created.", "success")
        return redirect(url_for("savings.list_goals"))
    return render_template("savings/form.html", form=form)


@savings_bp.route("/savings/<int:goal_id>/contribute", methods=["GET", "POST"])
@login_required
def contribute(goal_id):
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    form = ContributionForm()
    if form.validate_on_submit():
        db.session.add(SavingsContribution(goal_id=goal.id, amount=form.amount.data, date=form.date.data, note=(form.note.data or "").strip()))
        db.session.commit()
        flash("Contribution added.", "success")
        return redirect(url_for("savings.list_goals"))
    return render_template("savings/contribute.html", goal=goal, form=form)


@savings_bp.post("/savings/<int:goal_id>/delete")
@login_required
def delete_goal(goal_id):
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    form = DeleteForm()
    if form.validate_on_submit():
        db.session.delete(goal)
        db.session.commit()
        flash("Savings goal deleted.", "info")
    return redirect(url_for("savings.list_goals"))
