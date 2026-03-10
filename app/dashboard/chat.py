from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

bp = Blueprint('dashboard_chat', __name__, url_prefix='/dashboard/chat')


@bp.route('/')
@login_required
def team_chat():
    """Organization team chat page — accessible only to internal org members."""
    if not current_user.organization_id:
        flash('You must belong to an organization to access Team Chat.', 'error')
        return redirect(url_for('main.index'))

    # Auditors are read-only (they can view but cannot access the standalone chat)
    if current_user.role.value == 'auditor':
        flash('Auditors do not have access to the Team Chat.', 'error')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    org = current_user.organization
    return render_template(
        'pages/dashboard/team_chat.html',
        org=org,
        user=current_user
    )

