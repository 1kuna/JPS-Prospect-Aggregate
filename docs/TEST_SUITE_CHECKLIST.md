### Test Suite Modernization Checklist

Use this interactive checklist to track fixes and improvements to the test suite. Check items as you complete them; add new ones as issues are discovered.

#### Legend
- [ ] = not started
- [~] = in progress (replace with [ ] or [x] when done)
- [x] = done

---

### Immediate unbreakers (outdated endpoints, removed features)
- [x] Update Decisions API tests to match current endpoints
  - [x] Replace `GET /api/decisions/my` with `GET /api/decisions/user`
  - [x] Replace `GET /api/decisions/{prospect_id}` with `GET /api/decisions/prospect/{prospect_id}`
  - [x] Ensure `DELETE /api/decisions/{decision_id}` path uses integer ID and checks ownership
- [x] Update LLM API integration tests
  - [x] Remove SSE progress test against `/api/llm/stream/progress` (SSE removed)
  - [x] Use `/api/llm/queue/start-worker` and `/api/llm/queue/stop-worker` instead of older start/stop routes
  - [x] For `/api/llm/enhance-single`, validate both `enhancement_type` and `enhancement_types` array forms; assert response fields (`planned_steps`, `queue_item_id`, etc.)
  - [x] Ensure all responses are asserted using the standardized `{ status, data }` envelope
- [x] Remove/replace performance tests referencing non-existent helpers/modules
  - [x] Remove `add_prospect(...)` references
  - [x] Remove `from app.services.duplicate_detection import find_duplicates`
  - [x] Remove `Decision` model references (use `GoNoGoDecision` or API calls)

### Determinism and stability
- [x] Eliminate unseeded randomness across tests (backend and frontend)
  - [x] Introduce a global pytest fixture to seed `random` (and `numpy` if used)
  - [x] Replace random-driven data with deterministic factories where possible
- [x] Replace `time.sleep(...)` with deterministic synchronization
  - [x] LLM service thread tests: stop and join worker, or use events/flags
  - [x] Enhancement queue tests: loop with explicit iteration bounds or event hooks
- [x] Tighten broad assertions that mask regressions
  - [x] Replace `assert status_code in [200, 400, 404]` with exact expected codes
  - [x] Replace loose content checks with specific field/value relations

### API coverage gaps (add/update tests)
- [x] LLM API new endpoints
  - [x] `POST /api/llm/iterative/start` happy-path and validation errors
  - [x] `POST /api/llm/iterative/stop` idempotency
  - [x] `GET /api/llm/iterative/progress` percentage and totals
  - [x] `GET /api/llm/logs` structure and ordering
  - [x] `GET /api/llm/outputs` filtering by `enhancement_type`
  - [x] `POST /api/llm/cleanup-stale-locks` effects and count
- [x] Prospects API
  - [x] Invalid `source_ids` handling (non-integers should log warning and be ignored)
  - [x] `sort_by` fallback to `id` on invalid field
  - [x] Define and test max `limit` policy (error vs. clamp) and document expectation
  - [x] Combined filter interactions (`search`, `keywords`, `naics`, `ai_enrichment`, `source_ids`)
- [x] Decisions API
  - [x] Authorization/ownership checks on delete
  - [x] Pagination and filtering on `GET /api/decisions/user` (decision type)

### Unit test gaps (domain logic)
- [x] Set-aside standardization (`app/services/set_aside_standardization.py`)
  - [x] Map canonical forms to `StandardSetAside` values and labels
  - [x] Edge cases (empty, unknown, mixed-case, punctuation)
- [x] Value and date parsing: extend property-based or deterministic edge cases where helpful
- [x] NAICS lookup/validation: verify backfill behaviors when descriptions are missing

### Scraper tests
- [x] Ensure scraper tests verify field mappings semantically (not just counts)
- [x] Reduce random input; use deterministic CSV/XLSX/HTML fixtures per source
- [x] Add cross-source assertions for normalized fields (city/state/place parsing, value ranges, NAICS extraction)
- [x] Ensure no real network activity; all browser/file operations mocked

### Frontend tests
- [x] Replace random test data with deterministic factories/mocks
- [x] Remove mixed usage of random data with static UI assertions (e.g., expecting "Software Development Services")
- [x] Ensure fetch mocks align with backend schema (field names and shapes)
- [x] Verify decision workflow and enhancement flows against updated API responses

### Coverage and CI
- [x] Re-enable coverage in `pytest.ini`
  - [x] `--cov=app`, `--cov-report=term-missing`, `--cov-fail-under=80` (raise later)
- [x] Ensure coverage omits are minimal and intentional
- [x] Apply markers consistently (`unit`, `integration`, `slow`, `scraper`, `asyncio`)
- [x] Split CI jobs by markers (fast unit vs. integration/scraper)

### Test architecture & fixtures
- [x] Centralize deterministic factories in `tests/factories.py` (Prospect, DataSource, User, Decisions, etc.)
- [x] Consolidate/standardize DB setup/teardown in `tests/conftest.py`
- [x] Create reusable JSON/CSV/XLSX fixtures under `tests/fixtures/` for parsers and scrapers
- [x] Add a helper for authenticated test client sessions (role-aware)

### Performance tests (rewrite sanely)
- [x] Replace broken performance tests with API-level smoke benchmarks
  - [x] Basic response time checks (under deterministic in-memory DB)
  - [x] Pagination traversal sanity (no full data loads)
  - [x] Search and combined filters return promptly
  - [x] Avoid internal helpers or non-existent modules

### Security tests
- [x] Tighten placeholder assertions
  - [x] Replace `assert len(present_headers) >= 0` with specific headers we set
- [x] Ensure field names match models (`source_id` not `source_data_id`)
- [x] Verify SQLi/XSS handling aligns with current sanitization strategy (at render vs. API layer)

### TDD alignment (process improvements)
- [x] Test public interfaces (endpoints/services), not private methods (no leading `_` targets)
- [x] Mock only true externals (LLM API, browser); prefer real DB for app logic
- [x] Write strict, behavior-focused assertions (inputs → outputs/contracts)

### Migration & schema validation
- [x] Add migration tests to ensure Alembic heads match models
- [x] Validate indexes/constraints used by queries (e.g., prospects search/sort fields)

### Data mapping rule enforcement
- [x] Add cross-scraper test enforcing new first-class DB columns present in ≥80% of sources or inferable
  - [x] Load one small deterministic sample per source
  - [x] Run transforms
  - [x] Assert coverage threshold and produce actionable diff on failure

### Housekeeping
- [x] Remove or align `tests/scrapers/run_scraper_tests.py` with standard pytest usage
- [x] Ensure test suite does not rely on undeclared environment variables
- [x] Document test running instructions and marker usage in `docs/`

---

### Notes / Decisions to make
- [ ] Decide on max page size policy for `/api/prospects` and document (error vs. clamp)
- [ ] Confirm canonical set of security headers we aim to include and test for them
- [ ] Confirm which LLM endpoints are considered public vs. admin-only and reflect in tests


### Appendix: Implementation details and file targets

- Decisions API updates
  - Files:
    - `tests/api/test_decisions_api.py`
    - `tests/integration/test_api_workflows.py`
  - Replacements:
    - `/api/decisions/my` → `/api/decisions/user`
    - `GET /api/decisions/{prospect_id}` → `GET /api/decisions/prospect/{prospect_id}`
  - Acceptance:
    - 404/302 due to path mismatch eliminated; delete checks assert 403 (non-owner) and 404 (missing)

- LLM API integration alignment
  - Files:
    - `tests/integration/test_llm_api_integration.py`
    - `tests/api/test_llm_processing.py`
  - Changes:
    - Remove SSE: delete `GET /api/llm/stream/progress` test block
    - Start/Stop worker routes: `/api/llm/queue/start` → `/api/llm/queue/start-worker`, `/api/llm/queue/stop` → `/api/llm/queue/stop-worker`
    - `/api/llm/enhance` body should send `{"enhancement_type": "values|titles|naics|set_asides|all"}` (not arrays)
  - Acceptance:
    - Tests assert real response fields (e.g., `queue_item_id`, `planned_steps`) returned by current endpoints

- Performance tests replacement
  - File:
    - `tests/performance/test_performance.py`
  - Remove imports/calls:
    - `add_prospect(...)`, `from app.services.duplicate_detection import find_duplicates`, `Decision(...)`
  - Replace with API-level calls via Flask test client and realistic timing assertions using `time.perf_counter()`

- Seeding randomness for determinism
  - File:
    - `tests/conftest.py`
  - Add fixture:
    ```python
    @pytest.fixture(scope="session", autouse=True)
    def seed_random():
        import random
        random.seed(12345)
        try:
            import numpy as np
            np.random.seed(12345)
        except Exception:
            pass
    ```

- Replace sleeps with sync
  - Files:
    - `tests/services/test_llm_service.py`
    - `tests/services/test_enhancement_queue.py`
  - Actions:
    - Use thread `join(timeout=...)` and/or bounded polling on queue state/flags instead of `time.sleep(...)`

- Tighten assertions examples
  - Files:
    - `tests/api/test_prospects_api.py`, `tests/security/test_security.py`
  - Example changes:
    - For invalid `page=0`: expect `400` and an error JSON, not `status_code in [200, 400]`

- New LLM endpoints coverage
  - New file:
    - `tests/api/test_llm_iterative_and_logs.py`
  - Cases:
    - `POST /api/llm/iterative/start` with body `{ "enhancement_type": "values|titles|naics|set_asides|all", "skip_existing": true }`
    - `POST /api/llm/iterative/stop` idempotency
    - `GET /api/llm/iterative/progress` contains `processed`, `total`, `percentage`
    - `GET /api/llm/logs` returns list with `timestamp`, `enhancement_type`, `status`
    - `POST /api/llm/cleanup-stale-locks` returns `cleanup_count`

- Prospects API specifics
  - File:
    - `tests/api/test_prospects_api.py`
  - Add tests for:
    - `source_ids=a,b` → warning logged, no 500; filter ignored
    - `sort_by=unknown` → defaults to `id`
    - Max `limit` policy once decided (see Notes)

- Set-aside standardization unit tests
  - File:
    - `tests/services/test_set_aside_standardization.py`
  - Inputs:
    - "Small Business Set-Aside", "8(a)", "WOSB", "HUBZone", "Service-Disabled Veteran-Owned", "Unknown ABC", "  HUBZone  "
  - Assertions:
    - Enum value and human-friendly label where applicable

- Scraper fixtures and mappings
  - Files:
    - `tests/core/test_scraper_base.py`
    - `tests/core/scrapers/test_scrapers.py`
  - Actions:
    - Move dynamic DataFrame generation to static fixtures under `tests/fixtures/`
    - Validate transformed columns include: `title`, `agency`, `naics`, `estimated_value_text`, `place_city`, `place_state`

- Frontend integration stability
  - File:
    - `frontend-react/tests/integration/ProspectWorkflow.test.tsx`
  - Actions:
    - Replace randomized generator with deterministic fixtures
    - Align field names with backend (`source_id`, `naics`, `ollama_processed_at`)

- Coverage and CI
  - File:
    - `pytest.ini`
  - Actions:
    - Uncomment coverage options and set `--cov-fail-under=80`
    - Split CI runs by markers (`unit` vs `integration`/`scraper`) for faster feedback

- Auth test helpers
  - File:
    - `tests/conftest.py`
  - Add:
    - `auth_client(app, client, role="user|admin")` helper to pre-set session or mock auth for role-based tests

- Security tests specifics
  - File:
    - `tests/security/test_security.py`
  - Actions:
    - Replace placeholder header assertion with explicit headers if configured: `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`
    - Use `source_id` (not `source_data_id`) in model creations

- Migration verification
  - New file:
    - `tests/database/test_migrations.py`
  - Actions:
    - Compare Alembic head with models metadata using `alembic` APIs; ensure no pending diffs

- Cross-source 80% rule test
  - New file:
    - `tests/core/test_cross_source_coverage.py`
  - Columns to verify presence/inference:
    - `title`, `agency`, `naics`, `estimated_value_text` (or parsed numeric), `place_city`, `place_state`, `loaded_at`
  - Acceptance:
    - ≥80% of sources produce required fields post-transform; failure prints per-source missing-field report

- Docs/housekeeping
  - Files:
    - `docs/` (add Test Guide)
    - Remove or align `tests/scrapers/run_scraper_tests.py` with standard pytest
  - Actions:
    - Document marker usage: `pytest -m "unit"`, `pytest -m "integration"`

