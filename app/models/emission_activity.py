import enum
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db
from app.models.base import BaseModel
from app.models.emission_factor_database import ActivityType


class EmissionScope(enum.Enum):
    SCOPE_1 = "Scope 1"
    SCOPE_2 = "Scope 2"
    SCOPE_3 = "Scope 3"


class ActivityStatus(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    REJECTED = "rejected"
    AUDITED = "audited"       # finalised by auditor — locked, no further edits


class EmissionActivity(BaseModel):
    """
    Emission Activity Model
    
    Represents a single emission-generating activity with support for
    multiple calculation methodologies (simple, transport, process, fugitive).
    
    Core fields:
        organization_id: Organization that owns this activity
        created_by_id: User who created this activity
        scope: GHG Protocol scope (Scope 1, 2, or 3)
        category: Activity category (e.g., "Stationary Combustion", "Purchased Electricity")
        activity_type: Calculation type (simple, transport, process, fugitive)
        activity_data: Dynamic JSON data for activity-specific fields
        emission_factor_id: Reference to emission factor used
        co2e_result: Calculated emissions in kgCO2e
        status: Workflow status (draft, submitted, validated, rejected)
        period_start/period_end: Reporting period
    
    Transport-specific fields:
        tonnage: Mass transported in tonnes
        distance: Distance in kilometers
        transport_mode: Mode of transport (truck, rail, ship, air)
    
    ADEME fields (copied from emission factor):
        poste_emission: ADEME emission post
        perimetre: ADEME perimeter classification
    """
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
    category = db.Column(db.String(100), nullable=False)  # e.g. "Stationary Combustion", "Purchased Electricity"
    
    # Activity calculation type
    activity_type = db.Column(
        db.Enum(ActivityType), 
        default=ActivityType.SIMPLE, 
        nullable=False,
        index=True
    )
    
    # Store dynamic activity data (e.g. {"fuel_type": "diesel", "amount": 100})
    # defaulting to JSON type, but using db.JSON (works as Text in SQLite, JSONB in PG)
    activity_data = db.Column(db.JSON, nullable=True) 
    
    emission_factor_id = db.Column(
        db.Integer,
        db.ForeignKey("emission_factors.id"),
        nullable=True
    )

    co2e_result = db.Column(db.Float, nullable=True)  # Calculated CO2e in kgCO2e
    
    status = db.Column(
        db.Enum(ActivityStatus), 
        default=ActivityStatus.DRAFT, 
        nullable=False,
        index=True
    )

    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # User-entered quantity (the raw amount before × factor)
    quantity = db.Column(db.Float, nullable=True)  # e.g. 1000 (kWh), 500 (km)
    quantity_unit = db.Column(db.String(50), nullable=True)  # human-readable unit label

    # Transport-specific fields (nullable, only used when activity_type = TRANSPORT)
    tonnage = db.Column(db.Float, nullable=True)  # Mass in tonnes
    distance = db.Column(db.Float, nullable=True)  # Distance in km
    transport_mode = db.Column(db.String(50), nullable=True)  # truck, rail, ship, air, etc.

    # ADEME snapshot — denormalised from CSV at submission time for audit trail
    ademe_factor_id = db.Column(db.String(50), nullable=True, index=True)   # e.g. "12345"
    ademe_factor_name = db.Column(db.String(500), nullable=True)             # factor name in French
    ademe_factor_value = db.Column(db.Float, nullable=True)                  # kgCO2e per unit at time of submission
    ademe_factor_unit = db.Column(db.String(100), nullable=True)             # unit string from ADEME
    ademe_factor_source = db.Column(db.String(200), nullable=True)           # e.g. "AGRIBALYSE 3.1"
    ademe_factor_category = db.Column(db.String(500), nullable=True)         # full category path

    # Workflow notes
    description = db.Column(db.Text, nullable=True)    # worker free-text description
    rejection_reason = db.Column(db.Text, nullable=True)  # org-admin rejection note

    # ADEME legacy fields (kept for backward compat)
    poste_emission = db.Column(db.String(255), nullable=True)
    perimetre = db.Column(db.String(100), nullable=True)
    
    # Relationships
    organization = db.relationship("Organization", backref="activities")
    created_by = db.relationship("User", foreign_keys=[created_by_id], backref="created_activities")
    # Note: emission_factor_id is kept for optional database storage,
    # but we primarily use CSV-based emission factors via EmissionFactorLoader

    def __repr__(self):
        return f"<EmissionActivity {self.id} - {self.scope.value} - {self.activity_type.value} - {self.status.value}>"
    
    def get_calculation_value(self):
        """
        Get the value to use in emission calculation based on activity type
        
        Returns:
            float: Value to multiply by emission factor
        """
        if self.activity_type == ActivityType.TRANSPORT:
            if self.tonnage is not None and self.distance is not None:
                return self.tonnage * self.distance  # tonne-km
            else:
                raise ValueError("Transport activity missing tonnage or distance")
        else:
            # For SIMPLE, PROCESS, FUGITIVE: use value from activity_data
            if self.activity_data and 'value' in self.activity_data:
                return float(self.activity_data['value'])
            else:
                raise ValueError("Activity data missing 'value' field")
    
    def to_dict(self):
        """Convert emission activity to dictionary for API responses"""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'created_by_id': self.created_by_id,
            'scope': self.scope.value if self.scope else None,
            'category': self.category,
            'activity_type': self.activity_type.value if self.activity_type else None,
            'description': self.description,
            'activity_data': self.activity_data,
            'quantity': self.quantity,
            'quantity_unit': self.quantity_unit,
            'emission_factor_id': self.emission_factor_id,
            'co2e_result': self.co2e_result,
            'co2e_tonnes': round(self.co2e_result / 1000, 4) if self.co2e_result else None,
            'status': self.status.value if self.status else None,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'tonnage': self.tonnage,
            'distance': self.distance,
            'transport_mode': self.transport_mode,
            'ademe_factor_id': self.ademe_factor_id,
            'ademe_factor_name': self.ademe_factor_name,
            'ademe_factor_value': self.ademe_factor_value,
            'ademe_factor_unit': self.ademe_factor_unit,
            'ademe_factor_source': self.ademe_factor_source,
            'ademe_factor_category': self.ademe_factor_category,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by_name': self.created_by.full_name if self.created_by else None,
        }
