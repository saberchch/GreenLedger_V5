from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel


class AuditorPointLog(BaseModel):
    """
    Tracks every change to an auditor's reputation score.

    delta > 0  → bonus points
    delta < 0  → deduction (e.g. missed monthly audit = -20, failed trial = -50)
    """
    __tablename__ = "auditor_point_logs"

    auditor_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    contract_id     = db.Column(db.Integer, db.ForeignKey("auditor_contracts.id", ondelete="SET NULL"), nullable=True)

    delta  = db.Column(db.Integer, nullable=False)   # e.g. -20, -50, +10
    reason = db.Column(db.Text,    nullable=False)

    # Relationships
    auditor      = db.relationship("User",         backref=db.backref("point_logs", lazy="dynamic", cascade="all, delete-orphan"))
    organization = db.relationship("Organization", backref=db.backref("auditor_point_logs", lazy="dynamic"))
    contract     = db.relationship("AuditorContract", backref=db.backref("point_logs", lazy="dynamic"))

    def __repr__(self):
        sign = "+" if self.delta >= 0 else ""
        return f"<AuditorPointLog Auditor:{self.auditor_id} {sign}{self.delta} — {self.reason[:40]}>"
