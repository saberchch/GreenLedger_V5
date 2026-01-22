from app.extensions import db
from app.models.base import BaseModel


import enum

class OrganizationStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


class Organization(BaseModel):
    __tablename__ = "organizations"

    name = db.Column(db.String(255), nullable=False)
    legal_name = db.Column(db.String(255))
    country = db.Column(db.String(100))
    industry = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True, nullable=False) # Keep for backward compatibility or soft delete
    status = db.Column(db.Enum(OrganizationStatus), default=OrganizationStatus.PENDING, nullable=False)

    users = db.relationship("User", back_populates="organization", lazy="dynamic")
