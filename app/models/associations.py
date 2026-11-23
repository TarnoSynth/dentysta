from app.extensions import db

dentist_treatments = db.Table(
    "dentist_treatments",
    db.Column("dentist_id", db.Integer, db.ForeignKey("dentists.id"), primary_key=True),
    db.Column("treatment_id", db.Integer, db.ForeignKey("treatments.id"), primary_key=True),
)
