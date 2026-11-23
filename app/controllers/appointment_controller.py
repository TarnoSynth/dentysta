from datetime import datetime, timedelta

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.orm import selectinload

from app.booking import reserve_appointment
from app.decorators import admin_required, login_required, patient_required
from app.extensions import db
from app.labels import STATUSES
from app.models import Appointment, Dentist, Room, Treatment, User
from app.scheduling import (
    available_slots,
    candidate_starts,
    is_on_grid,
    parse_clock,
    person_busy,
    room_ids_free,
)

bp = Blueprint("appointments", __name__)


@bp.route("/appointments/new", methods=["GET", "POST"])
@patient_required
def book():
    if request.method == "POST":
        return _create_for_patient()
    treatment_id = request.args.get("treatment_id", type=int)
    return render_template(
        "appointments/book.html",
        errors=[],
        **_booking_view(treatment_id, "", "", ""),
    )


@bp.post("/appointments")
@patient_required
def create():
    return _create_for_patient()


@bp.get("/appointments")
@patient_required
def mine():
    now = datetime.now()
    rows = db.session.scalars(
        db.select(Appointment)
        .where(Appointment.patient_id == g.user.id)
        .options(
            selectinload(Appointment.dentist),
            selectinload(Appointment.treatment),
            selectinload(Appointment.room),
        )
        .order_by(Appointment.starts_at.desc())
    ).all()
    upcoming = [row for row in rows if row.status == "scheduled" and row.starts_at >= now]
    upcoming.sort(key=lambda row: row.starts_at)
    past = [row for row in rows if row not in upcoming]
    return render_template("appointments/my_list.html", upcoming=upcoming, past=past)


@bp.post("/appointments/<int:appointment_id>/cancel")
@patient_required
def cancel(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None or appointment.patient_id != g.user.id:
        abort(404)
    if appointment.status != "scheduled" or appointment.starts_at <= datetime.now():
        flash("Można odwołać tylko przyszłą, zaplanowaną wizytę.", "error")
        return redirect(url_for("appointments.mine"))
    appointment.status = "cancelled"
    db.session.commit()
    flash("Wizyta została odwołana.", "success")
    return redirect(url_for("appointments.mine"))


@bp.get("/admin/appointments")
@admin_required
def admin_list():
    day = _parse_date(request.args.get("date", ""))
    dentist_id = request.args.get("dentist_id", type=int)
    patient_id = request.args.get("patient_id", type=int)
    statement = db.select(Appointment).options(
        selectinload(Appointment.patient),
        selectinload(Appointment.dentist),
        selectinload(Appointment.treatment),
        selectinload(Appointment.room),
    )
    if day is not None:
        start = datetime.combine(day, datetime.min.time())
        statement = statement.where(
            Appointment.starts_at >= start,
            Appointment.starts_at < start + timedelta(days=1),
        )
    if dentist_id:
        statement = statement.where(Appointment.dentist_id == dentist_id)
    if patient_id:
        statement = statement.where(Appointment.patient_id == patient_id)
    statement = statement.order_by(Appointment.starts_at.desc())
    appointments = db.session.scalars(statement).all()
    return render_template(
        "admin/appointments.html",
        appointments=appointments,
        dentists=_all_dentists(),
        patients=_all_patients(),
        filters={
            "date": request.args.get("date", ""),
            "dentist_id": dentist_id or "",
            "patient_id": patient_id or "",
        },
    )


@bp.route("/admin/appointments/<int:appointment_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit(appointment_id):
    appointment = db.session.scalar(
        db.select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.dentist),
            selectinload(Appointment.treatment),
            selectinload(Appointment.room),
        )
    )
    if appointment is None:
        abort(404)

    errors = []
    if request.method == "POST":
        action = request.form.get("action")
        if action == "status":
            errors = _update_status(appointment)
            if not errors:
                flash("Status wizyty został zapisany.", "success")
                return redirect(url_for("appointments.admin_list"))
        elif action == "reschedule":
            errors = _reschedule(appointment)
            if not errors:
                flash("Termin wizyty został zmieniony.", "success")
                return redirect(url_for("appointments.admin_list"))
        else:
            errors = ["Nieznana operacja."]

    return render_template(
        "admin/appointment_form.html",
        appointment=appointment,
        errors=errors,
        **_booking_view(
            appointment.treatment_id,
            str(appointment.dentist_id),
            appointment.starts_at.strftime("%Y-%m-%d"),
            appointment.starts_at.strftime("%H:%M"),
            patient_id=appointment.patient_id,
            ignore_id=appointment.id,
            room_id=appointment.room_id,
        ),
    )


@bp.get("/api/dentists")
@login_required
def api_dentists():
    treatment = db.session.get(Treatment, request.args.get("treatment_id", type=int))
    if treatment is None or not treatment.is_active:
        return jsonify({"dentists": []})
    dentists = [item for item in treatment.dentists if item.is_active]
    dentists.sort(key=lambda item: (item.last_name, item.first_name))
    return jsonify({"dentists": [{"id": item.id, "name": item.full_name} for item in dentists]})


@bp.get("/api/slots")
@login_required
def api_slots():
    treatment = db.session.get(Treatment, request.args.get("treatment_id", type=int))
    dentist = db.session.get(Dentist, request.args.get("dentist_id", type=int))
    day = _parse_date(request.args.get("date", ""))
    if treatment is None or dentist is None or day is None or not treatment.is_active or not dentist.is_active:
        return jsonify({"slots": []})

    ignore_id = None
    if g.user.role == "admin":
        ignore_id = request.args.get("ignore_id", type=int)
        patient_id = request.args.get("patient_id", type=int)
        if patient_id is None:
            return jsonify({"error": "Brakuje identyfikatora pacjenta."}), 400
    else:
        patient_id = g.user.id

    slots = _slots_for(treatment, dentist, day, patient_id, ignore_id)
    return jsonify(
        {
            "slots": [
                {
                    "start": slot["start"].strftime("%H:%M"),
                    "rooms": slot["rooms"],
                }
                for slot in slots
            ]
        }
    )


def _create_for_patient():
    treatment_id = request.form.get("treatment_id", type=int)
    dentist_id = request.form.get("dentist_id", type=int)
    visit_date = request.form.get("visit_date", "")
    start_time = request.form.get("start_time", "")
    errors = []
    if not treatment_id or not dentist_id:
        errors.append("Wybierz zabieg i dentystę.")
    start, error = _combine_start(visit_date, start_time)
    if error:
        errors.append(error)
    if not errors:
        errors, _appointment = reserve_appointment(
            patient_id=g.user.id,
            treatment_id=treatment_id,
            dentist_id=dentist_id,
            start=start,
            room_id=None,
            actor_role="patient",
        )
        if not errors:
            flash("Wizyta została zarezerwowana. Gabinet został przypisany automatycznie.", "success")
            return redirect(url_for("appointments.mine"))

    return render_template(
        "appointments/book.html",
        errors=errors,
        **_booking_view(treatment_id, str(dentist_id or ""), visit_date, start_time),
    )


def _reschedule(appointment):
    treatment_id = request.form.get("treatment_id", type=int)
    dentist_id = request.form.get("dentist_id", type=int)
    room_id = request.form.get("room_id", type=int)
    if not treatment_id or not dentist_id:
        return ["Wybierz zabieg i dentystę."]
    start, error = _combine_start(
        request.form.get("visit_date", ""),
        request.form.get("start_time", ""),
    )
    if error:
        return [error]
    if room_id is None:
        return ["Wybierz gabinet."]
    errors, _appointment = reserve_appointment(
        patient_id=appointment.patient_id,
        treatment_id=treatment_id,
        dentist_id=dentist_id,
        start=start,
        room_id=room_id,
        ignore_id=appointment.id,
        status="scheduled",
        actor_role="admin",
    )
    return errors


def _update_status(appointment):
    new_status = request.form.get("status", "")
    if new_status not in STATUSES:
        return ["Wybierz status wizyty."]
    if new_status == appointment.status:
        return []
    if new_status == "cancelled":
        appointment.status = "cancelled"
        db.session.commit()
        return []
    if appointment.status == "cancelled":
        return _restore(appointment, new_status)
    appointment.status = new_status
    db.session.commit()
    return []


def _restore(appointment, new_status):
    if new_status == "scheduled" and appointment.starts_at <= datetime.now():
        return ["Nie można przywrócić przeszłej wizyty jako zaplanowanej."]
    end = appointment.ends_at
    blocking = Appointment.overlapping(
        appointment.starts_at,
        end,
        ignore_id=appointment.id,
        lock=True,
    )
    if person_busy(appointment.starts_at, end, appointment.dentist_id, blocking, "dentist_id"):
        db.session.rollback()
        return ["Wybrany dentysta jest już zajęty w tym terminie."]
    if person_busy(appointment.starts_at, end, appointment.patient_id, blocking, "patient_id"):
        db.session.rollback()
        return ["Pacjent ma już inną wizytę w tym terminie."]
    rooms = list(db.session.scalars(db.select(Room).where(Room.is_active.is_(True))))
    if appointment.room_id not in room_ids_free(appointment.starts_at, end, rooms, blocking):
        db.session.rollback()
        return ["Wybrany gabinet jest zajęty w tym terminie."]
    appointment.status = new_status
    db.session.commit()
    return []


def _booking_view(
    treatment_id,
    dentist_id,
    visit_date,
    start_time,
    patient_id=None,
    ignore_id=None,
    room_id=None,
):
    treatments = _active_treatments()
    selected = next((item for item in treatments if item.id == treatment_id), None)
    dentists = []
    if selected is not None:
        dentists = [item for item in selected.dentists if item.is_active]
        dentists.sort(key=lambda item: (item.last_name, item.first_name))
    slots = []
    day = _parse_date(visit_date)
    dentist = next((item for item in dentists if str(item.id) == str(dentist_id)), None)
    owner_id = patient_id if patient_id is not None else (g.user.id if g.user and g.user.role == "patient" else None)
    if selected and dentist and day and owner_id:
        slots = _slots_for(selected, dentist, day, owner_id, ignore_id)
    return {
        "treatments": treatments,
        "dentists": dentists,
        "slots": slots,
        "selected": {
            "treatment_id": treatment_id or "",
            "dentist_id": dentist_id or "",
            "visit_date": visit_date,
            "start_time": start_time,
            "room_id": room_id or "",
            "patient_id": owner_id or "",
            "ignore_id": ignore_id or "",
        },
    }


def _slots_for(treatment, dentist, day, patient_id, ignore_id):
    schedules = list(dentist.schedules)
    now = datetime.now()
    starts = candidate_starts(
        day,
        schedules,
        treatment.duration_minutes,
        current_app.config["SLOT_MINUTES"],
        current_app.config["CLINIC_OPEN"],
        current_app.config["CLINIC_CLOSE"],
        now,
    )
    window_start = datetime.combine(day, current_app.config["CLINIC_OPEN"])
    window_end = datetime.combine(day, current_app.config["CLINIC_CLOSE"])
    blocking = Appointment.overlapping(window_start, window_end, ignore_id=ignore_id)
    rooms = list(
        db.session.scalars(db.select(Room).where(Room.is_active.is_(True)).order_by(Room.id))
    )
    room_names = {room.id: room.name for room in rooms}
    slots = available_slots(
        starts,
        treatment.duration_minutes,
        dentist.id,
        patient_id,
        rooms,
        blocking,
        ignore_id,
    )
    for slot in slots:
        slot["rooms"] = [{"id": room_id, "name": room_names[room_id]} for room_id in slot["room_ids"]]
    return slots


def _combine_start(date_raw, time_raw):
    day = _parse_date(date_raw)
    if day is None:
        return None, "Podaj poprawną datę."
    kind, clock = parse_clock(time_raw)
    if kind != "ok":
        return None, "Podaj poprawną godzinę."
    if not is_on_grid(clock, current_app.config["SLOT_MINUTES"]):
        return None, "Godzina musi wypadać co 30 minut."
    return datetime.combine(day, clock), None


def _parse_date(raw):
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _active_treatments():
    return list(
        db.session.scalars(
            db.select(Treatment).where(Treatment.is_active.is_(True)).order_by(Treatment.name)
        )
    )


def _all_dentists():
    return list(db.session.scalars(db.select(Dentist).order_by(Dentist.last_name, Dentist.first_name)))


def _all_patients():
    return list(
        db.session.scalars(
            db.select(User).where(User.role == "patient").order_by(User.last_name, User.first_name)
        )
    )
