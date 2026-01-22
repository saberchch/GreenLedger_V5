from app.extensions import db
from app.models.base import BaseModel

class EmissionFactor(BaseModel):
    __tablename__ = "emission_factors"

    name = db.Column(db.String(255), nullable=False)
    factor = db.Column(db.Float, nullable=False) # kg CO2e per unit
    unit = db.Column(db.String(50), nullable=False) # e.g., "kWh", "liter", "km"
    category = db.Column(db.String(100), nullable=False, index=True) # e.g., "Electricity", "Fuel"
    source = db.Column(db.String(255)) # e.g., "EPA 2024"
    year = db.Column(db.Integer)
    region = db.Column(db.String(100)) # e.g., "US", "EU", "Global"

    def __repr__(self):
        return f"<EmissionFactor {self.name} ({self.unit})>"
