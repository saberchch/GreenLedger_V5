from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app

from flask_login import login_required, current_user
from app.extensions import db
from app.models.report import Report, ReportStatus
from app.models.emission_activity import EmissionActivity, EmissionScope, ActivityStatus
from app.models.emission_factor import EmissionFactor
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.security.permissions import PermissionManager
from app.security.encryption import EncryptionManager
from datetime import datetime
import json
from werkzeug.utils import secure_filename
import os

bp = Blueprint(
    'dashboard_worker',
    __name__,
    url_prefix='/dashboard/worker'
)


@bp.route('/analytics')
@login_required
def analytics():
    """Detailed standalone analytics page with charts."""
    return render_template('pages/dashboard/analytics.html', organization=current_user.organization)


@bp.route('/')
@login_required
def worker_index():
    """
    Worker dashboard — shows company-wide scope KPIs (read-only) and the worker's own activities.
    """
    # Worker's own activities (all, for stats)
    all_my_activities = (EmissionActivity.query
                     .filter_by(created_by_id=current_user.id)
                     .order_by(EmissionActivity.created_at.desc())
                     .all())

    recent_page = request.args.get('recent_page', 1, type=int)
    my_activities_paginated = (EmissionActivity.query
                     .filter_by(created_by_id=current_user.id)
                     .order_by(EmissionActivity.created_at.desc())
                     .paginate(page=recent_page, per_page=5, error_out=False))

    # Company-wide activities (same org) for the scope overview
    org_id = current_user.organization_id
    org_activities = (EmissionActivity.query
                      .filter_by(organization_id=org_id)
                      .all()) if org_id else []

    # Pool for chart: SUBMITTED + VALIDATED (same as admin)
    active_statuses = {ActivityStatus.SUBMITTED, ActivityStatus.VALIDATED}
    active_org = [a for a in org_activities if a.status in active_statuses and a.co2e_result]

    def scope_t(scope_enum, pool):
        return sum(a.co2e_result for a in pool if a.scope == scope_enum) / 1000

    total_t  = sum(a.co2e_result for a in active_org) / 1000
    scope1_t = scope_t(EmissionScope.SCOPE_1, active_org)
    scope2_t = scope_t(EmissionScope.SCOPE_2, active_org)
    scope3_t = scope_t(EmissionScope.SCOPE_3, active_org)

    # Worker-specific counts
    my_draft     = sum(1 for a in all_my_activities if a.status == ActivityStatus.DRAFT)
    my_submitted = sum(1 for a in all_my_activities if a.status == ActivityStatus.SUBMITTED)
    my_validated = sum(1 for a in all_my_activities if a.status == ActivityStatus.VALIDATED)
    my_rejected  = sum(1 for a in all_my_activities if a.status == ActivityStatus.REJECTED)

    kpis = {
        'total_emissions':        f"{total_t:,.2f}",
        'scope1':                 f"{scope1_t:,.2f}",
        'scope2':                 f"{scope2_t:,.2f}",
        'scope3':                 f"{scope3_t:,.2f}",
        'total_emissions_change': "+0.0%",
        'scope1_change':          "+0.0%",
        'scope2_change':          "+0.0%",
        'scope3_change':          "+0.0%",
        # For scope_chart status pills
        'pending_validation': my_submitted,
        'validated_count':    my_validated,
        'draft_count':        my_draft,
        'rejected_count':     my_rejected,
    }

    # Contextual alerts based on real state
    alerts = []
    if my_rejected:
        alerts.append({"type": "cancel", "color": "red",
                        "title": f"{my_rejected} activit{'ies' if my_rejected > 1 else 'y'} rejected",
                        "subtitle": "Open drafts to read feedback and resubmit",
                        "url": "/dashboard/worker/submissions/status"})
    if my_draft:
        alerts.append({"type": "edit_note", "color": "amber",
                        "title": f"{my_draft} draft{'s' if my_draft > 1 else ''} not submitted",
                        "subtitle": "Submit your drafts for validation",
                        "url": "/dashboard/worker/drafts"})
    if my_submitted:
        alerts.append({"type": "fact_check", "color": "blue",
                        "title": f"{my_submitted} awaiting validation",
                        "subtitle": "Your org admin will review these",
                        "url": "/dashboard/worker/submissions"})
    if not alerts:
        alerts.append({"type": "check_circle", "color": "green",
                        "subtitle": "No pending actions — add a new emission",
                        "url": "/dashboard/worker/emissions/new"})

    return render_template(
        'pages/dashboard/worker/index.html',
        user=current_user,
        my_activities=my_activities_paginated,
        kpis=kpis,
        alerts=alerts
    )

@bp.route('/emissions/new', methods=['GET', 'POST'])
@login_required
def new_emission():
    if not PermissionManager.can_submit_activity(current_user):
        flash('Permission denied.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))

    if request.method == 'POST':
        try:
            form = request.form.to_dict()
            action = form.pop('action', 'draft')

            from app.emissions.services import create_activity, submit_activity
            activity = create_activity(current_user, form)

            # Handle evidence file upload — isolated so encryption errors never kill the save
            file = request.files.get('evidence_file')
            if file and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    file_data = file.read()
                    encrypted_data = EncryptionManager.encrypt_file(file_data, current_user.organization_id)
                    upload_dir = os.path.join(current_app.root_path, 'uploads', str(current_user.organization_id))
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, f"{activity.id}_{filename}.enc")
                    with open(file_path, "wb") as f:
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
                        activity_id=activity.id
                    )
                    db.session.add(doc)
                    db.session.commit()
                except Exception as upload_err:
                    current_app.logger.warning(f"Evidence upload failed (activity saved): {upload_err}")
                    flash(f'Activity saved, but document upload failed: {upload_err}', 'warning')

            # Auto-submit if user clicked "Submit for Validation"
            if action == 'submit':
                submit_activity(current_user, activity.id)
                flash('Activity submitted for validation.', 'success')
            else:
                flash('Draft saved. You can submit it from the Drafts page.', 'success')

        except Exception as e:
            current_app.logger.error(f"Error creating emission: {e}")
            flash(f'Error saving activity: {str(e)}', 'error')

        return redirect(url_for('dashboard_worker.worker_index'))

    # GET — render wizard (no DB factor dropdown needed anymore)
    scopes = [s.value for s in EmissionScope]
    return render_template('pages/dashboard/worker/new_emission.html', scopes=scopes)

@bp.route('/emissions/<int:id>/submit', methods=['POST'])
@login_required
def submit_emission(id):
    from app.emissions.services import submit_activity
    try:
        submit_activity(current_user, id)
        flash('Emission activity submitted for validation.', 'success')
    except (PermissionError, ValueError) as e:
        flash(str(e), 'error')
    return redirect(url_for('dashboard_worker.worker_index'))


@bp.route('/emissions/<int:id>')
@login_required
def emission_detail(id):
    """Read-only detail view of a single emission activity."""
    activity = EmissionActivity.query.get_or_404(id)
    if activity.created_by_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))
    from app.models.document import Document
    documents = Document.query.filter_by(activity_id=id).all()
    return render_template('pages/dashboard/worker/emission_detail.html',
                           activity=activity, documents=documents)


@bp.route('/emissions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_emission(id):
    """Worker edits an activity they own. Resets its status to DRAFT."""
    activity = EmissionActivity.query.get_or_404(id)
    if activity.created_by_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))

    if activity.status == ActivityStatus.AUDITED:
        flash('This activity has been audited and is locked.', 'error')
        return redirect(url_for('dashboard_worker.emission_detail', id=id))

    if request.method == 'POST':
        try:
            form = request.form.to_dict()
            form.pop('action', None)

            from app.emissions.services import update_activity
            update_activity(current_user, id, form, is_admin=False)
            
            # Handle additional evidence file upload
            from werkzeug.utils import secure_filename
            from app.security.encryption import EncryptionManager
            from app.models.document import Document
            import os
            
            file = request.files.get('evidence_file')
            if file and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    file_data = file.read()
                    encrypted_data = EncryptionManager.encrypt_file(file_data, current_user.organization_id)
                    upload_dir = os.path.join(current_app.root_path, 'uploads', str(current_user.organization_id))
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, f"{activity.id}_{filename}.enc")
                    with open(file_path, "wb") as f:
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
                        activity_id=activity.id
                    )
                    db.session.add(doc)
                    db.session.commit()
                except Exception as upload_err:
                    current_app.logger.warning(f"Evidence upload failed (activity saved): {upload_err}")
                    flash(f'Activity saved, but document upload failed: {str(upload_err)}', 'warning')
            
            flash(f'Activity #{id} updated. You can now resubmit it.', 'success')
        except Exception as e:
            current_app.logger.error(f"Worker edit_emission error: {e}")
            flash(f'Error: {str(e)}', 'error')

        return redirect(url_for('dashboard_worker.emission_detail', id=id))

    scopes = [s.value for s in EmissionScope]
    return render_template(
        'pages/dashboard/worker/edit_emission.html',
        activity=activity,
        scopes=scopes,
    )



@bp.route('/emissions/<int:id>/duplicate')
@login_required
def duplicate_emission(id):
    """Redirect to new-emission wizard pre-filled with fields from an existing activity."""
    activity = EmissionActivity.query.get_or_404(id)
    if activity.created_by_id != current_user.id and activity.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))

    from urllib.parse import urlencode
    params = {
        'scope':                 activity.scope.value,
        'category':              activity.category or '',
        'activity_type':         activity.activity_type.value,
        'description':           activity.description or '',
        'transport_mode':        activity.transport_mode or '',
        'ademe_factor_id':       activity.ademe_factor_id or '',
        'ademe_factor_name':     activity.ademe_factor_name or '',
        'ademe_factor_value':    activity.ademe_factor_value or '',
        'ademe_factor_unit':     activity.ademe_factor_unit or '',
        'ademe_factor_source':   activity.ademe_factor_source or '',
        'ademe_factor_category': activity.ademe_factor_category or '',
    }
    base_url = url_for('dashboard_worker.new_emission')
    return redirect(f"{base_url}?{urlencode(params)}")


@bp.route('/submit', methods=['POST'])
@login_required
def submit_report():
    summary = request.form.get('summary')
    
    if not summary:
        flash('Report content cannot be empty.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))
    
    # Create Report
    if not current_user.organization_id:
        flash('You must belong to an organization to submit reports.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))

    report = Report(
        summary=summary,
        status=ReportStatus.PENDING_AUDIT, # Goes to auditor
        organization_id=current_user.organization_id,
        created_by_id=current_user.id
    )
    
    db.session.add(report)
    db.session.commit()
    
    flash('Data submitted for audit.', 'success')
    return redirect(url_for('dashboard_worker.worker_index'))

# ============================================
# NEW WORKER NAVIGATION ROUTES
# ============================================

@bp.route('/drafts')
@login_required
def drafts():
    """View draft emissions."""
    page = request.args.get('page', 1, type=int)
    drafts = EmissionActivity.query.filter_by(
        created_by_id=current_user.id,
        status=ActivityStatus.DRAFT
    ).order_by(EmissionActivity.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('pages/dashboard/worker/drafts.html', drafts=drafts)

@bp.route('/rejected')
@login_required
def rejected():
    """View rejected emissions."""
    page = request.args.get('page', 1, type=int)
    rejected = EmissionActivity.query.filter_by(
        created_by_id=current_user.id,
        status=ActivityStatus.REJECTED
    ).order_by(EmissionActivity.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('pages/dashboard/worker/rejected.html', rejected=rejected)

@bp.route('/submissions')
@login_required
def submissions():
    """View all submissions."""
    page = request.args.get('page', 1, type=int)
    submissions = EmissionActivity.query.filter_by(
        created_by_id=current_user.id
    ).filter(EmissionActivity.status.in_([ActivityStatus.SUBMITTED, ActivityStatus.VALIDATED])).order_by(
        EmissionActivity.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    return render_template('pages/dashboard/worker/submissions.html', submissions=submissions)

@bp.route('/submissions/status')
@login_required
def submission_status():
    """View submission status — all activities with their current status."""
    page = request.args.get('page', 1, type=int)
    all_activities = (EmissionActivity.query
                      .filter_by(created_by_id=current_user.id)
                      .order_by(EmissionActivity.created_at.desc())
                      .paginate(page=page, per_page=10, error_out=False))
    return render_template('pages/dashboard/worker/submission_status.html',
                           all_activities=all_activities)

@bp.route('/documents')
@login_required
def documents():
    """View my documents."""
    page = request.args.get('page', 1, type=int)
    docs = Document.query.filter_by(uploaded_by_id=current_user.id).order_by(Document.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('pages/dashboard/worker/documents.html', documents=docs)

@bp.route('/documents/upload', methods=['POST'])
@login_required
def upload_document():
    """Upload evidence document (standalone, not linked to a specific activity)."""
    file = request.files.get('document_file')
    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('dashboard_worker.documents'))

    try:
        filename = secure_filename(file.filename)
        file_data = file.read()
        encrypted_data = EncryptionManager.encrypt_file(file_data, current_user.organization_id)
        upload_dir = os.path.join(current_app.root_path, 'uploads', str(current_user.organization_id))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"worker_{current_user.id}_{filename}.enc")
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
        current_app.logger.error(f"Worker document upload error: {e}")
        flash(f'Upload failed: {str(e)}', 'error')

    return redirect(url_for('dashboard_worker.documents'))

@bp.route('/guidance/ghg')
@login_required
def ghg_guide():
    """GHG Protocol guide."""
    return render_template('pages/dashboard/worker/ghg_guide.html')

@bp.route('/guidance/calculations')
@login_required
def calculation_help():
    """Calculation help."""
    return render_template('pages/dashboard/worker/calculation_help.html')