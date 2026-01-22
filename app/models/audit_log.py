from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel

class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Who did it (Organization context is important for multi-tenancy)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True
    )

    action = db.Column(db.String(50), nullable=False) # e.g., "SUBMIT_EMISSION", "APPROVE_EMISSION"
    
    entity_type = db.Column(db.String(50), nullable=False) # e.g., "EmissionActivity", "Document"
    entity_id = db.Column(db.Integer, nullable=True) # ID of the affected entity
    
    details = db.Column(db.String(2048)) # Specific details, JSON or text
    
    ip_address = db.Column(db.String(45)) # IPv6 capable

    actor = db.relationship("User", backref="audit_logs")
    organization = db.relationship("Organization", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.actor_id} at {self.created_at}>"
