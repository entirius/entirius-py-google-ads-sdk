# AGENTS.md

Volkanos wrapper for the official `google-ads` Python client — distribution `entirius-py-google-ads-sdk`,
import `google_ads_sdk`. Currently exposes click-conversion uploads (`ConversionsClient`); namespace is open
for future `ReportingClient`, `BudgetsClient`, etc. without API breaks. No Django, no Volkanos coupling.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the import package `google_ads_sdk` — it is a public API contract.
- Default: do not commit — git is the user's call.

## Commit Message Format

**NEVER add `Co-Authored-By: Claude ...` (or any other Claude/Anthropic attribution) to commit messages.**

This overrides the default Claude Code behavior of appending a `Co-Authored-By` trailer. Commit messages MUST contain only the user's authored content — no robot footer, no "Generated with Claude Code" line, no co-author trailer.

Same rule applies to PR descriptions: no `Generated with [Claude Code]` footer.

## Architecture

```
src/google_ads_sdk/
├── __init__.py                # Re-exports the public API
├── conversions.py             # ConversionsClient — upload_click_conversions
├── _client_factory.py         # build_client(...) — wraps GoogleAdsClient.load_from_dict
├── types.py                   # ClickConversion, UploadResult, ConversionFailure
└── exceptions.py              # GoogleAdsSDKError, GoogleAdsAuthError, GoogleAdsUploadError

tests/
└── test_conversions.py        # Mocks google-ads at client.get_service boundary
```

## Public API

| Symbol | Purpose |
|---|---|
| `ConversionsClient(developer_token, oauth_client_id, oauth_client_secret, refresh_token, customer_id, login_customer_id=None)` | Click-conversion upload client, single customer per instance |
| `.upload_click_conversions(conversions, partial_failure=True) -> UploadResult` | Batch upload — empty list returns empty result, never errors |
| `ClickConversion(conversion_action_id, conversion_date_time, conversion_value, currency_code, gclid=None, hashed_email=None, order_id=None)` | One conversion to upload (gclid OR hashed_email required) |
| `UploadResult(successes: list[int], failures: list[ConversionFailure])` | Indices into the input list |
| `ConversionFailure(index, error_message)` | One per-row failure |
| `GoogleAdsSDKError`, `GoogleAdsAuthError`, `GoogleAdsUploadError` | Typed exceptions |

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

## Testing

```bash
uv run pytest
```

`google-ads` is fully mocked. The fake-proto stand-ins in tests assert SDK behavior without instantiating real proto messages.

## Anti-patterns

DO NOT:
- Import `django.*` or any Volkanos package
- Add config-loading logic (env vars, settings) — caller passes plain values
- Hide partial-failure errors from callers — surface them in `UploadResult.failures`
- Add retry/backoff inside the SDK — the consuming Celery worker owns retry
- Create a "high-level uploader" helper that knows about OfflineConversionQueue rows — that belongs in `django-contact-forms.services.conversions`
