import secrets
from datetime import date

from flask import Flask, abort, g, render_template, request, session

from app.config import Config
from app.extensions import db
from app.labels import (
    ROLE_LABELS,
    STATUS_LABELS,
    WEEKDAYS,
    format_date,
    format_price,
    format_time,
)


def create_app():
    app = Flask(__name__, template_folder="views", static_folder="static")
    app.config.from_object(Config)
    db.init_app(app)

    from app import models  # noqa: F401
    from app.controllers import register_blueprints

    register_blueprints(app)
    _register_hooks(app)
    return app


def _csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["_csrf_token"] = token
    return token


def _register_hooks(app):
    @app.context_processor
    def inject_template_helpers():
        return {
            "csrf_token": _csrf_token,
            "current_user": getattr(g, "user", None),
            "status_labels": STATUS_LABELS,
            "role_labels": ROLE_LABELS,
            "weekday_labels": WEEKDAYS,
            "format_price": format_price,
            "format_date": format_date,
            "format_time": format_time,
            "today": date.today().isoformat(),
        }

    @app.before_request
    def prepare_request():
        if request.method == "POST":
            expected = session.get("_csrf_token", "")
            sent = request.form.get("csrf_token", "")
            if not expected or not sent or not secrets.compare_digest(expected, sent):
                abort(400)

        g.user = None
        user_id = session.get("user_id")
        if not user_id:
            return

        from app.models import User

        user = db.session.get(User, user_id)
        if user is None or not user.is_active:
            session.pop("user_id", None)
            session.pop("role", None)
            return

        session["role"] = user.role
        g.user = user

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template(
            "error.html",
            title="Nieprawidłowy formularz",
            message="Odśwież stronę i wyślij formularz ponownie.",
        ), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "error.html",
            title="Nie znaleziono strony",
            message="Ten adres nie istnieje w aplikacji.",
        ), 404
