from app.extensions import db
from app.models.associations import dentist_treatments


class Treatment(db.Model):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2))
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    dentists = db.relationship(
        "Dentist",
        secondary=dentist_treatments,
        back_populates="treatments",
    )
    appointments = db.relationship("Appointment", back_populates="treatment")
