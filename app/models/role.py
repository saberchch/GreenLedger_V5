from app.extensions import db
from app.models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    # users = db.relationship(
    #     "User",
    #     secondary="user_roles",
    #     back_populates="roles",
    #     lazy="dynamic"
    # )
