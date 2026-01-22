"""Application factory pattern."""

from flask import Flask
from pathlib import Path
from app.config import config
from app.extensions import db, migrate, login_manager


def create_app(config_name='default'):
    """Create and configure the Flask application."""
    
    # Project root
    root_dir = Path(__file__).parent.parent
    template_dir = root_dir / 'templates'
    static_dir = root_dir / 'static'

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )

    app.config.from_object(config[config_name])

    # --------------------
    # Extensions
    # --------------------
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # --------------------
    # Blueprints
    # --------------------

    # Public pages
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Authentication
    from app.auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp)

    # Dashboards (role-based)
    from app.dashboard import init_app as init_dashboard
    init_dashboard(app)

    # Settings
    from app.settings import bp as settings_bp
    app.register_blueprint(settings_bp)

    # Documents
    from app.blueprints.documents import bp as documents_bp
    app.register_blueprint(documents_bp)

    # --------------------
    # Return app
    # --------------------
    return app

