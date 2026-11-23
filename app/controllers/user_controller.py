from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from app.controllers.auth_controller import _valid_email, _valid_phone
from app.decorators import admin_required
from app.extensions import db
from app.models import User

bp = Blueprint("users", __name__)


@bp.get("/admin/users")
@admin_required
def admin_list():
    users = db.session.scalars(db.select(User).order_by(User.last_name, User.first_name)).all()
    return render_template("admin/users.html", users=users)


@bp.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    form = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone or "",
    }
    errors = []
    if request.method == "POST":
        form = {
            "first_name": request.form.get("first_name", "").strip(),
            "last_name": request.form.get("last_name", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
            "phone": request.form.get("phone", "").strip(),
        }
        errors = _profile_errors(user, form)
        if not errors:
            user.first_name = form["first_name"]
            user.last_name = form["last_name"]
            user.email = form["email"]
            user.phone = form["phone"] or None
            db.session.commit()
            flash("Dane konta zostały zapisane.", "success")
            return redirect(url_for("users.admin_list"))
    return render_template("admin/user_form.html", form=form, errors=errors, user=user)


@bp.post("/admin/users/<int:user_id>/toggle")
@admin_required
def toggle(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.is_active and user.role == "admin" and _active_admin_count() <= 1:
        flash("Nie można dezaktywować ostatniego administratora.", "error")
        return redirect(url_for("users.admin_list"))
    user.is_active = not user.is_active
    db.session.commit()
    if g.user.id == user.id and not user.is_active:
        session.pop("user_id", None)
        session.pop("role", None)
        flash("Twoje konto zostało dezaktywowane.", "success")
        return redirect(url_for("auth.home"))
    flash("Status konta został zmieniony.", "success")
    return redirect(url_for("users.admin_list"))


def _profile_errors(user, form):
    errors = []
    if not form["first_name"] or len(form["first_name"]) > 100:
        errors.append("Podaj imię.")
    if not form["last_name"] or len(form["last_name"]) > 100:
        errors.append("Podaj nazwisko.")
    if not _valid_email(form["email"]):
        errors.append("Podaj poprawny adres e-mail.")
    else:
        taken = db.session.scalar(
            db.select(User.id).where(User.email == form["email"], User.id != user.id)
        )
        if taken is not None:
            errors.append("Ten adres e-mail jest już używany.")
    if form["phone"] and (len(form["phone"]) > 20 or not _valid_phone(form["phone"])):
        errors.append("Podaj telefon składający się z cyfr, spacji, plusa lub myślnika.")
    return errors


def _active_admin_count():
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(User)
        .where(User.role == "admin", User.is_active.is_(True))
    )
