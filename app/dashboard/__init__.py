from .routes import bp as dashboard_bp
from .admin import bp as admin_bp
from .auditor import bp as auditor_bp
from .worker import bp as worker_bp
from .viewer import bp as viewer_bp
from .org_admin import bp as org_admin_bp
from .notifications import bp as notifications_bp
from .chat import bp as chat_bp
from .secure_messages import bp as messages_bp


def init_app(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auditor_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(org_admin_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(messages_bp)

