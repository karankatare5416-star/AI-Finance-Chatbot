from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .config import Config
from .extensions import csrf, db, login_manager


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if isinstance(config_object, dict):
        app.config.update(config_object)
    elif config_object is not None:
        app.config.from_object(config_object)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    configured_secure = app.config["SESSION_COOKIE_SECURE"]
    configured_samesite = app.config["SESSION_COOKIE_SAMESITE"]

    @app.before_request
    def adapt_preview_cookie_policy():
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip().lower()
        is_https = request.is_secure or forwarded_proto == "https"
        app.config["SESSION_COOKIE_SECURE"] = configured_secure or is_https
        app.config["REMEMBER_COOKIE_SECURE"] = configured_secure or is_https
        app.config["SESSION_COOKIE_SAMESITE"] = "None" if is_https else configured_samesite
        app.config["REMEMBER_COOKIE_SAMESITE"] = "None" if is_https else configured_samesite

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.income import income_bp
    from .routes.expenses import expenses_bp
    from .routes.budget import budget_bp
    from .routes.savings import savings_bp
    from .routes.ai import ai_bp
    from .routes.reports import reports_bp
    from .routes.profile import profile_bp

    for blueprint in [auth_bp, dashboard_bp, income_bp, expenses_bp, budget_bp, savings_bp, ai_bp, reports_bp, profile_bp]:
        app.register_blueprint(blueprint)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "personal-finance-advisor"})

    @app.get("/manus-routes.json")
    def route_manifest():
        manifest_path = Path(app.static_folder) / "manus-routes.json"
        return app.response_class(manifest_path.read_text(encoding="utf-8"), mimetype="application/json")

    @app.context_processor
    def inject_globals():
        return {"app_name": "Personal Finance Advisor Bot"}

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    with app.app_context():
        db.create_all()

    return app
