from app.extensions import db
from app.models.associations import dentist_treatments


class Dentist(db.Model):
    __tablename__ = "dentists"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    treatments = db.relationship(
        "Treatment",
        secondary=dentist_treatments,
        back_populates="dentists",
    )
    schedules = db.relationship(
        "DentistSchedule",
        back_populates="dentist",
        cascade="all, delete-orphan",
    )
    appointments = db.relationship("Appointment", back_populates="dentist")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
