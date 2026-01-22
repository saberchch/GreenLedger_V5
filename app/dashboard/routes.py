"""Dashboard routes."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


from flask import redirect, url_for

@bp.route('/')
@login_required
def index():
    """Redirect to specific role dashboard."""
    if current_user.has_role('admin'):
        return redirect(url_for('dashboard_admin.admin_index'))
    elif current_user.has_role('auditor'):
        return redirect(url_for('dashboard_auditor.auditor_index'))
    elif current_user.has_role('org_admin'):
        return redirect(url_for('dashboard_org_admin.org_admin_index'))
    elif current_user.has_role('worker'):
        return redirect(url_for('dashboard_worker.worker_index'))
    else:
        # Default to viewer for anyone else
        return redirect(url_for('dashboard_viewer.viewer_index'))
