from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..forms import CategoryForm, DeleteForm, ExpenseForm
from ..models import Expense, ExpenseCategory
from ..services.analytics_service import month_range, selected_month

expenses_bp = Blueprint("expenses", __name__)


def expense_form(categories, obj=None):
    form = ExpenseForm(obj=obj)
    form.category_id.choices = [(category.id, category.name) for category in categories]
    return form


@expenses_bp.get("/expenses")
@login_required
def list_expenses():
    month = selected_month(request.args.get("month"))
    start, end = month_range(month)
    query = Expense.query.filter_by(user_id=current_user.id)
    if request.args.get("category") and request.args.get("category").isdigit():
        query = query.filter(Expense.category_id == int(request.args["category"]))
    if request.args.get("q"):
        term = f"%{request.args['q'].strip()}%"
        query = query.filter(or_(Expense.description.ilike(term), Expense.payment_method.ilike(term)))
    query = query.filter(Expense.date >= start, Expense.date < end)
    records = query.order_by(Expense.date.desc(), Expense.id.desc()).all()
    categories = ExpenseCategory.query.filter_by(user_id=current_user.id).order_by(ExpenseCategory.name).all()
    return render_template("expenses/list.html", records=records, categories=categories, month=month, delete_form=DeleteForm())


@expenses_bp.route("/expenses/new", methods=["GET", "POST"])
@login_required
def new_expense():
    categories = ExpenseCategory.query.filter_by(user_id=current_user.id).order_by(ExpenseCategory.name).all()
    form = expense_form(categories)
    if form.validate_on_submit():
        category = ExpenseCategory.query.filter_by(id=form.category_id.data, user_id=current_user.id).first_or_404()
        db.session.add(Expense(user_id=current_user.id, category_id=category.id, amount=form.amount.data, date=form.date.data, description=(form.description.data or "").strip(), payment_method=form.payment_method.data))
        db.session.commit()
        flash("Expense saved.", "success")
        return redirect(url_for("expenses.list_expenses", month=form.date.data.strftime("%Y-%m")))
    return render_template("expenses/form.html", form=form, title="Add expense")


@expenses_bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    record = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    categories = ExpenseCategory.query.filter_by(user_id=current_user.id).order_by(ExpenseCategory.name).all()
    form = expense_form(categories, record)
    if form.validate_on_submit():
        category = ExpenseCategory.query.filter_by(id=form.category_id.data, user_id=current_user.id).first_or_404()
        record.amount = form.amount.data
        record.category_id = category.id
        record.date = form.date.data
        record.description = (form.description.data or "").strip()
        record.payment_method = form.payment_method.data
        db.session.commit()
        flash("Expense updated.", "success")
        return redirect(url_for("expenses.list_expenses", month=form.date.data.strftime("%Y-%m")))
    return render_template("expenses/form.html", form=form, title="Edit expense")


@expenses_bp.post("/expenses/<int:expense_id>/delete")
@login_required
def delete_expense(expense_id):
    record = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    form = DeleteForm()
    if form.validate_on_submit():
        db.session.delete(record)
        db.session.commit()
        flash("Expense deleted.", "info")
    return redirect(url_for("expenses.list_expenses"))


@expenses_bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if ExpenseCategory.query.filter_by(user_id=current_user.id, name=name).first():
            flash("That category already exists.", "warning")
        else:
            db.session.add(ExpenseCategory(user_id=current_user.id, name=name, color="#0F766E"))
            db.session.commit()
            flash("Category added.", "success")
        return redirect(url_for("expenses.categories"))
    rows = ExpenseCategory.query.filter_by(user_id=current_user.id).order_by(ExpenseCategory.name).all()
    return render_template("expenses/categories.html", categories=rows, form=form)


@expenses_bp.post("/categories/<int:category_id>/delete")
@login_required
def delete_category(category_id):
    category = ExpenseCategory.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    if category.expenses:
        flash("Categories with expenses cannot be deleted; rename or keep it for history.", "warning")
    else:
        db.session.delete(category)
        db.session.commit()
        flash("Category deleted.", "info")
    return redirect(url_for("expenses.categories"))
