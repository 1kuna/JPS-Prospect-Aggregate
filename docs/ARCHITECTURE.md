# JPS Prospect Aggregate - System Architecture

## Overview

The JPS Prospect Aggregate system is a comprehensive web scraping and data processing platform designed to collect, process, and manage federal government contracting opportunities from multiple agency sources. The system employs a unified scraper architecture with intelligent data processing and storage management.

## Core Architecture Components

### 1. Unified Scraper Framework

The entire scraping system is built on a consolidated architecture that eliminates code duplication and provides consistent behavior across all agency scrapers.

#### ConsolidatedScraperBase (`app/core/consolidated_scraper_base.py`)
- **Purpose**: Single base class containing all scraping functionality
- **Key Features**:
  - Browser automation with Playwright
  - Anti-bot detection avoidance with stealth mode
  - Automatic retry logic with exponential backoff
  - Error handling with screenshot/HTML capture
  - File download management
  - Data transformation pipeline
  - Database integration

#### ScraperConfig (`app/core/consolidated_scraper_base.py`)
- **Purpose**: Unified configuration dataclass for all scrapers
- **Key Configuration Areas**:
  - Browser settings (stealth mode, timeouts, special args)
  - Selectors for UI interaction
  - File reading strategies
  - Data transformation rules
  - Field mapping configurations

#### Config Converter (`app/core/config_converter.py`)
- **Purpose**: Creates agency-specific configurations
- **Pattern**: Each agency has a `create_[agency]_config()` function
- **Benefit**: Centralizes all configuration logic

### 2. Agency Scrapers

Each agency scraper inherits from `ConsolidatedScraperBase` and focuses only on agency-specific requirements:

```python
class AgencyScraper(ConsolidatedScraperBase):
    def __init__(self):
        config = create_agency_config()
        config.base_url = active_config.AGENCY_URL
        super().__init__(config)
    
    # Optional: Agency-specific transformations
    def custom_transform(self, df):
        return df
```

**Current Agency Scrapers**:
- Acquisition Gateway
- Department of Commerce (DOC)
- Department of Homeland Security (DHS)
- Department of Justice (DOJ)
- Department of State (DOS)
- Department of Transportation (DOT)
- Department of Treasury
- Health and Human Services (HHS)
- Social Security Administration (SSA)

### 3. Data Processing Pipeline

The system follows a structured data flow from raw scraping to database storage:

1. **Extraction Phase**:
   - Navigate to agency website
   - Interact with UI elements (clicks, waits)
   - Download files (CSV, Excel, HTML)

2. **Transformation Phase**:
   - Read files based on configured strategy
   - Apply column renaming maps
   - Parse dates and fiscal quarters
   - Extract and clean values
   - Apply custom transformations

3. **Loading Phase**:
   - Generate unique IDs based on field combinations
   - Detect duplicates using fuzzy matching
   - Bulk upsert to database
   - Track file processing status

### 4. Database Architecture

#### Dual Database Design
- **Business Database** (`jps_aggregate.db`): Contains prospects and scraping data
- **User Database** (`jps_users.db`): Isolated authentication and user data

#### Key Models
- **Prospect**: Core business entity with all contract opportunity data
- **DataSource**: Configuration for each agency data source
- **ScraperStatus**: Real-time status tracking for scraper runs
- **FileProcessingLog**: Tracks which files have been successfully processed
- **User/Decision**: User authentication and go/no-go decision tracking

### 5. API Layer

Flask application with modular blueprint architecture:

- **Main API** (`/api/`): Core CRUD operations
- **Prospects API** (`/api/prospects/`): Search, filter, pagination
- **Decisions API** (`/api/decisions/`): User decision management
- **Data Sources API** (`/api/data_sources/`): Source configuration
- **Scrapers API** (`/api/scrapers/`): Trigger and monitor scraping

### 6. Frontend Architecture

React TypeScript SPA with modern tooling:

- **State Management**: TanStack Query for server state
- **UI Components**: Tailwind CSS + Radix UI
- **Table Virtualization**: TanStack Table for performance
- **Type Safety**: Full TypeScript coverage

### 7. Supporting Services

#### File Validation Service
- Tracks successfully processed files
- Prevents reprocessing of duplicate data
- Supports intelligent retention policies

#### LLM Enhancement Service
- Uses Ollama with qwen3 model
- Enhances data quality:
  - Value extraction from text
  - Contact information parsing
  - Title improvement
  - NAICS code classification

#### Duplicate Detection Service
- Fuzzy matching algorithms
- Confidence scoring
- Bulk duplicate checking

#### Data Retention Service
- Intelligent file cleanup
- Preserves recent + successful files
- Configurable retention policies

## Design Patterns and Principles

### 1. Configuration-Driven Development
All scraper behavior is controlled through configuration objects, making it easy to add new sources or modify existing ones without changing core logic.

### 2. Separation of Concerns
- Scrapers handle only web interaction
- Data processing is separate from scraping
- Database operations are isolated in CRUD modules
- Frontend and backend are completely decoupled

### 3. Error Resilience
- Automatic retries with backoff
- Screenshot capture on failures
- Graceful degradation
- Comprehensive logging

### 4. Performance Optimization
- Bulk database operations
- Table virtualization in frontend
- Efficient pagination
- Query optimization with indexes

### 5. Security
- Separate user database
- Session-based authentication
- Input validation
- SQL injection prevention

## System Flow

1. **Scraper Execution**:
   ```
   Trigger → Setup Browser → Navigate → Extract Data → Transform → Load to DB
   ```

2. **User Interaction**:
   ```
   Frontend → API Request → Database Query → Response → UI Update
   ```

3. **Data Enhancement**:
   ```
   New Prospect → Queue for Enhancement → LLM Processing → Update Record
   ```

## Deployment Considerations

- **Environment Variables**: All sensitive configuration in `.env`
- **Database Migrations**: Alembic for schema management
- **Error Monitoring**: Structured logging with Loguru
- **Performance**: Waitress WSGI server for production

## Future Architecture Considerations

1. **Horizontal Scaling**: Queue-based scraping with workers
2. **Caching Layer**: Redis for frequently accessed data
3. **Real-time Updates**: WebSocket support for live status
4. **Microservices**: Separate scraping from main application
5. **Container Orchestration**: Kubernetes for scaling