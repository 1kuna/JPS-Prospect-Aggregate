# Technical Debt Tracker

## Overview
This document tracks technical debt and improvement opportunities across the JPS Prospect Aggregate codebase. Items are organized by priority and impact.

**Last Updated**: 2025-01-03  
**Next Review**: 2025-01-10

## Priority Legend
- 🔴 **Critical** - Blocking issues or security concerns
- 🟠 **High** - Significant impact on maintainability or performance  
- 🟡 **Medium** - Quality of life improvements
- 🟢 **Low** - Nice-to-have enhancements

## Status Legend
- ❌ Not Started
- 🚧 In Progress
- ✅ Completed
- ⏸️ On Hold
- 🗑️ Deprecated/Won't Fix

---

## 🔥 Quick Wins (< 1 hour each)

### Logging Standardization
**Priority**: 🟠 High | **Status**: ✅ Completed  
**Effort**: ~2 hours total

Replace print() statements with proper logger calls across Python scripts:
- ✅ `/app/utils/data_retention.py` - Lines 317-323
- ✅ `/scripts/validate_file_naming.py` - Multiple print statements  
- ✅ `/scripts/migrate_data_directories.py` - Multiple print statements
- ✅ `/app/api/scrapers.py` - Contains print statements
- ✅ `/scripts/run_scraper_tests.py` - Contains print statements
- ✅ `/scripts/test_scraper_individual.py` - Contains print statements  
- ✅ `/scripts/init_user_database.py` - Contains print statements
- ✅ `/scripts/export_decisions_for_llm.py` - Contains print statements
- ✅ Archive scripts - Updated completed migration scripts

**Impact**: Consistent logging, better debugging in production

### Directory Cleanup
**Priority**: 🟡 Medium | **Status**: ✅ Completed  
**Effort**: 15 minutes

- ✅ Remove empty `/temp/` directory
- ✅ Clean up old error screenshots in `/logs/error_screenshots/` (11 files from June 2025)
- ⏸️ Review and clean `/logs/error_html/` directory (keeping for debugging)

**Impact**: Cleaner repository, reduced clutter

### Test Script Cleanup  
**Priority**: 🟡 Medium | **Status**: ❌ Not Started
**Effort**: 30 minutes

- Remove or refactor `/scripts/test_queue_manual.js` (17 console.log statements)
- Move to proper test framework or document as manual testing tool

**Impact**: Clearer testing strategy

---

## 🚨 Active Technical Debt

### 1. Documentation Maintenance
**Priority**: 🟠 High | **Status**: 🚧 Partially Complete  
**Effort**: 1-2 hours remaining

**Completed**:
- ✅ README.md updated with correct setup commands
- ✅ Deleted outdated scraper_architecture.md
- ✅ Converted add later.txt to BACKLOG.md

**Remaining Issues**:
- [ ] Missing API documentation
- [ ] No deployment guide

**Action Items**:
- [ ] Create API documentation with endpoint descriptions
- [ ] Add deployment guide for production setup

**Impact**: Reduced onboarding friction, accurate documentation

### 2. Performance Optimizations
**Priority**: 🟡 Medium | **Status**: 🚧 Partially Implemented  
**Effort**: 1-2 days

**Completed**:
- ✅ Code splitting with React.lazy() for all routes
- ✅ Suspense boundaries with loading fallbacks  
- ✅ React.memo used in Dashboard.tsx and ConfirmationDialog.tsx

**Remaining Issues**:
- [ ] Large bundle size (381KB main bundle)
- [ ] No bundle analysis tools
- [ ] Limited React.memo usage (only 2 components)
- [ ] No performance monitoring

**Action Items**:
- [ ] Add React.memo to expensive components (ProspectTable, ProspectFilters)
- [ ] Implement virtual scrolling for large tables
- [ ] Add performance monitoring (Web Vitals)
- [ ] Optimize re-renders with useMemo/useCallback

**Impact**: Faster load times, smoother user experience

### 3. Code Duplication & Architecture
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 1 week

**Backend Consolidation Opportunities**:
- Merge `contract_llm_service.py` and `iterative_llm_service_v2.py` (significant overlap)
- Consolidate duplicate validation logic across services
- Unify error handling patterns in scrapers
- Standardize retry logic implementations

**Frontend Consolidation**:
- Extract common form patterns into reusable hooks
- Create shared validation utilities
- Standardize modal/dialog patterns
- Consolidate API error handling

**Impact**: 30-40% code reduction, improved maintainability

### 4. Testing Infrastructure Gaps
**Priority**: 🟡 Medium | **Status**: 🚧 Basic Setup Complete  
**Effort**: 2-3 days

**Current State**:
- ✅ pytest and Vitest configured
- ✅ Basic test structure in place
- ❌ Minimal test coverage
- ❌ No integration tests
- ❌ No E2E tests

**Action Items**:
- [ ] Add unit tests for critical services (LLM service, scrapers)
- [ ] Create integration tests for API endpoints
- [ ] Add component tests for complex UI components
- [ ] Set up E2E tests for critical user flows
- [ ] Add pre-commit hooks for test running

**Impact**: Increased reliability, confidence in changes

### 5. Developer Experience
**Priority**: 🟢 Low | **Status**: ❌ Not Started  
**Effort**: 1 day

**Issues**:
- No code formatting standards (Prettier/Black)
- No pre-commit hooks
- Inconsistent naming conventions
- Missing JSDoc/docstrings in many files

**Action Items**:
- [ ] Set up Prettier for frontend
- [ ] Set up Black for Python code
- [ ] Add Husky for pre-commit checks
- [ ] Document coding standards
- [ ] Add JSDoc to public APIs

**Impact**: Consistent code style, fewer review cycles

---

## 🎯 Large Improvement Opportunities

### 1. Folder Structure Reorganization
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 4 hours

**Current Issues**:
- Scripts folder is cluttered with different types of utilities
- Documentation is scattered
- Test files mixed with fixtures
- No clear separation of concerns

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
├── unit/             # Unit tests
├── integration/      # Integration tests
├── fixtures/         # Test data
└── e2e/             # End-to-end tests
```

**Impact**: Clearer organization, easier navigation

### 2. LLM Service Architecture Refactor
**Priority**: 🟡 Medium | **Status**: ❌ Not Started  
**Effort**: 3-4 days

**Current Issues**:
- Two separate LLM services with overlapping functionality
- Hardcoded prompts scattered in code
- No abstraction for different LLM providers
- Limited error recovery

**Proposed Changes**:
- Unified LLM service interface
- Provider abstraction (Ollama, OpenAI, etc.)
- Centralized prompt management
- Retry strategies with fallbacks
- Better queue management

**Impact**: 40% code reduction, easier to add new LLM providers

### 3. Monitoring & Observability
**Priority**: 🟢 Low | **Status**: ❌ Not Started  
**Effort**: 1 week

**Missing Capabilities**:
- No APM (Application Performance Monitoring)
- Limited error tracking
- No user analytics
- No scraper success metrics dashboard

**Proposed Implementation**:
- Add OpenTelemetry instrumentation
- Implement Sentry for error tracking
- Create metrics dashboard
- Add scraper health monitoring

**Impact**: Better visibility into system health

---

## 📋 Won't Fix / Deprioritized

### CI/CD Pipeline
**Status**: 🗑️ Won't Fix  
**Reason**: Overkill for internal tool with small team

- Manual deployment is sufficient
- Automated testing provides minimal value
- Complexity outweighs benefits

### Bundle Size Optimization  
**Status**: 🗑️ Won't Fix  
**Reason**: Poor ROI for internal tool

- Current 381KB loads in ~0.5s on corporate network
- Cached after first load
- 8-12 hours of work for ~0.3s improvement

---

## 🏆 Completed Achievements Archive

### 2025-01-07 - Logging Standardization & Directory Cleanup
- ✅ **Logging Standardization**: Complete replacement of 142+ print() statements with loguru logger
- ✅ **Consistent logging**: All scripts now use centralized logger with proper log levels
- ✅ **Directory cleanup**: Removed empty /temp/ directory and 11 old error screenshots
- ✅ **Archive migration scripts**: Updated completed migrations with proper logging
- ✅ **Better debugging**: Structured logging with rotation and retention policies

### 2025-01-03 - Component Architecture Refactoring & Documentation
- ✅ **Dashboard.tsx**: 1,398 → 183 lines (87% reduction)
- ✅ **Advanced.tsx**: 429 → 107 lines (75% reduction)  
- ✅ Extracted 11 custom hooks
- ✅ Created 12 reusable components
- ✅ Type consolidation across files
- ✅ **Documentation Updates**:
  - Updated README.md with correct setup instructions
  - Deleted outdated scraper_architecture.md 
  - Created BACKLOG.md from informal TODO notes
  - Added clarifying comments to 4 key implementation files

### 2025-01-02 - TypeScript & Error Handling
- ✅ **100% TypeScript error elimination** (34 → 0 errors)
- ✅ Complete error handling infrastructure
- ✅ All 24 alert()/confirm() replaced with modern toasts
- ✅ Toast notification system with Radix UI
- ✅ Centralized error service

### 2025-01-02 - Code Quality
- ✅ All console.log statements removed (12 total)
- ✅ Mock/placeholder code cleanup (~70 lines removed)
- ✅ HTTP client standardization with retry logic
- ✅ Enhancement hooks consolidation

### Historical Achievements
- ✅ Testing infrastructure setup (pytest + Vitest)
- ✅ Environment configuration (.env files)
- ✅ Code splitting implementation
- ✅ React.memo optimization started

---

## 📊 Metrics & Progress

**Total Issues**: 23  
**Completed**: 20 (87%)  
**In Progress**: 0 (0%)  
**Not Started**: 3 (13%)

**Code Reduction Achieved**: ~2,000 lines (84% in major components)  
**Type Safety**: 100% (0 TypeScript errors)  
**Test Coverage**: ~20% (needs improvement)

---

## 🗓️ Upcoming Priorities

### This Sprint (by 2025-01-10)
1. ✅ ~~Replace all print() statements with logger~~ - Complete
2. ✅ ~~Update documentation (README, architecture)~~ - Complete
3. ✅ ~~Clean up directories and old files~~ - Complete
4. Complete remaining documentation (API docs, deployment guide)

### Next Sprint  
1. Performance optimizations (React.memo, virtualization)
2. Testing infrastructure expansion
3. Code duplication reduction

### Future Quarters
1. LLM service architecture refactor
2. Monitoring and observability
3. Folder structure reorganization