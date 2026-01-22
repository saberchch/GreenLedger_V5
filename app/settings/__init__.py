"""Settings blueprint for user profile and preferences."""
from flask import Blueprint

bp = Blueprint('settings', __name__, url_prefix='/settings')

from app.settings import routes
