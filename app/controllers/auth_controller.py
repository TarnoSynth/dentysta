from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__)


@bp.get("/")
def home():
    return render_template("home.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("auth.home"))

    form = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
    }
    errors = []
    if request.method == "POST":
        form = {
            "first_name": request.form.get("first_name", "").strip(),
            "last_name": request.form.get("last_name", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
            "phone": request.form.get("phone", "").strip(),
        }
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")
        errors = _registration_errors(form, password, confirm)
        if not errors:
            user = User(
                email=form["email"],
                password_hash=generate_password_hash(password),
                first_name=form["first_name"],
                last_name=form["last_name"],
                phone=form["phone"] or None,
                role="patient",
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()
            flash("Konto zostało utworzone. Możesz się zalogować.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form, errors=errors)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("auth.home"))

    email = ""
    errors = []
    next_url = _safe_next(request.args.get("next") or request.form.get("next"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user is None or not check_password_hash(user.password_hash, password):
            errors.append("Nieprawidłowy e-mail lub hasło.")
        elif not user.is_active:
            errors.append("Konto jest nieaktywne.")
        else:
            session["user_id"] = user.id
            session["role"] = user.role
            flash("Zalogowano.", "success")
            return redirect(next_url or url_for("auth.home"))

    return render_template("auth/login.html", email=email, errors=errors, next_url=next_url or "")


@bp.post("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("role", None)
    flash("Wylogowano.", "success")
    return redirect(url_for("auth.home"))


def _registration_errors(form, password, confirm):
    errors = []
    if not form["first_name"] or len(form["first_name"]) > 100:
        errors.append("Podaj imię.")
    if not form["last_name"] or len(form["last_name"]) > 100:
        errors.append("Podaj nazwisko.")
    if not _valid_email(form["email"]):
        errors.append("Podaj poprawny adres e-mail.")
    elif db.session.scalar(db.select(User.id).where(User.email == form["email"])) is not None:
        errors.append("Konto z tym adresem e-mail już istnieje.")
    if form["phone"] and (len(form["phone"]) > 20 or not _valid_phone(form["phone"])):
        errors.append("Podaj telefon składający się z cyfr, spacji, plusa lub myślnika.")
    if len(password) < 8 or len(password) > 128:
        errors.append("Hasło musi mieć od 8 do 128 znaków.")
    elif password != confirm:
        errors.append("Hasła nie są takie same.")
    return errors


def _valid_email(email):
    if len(email) > 255 or email.count("@") != 1:
        return False
    local, domain = email.split("@")
    return bool(local) and "." in domain and " " not in email


def _valid_phone(phone):
    allowed = set("0123456789 +-")
    return all(character in allowed for character in phone)


def _safe_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None
