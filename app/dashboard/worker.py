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
        scope = request.form.get('scope')
        category = request.form.get('category')
        emission_factor_id = request.form.get('emission_factor_id')
        activity_data_raw = request.form.get('activity_data', '{}')
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        
        try:
            activity_data = json.loads(activity_data_raw)
        except json.JSONDecodeError:
            flash('Invalid JSON data.', 'error')
            return redirect(url_for('dashboard_worker.new_emission'))

        # Calculate CO2e if factor is present (MVP simplified logic)
        co2e_result = 0.0
        factor = None
        if emission_factor_id:
            factor = EmissionFactor.query.get(emission_factor_id)
            if factor and 'amount' in activity_data:
                co2e_result = float(activity_data['amount']) * factor.factor

        activity = EmissionActivity(
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
            scope=EmissionScope(scope),
            category=category,
            activity_data=activity_data,
            emission_factor_id=emission_factor_id,
            co2e_result=co2e_result,
            status=ActivityStatus.DRAFT,
            period_start=datetime.strptime(period_start, '%Y-%m-%d').date(),
            period_end=datetime.strptime(period_end, '%Y-%m-%d').date()
        )
        
        db.session.add(activity)
        db.session.flush() # Get ID

        # Handle File Upload
        if 'evidence_file' in request.files:
            file = request.files['evidence_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_data = file.read()
                
                # Encrypt
                encrypted_data = EncryptionManager.encrypt_file(file_data, current_user.organization_id)
                
                # Save to disk
                upload_dir = os.path.join(current_app.root_path, 'uploads', str(current_user.organization_id))
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, f"{activity.id}_{filename}.enc")
                
                with open(file_path, "wb") as f:
                    f.write(encrypted_data)
                
                # Create Document
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
                db.session.add(doc)

        # Audit Log for creation
        log = AuditLog(
            actor_id=current_user.id,
            organization_id=current_user.organization_id,
            action="CREATE_EMISSION_DRAFT",
            entity_type="EmissionActivity",
            entity_id=activity.id,
            details="Worker created emission draft."
        )
        db.session.add(log)
        
        db.session.commit()

        
        flash('Emission activity draft created.', 'success')
        return redirect(url_for('dashboard_worker.worker_index'))

    factors = EmissionFactor.query.all()
    scopes = [s.value for s in EmissionScope]
    return render_template('pages/dashboard/worker/new_emission.html', factors=factors, scopes=scopes)

@bp.route('/emissions/<int:id>/submit', methods=['POST'])
@login_required
def submit_emission(id):
    activity = EmissionActivity.query.get_or_404(id)
    
    if activity.created_by_id != current_user.id:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))
        
    if activity.status != ActivityStatus.DRAFT:
        flash('Only drafts can be submitted.', 'error')
        return redirect(url_for('dashboard_worker.worker_index'))

    activity.status = ActivityStatus.SUBMITTED
    db.session.commit()
    
    flash('Emission activity submitted for validation.', 'success')
    return redirect(url_for('dashboard_worker.worker_index'))
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