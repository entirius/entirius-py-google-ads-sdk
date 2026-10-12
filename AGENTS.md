# AGENTS.md

Wrapper for the official `google-ads` Python client — distribution `entirius-py-google-ads-sdk`,
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

### Commit Message Format

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

Tests: `make test`. `google-ads` is fully mocked at the `client.get_service` boundary; the fake-proto stand-ins
assert SDK behavior without instantiating real proto messages.

| Topic | Where |
|---|---|
| Public API: classes, signatures, exceptions | `docs/api.md` |
| Design rules, adding a new sub-client, anti-patterns | `docs/design.md` |
| OAuth refresh-token flow, partial-failure semantics | `docs/usage.md` |
