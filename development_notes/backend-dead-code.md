# Backend dead code (last-lab-be)

For review. **Nothing here has been removed.** Paths are relative to `last-lab-be/`.

- **Dead**: unused, and not part of any plan.
- **Your call**: unused, or used only by disabled code, and not mentioned in the plan either way.
- Features that are planned but currently broken are disabled with `# TODO` comments. They are listed at the bottom for reference, not as dead code.

## Dead: whole modules

| Path | Why it is dead |
|---|---|
| `app/routers/lab/composite/thread_registry.py` | JSON-file thread registry, replaced by the `threads` table. Nothing imports it. |
| `app/services/generation_record.py` | The `generations` table is gone; reusing a canonical thread replaces it. Still imported by the disabled `compute.py` and by `seal/pipeline.py`. Drop those imports in their revamps. |
| `app/services/generation_shredder.py` | Typed output rows are not needed: outputs live in the checkpointer. Still referenced by `seal/pipeline.py` and `seal/resources.py`. |
| `app/services/outputs_service.py` | Reads the typed rows back. Nothing imports it. |
| `app/routers/lab/standalone/mindmap.py`, `app/schemas/mindmap.py` | Mock mindmap endpoint. Imports the removed `mindmap_service` and was never mounted; the mindmap arrives in the lab stream. |
| `app/services/future/rate_limit.py` | Part of the removed gates. Only the disabled `artifacts.py` imports it. |
| `app/services/future/platform_capacity_service.py` | The "we're full" capacity guard, removed. Only the disabled `admin.py` and `compute.py` import it. |
| `app/services/future/anomaly.py` | Tripwires on the removed gates. Only disabled code imports it (`dependencies/admin.py`, `compute.py`, `seal/sealed_reader.py`). |
| `app/services/legacy/demo_content.py` | Mock-engine demo content. Imports the removed `study_mocks_service`; nothing imports it. |
| `app/services/legacy/env_builder_service.py` | The environment pipeline was removed. Nothing imports it. |
| `app/services/legacy/infra/storage/` | The S3 store, replaced by GCS. Nothing imports it. |
| `app/schemas/careers.py` | The careers route was removed. |
| `app/db/migrations/` | Empty package; Alembic uses `alembic/`. |

## Dead: pieces inside live files

- `app/main.py`: `_CAREER_FIELD_LABELS` and the `/career-applications` branch of `validation_exception_handler` (that route was removed).
- `app/schemas/__init__.py`:
  - `__all__` lists `TimestampedQuizQuestion`, `ExtractedLens`, `BeyondLens` and `GeneratedNotebooks`, which are never imported, so a star import raises.
  - It also re-exports the dead request schemas below.
- `app/schemas/requests.py`: `GenerateTocRequest`, `GenerateTocResponse`, `GenerateLabRequest`, `GenerateLabResponse`, `InputSchema`, `LabOpenResponse` (the old generate-lab and open flow; nothing references them).
- `app/schemas/contact.py`: `ContactSubmissionResponse`, `ContactValidationErrorResponse`, `ContactErrorResponse` (the contact route never uses them).
- `app/dependencies/auth.py`: `get_current_active_user`.
- `app/services/semantic_resource_resolver_service.py`: `get_semantic_resource_resolver`.
- `app/services/core/pipelines/`: `process_first_page`, in both the base class and the LLM implementation.
- `app/config/settings.py`: `GENERATION_MONTHLY_LIMIT`, `GENERATION_MONTHLY_PLATFORM_LIMIT`, `GENERATION_WAIT_POLL_SECONDS`, `GENERATION_WAIT_TIMEOUT_SECONDS`, `PREWARM_MIN_BUDGET_SECONDS` (nothing reads them).
- `app/routers/lab/composite/__init__.py`: the module docstring describes `thread_registry`, `generation` and `library` layers that no longer exist.
- Tests and scripts tied to dead code:
  - `tests/legacy/` (both files) test the dead legacy modules above; remove them together.
  - `tests/test_skipped_suites_have_not_rotted.py`: `NAMESPACES["identity"]` points at the removed `app.services.core.identity`.
  - `scripts/seed_lab.py` uses the removed `identity` and `generation_record`.
  - `scripts/spawn_walkthrough.py` uses `platform_capacity_service`.

## Your call

- **Bring-your-own LLM keys:** `app/services/future/byok_service.py`, `app/routers/settings_keys.py` (mounted and working), `app/db/models/auth/llm_key.py`.
- **GitHub repo ingestion:** `app/services/future/git_resolver.py` and `POST /internal/resolve/git` (mounted).
- `app/services/email_service.py`: nothing imports it. The planned digest to Slack and email could use it.
- `app/db/models/auth/waitlist.py` (`Waitlist`): only the disabled digest reads it. Keep it while the table exists.
- `app/services/legacy/infra/clouds/aws.py`: still what the cloud abstraction selects when the provider is AWS.
- `app/scripts/send_email_personalized.py`: nothing imports it, but `tests/test_remediation_high.py` references it.
- Settings never read in this repo: `ANTHROPIC_API_KEY`, `GCP_REGION`, `JWT_ALGORITHM`, `JWT_SECRET`, `TURN_LENS_EXTRACTOR_ON`, `USERHOMES_GSA_EMAIL`. `last_lab` or your infrastructure may read them from the environment.

## Disabled with `# TODO` (planned, not dead)

| Feature | Where the `TODO` is | Code that goes with it |
|---|---|---|
| Admin dashboard | `app/routers/__init__.py` | `app/routers/admin.py`, `app/dependencies/admin.py`, the admin functions in `quota_service.py` |
| Sealing (artifacts, notes) | `app/routers/__init__.py`, `app/routers/lab/__init__.py` | `app/routers/artifacts.py`, `app/routers/lab/standalone/notes.py`, `app/services/seal/` |
| Compute attachment | `app/routers/lab/__init__.py` | `app/routers/lab/composite/compute.py`, `runtime_execution/lab_handle.py`, `runtime_execution/lab_status_service.py` |
| Library | `app/routers/lab/__init__.py` | `app/routers/lab/composite/library.py` |
| Daily digest | `app/main.py` (lifespan) | `app/services/future/digest_service.py` |
| Draining runs on shutdown | `app/main.py` (lifespan) | none; `protocol.drain_runs` was removed |
| Axiom chat | not mounted (never was) | `app/routers/lab/standalone/axiom.py`, `app/services/future/axiom_service.py` |

## Bug found while auditing (not dead code)

- In `app/main.py`, `validation_exception_handler` compares the request path to `/contact-submissions`, but the route is mounted at `/api/contact-submissions`. Contact form validation errors therefore never return `fieldErrors`.
