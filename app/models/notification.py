import enum
from app.extensions import db
from datetime import datetime
from app.models.base import BaseModel

class NotificationType(enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class Notification(BaseModel):
    __tablename__ = 'notifications'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(NotificationType), default=NotificationType.INFO, nullable=False)
    
    related_entity_type = db.Column(db.String(50), nullable=True) # e.g., 'emission_activity'
    related_entity_id = db.Column(db.Integer, nullable=True)
    
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade="all, delete-orphan"))

    def to_dict(self):
        from flask import url_for
        
        action_url = None
        if self.related_entity_type == 'emission_activity' and self.related_entity_id:
            # We determine the route based on the user's role
            if self.user.role.value == 'worker':
                action_url = url_for('dashboard_worker.emission_detail', id=self.related_entity_id)
            elif self.user.role.value == 'org_admin':
                action_url = url_for('dashboard_org_admin.emission_detail', id=self.related_entity_id)
                
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type.value if self.type else 'info',
            'related_entity_type': self.related_entity_type,
            'related_entity_id': self.related_entity_id,
            'is_read': self.is_read,
            'action_url': action_url,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }
