import os
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def main():
    reset_schema()
    from app import create_app
    from app.booking import reserve_appointment
    from app.extensions import db
    from app.models import Dentist, DentistSchedule, Room, Treatment, User

    app = create_app()
    with app.app_context():
        rooms = [
            Room(name="Gabinet 1"),
            Room(name="Gabinet 2"),
            Room(name="Gabinet 3"),
        ]
        db.session.add_all(rooms)

        admin = User(
            email="admin@klinika.local",
            password_hash=generate_password_hash("Admin12345"),
            first_name="Olga",
            last_name="Maj",
            phone="500100100",
            role="admin",
        )
        jan = User(
            email="jan@example.com",
            password_hash=generate_password_hash("Pacjent123"),
            first_name="Jan",
            last_name="Kowalski",
            phone="500100200",
            role="patient",
        )
        ewa = User(
            email="ewa@example.com",
            password_hash=generate_password_hash("Pacjent123"),
            first_name="Ewa",
            last_name="Lewandowska",
            phone="500100201",
            role="patient",
        )
        db.session.add_all([admin, jan, ewa])

        consultation = Treatment(
            name="Konsultacja",
            description="Ocena stanu uzębienia i planu leczenia.",
            duration_minutes=30,
            price=Decimal("100.00"),
        )
        review = Treatment(
            name="Przegląd",
            description="Kontrola jamy ustnej i higieny.",
            duration_minutes=30,
            price=Decimal("150.00"),
        )
        extraction = Treatment(
            name="Ekstrakcja",
            description="Usunięcie zęba w znieczuleniu miejscowym.",
            duration_minutes=60,
            price=Decimal("350.00"),
        )
        whitening = Treatment(
            name="Wybielanie",
            description="Wybielanie zębów. Cenę ustala lekarz na wizycie.",
            duration_minutes=90,
            price=None,
        )
        db.session.add_all([consultation, review, extraction, whitening])

        anna = Dentist(first_name="Anna", last_name="Nowak")
        piotr = Dentist(first_name="Piotr", last_name="Wiśniewski")
        maria = Dentist(first_name="Maria", last_name="Zielińska")
        anna.treatments = [consultation, review, extraction]
        piotr.treatments = [consultation, review, whitening]
        maria.treatments = [consultation, review]
        db.session.add_all([anna, piotr, maria])

        for dentist, start_hour, end_hour in (
            (anna, 8, 16),
            (piotr, 10, 18),
        ):
            for weekday in range(5):
                db.session.add(
                    DentistSchedule(
                        dentist=dentist,
                        weekday=weekday,
                        start_time=time(start_hour, 0),
                        end_time=time(end_hour, 0),
                    )
                )
        for weekday in (0, 2, 4):
            db.session.add(
                DentistSchedule(
                    dentist=maria,
                    weekday=weekday,
                    start_time=time(8, 0),
                    end_time=time(12, 0),
                )
            )
            db.session.add(
                DentistSchedule(
                    dentist=maria,
                    weekday=weekday,
                    start_time=time(14, 0),
                    end_time=time(18, 0),
                )
            )
        db.session.commit()

        today = datetime.now().date()
        past_monday = shift_weekday(today, 0, past=True)
        past_wednesday = shift_weekday(today, 2, past=True)
        next_monday = shift_weekday(today, 0, past=False)

        bookings = [
            {
                "patient": jan,
                "treatment": consultation,
                "dentist": anna,
                "start": datetime.combine(past_monday, time(9, 0)),
                "room_id": 1,
                "status": "completed",
                "allow_past": True,
            },
            {
                "patient": ewa,
                "treatment": consultation,
                "dentist": maria,
                "start": datetime.combine(past_wednesday, time(8, 30)),
                "room_id": 2,
                "status": "completed",
                "allow_past": True,
            },
            {
                "patient": jan,
                "treatment": extraction,
                "dentist": anna,
                "start": datetime.combine(next_monday, time(9, 0)),
                "room_id": 1,
                "status": "scheduled",
                "allow_past": False,
            },
            {
                "patient": ewa,
                "treatment": whitening,
                "dentist": piotr,
                "start": datetime.combine(next_monday, time(12, 0)),
                "room_id": 2,
                "status": "cancelled",
                "allow_past": False,
            },
        ]
        for item in bookings:
            errors, _appointment = reserve_appointment(
                patient_id=item["patient"].id,
                treatment_id=item["treatment"].id,
                dentist_id=item["dentist"].id,
                start=item["start"],
                room_id=item["room_id"],
                status=item["status"],
                allow_past=item["allow_past"],
                actor_role="admin",
            )
            if errors:
                raise SystemExit("Nie udało się wstawić wizyty demo: " + " ".join(errors))

    print("Baza dental_clinic jest gotowa.")
    print("Administrator: admin@klinika.local / Admin12345")
    print("Pacjent: jan@example.com / Pacjent123")
    print("Pacjent: ewa@example.com / Pacjent123")


def shift_weekday(day, weekday, past):
    if past:
        delta = (day.weekday() - weekday) % 7
        if delta == 0:
            delta = 7
        return day - timedelta(days=delta)
    delta = (weekday - day.weekday()) % 7
    if delta == 0:
        delta = 7
    return day + timedelta(days=delta)


def reset_schema():
    connection = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
    )
    script = (ROOT / "schema.sql").read_text(encoding="utf-8")
    try:
        with connection.cursor() as cursor:
            for statement in sql_statements(script):
                cursor.execute(statement)
    finally:
        connection.close()


def sql_statements(script):
    buffer = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()[:-1].strip()
            buffer = []
            if statement:
                yield statement


if __name__ == "__main__":
    try:
        main()
    except pymysql.MySQLError as exc:
        raise SystemExit(f"Nie można połączyć się z MySQL: {exc}") from exc
