from datetime import date, datetime, time, timedelta


def as_time(value):
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return time(total // 3600, (total % 3600) // 60)
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    raise TypeError(f"Nieobsługiwany typ czasu: {type(value)!r}")


def intervals_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def is_on_grid(value, grid_minutes):
    clock = as_time(value)
    return (clock.hour * 60 + clock.minute) % grid_minutes == 0


def parse_clock(raw):
    text = (raw or "").strip()
    if text == "":
        return "empty", None
    for pattern in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, pattern).time()
        except ValueError:
            continue
        return "ok", parsed.replace(second=0, microsecond=0)
    return "invalid", None


def validate_schedule_intervals(intervals, clinic_open, clinic_close, grid_minutes):
    errors = []
    by_day = {}
    for weekday, start, end in intervals:
        if weekday < 0 or weekday > 6:
            errors.append("Nieprawidłowy dzień tygodnia.")
            continue
        if start is None or end is None:
            errors.append("Podaj godzinę rozpoczęcia i zakończenia przedziału.")
            continue
        if not is_on_grid(start, grid_minutes) or not is_on_grid(end, grid_minutes):
            errors.append("Godziny grafiku muszą wypadać co 30 minut.")
        if start < clinic_open or end > clinic_close:
            errors.append("Grafik musi mieścić się w godzinach kliniki 08:00–20:00.")
        if start >= end:
            errors.append("Godzina rozpoczęcia musi być wcześniejsza niż zakończenia.")
        by_day.setdefault(weekday, []).append((start, end))

    for spans in by_day.values():
        ordered = sorted(spans)
        overlapped = False
        for index, current in enumerate(ordered):
            for other in ordered[index + 1 :]:
                if intervals_overlap(
                    datetime.combine(date.min, current[0]),
                    datetime.combine(date.min, current[1]),
                    datetime.combine(date.min, other[0]),
                    datetime.combine(date.min, other[1]),
                ):
                    overlapped = True
        if overlapped:
            errors.append("Przedziały grafiku tego samego dnia nie mogą na siebie nachodzić.")

    unique = []
    for error in errors:
        if error not in unique:
            unique.append(error)
    return unique


def candidate_starts(day, schedule_rows, duration_minutes, grid_minutes, clinic_open, clinic_close, now):
    duration = timedelta(minutes=duration_minutes)
    grid = timedelta(minutes=grid_minutes)
    clinic_start = datetime.combine(day, clinic_open)
    clinic_end = datetime.combine(day, clinic_close)
    starts = []
    seen = set()
    for row in schedule_rows:
        if row.weekday != day.weekday():
            continue
        window_start = max(datetime.combine(day, as_time(row.start_time)), clinic_start)
        window_end = min(datetime.combine(day, as_time(row.end_time)), clinic_end)
        cursor = window_start
        while cursor + duration <= window_end:
            if cursor > now and cursor not in seen and is_on_grid(cursor, grid_minutes):
                starts.append(cursor)
                seen.add(cursor)
            cursor += grid
    starts.sort()
    return starts


def within_working_window(start, end, schedule_rows, clinic_open, clinic_close):
    if start.date() != end.date():
        return False
    if start.time() < clinic_open or end.time() > clinic_close:
        return False
    for row in schedule_rows:
        if row.weekday != start.weekday():
            continue
        if start.time() >= as_time(row.start_time) and end.time() <= as_time(row.end_time):
            return True
    return False


def _kept(appointment, ignore_id):
    if ignore_id is not None and appointment.id == ignore_id:
        return False
    return appointment.status != "cancelled"


def person_busy(start, end, person_id, appointments, attribute, ignore_id=None):
    for appointment in appointments:
        if not _kept(appointment, ignore_id):
            continue
        if getattr(appointment, attribute) != person_id:
            continue
        if intervals_overlap(start, end, appointment.starts_at, appointment.ends_at):
            return True
    return False


def room_ids_free(start, end, rooms, appointments, ignore_id=None):
    free = []
    for room in rooms:
        if not room.is_active:
            continue
        busy = False
        for appointment in appointments:
            if not _kept(appointment, ignore_id):
                continue
            if appointment.room_id != room.id:
                continue
            if intervals_overlap(start, end, appointment.starts_at, appointment.ends_at):
                busy = True
                break
        if not busy:
            free.append(room.id)
    return free


def available_slots(starts, duration_minutes, dentist_id, patient_id, rooms, appointments, ignore_id=None):
    duration = timedelta(minutes=duration_minutes)
    slots = []
    for start in starts:
        end = start + duration
        if person_busy(start, end, dentist_id, appointments, "dentist_id", ignore_id):
            continue
        if patient_id is not None and person_busy(
            start, end, patient_id, appointments, "patient_id", ignore_id
        ):
            continue
        free_rooms = room_ids_free(start, end, rooms, appointments, ignore_id)
        if not free_rooms:
            continue
        slots.append({"start": start, "room_ids": free_rooms})
    return slots
