from functools import wraps

from flask import flash, g, redirect, request, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Zaloguj się, aby kontynuować.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Zaloguj się, aby kontynuować.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if g.user.role != "admin":
            flash("Brak uprawnień do tej strony.", "error")
            return redirect(url_for("auth.home"))
        return view(*args, **kwargs)

    return wrapped


def patient_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Zaloguj się, aby kontynuować.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if g.user.role != "patient":
            flash("Rezerwacja wizyty jest dostępna dla pacjenta.", "error")
            return redirect(url_for("auth.home"))
        return view(*args, **kwargs)

    return wrapped
