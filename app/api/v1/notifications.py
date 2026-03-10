from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.notification import Notification

bp = Blueprint('api_notifications', __name__, url_prefix='/api/v1/notifications')

@bp.route('/unread', methods=['GET'])
@login_required
def get_unread():
    """Fetch all unread notifications for the current user."""
    notifs = (
        Notification.query
        .filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify([n.to_dict() for n in notifs]), 200


@bp.route('/<int:id>/read', methods=['POST'])
@login_required
def mark_read(id):
    """Mark a specific notification as read."""
    notif = Notification.query.get_or_404(id)
    if notif.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notif.is_read = True
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Notification marked as read'}), 200


@bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read for the current user."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'All notifications marked as read'}), 200
