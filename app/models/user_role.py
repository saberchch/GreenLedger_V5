from app.extensions import db

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    db.Column("organization_id", db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    db.UniqueConstraint("user_id", "role_id", "organization_id", name="uq_user_role_org")
)
