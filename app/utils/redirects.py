from flask import redirect, url_for


from app.models.user import UserRole

def redirect_to_dashboard(user):
    if user.role == UserRole.PLATFORM_ADMIN:
        return redirect(url_for('dashboard_admin.admin_index'))
    
    if user.role == UserRole.ORG_ADMIN:
        return redirect(url_for('dashboard_org_admin.org_admin_index'))

    if user.role == UserRole.AUDITOR:
        return redirect(url_for('dashboard_auditor.auditor_index'))

    if user.role == UserRole.WORKER:
        return redirect(url_for('dashboard_worker.worker_index'))

    return redirect(url_for('dashboard_viewer.viewer_index'))
