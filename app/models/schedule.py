from app.extensions import db


class DentistSchedule(db.Model):
    __tablename__ = "dentist_schedules"

    id = db.Column(db.Integer, primary_key=True)
    dentist_id = db.Column(db.Integer, db.ForeignKey("dentists.id"), nullable=False)
    weekday = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    dentist = db.relationship("Dentist", back_populates="schedules")
