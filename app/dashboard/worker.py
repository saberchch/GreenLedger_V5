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


@bp.route('/')
@login_required
def worker_index():
    """
    Worker dashboard
    """
    my_activities = EmissionActivity.query.filter_by(created_by_id=current_user.id).order_by(EmissionActivity.created_at.desc()).all()
    
    # Mock KPIs for design (Replace with real logic later)
    kpis = {
        'footprint': "12,450",
        'footprint_change': "-5%",
        'liability': "€45,200",
        'liability_change': "+2%",
        'exposure': "€125,000",
        'exposure_change': "0%",
        'completeness': "82%"
    }
    
    # Mock Alerts
    alerts = [
        {"type": "priority_high", "color": "amber", "title": "Missing supplier data", "subtitle": "Invoice #204 - Steel Import"},
        {"type": "fact_check", "color": "blue", "title": "Pending Approval", "subtitle": "Q2 Compliance Report"},
        {"type": "update", "color": "green", "title": "System Update", "subtitle": "New emission factors available"}
    ]

    return render_template(
        'pages/dashboard/worker/index.html',
        user=current_user,
        my_activities=my_activities,
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

            # Handle evidence file upload
            if 'evidence_file' in request.files:
                file = request.files['evidence_file']
                if file and file.filename:
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
                        content_type=file.content_type,
                        file_size=len(file_data),
                        uploaded_by_id=current_user.id,
                        organization_id=current_user.organization_id,
                        activity_id=activity.id
                    )
                    from app.extensions import db as _db
                    _db.session.add(doc)
                    _db.session.commit()

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
    """Worker edits a DRAFT or REJECTED activity. Resets status to DRAFT."""
    activity = EmissionActivity.query.get_or_404(id)
    if activity.created_by_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))

    if activity.status == ActivityStatus.AUDITED:
        flash('This activity has been audited and is locked.', 'error')
        return redirect(url_for('dashboard_worker.emission_detail', id=id))
    if activity.status not in (ActivityStatus.DRAFT, ActivityStatus.REJECTED):
        flash('Only draft or rejected activities can be edited.', 'error')
        return redirect(url_for('dashboard_worker.emission_detail', id=id))

    if request.method == 'POST':
        try:
            form = request.form.to_dict()
            form.pop('action', None)

            from app.emissions.services import update_activity
            update_activity(current_user, id, form, is_admin=False)
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
    drafts = EmissionActivity.query.filter_by(
        created_by_id=current_user.id,
        status=ActivityStatus.DRAFT
    ).order_by(EmissionActivity.created_at.desc()).all()
    return render_template('pages/dashboard/worker/drafts.html', drafts=drafts)

@bp.route('/rejected')
@login_required
def rejected():
    """View rejected emissions."""
    rejected = EmissionActivity.query.filter_by(
        created_by_id=current_user.id,
        status=ActivityStatus.REJECTED
    ).order_by(EmissionActivity.created_at.desc()).all()
    return render_template('pages/dashboard/worker/rejected.html', rejected=rejected)

@bp.route('/submissions')
@login_required
def submissions():
    """View all submissions."""
    submissions = EmissionActivity.query.filter_by(
        created_by_id=current_user.id
    ).filter(EmissionActivity.status.in_([ActivityStatus.SUBMITTED, ActivityStatus.VALIDATED])).order_by(
        EmissionActivity.created_at.desc()
    ).all()
    return render_template('pages/dashboard/worker/submissions.html', submissions=submissions)

@bp.route('/submissions/status')
@login_required
def submission_status():
    """View submission status."""
    return render_template('pages/dashboard/worker/submission_status.html')

@bp.route('/documents')
@login_required
def documents():
    """View my documents."""
    docs = Document.query.filter_by(uploaded_by_id=current_user.id).order_by(Document.created_at.desc()).all()
    return render_template('pages/dashboard/worker/documents.html', documents=docs)

@bp.route('/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    """Upload evidence document."""
    if request.method == 'POST':
        flash('Document upload functionality coming soon!', 'info')
        return redirect(url_for('dashboard_worker.documents'))
    return render_template('pages/dashboard/worker/upload_document.html')

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