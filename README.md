# entirius-py-google-ads-sdk

A Python client for uploading click conversions to the Google Ads API, part of
Entirius, the open-source modular ecommerce platform. It wraps the official `google-ads` client behind one
`ConversionsClient`; it is stateless and has no Django dependency: the caller passes credentials as plain strings.

[![PyPI](https://img.shields.io/pypi/v/entirius-py-google-ads-sdk.svg)](https://pypi.org/project/entirius-py-google-ads-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-py-google-ads-sdk.svg)](https://pypi.org/project/entirius-py-google-ads-sdk/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-py-google-ads-sdk/blob/develop/LICENSE)

## What it does

- Uploads a batch of click conversions for one Google Ads customer (`upload_click_conversions()`).
- Identifies a conversion by `gclid` or, as the enhanced-conversions fallback, by `hashed_email`.
- Reports per-row results: `UploadResult.successes` and `UploadResult.failures` hold indices into the input list.
- Raises typed exceptions for whole-call failures (`GoogleAdsAuthError`, `GoogleAdsUploadError`).
- Reaches an account through a manager account when `login_customer_id` is set.

## Installation

```shell
uv add entirius-py-google-ads-sdk
pip install entirius-py-google-ads-sdk
```

The import name is `google_ads_sdk`.

## Quick start

```python
from google_ads_sdk import ClickConversion, ConversionsClient

client = ConversionsClient(
    developer_token="...", oauth_client_id="...", oauth_client_secret="...",
    refresh_token="...", customer_id="1234567890",
)
conversion = ClickConversion(
    conversion_action_id="9876543210", conversion_date_time="2026-04-19 14:30:00+00:00",
    conversion_value=200.0, currency_code="EUR", gclid="...",
)
result = client.upload_click_conversions([conversion])
print(result.successes, result.failures)
```

## Requirements

- Python 3.11 or newer.
- `google-ads` and `google-auth` (installed as dependencies).
- A Google Ads developer token, an OAuth client id and secret, and a refresh token for the account.

## Documentation

- Usage (OAuth refresh token, partial failures): https://github.com/entirius/entirius-py-google-ads-sdk/blob/develop/docs/usage.md
- Public API: https://github.com/entirius/entirius-py-google-ads-sdk/blob/develop/docs/api.md
- Design rules: https://github.com/entirius/entirius-py-google-ads-sdk/blob/develop/docs/design.md
- Entirius documentation: https://docs.entirius.com/
- Releases: https://github.com/entirius/entirius-py-google-ads-sdk/releases

## Part of Entirius

This SDK is the Google Ads client of the Entirius backend service (Volkanos) and its modules.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Consumer module: https://github.com/entirius/entirius-django-contact-forms

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest); the Google Ads client is mocked, no account or network needed
```

Development and agent instructions: https://github.com/entirius/entirius-py-google-ads-sdk/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-py-google-ads-sdk/blob/develop/LICENSE.
