from app.extensions import db
from app.models.base import BaseModel

class SystemSetting(BaseModel):
    __tablename__ = "system_settings"

    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"
