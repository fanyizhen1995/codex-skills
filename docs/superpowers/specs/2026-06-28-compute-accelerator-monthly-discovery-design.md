# Compute Accelerator Monthly Discovery Design

## Status

Approved by user on 2026-06-28.

## Goal

Existing accelerator model sources are evidence captures for known hardware
models. After a known model source has been captured successfully once, the
crawler should not keep refetching it on a schedule.

The system still needs to notice future hardware releases. It will run a
monthly discovery layer over controlled vendor, cloud, benchmark, news, and
download index sources. Discovery output is a review queue of candidate models;
it never auto-creates formal source profiles or auto-fetches candidate detail
pages.

Scope includes GPU, NPU, TPU, DPU, IPU, FPGA, DSA, and AI ASIC accelerator
families, including domestic vendors.

## Non-Goals

- No fully automatic web-wide search.
- No automatic subscription of newly detected models.
- No automatic fetch of candidate detail pages.
- No periodic refetch of successfully captured known model spec pages.
- No credential storage in source YAML, raw evidence, or git.

## Source Run Policy

Source profiles gain an optional `run_policy` field:

- `scheduled`: normal recurring behavior using the existing `schedule` field.
- `once`: a source may be manually run or scheduled until it has one successful
  run that produced a raw capture or content baseline. After that, scheduler
  skips it.

Default behavior remains compatible with existing profiles:

- If `run_policy` is omitted, treat it as `scheduled`.
- Existing concrete `compute-accelerators-*` model/spec sources will be updated
  to `run_policy: once`.
- Discovery sources use `run_policy: scheduled` and `schedule: monthly`.

The API should return `run_policy` so the frontend can show why a source will
not run again automatically.

## Discovery Profiles

Discovery profiles are source profiles with accelerator discovery metadata:

- `discovery_mode: accelerator_models`
- `schedule: monthly`
- `run_policy: scheduled`
- `extract_mode: discovery_index`
- optional `vendor_hint`
- optional `include_patterns` and `exclude_patterns`
- optional `candidate_url_patterns`

Initial discovery sources should prefer durable indexes:

- official vendor product and solution indexes,
- official vendor news and announcement indexes,
- official document or download indexes,
- cloud instance type catalogs,
- benchmark result indexes that expose accelerator names.

Sources that need login, captcha, fragile JavaScript, or aggressive scraping are
disabled until a stable fetch path or explicit auth configuration exists.

## Candidate Queue

Add an `accelerator_candidates` table:

- `id`
- `vendor`
- `model_name`
- `normalized_model`
- `scope`
- `source_profile_id`
- `source_url`
- `evidence_url`
- `evidence_text`
- `confidence`
- `status`: `pending`, `accepted`, `rejected`
- `accepted_source_id`
- `created_at`
- `updated_at`

Deduplication key:

- `vendor`
- `normalized_model`
- `coalesce(evidence_url, source_url)`

If a rediscovered pending candidate has stronger evidence or confidence, update
the existing row instead of creating a duplicate. Rejected candidates remain
rejected unless the normalized model or evidence URL changes.

## Candidate Extraction

Discovery fetches use existing web/RSS fetchers where possible, then run a
lightweight extractor over titles, link text, headings, and nearby text. The
extractor should be conservative:

- identify vendor/model-like tokens from controlled indexes,
- classify candidate scope using profile hints and keyword context,
- assign confidence from evidence quality,
- record the source text that caused the candidate.

The extractor should avoid treating generic product family pages or old pages as
new models unless there is concrete model text and an evidence URL.

## Review Flow

Frontend adds a "new accelerator candidates" review view near Sources:

- list pending candidates,
- show vendor, model, scope, confidence, source, evidence text, and discovery
  timestamp,
- allow reject with reason,
- allow accept by entering or confirming the formal source id, name, URL, and
  scope.

Acceptance creates a formal source profile equivalent to existing
`compute-accelerators-*` profiles:

- `run_policy: once`
- `auto_ingest: false`
- `auth_required: false` unless explicitly configured later
- accelerator metadata copied from the candidate and review form

The accepted source can then be manually run once from the normal source page.

## API Surface

Add endpoints:

- `GET /api/accelerator-candidates`
- `POST /api/accelerator-candidates/{id}/reject`
- `POST /api/accelerator-candidates/{id}/accept`

Acceptance should validate the new source id with the same path safety rules as
source profile loading.

## Scheduler Behavior

The scheduler keeps its existing loop and interval handling, but filters due
sources by run policy:

- `scheduled`: current behavior.
- `once`: skip when the source already has a successful fetch run with evidence
  or baseline content version.

Discovery sources run monthly and create/update candidates. They do not create
raw items for every unchanged index unless the underlying fetch result changed
under existing content-version rules.

## Testing

Backend tests:

- profile validation accepts `run_policy` and discovery metadata;
- profile validation rejects unsafe accepted source ids;
- scheduler skips completed `once` sources;
- scheduler still runs due monthly discovery sources;
- discovery extraction creates candidates from representative index content;
- discovery candidate dedup updates existing rows instead of duplicating;
- candidate acceptance creates a disabled or enabled one-shot source according
  to the request and marks the candidate accepted;
- candidate rejection does not create a source.

Frontend tests:

- source list displays run policy;
- candidate list renders pending candidates;
- accept and reject actions call the expected APIs and update state.

Wiki/catalog validation:

- `validate-accelerators` continues to pass after adding discovery metadata and
  one-shot policies.
- `validate --domain ai_infra` continues to pass.

## Rollout

1. Add schema migrations and backend model/profile support.
2. Add discovery extraction and candidate persistence.
3. Add scheduler filtering for `run_policy: once`.
4. Add API endpoints and frontend review UI.
5. Update accelerator source YAML: known model sources to `once`, discovery
   indexes to monthly scheduled.
6. Run backend, frontend, wiki validation, then task evaluator.
