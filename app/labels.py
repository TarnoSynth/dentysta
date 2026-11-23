from datetime import datetime, time, timedelta
from decimal import Decimal

WEEKDAYS = [
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
]

STATUS_LABELS = {
    "scheduled": "Zaplanowana",
    "completed": "Zakończona",
    "cancelled": "Odwołana",
}

ROLE_LABELS = {
    "patient": "Pacjent",
    "admin": "Administrator",
}

STATUSES = ("scheduled", "completed", "cancelled")


def format_price(value):
    if value is None:
        return "do ustalenia"
    if not isinstance(value, Decimal):
        value = Decimal(value)
    quantized = value.quantize(Decimal("0.01"))
    return f"{quantized:.2f}".replace(".", ",") + " zł"


def format_date(value):
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y")


def format_time(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)
