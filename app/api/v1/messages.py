from flask import Blueprint, jsonify, request, abort, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.emission_activity import EmissionActivity
from app.models.activity_message import ActivityMessage, MessageType
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.secure_message import SecureMessage, MessageChannel
from sqlalchemy import func, or_

bp = Blueprint('api_messages', __name__, url_prefix='/api/v1/messages')


def _is_internal_member():
    return current_user.role.value in ('worker', 'org_admin', 'viewer')


def _require_org_member():
    if not _is_internal_member():
        abort(403)


def _require_org_access(organization_id):
    if current_user.has_role('admin'):
        return
    if current_user.organization_id != organization_id:
        abort(403)


def _require_auditor_org_access(org_id: int, auditor_id: int):
    """
    Grant access if the current user is:
      - the auditor in this channel, OR
      - a member of the org, OR
      - a platform admin
    No contract required — open even before any request is made.
    """
    if current_user.has_role('admin'):
        return
    if current_user.id == auditor_id:
        return
    if current_user.organization_id == org_id:
        return
    abort(403)


# ─── Members list ────────────────────────────────────────────────────────────

@bp.route('/org/<int:org_id>/members', methods=['GET'])
@login_required
def get_org_members(org_id):
    _require_org_access(org_id)
    members = User.query.filter_by(organization_id=org_id).all()
    result = []
    for u in members:
        if u.id == current_user.id:
            continue
        name = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
        result.append({
            'id': u.id,
            'name': name,
            'role': u.role.value if u.role else 'unknown',
            'initials': (name[0]).upper() if name else '?'
        })
    return jsonify(result), 200


# ─── Organization Team Chat ───────────────────────────────────────────────────

@bp.route('/org/<int:org_id>', methods=['GET'])
@login_required
def get_org_messages(org_id):
    _require_org_access(org_id)
    messages = (
        ActivityMessage.query
        .filter_by(organization_id=org_id, activity_id=None, recipient_auditor_id=None)
        .order_by(ActivityMessage.created_at.asc())
        .limit(100)
        .all()
    )
    return jsonify([m.to_dict() for m in messages]), 200


import re
from app.models.notification import Notification, NotificationType

@bp.route('/org/<int:org_id>', methods=['POST'])
@login_required
def post_org_message(org_id):
    _require_org_access(org_id)
    _require_org_member()
    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return jsonify({'error': 'Message cannot be empty'}), 400
        
    raw_message = data['message'].strip()
    msg_type_raw = data.get('message_type', 'message').upper()
    try:
        msg_type = MessageType[msg_type_raw]
    except KeyError:
        msg_type = MessageType.MESSAGE

    # ─── Process Slash Commands ──────────────────────────────────────────────
    if raw_message.startswith('/'):
        parts = raw_message.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == '/help':
            # Create an ephemeral system message just for this response
            system_msg = ActivityMessage(
                organization_id=org_id,
                activity_id=None,
                recipient_auditor_id=None,
                author_id=current_user.id, # Keep author so frontend can render correctly
                message="**Available Commands:**\n`/help` - Show this message\n`/urgent [message]` - Send a high-priority alert to the team\n`/me [action]` - Send an action message",
                message_type=MessageType.SYSTEM
            )
            db.session.add(system_msg)
            db.session.commit()
            return jsonify(system_msg.to_dict()), 201
            
        elif command == '/urgent':
            if not args:
                 return jsonify({'error': 'Please provide a message for the urgent alert.'}), 400
            
            # Save the message normally, but flag it as a request to make it stand out
            msg = ActivityMessage(
                organization_id=org_id,
                activity_id=None,
                recipient_auditor_id=None,
                author_id=current_user.id,
                message=f"🚨 URGENT: {args}",
                message_type=MessageType.REQUEST
            )
            db.session.add(msg)
            
            # Notify everyone in the org
            org_members = User.query.filter(
                User.organization_id == org_id,
                User.role.in_([UserRole.ORG_ADMIN, UserRole.WORKER, UserRole.VIEWER]),
                User.id != current_user.id
            ).all()
            
            author_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
            for u in org_members:
                notif = Notification(
                    user_id=u.id,
                    title="Urgent Team Alert",
                    message=f"{author_name}: {args[:50]}{'...' if len(args)>50 else ''}",
                    type=NotificationType.ERROR,
                    related_entity_type='team_chat',
                    related_entity_id=org_id
                )
                db.session.add(notif)
                
            db.session.commit()
            return jsonify(msg.to_dict()), 201
            
        elif command == '/me':
             if not args:
                 return jsonify({'error': 'Please provide an action.'}), 400
             # Create a system message displaying the action
             author_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
             msg = ActivityMessage(
                 organization_id=org_id,
                 activity_id=None,
                 recipient_auditor_id=None,
                 author_id=current_user.id,
                 message=f"_{author_name} {args}_",
                 message_type=MessageType.SYSTEM
             )
             db.session.add(msg)
             db.session.commit()
             return jsonify(msg.to_dict()), 201
             
        else:
             return jsonify({'error': f"Unknown command: {command}. Type /help for available commands."}), 400

    # ─── Standard Message ────────────────────────────────────────────────────
    msg = ActivityMessage(
        organization_id=org_id,
        activity_id=None,
        recipient_auditor_id=None,
        author_id=current_user.id,
        message=raw_message,
        message_type=msg_type
    )
    db.session.add(msg)
    db.session.commit()
    
    # ─── Process @Mentions ───────────────────────────────────────────────────
    # Regex looks for @ followed by words/spaces until the next @, <, or end of string
    mention_matches = re.findall(r'@([\w\s]+?)(?=\s|$|@|<)', raw_message)
    if mention_matches:
        # Fetch all internal org members to match against
        org_members = User.query.filter(
            User.organization_id == org_id,
            User.role.in_([UserRole.ORG_ADMIN, UserRole.WORKER, UserRole.VIEWER])
        ).all()
        
        # Build lookup table: lowercase full name -> User object
        name_lookup = {}
        for u in org_members:
            full_name = f"{u.first_name or ''} {u.last_name or ''}".strip()
            if full_name:
                name_lookup[full_name.lower()] = u
        
        notified_users = set()
        for match in mention_matches:
            target_name = match.strip().lower()
            target_user = name_lookup.get(target_name)
            
            # Don't notify if the user mentioned themselves or already notified in this msg
            if target_user and target_user.id != current_user.id and target_user.id not in notified_users:
                author_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
                notif = Notification(
                    user_id=target_user.id,
                    title="New Mention in Team Chat",
                    message=f"{author_name} mentioned you: \"{raw_message[:50]}{'...' if len(raw_message)>50 else ''}\"",
                    type=NotificationType.INFO,
                    related_entity_type='team_chat',
                    related_entity_id=org_id
                )
                db.session.add(notif)
                notified_users.add(target_user.id)
                
        if notified_users:
            db.session.commit()

    return jsonify(msg.to_dict()), 201
# ─── Emission Discussion ──────────────────────────────────────────────────────

@bp.route('/activity/<int:activity_id>', methods=['GET'])
@login_required
def get_messages(activity_id):
    activity = EmissionActivity.query.get_or_404(activity_id)
    _require_org_access(activity.organization_id)
    messages = (
        ActivityMessage.query
        .filter_by(activity_id=activity.id)
        .order_by(ActivityMessage.created_at.asc())
        .all()
    )
    return jsonify([m.to_dict() for m in messages]), 200


@bp.route('/activity/<int:activity_id>', methods=['POST'])
@login_required
def post_message(activity_id):
    activity = EmissionActivity.query.get_or_404(activity_id)
    _require_org_access(activity.organization_id)
    _require_org_member()
    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return jsonify({'error': 'Message cannot be empty'}), 400
    msg_type_raw = data.get('message_type', 'message').upper()
    try:
        msg_type = MessageType[msg_type_raw]
    except KeyError:
        msg_type = MessageType.MESSAGE
    msg = ActivityMessage(
        organization_id=activity.organization_id,
        activity_id=activity.id,
        author_id=current_user.id,
        message=data['message'].strip(),
        message_type=msg_type
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify(msg.to_dict()), 201


# ─── Auditor ↔ Org Direct Channel ────────────────────────────────────────────
# Open to the auditor and any org member — no contract required.
# Used to discuss contract terms, ask questions, etc. before any engagement.

AI_BOT_AUTO_REPLY = (
    "Hello! 👋 The **GreenLedger AI Assistant** is currently in development and will be available soon.\n\n"
    "In the meantime, here are some quick tips:\n"
    "• 🌱 **Scope 1** — Direct emissions (e.g. company vehicles, on-site combustion)\n"
    "• 🏭 **Scope 2** — Indirect emissions from purchased electricity/heat\n"
    "• 🌍 **Scope 3** — All other indirect emissions in your value chain\n\n"
    "Stay tuned for the full AI experience! 🚀"
)


@bp.route('/auditor/<int:auditor_id>/org/<int:org_id>', methods=['GET'])
@login_required
def get_auditor_org_messages(auditor_id, org_id):
    """Fetch the direct thread between a user and an auditor/AI-bot."""
    auditor = User.query.get_or_404(auditor_id)
    is_ai = (auditor.role == UserRole.BOT)

    if is_ai:
        # Security: the org_id IS the current user's id for AI threads.
        # Prevent user A from reading user B's private AI thread.
        if org_id != current_user.id:
            abort(403)
    else:
        _require_auditor_org_access(org_id, auditor_id)
        if auditor.role != UserRole.AUDITOR:
            abort(400)

    messages = (
        ActivityMessage.query
        .filter_by(organization_id=org_id, activity_id=None,
                   recipient_auditor_id=auditor_id)
        .order_by(ActivityMessage.created_at.asc())
        .limit(200)
        .all()
    )
    return jsonify([m.to_dict() for m in messages]), 200


@bp.route('/auditor/<int:auditor_id>/org/<int:org_id>', methods=['POST'])
@login_required
def post_auditor_org_message(auditor_id, org_id):
    """Post to the auditor-org OR personal AI direct channel."""
    auditor = User.query.get_or_404(auditor_id)
    is_ai = (auditor.role == UserRole.BOT)

    if is_ai:
        # Security: ensure users can only write to their own AI thread.
        if org_id != current_user.id:
            abort(403)
    else:
        _require_auditor_org_access(org_id, auditor_id)
        if auditor.role != UserRole.AUDITOR:
            abort(400)

    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return jsonify({'error': 'Message cannot be empty'}), 400

    msg = ActivityMessage(
        organization_id=org_id,  # For AI: this is current_user.id (personal channel)
        activity_id=None,
        recipient_auditor_id=auditor_id,
        author_id=current_user.id,
        message=data['message'].strip(),
        message_type=MessageType.MESSAGE,
    )
    db.session.add(msg)

    # ─── AI Chatbot Auto-Reply ───────────────────────────────────────────────
    if is_ai:
        db.session.flush()
        ai_reply = ActivityMessage(
            organization_id=org_id,  # Same personal channel key
            activity_id=None,
            recipient_auditor_id=auditor_id,
            author_id=auditor.id,
            message=AI_BOT_AUTO_REPLY,
            message_type=MessageType.MESSAGE,
            is_read=False
        )
        db.session.add(ai_reply)
        db.session.commit()
        return jsonify({'messages': [msg.to_dict(), ai_reply.to_dict()]}), 201

    db.session.commit()
    return jsonify(msg.to_dict()), 201


# ─── Recent Conversations (Inbox & Dropdown) ─────────────────────────────────

@bp.route('/recent', methods=['GET'])
@login_required
def get_recent_conversations():
    """
    Fetch the most recent message for each distinct conversation the user belongs to,
    along with the count of unread messages in that conversation.
    """
    channels = {}
    
    # 1. Team Chat (Org Members only)
    if _is_internal_member() and current_user.organization_id:
        org_id = current_user.organization_id
        # Get team messages
        team_msgs = ActivityMessage.query.filter_by(
            organization_id=org_id, 
            activity_id=None, 
            recipient_auditor_id=None
        ).order_by(ActivityMessage.created_at.desc()).all()
        
        if team_msgs:
            latest = team_msgs[0]
            unread = sum(1 for m in team_msgs if m.author_id != current_user.id and not m.is_read)
            channels['team'] = {
                'id': f"team_{org_id}",
                'title': "Team Chat",
                'subtitle': "Internal organization",
                'latest_message': latest.message,
                'created_at': latest.created_at.isoformat() + 'Z',
                'unread_count': unread,
                'url': url_for('dashboard_chat.team_chat'),
                'avatar_type': 'team',
                'initials': 'T'
            }

    # 2. Auditor ↔ Org Direct Channels
    if current_user.role == UserRole.AUDITOR:
        # Auditor: fetch messages where recipient_auditor_id is them
        dm_msgs = ActivityMessage.query.filter_by(
            activity_id=None,
            recipient_auditor_id=current_user.id
        ).order_by(ActivityMessage.created_at.desc()).all()
        
        # Group by organization_id
        org_groups = {}
        for m in dm_msgs:
            if m.organization_id not in org_groups:
                org_groups[m.organization_id] = []
            org_groups[m.organization_id].append(m)
            
        for org_id, msgs in org_groups.items():
            latest = msgs[0]
            unread = sum(1 for m in msgs if m.author_id != current_user.id and not m.is_read)
            org = Organization.query.get(org_id)
            if org:
                # Find the org admin to act as the chat target
                admin = User.query.filter_by(organization_id=org_id, role=UserRole.ORG_ADMIN).first()
                target_id = admin.id if admin else msgs[0].author_id
                
                channels[f"dm_{org_id}"] = {
                    'id': f"dm_{org_id}",
                    'title': org.name,
                    'subtitle': "Organisation",
                    'latest_message': latest.message,
                    'created_at': latest.created_at.isoformat() + 'Z',
                    'unread_count': unread,
                    'url': f'/dashboard/messages/chat/{target_id}',
                    'avatar_type': 'org',
                    'initials': org.name[0].upper()
                }
                
    elif _is_internal_member() and current_user.organization_id:
        # Org member: fetch messages for their org sent to specific auditors
        dm_msgs = ActivityMessage.query.filter(
            ActivityMessage.organization_id == current_user.organization_id,
            ActivityMessage.activity_id == None,
            ActivityMessage.recipient_auditor_id != None
        ).order_by(ActivityMessage.created_at.desc()).all()
        
        # Group by recipient_auditor_id
        auditor_groups = {}
        for m in dm_msgs:
            if m.recipient_auditor_id not in auditor_groups:
                auditor_groups[m.recipient_auditor_id] = []
            auditor_groups[m.recipient_auditor_id].append(m)
            
        for aud_id, msgs in auditor_groups.items():
            latest = msgs[0]
            unread = sum(1 for m in msgs if m.author_id != current_user.id and not m.is_read)
            auditor = User.query.get(aud_id)
            if auditor:
                name = f"{auditor.first_name or ''} {auditor.last_name or ''}".strip()
                channels[f"dm_{aud_id}"] = {
                    'id': f"dm_{aud_id}",
                    'title': name,
                    'subtitle': "Platform Auditor",
                    'latest_message': latest.message,
                    'created_at': latest.created_at.isoformat() + 'Z',
                    'unread_count': unread,
                    'url': f'/dashboard/messages/chat/{aud_id}',
                    'avatar_type': 'auditor',
                    'initials': name[0].upper() if name else 'A'
                }

    # 3. Platform Admin ↔ Any User (PREMIUM_SUPPORT SecureMessage channel)
    support_query = SecureMessage.query.filter_by(channel=MessageChannel.PREMIUM_SUPPORT)
    if current_user.has_role('admin'): # Platform Admin view: group by OTHER user
        # We need to find all unique users the admin has chatted with
        # (sender_id or recipient_id that is NOT the current_user)
        all_support = support_query.filter(
            or_(SecureMessage.sender_id == current_user.id, SecureMessage.recipient_id == current_user.id)
        ).order_by(SecureMessage.created_at.desc()).all()

        user_threads = {}
        for m in all_support:
            other_id = m.recipient_id if m.sender_id == current_user.id else m.sender_id
            if other_id == current_user.id:
                continue # Skip self-messaging
            if other_id not in user_threads:
                user_threads[other_id] = []
            user_threads[other_id].append(m)

        for other_id, msgs in user_threads.items():
            other = User.query.get(other_id)
            if not other: continue
            latest = msgs[0]
            unread = sum(1 for m in msgs if m.recipient_id == current_user.id and not m.is_read)
            name = f"{other.first_name or ''} {other.last_name or ''}".strip() or other.email
            role_label = other.role.value.replace('_', ' ').title() if other.role else 'User'
            channels[f"support_{other_id}"] = {
                'id': f"support_{other_id}",
                'title': name,
                'subtitle': f"Support Request · {role_label}",
                'latest_message': latest.encrypted_content[:80] + ('…' if len(latest.encrypted_content) > 80 else ''),
                'created_at': latest.created_at.isoformat() + 'Z',
                'unread_count': unread,
                'url': f'/dashboard/admin/support/thread/{other_id}', # Use existing support thread view
                'avatar_type': 'user',
                'initials': name[0].upper() if name else '?'
            }
    else: # Regular user view: group all support into "GreenLedger Platform"
        platform_msgs = support_query.filter(
            or_(SecureMessage.sender_id == current_user.id, SecureMessage.recipient_id == current_user.id)
        ).order_by(SecureMessage.created_at.desc()).all()

        if platform_msgs:
            latest = platform_msgs[0]
            unread = sum(1 for m in platform_msgs if m.recipient_id == current_user.id and not m.is_read)
            channels['platform_support'] = {
                'id': 'platform_support',
                'title': 'GreenLedger Platform',
                'subtitle': 'Admin · Credential & Support',
                'latest_message': latest.encrypted_content[:80] + ('…' if len(latest.encrypted_content) > 80 else ''),
                'created_at': latest.created_at.isoformat() + 'Z',
                'unread_count': unread,
                'url': '/dashboard/messages/platform-support',
                'avatar_type': 'platform',
                'initials': 'GL'
            }

    # Sort channels by latest message time
    sorted_channels = sorted(channels.values(), key=lambda x: x['created_at'], reverse=True)
    return jsonify(sorted_channels), 200


@bp.route('/read/<channel_id>', methods=['POST'])
@login_required
def mark_channel_read(channel_id):
    """Mark all messages in a specific channel as read for the current user."""
    # channel_id format: "team_X" or "dm_X"
    parts = channel_id.split('_')
    if len(parts) != 2:
        return jsonify({'error': 'Invalid channel ID'}), 400
        
    ctype, cid = parts[0], parts[1]
    
    try:
        cid = int(cid)
    except ValueError:
        return jsonify({'error': 'Invalid channel ID format'}), 400

    query = ActivityMessage.query.filter(ActivityMessage.author_id != current_user.id, ActivityMessage.is_read == False)
    
    if ctype == 'team':
        if not _is_internal_member() or current_user.organization_id != cid:
            abort(403)
        query = query.filter_by(organization_id=cid, activity_id=None, recipient_auditor_id=None)
    elif ctype == 'dm':
        if current_user.role == UserRole.AUDITOR:
            # cid is the org_id
            query = query.filter_by(organization_id=cid, activity_id=None, recipient_auditor_id=current_user.id)
        else:
            # cid is the auditor_id
            if not current_user.organization_id:
                abort(403)
            query = query.filter_by(organization_id=current_user.organization_id, activity_id=None, recipient_auditor_id=cid)
    else:
        return jsonify({'error': 'Unknown channel type'}), 400
        
    unread_msgs = query.all()
    for m in unread_msgs:
        m.is_read = True
        
    db.session.commit()
    return jsonify({'success': True, 'marked': len(unread_msgs)}), 200

