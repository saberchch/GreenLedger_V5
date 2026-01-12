"""Application factory pattern."""

from flask import Flask
from pathlib import Path
from app.config import config
from app.extensions import login_manager
# Database extensions (commented out for now - will be enabled soon)
# from app.extensions import db, migrate


def create_app(config_name='default'):
    """Create and configure the Flask application."""
    # Get the root directory (parent of app directory)
    root_dir = Path(__file__).parent.parent
    template_dir = root_dir / 'templates'
    static_dir = root_dir / 'static'
    
    app = Flask(__name__, 
                template_folder=str(template_dir),
                static_folder=str(static_dir))
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    # Database (commented out for now - will be enabled soon)
    # db.init_app(app)
    # migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Minimal user_loader (will be implemented when auth is added)
    @login_manager.user_loader
    def load_user(user_id):
        # Return None for now - will be implemented with actual user model later
        return None
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    # from app.dashboard import bp as dashboard_bp
    # app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    # Add more blueprint registrations as modules are created
    
    return app
