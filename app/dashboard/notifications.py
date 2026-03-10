from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.notification import Notification

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@bp.route('/', methods=['GET'])
@login_required
def get_notifications():
    """Fetch recent notifications for the current user."""
    # Get the latest 10 unread notifications
    unread = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    return jsonify([n.to_dict() for n in unread])


@bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'success': True})
