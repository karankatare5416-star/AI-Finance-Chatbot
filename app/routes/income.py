from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import DeleteForm, IncomeForm
from ..models import Income
from ..services.analytics_service import month_range, selected_month

income_bp = Blueprint("income", __name__)


@income_bp.get("/income")
@login_required
def list_income():
    month = selected_month(request.args.get("month"))
    start, end = month_range(month)
    records = Income.query.filter(Income.user_id == current_user.id, Income.date >= start, Income.date < end).order_by(Income.date.desc(), Income.id.desc()).all()
    delete_form = DeleteForm()
    return render_template("income/list.html", records=records, delete_form=delete_form, month=month)


@income_bp.route("/income/new", methods=["GET", "POST"])
@login_required
def new_income():
    form = IncomeForm()
    if form.validate_on_submit():
        db.session.add(Income(user_id=current_user.id, source=form.source.data.strip(), amount=form.amount.data, date=form.date.data, recurring=form.recurring.data))
        db.session.commit()
        flash("Income record added.", "success")
        return redirect(url_for("income.list_income", month=form.date.data.strftime("%Y-%m")))
    return render_template("income/form.html", form=form, title="Add income")


@income_bp.route("/income/<int:income_id>/edit", methods=["GET", "POST"])
@login_required
def edit_income(income_id):
    record = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()
    form = IncomeForm(obj=record)
    if form.validate_on_submit():
        form.populate_obj(record)
        record.source = record.source.strip()
        db.session.commit()
        flash("Income record updated.", "success")
        return redirect(url_for("income.list_income", month=form.date.data.strftime("%Y-%m")))
    return render_template("income/form.html", form=form, title="Edit income")


@income_bp.post("/income/<int:income_id>/delete")
@login_required
def delete_income(income_id):
    record = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()
    form = DeleteForm()
    if form.validate_on_submit():
        month = record.date.strftime("%Y-%m")
        db.session.delete(record)
        db.session.commit()
        flash("Income record deleted.", "info")
        return redirect(url_for("income.list_income", month=month))
    return redirect(url_for("income.list_income"))
