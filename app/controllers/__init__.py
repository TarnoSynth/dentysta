def register_blueprints(app):
    from app.controllers.appointment_controller import bp as appointments_bp
    from app.controllers.auth_controller import bp as auth_bp
    from app.controllers.dentist_controller import bp as dentists_bp
    from app.controllers.treatment_controller import bp as treatments_bp
    from app.controllers.user_controller import bp as users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(treatments_bp)
    app.register_blueprint(dentists_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(users_bp)
