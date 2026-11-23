from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.decorators import admin_required, login_required
from app.extensions import db
from app.models import Treatment

bp = Blueprint("treatments", __name__)


@bp.get("/treatments")
@login_required
def catalog():
    treatments = db.session.scalars(
        db.select(Treatment).where(Treatment.is_active.is_(True)).order_by(Treatment.name)
    ).all()
    return render_template("treatments/list.html", treatments=treatments, manage=False)


@bp.get("/admin/treatments")
@admin_required
def admin_list():
    treatments = db.session.scalars(db.select(Treatment).order_by(Treatment.name)).all()
    return render_template("treatments/list.html", treatments=treatments, manage=True)


@bp.route("/admin/treatments/new", methods=["GET", "POST"])
@admin_required
def create():
    return _save_treatment(None)


@bp.route("/admin/treatments/<int:treatment_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(treatment_id):
    treatment = db.session.get(Treatment, treatment_id)
    if treatment is None:
        abort(404)
    return _save_treatment(treatment)


@bp.post("/admin/treatments/<int:treatment_id>/toggle")
@admin_required
def toggle(treatment_id):
    treatment = db.session.get(Treatment, treatment_id)
    if treatment is None:
        abort(404)
    treatment.is_active = not treatment.is_active
    db.session.commit()
    flash("Status zabiegu został zmieniony.", "success")
    return redirect(url_for("treatments.admin_list"))


def _save_treatment(treatment):
    form = _form_from_treatment(treatment)
    errors = []
    if request.method == "POST":
        form = {
            "name": request.form.get("name", "").strip(),
            "description": request.form.get("description", "").strip(),
            "duration_minutes": request.form.get("duration_minutes", "").strip(),
            "price": request.form.get("price", "").strip(),
            "is_active": request.form.get("is_active") == "1",
        }
        parsed, errors = _parse_treatment(form)
        if not errors:
            if treatment is None:
                treatment = Treatment()
                db.session.add(treatment)
            treatment.name = parsed["name"]
            treatment.description = parsed["description"]
            treatment.duration_minutes = parsed["duration_minutes"]
            treatment.price = parsed["price"]
            treatment.is_active = parsed["is_active"]
            db.session.commit()
            flash("Zabieg został zapisany.", "success")
            return redirect(url_for("treatments.admin_list"))

    return render_template(
        "treatments/form.html",
        form=form,
        errors=errors,
        treatment=treatment,
    )


def _form_from_treatment(treatment):
    if treatment is None:
        return {
            "name": "",
            "description": "",
            "duration_minutes": "30",
            "price": "",
            "is_active": True,
        }
    price = ""
    if treatment.price is not None:
        price = f"{treatment.price:.2f}"
    return {
        "name": treatment.name,
        "description": treatment.description or "",
        "duration_minutes": str(treatment.duration_minutes),
        "price": price,
        "is_active": treatment.is_active,
    }


def _parse_treatment(form):
    errors = []
    if not form["name"] or len(form["name"]) > 150:
        errors.append("Podaj nazwę zabiegu, maksymalnie 150 znaków.")
    if len(form["description"]) > 2000:
        errors.append("Opis może mieć najwyżej 2000 znaków.")

    try:
        duration = int(form["duration_minutes"])
    except ValueError:
        duration = None
        errors.append("Czas trwania podaj jako liczbę minut.")
    if duration is not None and (duration < 30 or duration > 240 or duration % 30 != 0):
        errors.append("Czas trwania musi być wielokrotnością 30 minut, od 30 do 240.")

    price, price_error = _parse_price(form["price"])
    if price_error:
        errors.append(price_error)

    if errors:
        return None, errors
    return {
        "name": form["name"],
        "description": form["description"] or None,
        "duration_minutes": duration,
        "price": price,
        "is_active": form["is_active"],
    }, []


def _parse_price(raw):
    text = raw.strip().replace(",", ".")
    if text == "":
        return None, None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None, "Podaj cenę w złotych albo zostaw puste pole."
    if value < 0 or value >= Decimal("1000000"):
        return None, "Cena musi być liczbą nieujemną."
    return value.quantize(Decimal("0.01")), None
