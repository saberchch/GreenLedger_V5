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
    
    from app.models.emission_activity import EmissionScope

    # ── Activity pools ────────────────────────────────────────────────────────
    # Chart shows SUBMITTED + VALIDATED so it updates with every new submission
    active_statuses = {ActivityStatus.SUBMITTED, ActivityStatus.VALIDATED}
    active_activities = [
        a for a in activities if a.status in active_statuses and a.co2e_result
    ]
    validated_activities = [
        a for a in activities if a.status == ActivityStatus.VALIDATED and a.co2e_result
    ]

    def scope_t(scope_enum, pool):
        return sum(a.co2e_result for a in pool if a.scope == scope_enum) / 1000

    # Live scope totals in tCO2e (drives scope_chart bars)
    total_t  = sum(a.co2e_result for a in active_activities) / 1000
    scope1_t = scope_t(EmissionScope.SCOPE_1, active_activities)
    scope2_t = scope_t(EmissionScope.SCOPE_2, active_activities)
    scope3_t = scope_t(EmissionScope.SCOPE_3, active_activities)

    # Validated-only subtotals (for KPI sub-labels)
    val_total_t  = sum(a.co2e_result for a in validated_activities) / 1000
    val_scope1_t = scope_t(EmissionScope.SCOPE_1, validated_activities)
    val_scope2_t = scope_t(EmissionScope.SCOPE_2, validated_activities)
    val_scope3_t = scope_t(EmissionScope.SCOPE_3, validated_activities)

    # Status counts
    pending_validation = sum(1 for a in activities if a.status == ActivityStatus.SUBMITTED)
    validated_count    = sum(1 for a in activities if a.status == ActivityStatus.VALIDATED)
    draft_count        = sum(1 for a in activities if a.status == ActivityStatus.DRAFT)
    rejected_count     = sum(1 for a in activities if a.status == ActivityStatus.REJECTED)

    # Real completeness: % of non-draft activities that have an ADEME factor
    non_draft_total = pending_validation + validated_count + rejected_count
    with_factor = sum(
        1 for a in activities
        if a.status in active_statuses and getattr(a, 'ademe_factor_id', None)
    )
    completeness = int(with_factor / non_draft_total * 100) if non_draft_total else 0

    # Pending emissions for validation table
    pending_emissions = [a for a in activities if a.status == ActivityStatus.SUBMITTED][:10]

    kpis = {
        # Scope totals in tCO2e — SUBMITTED + VALIDATED (drives chart)
        'total_emissions': f"{total_t:,.2f}",
        'scope1': f"{scope1_t:,.2f}",
        'scope2': f"{scope2_t:,.2f}",
        'scope3': f"{scope3_t:,.2f}",
        # Validated-only sub-totals
        'val_total': f"{val_total_t:,.2f}",
        'val_scope1': f"{val_scope1_t:,.2f}",
        'val_scope2': f"{val_scope2_t:,.2f}",
        'val_scope3': f"{val_scope3_t:,.2f}",
        # Trend placeholders
        'total_emissions_change': "+0.0%",
        'scope1_change': "+0.0%",
        'scope2_change': "+0.0%",
        'scope3_change': "+0.0%",
        # Counts
        'pending_validation': pending_validation,
        'validated_count': validated_count,
        'draft_count': draft_count,
        'rejected_count': rejected_count,
        'user_count': len(users),
        'completeness': f"{completeness}%",
        'activity_count': len(activities),
    }

    alerts = [
        {"type": "fact_check", "color": "blue",
         "title": f"{pending_validation} emission{'s' if pending_validation != 1 else ''} pending",
         "subtitle": "Awaiting your validation",
         "url": "/dashboard/org-admin/emissions/pending"},
        {"type": "group", "color": "green",
         "title": f"{len(users)} active user{'s' if len(users) != 1 else ''}",
         "subtitle": "In your organization",
         "url": "/dashboard/org-admin/users"},
        {"type": "verified", "color": "emerald",
         "title": f"{validated_count} validated record{'s' if validated_count != 1 else ''}",
         "subtitle": "View completed emission data",
         "url": "/dashboard/org-admin/emissions/completed"},
        {"type": "description", "color": "amber",
         "title": f"{completeness}% data completeness",
         "subtitle": f"{with_factor}/{non_draft_total} activities have ADEME factors",
         "url": "/dashboard/org-admin/emissions"},
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
    from app.emissions.services import reject_activity
    from app.security.permissions import PermissionManager

    activity = EmissionActivity.query.get_or_404(id)
    if not PermissionManager.can_validate_activity(current_user, activity):
        flash('Permission denied.', 'error')
        return redirect(url_for('dashboard_org_admin.org_admin_index'))

    reason = request.form.get('rejection_reason', '').strip()
    if not reason:
        flash('A rejection reason is required.', 'error')
        return redirect(url_for('dashboard_org_admin.emission_detail', id=id))

    try:
        reject_activity(current_user, id, reason)
        flash(f'Activity #{id} rejected.', 'info')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(request.referrer or url_for('dashboard_org_admin.emissions'))

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


# ============================================
# EMISSION PIPELINE ROUTES
# ============================================

@bp.route('/emissions')
@login_required
def emissions():
    """Full paginated list of org emissions with filters."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    org_id = current_user.organization_id
    filters = {
        'status':    request.args.get('status', ''),
        'scope':     request.args.get('scope', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to':   request.args.get('date_to', ''),
    }

    q = EmissionActivity.query.filter_by(organization_id=org_id)

    if filters['status']:
        q = q.filter(EmissionActivity.status == ActivityStatus(filters['status']))
    if filters['scope']:
        from app.models.emission_activity import EmissionScope
        q = q.filter(EmissionActivity.scope == EmissionScope(filters['scope']))
    if filters['date_from']:
        from datetime import datetime
        q = q.filter(EmissionActivity.period_start >= datetime.strptime(filters['date_from'], '%Y-%m-%d').date())
    if filters['date_to']:
        from datetime import datetime
        q = q.filter(EmissionActivity.period_end <= datetime.strptime(filters['date_to'], '%Y-%m-%d').date())

    activities = q.order_by(EmissionActivity.created_at.desc()).all()
    all_org = EmissionActivity.query.filter_by(organization_id=org_id).all()

    stats = {
        'total':     len(all_org),
        'submitted': sum(1 for a in all_org if a.status == ActivityStatus.SUBMITTED),
        'validated': sum(1 for a in all_org if a.status == ActivityStatus.VALIDATED),
        'rejected':  sum(1 for a in all_org if a.status == ActivityStatus.REJECTED),
    }

    return render_template(
        'pages/dashboard/org_admin/emissions.html',
        activities=activities,
        organization=current_user.organization,
        filters=filters,
        stats=stats,
    )


@bp.route('/emission/<int:id>')
@login_required
def emission_detail(id):
    """Detail view of a single emission for org-admin review."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    activity = EmissionActivity.query.get_or_404(id)
    if activity.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.emissions'))

    from app.models.document import Document
    documents = Document.query.filter_by(activity_id=id).all()

    return render_template(
        'pages/dashboard/org_admin/emission_detail.html',
        activity=activity,
        documents=documents,
        organization=current_user.organization,
    )


@bp.route('/emissions/new', methods=['GET', 'POST'])
@login_required
def new_emission():
    """Org-admin direct entry -- auto-validated, no worker loop."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        try:
            form = request.form.to_dict()
            form.pop('action', None)

            from app.emissions.services import create_activity
            activity = create_activity(current_user, form, auto_validate=True)
            flash(f'Activity #{activity.id} created and auto-validated.', 'success')
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Admin new_emission error: {e}")
            flash(f'Error: {str(e)}', 'error')

        return redirect(url_for('dashboard_org_admin.emissions'))

    from app.models.emission_activity import EmissionScope
    scopes = [s.value for s in EmissionScope]
    return render_template(
        'pages/dashboard/worker/new_emission.html',
        scopes=scopes,
        is_admin=True,
    )


@bp.route('/emission/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_emission(id):
    """Edit a non-AUDITED emission. Admin edits stay VALIDATED."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    activity = EmissionActivity.query.get_or_404(id)
    if activity.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.emissions'))

    if activity.status == ActivityStatus.AUDITED:
        flash('This activity has been audited and is locked.', 'error')
        return redirect(url_for('dashboard_org_admin.emission_detail', id=id))

    if request.method == 'POST':
        try:
            form = request.form.to_dict()
            form.pop('action', None)

            from app.emissions.services import update_activity
            update_activity(current_user, id, form, is_admin=True)
            flash(f'Activity #{id} updated successfully.', 'success')
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Admin edit_emission error: {e}")
            flash(f'Error: {str(e)}', 'error')

        return redirect(url_for('dashboard_org_admin.emission_detail', id=id))

    from app.models.emission_activity import EmissionScope
    scopes = [s.value for s in EmissionScope]
    return render_template(
        'pages/dashboard/org_admin/edit_emission.html',
        activity=activity,
        scopes=scopes,
        organization=current_user.organization,
    )


# ============================================
# PENDING EMISSIONS PAGE
# ============================================

@bp.route('/emissions/pending')
@login_required
def pending_emissions_page():
    """Dedicated page for pending-validation emissions."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    org_id = current_user.organization_id
    activities = (EmissionActivity.query
                  .filter_by(organization_id=org_id, status=ActivityStatus.SUBMITTED)
                  .order_by(EmissionActivity.created_at.desc())
                  .all())

    return render_template(
        'pages/dashboard/org_admin/pending_emissions.html',
        activities=activities,
        organization=current_user.organization,
    )


# ============================================
# COMPLETED (VALIDATED) EMISSIONS PAGE
# ============================================

@bp.route('/emissions/completed')
@login_required
def completed_emissions():
    """Dedicated page for validated/audited emissions."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    org_id = current_user.organization_id
    activities = (EmissionActivity.query
                  .filter(
                      EmissionActivity.organization_id == org_id,
                      EmissionActivity.status.in_([ActivityStatus.VALIDATED, ActivityStatus.AUDITED])
                  )
                  .order_by(EmissionActivity.created_at.desc())
                  .all())

    total_t = sum((a.co2e_result or 0) for a in activities) / 1000

    return render_template(
        'pages/dashboard/org_admin/completed_emissions.html',
        activities=activities,
        total_t=total_t,
        organization=current_user.organization,
    )


# ============================================
# DOCUMENT UPLOAD
# ============================================

@bp.route('/documents/upload', methods=['POST'])
@login_required
def upload_document():
    """Handle direct document upload from admin document page."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    from werkzeug.utils import secure_filename
    from flask import current_app
    from app.security.encryption import EncryptionManager
    from app.models.document import Document
    import os

    file = request.files.get('document_file')
    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('dashboard_org_admin.documents'))

    filename = secure_filename(file.filename)
    file_data = file.read()

    try:
        encrypted_data = EncryptionManager.encrypt_file(file_data, current_user.organization_id)
        upload_dir = os.path.join(current_app.root_path, 'uploads', str(current_user.organization_id))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"admin_{current_user.id}_{filename}.enc")
        with open(file_path, 'wb') as f:
            f.write(encrypted_data)

        doc = Document(
            filename=filename,
            file_path=file_path,
            encrypted=True,
            hash_checksum=EncryptionManager.get_file_hash(file_data),
            content_type=file.content_type or 'application/octet-stream',
            file_size=len(file_data),
            uploaded_by_id=current_user.id,
            organization_id=current_user.organization_id,
            activity_id=None,
        )
        db.session.add(doc)
        db.session.commit()
        flash(f'"{filename}" uploaded and encrypted successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Document upload error: {e}")
        flash(f'Upload failed: {str(e)}', 'error')

    return redirect(url_for('dashboard_org_admin.documents'))


# ============================================
# USER ROLE MANAGEMENT
# ============================================

@bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
def change_user_role(user_id):
    """Change a user's role within the organization."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    user = User.query.get_or_404(user_id)
    if user.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    if user.id == current_user.id:
        flash("You cannot change your own role.", 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    new_role_str = request.form.get('role', '').strip()
    try:
        user.role = UserRole(new_role_str)
        db.session.commit()
        flash(f'{user.email} role updated to {new_role_str.replace("_", " ").title()}.', 'success')
    except (ValueError, Exception) as e:
        flash(f'Invalid role: {str(e)}', 'error')

    return redirect(url_for('dashboard_org_admin.users'))
