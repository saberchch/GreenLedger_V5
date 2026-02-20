from app.extensions import db
from app.models.base import BaseModel
from app.models.emission_factor_database import EmissionFactorDatabase


class EmissionFactor(BaseModel):
    """
    Emission Factor Model
    
    Stores emission factors from various databases (ADEME, GHG Protocol, EPA, etc.)
    with support for ADEME-specific fields while maintaining backward compatibility.
    
    Core fields:
        name: Activity name/description
        factor: Emission factor in kgCO2e per unit
        unit: Unit of measurement (e.g., "kWh", "liter", "km", "tonne-km")
        category: Activity category (e.g., "Electricity", "Fuel", "Transport")
        source: Data source (e.g., "EPA 2024", "ADEME Base Carbone V23.6")
        year: Year of the emission factor
        region: Geographic region (e.g., "US", "EU", "Global", "FR")
    
    ADEME-specific fields (nullable for other databases):
        scope: GHG Protocol scope (1, 2, or 3)
        poste_emission: ADEME emission post classification
        gaz: Gases concerned (e.g., "CO2", "CO2,CH4,N2O")
        perimetre: ADEME perimeter (e.g., "Direct", "Indirect amont", "Indirect aval")
        database_source: Source database enum
        ademe_id: ADEME unique identifier
        notes: Additional metadata and comments
    """
    __tablename__ = "emission_factors"

    # Core fields (required)
    name = db.Column(db.String(255), nullable=False, index=True)
    factor = db.Column(db.Float, nullable=False)  # kgCO2e per unit
    unit = db.Column(db.String(50), nullable=False)  # e.g., "kWh", "liter", "km", "tonne-km"
    category = db.Column(db.String(100), nullable=False, index=True)  # e.g., "Electricity", "Fuel"
    source = db.Column(db.String(255))  # e.g., "EPA 2024", "ADEME Base Carbone V23.6"
    year = db.Column(db.Integer)
    region = db.Column(db.String(100))  # e.g., "US", "EU", "Global", "FR"
    
    # ADEME-specific fields (nullable for backward compatibility)
    scope = db.Column(db.Integer, nullable=True, index=True)  # 1, 2, or 3 (GHG Protocol)
    poste_emission = db.Column(db.String(255), nullable=True)  # ADEME emission post
    gaz = db.Column(db.String(100), nullable=True)  # Gases (CO2, CH4, N2O, HFC)
    perimetre = db.Column(db.String(100), nullable=True)  # Direct, Indirect amont, Indirect aval
    database_source = db.Column(
        db.Enum(EmissionFactorDatabase), 
        default=EmissionFactorDatabase.CUSTOM,
        nullable=False,
        index=True
    )
    ademe_id = db.Column(db.String(50), nullable=True, unique=True)  # ADEME identifier
    notes = db.Column(db.Text, nullable=True)  # Additional metadata

    def __repr__(self):
        return f"<EmissionFactor {self.name} ({self.unit}) - {self.database_source.value}>"
    
    def to_dict(self):
        """Convert emission factor to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'factor': self.factor,
            'unit': self.unit,
            'category': self.category,
            'source': self.source,
            'year': self.year,
            'region': self.region,
            'scope': self.scope,
            'poste_emission': self.poste_emission,
            'gaz': self.gaz,
            'perimetre': self.perimetre,
            'database_source': self.database_source.value if self.database_source else None,
            'ademe_id': self.ademe_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
