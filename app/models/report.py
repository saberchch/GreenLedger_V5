from app.extensions import db
from app.models.base import BaseModel
import enum
from datetime import datetime


class ReportStatus(enum.Enum):
    DRAFT                      = "draft"
    PENDING_COLLATERAL_REVIEW  = "pending_collateral_review"  # Awaiting collateral auditor countersignature
    PENDING_AUDIT              = "pending_audit"              # Awaiting GreenLedger platform admin sign-off
    AUDITED                    = "audited"
    NOTARIZED                  = "notarized"


class Report(BaseModel):
    __tablename__ = "reports"

    summary = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ReportStatus), default=ReportStatus.DRAFT, nullable=False)
    blockchain_tx_hash = db.Column(db.String(255), nullable=True)

    # Period covered by this report
    period_type    = db.Column(db.String(50),  nullable=True)   # e.g. "Monthly", "Quarterly", "Yearly", "Other"
    period_label   = db.Column(db.String(100), nullable=True)   # e.g. "2025 Full Year"
    total_co2e_kg  = db.Column(db.Float,       nullable=True)   # cached total from validated activities

    # Audit lifecycle — Primary Auditor
    recommendations    = db.Column(db.Text,     nullable=True)  # Actions/Suggestions to reduce emissions

    # Audit lifecycle — Primary Auditor
    audit_notes        = db.Column(db.Text,     nullable=True)
    audit_finalized_at = db.Column(db.DateTime, nullable=True)  # when primary auditor finalized

    # Audit lifecycle — Collateral Auditor countersignature
    collateral_signer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    collateral_signed_at = db.Column(db.DateTime, nullable=True)
    collateral_notes     = db.Column(db.Text,     nullable=True)

    # Audit lifecycle — Platform Admin
    platform_signed_at = db.Column(db.DateTime, nullable=True)

    # Foreign Keys
    organization_id    = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    auditor_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)    # primary author
    created_by_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    platform_signer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    organization       = db.relationship("Organization", backref=db.backref("reports", lazy="dynamic"))
    auditor            = db.relationship("User", foreign_keys=[auditor_id],         backref="audited_reports")
    collateral_signer  = db.relationship("User", foreign_keys=[collateral_signer_id], backref="countersigned_reports")
    created_by         = db.relationship("User", foreign_keys=[created_by_id],      backref="created_reports")
    platform_signer    = db.relationship("User", foreign_keys=[platform_signer_id], backref="signed_reports")

    def __repr__(self):
        return f"<Report {self.id} - {self.status.value}>"

