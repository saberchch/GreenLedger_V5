from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.report import Report, ReportStatus
from app.models.emission_activity import EmissionActivity, ActivityStatus
from app.models.audit_log import AuditLog
from app.security.permissions import PermissionManager
from datetime import datetime

bp = Blueprint(
    'dashboard_auditor',
    __name__,
    url_prefix='/dashboard/auditor'
)


@bp.route('/')
@login_required
def auditor_index():
    """
    Auditor dashboard
    """
    # Show pending audits (Validation Flow)
    query = EmissionActivity.query.filter_by(status=ActivityStatus.SUBMITTED)
    
    # Organization isolation
    if current_user.role.name == 'ORG_ADMIN': # Or check via PermissionManager
         query = query.filter_by(organization_id=current_user.organization_id)
    # If Auditor, seeing all assigned (mock: all pending)
    
    pending_activities = query.all()
    
    return render_template(
        'pages/dashboard/auditor/index.html',
        user=current_user,
        pending_activities=pending_activities,
        kpis={
            'pending_review': len(pending_activities),
            'approved_this_month': 0, # To be implemented
            'compliance_score': '98%' 
        }
    )

@bp.route('/audit/<int:id>/approve', methods=['POST'])
@login_required
def approve_emission(id):
    activity = EmissionActivity.query.get_or_404(id)
    
    if not PermissionManager.can_validate_activity(current_user, activity):
        flash('Permission denied: You cannot validate this activity.', 'error')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    activity.status = ActivityStatus.VALIDATED
    
    # Audit Log
    log = AuditLog(
        actor_id=current_user.id,
        organization_id=activity.organization_id,
        action="APPROVE_EMISSION",
        entity_type="EmissionActivity",
        entity_id=activity.id,
        details=f"Approved emission {activity.id}."
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Emission ID {activity.id} approved.', 'success')
    return redirect(url_for('dashboard_auditor.auditor_index'))

@bp.route('/audit/<int:id>/reject', methods=['POST'])
@login_required
def reject_emission(id):
    activity = EmissionActivity.query.get_or_404(id)
    
    if not PermissionManager.can_validate_activity(current_user, activity):
        flash('Permission denied.', 'error')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    activity.status = ActivityStatus.REJECTED
    
    # Audit Log
    log = AuditLog(
        actor_id=current_user.id,
        organization_id=activity.organization_id,
        action="REJECT_EMISSION",
        entity_type="EmissionActivity",
        entity_id=activity.id,
        details=f"Rejected emission {activity.id}."
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Emission ID {activity.id} rejected.', 'info')
    return redirect(url_for('dashboard_auditor.auditor_index'))

@bp.route('/report/<int:report_id>/sign', methods=['POST'])
@login_required
def sign_report(report_id):
    report = Report.query.get_or_404(report_id)
    
    # Validation logic here
    
    report.status = ReportStatus.AUDITED
    report.auditor_id = current_user.id
    db.session.commit()
    
    flash(f'Report #{report.id} signed and approved.', 'success')
    return redirect(url_for('dashboard_auditor.auditor_index'))

@bp.route('/history')
@login_required
def audit_history():
    return render_template('pages/dashboard/coming_soon.html', user=current_user)

@bp.route('/standards')
@login_required
def compliance_standards():
    return render_template('pages/dashboard/coming_soon.html', user=current_user)

@bp.route('/reports')
@login_required
def reporting_tools():
    return render_template('pages/dashboard/coming_soon.html', user=current_user)

@bp.route('/settings')
@login_required
def settings():
    return render_template('pages/dashboard/coming_soon.html', user=current_user)
