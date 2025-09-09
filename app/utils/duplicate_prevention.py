"""Advanced duplicate prevention and matching utilities.

This module provides sophisticated matching strategies to prevent duplicates
when source data changes titles, descriptions, or other identifying fields.
"""

import difflib
import hashlib
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.orm import Session

from app.config import active_config
from app.database.models import Prospect
from app.utils.logger import get_logger

logger = get_logger("utils.duplicate_prevention")


@dataclass
class MatchCandidate:
    """Represents a potential matching record with confidence scores."""

    prospect_id: str
    native_id: str
    title: str
    confidence_score: float
    match_type: str  # 'exact', 'strong', 'fuzzy', 'weak'
    matched_fields: list[str]


@dataclass
class MatchingStrategy:
    """Configuration for different matching strategies."""

    name: str
    weight: float
    min_confidence: float
    required_fields: list[str]
    optional_fields: list[str]


class DuplicateDetector:
    """Advanced duplicate detection with multiple fallback strategies."""

    def __init__(self):
        self._prospects_cache = None
        self._cache_source_id = None
        self.strategies = [
            # Strategy 1: Exact native_id + source match (highest confidence)
            MatchingStrategy(
                name="exact_native_id",
                weight=1.0,
                min_confidence=0.95,
                required_fields=["native_id", "source_id"],
                optional_fields=[],
            ),
            # Strategy 2: Strong match - native_id + similar title
            MatchingStrategy(
                name="native_id_title_fuzzy",
                weight=0.85,
                min_confidence=0.80,
                required_fields=["native_id", "source_id"],
                optional_fields=["title"],
            ),
            # Strategy 3: NAICS + location + similar title (for records without native_id)
            MatchingStrategy(
                name="naics_location_title",
                weight=0.75,
                min_confidence=0.75,
                required_fields=["naics", "place_city", "place_state"],
                optional_fields=["title", "agency"],
            ),
            # Strategy 4: Agency + location + very similar title + similar description
            MatchingStrategy(
                name="agency_location_content",
                weight=0.70,
                min_confidence=0.70,
                required_fields=["agency", "place_city", "place_state"],
                optional_fields=["title", "description"],
            ),
            # Strategy 5: Fuzzy content matching (lowest confidence)
            MatchingStrategy(
                name="fuzzy_content",
                weight=0.60,
                min_confidence=0.60,
                required_fields=["title"],
                optional_fields=["description", "agency"],
            ),
        ]

    def preload_source_prospects(self, session: Session, source_id: int):
        """Pre-load all prospects for a source to optimize batch processing."""
        if self._cache_source_id != source_id:
            # Load all prospects for this source into memory
            self._prospects_cache = {}
            prospects = (
                session.query(Prospect).filter(Prospect.source_id == source_id).all()
            )

            # Create indexes for fast lookup
            self._prospects_cache["by_native_id"] = {}
            self._prospects_cache["by_naics_location"] = {}
            self._prospects_cache["by_agency_location"] = {}
            self._prospects_cache["all"] = []

            for p in prospects:
                # Index by native_id
                if p.native_id:
                    if p.native_id not in self._prospects_cache["by_native_id"]:
                        self._prospects_cache["by_native_id"][p.native_id] = []
                    self._prospects_cache["by_native_id"][p.native_id].append(p)

                # Index by NAICS + location
                if p.naics and p.place_city and p.place_state:
                    key = f"{p.naics}|{p.place_city.lower()}|{p.place_state.lower()}"
                    if key not in self._prospects_cache["by_naics_location"]:
                        self._prospects_cache["by_naics_location"][key] = []
                    self._prospects_cache["by_naics_location"][key].append(p)

                # Index by agency + location
                if p.agency and p.place_city and p.place_state:
                    key = f"{p.agency}|{p.place_city.lower()}|{p.place_state.lower()}"
                    if key not in self._prospects_cache["by_agency_location"]:
                        self._prospects_cache["by_agency_location"][key] = []
                    self._prospects_cache["by_agency_location"][key].append(p)

                # Store all prospects for fuzzy matching
                self._prospects_cache["all"].append(p)

            self._cache_source_id = source_id
            logger.info(f"Pre-loaded {len(prospects)} prospects for source {source_id}")

    def find_potential_matches(
        self, session: Session, new_record: dict, source_id: int
    ) -> list[MatchCandidate]:
        """Find potential matching records using multiple strategies.

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

    def _apply_strategy(
        self,
        session: Session,
        new_record: dict,
        source_id: int,
        strategy: MatchingStrategy,
    ) -> list[MatchCandidate]:
        """Apply a specific matching strategy."""
        candidates = []

        try:
            # Build base query
            query = session.query(Prospect).filter(Prospect.source_id == source_id)

            # Validate required fields exist in new_record
            for field in strategy.required_fields:
                if field not in new_record or new_record.get(field) is None:
                    # Skip strategy silently - this is expected when fields are missing
                    return []

            if strategy.name == "exact_native_id":
                candidates.extend(
                    self._exact_native_id_match(query, new_record, strategy)
                )

            elif strategy.name == "native_id_title_fuzzy":
                candidates.extend(
                    self._native_id_title_fuzzy_match(query, new_record, strategy)
                )

            elif strategy.name == "naics_location_title":
                candidates.extend(
                    self._naics_location_title_match(query, new_record, strategy)
                )

            elif strategy.name == "agency_location_content":
                candidates.extend(
                    self._agency_location_content_match(query, new_record, strategy)
                )

            elif strategy.name == "fuzzy_content":
                candidates.extend(
                    self._fuzzy_content_match(query, new_record, strategy)
                )

        except Exception as e:
            logger.warning(f"Error applying strategy {strategy.name}: {e}")

        return candidates

    def _exact_native_id_match(
        self, query, new_record: dict, strategy: MatchingStrategy
    ) -> list[MatchCandidate]:
        """Native_id matching with content similarity scoring."""
        native_id = new_record.get("native_id")
        if not native_id:
            return []

        # Use cache if available
        if self._prospects_cache and "by_native_id" in self._prospects_cache:
            matches = self._prospects_cache["by_native_id"].get(native_id, [])
        else:
            matches = query.filter(Prospect.native_id == native_id).all()
        candidates = []

        for match in matches:
            # Calculate confidence based on content similarity, not just ID match
            matched_fields = ["native_id"]
            similarity_scores = []

            # Check title similarity
            title_sim = self._calculate_text_similarity(
                new_record.get("title", ""), match.title or ""
            )
            if title_sim > 0.7:
                matched_fields.append("title")
            similarity_scores.append(title_sim)

            # Check description similarity
            desc_sim = self._calculate_text_similarity(
                new_record.get("description", ""), match.description or ""
            )
            if desc_sim > 0.7:
                matched_fields.append("description")
            similarity_scores.append(desc_sim)

            # Check agency similarity
            agency_sim = self._calculate_text_similarity(
                new_record.get("agency", ""), match.agency or ""
            )
            if agency_sim > 0.8:
                matched_fields.append("agency")
            similarity_scores.append(agency_sim)

            # Check location similarity
            new_city = (new_record.get("place_city") or "").strip().lower()
            new_state = (new_record.get("place_state") or "").strip().lower()
            match_city = (match.place_city or "").strip().lower()
            match_state = (match.place_state or "").strip().lower()

            location_sim = (
                1.0
                if (
                    new_city
                    and match_city
                    and new_city == match_city
                    and new_state
                    and match_state
                    and new_state == match_state
                )
                else 0.0
            )
            if location_sim > 0.5:
                matched_fields.append("location")
            similarity_scores.append(location_sim)

            # Calculate weighted confidence score
            # For native_id matches, we need to ensure content similarity matters significantly
            # Otherwise different job postings with same ID will show as duplicates
            title_weight = 0.4  # Increased title importance
            desc_weight = 0.3  # Increased description importance
            agency_weight = 0.2
            location_weight = (
                0.1  # Reduced location weight since many records share locations
            )

            weighted_similarity = (
                title_sim * title_weight
                + desc_sim * desc_weight
                + agency_sim * agency_weight
                + location_sim * location_weight
            )

            # For native_id matches, require significant content similarity
            # This prevents false positives when IDs match but content is completely different
            min_content_sim = active_config.DUPLICATE_NATIVE_ID_MIN_CONTENT_SIM

            if title_sim < min_content_sim and desc_sim < min_content_sim:
                # If both title AND description are very different, this is likely NOT a duplicate
                # even if native_id matches (could be reused ID or different positions)
                # Set very low confidence to avoid false positives
                confidence_score = 0.1 + (weighted_similarity * 0.2)
            elif title_sim < 0.5 or desc_sim < 0.5:
                # Moderate content difference - use cautious scoring
                confidence_score = 0.3 + (weighted_similarity * 0.5)
            else:
                # Good content similarity - normal calculation
                confidence_score = 0.4 + (weighted_similarity * 0.6)

            # Strong penalties for very low content similarity
            if title_sim < 0.1:
                confidence_score *= (
                    0.5  # Halve confidence for completely different titles
                )
            elif title_sim < 0.3:
                confidence_score *= 0.7

            if desc_sim < 0.1:
                confidence_score *= (
                    0.7  # Additional penalty for completely different descriptions
                )

            if agency_sim < 0.3:
                confidence_score *= 0.85

            # Determine match type based on confidence
            if confidence_score >= 0.95:
                match_type = "exact"
            elif confidence_score >= 0.85:
                match_type = "strong"
            elif confidence_score >= 0.75:
                match_type = "fuzzy"
            else:
                match_type = "weak"

            # Ensure confidence score is capped at 1.0
            confidence_score = min(confidence_score, 1.0)

            # Only include candidates with meaningful confidence scores
            # This prevents false positives from native_id matches with completely different content
            if confidence_score >= 0.3:  # Minimum threshold
                candidates.append(
                    MatchCandidate(
                        prospect_id=match.id,
                        native_id=match.native_id,
                        title=match.title or "",
                        confidence_score=confidence_score,
                        match_type=match_type,
                        matched_fields=matched_fields,
                    )
                )

        return candidates

    def _native_id_title_fuzzy_match(
        self, query, new_record: dict, strategy: MatchingStrategy
    ) -> list[MatchCandidate]:
        """Native ID + fuzzy title matching."""
        native_id = new_record.get("native_id")
        new_title = new_record.get("title", "")

        if not native_id or not new_title:
            return []

        # Use cache if available
        if self._prospects_cache and "by_native_id" in self._prospects_cache:
            matches = self._prospects_cache["by_native_id"].get(native_id, [])
        else:
            matches = query.filter(Prospect.native_id == native_id).all()
        candidates = []

        for match in matches:
            if not match.title:
                continue

            title_similarity = self._calculate_text_similarity(new_title, match.title)
            if title_similarity >= active_config.DUPLICATE_TITLE_SIMILARITY_THRESHOLD:
                # Base confidence from native_id match (40%) + title similarity contribution
                confidence = 0.4 + (title_similarity * 0.6 * strategy.weight)
                confidence = min(confidence, 1.0)  # Cap at 1.0

                if confidence >= strategy.min_confidence:
                    candidates.append(
                        MatchCandidate(
                            prospect_id=match.id,
                            native_id=match.native_id,
                            title=match.title,
                            confidence_score=confidence,
                            match_type="strong",
                            matched_fields=["native_id", "title_fuzzy"],
                        )
                    )

        return candidates

    def _naics_location_title_match(
        self, query, new_record: dict, strategy: MatchingStrategy
    ) -> list[MatchCandidate]:
        """NAICS + location + title similarity matching."""
        naics = new_record.get("naics")
        city = new_record.get("place_city")
        state = new_record.get("place_state")
        new_title = new_record.get("title", "")

        if not all([naics, city, state, new_title]):
            return []

        # Use cache if available
        if self._prospects_cache and "by_naics_location" in self._prospects_cache:
            key = f"{naics}|{city.lower()}|{state.lower()}"
            matches = self._prospects_cache["by_naics_location"].get(key, [])
        else:
            # Use case-insensitive matching for location
            matches = query.filter(
                Prospect.naics == naics,
                Prospect.place_city.ilike(city),
                Prospect.place_state.ilike(state),
            ).all()

        candidates = []
        for match in matches:
            if not match.title:
                continue

            title_similarity = self._calculate_text_similarity(new_title, match.title)
            if title_similarity >= 0.6:  # 60% title similarity for this strategy
                # Base confidence for NAICS+location match (60%) + title similarity contribution
                confidence = 0.6 * strategy.weight + (
                    title_similarity * 0.4 * strategy.weight
                )
                confidence = min(confidence, 1.0)  # Cap at 1.0

                if confidence >= strategy.min_confidence:
                    candidates.append(
                        MatchCandidate(
                            prospect_id=match.id,
                            native_id=match.native_id or "",
                            title=match.title,
                            confidence_score=confidence,
                            match_type="fuzzy",
                            matched_fields=["naics", "location", "title_fuzzy"],
                        )
                    )

        return candidates

    def _agency_location_content_match(
        self, query, new_record: dict, strategy: MatchingStrategy
    ) -> list[MatchCandidate]:
        """Agency + location + content similarity matching."""
        agency = new_record.get("agency")
        city = new_record.get("place_city")
        state = new_record.get("place_state")
        new_title = new_record.get("title", "")
        new_desc = new_record.get("description", "")

        if not all([agency, city, state]) or not (new_title or new_desc):
            return []

        # Use cache if available
        if self._prospects_cache and "by_agency_location" in self._prospects_cache:
            key = f"{agency}|{city.lower()}|{state.lower()}"
            matches = self._prospects_cache["by_agency_location"].get(key, [])
        else:
            # Use case-insensitive matching for location
            matches = query.filter(
                Prospect.agency == agency,
                Prospect.place_city.ilike(city),
                Prospect.place_state.ilike(state),
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
                confidence = min(confidence, 1.0)  # Cap at 1.0

                if confidence >= strategy.min_confidence:
                    matched_fields = ["agency", "location"]
                    if title_sim >= 0.8:
                        matched_fields.append("title_fuzzy")
                    if desc_sim >= 0.8:
                        matched_fields.append("description_fuzzy")

                    candidates.append(
                        MatchCandidate(
                            prospect_id=match.id,
                            native_id=match.native_id or "",
                            title=match.title or "",
                            confidence_score=confidence,
                            match_type="fuzzy",
                            matched_fields=matched_fields,
                        )
                    )

        return candidates

    def _fuzzy_content_match(
        self, query, new_record: dict, strategy: MatchingStrategy
    ) -> list[MatchCandidate]:
        """Fuzzy content-only matching (last resort)."""
        new_title = new_record.get("title", "")
        new_desc = new_record.get("description", "")

        if not new_title:
            return []

        # Use cache if available, otherwise limit query
        if self._prospects_cache and "all" in self._prospects_cache:
            # Use first 1000 cached prospects to avoid O(n^2) complexity
            matches = self._prospects_cache["all"][:1000]
        else:
            # Limit to recent records to avoid false positives
            matches = query.filter(Prospect.title.isnot(None)).limit(1000).all()

        candidates = []
        for match in matches:
            if not match.title:
                continue

            title_sim = self._calculate_text_similarity(new_title, match.title)

            # Very high title similarity required for content-only matching
            if title_sim >= active_config.DUPLICATE_FUZZY_CONTENT_THRESHOLD:
                desc_sim = 0
                if match.description and new_desc:
                    desc_sim = self._calculate_text_similarity(
                        new_desc, match.description
                    )
                    # Combine title and description similarity
                    combined_sim = 0.7 * title_sim + 0.3 * desc_sim
                else:
                    # If no description to compare, use title similarity only
                    combined_sim = title_sim
                confidence = strategy.weight * combined_sim
                confidence = min(confidence, 1.0)  # Cap at 1.0

                if confidence >= strategy.min_confidence:
                    candidates.append(
                        MatchCandidate(
                            prospect_id=match.id,
                            native_id=match.native_id or "",
                            title=match.title,
                            confidence_score=confidence,
                            match_type="weak",
                            matched_fields=["title_fuzzy"],
                        )
                    )

        return candidates

    @lru_cache(maxsize=10000)
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings with caching."""
        # Handle None values explicitly
        if text1 is None or text2 is None:
            return 0.0

        # Convert to strings and check if empty
        text1_str = str(text1).strip()
        text2_str = str(text2).strip()

        if not text1_str or not text2_str:
            return 0.0

        # Normalize texts
        text1_norm = text1_str.lower()
        text2_norm = text2_str.lower()

        if text1_norm == text2_norm:
            return 1.0

        # Handle very short strings (less than 3 characters)
        if len(text1_norm) < 3 or len(text2_norm) < 3:
            # For very short strings, check if one is contained in the other
            # This helps with cases like "IT" vs "I.T." or "AI" vs "A.I."
            if text1_norm in text2_norm or text2_norm in text1_norm:
                return 0.9  # High similarity for contained short strings
            # Check without punctuation
            text1_alpha = "".join(c for c in text1_norm if c.isalnum())
            text2_alpha = "".join(c for c in text2_norm if c.isalnum())
            if text1_alpha == text2_alpha and text1_alpha:
                return 0.95  # Very high similarity for same alphanumeric content
            return 1.0 if text1_norm == text2_norm else 0.0

        # Use difflib for sequence matching
        similarity = difflib.SequenceMatcher(None, text1_norm, text2_norm).ratio()
        return similarity

    def _deduplicate_candidates(
        self, candidates: list[MatchCandidate]
    ) -> list[MatchCandidate]:
        """Remove duplicate candidates, keeping the highest confidence."""
        seen_ids = {}

        for candidate in candidates:
            existing = seen_ids.get(candidate.prospect_id)
            if not existing or candidate.confidence_score > existing.confidence_score:
                seen_ids[candidate.prospect_id] = candidate

        return list(seen_ids.values())


def enhanced_bulk_upsert_prospects(
    df_in,
    session: Session,
    source_id: int = None,
    preserve_ai_data: bool = True,
    enable_smart_matching: bool = True,
) -> dict:
    """Enhanced bulk upsert with advanced duplicate detection.

    Args:
        df_in: DataFrame containing prospect data
        session: SQLAlchemy session
        source_id: ID of the data source (optional, will extract from data if not provided)
        preserve_ai_data: Whether to preserve AI-enhanced fields
        enable_smart_matching: Whether to use advanced matching strategies

    Returns:
        Dictionary with processing statistics
    """
    if df_in.empty:
        logger.info("DataFrame is empty, skipping database insertion.")
        return {"processed": 0, "matched": 0, "inserted": 0, "duplicates_prevented": 0, "ai_preserved": 0}

    # Extract source_id from data if not provided
    if source_id is None and not df_in.empty:
        source_id = df_in.iloc[0].get("source_id")
        if source_id is None:
            logger.warning("No source_id found in data, smart matching will be limited")
    
    # Convert DataFrame to list of dicts
    records = df_in.to_dict(orient="records")
    
    # Remove duplicates within the batch
    records = _remove_batch_duplicates(records)
    
    stats = {
        "processed": 0,
        "matched": 0,
        "updated": 0,  # Alias for matched, kept for backward compatibility
        "inserted": 0,
        "duplicates_prevented": 0,
        "ai_preserved": 0,
    }

    # If smart matching is disabled, use batch processing for better performance
    if not enable_smart_matching:
        return _batch_upsert_without_smart_matching(
            session, records, source_id, preserve_ai_data, stats
        )
    
    # Smart matching enabled - use row-by-row processing
    detector = DuplicateDetector()

    for record_data in records:
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
            stats["updated"] += 1  # Backward compatibility

        elif enable_smart_matching:
            # No exact match, try advanced matching
            potential_matches = detector.find_potential_matches(
                session, record_data, source_id
            )

            if (
                potential_matches
                and potential_matches[0].confidence_score
                >= active_config.DUPLICATE_MIN_CONFIDENCE
            ):
                # High-confidence match found
                best_match = potential_matches[0]
                existing_prospect = (
                    session.query(Prospect).filter_by(id=best_match.prospect_id).first()
                )

                if existing_prospect:
                    logger.info(
                        f"Smart match found: {best_match.match_type} confidence={best_match.confidence_score:.2f}"
                    )

                    if preserve_ai_data and existing_prospect.ollama_processed_at:
                        _update_preserving_ai_fields(existing_prospect, record_data)
                        stats["ai_preserved"] += 1
                    else:
                        _update_all_fields(existing_prospect, record_data)

                    stats["duplicates_prevented"] += 1
                    stats["matched"] += 1
                    stats["updated"] += 1  # Backward compatibility
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


def _remove_batch_duplicates(records: list[dict]) -> list[dict]:
    """Remove duplicate records within the same batch based on ID."""
    seen_ids = set()
    unique_records = []
    duplicates_count = 0
    
    for record in records:
        record_id = record.get("id")
        if record_id:
            if record_id not in seen_ids:
                seen_ids.add(record_id)
                unique_records.append(record)
            else:
                duplicates_count += 1
        else:
            # Records without ID are kept (will be assigned ID later)
            unique_records.append(record)
    
    if duplicates_count > 0:
        logger.warning(f"Removed {duplicates_count} duplicate records within the same batch")
    
    return unique_records


def _batch_upsert_without_smart_matching(
    session: Session,
    records: list[dict],
    source_id: int,
    preserve_ai_data: bool,
    stats: dict,
) -> dict:
    """Optimized batch upsert when smart matching is disabled."""
    logger.info(f"Performing batch upsert for {len(records)} records")
    
    # Generate IDs for all records
    for record in records:
        if "id" not in record or not record["id"]:
            record["id"] = _generate_primary_hash(record, source_id or 0)
    
    # Extract all IDs
    ids_to_upsert = [r["id"] for r in records if r.get("id")]
    
    if not ids_to_upsert:
        logger.warning("No valid IDs found in records")
        return stats
    
    # Get existing records
    existing_records = session.query(Prospect).filter(
        Prospect.id.in_(ids_to_upsert)
    ).all()
    existing_map = {r.id: r for r in existing_records}
    
    # Separate updates and inserts
    records_to_update = []
    records_to_insert = []
    
    for record in records:
        record_id = record.get("id")
        if record_id in existing_map:
            existing = existing_map[record_id]
            if preserve_ai_data and existing.ollama_processed_at:
                # Preserve AI fields
                _update_preserving_ai_fields(existing, record)
                stats["ai_preserved"] += 1
            else:
                # Update all fields
                _update_all_fields(existing, record)
            stats["matched"] += 1
            stats["updated"] += 1  # Backward compatibility
        else:
            records_to_insert.append(record)
            stats["inserted"] += 1
    
    # Bulk insert new records
    if records_to_insert:
        # Use bulk_insert_mappings for better performance
        session.bulk_insert_mappings(Prospect, records_to_insert)
        logger.info(f"Bulk inserted {len(records_to_insert)} new records")
    
    stats["processed"] = len(records)
    
    try:
        session.commit()
        logger.info(f"Batch upsert completed: {stats}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error during batch upsert: {e}")
        raise
    
    return stats


def _generate_primary_hash(record_data: dict, source_id: int) -> str:
    """Generate primary hash ID for a record."""
    # Use key fields for hashing
    key_fields = [
        "native_id",
        "title",
        "description",
        "naics",
        "agency",
        "place_city",
        "place_state",
    ]
    hash_parts = [str(source_id)]

    for field in key_fields:
        value = record_data.get(field, "")
        hash_parts.append(str(value) if value is not None else "")

    hash_string = "-".join(hash_parts)
    return hashlib.md5(hash_string.encode("utf-8")).hexdigest()


def _update_preserving_ai_fields(existing_prospect: Prospect, new_data: dict):
    """Update prospect while preserving AI-enhanced fields."""
    for key, value in new_data.items():
        if key not in active_config.AI_PRESERVED_FIELDS and hasattr(existing_prospect, key):
            setattr(existing_prospect, key, value)


def _update_all_fields(existing_prospect: Prospect, new_data: dict):
    """Update all fields in prospect."""
    for key, value in new_data.items():
        if hasattr(existing_prospect, key):
            setattr(existing_prospect, key, value)


def _insert_new_prospect(session: Session, record_data: dict):
    """Insert a new prospect record."""
    new_prospect = Prospect(**record_data)
    session.add(new_prospect)
