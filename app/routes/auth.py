from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func

from ..extensions import db
from ..forms import LoginForm, RegistrationForm
from ..models import DEFAULT_CATEGORIES, ExpenseCategory, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("landing.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    form = RegistrationForm()
    if form.validate_on_submit():
        existing = db.session.query(User).filter(func.lower(User.email) == form.email.data.lower()).first()
        if existing:
            form.email.errors.append("That email is already registered.")
        else:
            user = User(name=form.name.data.strip(), email=form.email.data.lower().strip(), occupation_type=form.occupation_type.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            db.session.add_all([ExpenseCategory(user_id=user.id, name=name, is_default=True, color=["#0F766E", "#2563EB", "#F59E0B", "#7C3AED", "#DC5A5A"][idx % 5]) for idx, name in enumerate(DEFAULT_CATEGORIES)])
            db.session.commit()
            login_user(user)
            flash("Welcome to your personal finance workspace.", "success")
            return redirect(url_for("dashboard.dashboard"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(func.lower(User.email) == form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash("You are signed in.", "success")
            return redirect(url_for("dashboard.dashboard"))
        flash("Email or password was not recognised.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.post("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.landing"))
