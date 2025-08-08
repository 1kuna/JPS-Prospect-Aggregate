# Product Backlog

This document tracks feature requests, bug reports, and questions that need to be addressed. Items are organized by category and priority.

**Last Updated**: 2025-08-08  
**Source**: Converted from docs/add later.txt

## Priority Legend
- 🔴 **High** - Critical bugs or blockers
- 🟡 **Medium** - Important features or fixes
- 🟢 **Low** - Nice-to-have improvements

---

## 🐛 Bug Fixes

### Time Display Issue on Data Sources Tab
**Priority**: 🔴 High  
**Status**: ⚠️ Needs Verification  
**Description**: Time displays 4 hours ahead on the Data Sources tab only. All other pages show correct time.  
**Suggested Fix**: Replace time logic with implementation from other pages that work correctly.  
**Note**: DataSources component may have been refactored - needs verification if issue persists.

### AI Enhancement Filter Not Working
**Priority**: 🔴 High  
**Status**: ✅ Likely Fixed  
**Description**: The AI enrichment filter on the dashboard page doesn't filter results - all results show regardless of selection.  
**Update**: Filter logic appears to be properly implemented in ProspectFilters.tsx and usePaginatedProspects.ts - needs user verification.

### Enhancement Activity Display
**Priority**: 🟡 Medium  
**Status**: ❌ Component Removed  
**Description**: Real enhancement runs don't appear in the "Recent Activity" section. Demo listings should be removed.  
**Update**: The "Recent Activity" component has been removed from the codebase. Enhancement status is now shown through other UI elements.

---

## ✨ Feature Requests

### LLM Enhancement Improvements
**Priority**: 🟡 Medium

**Current Issues**:
- Batch processing may reduce accuracy
- No visual indication of inferred vs original data
- No way to filter between original and enhanced data

**Proposed Changes**:
1. Process listings one-by-one for higher accuracy
2. Replace batch size selector with simple "Start/Stop" button
3. Mark all inferred data with blue text (like Tesla Autopilot blue)
4. Add filter to show original vs inferred data
5. Add LLM enrichment status and controls on Advanced page

### Go/No-Go Decision Tracking
**Priority**: 🟡 Medium  
**Status**: ✅ Implemented  
**Description**: Add ability to mark opportunities as go/no-go with:
- User attribution (who marked it)
- Timestamp (when marked)
- Queue for manual verification
- Reasoning field for decisions
**Update**: Fully implemented with Decision model, API endpoints, and UI components (GoNoGoDecision.tsx)

### Database Management Enhancements
**Priority**: 🟡 Medium  
**Description**: In the Database tab of Advanced page, add separate options to:
- Clear only AI-enhanced entries
- Clear only original entries  
- Clear all entries (current functionality)

### Filter Panel UX Improvement
**Priority**: 🟢 Low  
**Description**: The "Clear All" button should be disabled/greyed out when no filters are active.

---

## ❓ Technical Questions

### Data Refresh Safety
**Question**: When data sources are refreshed, is there a mechanism to prevent overwriting AI-enhanced data?

**Considerations**:
- Need to preserve AI enhancements if they're more accurate
- But also need to capture legitimate updates from sources
- Possible solution: Version tracking or merge strategy

### LLM Processing Strategy
**Question**: Should batch processing be replaced with iterative one-by-one processing?

**Trade-offs**:
- Batch: Faster but potentially less accurate
- Iterative: Slower but more accurate, better context per listing
- User preference seems to be accuracy over speed

---

## 🔧 Technical Improvements (Not User-Facing)

### Add to Tech Stack
**Priority**: 🟢 Low
- Celery/Redis for background tasks
- Pydantic for data validation
- React Router for proper navigation
- React Hook Form + Zod for form handling
- Docker for deployment
- Tailwind CSS (already implemented ✅)
- Loguru (already implemented ✅)

---

## 📝 Notes

- Dashboard toasts implementation is complete ✅
- NAICS inference should stay within 4-digit parent codes unless generic
- All items converted from informal notes in "add later.txt"
- Set-aside LLM processing is marked as critical issue in CODEBASE_IMPROVEMENTS.md
- Extensive test coverage (27k+ lines) has been added since initial backlog creation
- Go/No-Go decision tracking has been fully implemented with user attribution and reasoning