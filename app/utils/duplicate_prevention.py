"""
Advanced duplicate prevention and matching utilities.

This module provides sophisticated matching strategies to prevent duplicates
when source data changes titles, descriptions, or other identifying fields.
"""

import hashlib
import difflib
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models import Prospect
from app.utils.logger import logger

logger = logger.bind(name="utils.duplicate_prevention")

@dataclass
class MatchCandidate:
    """Represents a potential matching record with confidence scores."""
    prospect_id: str
    native_id: str
    title: str
    confidence_score: float
    match_type: str  # 'exact', 'strong', 'fuzzy', 'weak'
    matched_fields: List[str]

@dataclass
class MatchingStrategy:
    """Configuration for different matching strategies."""
    name: str
    weight: float
    min_confidence: float
    required_fields: List[str]
    optional_fields: List[str]

class DuplicateDetector:
    """
    Advanced duplicate detection with multiple fallback strategies.
    """
    
    def __init__(self):
        self.strategies = [
            # Strategy 1: Exact native_id + source match (highest confidence)
            MatchingStrategy(
                name="exact_native_id",
                weight=1.0,
                min_confidence=0.95,
                required_fields=["native_id", "source_id"],
                optional_fields=[]
            ),
            
            # Strategy 2: Strong match - native_id + similar title
            MatchingStrategy(
                name="native_id_title_fuzzy", 
                weight=0.85,
                min_confidence=0.80,
                required_fields=["native_id", "source_id"],
                optional_fields=["title"]
            ),
            
            # Strategy 3: NAICS + location + similar title (for records without native_id)
            MatchingStrategy(
                name="naics_location_title",
                weight=0.75,
                min_confidence=0.75,
                required_fields=["naics", "place_city", "place_state"],
                optional_fields=["title", "agency"]
            ),
            
            # Strategy 4: Agency + location + very similar title + similar description
            MatchingStrategy(
                name="agency_location_content",
                weight=0.70,
                min_confidence=0.70,
                required_fields=["agency", "place_city", "place_state"],
                optional_fields=["title", "description"]
            ),
            
            # Strategy 5: Fuzzy content matching (lowest confidence)
            MatchingStrategy(
                name="fuzzy_content",
                weight=0.60,
                min_confidence=0.60,
                required_fields=["title"],
                optional_fields=["description", "agency"]
            )
        ]
    
    def find_potential_matches(self, session: Session, new_record: Dict, 
                             source_id: int) -> List[MatchCandidate]:
        """
        Find potential matching records using multiple strategies.
        
        Args:
            session: SQLAlchemy session
            new_record: Dictionary containing new record data
            source_id: ID of the data source
            
        Returns:
            List of MatchCandidate objects sorted by confidence score
        """
        all_candidates = []
        
        for strategy in self.strategies:
            candidates = self._apply_strategy(session, new_record, source_id, strategy)
            all_candidates.extend(candidates)
        
        # Remove duplicates and sort by confidence
        unique_candidates = self._deduplicate_candidates(all_candidates)
        return sorted(unique_candidates, key=lambda x: x.confidence_score, reverse=True)
    
    def _apply_strategy(self, session: Session, new_record: Dict, 
                       source_id: int, strategy: MatchingStrategy) -> List[MatchCandidate]:
        """Apply a specific matching strategy."""
        candidates = []
        
        try:
            # Build base query
            query = session.query(Prospect).filter(Prospect.source_id == source_id)
            
            if strategy.name == "exact_native_id":
                candidates.extend(self._exact_native_id_match(
                    query, new_record, strategy
                ))
            
            elif strategy.name == "native_id_title_fuzzy":
                candidates.extend(self._native_id_title_fuzzy_match(
                    query, new_record, strategy
                ))
            
            elif strategy.name == "naics_location_title":
                candidates.extend(self._naics_location_title_match(
                    query, new_record, strategy
                ))
            
            elif strategy.name == "agency_location_content":
                candidates.extend(self._agency_location_content_match(
                    query, new_record, strategy
                ))
            
            elif strategy.name == "fuzzy_content":
                candidates.extend(self._fuzzy_content_match(
                    query, new_record, strategy
                ))
        
        except Exception as e:
            logger.warning(f"Error applying strategy {strategy.name}: {e}")
        
        return candidates
    
    def _exact_native_id_match(self, query, new_record: Dict, 
                              strategy: MatchingStrategy) -> List[MatchCandidate]:
        """Native_id matching with content similarity scoring."""
        native_id = new_record.get('native_id')
        if not native_id:
            return []
        
        matches = query.filter(Prospect.native_id == native_id).all()
        candidates = []
        
        for match in matches:
            # Calculate confidence based on content similarity, not just ID match
            matched_fields = ["native_id"]
            similarity_scores = []
            
            # Check title similarity
            title_sim = self._calculate_text_similarity(
                new_record.get('title', ''), match.title or ''
            )
            if title_sim > 0.7:
                matched_fields.append("title")
            similarity_scores.append(title_sim)
            
            # Check description similarity
            desc_sim = self._calculate_text_similarity(
                new_record.get('description', ''), match.description or ''
            )
            if desc_sim > 0.7:
                matched_fields.append("description")
            similarity_scores.append(desc_sim)
            
            # Check agency similarity
            agency_sim = self._calculate_text_similarity(
                new_record.get('agency', ''), match.agency or ''
            )
            if agency_sim > 0.8:
                matched_fields.append("agency")
            similarity_scores.append(agency_sim)
            
            # Check location similarity
            location_sim = 1.0 if (
                new_record.get('place_city', '').lower() == (match.place_city or '').lower() and
                new_record.get('place_state', '').lower() == (match.place_state or '').lower()
            ) else 0.0
            if location_sim > 0.5:
                matched_fields.append("location")
            similarity_scores.append(location_sim)
            
            # Calculate weighted confidence score
            # Native ID match gives base 50%, but require meaningful content similarity
            title_weight = 0.3
            desc_weight = 0.15  
            agency_weight = 0.15
            location_weight = 0.1  # Reduced location weight since many records share locations
            
            weighted_similarity = (
                title_sim * title_weight +
                desc_sim * desc_weight +
                agency_sim * agency_weight +
                location_sim * location_weight
            )
            
            # Base score of 50% for native_id match + weighted content similarity
            confidence_score = 0.5 + (weighted_similarity * 0.5)
            
            # Penalty for very low title similarity (different job titles probably aren't duplicates)
            if title_sim < 0.3:
                confidence_score *= 0.8
            
            # Penalty for very low agency similarity 
            if agency_sim < 0.3:
                confidence_score *= 0.9
            
            # Determine match type based on confidence
            if confidence_score >= 0.95:
                match_type = "exact"
            elif confidence_score >= 0.85:
                match_type = "strong"
            elif confidence_score >= 0.75:
                match_type = "fuzzy"
            else:
                match_type = "weak"
            
            candidates.append(MatchCandidate(
                prospect_id=match.id,
                native_id=match.native_id,
                title=match.title or "",
                confidence_score=confidence_score,
                match_type=match_type,
                matched_fields=matched_fields
            ))
        
        return candidates
    
    def _native_id_title_fuzzy_match(self, query, new_record: Dict,
                                   strategy: MatchingStrategy) -> List[MatchCandidate]:
        """Native ID + fuzzy title matching."""
        native_id = new_record.get('native_id')
        new_title = new_record.get('title', '')
        
        if not native_id or not new_title:
            return []
        
        matches = query.filter(Prospect.native_id == native_id).all()
        candidates = []
        
        for match in matches:
            if not match.title:
                continue
                
            title_similarity = self._calculate_text_similarity(new_title, match.title)
            if title_similarity >= 0.7:  # 70% title similarity threshold
                confidence = strategy.weight * (0.5 + 0.5 * title_similarity)
                
                if confidence >= strategy.min_confidence:
                    candidates.append(MatchCandidate(
                        prospect_id=match.id,
                        native_id=match.native_id,
                        title=match.title,
                        confidence_score=confidence,
                        match_type="strong",
                        matched_fields=["native_id", "title_fuzzy"]
                    ))
        
        return candidates
    
    def _naics_location_title_match(self, query, new_record: Dict,
                                  strategy: MatchingStrategy) -> List[MatchCandidate]:
        """NAICS + location + title similarity matching."""
        naics = new_record.get('naics')
        city = new_record.get('place_city')
        state = new_record.get('place_state')
        new_title = new_record.get('title', '')
        
        if not all([naics, city, state, new_title]):
            return []
        
        matches = query.filter(
            Prospect.naics == naics,
            Prospect.place_city == city,
            Prospect.place_state == state
        ).all()
        
        candidates = []
        for match in matches:
            if not match.title:
                continue
                
            title_similarity = self._calculate_text_similarity(new_title, match.title)
            if title_similarity >= 0.6:  # 60% title similarity for this strategy
                confidence = strategy.weight * title_similarity
                
                if confidence >= strategy.min_confidence:
                    candidates.append(MatchCandidate(
                        prospect_id=match.id,
                        native_id=match.native_id or "",
                        title=match.title,
                        confidence_score=confidence,
                        match_type="fuzzy",
                        matched_fields=["naics", "location", "title_fuzzy"]
                    ))
        
        return candidates
    
    def _agency_location_content_match(self, query, new_record: Dict,
                                     strategy: MatchingStrategy) -> List[MatchCandidate]:
        """Agency + location + content similarity matching."""
        agency = new_record.get('agency')
        city = new_record.get('place_city')
        state = new_record.get('place_state')
        new_title = new_record.get('title', '')
        new_desc = new_record.get('description', '')
        
        if not all([agency, city, state]) or not (new_title or new_desc):
            return []
        
        matches = query.filter(
            Prospect.agency == agency,
            Prospect.place_city == city,
            Prospect.place_state == state
        ).all()
        
        candidates = []
        for match in matches:
            title_sim = 0
            desc_sim = 0
            
            if match.title and new_title:
                title_sim = self._calculate_text_similarity(new_title, match.title)
            
            if match.description and new_desc:
                desc_sim = self._calculate_text_similarity(new_desc, match.description)
            
            # Require high similarity in at least one content field
            max_content_sim = max(title_sim, desc_sim)
            if max_content_sim >= 0.8:  # 80% content similarity
                confidence = strategy.weight * max_content_sim
                
                if confidence >= strategy.min_confidence:
                    matched_fields = ["agency", "location"]
                    if title_sim >= 0.8:
                        matched_fields.append("title_fuzzy")
                    if desc_sim >= 0.8:
                        matched_fields.append("description_fuzzy")
                    
                    candidates.append(MatchCandidate(
                        prospect_id=match.id,
                        native_id=match.native_id or "",
                        title=match.title or "",
                        confidence_score=confidence,
                        match_type="fuzzy",
                        matched_fields=matched_fields
                    ))
        
        return candidates
    
    def _fuzzy_content_match(self, query, new_record: Dict,
                           strategy: MatchingStrategy) -> List[MatchCandidate]:
        """Fuzzy content-only matching (last resort)."""
        new_title = new_record.get('title', '')
        new_desc = new_record.get('description', '')
        
        if not new_title:
            return []
        
        # Limit to recent records to avoid false positives
        matches = query.filter(Prospect.title.isnot(None)).limit(1000).all()
        
        candidates = []
        for match in matches:
            if not match.title:
                continue
            
            title_sim = self._calculate_text_similarity(new_title, match.title)
            
            # Very high title similarity required for content-only matching
            if title_sim >= 0.9:
                desc_sim = 0
                if match.description and new_desc:
                    desc_sim = self._calculate_text_similarity(new_desc, match.description)
                
                # Combine title and description similarity
                combined_sim = 0.7 * title_sim + 0.3 * desc_sim
                confidence = strategy.weight * combined_sim
                
                if confidence >= strategy.min_confidence:
                    candidates.append(MatchCandidate(
                        prospect_id=match.id,
                        native_id=match.native_id or "",
                        title=match.title,
                        confidence_score=confidence,
                        match_type="weak",
                        matched_fields=["title_fuzzy"]
                    ))
        
        return candidates
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1_norm = text1.lower().strip()
        text2_norm = text2.lower().strip()
        
        if text1_norm == text2_norm:
            return 1.0
        
        # Use difflib for sequence matching
        similarity = difflib.SequenceMatcher(None, text1_norm, text2_norm).ratio()
        return similarity
    
    def _deduplicate_candidates(self, candidates: List[MatchCandidate]) -> List[MatchCandidate]:
        """Remove duplicate candidates, keeping the highest confidence."""
        seen_ids = {}
        unique_candidates = []
        
        for candidate in candidates:
            existing = seen_ids.get(candidate.prospect_id)
            if not existing or candidate.confidence_score > existing.confidence_score:
                seen_ids[candidate.prospect_id] = candidate
        
        return list(seen_ids.values())

def enhanced_bulk_upsert_prospects(df_in, session: Session, source_id: int, 
                                 preserve_ai_data: bool = True,
                                 enable_smart_matching: bool = True) -> Dict:
    """
    Enhanced bulk upsert with advanced duplicate detection.
    
    Args:
        df_in: DataFrame containing prospect data
        session: SQLAlchemy session
        source_id: ID of the data source
        preserve_ai_data: Whether to preserve AI-enhanced fields
        enable_smart_matching: Whether to use advanced matching strategies
        
    Returns:
        Dictionary with processing statistics
    """
    if df_in.empty:
        logger.info("DataFrame is empty, skipping database insertion.")
        return {"processed": 0, "matched": 0, "inserted": 0, "duplicates_prevented": 0}
    
    detector = DuplicateDetector()
    stats = {
        "processed": 0,
        "matched": 0, 
        "inserted": 0,
        "duplicates_prevented": 0,
        "ai_preserved": 0
    }
    
    for _, row in df_in.iterrows():
        record_data = row.to_dict()
        stats["processed"] += 1
        
        # Generate primary hash ID
        primary_id = _generate_primary_hash(record_data, source_id)
        record_data["id"] = primary_id
        
        # Check for exact primary match first
        existing_prospect = session.query(Prospect).filter_by(id=primary_id).first()
        
        if existing_prospect:
            # Direct match found
            if preserve_ai_data and existing_prospect.ollama_processed_at:
                _update_preserving_ai_fields(existing_prospect, record_data)
                stats["ai_preserved"] += 1
            else:
                _update_all_fields(existing_prospect, record_data)
            stats["matched"] += 1
        
        elif enable_smart_matching:
            # No exact match, try advanced matching
            potential_matches = detector.find_potential_matches(session, record_data, source_id)
            
            if potential_matches and potential_matches[0].confidence_score >= 0.80:
                # High-confidence match found
                best_match = potential_matches[0]
                existing_prospect = session.query(Prospect).filter_by(id=best_match.prospect_id).first()
                
                if existing_prospect:
                    logger.info(f"Smart match found: {best_match.match_type} confidence={best_match.confidence_score:.2f}")
                    
                    if preserve_ai_data and existing_prospect.ollama_processed_at:
                        _update_preserving_ai_fields(existing_prospect, record_data)
                        stats["ai_preserved"] += 1
                    else:
                        _update_all_fields(existing_prospect, record_data)
                    
                    stats["duplicates_prevented"] += 1
                    stats["matched"] += 1
                else:
                    # Insert as new
                    _insert_new_prospect(session, record_data)
                    stats["inserted"] += 1
            else:
                # No good match, insert as new
                _insert_new_prospect(session, record_data)
                stats["inserted"] += 1
        else:
            # Smart matching disabled, insert as new
            _insert_new_prospect(session, record_data)
            stats["inserted"] += 1
    
    try:
        session.commit()
        logger.info(f"Enhanced upsert completed: {stats}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error during enhanced upsert: {e}")
        raise
    
    return stats

def _generate_primary_hash(record_data: Dict, source_id: int) -> str:
    """Generate primary hash ID for a record."""
    # Use key fields for hashing
    key_fields = ['native_id', 'title', 'description', 'naics', 'agency', 'place_city', 'place_state']
    hash_parts = [str(source_id)]
    
    for field in key_fields:
        value = record_data.get(field, '')
        hash_parts.append(str(value) if value is not None else '')
    
    hash_string = '-'.join(hash_parts)
    return hashlib.md5(hash_string.encode('utf-8')).hexdigest()

def _update_preserving_ai_fields(existing_prospect: Prospect, new_data: Dict):
    """Update prospect while preserving AI-enhanced fields."""
    ai_fields = {
        'naics', 'naics_description', 'naics_source',
        'estimated_value_min', 'estimated_value_max', 'estimated_value_single',
        'primary_contact_email', 'primary_contact_name',
        'ollama_processed_at', 'ollama_model_version'
    }
    
    for key, value in new_data.items():
        if key not in ai_fields and hasattr(existing_prospect, key):
            setattr(existing_prospect, key, value)

def _update_all_fields(existing_prospect: Prospect, new_data: Dict):
    """Update all fields in prospect."""
    for key, value in new_data.items():
        if hasattr(existing_prospect, key):
            setattr(existing_prospect, key, value)

def _insert_new_prospect(session: Session, record_data: Dict):
    """Insert a new prospect record."""
    new_prospect = Prospect(**record_data)
    session.add(new_prospect)