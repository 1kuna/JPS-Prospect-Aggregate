## Codebase Improvements (Proposed)

### Goals
- Ensure accurate, deterministic field mapping per source (no "garbage in, garbage out").
- Keep the model lean with first-class columns only for fields present or inferable in ≥80% of sources.
- Improve resilience to minor upstream header drift without sacrificing correctness.
- Provide visibility and validation tooling for ongoing quality.

### Current State (summary)
- Per-source hard-coded mappings in `app/core/scraper_configs.py` are the ground truth and have been audited/updated for known variants in the fixtures.
- Per-source custom transforms (in `app/core/scrapers/*_scraper.py`) handle contact name joins, location parsing, date/quarter logic, and extras collection.
- A lightweight normalization step in the scraper base safely fills only missing targets from vetted header candidates. It does not overwrite non-empty values.
- A standalone CLI (`scripts/analyze_field_coverage.py`) reports coverage/gaps per field across sample files to guide future mapping tweaks.

### Recommendations

#### 1) Keep hard-coded mappings as the primary mechanism (per-source)
- Treat `raw_column_rename_map` as the authoritative mapping for each source.
- Avoid global magic; make any fallback behavior opt-in per source.
- Action:
  - Continue to add missing explicit header mappings per source as sources evolve.

#### 2) Opt-in fallback normalization (source-scoped)
- Use a conservative fallback layer only for each source’s known header variants, running after the explicit renames.
- Fill-only-if-empty; never overwrite mapped values.
- Action:
  - Define a small, per-source whitelist of fallback candidates (e.g., AG: `Body`→`description`; Treasury: `Place of Performance`→`place_raw`).

#### 3) Enforce minimal load fields per source
- Drop rows early if missing essentials to ensure DB cleanliness.
- Example: `required_fields_for_load = ["id", "title", "agency"]`.
- Action:
  - Add `required_fields_for_load` in each scraper config based on the source’s data quality.

#### 4) Normalize locations via config
- For sources with combined location strings (e.g., "City, ST"), define `place_column_configs` in the config and let the base split into `place_city`/`place_state`.
- Default `place_country` to `USA` where appropriate.
- Action:
  - Add or expand `place_column_configs` for DOT, DOJ, Treasury, SSA where combined locations are common.

#### 5) Tighten date/quarter parsing consistently
- Ensure variants like "FY25 Q2", "Target Solicitation Month/Year", and direct dates are consistently parsed to `release_date`, `award_date`, and `award_fiscal_year` via config (`date_column_configs` and `fiscal_year_configs`).
- Action:
  - Verify each source’s config for quarter/date coverage and align on a single, reliable parse path per variant.

#### 6) Contacts: reliable fallbacks
- Where sources provide separate first/last name fields, concatenate to `primary_contact_name` (per-source transform).
- If only org-level contact lines exist (e.g., Treasury), promote to `primary_contact_name` when it’s clearly the correct semantic field.
- Action:
  - Keep this logic in each scraper’s custom transform to avoid global false positives.

#### 7) Keep first-class columns minimal
- Based on current coverage, do not promote new columns now (contract vehicle, incumbent, PSC remain in `extra`).
- Re-evaluate if/when coverage reaches ≥80% across sources or values become reliably inferable.

#### 8) Validation & visibility
- Use the CLI to measure field coverage/gaps on sample or real files regularly:
  - `python scripts/analyze_field_coverage.py --fixtures tests/fixtures/golden_files --min-threshold 0.8`
- Log a short per-run mapping summary: number of normalized fields, examples of collected `extra` keys.
- Action:
  - Add a simple log summary in the scraping pipeline (counts + a few example keys) for quick QA.

#### 9) Database strategy (SQLite now, Postgres later)
- SQLite: current schema is fine; no change required today.
- Postgres (later): use NUMERIC(15,2) for values and JSONB+GIN index for `extra` if querying by keys becomes common.
- A migration that aligns types exists (no-op on SQLite; aligns types when Postgres is used again).

#### 10) Testing & safety nets
- Add unit tests for each source’s header mapping (fixture → mapped DataFrame) so drift is caught early.
- Add regression tests around tricky transforms (e.g., quarter parsing, place parsing, contact joins).

### Actionable Plan (incremental)
1) Make fallback normalization opt-in per source (small refactor):
   - Keep today’s mappings, convert any global candidates to per-source whitelists.
2) Add `required_fields_for_load` for each source.
3) Expand `place_column_configs` where combined locations are prevalent.
4) Use the CLI monthly (or after vendor site UI changes) to spot header drift and update explicit maps.
5) When switching back to Postgres:
   - Run `alembic upgrade head` to apply NUMERIC/JSONB alignment.
   - Add GIN index on `extra` if needed for key-based filtering.

### Acceptance Criteria
- All sources load with consistently populated core fields (title, agency, id, NAICS when present, value text, location, set-aside).
- No unexpected overwrites by fallback logic (explicit maps win; fallbacks fill only when empty).
- CLI shows ≥ current coverage and highlights real drift, not mapping bugs.
- No DB changes required while on SQLite; future Postgres migration is straightforward.


