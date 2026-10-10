# Design

## Design rules

- **Stateless beyond the upstream client.** No caching of conversion-action IDs, no retry loops — the consuming worker (Celery) owns retry policy.
- **Whole-call failures raise; per-row failures are reported.** Callers can rely on always getting an `UploadResult` when the call returned at all (with `partial_failure=True`). When `partial_failure=False`, any single row error becomes a whole-call `GoogleAdsUploadError`; `UploadResult.failures` will be empty only because the exception is raised instead.
- **Failures with no recoverable index are surfaced, not silenced.** A failure with no `location` (batch-level error) or out-of-range index is reported in `failures` with `index=-1`. If `partial_failure_error` is set but no error has any extractable info at all, the SDK raises `GoogleAdsUploadError` rather than falsely reporting all rows as success. `_unpack_failure` lets proto-Unpack errors propagate (signal of upstream schema drift, not "no failure").
- **No OAuth flow.** The SDK takes a refresh token already obtained. The consumer module is responsible for storing/decrypting it.
- **Resource-name building stays here.** Callers pass `conversion_action_id` as a digits-only string; the SDK constructs `customers/{cid}/conversionActions/{aid}` internally via `ConversionActionService.conversion_action_path` (resolved once at `__init__`).
- **Validation at the boundary.** All five credentials checked for emptiness in `build_client`; `customer_id` checked in `ConversionsClient.__init__`. `ClickConversion.__post_init__` enforces that `gclid` or `hashed_email` is set — invalid instances cannot be constructed.
- **Frozen value types use tuples, not lists.** `UploadResult.successes` and `failures` are tuples so a frozen dataclass actually behaves immutably (caller can't `result.successes.append(...)`).

## Adding a new sub-client (future)

Pattern for `ReportingClient`, `BudgetsClient`, etc.:
1. New file `src/google_ads_sdk/{feature}.py` with one class.
2. Reuse `_client_factory.build_client(...)` for the upstream client.
3. Add re-exports to `__init__.py`.
4. Tests mock at `client.get_service("...Service")` like the conversions tests.

## Anti-patterns

DO NOT:
- Import `django.*` or any Volkanos package
- Add config-loading logic (env vars, settings) — caller passes plain values
- Hide partial-failure errors from callers — surface them in `UploadResult.failures`
- Add retry/backoff inside the SDK — the consuming Celery worker owns retry
- Create a "high-level uploader" helper that knows about OfflineConversionQueue rows — that belongs in `django-contact-forms.services.conversions`
