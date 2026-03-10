import enum
from app.extensions import db
from app.models.base import BaseModel

class RequestStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class AuditorRequest(BaseModel):
    __tablename__ = "auditor_requests"

    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    
    # Optional message from the org admin
    message = db.Column(db.Text, nullable=True)

    organization = db.relationship("Organization", backref=db.backref("auditor_requests", lazy="dynamic", cascade="all, delete-orphan"))
    auditor = db.relationship("User", backref=db.backref("received_audit_requests", lazy="dynamic", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<AuditorRequest Org:{self.organization_id} Auditor:{self.auditor_id} Status:{self.status.value}>"
