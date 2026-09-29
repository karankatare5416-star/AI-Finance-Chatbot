from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..services.report_service import csv_bytes, generate_monthly_report
from ..models import MonthlyReport
from ..services.analytics_service import selected_month

reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/reports")
@login_required
def reports():
    rows = MonthlyReport.query.filter_by(user_id=current_user.id).order_by(MonthlyReport.month.desc()).all()
    return render_template("reports/list.html", reports=rows, month=selected_month(request.args.get("month")))


@reports_bp.post("/reports/generate")
@login_required
def generate_report():
    month = selected_month(request.form.get("month"))
    report = generate_monthly_report(current_user, month)
    flash("Monthly report generated.", "success")
    return redirect(url_for("reports.view_report", report_id=report.id))


@reports_bp.get("/reports/<int:report_id>")
@login_required
def view_report(report_id):
    report = MonthlyReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    return render_template("reports/detail.html", report=report)


@reports_bp.get("/reports/<int:report_id>/print")
@login_required
def print_report(report_id):
    report = MonthlyReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    return render_template("reports/print.html", report=report)


@reports_bp.get("/reports/<int:report_id>/csv")
@login_required
def export_csv(report_id):
    report = MonthlyReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    return Response(csv_bytes(report), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=finance-report-{report.month}.csv"})


@reports_bp.get("/reports/<int:report_id>/pdf")
@login_required
def export_pdf(report_id):
    report = MonthlyReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(f"Finance report {report.month}")
        pdf.drawString(48, 800, f"Personal Finance Advisor Bot — {report.month}")
        y = 770
        for key, value in report.summary_json.get("summary", {}).items():
            pdf.drawString(60, y, f"{key.replace('_', ' ').title()}: {value}")
            y -= 18
        y -= 10
        pdf.drawString(60, y, "Top categories")
        y -= 18
        for item in report.summary_json.get("top_categories", []):
            pdf.drawString(72, y, f"{item['name']}: {item['amount']}")
            y -= 16
        pdf.save()
        return Response(buffer.getvalue(), mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=finance-report-{report.month}.pdf"})
    except Exception:
        flash("PDF export is temporarily unavailable. Use print or CSV export instead.", "warning")
        return redirect(url_for("reports.view_report", report_id=report_id))
