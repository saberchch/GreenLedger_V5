import enum
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db
from app.models.base import BaseModel

class EmissionScope(enum.Enum):
    SCOPE_1 = "Scope 1"
    SCOPE_2 = "Scope 2"
    SCOPE_3 = "Scope 3"

class ActivityStatus(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    REJECTED = "rejected"

class EmissionActivity(BaseModel):
    __tablename__ = "emission_activities"

    organization_id = db.Column(
        db.Integer, 
        db.ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    created_by_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id"), 
        nullable=False
    )
    
    scope = db.Column(db.Enum(EmissionScope), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False) # e.g. "Stationary Combustion", "Purchased Electricity"
    
    # Store dynamic activity data (e.g. {"fuel_type": "diesel", "amount": 100})
    # defaulting to JSON type, but using db.JSON (works as Text in SQLite, JSONB in PG)
    activity_data = db.Column(db.JSON, nullable=True) 
    
    emission_factor_id = db.Column(
        db.Integer,
        db.ForeignKey("emission_factors.id"),
        nullable=True
    )

    co2e_result = db.Column(db.Float, nullable=True) # Calculated CO2e
    
    status = db.Column(
        db.Enum(ActivityStatus), 
        default=ActivityStatus.DRAFT, 
        nullable=False,
        index=True
    )

    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", backref="activities")
    created_by = db.relationship("User", foreign_keys=[created_by_id], backref="created_activities")
    emission_factor = db.relationship("EmissionFactor")

    def __repr__(self):
        return f"<EmissionActivity {self.id} - {self.scope.value} - {self.status.value}>"
