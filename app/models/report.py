from app.extensions import db
from app.models.base import BaseModel
import enum

class ReportStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_AUDIT = "pending_audit"
    AUDITED = "audited"
    NOTARIZED = "notarized"

class Report(BaseModel):
    __tablename__ = "reports"

    summary = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ReportStatus), default=ReportStatus.DRAFT, nullable=False)
    blockchain_tx_hash = db.Column(db.String(255), nullable=True)
    
    # Foreign Keys
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    auditor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Relationships
    organization = db.relationship("Organization", backref=db.backref("reports", lazy="dynamic"))
    auditor = db.relationship("User", foreign_keys=[auditor_id], backref="audited_reports")
    created_by = db.relationship("User", foreign_keys=[created_by_id], backref="created_reports")

    def __repr__(self):
        return f"<Report {self.id} - {self.status.value}>"
