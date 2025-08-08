# Codebase Improvements

## Executive Summary

This document tracks ongoing improvements and technical debt items that still need attention. Items are organized by priority and effort required.

---

## 🔴 Critical Issues

### 1. Fix Set-Aside LLM Processing
**Priority**: 🔴 Critical | **Status**: ❌ Not Started  
**Effort**: 2-4 hours

**Current Issue**:
- Set-aside standardization is not being properly processed by the LLM
- The `standardize_set_aside_with_llm()` method exists but may not be integrated correctly
- Enhanced titles and values work, but set-asides are not being updated

**Root Cause Investigation Needed**:
- Verify LLM service integration for set-aside processing
- Check if `enhance_prospect_set_asides()` method is being called properly
- Ensure API endpoints are invoking set-aside enhancement
- Validate that set-aside results are being saved to the database

**Expected Fix**:
- Set-asides should be processed and standardized via LLM like other fields
- UI should show enhanced set-aside values with proper indicators
- Database should store standardized set-aside data

**Impact**: Critical functionality gap - set-aside processing is a core feature for federal contracting

---

## 🚀 Quick Wins (< 1 day each)

### 1. Remove Test Script Clutter
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 30 minutes

- Remove `/scripts/test_queue_manual.js` (17 console.log statements)
- Move to proper test framework or document as manual testing tool

**Impact**: Cleaner testing strategy, reduced repository clutter

### 2. Documentation Gaps
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1-2 hours

**Items**:
- [ ] Create API documentation with endpoint descriptions
- [ ] Add deployment guide for production setup
- [ ] Document the database model design rationale (why multiple value fields exist)

**Impact**: Reduced onboarding friction, preserved architectural knowledge

### 3. Frontend Performance Quick Wins
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 2-3 hours

Add React.memo to expensive components:
- `ProspectTable` (high re-render frequency)
- `ProspectFilters` (complex form state)
- `ProspectDetailsModal` (large data objects)

**Impact**: Immediate UI performance improvement, smoother user experience

---

## 🎯 Medium-Term Improvements (1-2 weeks total)

### 1. Database Model Optimization (Safe Changes Only)
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1-2 days

**Why Current Structure Exists** (Preserving Design Rationale):
The multiple value fields in the Prospect model serve specific purposes:
- `estimated_value`: Original scraped value
- `estimated_value_text`: Raw text for LLM parsing
- `estimated_value_min/max`: LLM-parsed ranges ("$100K - $500K")
- `estimated_value_single`: LLM-parsed single values ("$250,000")

**Safe Optimizations**:
1. **Add Database Views** for common queries without changing models
2. **Optimize Indexes** based on actual query patterns
3. **Add Computed Columns** for frequently calculated values
4. **Create Helper Methods** to reduce model complexity in views

**What NOT to Change**:
- The multi-field value structure (handles ranges vs single values correctly)
- The separation of original vs LLM-enhanced data
- The tracking of LLM processing metadata

**Impact**: Better query performance without architectural disruption

### 2. Scraper Framework Leverage
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 2-3 days

**Current Excellence**: The unified `ConsolidatedScraperBase` is well-designed
**Opportunity**: Some scrapers don't fully leverage the framework

**Improvements**:
1. **Standardize Configuration** usage across all scrapers
2. **Extract Common Transformations** into base class methods
3. **Unified Error Handling** patterns
4. **Consistent Retry Logic** implementations

**Impact**: More consistent scraper behavior, easier maintenance

---

## 🔍 Data Quality & Field Mapping Improvements

### 1. Implement Required Fields Validation
**Priority**: 🔴 High | **Status**: ❌ Not Started  
**Effort**: 4-6 hours

**Current Issue**:
- No validation that essential fields are present before database load
- Can result in low-quality records with missing critical data
- Inconsistent data quality across sources

**Implementation**:
- Add `required_fields_for_load` to each scraper config
- Drop rows missing essential fields early in pipeline
- Example: `["id", "title", "agency"]` as minimum for most sources

**Impact**: Ensures database contains only complete, usable records

### 2. Standardize Location Parsing
**Priority**: 🔴 High | **Status**: ❌ Not Started  
**Effort**: 1 day

**Current Issue**:
- Sources provide locations in various formats ("City, ST", separate fields, etc.)
- Inconsistent parsing leads to missing or malformed location data
- No default country handling

**Implementation**:
- Define `place_column_configs` in scraper configs
- Auto-split combined locations into city/state
- Default `place_country` to "USA" where appropriate
- Priority sources: DOT, DOJ, Treasury, SSA

**Impact**: Consistent location data across all sources for better search/filtering

### 3. Improve Contact Field Handling
**Priority**: 🔴 High | **Status**: ❌ Not Started  
**Effort**: 4-6 hours

**Current Issue**:
- Contact information in various formats (first/last separate, full name, org only)
- Missing contact data when it exists but in unexpected format
- No standardized concatenation logic

**Implementation**:
- Per-source transforms for contact name joining
- Fallback logic for org-level contacts
- Consistent `primary_contact_name` field population

**Impact**: Better contact data extraction for improved communication capabilities

### 4. Field Coverage Monitoring
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 2 hours

**Current Issue**:
- No visibility into field coverage/gaps across sources
- Header drift goes unnoticed until data issues appear
- Difficult to prioritize mapping improvements

**Implementation**:
- Regular use of existing CLI tool: `scripts/analyze_field_coverage.py`
- Monthly monitoring schedule after vendor UI changes
- Automated alerts for coverage drops

**Example Usage**:
```bash
python scripts/analyze_field_coverage.py --fixtures tests/fixtures/golden_files --min-threshold 0.8
```

**Impact**: Proactive detection of mapping issues before they affect production

### 5. Per-Source Fallback Normalization
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1-2 days

**Current Issue**:
- Header variations cause data loss when exact matches fail
- Global normalization can cause false positives
- No safety against overwriting good data

**Implementation**:
- Convert global normalization to per-source whitelists
- Fill-only-if-empty logic (never overwrite mapped values)
- Example: AG: `Body`→`description`, Treasury: `Place of Performance`→`place_raw`

**Impact**: Resilience to minor header changes without sacrificing accuracy

### 6. Date and Quarter Parsing Consistency
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1 day

**Current Issue**:
- Various date formats across sources ("FY25 Q2", "Q3 2024", direct dates)
- Inconsistent parsing leads to missing temporal data
- Complex fallback logic scattered across scrapers

**Implementation**:
- Verify each source's `date_column_configs` and `fiscal_year_configs`
- Standardize parsing for common patterns
- Single reliable parse path per variant

**Impact**: Consistent temporal data for better forecasting and filtering

**See `docs/DATA_MAPPING_GUIDE.md` for detailed technical specifications and examples.**

---

## 🏗️ Architecture Improvements (Ongoing)

### 1. Folder Structure Reorganization
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 4 hours

**Current Issues**:
- Scripts folder cluttered with different utility types
- No clear separation of concerns
- Documentation scattered

**Proposed Structure**:
```
docs/
├── architecture/      # System design docs
├── guides/           # Setup, deployment guides  
├── api/              # API documentation
└── archive/          # Historical docs

scripts/
├── setup/            # DB setup, initialization
├── maintenance/      # Data retention, validation
├── scrapers/         # Scraper runners
├── enrichment/       # LLM enhancement
└── archive/          # Completed migrations

tests/
├── unit/             # Unit tests (existing structure)
├── integration/      # Integration tests
├── fixtures/         # Test data
└── e2e/             # End-to-end tests
```

**Impact**: Clearer organization, easier navigation

### 2. Error Handling Standardization
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1-2 days

**Current Issues**:
- Mix of try/catch patterns
- Some services return None, others raise exceptions
- Frontend error handling varies by component

**Standardization Plan**:
1. **Unified Error Types** with specific error classes
2. **Consistent Response Format** across all services
3. **Centralized Error Logging** with structured data
4. **Frontend Error Boundaries** for graceful degradation

### 3. Configuration Validation System
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1 day

**Current Issues**:
- Environment variables scattered across files
- No validation for required configurations
- Some hardcoded values in scrapers

**Proposed Solution**:
1. **Central Configuration Class** with validation
2. **Environment Variable Documentation** with examples
3. **Startup Validation** to catch configuration issues early
4. **Configuration Testing** utilities

---

## 🧪 Testing & Quality Improvements

### 1. Code Quality Standards
**Priority**: 🟢 Low | **Status**: ❌ Not Started  
**Effort**: 1 day

**Setup**:
- Black formatter for Python code
- Prettier for frontend code (already configured)
- Husky for pre-commit hooks
- ESLint/Pylint rule standardization

**Impact**: Consistent code style, fewer review cycles

### 2. Add Missing Critical Tests
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 2-3 days

Despite extensive test coverage (27k+ lines), some critical paths need testing:
- Set-aside LLM processing workflow
- Error recovery in scrapers
- Frontend filter interactions
- Decision tracking workflows

**Impact**: Confidence in critical features, reduced regression risk

---

## 📊 Performance Optimizations

### 1. Frontend Performance
**Priority**: 🟡 Medium | **Status**: 🚧 Partially Implemented  
**Effort**: 1-2 days

**Current State**:
- ✅ Code splitting with React.lazy()
- ✅ React.memo used in 2 components
- ❌ Large bundle size (381KB)
- ❌ No virtual scrolling for large tables

**Optimization Plan**:
1. **Add React.memo** to expensive components (listed above)
2. **Implement Virtual Scrolling** for ProspectTable
3. **Add Performance Monitoring** (Web Vitals)
4. **Optimize Re-renders** with useMemo/useCallback

### 2. Backend Performance
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1-2 days

**Opportunities**:
1. **Database Query Optimization** (add missing indexes)
2. **LLM Response Caching** (avoid repeat calls)
3. **Bulk Operations** for large datasets
4. **Connection Pooling** optimization

---

## 📝 Notes

- Focus on critical issues first (set-aside processing)
- Many previously identified issues have been resolved
- Test coverage is extensive but some workflows need additional coverage
- Architecture is generally solid, improvements are incremental