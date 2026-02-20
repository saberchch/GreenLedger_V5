"""
ADEME Emission Factors Seed Data
Seeds the database with representative ADEME Base Carbone emission factors
covering major industrial activities across all scopes.

Data source: ADEME Base Carbone V23.6
"""

from app.extensions import db
from app.models.emission_factor import EmissionFactor
from app.models.emission_factor_database import EmissionFactorDatabase


def seed_ademe_emission_factors():
    """
    Seed database with representative ADEME emission factors
    
    Categories covered:
    - Combustion (Scope 1): Natural gas, diesel, coal, fuel oil
    - Electricity (Scope 2): Grid electricity (France, EU)
    - Transport (Scope 3): Truck, rail, ship, air freight
    - Process Emissions (Scope 1): Cement calcination, chemical reactions
    - Materials (Scope 3): Steel, concrete, plastics
    - Waste (Scope 3): Landfill, incineration
    """
    
    print("🌱 Seeding ADEME emission factors...")
    
    # Check if ADEME factors already exist
    existing_count = EmissionFactor.query.filter_by(database_source=EmissionFactorDatabase.ADEME).count()
    if existing_count > 0:
        print(f"⚠️  Found {existing_count} existing ADEME factors. Skipping seed.")
        return
    
    factors = []
    
    # ============================================================================
    # SCOPE 1: DIRECT EMISSIONS
    # ============================================================================
    
    # --- Combustion (Stationary) ---
    factors.extend([
        {
            'name': 'Gaz naturel - Combustion fixe',
            'factor': 227.0,  # kgCO2e/MWh PCI
            'unit': 'MWh',
            'category': 'Combustion',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 1,
            'poste_emission': 'Combustion fixe',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Direct',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_GAS_NAT_001',
            'notes': 'Natural gas combustion in stationary equipment (boilers, furnaces)'
        },
        {
            'name': 'Fioul lourd - Combustion fixe',
            'factor': 324.0,  # kgCO2e/MWh PCI
            'unit': 'MWh',
            'category': 'Combustion',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 1,
            'poste_emission': 'Combustion fixe',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Direct',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_FUEL_HEAVY_001',
            'notes': 'Heavy fuel oil combustion in industrial boilers'
        },
        {
            'name': 'Charbon - Combustion fixe',
            'factor': 384.0,  # kgCO2e/MWh PCI
            'unit': 'MWh',
            'category': 'Combustion',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 1,
            'poste_emission': 'Combustion fixe',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Direct',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_COAL_001',
            'notes': 'Coal combustion in industrial facilities'
        },
        {
            'name': 'Gazole non routier (GNR)',
            'factor': 3180.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Combustion',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 1,
            'poste_emission': 'Combustion mobile',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Direct',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_DIESEL_NR_001',
            'notes': 'Non-road diesel for mobile equipment (construction, agriculture)'
        },
    ])
    
    # --- Process Emissions ---
    factors.extend([
        {
            'name': 'Calcination du calcaire (CaCO3)',
            'factor': 440.0,  # kgCO2/tonne CaCO3
            'unit': 'tonne',
            'category': 'Process',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 1,
            'poste_emission': 'Procédés industriels - émissions non énergétiques',
            'gaz': 'CO2',
            'perimetre': 'Direct',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_CALC_LIME_001',
            'notes': 'CO2 emissions from limestone calcination (major source in cement production)'
        },
        {
            'name': 'Production de ciment - Clinker',
            'factor': 866.0,  # kgCO2e/tonne clinker
            'unit': 'tonne',
            'category': 'Process',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 1,
            'poste_emission': 'Procédés industriels - émissions non énergétiques',
            'gaz': 'CO2',
            'perimetre': 'Direct',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_CEMENT_CLINKER_001',
            'notes': 'Process emissions from clinker production (includes calcination)'
        },
    ])
    
    # --- Fugitive Emissions ---
    factors.extend([
        {
            'name': 'Fuite de R-410A (climatisation)',
            'factor': 2088000.0,  # kgCO2e/tonne (GWP = 2088)
            'unit': 'kg',
            'category': 'Fugitive',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 1,
            'poste_emission': 'Émissions fugitives',
            'gaz': 'HFC',
            'perimetre': 'Direct',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_FUGITIVE_R410A_001',
            'notes': 'Refrigerant R-410A leakage from air conditioning systems'
        },
    ])
    
    # ============================================================================
    # SCOPE 2: INDIRECT EMISSIONS - ENERGY
    # ============================================================================
    
    factors.extend([
        {
            'name': 'Électricité - Mix France',
            'factor': 52.0,  # kgCO2e/MWh
            'unit': 'MWh',
            'category': 'Electricity',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 2,
            'poste_emission': 'Électricité',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect - Énergie',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_ELEC_FR_001',
            'notes': 'French electricity grid mix (low carbon due to nuclear)'
        },
        {
            'name': 'Électricité - Mix Europe',
            'factor': 429.0,  # kgCO2e/MWh
            'unit': 'MWh',
            'category': 'Electricity',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'EU',
            'scope': 2,
            'poste_emission': 'Électricité',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect - Énergie',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_ELEC_EU_001',
            'notes': 'European electricity grid mix'
        },
        {
            'name': 'Vapeur - Réseau de chaleur',
            'factor': 186.0,  # kgCO2e/MWh
            'unit': 'MWh',
            'category': 'Heating',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 2,
            'poste_emission': 'Énergie - Réseau de chaleur',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect - Énergie',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_STEAM_NETWORK_001',
            'notes': 'Steam from district heating network'
        },
    ])
    
    # ============================================================================
    # SCOPE 3: OTHER INDIRECT EMISSIONS
    # ============================================================================
    
    # --- Transport (Freight) ---
    factors.extend([
        {
            'name': 'Transport routier - Poids lourd >32t',
            'factor': 0.0937,  # kgCO2e/tonne-km
            'unit': 'tonne-km',
            'category': 'Transport',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Fret',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_TRUCK_HEAVY_001',
            'notes': 'Heavy truck freight >32 tonnes'
        },
        {
            'name': 'Transport routier - Poids lourd 3.5-32t',
            'factor': 0.188,  # kgCO2e/tonne-km
            'unit': 'tonne-km',
            'category': 'Transport',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Fret',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_TRUCK_MEDIUM_001',
            'notes': 'Medium truck freight 3.5-32 tonnes'
        },
        {
            'name': 'Transport ferroviaire - Fret',
            'factor': 0.0297,  # kgCO2e/tonne-km
            'unit': 'tonne-km',
            'category': 'Transport',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Fret',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_RAIL_FREIGHT_001',
            'notes': 'Rail freight transport'
        },
        {
            'name': 'Transport maritime - Porte-conteneurs',
            'factor': 0.0115,  # kgCO2e/tonne-km
            'unit': 'tonne-km',
            'category': 'Transport',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'Global',
            'scope': 3,
            'poste_emission': 'Fret',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_SHIP_CONTAINER_001',
            'notes': 'Container ship freight transport'
        },
        {
            'name': 'Transport aérien - Fret',
            'factor': 1.53,  # kgCO2e/tonne-km
            'unit': 'tonne-km',
            'category': 'Transport',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'Global',
            'scope': 3,
            'poste_emission': 'Fret',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_AIR_FREIGHT_001',
            'notes': 'Air freight transport'
        },
    ])
    
    # --- Materials (Upstream) ---
    factors.extend([
        {
            'name': 'Acier - Production primaire',
            'factor': 2270.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Materials',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'EU',
            'scope': 3,
            'poste_emission': 'Achats de biens',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_STEEL_PRIMARY_001',
            'notes': 'Primary steel production (blast furnace)'
        },
        {
            'name': 'Acier - Recyclé',
            'factor': 630.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Materials',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'EU',
            'scope': 3,
            'poste_emission': 'Achats de biens',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_STEEL_RECYCLED_001',
            'notes': 'Recycled steel production (electric arc furnace)'
        },
        {
            'name': 'Béton - Prêt à l\'emploi',
            'factor': 235.0,  # kgCO2e/m³
            'unit': 'm³',
            'category': 'Materials',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Achats de biens',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_CONCRETE_RMC_001',
            'notes': 'Ready-mix concrete (includes cement, aggregates, water)'
        },
        {
            'name': 'Ciment - CEM I (Portland)',
            'factor': 866.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Materials',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Achats de biens',
            'gaz': 'CO2',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_CEMENT_CEM1_001',
            'notes': 'Portland cement CEM I (95-100% clinker)'
        },
        {
            'name': 'Plastique - PET',
            'factor': 2150.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Materials',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'EU',
            'scope': 3,
            'poste_emission': 'Achats de biens',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_PLASTIC_PET_001',
            'notes': 'PET plastic production'
        },
        {
            'name': 'Aluminium - Production primaire',
            'factor': 8240.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Materials',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'EU',
            'scope': 3,
            'poste_emission': 'Achats de biens',
            'gaz': 'CO2, CH4, N2O, PFC',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_ALUMINUM_PRIMARY_001',
            'notes': 'Primary aluminum production (electrolysis)'
        },
    ])
    
    # --- Waste (Downstream) ---
    factors.extend([
        {
            'name': 'Déchets - Enfouissement (décharge)',
            'factor': 543.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Waste',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Fin de vie',
            'gaz': 'CO2, CH4',
            'perimetre': 'Indirect aval',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_WASTE_LANDFILL_001',
            'notes': 'Landfill disposal of mixed waste'
        },
        {
            'name': 'Déchets - Incinération avec récupération d\'énergie',
            'factor': 37.0,  # kgCO2e/tonne
            'unit': 'tonne',
            'category': 'Waste',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Fin de vie',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect aval',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_WASTE_INCINERATION_001',
            'notes': 'Waste incineration with energy recovery (net emissions after energy credit)'
        },
        {
            'name': 'Déchets - Recyclage papier-carton',
            'factor': -670.0,  # kgCO2e/tonne (negative = avoided emissions)
            'unit': 'tonne',
            'category': 'Waste',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Fin de vie',
            'gaz': 'CO2',
            'perimetre': 'Indirect aval',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_WASTE_RECYCLE_PAPER_001',
            'notes': 'Paper/cardboard recycling (avoided emissions from virgin production)'
        },
    ])
    
    # --- Energy Upstream ---
    factors.extend([
        {
            'name': 'Gaz naturel - Amont (extraction, transport)',
            'factor': 46.0,  # kgCO2e/MWh PCI
            'unit': 'MWh',
            'category': 'Energy Upstream',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'EU',
            'scope': 3,
            'poste_emission': 'Énergie - Amont',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_GAS_UPSTREAM_001',
            'notes': 'Upstream emissions from natural gas extraction and transport'
        },
        {
            'name': 'Électricité - Amont France',
            'factor': 6.8,  # kgCO2e/MWh
            'unit': 'MWh',
            'category': 'Energy Upstream',
            'source': 'ADEME Base Carbone V23.6',
            'year': 2023,
            'region': 'FR',
            'scope': 3,
            'poste_emission': 'Énergie - Amont',
            'gaz': 'CO2, CH4, N2O',
            'perimetre': 'Indirect amont',
            'database_source': EmissionFactorDatabase.ADEME,
            'ademe_id': 'ADEME_ELEC_UPSTREAM_FR_001',
            'notes': 'Upstream emissions from French electricity production (fuel extraction, infrastructure)'
        },
    ])
    
    # Create EmissionFactor objects
    emission_factors = []
    for factor_data in factors:
        ef = EmissionFactor(**factor_data)
        emission_factors.append(ef)
    
    # Bulk insert
    db.session.bulk_save_objects(emission_factors)
    db.session.commit()
    
    print(f"✅ Successfully seeded {len(emission_factors)} ADEME emission factors")
    print(f"   - Scope 1 (Direct): {sum(1 for f in factors if f['scope'] == 1)} factors")
    print(f"   - Scope 2 (Indirect - Energy): {sum(1 for f in factors if f['scope'] == 2)} factors")
    print(f"   - Scope 3 (Other Indirect): {sum(1 for f in factors if f['scope'] == 3)} factors")
    
    return len(emission_factors)


if __name__ == '__main__':
    from app.factory import create_app
    
    app = create_app()
    with app.app_context():
        seed_ademe_emission_factors()
