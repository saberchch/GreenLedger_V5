"""
Emission Factor CSV Loader for Official ADEME Base Carbone
Loads emission factors from the official ADEME Base Carbone V23.6 CSV file
Includes advanced search engine with fuzzy matching for factor selection
"""

import csv
import os
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class EmissionFactorData:
    """
    Data class for emission factor loaded from ADEME Base Carbone CSV
    """
    # Core identification
    id: str  # ADEME identifier
    name_fr: str  # French name
    name_en: str  # English name
    
    # Factor value and unit
    factor: float  # Total CO2e in kgCO2e per unit
    unit_fr: str  # Unit in French
    unit_en: str  # Unit in English
    
    # Classification
    category: str  # Category path (e.g., "Achats de biens > Produits agro-alimentaires")
    tags_fr: str  # French tags
    tags_en: str  # English tags
    
    # Metadata
    source: str  # Data source (e.g., "AGRIBALYSE")
    geographic_location: str  # Geographic location
    validity_period: str  # Validity period
    status: str  # Status (Valide, Archivé, etc.)
    
    # GHG breakdown
    co2_fossil: Optional[float] = None  # CO2 fossil
    ch4_fossil: Optional[float] = None  # CH4 fossil
    ch4_bio: Optional[float] = None  # CH4 biogenic
    n2o: Optional[float] = None  # N2O
    co2_bio: Optional[float] = None  # CO2 biogenic
    other_ghg: Optional[float] = None  # Other GHG
    
    # Additional info
    comment_fr: Optional[str] = None  # French comment
    comment_en: Optional[str] = None  # English comment
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name_fr': self.name_fr,
            'name_en': self.name_en,
            'factor': self.factor,
            'unit_fr': self.unit_fr,
            'unit_en': self.unit_en,
            'category': self.category,
            'tags_fr': self.tags_fr,
            'tags_en': self.tags_en,
            'source': self.source,
            'geographic_location': self.geographic_location,
            'validity_period': self.validity_period,
            'status': self.status,
            'co2_fossil': self.co2_fossil,
            'ch4_fossil': self.ch4_fossil,
            'ch4_bio': self.ch4_bio,
            'n2o': self.n2o,
            'co2_bio': self.co2_bio,
            'other_ghg': self.other_ghg,
            'comment_fr': self.comment_fr,
            'comment_en': self.comment_en,
        }


class EmissionFactorSearchEngine:
    """
    Advanced search engine for emission factors with fuzzy matching
    Prepares for future AI-powered automatic factor selection
    """
    
    def __init__(self, factors: List[EmissionFactorData]):
        """Initialize search engine with factors"""
        self.factors = factors
        self._build_indexes()
    
    def _build_indexes(self):
        """Build search indexes for fast lookups"""
        self.by_id = {f.id: f for f in self.factors}
        self.by_category = {}
        self.by_source = {}
        
        for factor in self.factors:
            # Index by category
            if factor.category not in self.by_category:
                self.by_category[factor.category] = []
            self.by_category[factor.category].append(factor)
            
            # Index by source
            if factor.source not in self.by_source:
                self.by_source[factor.source] = []
            self.by_source[factor.source].append(factor)
    
    def search(self, query: str, language: str = 'fr', max_results: int = 20) -> List[Tuple[EmissionFactorData, float]]:
        """
        Search for emission factors with fuzzy matching
        
        Args:
            query: Search query
            language: 'fr' or 'en'
            max_results: Maximum number of results to return
        
        Returns:
            List of (factor, score) tuples, sorted by relevance score (0-1)
        """
        query_lower = query.lower()
        results = []
        
        for factor in self.factors:
            # Skip archived factors
            if factor.status == 'Archivé':
                continue
            
            # Get name based on language
            name = factor.name_fr if language == 'fr' else factor.name_en
            tags = factor.tags_fr if language == 'fr' else factor.tags_en
            
            # Calculate relevance score
            score = 0.0
            
            # Exact match in name (highest priority)
            if query_lower in name.lower():
                score += 1.0
            
            # Fuzzy match in name
            name_similarity = SequenceMatcher(None, query_lower, name.lower()).ratio()
            score += name_similarity * 0.8
            
            # Match in tags
            if tags and query_lower in tags.lower():
                score += 0.5
            
            # Match in category
            if query_lower in factor.category.lower():
                score += 0.3
            
            # Only include if score is above threshold
            if score > 0.2:
                results.append((factor, score))
        
        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:max_results]
    
    def search_by_category(self, category: str, exact: bool = False) -> List[EmissionFactorData]:
        """
        Search factors by category
        
        Args:
            category: Category to search for
            exact: If True, exact match; if False, partial match
        
        Returns:
            List of matching factors
        """
        if exact:
            return self.by_category.get(category, [])
        else:
            results = []
            category_lower = category.lower()
            for cat, factors in self.by_category.items():
                if category_lower in cat.lower():
                    results.extend(factors)
            return results
    
    def search_by_source(self, source: str) -> List[EmissionFactorData]:
        """Get all factors from a specific source"""
        return self.by_source.get(source, [])
    
    def get_by_id(self, factor_id: str) -> Optional[EmissionFactorData]:
        """Get factor by ADEME ID"""
        return self.by_id.get(factor_id)
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        return sorted(list(self.by_category.keys()))
    
    def get_sources(self) -> List[str]:
        """Get all unique sources"""
        return sorted(list(self.by_source.keys()))


class ADEMEEmissionFactorLoader:
    """
    Loads and manages emission factors from official ADEME Base Carbone CSV
    """
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize the loader
        
        Args:
            csv_path: Path to ADEME CSV file. If None, uses default
        """
        if csv_path is None:
            # Default to official ADEME CSV
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, 'data', 'Base_Carbone_V23.6.csv')
        
        self.csv_path = csv_path
        self.factors: List[EmissionFactorData] = []
        self.search_engine: Optional[EmissionFactorSearchEngine] = None
        
        if os.path.exists(csv_path):
            self.load_factors()
    
    def load_factors(self):
        """Load emission factors from official ADEME CSV"""
        self.factors = []
        
        print(f"📂 Loading ADEME Base Carbone from: {self.csv_path}")
        
        # ADEME CSV uses latin-1 encoding (ISO-8859-1)
        with open(self.csv_path, 'r', encoding='latin-1') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                try:
                    # Only load "Élément" or "Elément" type rows (actual emission factors)
                    type_ligne = row.get('Type Ligne', '').strip()
                    if type_ligne not in ['Élément', 'Elément', 'Element']:
                        continue
                    
                    # Parse total factor value
                    total_str = row.get('Total poste non décomposé', '').strip()
                    if not total_str:
                        continue
                    
                    try:
                        factor_value = float(total_str.replace(',', '.'))
                    except ValueError:
                        continue
                    
                    # Parse GHG breakdown (optional)
                    def parse_float(value: str) -> Optional[float]:
                        if not value or value.strip() == '':
                            return None
                        try:
                            return float(value.replace(',', '.'))
                        except ValueError:
                            return None
                    
                    factor = EmissionFactorData(
                        id=row.get('Identifiant de l\'élément', ''),
                        name_fr=row.get('Nom base français', ''),
                        name_en=row.get('Nom base anglais', ''),
                        factor=factor_value,
                        unit_fr=row.get('Unité français', ''),
                        unit_en=row.get('Unité anglais', ''),
                        category=row.get('Code de la catégorie', ''),
                        tags_fr=row.get('Tags français', ''),
                        tags_en=row.get('Tags anglais', ''),
                        source=row.get('Programme', ''),
                        geographic_location=row.get('Localisation géographique', ''),
                        validity_period=row.get('Période de validité', ''),
                        status=row.get('Statut de l\'élément', ''),
                        co2_fossil=parse_float(row.get('CO2f', '')),
                        ch4_fossil=parse_float(row.get('CH4f', '')),
                        ch4_bio=parse_float(row.get('CH4b', '')),
                        n2o=parse_float(row.get('N2O', '')),
                        co2_bio=parse_float(row.get('CO2b', '')),
                        other_ghg=parse_float(row.get('Autres GES', '')),
                        comment_fr=row.get('Commentaire français', ''),
                        comment_en=row.get('Commentaire anglais', ''),
                    )
                    
                    self.factors.append(factor)
                    
                except Exception as e:
                    # Skip invalid rows
                    continue
        
        # Build search engine
        self.search_engine = EmissionFactorSearchEngine(self.factors)
        
        print(f"✅ Loaded {len(self.factors)} emission factors from ADEME Base Carbone V23.6")
        
        # Print statistics
        valid_count = sum(1 for f in self.factors if f.status != 'Archivé')
        archived_count = len(self.factors) - valid_count
        print(f"   - Valid: {valid_count}")
        print(f"   - Archived: {archived_count}")
        print(f"   - Categories: {len(self.search_engine.get_categories())}")
        print(f"   - Sources: {len(self.search_engine.get_sources())}")
    
    def search(self, query: str, language: str = 'fr', max_results: int = 20) -> List[Tuple[EmissionFactorData, float]]:
        """Search for emission factors"""
        if not self.search_engine:
            return []
        return self.search_engine.search(query, language, max_results)
    
    def get_all_factors(self) -> List[EmissionFactorData]:
        """Get all loaded emission factors"""
        return self.factors
    
    def get_by_id(self, factor_id: str) -> Optional[EmissionFactorData]:
        """Get factor by ADEME ID"""
        if not self.search_engine:
            return None
        return self.search_engine.get_by_id(factor_id)


# Global loader instance (lazy-loaded)
_global_loader: Optional[ADEMEEmissionFactorLoader] = None


def get_loader() -> ADEMEEmissionFactorLoader:
    """Get global ADEME emission factor loader instance"""
    global _global_loader
    if _global_loader is None:
        _global_loader = ADEMEEmissionFactorLoader()
    return _global_loader


def reload_factors():
    """Reload emission factors from CSV"""
    global _global_loader
    if _global_loader is not None:
        _global_loader.load_factors()
