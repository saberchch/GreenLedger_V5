from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.emission_activity import EmissionActivity, ActivityStatus
from app.models.user import User, UserRole
from app.security.permissions import PermissionManager
from app.models.audit_log import AuditLog

bp = Blueprint(
    'dashboard_org_admin',
    __name__,
    url_prefix='/dashboard/org-admin'
)


@bp.route('/')
@login_required
def org_admin_index():
    """
    Organization Admin Dashboard - Enterprise Owner View
    """
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
         flash('Access denied.', 'error')
         return redirect(url_for('main.index'))

    # Organizational Data
    org_id = current_user.organization_id
    
    activities = EmissionActivity.query.filter_by(organization_id=org_id).order_by(EmissionActivity.created_at.desc()).all()
    users = User.query.filter_by(organization_id=org_id).all()
    
    # Calculate comprehensive KPIs
    validated_activities = [a for a in activities if a.co2e_result and a.status == ActivityStatus.VALIDATED]
    
    # Total emissions
    total_emissions = sum(a.co2e_result for a in validated_activities)
    
    # Scope breakdown
    from app.models.emission_activity import EmissionScope
    scope1_emissions = sum(a.co2e_result for a in validated_activities if a.scope == EmissionScope.SCOPE_1)
    scope2_emissions = sum(a.co2e_result for a in validated_activities if a.scope == EmissionScope.SCOPE_2)
    scope3_emissions = sum(a.co2e_result for a in validated_activities if a.scope == EmissionScope.SCOPE_3)
    
    # Pending validation count
    pending_validation = len([a for a in activities if a.status == ActivityStatus.SUBMITTED])
    
    # Get pending emissions for validation section
    pending_emissions = [a for a in activities if a.status == ActivityStatus.SUBMITTED][:10]
    
    # Mock trends (for MVP - replace with real calculation later)
    kpis = {
        'total_emissions': f"{total_emissions:,.0f}",
        'total_emissions_change': "-3.2%",
        'scope1': f"{scope1_emissions:,.0f}",
        'scope1_change': "-5%",
        'scope2': f"{scope2_emissions:,.0f}",
        'scope2_change': "+2%",
        'scope3': f"{scope3_emissions:,.0f}",
        'scope3_change': "-1%",
        'pending_validation': pending_validation,
        'user_count': len(users),
        'completeness': "87%"
    }
    
    # Mock alerts for Action Center
    alerts = [
        {"type": "fact_check", "color": "blue", "title": f"{pending_validation} emissions pending", "subtitle": "Awaiting your validation"},
        {"type": "group", "color": "green", "title": f"{len(users)} active users", "subtitle": "In your organization"},
        {"type": "description", "color": "amber", "title": "Monthly report due", "subtitle": "Due in 5 days"}
    ]
    
    return render_template(
        'pages/dashboard/org_admin/index.html',
        user=current_user,
        organization=current_user.organization,
        recent_activities=activities[:10],
        pending_emissions=pending_emissions,
        users=users,
        kpis=kpis,
        alerts=alerts
    )

# Org Admin can also validate reports from their workers
@bp.route('/emission/<int:id>/approve', methods=['POST'])
@login_required
def approve_emission(id):
    activity = EmissionActivity.query.get_or_404(id)
    
    if not PermissionManager.can_validate_activity(current_user, activity):
        flash('Permission denied.', 'error')
        return redirect(url_for('dashboard_org_admin.org_admin_index'))
        
    activity.status = ActivityStatus.VALIDATED
    
    log = AuditLog(
        actor_id=current_user.id,
        organization_id=activity.organization_id,
        action="APPROVE_EMISSION",
        entity_type="EmissionActivity",
        entity_id=activity.id,
        details=f"Org Admin approved emission {activity.id}."
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Emission {activity.id} approved.', 'success')
    return redirect(url_for('dashboard_org_admin.org_admin_index'))

@bp.route('/emission/<int:id>/reject', methods=['POST'])
@login_required
def reject_emission(id):
    activity = EmissionActivity.query.get_or_404(id)
    
    if not PermissionManager.can_validate_activity(current_user, activity):
        flash('Permission denied.', 'error')
        return redirect(url_for('dashboard_org_admin.org_admin_index'))
        
    activity.status = ActivityStatus.REJECTED
    
    log = AuditLog(
        actor_id=current_user.id,
        organization_id=activity.organization_id,
        action="REJECT_EMISSION",
        entity_type="EmissionActivity",
        entity_id=activity.id,
        details=f"Org Admin rejected emission {activity.id}."
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Emission {activity.id} rejected.', 'info')
    return redirect(url_for('dashboard_org_admin.org_admin_index'))

# ============================================
# ADDITIONAL ORG ADMIN ROUTES
# ============================================

@bp.route('/users')
@login_required
def users():
    """Users & Roles management page."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    users = User.query.filter_by(organization_id=current_user.organization_id).all()
    return render_template('pages/dashboard/org_admin/users.html', users=users)

@bp.route('/documents')
@login_required
def documents():
    """Documents viewing page."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    from app.models.document import Document
    docs = Document.query.filter_by(organization_id=current_user.organization_id).order_by(Document.created_at.desc()).all()
    return render_template('pages/dashboard/org_admin/documents.html', documents=docs)

@bp.route('/reports')
@login_required
def reports():
    """Reports generation page."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('pages/dashboard/org_admin/reports.html')

@bp.route('/settings')
@login_required
def settings():
    """Organization settings page."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('pages/dashboard/org_admin/settings.html', organization=current_user.organization)

@bp.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate carbon report (placeholder)."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.org_admin_index'))
    
    flash('Report generation feature coming soon!', 'info')
    return redirect(url_for('dashboard_org_admin.reports'))

@bp.route('/users/invite', methods=['POST'])
@login_required
def invite_user():
    """Invite user (placeholder)."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.org_admin_index'))
    
    flash('User invitation feature coming soon!', 'info')
    return redirect(url_for('dashboard_org_admin.users'))

