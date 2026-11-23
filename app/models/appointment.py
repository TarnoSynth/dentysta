from datetime import datetime

from app.extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    dentist_id = db.Column(db.Integer, db.ForeignKey("dentists.id"), nullable=False)
    treatment_id = db.Column(db.Integer, db.ForeignKey("treatments.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    patient = db.relationship("User", back_populates="appointments")
    dentist = db.relationship("Dentist", back_populates="appointments")
    treatment = db.relationship("Treatment", back_populates="appointments")
    room = db.relationship("Room", back_populates="appointments")

    @classmethod
    def overlapping(cls, start, end, ignore_id=None, lock=False):
        statement = db.select(cls).where(
            cls.status != "cancelled",
            cls.starts_at < end,
            cls.ends_at > start,
        )
        if ignore_id is not None:
            statement = statement.where(cls.id != ignore_id)
        if lock:
            statement = statement.with_for_update()
        return list(db.session.scalars(statement))
