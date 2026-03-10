"""
Auditor ↔ Organisation direct messaging — dashboard pages.

These are thin server-rendered pages.  All actual message data is stored in
the existing ActivityMessage table and served through the existing
/api/v1/messages/auditor/<id>/org/<id> REST endpoints that the page JS calls.

No contract required — either party can start the conversation at any time.
"""
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.extensions import db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.secure_message import SecureMessage, MessageChannel

bp = Blueprint('dashboard_messages', __name__, url_prefix='/dashboard/messages')


@bp.route('/')
@login_required
def inbox():
    """
    Unified Inbox — Shows active conversations (via JS) and Categorized Directory for new ones.
    """
    if current_user.role not in (UserRole.AUDITOR, UserRole.ORG_ADMIN,
                                  UserRole.WORKER, UserRole.VIEWER, UserRole.PLATFORM_ADMIN):
        flash('Messaging is not available for your role.', 'error')
        return redirect(url_for('main.index'))

    from app.models.organization import OrganizationStatus
    
    # 1. Start Categorized Reachability
    directory = {
        'support': [],
        'ai': [],
        'auditors': [],
        'organisations': []
    }

    # AI Assistant (Always available to everyone except itself)
    ai_bot = User.query.filter_by(role=UserRole.BOT).first()
    if ai_bot and ai_bot.id != current_user.id:
        directory['ai'].append(ai_bot)

    # Platform Support (Available to everyone EXCEPT Platform Admins)
    if not current_user.is_platform_admin:
        admin = User.query.filter_by(role=UserRole.PLATFORM_ADMIN).first()
        if admin:
            directory['support'].append(admin)

    # Professional Contacts based on role
    if current_user.is_platform_admin:
        # Admins can reach all verified auditors and org admins
        directory['auditors'] = User.query.filter_by(role=UserRole.AUDITOR).all()
        # Find all active organization admins
        directory['organisations'] = User.query.join(Organization, User.organization_id == Organization.id).filter(
            Organization.status == OrganizationStatus.ACTIVE,
            User.role == UserRole.ORG_ADMIN
        ).all()
    
    elif current_user.role == UserRole.AUDITOR:
        # Auditors can reach all active organization admins
        directory['organisations'] = User.query.join(Organization, User.organization_id == Organization.id).filter(
            Organization.status == OrganizationStatus.ACTIVE,
            User.role == UserRole.ORG_ADMIN
        ).all()
        
    else:
        # Organization members (Worker, Viewer, Org Admin) can reach all platform auditors
        directory['auditors'] = User.query.filter_by(role=UserRole.AUDITOR).all()

    # CRITICAL: Prevent self-messaging in all categories
    for cat in directory:
        directory[cat] = [u for u in directory[cat] if u.id != current_user.id]

    return render_template(
        'pages/dashboard/messages/inbox.html',
        directory=directory,
    )


@bp.route('/chat/<int:other_id>')
@login_required
def chat(other_id):
    """
    Chat page between the current user and another user.
    Both sides (auditor or org member) land here.
    The actual messages are loaded asynchronously by the frontend JS
    from /api/v1/messages/auditor/<auditor_id>/org/<org_id>.
    """
    other = User.query.get_or_404(other_id)

    # ─── AI Bot: Check FIRST before any role-based routing ────────────────────
    if other.role == UserRole.BOT:
        # Use the current user's OWN ID as the "virtual org" key for the AI channel.
        # This gives every user (worker, org admin, auditor) their own PRIVATE AI thread.
        # SQLite doesn't enforce FK constraints, so this is safe.
        auditor_id = other.id
        org_id = current_user.id  # Personal channel — not shared with org members!
    # ─── Standard role-based routing ──────────────────────────────────────────
    elif current_user.role == UserRole.AUDITOR and other.role != UserRole.AUDITOR:
        auditor_id = current_user.id
        org_id = other.organization_id
    elif current_user.role != UserRole.AUDITOR and other.role == UserRole.AUDITOR:
        auditor_id = other_id
        org_id = current_user.organization_id
    else:
        abort(400)  # auditor↔auditor or same-side chat not supported here

    # Only enforce org presence for standard (non-bot) conversations
    if not org_id and other.role != UserRole.BOT:
        flash('Organisation not found.', 'error')
        return redirect(url_for('dashboard_messages.inbox'))

    api_url = url_for('api_messages.get_auditor_org_messages',
                      auditor_id=auditor_id, org_id=org_id or 0)
    post_url = url_for('api_messages.post_auditor_org_message',
                       auditor_id=auditor_id, org_id=org_id or 0)

    org = Organization.query.get(org_id) if org_id else None

    return render_template(
        'pages/dashboard/messages/chat.html',
        other=other,
        org=org,
        api_url=api_url,
        post_url=post_url,
        current_user_id=current_user.id,
        current_user_name=(f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email),
    )


@bp.route('/unread-count')
@login_required
def unread_count():
    """Stub — unread count via the existing ActivityMessage system."""
    from flask import jsonify
    return jsonify({'unread': 0})
@bp.route('/platform-support')
@bp.route('/platform-support/<int:other_id>')
@login_required
def platform_support_chat(other_id=None):
    """
    Unified support thread view.
    If Admin: other_id is required (the user requesting support).
    If User: other_id is optional (defaults to the Platform Admin).
    """
    admin = User.query.filter_by(role=UserRole.PLATFORM_ADMIN).first()
    
    if current_user.is_platform_admin:
        if not other_id:
            # Admins without an ID are sent back to the main hub list
            return redirect(url_for('dashboard_messages.inbox'))
        other = User.query.get_or_404(other_id)
        # Verify we aren't chatting with ourselves
        if other.id == current_user.id:
            flash('You cannot message yourself.', 'error')
            return redirect(url_for('dashboard_messages.inbox'))
    else:
        # Regular user: other is the admin
        other = admin
        if not other:
            flash('Platform Support is currently unavailable.', 'error')
            return redirect(url_for('dashboard_messages.inbox'))

    # Fetch messages between current_user and other
    messages = (
        SecureMessage.query
        .filter(
            SecureMessage.channel == MessageChannel.PREMIUM_SUPPORT,
            ((SecureMessage.sender_id == current_user.id) & (SecureMessage.recipient_id == other.id)) |
            ((SecureMessage.recipient_id == current_user.id) & (SecureMessage.sender_id == other.id))
        )
        .order_by(SecureMessage.created_at.asc())
        .all()
    )

    # Mark incoming as read
    for msg in messages:
        if msg.recipient_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()

    return render_template(
        'pages/dashboard/platform_support_chat.html',
        messages=messages,
        other=other,
        admin=admin, # pass admin for UI context
    )


@bp.route('/platform-support/reply', methods=['POST'])
@bp.route('/platform-support/reply/<int:other_id>', methods=['POST'])
@login_required
def platform_support_reply(other_id=None):
    """Replies to a support thread."""
    if current_user.is_platform_admin:
        if not other_id:
            abort(400)
        recipient = User.query.get_or_404(other_id)
    else:
        recipient = User.query.filter_by(role=UserRole.PLATFORM_ADMIN).first()
        if not recipient:
            flash('Platform Admin not available.', 'error')
            return redirect(url_for('dashboard_messages.inbox'))

    content = request.form.get('message', '').strip()
    if not content:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('dashboard_messages.platform_support_chat', other_id=other_id))

    from app.security.encryption import EncryptionManager
    try:
        encrypted = EncryptionManager.encrypt(content)
    except Exception:
        encrypted = content

    msg = SecureMessage(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        channel=MessageChannel.PREMIUM_SUPPORT,
        subject='Support Communication',
        encrypted_content=encrypted,
    )
    db.session.add(msg)
    db.session.commit()
    
    return redirect(url_for('dashboard_messages.platform_support_chat', other_id=other_id))
