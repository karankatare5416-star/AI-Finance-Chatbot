from datetime import date

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, DecimalField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError

from .models import OCCUPATIONS


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class RegistrationForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    occupation_type = SelectField("Occupation type", choices=[(x, x) for x in sorted(OCCUPATIONS)], validators=[DataRequired()])
    submit = SubmitField("Create account")


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    currency = SelectField("Currency", choices=[("INR", "INR — Indian Rupee"), ("USD", "USD — US Dollar"), ("EUR", "EUR — Euro"), ("GBP", "GBP — Pound")], validators=[DataRequired()])
    monthly_income_baseline = DecimalField("Monthly income baseline", validators=[Optional(), NumberRange(min=0, max=999999999)])
    financial_goals = TextAreaField("Financial goals", validators=[Optional(), Length(max=1000)])
    occupation_type = SelectField("Occupation type", choices=[(x, x) for x in sorted(OCCUPATIONS)], validators=[DataRequired()])
    submit = SubmitField("Save profile")


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    password = PasswordField("New password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Update password")


class IncomeForm(FlaskForm):
    source = StringField("Source", validators=[DataRequired(), Length(max=120)])
    amount = DecimalField("Amount", validators=[DataRequired(), NumberRange(min=0.01, max=999999999)])
    date = DateField("Date", default=date.today, validators=[DataRequired()])
    recurring = BooleanField("Recurring income")
    submit = SubmitField("Save income")


class ExpenseForm(FlaskForm):
    amount = DecimalField("Amount", validators=[DataRequired(), NumberRange(min=0.01, max=999999999)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    date = DateField("Date", default=date.today, validators=[DataRequired()])
    description = StringField("Description", validators=[Optional(), Length(max=255)])
    payment_method = SelectField("Payment method", choices=[("UPI", "UPI"), ("Card", "Card"), ("Cash", "Cash"), ("Bank transfer", "Bank transfer"), ("Other", "Other")], validators=[DataRequired()])
    submit = SubmitField("Save expense")


class CategoryForm(FlaskForm):
    name = StringField("Category name", validators=[DataRequired(), Length(min=2, max=80)])
    submit = SubmitField("Add category")


class BudgetSaveForm(FlaskForm):
    submit = SubmitField("Save budget")


class SavingsGoalForm(FlaskForm):
    name = StringField("Goal name", validators=[DataRequired(), Length(max=120)])
    target_amount = DecimalField("Target amount", validators=[DataRequired(), NumberRange(min=0.01, max=999999999)])
    deadline = DateField("Deadline", validators=[Optional()])
    submit = SubmitField("Create goal")


class ContributionForm(FlaskForm):
    amount = DecimalField("Contribution amount", validators=[DataRequired(), NumberRange(min=0.01, max=999999999)])
    date = DateField("Date", default=date.today, validators=[DataRequired()])
    note = StringField("Note", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Add contribution")


class AdvisorQuestionForm(FlaskForm):
    question = TextAreaField("Ask your advisor", validators=[DataRequired(), Length(min=5, max=1000)])
    submit = SubmitField("Ask advisor")


class MonthForm(FlaskForm):
    month = StringField("Month", validators=[DataRequired(), Length(min=7, max=7)])
    submit = SubmitField("Apply")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")


def validate_month(form, field):
    if len(field.data or "") != 7 or field.data[4] != "-":
        raise ValidationError("Choose a valid month.")
