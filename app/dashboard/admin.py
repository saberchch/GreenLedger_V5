from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.organization import Organization, OrganizationStatus
from app.models.report import Report, ReportStatus
from app.models.user import User, UserRole
from app.models.activity_message import ActivityMessage
from app.models.audit_log import AuditLog
from app.models.secure_message import SecureMessage, MessageChannel
from app.models.system_setting import SystemSetting
from datetime import datetime
import uuid
import hashlib
import json

bp = Blueprint(
    'dashboard_admin',
    __name__,
    url_prefix='/dashboard/admin'
)


def _require_admin():
    if not current_user.is_platform_admin:
        return redirect(url_for('main.index'))


# ─── Dashboard Index ─────────────────────────────────────────────────────────

@bp.route('/')
@login_required
def admin_index():
    _require_admin()
    pending_organizations = Organization.query.filter_by(status=OrganizationStatus.PENDING).all()
    audited_reports = Report.query.filter_by(status=ReportStatus.AUDITED).all()
    pending_audit_reports = Report.query.filter_by(status=ReportStatus.PENDING_AUDIT).all()

    total_users = User.query.filter(User.role != UserRole.BOT).count()
    total_orgs = Organization.query.count()
    active_orgs = Organization.query.filter_by(status=OrganizationStatus.ACTIVE).count()
    total_reports = Report.query.count()

    # Unread support messages
    unread_support = SecureMessage.query.filter_by(
        recipient_id=current_user.id,
        channel=MessageChannel.PREMIUM_SUPPORT,
        is_read=False
    ).count()

    return render_template(
        'pages/dashboard/admin/index.html',
        user=current_user,
        pending_organizations=pending_organizations,
        audited_reports=audited_reports,
        pending_audit_reports=pending_audit_reports,
        unread_support=unread_support,
        kpis={
            'total_users': total_users,
            'total_orgs': total_orgs,
            'active_orgs': active_orgs,
            'total_reports': total_reports,
            'pending_audit': len(pending_audit_reports),
        }
    )


# ─── Analytics ───────────────────────────────────────────────────────────────

@bp.route('/analytics')
@login_required
def analytics():
    """Platform-wide analytics visualization."""
    _require_admin()
    return render_template('pages/dashboard/admin/analytics.html')


# ─── Organization Management ─────────────────────────────────────────────────

@bp.route('/organization/<int:org_id>/approve', methods=['POST'])
@login_required
def approve_organization(org_id):
    _require_admin()
    org = Organization.query.get_or_404(org_id)
    org.status = OrganizationStatus.ACTIVE
    org.is_active = True
    db.session.commit()
    flash(f'Organization {org.name} approved successfully.', 'success')
    return redirect(url_for('dashboard_admin.admin_index'))


@bp.route('/organization/<int:org_id>/reject', methods=['POST'])
@login_required
def reject_organization(org_id):
    _require_admin()
    org = Organization.query.get_or_404(org_id)
    org.status = OrganizationStatus.REJECTED
    org.is_active = False
    db.session.commit()
    flash(f'Organization {org.name} rejected.', 'info')
    return redirect(url_for('dashboard_admin.admin_index'))


# ─── User Management ─────────────────────────────────────────────────────────

@bp.route('/users')
@login_required
def user_management():
    _require_admin()
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    search = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)

    query = User.query.filter(User.role != UserRole.BOT)

    if role_filter:
        try:
            query = query.filter_by(role=UserRole(role_filter))
        except ValueError:
            pass

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search:
        query = query.filter(
            (User.email.ilike(f'%{search}%')) |
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%'))
        )

    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=25, error_out=False)

    return render_template(
        'pages/dashboard/admin/users.html',
        users=users,
        role_filter=role_filter,
        status_filter=status_filter,
        search=search,
        UserRole=UserRole,
    )


@bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    _require_admin()
    user = User.query.get_or_404(user_id)

    if user.is_platform_admin:
        flash('Cannot modify a Platform Admin account.', 'error')
        return redirect(url_for('dashboard_admin.user_management'))

    user.status = 'inactive' if user.status == 'active' else 'active'
    db.session.commit()

    action = 'DEACTIVATE_USER' if user.status == 'inactive' else 'ACTIVATE_USER'
    log = AuditLog(
        actor_id=current_user.id,
        action=action,
        entity_type='User',
        entity_id=user.id,
        details=f'Admin {current_user.email} changed status of {user.email} to {user.status}.',
    )
    db.session.add(log)
    db.session.commit()

    flash(f'User {user.email} is now {user.status}.', 'success')
    return redirect(url_for('dashboard_admin.user_management'))


# ─── Auditor Management & Verification ───────────────────────────────────────

@bp.route('/auditors')
@login_required
def auditor_management():
    _require_admin()
    auditors = User.query.filter_by(role=UserRole.AUDITOR).order_by(User.is_verified.asc(), User.created_at.desc()).all()
    all_orgs = Organization.query.filter_by(status=OrganizationStatus.ACTIVE).order_by(Organization.name).all()

    return render_template(
        'pages/dashboard/admin/auditors.html',
        auditors=auditors,
        all_orgs=all_orgs,
    )


@bp.route('/auditor/<int:auditor_id>/verify', methods=['POST'])
@login_required
def verify_auditor(auditor_id):
    _require_admin()
    auditor = User.query.get_or_404(auditor_id)
    if auditor.role != UserRole.AUDITOR:
        flash('User is not an auditor.', 'error')
        return redirect(url_for('dashboard_admin.auditor_management'))

    auditor.is_verified = True
    log = AuditLog(
        actor_id=current_user.id,
        action='VERIFY_AUDITOR',
        entity_type='User',
        entity_id=auditor.id,
        details=f'Platform admin verified auditor {auditor.email}.',
    )
    db.session.add(log)
    db.session.commit()
    flash(f'Auditor {auditor.first_name} {auditor.last_name} has been verified ✓', 'success')
    return redirect(url_for('dashboard_admin.auditor_management'))


@bp.route('/auditor/<int:auditor_id>/revoke-verification', methods=['POST'])
@login_required
def revoke_auditor_verification(auditor_id):
    _require_admin()
    auditor = User.query.get_or_404(auditor_id)
    auditor.is_verified = False
    db.session.commit()
    flash(f'Verification for {auditor.first_name} {auditor.last_name} revoked.', 'warning')
    return redirect(url_for('dashboard_admin.auditor_management'))


@bp.route('/auditor/<int:auditor_id>')
@login_required
def auditor_profile(auditor_id):
    """Full auditor profile: credentials, stats, contracts, audit history, points."""
    _require_admin()
    from app.models.auditor_contract import AuditorContract
    from app.models.auditor_point_log import AuditorPointLog

    auditor = User.query.get_or_404(auditor_id)
    if auditor.role != UserRole.AUDITOR:
        flash('User is not an auditor.', 'error')
        return redirect(url_for('dashboard_admin.auditor_management'))

    contracts = (
        AuditorContract.query
        .filter_by(auditor_id=auditor_id)
        .order_by(AuditorContract.created_at.desc())
        .all()
    )
    point_log = (
        AuditorPointLog.query
        .filter_by(auditor_id=auditor_id)
        .order_by(AuditorPointLog.created_at.desc())
        .limit(30)
        .all()
    )
    audit_reports = (
        Report.query
        .filter_by(auditor_id=auditor_id)
        .order_by(Report.audit_finalized_at.desc())
        .all()
    )
    audit_logs = (
        AuditLog.query
        .filter_by(actor_id=auditor_id)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )
    # Load existing support thread between admin and this auditor
    thread_messages = (
        SecureMessage.query
        .filter(
            SecureMessage.channel == MessageChannel.PREMIUM_SUPPORT,
            ((SecureMessage.sender_id == current_user.id) & (SecureMessage.recipient_id == auditor_id)) |
            ((SecureMessage.sender_id == auditor_id) & (SecureMessage.recipient_id == current_user.id))
        )
        .order_by(SecureMessage.created_at.asc())
        .all()
    )
    # Mark incoming as read
    for msg in thread_messages:
        if msg.recipient_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()

    return render_template(
        'pages/dashboard/admin/auditor_profile.html',
        auditor=auditor,
        contracts=contracts,
        point_log=point_log,
        audit_reports=audit_reports,
        audit_logs=audit_logs,
        thread_messages=thread_messages,
    )


@bp.route('/auditor/<int:auditor_id>/message', methods=['POST'])
@login_required
def message_auditor(auditor_id):
    """Admin sends a direct PREMIUM_SUPPORT message to an auditor."""
    _require_admin()
    auditor = User.query.get_or_404(auditor_id)
    content = request.form.get('message', '').strip()
    if not content:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('dashboard_admin.auditor_profile', auditor_id=auditor_id))

    from app.security.encryption import EncryptionManager
    try:
        encrypted = EncryptionManager.encrypt(content)
    except Exception:
        encrypted = content

    msg = SecureMessage(
        sender_id=current_user.id,
        recipient_id=auditor_id,
        channel=MessageChannel.PREMIUM_SUPPORT,
        subject='Admin Request — Credentials',
        encrypted_content=encrypted,
    )
    db.session.add(msg)
    log = AuditLog(
        actor_id=current_user.id,
        action='ADMIN_MESSAGE_AUDITOR',
        entity_type='User',
        entity_id=auditor_id,
        details=f'Admin sent a direct message to auditor {auditor.email}.',
    )
    db.session.add(log)
    db.session.commit()
    flash('Message sent to auditor.', 'success')
    return redirect(url_for('dashboard_admin.auditor_profile', auditor_id=auditor_id))


# ─── Audit Sign-off Queue ────────────────────────────────────────────────────

@bp.route('/audit-queue')
@login_required
def audit_queue():
    """GreenLedger admin: list all reports awaiting platform sign-off."""
    _require_admin()
    page = request.args.get('page', 1, type=int)
    reports = (
        Report.query
        .filter_by(status=ReportStatus.PENDING_AUDIT)
        .order_by(Report.audit_finalized_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    notarized = (
        Report.query
        .filter_by(status=ReportStatus.NOTARIZED)
        .order_by(Report.platform_signed_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        'pages/dashboard/admin/audit_queue.html',
        reports=reports,
        notarized=notarized,
    )


@bp.route('/report/<int:report_id>/sign', methods=['POST'])
@login_required
def sign_report(report_id):
    """Platform admin sign-off: mark report as AUDITED."""
    _require_admin()
    report = Report.query.get_or_404(report_id)
    if report.status != ReportStatus.PENDING_AUDIT:
        flash('This report is not awaiting sign-off.', 'error')
        return redirect(url_for('dashboard_admin.audit_queue'))

    report.status = ReportStatus.AUDITED
    report.platform_signer_id = current_user.id
    report.platform_signed_at = datetime.utcnow()

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=report.organization_id,
        action='PLATFORM_SIGN_REPORT',
        entity_type='Report',
        entity_id=report.id,
        details=f'Platform admin signed audit report #{report.id}. Ready for blockchain notarization.',
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Report #{report.id} signed ✓ — ready for blockchain notarization.', 'success')
    return redirect(url_for('dashboard_admin.audit_queue'))


@bp.route('/report/<int:report_id>/notarize', methods=['POST'])
@login_required
def notarize_report(report_id):
    """Hash the report data and simulate blockchain notarization."""
    _require_admin()
    report = Report.query.get_or_404(report_id)

    if report.status != ReportStatus.AUDITED:
        return jsonify({'error': 'Report is not ready for notarization.'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing data.'}), 400

    # If a tx_hash was provided from UI (simulated), use it
    tx_hash = data.get('tx_hash')

    # Otherwise, generate a deterministic sha256 hash from the report's data
    if not tx_hash:
        report_payload = json.dumps({
            'id': report.id,
            'org_id': report.organization_id,
            'finalized_at': str(report.audit_finalized_at),
            'signer_id': report.platform_signer_id,
            'nonce': str(uuid.uuid4()),
        }, sort_keys=True)
        tx_hash = '0x' + hashlib.sha256(report_payload.encode()).hexdigest()

    report.status = ReportStatus.NOTARIZED
    report.blockchain_tx_hash = tx_hash

    log = AuditLog(
        actor_id=current_user.id,
        organization_id=report.organization_id,
        action='REPORT_NOTARIZED_ON_CHAIN',
        entity_type='Report',
        entity_id=report.id,
        details=f'Report notarized. TX: {report.blockchain_tx_hash}',
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'tx_hash': report.blockchain_tx_hash}), 200


# ─── Certification Management ────────────────────────────────────────────────

@bp.route('/certifications')
@login_required
def certification_management():
    _require_admin()
    from app.models.academy import Certificate
    page = request.args.get('page', 1, type=int)
    pending = Certificate.query.filter_by(status='PENDING', passed=True).order_by(Certificate.issued_at.desc()).paginate(page=page, per_page=20, error_out=False)
    notarized = Certificate.query.filter_by(status='NOTARIZED').order_by(Certificate.issued_at.desc()).limit(10).all()
    
    return render_template('pages/dashboard/admin/certifications.html', pending=pending, notarized=notarized)


@bp.route('/certificate/<int:cert_id>/notarize', methods=['POST'])
@login_required
def notarize_certificate(cert_id):
    _require_admin()
    from app.models.academy import Certificate
    from app.models.notification import Notification, NotificationType
    cert = Certificate.query.get_or_404(cert_id)
    
    if cert.status == 'NOTARIZED':
        flash('Certificate is already notarized.', 'info')
        return redirect(url_for('dashboard_admin.certification_management'))
        
    data = request.get_json() or {}
    tx_hash = data.get('tx_hash')
    if not tx_hash:
        import hashlib
        import uuid
        import json
        payload = json.dumps({'cert_id': cert.id, 'user_id': cert.user_id, 'nonce': str(uuid.uuid4())}, sort_keys=True)
        tx_hash = '0x' + hashlib.sha256(payload.encode()).hexdigest()
        
    cert.blockchain_tx = tx_hash
    cert.status = 'NOTARIZED'
    
    # Notify user
    notif = Notification(
        user_id=cert.user_id,
        title="Certificate Notarized on Blockchain",
        message=f"Congratulations! Your GreenLedger Academy certificate has been permanently notarized on the blockchain. TX Hash: {tx_hash}",
        type=NotificationType.SUCCESS,
        related_entity_type='certificate',
        related_entity_id=cert.id
    )
    db.session.add(notif)
    
    log = AuditLog(
        actor_id=current_user.id,
        action='CERTIFICATE_NOTARIZED',
        entity_type='Certificate',
        entity_id=cert.id,
        details=f'Admin notarized certificate for user {cert.user_id}. TX: {tx_hash}'
    )
    db.session.add(log)
    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True, 'tx_hash': tx_hash})
    
    flash(f'Certificate #{cert.id} notarized successfully.', 'success')
    return redirect(url_for('dashboard_admin.certification_management'))

# ─── Premium Support Channel ─────────────────────────────────────────────────

@bp.route('/support')
@login_required
def support_inbox():
    _require_admin()
    return redirect(url_for('dashboard_messages.inbox'))


@bp.route('/support/thread/<int:user_id>')
@login_required
def support_thread(user_id):
    _require_admin()
    return redirect(url_for('dashboard_messages.platform_support_chat', other_id=user_id))


@bp.route('/support/reply/<int:user_id>', methods=['POST'])
@login_required
def support_reply(user_id):
    _require_admin()
    # Redirect to the new reply handler
    return redirect(url_for('dashboard_messages.platform_support_reply', other_id=user_id), code=307)


# ─── System Logs ─────────────────────────────────────────────────────────────

@bp.route('/logs')
@login_required
def system_logs():
    _require_admin()
    action_filter = request.args.get('action', '')
    page = request.args.get('page', 1, type=int)

    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))

    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)

    all_actions = db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    all_actions = [a[0] for a in all_actions]

    return render_template(
        'pages/dashboard/admin/logs.html',
        logs=logs,
        action_filter=action_filter,
        all_actions=all_actions,
    )


# ─── Global Settings ─────────────────────────────────────────────────────────

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def global_settings():
    _require_admin()

    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key[len('setting_'):]
                setting = SystemSetting.query.filter_by(key=setting_key).first()
                if setting:
                    setting.value = value
                else:
                    setting = SystemSetting(key=setting_key, value=value)
                    db.session.add(setting)

        log = AuditLog(
            actor_id=current_user.id,
            action='UPDATE_GLOBAL_SETTINGS',
            entity_type='SystemSetting',
            details='Platform admin updated global settings.',
        )
        db.session.add(log)
        db.session.commit()
        flash('Settings saved successfully.', 'success')
        return redirect(url_for('dashboard_admin.global_settings'))

    # Seed default settings if none exist
    default_settings = [
        ('platform_name', 'GreenLedger', 'The public name of the platform.'),
        ('carbon_unit', 'tCO2e', 'Default carbon emission unit.'),
        ('max_org_workers', '50', 'Maximum number of workers per organization.'),
        ('require_auditor_verification', 'true', 'Require platform admin verification before auditors can work.'),
        ('support_email', 'support@greenledger.io', 'Email address for user support.'),
    ]
    for key, default_val, desc in default_settings:
        existing = SystemSetting.query.filter_by(key=key).first()
        if not existing:
            db.session.add(SystemSetting(key=key, value=default_val, description=desc))
    db.session.commit()

    settings = SystemSetting.query.order_by(SystemSetting.key).all()
    return render_template('pages/dashboard/admin/settings.html', settings=settings)


# ─── AI Bot Management ───────────────────────────────────────────────────────

@bp.route('/bot')
@login_required
def bot_management():
    """Read-only monitoring page for the platform AI Assistant."""
    _require_admin()
    
    # Identify the representative BOT user
    bot = User.query.filter_by(role=UserRole.BOT).first()
    
    # Calculate metrics (Total messages sent/received by the bot)
    total_messages = 0
    total_chars = 0
    recent_interactions = []
    
    if bot:
        # Message metrics from ActivityMessage (Regular Organization/Auditor chat)
        bot_msgs = ActivityMessage.query.filter_by(author_id=bot.id).all()
        total_messages += len(bot_msgs)
        total_chars += sum(len(m.message or '') for m in bot_msgs)
        
        # Message metrics from SecureMessage (Platform Support/Credential channel)
        # Note: SecureMessage content is encrypted, so we only count items.
        secure_bot_msgs = SecureMessage.query.filter_by(sender_id=bot.id).count()
        total_messages += secure_bot_msgs
        
        # Find unique users interacting with the bot
        interacted_users = db.session.query(ActivityMessage.recipient_auditor_id).distinct().filter(
            ActivityMessage.author_id != bot.id,
            ActivityMessage.recipient_auditor_id == bot.id
        ).count()
    else:
        interacted_users = 0

    # Automation Rules (Hardcoded for now as per current architectural state)
    automation_rules = [
        {'id': 1, 'name': 'Auto-Greeting', 'trigger': 'New User Message', 'action': 'Send Welcome & FAQ'},
        {'id': 2, 'name': 'Credential Request', 'trigger': 'Admin Platform Support', 'action': 'Request Verified Docs'},
        {'id': 3, 'name': 'Report Summary', 'trigger': 'Audit Finalized', 'action': 'Notify Org Admin'}
    ]

    return render_template(
        'pages/dashboard/admin/bot_monitoring.html',
        bot=bot,
        metrics={
            'total_messages': total_messages,
            'estimated_tokens': total_chars // 4,
            'interacted_users': interacted_users,
            'status': 'Online' if bot else 'Offline'
        },
        automation_rules=automation_rules,
        settings=SystemSetting.query.all()
    )


# ─── Smart Contracts (Placeholder) ───────────────────────────────────────────

@bp.route('/contracts')
@login_required
def smart_contracts():
    _require_admin()
    return render_template('pages/dashboard/coming_soon.html', user=current_user)