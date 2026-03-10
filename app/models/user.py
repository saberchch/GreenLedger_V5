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
    BOT = "bot"  # Reserved for AI bot users — only one instance per platform


class User(UserMixin, BaseModel):
    __tablename__ = "users"

    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))

    status = db.Column(db.String(20), default="active", nullable=False)
    
    # Role - strictly typed as Enum (stored as string in DB)
    role = db.Column(db.Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    
    # Whether the user has been fully vetted by a platform admin (crucial for Auditors)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Auditor reputation score (starts at 100, deducted on missed audits/failed trials)
    reputation_score = db.Column(db.Integer, nullable=False, default=100)

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True
    )

    organization = db.relationship("Organization", back_populates="users",
                                   foreign_keys="[User.organization_id]")

    # Relationships for audit and activities
    # These will be defined in the respective models to avoid circular imports, 
    # or using string references in those models.

    @property
    def reputation_label(self):
        """Human-readable badge for the auditor reputation score."""
        s = self.reputation_score
        if s >= 90: return ("Excellent", "success")
        if s >= 70: return ("Good",      "info")
        if s >= 50: return ("Fair",      "warning")
        return              ("Poor",      "error")

    @property
    def is_platform_admin(self):
        return self.role == UserRole.PLATFORM_ADMIN

    @property
    def is_org_admin(self):
        return self.role == UserRole.ORG_ADMIN

    @property
    def is_premium(self):
        """
        True if this user has access to premium features (e.g., AI Assistant).
        - Platform admins: always True (they control the platform)
        - Auditors: always True (platform professionals)
        - Org members (Admin/Worker/Viewer): depends on their organization's premium status
        """
        if self.role in (UserRole.PLATFORM_ADMIN, UserRole.AUDITOR, UserRole.BOT):
            return True
        if self.organization:
            return self.organization.is_premium
        return False

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

