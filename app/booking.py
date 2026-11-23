from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import NoResultFound

from app.extensions import db
from app.models import Appointment, Dentist, DentistSchedule, Room, Treatment, User
from app.scheduling import (
    is_on_grid,
    person_busy,
    room_ids_free,
    within_working_window,
)


def reserve_appointment(
    *,
    patient_id,
    treatment_id,
    dentist_id,
    start,
    room_id=None,
    ignore_id=None,
    status="scheduled",
    allow_past=False,
    actor_role="patient",
):
    if status not in {"scheduled", "completed", "cancelled"}:
        return ["Nieprawidłowy status wizyty."], None

    grid = current_app.config["SLOT_MINUTES"]
    clinic_open = current_app.config["CLINIC_OPEN"]
    clinic_close = current_app.config["CLINIC_CLOSE"]

    if not isinstance(start, datetime) or not is_on_grid(start, grid):
        return ["Godzina musi wypadać co 30 minut."], None
    if not allow_past and start <= datetime.now():
        return ["Termin musi być w przyszłości."], None

    try:
        patient = db.session.scalars(
            db.select(User).where(User.id == patient_id).with_for_update()
        ).one()
        dentist = db.session.scalars(
            db.select(Dentist).where(Dentist.id == dentist_id).with_for_update()
        ).one()
        rooms = list(
            db.session.scalars(
                db.select(Room)
                .where(Room.is_active.is_(True))
                .order_by(Room.id)
                .with_for_update()
            )
        )
    except NoResultFound:
        db.session.rollback()
        return ["Nie znaleziono danych potrzebnych do zapisu wizyty."], None

    treatment = db.session.get(Treatment, treatment_id)
    errors = _entity_errors(patient, treatment, dentist)
    if errors:
        db.session.rollback()
        return errors, None

    end = start + timedelta(minutes=treatment.duration_minutes)
    schedules = list(
        db.session.scalars(
            db.select(DentistSchedule).where(
                DentistSchedule.dentist_id == dentist.id,
                DentistSchedule.weekday == start.weekday(),
            )
        )
    )
    if not within_working_window(start, end, schedules, clinic_open, clinic_close):
        db.session.rollback()
        return ["Termin nie mieści się w grafiku dentysty i godzinach kliniki 08:00–20:00."], None

    blocking = Appointment.overlapping(start, end, ignore_id=ignore_id, lock=True)
    if person_busy(start, end, dentist.id, blocking, "dentist_id", ignore_id):
        db.session.rollback()
        return ["Wybrany dentysta jest już zajęty w tym terminie."], None

    if person_busy(start, end, patient.id, blocking, "patient_id", ignore_id):
        db.session.rollback()
        if actor_role == "patient":
            return ["Masz już inną wizytę w tym terminie."], None
        return ["Pacjent ma już inną wizytę w tym terminie."], None

    free_rooms = room_ids_free(start, end, rooms, blocking, ignore_id)
    if room_id is None:
        if not free_rooms:
            db.session.rollback()
            return ["W tym terminie nie ma wolnego gabinetu."], None
        room_id = min(free_rooms)
    elif room_id not in free_rooms:
        db.session.rollback()
        return ["Wybrany gabinet jest zajęty w tym terminie."], None

    if ignore_id is None:
        appointment = Appointment(created_at=datetime.now())
        db.session.add(appointment)
    else:
        appointment = db.session.get(Appointment, ignore_id)
        if appointment is None:
            db.session.rollback()
            return ["Nie znaleziono wizyty."], None

    appointment.patient_id = patient.id
    appointment.dentist_id = dentist.id
    appointment.treatment_id = treatment.id
    appointment.room_id = room_id
    appointment.starts_at = start
    appointment.ends_at = end
    appointment.duration_minutes = treatment.duration_minutes
    appointment.price = treatment.price
    appointment.status = status
    db.session.commit()
    return [], appointment


def _entity_errors(patient, treatment, dentist):
    errors = []
    if patient is None or patient.role != "patient" or not patient.is_active:
        errors.append("Nieprawidłowy pacjent.")
    if treatment is None or not treatment.is_active:
        errors.append("Wybierz aktywny zabieg.")
    if dentist is None or not dentist.is_active:
        errors.append("Wybierz aktywnego dentystę.")
    if treatment is not None and dentist is not None:
        qualified = {item.id for item in dentist.treatments}
        if treatment.id not in qualified:
            errors.append("Ten dentysta nie ma uprawnienia do wybranego zabiegu.")
    return errors
