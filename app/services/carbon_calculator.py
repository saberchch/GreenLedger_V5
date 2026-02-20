"""
Carbon Calculation Engine
Implements ADEME-compliant carbon footprint calculations
Uses CSV-based emission factors instead of database
"""

from typing import Optional, Dict, Any
from app.models.emission_activity import EmissionActivity, ActivityType
from app.services.emission_factor_loader import EmissionFactorData, get_loader


class CarbonCalculator:
    """
    Carbon calculation engine implementing ADEME methodology
    
    Formula: Emissions (tCO₂e) = Activity Value × Emission Factor / 1000
    
    Supports multiple calculation types:
    - SIMPLE: value × emission_factor
    - TRANSPORT: tonnage × distance × emission_factor
    - PROCESS: mass × emission_factor
    - FUGITIVE: leakage_mass × GWP
    """
    
    @staticmethod
    def calculate_emissions(activity: EmissionActivity, factor: EmissionFactorData) -> float:
        """
        Calculate emissions for an activity based on its type
        
        Args:
            activity: EmissionActivity instance with activity data
            factor: EmissionFactorData from CSV
        
        Returns:
            float: Emissions in tCO2e (tonnes CO2 equivalent)
        
        Raises:
            ValueError: If required data is missing or invalid
        """
        # Get calculation value based on activity type
        try:
            calculation_value = activity.get_calculation_value()
        except ValueError as e:
            raise ValueError(f"Cannot calculate emissions: {str(e)}")
        
        # Validate emission factor
        if factor is None:
            raise ValueError("Emission factor is required for calculation")
        
        if factor.factor < 0 and 'recycle' not in factor.name.lower():
            # Allow negative factors for recycling (avoided emissions)
            raise ValueError(f"Invalid emission factor: {factor.factor}")
        
        # Calculate emissions: value × factor (kgCO2e)
        emissions_kg = calculation_value * factor.factor
        
        # Convert to tonnes CO2e
        emissions_tco2e = emissions_kg / 1000.0
        
        return round(emissions_tco2e, 6)  # Round to 6 decimal places
    
    @staticmethod
    def calculate_and_save(activity: EmissionActivity, factor: EmissionFactorData) -> float:
        """
        Calculate emissions and save result to activity
        
        Args:
            activity: EmissionActivity instance
            factor: EmissionFactorData from CSV
        
        Returns:
            float: Calculated emissions in tCO2e
        """
        emissions = CarbonCalculator.calculate_emissions(activity, factor)
        
        # Save result to activity (in kgCO2e for database storage)
        activity.co2e_result = emissions * 1000  # Convert back to kg for storage
        
        # Copy ADEME fields from factor for audit trail
        if factor.poste_emission:
            activity.poste_emission = factor.poste_emission
        if factor.perimetre:
            activity.perimetre = factor.perimetre
        
        return emissions
    
    @staticmethod
    def calculate_with_factor_lookup(activity: EmissionActivity, 
                                     activity_name: str, 
                                     unit: str, 
                                     scope: int) -> Optional[float]:
        """
        Find emission factor from CSV and calculate emissions
        
        Args:
            activity: EmissionActivity instance
            activity_name: Name to search for in CSV
            unit: Unit of measurement
            scope: GHG Protocol scope
        
        Returns:
            float: Emissions in tCO2e, or None if factor not found
        """
        loader = get_loader()
        factor = loader.find_factor(activity_name, unit, scope)
        
        if factor is None:
            return None
        
        return CarbonCalculator.calculate_and_save(activity, factor)
    
    @staticmethod
    def get_calculation_details(activity: EmissionActivity, factor: EmissionFactorData) -> Dict[str, Any]:
        """
        Get detailed calculation breakdown for transparency
        
        Args:
            activity: EmissionActivity instance
            factor: EmissionFactorData used
        
        Returns:
            dict: Calculation details including formula, values, and result
        """
        calculation_value = activity.get_calculation_value()
        emissions_tco2e = CarbonCalculator.calculate_emissions(activity, factor)
        
        details = {
            'activity_type': activity.activity_type.value,
            'calculation_value': calculation_value,
            'emission_factor': factor.factor,
            'unit': factor.unit,
            'emissions_kgco2e': emissions_tco2e * 1000,
            'emissions_tco2e': emissions_tco2e,
            'formula': None,
            'breakdown': {},
            'factor_info': {
                'name': factor.name,
                'source': factor.source,
                'database': factor.database_source,
                'ademe_id': factor.ademe_id,
            }
        }
        
        # Add type-specific details
        if activity.activity_type == ActivityType.TRANSPORT:
            details['formula'] = 'Emissions (tCO₂e) = tonnage × distance × emission_factor / 1000'
            details['breakdown'] = {
                'tonnage': activity.tonnage,
                'distance': activity.distance,
                'transport_mode': activity.transport_mode,
                'tonne_km': calculation_value
            }
        elif activity.activity_type == ActivityType.SIMPLE:
            details['formula'] = 'Emissions (tCO₂e) = value × emission_factor / 1000'
            details['breakdown'] = {
                'value': calculation_value
            }
        elif activity.activity_type == ActivityType.PROCESS:
            details['formula'] = 'Emissions (tCO₂e) = mass × emission_factor / 1000'
            details['breakdown'] = {
                'mass': calculation_value
            }
        elif activity.activity_type == ActivityType.FUGITIVE:
            details['formula'] = 'Emissions (tCO₂e) = leakage_mass × GWP / 1000'
            details['breakdown'] = {
                'leakage_mass': calculation_value
            }
        
        return details
    
    @staticmethod
    def validate_activity_data(activity: EmissionActivity) -> tuple[bool, Optional[str]]:
        """
        Validate that activity has all required data for calculation
        
        Args:
            activity: EmissionActivity to validate
        
        Returns:
            tuple: (is_valid, error_message)
        """
        # Check activity type specific requirements
        if activity.activity_type == ActivityType.TRANSPORT:
            if activity.tonnage is None or activity.tonnage <= 0:
                return False, "Transport activity requires positive tonnage"
            if activity.distance is None or activity.distance <= 0:
                return False, "Transport activity requires positive distance"
            if not activity.transport_mode:
                return False, "Transport activity requires transport mode"
        else:
            # For SIMPLE, PROCESS, FUGITIVE: check activity_data
            if not activity.activity_data or 'value' not in activity.activity_data:
                return False, f"{activity.activity_type.value} activity requires 'value' in activity_data"
            
            try:
                value = float(activity.activity_data['value'])
                if value < 0:
                    return False, "Activity value cannot be negative"
            except (ValueError, TypeError):
                return False, "Activity value must be a valid number"
        
        return True, None

