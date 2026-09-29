from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import PasswordChangeForm, ProfileForm
from ..models import User

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        duplicate = User.query.filter(User.email == form.email.data.lower().strip(), User.id != current_user.id).first()
        if duplicate:
            form.email.errors.append("That email is already in use.")
        else:
            current_user.name = form.name.data.strip()
            current_user.email = form.email.data.lower().strip()
            current_user.currency = form.currency.data
            current_user.monthly_income_baseline = form.monthly_income_baseline.data or 0
            current_user.financial_goals = form.financial_goals.data or ""
            current_user.occupation_type = form.occupation_type.data
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile.profile"))
    password_form = PasswordChangeForm()
    return render_template("profile.html", form=form, password_form=password_form)


@profile_bp.post("/profile/password")
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password was not correct.", "danger")
        else:
            current_user.set_password(form.password.data)
            db.session.commit()
            flash("Password updated.", "success")
    return redirect(url_for("profile.profile"))
