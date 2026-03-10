from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.emission_activity import EmissionActivity, ActivityStatus
from app.models.user import User, UserRole
from app.security.permissions import PermissionManager
from app.models.audit_log import AuditLog
from app.models.report import Report

bp = Blueprint(
    'dashboard_org_admin',
    __name__,
    url_prefix='/dashboard/org-admin'
)


@bp.route('/analytics')
@login_required
def analytics():
    """Detailed standalone analytics page with charts."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
         flash('Access denied.', 'error')
         return redirect(url_for('main.index'))

    return render_template('pages/dashboard/analytics.html', organization=current_user.organization)


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
    
    all_activities = EmissionActivity.query.filter_by(organization_id=org_id).order_by(EmissionActivity.created_at.desc()).all()
    users = User.query.filter_by(organization_id=org_id).all()
    
    recent_page = request.args.get('recent_page', 1, type=int)
    recent_activities_paginated = EmissionActivity.query.filter_by(organization_id=org_id).order_by(EmissionActivity.created_at.desc()).paginate(page=recent_page, per_page=5, error_out=False)

    pending_page = request.args.get('pending_page', 1, type=int)
    pending_emissions_paginated = EmissionActivity.query.filter_by(organization_id=org_id, status=ActivityStatus.SUBMITTED).order_by(EmissionActivity.created_at.desc()).paginate(page=pending_page, per_page=5, error_out=False)
    
    from app.models.emission_activity import EmissionScope

    # ── Activity pools ────────────────────────────────────────────────────────
    # Chart shows SUBMITTED + VALIDATED so it updates with every new submission
    active_statuses = {ActivityStatus.SUBMITTED, ActivityStatus.VALIDATED}
    active_activities = [
        a for a in all_activities if a.status in active_statuses and a.co2e_result
    ]
    validated_activities = [
        a for a in all_activities if a.status == ActivityStatus.VALIDATED and a.co2e_result
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
    pending_validation = sum(1 for a in all_activities if a.status == ActivityStatus.SUBMITTED)
    validated_count    = sum(1 for a in all_activities if a.status == ActivityStatus.VALIDATED)
    draft_count        = sum(1 for a in all_activities if a.status == ActivityStatus.DRAFT)
    rejected_count     = sum(1 for a in all_activities if a.status == ActivityStatus.REJECTED)

    # Real completeness: % of non-draft activities that have an ADEME factor
    non_draft_total = pending_validation + validated_count + rejected_count
    with_factor = sum(
        1 for a in all_activities
        if a.status in active_statuses and getattr(a, 'ademe_factor_id', None)
    )
    completeness = int(with_factor / non_draft_total * 100) if non_draft_total else 0

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
        'activity_count': len(all_activities),
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
        recent_activities=recent_activities_paginated,
        pending_emissions=pending_emissions_paginated,
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
    
    page = request.args.get('page', 1, type=int)
    users_paginated = User.query.filter_by(organization_id=current_user.organization_id).paginate(page=page, per_page=10, error_out=False)
    
    # ── Auditor contract data (new smart-contract system) ──────────────────────
    from app.models.auditor_contract import AuditorContract, ContractStatus

    OPEN_STATUSES = [ContractStatus.PENDING, ContractStatus.TRIAL, ContractStatus.ACTIVE]

    # IDs of auditors that already have an open contract with this org
    engaged_auditor_ids = {
        c.auditor_id
        for c in AuditorContract.query.filter(
            AuditorContract.organization_id == current_user.organization_id,
            AuditorContract.status.in_(OPEN_STATUSES)
        ).all()
    }

    # All verified platform auditors NOT already engaged with this org
    all_platform_auditors = User.query.filter(User.role == UserRole.AUDITOR).all()
    available_auditors = [a for a in all_platform_auditors
                          if a.id not in engaged_auditor_ids]

    # Still pass pending_requests for backward-compat (unused in new template)
    pending_requests = []

    return render_template(
        'pages/dashboard/org_admin/users.html',
        users=users_paginated,
        pending_requests=pending_requests,
        available_auditors=available_auditors
    )

@bp.route('/auditor/propose/<int:auditor_id>', methods=['POST'])
@login_required
def propose_contract(auditor_id):
    """Propose a smart-contract engagement to a platform auditor."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    from app.models.auditor_contract import AuditorContract, ContractStatus, AuditorType
    from app.models.notification import Notification, NotificationType

    auditor = User.query.get_or_404(auditor_id)
    if auditor.role != UserRole.AUDITOR:
        flash('Selected user is not a platform auditor.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    org = current_user.organization
    auditor_type_str = request.form.get('auditor_type', 'primary').lower()

    # Enforce 1 primary + 1 collateral limit
    if auditor_type_str == 'primary' and org.primary_auditor_id:
        flash('Your organisation already has a Primary Auditor. Cancel the existing contract first.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))
    if auditor_type_str == 'collateral' and org.collateral_auditor_id:
        flash('Your organisation already has a Collateral Auditor. Cancel the existing contract first.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    # Check no pending contract to same auditor already
    existing = AuditorContract.query.filter_by(
        organization_id=org.id,
        auditor_id=auditor_id,
        status=ContractStatus.PENDING
    ).first()
    if existing:
        flash('A pending contract already exists for this auditor.', 'warning')
        return redirect(url_for('dashboard_org_admin.users'))

    monthly_fee = request.form.get('monthly_fee', '').strip()
    message     = request.form.get('message', '').strip()

    try:
        fee = float(monthly_fee) if monthly_fee else None
    except ValueError:
        fee = None

    contract = AuditorContract(
        organization_id=org.id,
        auditor_id=auditor_id,
        auditor_type=AuditorType.PRIMARY if auditor_type_str == 'primary' else AuditorType.COLLATERAL,
        status=ContractStatus.PENDING,
        monthly_fee=fee,
        message=message or None,
    )
    db.session.add(contract)

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=org.id,
        action='PROPOSE_AUDITOR_CONTRACT',
        entity_type='AuditorContract',
        details=f'Org Admin proposed {auditor_type_str} contract to {auditor.email}. Fee: {fee}/mo.'
    )
    db.session.add(log)

    notif = Notification(
        user_id=auditor.id,
        title='New Audit Contract Proposal',
        message=f'{org.name} has proposed a {auditor_type_str} auditor contract. Monthly fee: {fee or "TBD"}.',
        type=NotificationType.INFO,
        related_entity_type='auditor_contract',
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Contract proposal sent to {auditor.first_name} {auditor.last_name}.', 'success')
    return redirect(url_for('dashboard_org_admin.users'))


@bp.route('/auditor/contract/<int:contract_id>')
@login_required
def contract_detail(contract_id):
    """View full details of an auditor contract."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    from app.models.auditor_contract import AuditorContract
    contract = AuditorContract.query.get_or_404(contract_id)
    if contract.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    return render_template('pages/dashboard/org_admin/contract_detail.html',
                           contract=contract,
                           organization=current_user.organization)


@bp.route('/auditor/contract/<int:contract_id>/cancel', methods=['POST'])
@login_required
def cancel_contract(contract_id):
    """Cancel an auditor contract. If PRIMARY is cancelled during trial, auto-notify collateral to step up."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    from app.models.auditor_contract import AuditorContract, ContractStatus, AuditorType
    from app.models.notification import Notification, NotificationType

    contract = AuditorContract.query.get_or_404(contract_id)
    if contract.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    if contract.status in (ContractStatus.COMPLETED, ContractStatus.CANCELLED, ContractStatus.DISCARDED):
        flash('This contract is already closed.', 'warning')
        return redirect(url_for('dashboard_org_admin.users'))

    was_trial    = contract.status == ContractStatus.TRIAL
    was_primary  = contract.auditor_type == AuditorType.PRIMARY

    # Mark as discarded (trial failure) or cancelled (explicit termination)
    contract.status = ContractStatus.DISCARDED if was_trial else ContractStatus.CANCELLED
    org = current_user.organization

    # Free the org auditor ID slot
    if was_primary and org.primary_auditor_id == contract.auditor_id:
        org.primary_auditor_id = None
    elif contract.auditor_type == AuditorType.COLLATERAL and org.collateral_auditor_id == contract.auditor_id:
        org.collateral_auditor_id = None

    # Notify the terminated auditor
    db.session.add(Notification(
        user_id=contract.auditor_id,
        title='Contract Terminated',
        message=f'{org.name} has terminated your {contract.auditor_type.value} audit contract.'
                + (' (Trial period failure)' if was_trial else ''),
        type=NotificationType.WARNING,
        related_entity_type='auditor_contract',
    ))

    action = 'DISCARD_AUDITOR_CONTRACT_TRIAL' if was_trial else 'CANCEL_AUDITOR_CONTRACT'
    log = AuditLog(
        actor_id=current_user.id,
        organization_id=org.id,
        action=action,
        entity_type='AuditorContract',
        entity_id=contract.id,
        details=f'Org Admin terminated {contract.auditor_type.value} contract #{contract.id} with auditor {contract.auditor.email}.'
    )
    db.session.add(log)

    # ── Smart Contract: If PRIMARY was terminated, promote COLLATERAL ──
    promoted_collateral = None
    if was_primary:
        collateral_contract = AuditorContract.query.filter(
            AuditorContract.organization_id == org.id,
            AuditorContract.auditor_type  == AuditorType.COLLATERAL,
            AuditorContract.status.in_([ContractStatus.TRIAL, ContractStatus.ACTIVE])
        ).first()

        if collateral_contract:
            promoted_collateral = collateral_contract.auditor

            # ✅ THE KEY STEP: Actually convert the collateral contract to PRIMARY
            collateral_contract.auditor_type = AuditorType.PRIMARY
            org.primary_auditor_id = collateral_contract.auditor_id  # fill the primary slot
            org.collateral_auditor_id = None                          # reopen collateral slot

            # Notify the promoted auditor
            db.session.add(Notification(
                user_id=collateral_contract.auditor_id,
                title='You are now the Primary Auditor',
                message=(
                    f'The primary auditor contract at {org.name} was terminated. '
                    f'Your role has been upgraded from Collateral to Primary Auditor. '
                    f'You can now review and validate emission activities immediately.'
                ),
                type=NotificationType.WARNING,
                related_entity_type='auditor_contract',
                related_entity_id=collateral_contract.id,
            ))
            db.session.add(AuditLog(
                actor_id=current_user.id,
                organization_id=org.id,
                action='COLLATERAL_PROMOTED_TO_PRIMARY',
                entity_type='AuditorContract',
                entity_id=collateral_contract.id,
                details=f'Collateral auditor {collateral_contract.auditor.email} promoted to Primary. Collateral slot reopened.',
            ))

    db.session.commit()

    if was_primary and promoted_collateral:
        flash(
            f'Primary auditor contract terminated. Collateral auditor '
            f'{promoted_collateral.first_name} {promoted_collateral.last_name} '
            f'has been notified and is now the acting auditor.',
            'warning'
        )
    else:
        flash('Auditor contract cancelled.', 'info')
    return redirect(url_for('dashboard_org_admin.users'))


@bp.route('/documents')
@login_required
def documents():
    """Documents viewing page."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    from app.models.document import Document
    page = request.args.get('page', 1, type=int)
    docs = Document.query.filter_by(organization_id=current_user.organization_id).order_by(Document.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('pages/dashboard/org_admin/documents.html', documents=docs)

@bp.route('/reports')
@login_required
def reports():
    """Reports generation page."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    # Pass existing reports to the template
    reports_list = Report.query.filter_by(organization_id=current_user.organization_id).order_by(Report.created_at.desc()).all()
    return render_template('pages/dashboard/org_admin/reports.html', reports=reports_list)

@bp.route('/reports/<int:report_id>/download/<format>')
@login_required
def download_report(report_id, format):
    """Download a generated report in the specified format."""
    from flask import send_file
    from app.services.report_generator import PDFReportGenerator, DocxReportGenerator, ExcelReportGenerator

    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.reports'))

    report = Report.query.get_or_404(report_id)
    if report.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.reports'))

    try:
        if format == 'pdf':
            generator = PDFReportGenerator()
            buffer = generator.generate(report_id)
            mimetype = 'application/pdf'
            filename = f"GreenLedger_Report_{report.period_label or report.id}.pdf"
        elif format == 'docx':
            generator = DocxReportGenerator()
            buffer = generator.generate(report_id)
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            filename = f"GreenLedger_Report_{report.period_label or report.id}.docx"
        elif format == 'xlsx':
            generator = ExcelReportGenerator()
            buffer = generator.generate(report_id)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f"GreenLedger_Report_{report.period_label or report.id}.xlsx"
        else:
            flash(f"Unsupported format: {format}", 'error')
            return redirect(url_for('dashboard_org_admin.reports'))

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('dashboard_org_admin.reports'))

@bp.route('/reports/download_latest/<format>')
@login_required
def download_latest_report(format):
    """Convenience route to download the most recent report for macro buttons."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.reports'))

    latest = Report.query.filter_by(organization_id=current_user.organization_id).order_by(Report.created_at.desc()).first()
    if not latest:
        flash('No reports available to download. Please generate one first.', 'warning')
        return redirect(url_for('dashboard_org_admin.reports'))
        
    return redirect(url_for('dashboard_org_admin.download_report', report_id=latest.id, format=format))

@bp.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Stub to trigger the 'create a draft/final report' UI."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.org_admin_index'))
    
    # In a real flow, this creates the Report record in the DB based on date ranges
    # For now, let's just make sure there is at least a mock report record if empty so users can test downloads
    existing = Report.query.filter_by(organization_id=current_user.organization_id).first()
    if not existing:
        from app.models.report import ReportStatus
        rep = Report(
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
            summary="This is an automatically generated Executive Summary. It highlights the primary emission sources and outlines the company's commitment to reducing Scope 2 and 3 emissions over the next fiscal year.",
            status=ReportStatus.DRAFT,
            period_label="Current Year"
        )
        db.session.add(rep)
        db.session.commit()
        flash('New draft report created!', 'success')
    else:
        flash('Report generation pipeline triggered (mocked).', 'success')
        
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
    if current_user.role not in [UserRole.ORG_ADMIN, UserRole.WORKER] or not current_user.organization_id:
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

    page = request.args.get('page', 1, type=int)
    activities = q.order_by(EmissionActivity.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
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
    if current_user.role not in [UserRole.ORG_ADMIN, UserRole.WORKER] or not current_user.organization_id:
        flash('Access denied.', 'error')
        if current_user.role == UserRole.WORKER:
            return redirect(url_for('dashboard_worker.worker_index'))
        return redirect(url_for('dashboard_org_admin.org_admin_index'))

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
            
            # Handle additional evidence file upload
            from werkzeug.utils import secure_filename
            from flask import current_app
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
# DUPLICATE EMISSION
# ============================================

@bp.route('/emission/<int:id>/duplicate')
@login_required
def duplicate_emission(id):
    """Redirect to new-emission wizard pre-filled with fields from an existing activity."""
    if current_user.role not in [UserRole.ORG_ADMIN, UserRole.WORKER] or not current_user.organization_id:
        flash('Access denied.', 'error')
        if current_user.role == UserRole.WORKER:
            return redirect(url_for('dashboard_worker.worker_index'))
        return redirect(url_for('dashboard_org_admin.org_admin_index'))

    activity = EmissionActivity.query.get_or_404(id)
    if activity.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.emissions'))

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
    if current_user.role == UserRole.WORKER:
        base_url = url_for('dashboard_worker.new_emission')
    else:
        base_url = url_for('dashboard_org_admin.new_emission')
        
    return redirect(f"{base_url}?{urlencode(params)}")


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
    page = request.args.get('page', 1, type=int)
    activities = (EmissionActivity.query
                  .filter_by(organization_id=org_id, status=ActivityStatus.SUBMITTED)
                  .order_by(EmissionActivity.created_at.desc())
                  .paginate(page=page, per_page=10, error_out=False))

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
    page = request.args.get('page', 1, type=int)
    activities = (EmissionActivity.query
                  .filter(
                      EmissionActivity.organization_id == org_id,
                      EmissionActivity.status.in_([ActivityStatus.VALIDATED, ActivityStatus.AUDITED])
                  )
                  .order_by(EmissionActivity.created_at.desc())
                  .paginate(page=page, per_page=10, error_out=False))

    # Calculate total co2 from the full unpaginated list 
    all_completed = EmissionActivity.query.filter(
        EmissionActivity.organization_id == org_id,
        EmissionActivity.status.in_([ActivityStatus.VALIDATED, ActivityStatus.AUDITED])
    ).all()
    total_t = sum((a.co2e_result or 0) for a in all_completed) / 1000

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


@bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
def change_user_role(user_id):
    """Change a user's role within the organization."""
    if not PermissionManager.is_org_admin(current_user, current_user.organization_id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    user = User.query.get_or_404(user_id)

    # Must be in same org
    if user.organization_id != current_user.organization_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    # Cannot change own role
    if user.id == current_user.id:
        flash("You cannot change your own role.", 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    # Platform Admins are untouchable — cannot be modified by any Org Admin
    if user.role == UserRole.PLATFORM_ADMIN:
        flash('Platform Administrators cannot be modified by Organization Admins.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    new_role_str = request.form.get('role', '').strip()
    
    # Restrict assigning protected roles
    blocked_roles = {'auditor', 'platform_admin', 'org_admin'}
    if new_role_str in blocked_roles:
        role_label = new_role_str.replace('_', ' ').title()
        flash(f'You cannot directly assign the "{role_label}" role. Use the appropriate workflow.', 'error')
        return redirect(url_for('dashboard_org_admin.users'))

    try:
        user.role = UserRole(new_role_str)
        db.session.commit()

        log = AuditLog(
            actor_id=current_user.id,
            organization_id=current_user.organization_id,
            action='CHANGE_USER_ROLE',
            entity_type='User',
            entity_id=user.id,
            details=f'Changed role of {user.email} to {new_role_str}.'
        )
        db.session.add(log)
        db.session.commit()

        flash(f'{user.email} role updated to {new_role_str.replace("_", " ").title()}.', 'success')
    except (ValueError, Exception) as e:
        flash(f'Invalid role: {str(e)}', 'error')

    return redirect(url_for('dashboard_org_admin.users'))
