from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.report import Report, ReportStatus
from app.models.emission_activity import EmissionActivity, ActivityStatus
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.models.notification import Notification, NotificationType
from app.models.organization import Organization
from app.models.auditor_contract import AuditorContract, ContractStatus, AuditorType
from app.models.auditor_point_log import AuditorPointLog
from datetime import datetime

bp = Blueprint(
    'dashboard_auditor',
    __name__,
    url_prefix='/dashboard/auditor'
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _require_auditor():
    if not current_user.has_role('auditor'):
        abort(403)


def _get_contract_for_auditor(org_id):
    """Return the active/trial contract between current auditor and an org, or None."""
    return AuditorContract.query.filter(
        AuditorContract.organization_id == org_id,
        AuditorContract.auditor_id == current_user.id,
        AuditorContract.status.in_([ContractStatus.TRIAL, ContractStatus.ACTIVE])
    ).first()


def _org_for_auditor(org_id):
    """
    Return Org if this auditor has an active/trial contract with it.
    Platform admins always pass.
    """
    org = Organization.query.get_or_404(org_id)
    if current_user.has_role('admin'):
        return org
    if _get_contract_for_auditor(org_id):
        return org
    abort(403)


def _require_primary_auditor(org_id):
    """Abort 403 unless the current user is the PRIMARY auditor for the org."""
    if current_user.has_role('admin'):
        return
    contract = _get_contract_for_auditor(org_id)
    if not contract or contract.auditor_type != AuditorType.PRIMARY:
        flash('This action is restricted to the Primary Auditor for this organization.', 'error')
        abort(403)


def _require_collateral_auditor(org_id):
    """Abort 403 unless the current user is the COLLATERAL auditor for the org."""
    if current_user.has_role('admin'):
        return
    contract = _get_contract_for_auditor(org_id)
    if not contract or contract.auditor_type != AuditorType.COLLATERAL:
        flash('This action is restricted to the Collateral Auditor for this organization.', 'error')
        abort(403)


def _apply_point_delta(auditor, delta, reason, org=None, contract=None):
    """Apply a reputation score change and log it."""
    auditor.reputation_score = max(0, (auditor.reputation_score or 100) + delta)
    log = AuditorPointLog(
        auditor_id=auditor.id,
        organization_id=org.id if org else None,
        contract_id=contract.id if contract else None,
        delta=delta,
        reason=reason,
    )
    db.session.add(log)


# ─── Dashboard home ──────────────────────────────────────────────────────────

@bp.route('/')
@login_required
def auditor_index():
    """Auditor landing — role-aware view of contracts, queues, and deadlines."""
    _require_auditor()

    # All contracts for this auditor
    all_contracts = AuditorContract.query.filter_by(
        auditor_id=current_user.id
    ).order_by(AuditorContract.created_at.desc()).all()

    pending_contracts = [c for c in all_contracts if c.status == ContractStatus.PENDING]
    active_contracts  = [c for c in all_contracts if c.status in (ContractStatus.TRIAL, ContractStatus.ACTIVE)]

    # Upcoming deadlines for the quick-action panel
    deadlines = []
    for c in active_contracts:
        if c.status == ContractStatus.TRIAL and c.trial_end:
            deadlines.append({
                'label': f'Trial ends — {c.organization.name}',
                'date':  c.trial_end,
                'days':  c.trial_days_remaining(),
                'color': 'amber',
                'org_id': c.organization_id,
            })
        if c.contract_end:
            days_left = c.days_remaining()
            if days_left is not None and days_left <= 60:
                deadlines.append({
                    'label': f'Contract expires — {c.organization.name}',
                    'date':  c.contract_end,
                    'days':  days_left,
                    'color': 'red' if days_left <= 30 else 'orange',
                    'org_id': c.organization_id,
                })
    deadlines.sort(key=lambda d: d['days'] if d['days'] is not None else 9999)

    # Per-org data split by role
    primary_orgs    = []   # auditor is PRIMARY → shows activity review queue
    collateral_orgs = []   # auditor is COLLATERAL → shows countersign queue + backup review queue

    for contract in active_contracts:
        org = contract.organization

        # Pre-fetch the org admin user for message routing
        org_admin_user = User.query.filter_by(
            organization_id=org.id, role=UserRole.ORG_ADMIN
        ).first()

        base = EmissionActivity.query.filter_by(organization_id=org.id)
        kpis = {
            'pending_review':  base.filter_by(status=ActivityStatus.SUBMITTED).count(),
            'proof_requested': base.filter(
                EmissionActivity.proof_requested == True,
                EmissionActivity.status == ActivityStatus.SUBMITTED
            ).count(),
            'validated': base.filter_by(status=ActivityStatus.VALIDATED).count(),
            'rejected':  base.filter_by(status=ActivityStatus.REJECTED).count(),
        }

        if contract.auditor_type == AuditorType.PRIMARY:
            primary_orgs.append({
                'contract': contract,
                'org': org,
                'org_admin_user': org_admin_user,
                'kpis': kpis,
                'pending_reports': Report.query.filter_by(
                    organization_id=org.id, status=ReportStatus.PENDING_AUDIT
                ).all(),
                'completed_reports': Report.query.filter(
                    Report.organization_id == org.id,
                    Report.status.in_([
                        ReportStatus.PENDING_COLLATERAL_REVIEW, 
                        ReportStatus.PENDING_AUDIT, 
                        ReportStatus.AUDITED, 
                        ReportStatus.NOTARIZED
                    ])
                ).count(),
            })
        else:  # COLLATERAL
            # Check if primary auditor contract exists and is active/trial
            primary_contract = AuditorContract.query.filter(
                AuditorContract.organization_id == org.id,
                AuditorContract.auditor_type == AuditorType.PRIMARY,
                AuditorContract.status.in_([ContractStatus.TRIAL, ContractStatus.ACTIVE])
            ).first()

            # Collateral can review queue if no primary is active (stepped-up scenario)
            primary_defaulted = primary_contract is None

            pending_countersign = Report.query.filter_by(
                organization_id=org.id,
                status=ReportStatus.PENDING_COLLATERAL_REVIEW
            ).all()

            collateral_orgs.append({
                'contract': contract,
                'org': org,
                'org_admin_user': org_admin_user,
                'kpis': kpis,
                'pending_countersign': pending_countersign,
                'primary_defaulted': primary_defaulted,  # True → show full review queue
                'primary_contract': primary_contract,
            })

    reputation_label, reputation_color = current_user.reputation_label

    # Unread message count
    from app.models.activity_message import ActivityMessage
    unread_dm_count = ActivityMessage.query.filter(
        ActivityMessage.recipient_auditor_id == current_user.id,
        ActivityMessage.activity_id == None,
    ).count()

    return render_template(
        'pages/dashboard/auditor/index.html',
        user=current_user,
        primary_orgs=primary_orgs,
        collateral_orgs=collateral_orgs,
        pending_contracts=pending_contracts,
        all_contracts=all_contracts,
        deadlines=deadlines,
        unread_dm_count=unread_dm_count,
        reputation_label=reputation_label,
        reputation_color=reputation_color,
    )




# ─── Contract Management ─────────────────────────────────────────────────────

@bp.route('/contract/<int:contract_id>/accept', methods=['POST'])
@login_required
def accept_contract(contract_id):
    _require_auditor()
    contract = AuditorContract.query.get_or_404(contract_id)

    if contract.auditor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    if contract.status != ContractStatus.PENDING:
        flash('This contract proposal has already been processed.', 'warning')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    # Activate the contract (sets TRIAL status + timestamps)
    contract.activate()

    # Update the org's primary/collateral slot
    org = contract.organization
    if contract.auditor_type == AuditorType.PRIMARY:
        org.primary_auditor_id = current_user.id
    else:
        org.collateral_auditor_id = current_user.id

    # Also add to legacy M2M for backward compat
    if org not in current_user.audited_organizations:
        current_user.audited_organizations.append(org)

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=org.id,
        action='ACCEPT_AUDITOR_CONTRACT',
        entity_type='AuditorContract',
        entity_id=contract.id,
        details=f'Auditor accepted {contract.auditor_type.value} contract. Trial ends {contract.trial_end.date()}.',
    )
    db.session.add(log)

    notif = Notification(
        user_id=next((u.id for u in org.users if u.role == UserRole.ORG_ADMIN), None),
        title='Auditor Accepted Contract',
        message=f'{current_user.first_name} {current_user.last_name} accepted your {contract.auditor_type.value} auditor contract. Trial period begins today.',
        type=NotificationType.SUCCESS,
        related_entity_type='auditor_contract',
    ) if org.users.filter_by(role=UserRole.ORG_ADMIN).first() else None
    if notif:
        db.session.add(notif)

    db.session.commit()
    flash(f'Contract accepted! You are now in a 30-day trial as {contract.auditor_type.value} auditor for {org.name}.', 'success')
    return redirect(url_for('dashboard_auditor.auditor_index'))


@bp.route('/contract/<int:contract_id>/reject', methods=['POST'])
@login_required
def reject_contract(contract_id):
    _require_auditor()
    contract = AuditorContract.query.get_or_404(contract_id)

    if contract.auditor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    if contract.status != ContractStatus.PENDING:
        flash('This contract proposal has already been processed.', 'warning')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    contract.status = ContractStatus.CANCELLED

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=contract.organization_id,
        action='REJECT_AUDITOR_CONTRACT',
        entity_type='AuditorContract',
        entity_id=contract.id,
        details=f'Auditor rejected contract proposal from {contract.organization.name}.',
    )
    db.session.add(log)
    db.session.commit()

    flash(f'You have declined the contract from {contract.organization.name}.', 'info')
    return redirect(url_for('dashboard_auditor.auditor_index'))


# ─── Monthly Audit Submission ─────────────────────────────────────────────────

@bp.route('/contract/<int:contract_id>/submit-monthly', methods=['POST'])
@login_required
def submit_monthly_audit(contract_id):
    """Auditor confirms they have reviewed all emissions for the month."""
    _require_auditor()
    contract = AuditorContract.query.get_or_404(contract_id)

    if contract.auditor_id != current_user.id:
        abort(403)

    if contract.status not in (ContractStatus.TRIAL, ContractStatus.ACTIVE):
        flash('No active contract to submit audit for.', 'warning')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    org = contract.organization
    note = request.form.get('audit_note', '').strip()

    # Check if there are still unreviewed emissions
    unreviewed = EmissionActivity.query.filter_by(
        organization_id=org.id, status=ActivityStatus.SUBMITTED
    ).count()

    if unreviewed > 0:
        flash(f'There are still {unreviewed} unreviewed emissions. Please review all before submitting monthly audit.', 'warning')
        return redirect(url_for('dashboard_auditor.review_queue', org_id=org.id))

    # --- Trial → Active promotion check ---
    if contract.status == ContractStatus.TRIAL and contract.trial_end and datetime.utcnow() >= contract.trial_end:
        contract.status = ContractStatus.ACTIVE
        flash(f'🎉 Trial period passed! You are now the full {contract.auditor_type.value} auditor for {org.name}.', 'success')

    contract.last_audit_submitted_at = datetime.utcnow()

    # +5 bonus points for on-time monthly audit
    _apply_point_delta(current_user, +5,
                       f'Monthly audit submitted on time for {org.name}.',
                       org=org, contract=contract)

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=org.id,
        action='MONTHLY_AUDIT_SUBMITTED',
        entity_type='AuditorContract',
        entity_id=contract.id,
        details=f'Monthly audit submitted. Note: {note or "—"}',
    )
    db.session.add(log)
    db.session.commit()

    flash('Monthly audit report submitted successfully. +5 reputation points.', 'success')
    return redirect(url_for('dashboard_auditor.auditor_index'))


# ─── Mark Missed Audit (admin helper / CRON-triggered) ───────────────────────

@bp.route('/contract/<int:contract_id>/mark-missed', methods=['POST'])
@login_required
def mark_missed_audit(contract_id):
    """
    Mark a missed monthly audit. Can be triggered by platform admin or a scheduled job.
    Trial failure → DISCARDED (-50 pts). Active miss → -20 pts.
    """
    if not current_user.has_role('admin') and not current_user.has_role('auditor'):
        abort(403)

    contract = AuditorContract.query.get_or_404(contract_id)
    auditor  = contract.auditor
    org      = contract.organization

    if contract.status == ContractStatus.TRIAL:
        # Trial failure → discard
        contract.status = ContractStatus.DISCARDED
        contract.missed_months = (contract.missed_months or 0) + 1

        if org.primary_auditor_id == auditor.id:
            org.primary_auditor_id = None
        if org.collateral_auditor_id == auditor.id:
            org.collateral_auditor_id = None

        _apply_point_delta(auditor, -50,
                           f'Failed trial audit duty for {org.name}. Contract discarded.',
                           org=org, contract=contract)

        # Notify org admins
        for admin in org.users.filter_by(role=UserRole.ORG_ADMIN):
            db.session.add(Notification(
                user_id=admin.id,
                title='Auditor Discarded — Trial Failure',
                message=f'{auditor.first_name} {auditor.last_name} failed the trial audit duty and has been removed.',
                type=NotificationType.ERROR,
                related_entity_type='auditor_contract',
            ))
        flash(f'Trial failure recorded. {auditor.email} discarded (-50 pts).', 'warning')

    elif contract.status == ContractStatus.ACTIVE:
        contract.missed_months = (contract.missed_months or 0) + 1
        _apply_point_delta(auditor, -20,
                           f'Missed monthly audit for {org.name}. Month missed: {contract.missed_months}.',
                           org=org, contract=contract)
        flash(f'Missed audit recorded for {auditor.email} (-20 pts).', 'warning')
    else:
        flash('Contract is not in an active state.', 'info')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=org.id,
        action='MISSED_MONTHLY_AUDIT',
        entity_type='AuditorContract',
        entity_id=contract.id,
        details=f'Missed audit recorded. Status: {contract.status.value}. Auditor score now {auditor.reputation_score}.',
    )
    db.session.add(log)
    db.session.commit()
    return redirect(url_for('dashboard_auditor.auditor_index'))


# ─── Reputation Page ─────────────────────────────────────────────────────────

@bp.route('/reputation')
@login_required
def reputation():
    _require_auditor()
    logs = AuditorPointLog.query.filter_by(
        auditor_id=current_user.id
    ).order_by(AuditorPointLog.created_at.desc()).all()

    contracts = AuditorContract.query.filter_by(
        auditor_id=current_user.id
    ).order_by(AuditorContract.created_at.desc()).all()

    reputation_label, reputation_color = current_user.reputation_label
    return render_template(
        'pages/dashboard/auditor/reputation.html',
        user=current_user,
        point_logs=logs,
        contracts=contracts,
        reputation_label=reputation_label,
        reputation_color=reputation_color,
    )


@bp.route('/org/<int:org_id>/analytics')
@login_required
def analytics(org_id):
    """Detailed standalone analytics page for a specific organization."""
    _require_auditor()
    org = _org_for_auditor(org_id)
    return render_template('pages/dashboard/auditor/analytics.html', organization=org)


# ─── Review Queue ────────────────────────────────────────────────────────────

@bp.route('/org/<int:org_id>/review')
@login_required
def review_queue(org_id):
    _require_auditor()
    org = _org_for_auditor(org_id)

    status_filter = request.args.get('status', 'submitted')
    try:
        status_enum = ActivityStatus(status_filter)
    except ValueError:
        status_enum = ActivityStatus.SUBMITTED

    page = request.args.get('page', 1, type=int)
    activities = (
        EmissionActivity.query
        .filter_by(organization_id=org_id, status=status_enum)
        .order_by(EmissionActivity.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )

    counts = {}
    for s in ActivityStatus:
        counts[s.value] = EmissionActivity.query.filter_by(
            organization_id=org_id, status=s
        ).count()

    # Active contract for this org
    contract = AuditorContract.query.filter(
        AuditorContract.organization_id == org_id,
        AuditorContract.auditor_id == current_user.id,
        AuditorContract.status.in_([ContractStatus.TRIAL, ContractStatus.ACTIVE])
    ).first()

    return render_template(
        'pages/dashboard/auditor/review_queue.html',
        user=current_user,
        org=org,
        contract=contract,
        activities=activities,
        current_status=status_filter,
        counts=counts,
    )


# ─── Emission Detail ─────────────────────────────────────────────────────────

@bp.route('/emission/<int:id>')
@login_required
def emission_detail(id):
    _require_auditor()
    activity = EmissionActivity.query.get_or_404(id)
    _org_for_auditor(activity.organization_id)

    documents = Document.query.filter_by(activity_id=id).all()
    audit_logs = (
        AuditLog.query
        .filter_by(entity_type='EmissionActivity', entity_id=id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    # Messages on this activity (read-only for auditors)
    from app.models.activity_message import ActivityMessage
    messages = ActivityMessage.query.filter_by(activity_id=id).order_by(ActivityMessage.created_at.asc()).all()

    return render_template(
        'pages/dashboard/auditor/emission_detail.html',
        user=current_user,
        activity=activity,
        documents=documents,
        audit_logs=audit_logs,
        messages=messages,
    )


# ─── Approve ────────────────────────────────────────────────────────────────

@bp.route('/emission/<int:id>/approve', methods=['POST'])
@login_required
def approve_emission(id):
    _require_auditor()
    activity = EmissionActivity.query.get_or_404(id)
    _org_for_auditor(activity.organization_id)

    note = request.form.get('auditor_notes', '').strip()
    activity.status = ActivityStatus.VALIDATED
    activity.auditor_notes = note or None
    activity.proof_requested = False
    activity.audited_by_id = current_user.id

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=activity.organization_id,
        action='AUDITOR_APPROVE',
        entity_type='EmissionActivity',
        entity_id=activity.id,
        details=f'Auditor approved emission #{activity.id}.' + (f' Note: {note}' if note else ''),
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Emission #{activity.id} validated ✓', 'success')
    return redirect(url_for('dashboard_auditor.review_queue', org_id=activity.organization_id, status='submitted'))


# ─── Reject ─────────────────────────────────────────────────────────────────

@bp.route('/emission/<int:id>/reject', methods=['POST'])
@login_required
def reject_emission(id):
    _require_auditor()
    activity = EmissionActivity.query.get_or_404(id)
    _org_for_auditor(activity.organization_id)

    reason = request.form.get('rejection_reason', '').strip()
    if not reason:
        flash('Please provide a rejection reason.', 'error')
        return redirect(url_for('dashboard_auditor.emission_detail', id=id))

    activity.status = ActivityStatus.REJECTED
    activity.rejection_reason = reason
    activity.auditor_notes = reason
    activity.proof_requested = False
    activity.audited_by_id = current_user.id

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=activity.organization_id,
        action='AUDITOR_REJECT',
        entity_type='EmissionActivity',
        entity_id=activity.id,
        details=f'Auditor rejected emission #{activity.id}. Reason: {reason}',
    )
    db.session.add(log)

    if activity.created_by_id:
        db.session.add(Notification(
            user_id=activity.created_by_id,
            title='Emission Data Rejected',
            message=f'Auditor rejected your emission activity #{activity.id}. Reason: {reason}',
            type=NotificationType.ERROR,
            related_entity_type='emission_activity',
            related_entity_id=activity.id
        ))

    for admin in User.query.filter_by(organization_id=activity.organization_id, role=UserRole.ORG_ADMIN):
        db.session.add(Notification(
            user_id=admin.id,
            title='Emission Data Rejected',
            message=f'Auditor rejected emission #{activity.id}. Reason: {reason}',
            type=NotificationType.ERROR,
            related_entity_type='emission_activity',
            related_entity_id=activity.id
        ))

    db.session.commit()
    flash(f'Emission #{activity.id} rejected.', 'warning')
    return redirect(url_for('dashboard_auditor.review_queue', org_id=activity.organization_id, status='submitted'))


# ─── Request Proof ───────────────────────────────────────────────────────────

@bp.route('/emission/<int:id>/request-proof', methods=['POST'])
@login_required
def request_proof(id):
    _require_auditor()
    activity = EmissionActivity.query.get_or_404(id)
    _org_for_auditor(activity.organization_id)

    note = request.form.get('auditor_notes', '').strip()
    if not note:
        flash('Please describe what evidence is required.', 'error')
        return redirect(url_for('dashboard_auditor.emission_detail', id=id))

    activity.proof_requested = True
    activity.auditor_notes = note
    activity.audited_by_id = current_user.id

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=activity.organization_id,
        action='AUDITOR_REQUEST_PROOF',
        entity_type='EmissionActivity',
        entity_id=activity.id,
        details=f'Proof requested for emission #{activity.id}: {note}',
    )
    db.session.add(log)

    if activity.created_by_id:
        db.session.add(Notification(
            user_id=activity.created_by_id,
            title='Proof Requested',
            message=f'Auditor requested proof for emission #{activity.id}. Note: {note}',
            type=NotificationType.WARNING,
            related_entity_type='emission_activity',
            related_entity_id=activity.id
        ))

    for admin in User.query.filter_by(organization_id=activity.organization_id, role=UserRole.ORG_ADMIN):
        db.session.add(Notification(
            user_id=admin.id,
            title='Proof Requested',
            message=f'Auditor requested proof for emission #{activity.id}. Note: {note}',
            type=NotificationType.WARNING,
            related_entity_type='emission_activity',
            related_entity_id=activity.id
        ))

    db.session.commit()
    flash(f'Proof request sent for emission #{activity.id}.', 'info')
    return redirect(url_for('dashboard_auditor.review_queue', org_id=activity.organization_id, status='submitted'))


# ─── Finalize Audit (PRIMARY only) ───────────────────────────────────────────────

@bp.route('/org/<int:org_id>/finalize', methods=['GET', 'POST'])
@login_required
def finalize_audit(org_id):
    _require_auditor()
    org = _org_for_auditor(org_id)
    _require_primary_auditor(org_id)

    validated_activities = (
        EmissionActivity.query
        .filter_by(organization_id=org_id, status=ActivityStatus.VALIDATED)
        .order_by(EmissionActivity.scope)
        .all()
    )

    scope_totals = {'Scope 1': 0.0, 'Scope 2': 0.0, 'Scope 3': 0.0}
    total_kg = 0.0
    for a in validated_activities:
        kg = a.co2e_result or 0.0
        total_kg += kg
        scope_totals[a.scope.value] = scope_totals.get(a.scope.value, 0.0) + kg

    if request.method == 'POST':
        period_label    = request.form.get('period_label', '').strip()
        period_type     = request.form.get('period_type', '').strip()
        audit_notes     = request.form.get('audit_notes', '').strip()
        recommendations = request.form.get('recommendations', '').strip()

        if not validated_activities:
            flash('No validated activities to include in the audit report.', 'error')
            return redirect(url_for('dashboard_auditor.finalize_audit', org_id=org_id))

        summary_lines = [f"Audit Report — {org.name} — {period_label}"]
        for scope, kg in scope_totals.items():
            summary_lines.append(f"  {scope}: {kg/1000:.4f} tCO₂e")
        summary_lines.append(f"  Total: {total_kg/1000:.4f} tCO₂e")

        # Check if a collateral auditor is engaged for this org
        collateral_contract = AuditorContract.query.filter(
            AuditorContract.organization_id == org_id,
            AuditorContract.auditor_type  == AuditorType.COLLATERAL,
            AuditorContract.status.in_([ContractStatus.TRIAL, ContractStatus.ACTIVE])
        ).first()

        # If collateral exists, route for countersignature first; else go straight to admin
        initial_status = (
            ReportStatus.PENDING_COLLATERAL_REVIEW if collateral_contract
            else ReportStatus.PENDING_AUDIT
        )

        report = Report(
            summary='\n'.join(summary_lines),
            status=initial_status,
            organization_id=org_id,
            auditor_id=current_user.id,
            created_by_id=current_user.id,
            period_label=period_label,
            period_type=period_type or None,
            total_co2e_kg=total_kg,
            audit_notes=audit_notes or None,
            recommendations=recommendations or None,
            audit_finalized_at=datetime.utcnow(),
        )
        db.session.add(report)

        for a in validated_activities:
            a.status = ActivityStatus.AUDITED

        action_label = (
            'AUDIT_FINALIZED_PENDING_COLLATERAL'
            if collateral_contract else 'AUDIT_FINALIZED'
        )
        log = AuditLog(
            actor_id=current_user.id,
            organization_id=org_id,
            action=action_label,
            entity_type='Organization',
            entity_id=org_id,
            details=f'Primary auditor finalized report. {len(validated_activities)} activities locked. Total: {total_kg/1000:.4f} tCO₂e.',
        )
        db.session.add(log)

        # Notify collateral auditor if applicable
        if collateral_contract:
            db.session.add(Notification(
                user_id=collateral_contract.auditor_id,
                title='Report awaiting your countersignature',
                message=f'Primary auditor has finalized an audit report for {org.name}. Please review and countersign.',
                type=NotificationType.WARNING,
                related_entity_type='report',
                related_entity_id=report.id
            ))

        db.session.commit()

        if collateral_contract:
            flash(f'Audit report created. Awaiting collateral auditor countersignature before GreenLedger review. Report #{report.id}', 'success')
        else:
            flash(f'Audit report created and sent directly to GreenLedger for sign-off. Report #{report.id}', 'success')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    return render_template(
        'pages/dashboard/auditor/finalize_audit.html',
        user=current_user,
        org=org,
        validated_activities=validated_activities,
        scope_totals=scope_totals,
        total_kg=total_kg,
    )


# ─── Countersign Report (COLLATERAL only) ──────────────────────────────────────────

@bp.route('/report/<int:report_id>/countersign', methods=['POST'])
@login_required
def countersign_report(report_id):
    """Collateral auditor countersigns a finalized report, advancing it to GreenLedger review."""
    _require_auditor()
    report = Report.query.get_or_404(report_id)

    if report.status != ReportStatus.PENDING_COLLATERAL_REVIEW:
        flash('This report is not awaiting a collateral countersignature.', 'error')
        return redirect(url_for('dashboard_auditor.auditor_index'))

    _require_collateral_auditor(report.organization_id)

    notes = request.form.get('collateral_notes', '').strip()
    report.status               = ReportStatus.PENDING_AUDIT
    report.collateral_signer_id = current_user.id
    report.collateral_signed_at = datetime.utcnow()
    report.collateral_notes     = notes or None

    # +3 rep for timely countersignature
    _apply_point_delta(
        current_user, +3,
        f'Countersigned audit report #{report.id} for {report.organization.name}.',
        org=report.organization,
    )

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=report.organization_id,
        action='COLLATERAL_COUNTERSIGN',
        entity_type='Report',
        entity_id=report.id,
        details=f'Collateral auditor countersigned report #{report.id}. Forwarded to GreenLedger admin.'
                + (f' Note: {notes}' if notes else ''),
    )
    db.session.add(log)

    # Notify the primary auditor
    if report.auditor_id:
        db.session.add(Notification(
            user_id=report.auditor_id,
            title='Report countersigned',
            message=f'Collateral auditor countersigned report #{report.id} for {report.organization.name}. It is now with GreenLedger admin.',
            type=NotificationType.SUCCESS,
            related_entity_type='report',
            related_entity_id=report.id
        ))

    db.session.commit()
    flash(f'Report #{report.id} countersigned ✓ — forwarded to GreenLedger admin for final sign-off.', 'success')
    return redirect(url_for('dashboard_auditor.auditor_index'))


# ─── Legacy / placeholder routes ─────────────────────────────────────────────

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


@bp.route('/report/<int:report_id>/sign', methods=['POST'])
@login_required
def sign_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.status = ReportStatus.AUDITED
    report.auditor_id = current_user.id
    db.session.commit()
    flash(f'Report #{report.id} signed.', 'success')
    return redirect(url_for('dashboard_auditor.auditor_index'))
