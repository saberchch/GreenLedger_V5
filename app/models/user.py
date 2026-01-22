import enum
from flask_login import UserMixin
from app.extensions import db
from app.models.base import BaseModel


class UserRole(enum.Enum):
    PLATFORM_ADMIN = "platform_admin"
    ORG_ADMIN = "org_admin"
    WORKER = "worker"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class User(UserMixin, BaseModel):
    __tablename__ = "users"

    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))

    status = db.Column(db.String(20), default="active", nullable=False)
    
    # Role - strictly typed as Enum (stored as string in DB)
    role = db.Column(db.Enum(UserRole), default=UserRole.VIEWER, nullable=False)

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True
    )

    organization = db.relationship("Organization", back_populates="users")

    # Relationships for audit and activities
    # These will be defined in the respective models to avoid circular imports, 
    # or using string references in those models.

    @property
    def is_platform_admin(self):
        return self.role == UserRole.PLATFORM_ADMIN

    @property
    def is_org_admin(self):
        return self.role == UserRole.ORG_ADMIN

    def has_role(self, role_name):
        """Helper for templates checking roles by string name"""
        # Map common string variations to Enum value
        role_map = {
            'admin': UserRole.PLATFORM_ADMIN,
            'platform_admin': UserRole.PLATFORM_ADMIN,
            'org_admin': UserRole.ORG_ADMIN,
            'worker': UserRole.WORKER,
            'auditor': UserRole.AUDITOR,
            'viewer': UserRole.VIEWER
        }
        
        target_role = role_map.get(role_name.lower())
        if target_role:
            return self.role == target_role
            
        # Fallback direct string comparison if enum value matches
        return self.role.value == role_name

    def __repr__(self):
        return f"<User {self.email} - {self.role.value}>"

