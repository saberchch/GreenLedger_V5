"""
Emission Factor Database Enums
Defines supported emission factor databases and activity calculation types
"""

import enum


class EmissionFactorDatabase(enum.Enum):
    """
    Supported emission factor databases
    
    This enum tracks the source database for emission factors,
    enabling support for multiple international standards and
    custom user-defined factors.
    """
    ADEME = "ademe"  # ADEME Base Carbone (France)
    GHG_PROTOCOL = "ghg_protocol"  # GHG Protocol
    EPA = "epa"  # US EPA
    DEFRA = "defra"  # UK DEFRA
    IPCC = "ipcc"  # IPCC
    CUSTOM = "custom"  # User-defined


class ActivityType(enum.Enum):
    """
    Activity calculation types
    
    Defines how emissions are calculated based on the activity type:
    - SIMPLE: Direct multiplication (value × emission factor)
    - TRANSPORT: Tonne-kilometers (tonnage × distance × emission factor)
    - PROCESS: Process emissions (mass × emission factor)
    - FUGITIVE: Fugitive emissions (leakage mass × GWP)
    """
    SIMPLE = "simple"  # value × EF (e.g., fuel consumption, electricity)
    TRANSPORT = "transport"  # tonnage × distance × EF (e.g., freight)
    PROCESS = "process"  # mass × EF (e.g., calcination, chemical reactions)
    FUGITIVE = "fugitive"  # leakage × GWP (e.g., refrigerant leaks)
