from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app.decorators import admin_required
from app.extensions import db
from app.labels import WEEKDAYS
from app.models import Dentist, DentistSchedule, Treatment
from app.scheduling import as_time, parse_clock, validate_schedule_intervals

bp = Blueprint("dentists", __name__)


@bp.get("/admin/dentists")
@admin_required
def admin_list():
    dentists = db.session.scalars(db.select(Dentist).order_by(Dentist.last_name, Dentist.first_name)).all()
    return render_template("dentists/list.html", dentists=dentists)


@bp.route("/admin/dentists/new", methods=["GET", "POST"])
@admin_required
def create():
    return _save_dentist(None)


@bp.route("/admin/dentists/<int:dentist_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(dentist_id):
    dentist = db.session.get(Dentist, dentist_id)
    if dentist is None:
        abort(404)
    return _save_dentist(dentist)


@bp.post("/admin/dentists/<int:dentist_id>/toggle")
@admin_required
def toggle(dentist_id):
    dentist = db.session.get(Dentist, dentist_id)
    if dentist is None:
        abort(404)
    dentist.is_active = not dentist.is_active
    db.session.commit()
    flash("Status dentysty został zmieniony.", "success")
    return redirect(url_for("dentists.admin_list"))


def _save_dentist(dentist):
    treatments = db.session.scalars(db.select(Treatment).order_by(Treatment.name)).all()
    form = _form_from_dentist(dentist, treatments)
    errors = []
    if request.method == "POST":
        form, parsed, errors = _parse_dentist_form(treatments)
        if not errors:
            if dentist is None:
                dentist = Dentist()
                db.session.add(dentist)
            dentist.first_name = parsed["first_name"]
            dentist.last_name = parsed["last_name"]
            dentist.is_active = parsed["is_active"]
            dentist.treatments = parsed["treatments"]
            dentist.schedules.clear()
            db.session.flush()
            for weekday, start, end in parsed["intervals"]:
                db.session.add(
                    DentistSchedule(
                        dentist=dentist,
                        weekday=weekday,
                        start_time=start,
                        end_time=end,
                    )
                )
            db.session.commit()
            flash("Dentysta został zapisany.", "success")
            return redirect(url_for("dentists.admin_list"))

    return render_template(
        "dentists/form.html",
        form=form,
        errors=errors,
        dentist=dentist,
        treatments=treatments,
        weekdays=WEEKDAYS,
    )


def _form_from_dentist(dentist, treatments):
    selected = set()
    intervals = {day: [("", ""), ("", "")] for day in range(7)}
    if dentist is not None:
        selected = {item.id for item in dentist.treatments}
        grouped = {day: [] for day in range(7)}
        for row in dentist.schedules:
            grouped[row.weekday].append(row)
        for day, rows in grouped.items():
            rows.sort(key=lambda row: as_time(row.start_time))
            for index, row in enumerate(rows[:2]):
                intervals[day][index] = (
                    as_time(row.start_time).strftime("%H:%M"),
                    as_time(row.end_time).strftime("%H:%M"),
                )
    return {
        "first_name": dentist.first_name if dentist else "",
        "last_name": dentist.last_name if dentist else "",
        "is_active": True if dentist is None else dentist.is_active,
        "treatment_ids": selected,
        "intervals": intervals,
        "known_treatment_ids": {item.id for item in treatments},
    }


def _parse_dentist_form(treatments):
    form = {
        "first_name": request.form.get("first_name", "").strip(),
        "last_name": request.form.get("last_name", "").strip(),
        "is_active": request.form.get("is_active") == "1",
        "treatment_ids": set(),
        "intervals": {day: [("", ""), ("", "")] for day in range(7)},
        "known_treatment_ids": {item.id for item in treatments},
    }
    errors = []
    if not form["first_name"] or len(form["first_name"]) > 100:
        errors.append("Podaj imię dentysty.")
    if not form["last_name"] or len(form["last_name"]) > 100:
        errors.append("Podaj nazwisko dentysty.")

    raw_ids = request.form.getlist("treatment_ids")
    try:
        selected_ids = {int(value) for value in raw_ids}
    except ValueError:
        selected_ids = set()
        errors.append("Nieprawidłowa lista zabiegów.")
    known = {item.id: item for item in treatments}
    if not selected_ids or not selected_ids <= set(known):
        errors.append("Wybierz co najmniej jeden zabieg, który dentysta może wykonywać.")
    form["treatment_ids"] = selected_ids

    intervals = []
    for day in range(7):
        for slot in (1, 2):
            start_raw = request.form.get(f"start_{day}_{slot}", "")
            end_raw = request.form.get(f"end_{day}_{slot}", "")
            form["intervals"][day][slot - 1] = (start_raw.strip(), end_raw.strip())
            start_kind, start = parse_clock(start_raw)
            end_kind, end = parse_clock(end_raw)
            if start_kind == "empty" and end_kind == "empty":
                continue
            if start_kind == "invalid" or end_kind == "invalid":
                errors.append("Godziny grafiku wpisz w formacie GG:MM.")
                continue
            if start_kind == "empty" or end_kind == "empty":
                errors.append("Podaj godzinę rozpoczęcia i zakończenia przedziału.")
                continue
            intervals.append((day, start, end))

    if not intervals:
        errors.append("Ustal co najmniej jeden dzień pracy.")

    errors.extend(
        validate_schedule_intervals(
            intervals,
            current_app.config["CLINIC_OPEN"],
            current_app.config["CLINIC_CLOSE"],
            current_app.config["SLOT_MINUTES"],
        )
    )
    unique = []
    for error in errors:
        if error not in unique:
            unique.append(error)
    if unique:
        return form, None, unique
    return form, {
        "first_name": form["first_name"],
        "last_name": form["last_name"],
        "is_active": form["is_active"],
        "treatments": [known[item_id] for item_id in sorted(selected_ids)],
        "intervals": intervals,
    }, []
