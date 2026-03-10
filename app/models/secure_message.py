import enum
from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel


class MessageChannel(enum.Enum):
    ORG_AUDITOR      = "org_auditor"       # Between org admin and their contracted auditor
    AUDITOR_AUDITOR  = "auditor_auditor"   # Between two platform auditors
    PREMIUM_SUPPORT  = "premium_support"   # Direct line between Premium User and Platform Admin


class SecureMessage(BaseModel):
    """
    End-to-end encrypted direct messages between:
      - Auditor ↔ Org Admin (for a contracted org)
      - Auditor ↔ Auditor   (platform-wide, between certified auditors)

    Content is AES-encrypted at rest using the EncryptionManager.
    The encryption key scope is based on a symmetric context derived from
    the two user IDs so that only the conversation participants (and platform
    admin with the master key) can decrypt.
    """
    __tablename__ = "secure_messages"

    sender_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Context — which org this conversation relates to (may be NULL for auditor↔auditor)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )

    subject           = db.Column(db.String(200), nullable=False, default="(no subject)")
    encrypted_content = db.Column(db.Text, nullable=False)   # AES encrypted
    is_read           = db.Column(db.Boolean, default=False, nullable=False)
    channel           = db.Column(db.Enum(MessageChannel), nullable=False)

    # Optional: thread linking (reply chain)
    parent_message_id = db.Column(
        db.Integer, db.ForeignKey("secure_messages.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    sender    = db.relationship("User", foreign_keys=[sender_id],    backref=db.backref("sent_messages",     lazy="dynamic"))
    recipient = db.relationship("User", foreign_keys=[recipient_id], backref=db.backref("received_messages", lazy="dynamic"))
    organization = db.relationship("Organization", backref=db.backref("org_messages", lazy="dynamic"))
    replies   = db.relationship("SecureMessage", backref=db.backref("parent", remote_side="SecureMessage.id"), lazy="dynamic")

    def __repr__(self):
        return (
            f"<SecureMessage from:{self.sender_id} to:{self.recipient_id} "
            f"channel:{self.channel.value} read:{self.is_read}>"
        )
