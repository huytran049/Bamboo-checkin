"""
Routes package. Registers all blueprints with the Flask app.
"""


def register_blueprints(app):
    from routes.pages import bp as pages_bp
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.registration import bp as registration_bp
    from routes.face import bp as face_bp
    from routes.card import bp as card_bp
    from routes.ocr import bp as ocr_bp
    from routes.cccd import bp as cccd_bp
    from routes.qa import bp as qa_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(registration_bp)
    app.register_blueprint(face_bp)
    app.register_blueprint(card_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(cccd_bp)
    app.register_blueprint(qa_bp)
