from app.extensions import db
from app.models.base import BaseModel


import enum

class OrganizationStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


organization_auditors = db.Table('organization_auditors',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('organization_id', db.Integer, db.ForeignKey('organizations.id'), primary_key=True)
)


class Organization(BaseModel):
    __tablename__ = "organizations"

    name = db.Column(db.String(255), nullable=False)
    legal_name = db.Column(db.String(255))
    country = db.Column(db.String(100))
    industry = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True, nullable=False) # Keep for backward compatibility or soft delete
    status = db.Column(db.Enum(OrganizationStatus), default=OrganizationStatus.PENDING, nullable=False)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)  # Premium tier — unlocks AI Assistant

    # Smart-contract auditor slots (max 1 primary + 1 collateral)
    primary_auditor_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    collateral_auditor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    users = db.relationship("User", back_populates="organization", lazy="dynamic",
                            foreign_keys="[User.organization_id]")

    # Legacy M2M — kept for backward-compat; new code uses primary/collateral FKs
    delegated_auditors = db.relationship("User", secondary=organization_auditors,
                                         backref=db.backref("audited_organizations", lazy="dynamic"),
                                         lazy="dynamic")

    primary_auditor    = db.relationship("User", foreign_keys=[primary_auditor_id],
                                          backref=db.backref("primary_for_orgs",    lazy="dynamic"))
    collateral_auditor = db.relationship("User", foreign_keys=[collateral_auditor_id],
                                          backref=db.backref("collateral_for_orgs", lazy="dynamic"))
