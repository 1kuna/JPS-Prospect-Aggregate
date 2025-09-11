"""
Centralized test factories for deterministic test data generation.

These factories provide predictable, consistent test data without randomness.
All data is generated deterministically based on counters and indices.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

UTC = timezone.utc

# Global counters for unique IDs
_counters = {
    "prospect": 0,
    "data_source": 0,
    "user": 0,
    "decision": 0,
}


def reset_counters():
    """Reset all counters - useful for test isolation."""
    global _counters
    for key in _counters:
        _counters[key] = 0


class ProspectFactory:
    """Factory for creating deterministic Prospect test data."""
    
    # Predefined values for variety
    TITLES = [
        "Software Development Services",
        "Cloud Infrastructure Management",
        "Data Analytics Platform",
        "Cybersecurity Assessment",
        "Network Infrastructure Upgrade",
        "AI/ML Research Services",
        "Database Administration",
        "Web Application Development",
    ]
    
    AGENCIES = [
        "Department of Defense",
        "Health and Human Services",
        "Department of Commerce",
        "Department of Energy",
        "Department of State",
        "Social Security Administration",
        "Department of Treasury",
        "Department of Transportation",
    ]
    
    NAICS_CODES = ["541511", "541512", "541519", "517311", "518210", "541611"]
    
    CITIES = ["Washington", "New York", "San Francisco", "Austin", "Chicago"]
    STATES = ["DC", "NY", "CA", "TX", "IL"]
    
    SET_ASIDES = ["Small Business", "8(a) Set-Aside", "WOSB Set-Aside", "Full and Open"]
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a deterministic prospect with optional overrides."""
        global _counters
        idx = _counters["prospect"]
        _counters["prospect"] += 1
        
        # Generate deterministic values based on index
        defaults = {
            "id": f"PROSPECT-{idx:04d}",
            "native_id": f"NATIVE-{idx:04d}",
            "title": ProspectFactory.TITLES[idx % len(ProspectFactory.TITLES)] + f" {idx}",
            "description": f"Description for prospect {idx} with detailed requirements and specifications",
            "agency": ProspectFactory.AGENCIES[idx % len(ProspectFactory.AGENCIES)],
            "naics": ProspectFactory.NAICS_CODES[idx % len(ProspectFactory.NAICS_CODES)] if idx % 5 != 0 else None,
            "estimated_value_text": f"${(idx + 1) * 10000:,}" if idx % 3 != 0 else "TBD",
            "estimated_value_single": (idx + 1) * 10000 if idx % 3 != 0 else None,
            "posted_date": (datetime.now(UTC).date() - timedelta(days=idx)).isoformat(),
            "response_date": (datetime.now(UTC).date() + timedelta(days=30 - idx)).isoformat(),
            "place_city": ProspectFactory.CITIES[idx % len(ProspectFactory.CITIES)],
            "place_state": ProspectFactory.STATES[idx % len(ProspectFactory.STATES)],
            "set_aside": ProspectFactory.SET_ASIDES[idx % len(ProspectFactory.SET_ASIDES)],
            "source_id": (idx % 3) + 1,  # Cycles through 1, 2, 3
            "loaded_at": datetime.now(UTC) - timedelta(hours=idx),
            "ollama_processed_at": datetime.now(UTC) if idx % 3 == 0 else None,
            "ollama_model_version": "test-model-v1" if idx % 3 == 0 else None,
            "enhancement_status": ["idle", "queued", "processing", "completed", "failed"][idx % 5],
            "title_enhanced": f"Enhanced Title {idx}" if idx % 3 == 0 else None,
            "naics_source": "original" if idx % 2 == 0 else "llm_inferred" if idx % 3 == 0 else None,
            "set_aside_standardized": ["SMALL_BUSINESS", "EIGHT_A", "WOSB", None][idx % 4],
        }
        
        # Apply any overrides
        defaults.update(kwargs)
        return defaults


class DataSourceFactory:
    """Factory for creating deterministic DataSource test data."""
    
    SOURCES = [
        ("Department of Defense", "https://dod.gov", "DOD"),
        ("Health and Human Services", "https://hhs.gov", "HHS"),
        ("Department of Commerce", "https://commerce.gov", "DOC"),
        ("Department of Treasury", "https://treasury.gov", "TREAS"),
        ("Department of Transportation", "https://dot.gov", "DOT"),
        ("Social Security Administration", "https://ssa.gov", "SSA"),
        ("Department of State", "https://state.gov", "DOS"),
        ("Department of Justice", "https://justice.gov", "DOJ"),
    ]
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a deterministic data source with optional overrides."""
        global _counters
        idx = _counters["data_source"]
        _counters["data_source"] += 1
        
        source_data = DataSourceFactory.SOURCES[idx % len(DataSourceFactory.SOURCES)]
        
        defaults = {
            "id": idx + 1,
            "name": source_data[0],
            "url": source_data[1],
            "scraper_class": f"{source_data[2]}Scraper",
            "active": idx % 4 != 0,  # 75% active
            "last_scraped": datetime.now(UTC) - timedelta(days=idx % 7),
            "created_at": datetime.now(UTC) - timedelta(days=30 + idx),
        }
        
        defaults.update(kwargs)
        return defaults


class UserFactory:
    """Factory for creating deterministic User test data."""
    
    FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    ROLES = ["user", "admin", "analyst", "super-admin"]
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a deterministic user with optional overrides."""
        global _counters
        idx = _counters["user"]
        _counters["user"] += 1
        
        first_name = UserFactory.FIRST_NAMES[idx % len(UserFactory.FIRST_NAMES)]
        last_name = UserFactory.LAST_NAMES[idx % len(UserFactory.LAST_NAMES)]
        
        defaults = {
            "id": idx + 1,
            "username": f"{first_name.lower()}{idx}",
            "email": f"{first_name.lower()}.{last_name.lower()}{idx}@example.com",
            "first_name": first_name,
            "last_name": last_name,
            "role": UserFactory.ROLES[idx % len(UserFactory.ROLES)],
            "is_active": idx % 10 != 0,  # 90% active
            "created_at": datetime.now(UTC) - timedelta(days=idx * 7),
        }
        
        defaults.update(kwargs)
        return defaults


class DecisionFactory:
    """Factory for creating deterministic GoNoGoDecision test data."""
    
    DECISIONS = ["go", "no-go"]
    REASONS = [
        "Good fit for our capabilities",
        "Not aligned with current strategy",
        "High competition expected",
        "Strategic opportunity",
        "Resource constraints",
        "Excellent profit margin potential",
        "Timeline conflicts with other projects",
        "Strong existing relationship with agency",
    ]
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a deterministic decision with optional overrides."""
        global _counters
        idx = _counters["decision"]
        _counters["decision"] += 1
        
        defaults = {
            "id": idx + 1,
            "prospect_id": f"PROSPECT-{idx % 10:04d}",  # Links to prospects
            "user_id": (idx % 5) + 1,  # Cycles through user IDs 1-5
            "decision": DecisionFactory.DECISIONS[idx % 2],
            "reason": DecisionFactory.REASONS[idx % len(DecisionFactory.REASONS)],
            "created_at": datetime.now(UTC) - timedelta(hours=idx * 2),
            "updated_at": datetime.now(UTC) - timedelta(hours=idx),
        }
        
        defaults.update(kwargs)
        return defaults


class EnhancementQueueFactory:
    """Factory for creating deterministic enhancement queue items."""
    
    ENHANCEMENT_TYPES = ["values", "titles", "naics", "set_asides", "all"]
    STATUSES = ["pending", "processing", "completed", "failed", "cancelled"]
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a deterministic enhancement queue item."""
        global _counters
        idx = _counters.get("enhancement_queue", 0)
        _counters["enhancement_queue"] = idx + 1
        
        defaults = {
            "id": f"queue-{idx:04d}",
            "prospect_id": f"PROSPECT-{idx % 20:04d}",
            "user_id": (idx % 3) + 1,
            "enhancement_type": EnhancementQueueFactory.ENHANCEMENT_TYPES[idx % len(EnhancementQueueFactory.ENHANCEMENT_TYPES)],
            "status": EnhancementQueueFactory.STATUSES[idx % len(EnhancementQueueFactory.STATUSES)],
            "priority": idx % 3,  # 0=low, 1=medium, 2=high
            "created_at": datetime.now(UTC) - timedelta(minutes=idx * 10),
            "started_at": datetime.now(UTC) - timedelta(minutes=idx * 5) if idx % 3 == 0 else None,
            "completed_at": datetime.now(UTC) if idx % 4 == 0 else None,
            "error_message": "Test error" if idx % 5 == 3 else None,
        }
        
        defaults.update(kwargs)
        return defaults


class ScraperDataFactory:
    """Factory for creating deterministic scraper test data."""
    
    @staticmethod
    def create_csv_data(num_rows: int = 5) -> str:
        """Create deterministic CSV data for scraper tests."""
        lines = ["Title,Agency,NAICS,Value,Posted Date,Response Date"]
        
        for i in range(num_rows):
            title = ProspectFactory.TITLES[i % len(ProspectFactory.TITLES)]
            agency = ProspectFactory.AGENCIES[i % len(ProspectFactory.AGENCIES)]
            naics = ProspectFactory.NAICS_CODES[i % len(ProspectFactory.NAICS_CODES)]
            value = f"${(i + 1) * 25000:,}"
            posted = (datetime.now(UTC).date() - timedelta(days=i * 2)).isoformat()
            response = (datetime.now(UTC).date() + timedelta(days=20 - i)).isoformat()
            
            lines.append(f'"{title}","{agency}",{naics},{value},{posted},{response}')
        
        return "\n".join(lines)
    
    @staticmethod
    def create_opportunity_dict(idx: int = 0) -> Dict[str, Any]:
        """Create a deterministic opportunity dictionary for scrapers."""
        return {
            "title": ProspectFactory.TITLES[idx % len(ProspectFactory.TITLES)],
            "agency": ProspectFactory.AGENCIES[idx % len(ProspectFactory.AGENCIES)],
            "description": f"Opportunity description {idx} with requirements",
            "naics": ProspectFactory.NAICS_CODES[idx % len(ProspectFactory.NAICS_CODES)],
            "value": f"${(idx + 1) * 15000:,}",
            "posted_date": (datetime.now(UTC).date() - timedelta(days=idx)).isoformat(),
            "response_date": (datetime.now(UTC).date() + timedelta(days=15 - idx)).isoformat(),
            "place": f"{ProspectFactory.CITIES[idx % len(ProspectFactory.CITIES)]}, {ProspectFactory.STATES[idx % len(ProspectFactory.STATES)]}",
            "set_aside": ProspectFactory.SET_ASIDES[idx % len(ProspectFactory.SET_ASIDES)],
            "notice_id": f"NOTICE-{idx:04d}",
            "solicitation_number": f"SOL-{idx:04d}",
        }


# Convenience functions for batch creation
def create_prospects(count: int, **kwargs) -> list:
    """Create multiple prospects with optional overrides."""
    return [ProspectFactory.create(**kwargs) for _ in range(count)]


def create_data_sources(count: int, **kwargs) -> list:
    """Create multiple data sources with optional overrides."""
    return [DataSourceFactory.create(**kwargs) for _ in range(count)]


def create_users(count: int, **kwargs) -> list:
    """Create multiple users with optional overrides."""
    return [UserFactory.create(**kwargs) for _ in range(count)]


def create_decisions(count: int, **kwargs) -> list:
    """Create multiple decisions with optional overrides."""
    return [DecisionFactory.create(**kwargs) for _ in range(count)]