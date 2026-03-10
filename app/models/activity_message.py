import enum
from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel


class MessageType(enum.Enum):
    MESSAGE = "message"
    REQUEST = "request"
    DOCUMENT = "document"
    SYSTEM = "system"  # For bot replies like /help or slash command outputs


class ActivityMessage(BaseModel):
    """
    Unified messaging model for GreenLedger.

    Two modes:
      - Organization Team Chat:  activity_id is NULL,  organization_id is set.
      - Emission Discussion:     activity_id is set,  organization_id is set.

    Access:
      - Only internal org members (worker, org_admin, viewer) can write.
      - Auditors are read-only.
    """
    __tablename__ = 'activity_messages'

    # Channel — either org-wide (activity_id=NULL, recipient_auditor_id=NULL)
    #            or emission-specific (activity_id set)
    #            or auditor-org DM  (activity_id=NULL, recipient_auditor_id set)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('emission_activities.id'), nullable=True)

    # When set, this message belongs to the auditor↔org direct channel
    recipient_auditor_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.Enum(MessageType), default=MessageType.MESSAGE, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    author = db.relationship(
        'User',
        foreign_keys=[author_id],
        backref=db.backref('activity_messages', lazy='dynamic')
    )
    recipient_auditor = db.relationship(
        'User',
        foreign_keys=[recipient_auditor_id],
        backref=db.backref('auditor_dm_messages', lazy='dynamic')
    )
    organization = db.relationship(
        'Organization',
        backref=db.backref('team_messages', lazy='dynamic')
    )
    activity = db.relationship(
        'EmissionActivity',
        backref=db.backref('messages', lazy='dynamic', cascade="all, delete-orphan",
                           order_by="ActivityMessage.created_at.asc()")
    )

    def to_dict(self):
        """Standardized JSON serialization for the frontend API"""
        if self.author:
            author_name = f"{self.author.first_name or ''} {self.author.last_name or ''}".strip() or self.author.email
            author_role = self.author.role.value if self.author.role else 'unknown'
        else:
            author_name = 'Unknown'
            author_role = 'unknown'

        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'activity_id': self.activity_id,
            'recipient_auditor_id': self.recipient_auditor_id,
            'author_id': self.author_id,
            'author_name': author_name,
            'author_role': author_role,
            'message': self.message,
            'message_type': self.message_type.value if self.message_type else 'message',
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }
