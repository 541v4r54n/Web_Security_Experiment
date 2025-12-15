from __future__ import annotations

from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for
from dotenv import load_dotenv

from .config import AppConfig
from .db import close_db, get_db, init_db_if_missing
from .security import csrf_token, require_csrf


def create_app() -> Flask:
    load_dotenv()
    cfg = AppConfig.load()

    app = Flask(__name__)
    app.config.from_mapping(cfg.as_flask_config())

    cfg.ensure_dirs()
    init_db_if_missing(cfg.db_path)

    app.teardown_appcontext(close_db)
    app.before_request(require_csrf)

    @app.before_request
    def load_user() -> None:
        from .auth import get_current_user

        g.user = get_current_user()

    app.jinja_env.globals["csrf_token"] = csrf_token

    from .auth import bp as auth_bp
    from .images import bp as images_bp
    from .labs import bp as labs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(images_bp)
    app.register_blueprint(labs_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def api_health():
        user = None
        if getattr(g, "user", None):
            user = {"id": g.user["id"], "username": g.user["username"]}
        return {"ok": True, "time": cfg.now_iso(), "user": user}

    @app.get("/_debug/whoami")
    def debug_whoami():
        # 仅用于本地实验排查，不建议暴露到公网
        return {
            "ip": request.remote_addr,
            "ua": request.headers.get("User-Agent", ""),
            "user": getattr(g, "user", None),
        }

    @app.get("/_redirect/labs")
    def redirect_labs():
        return redirect(url_for("labs.index"))

    # Ensure the DB file is readable at least once (fail fast if path is wrong)
    with app.app_context():
        get_db().execute("SELECT 1")

    return app


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
