"""Flask extensions initialization."""

# Database extensions (commented out for now - will be enabled soon)
# from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
from flask_login import LoginManager

# Initialize extensions
# db = SQLAlchemy()
# migrate = Migrate()
login_manager = LoginManager()
