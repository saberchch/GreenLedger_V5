import enum
from datetime import datetime, timedelta
from app.extensions import db
from app.models.base import BaseModel


class ContractStatus(enum.Enum):
    PENDING    = "pending"      # Org proposed, auditor hasn't answered
    TRIAL      = "trial"        # Auditor accepted — 1-month trial running
    ACTIVE     = "active"       # Trial passed, full yearly contract active
    COMPLETED  = "completed"    # Contract ended naturally (1 year up)
    CANCELLED  = "cancelled"    # Either party cancelled before expiry
    DISCARDED  = "discarded"    # Auditor failed trial duty → auto-removed


class AuditorType(enum.Enum):
    PRIMARY    = "primary"      # Main auditor for the organisation
    COLLATERAL = "collateral"   # Backup auditor


class AuditorContract(BaseModel):
    """
    Smart-contract-style engagement between an Organisation and an Auditor.

    Lifecycle:
        PENDING  →  TRIAL  →  ACTIVE  →  COMPLETED
                 ↘  CANCELLED / DISCARDED (on failure)
    The org admin creates the contract proposal; the auditor accepts or rejects it.
    """
    __tablename__ = "auditor_contracts"

    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    auditor_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    auditor_type  = db.Column(db.Enum(AuditorType),    nullable=False, default=AuditorType.PRIMARY)
    status        = db.Column(db.Enum(ContractStatus), nullable=False, default=ContractStatus.PENDING)

    # Financial terms
    monthly_fee   = db.Column(db.Numeric(10, 2), nullable=True)  # agreed monthly fee in org's currency

    # Timeline
    contract_start = db.Column(db.DateTime, nullable=True)
    trial_end      = db.Column(db.DateTime, nullable=True)   # start + 30 days
    contract_end   = db.Column(db.DateTime, nullable=True)   # start + 365 days

    # Proposal message from org admin
    message = db.Column(db.Text, nullable=True)

    # Audit accountability
    last_audit_submitted_at = db.Column(db.DateTime, nullable=True)
    missed_months           = db.Column(db.Integer, nullable=False, default=0)

    # Relationships
    organization = db.relationship(
        "Organization",
        backref=db.backref("auditor_contracts", lazy="dynamic", cascade="all, delete-orphan")
    )
    auditor = db.relationship(
        "User",
        backref=db.backref("audit_contracts", lazy="dynamic", cascade="all, delete-orphan")
    )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def activate(self):
        """Called when the auditor accepts the proposal."""
        now = datetime.utcnow()
        self.status         = ContractStatus.TRIAL
        self.contract_start = now
        self.trial_end      = now + timedelta(days=30)
        self.contract_end   = now + timedelta(days=365)

    def is_in_trial(self):
        if self.status != ContractStatus.TRIAL:
            return False
        return self.trial_end and datetime.utcnow() < self.trial_end

    def is_expired(self):
        if self.contract_end is None:
            return False
        return datetime.utcnow() > self.contract_end

    def days_remaining(self):
        if not self.contract_end:
            return None
        delta = self.contract_end - datetime.utcnow()
        return max(0, delta.days)

    def trial_days_remaining(self):
        if not self.trial_end:
            return None
        delta = self.trial_end - datetime.utcnow()
        return max(0, delta.days)

    def __repr__(self):
        return (
            f"<AuditorContract Org:{self.organization_id} "
            f"Auditor:{self.auditor_id} "
            f"Type:{self.auditor_type.value} "
            f"Status:{self.status.value}>"
        )
