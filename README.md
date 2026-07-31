# google-ads-sdk

Volkanos wrapper around the official `google-ads` Python client. Currently exposes click-conversion uploads (`ConversionsClient`); designed to grow with `ReportingClient`, `BudgetsClient`, etc. as more Volkanos modules need them.

This SDK is **stateless and Django-agnostic**. Caller passes credentials as plain strings; caller stores them however it likes (encrypted DB column, env vars, vault).

## Install

```bash
uv pip install entirius-py-google-ads-sdk
```

Or as a dependency in `pyproject.toml`:

```toml
"entirius-py-google-ads-sdk>=2.0.0"
```

## Use

```python
from google_ads_sdk import ConversionsClient, ClickConversion

client = ConversionsClient(
    developer_token="ABC...",  # global, from Google Ads dev console
    oauth_client_id="...apps.googleusercontent.com",
    oauth_client_secret="...",
    refresh_token="1//0gAa...",  # per-account, from OAuth flow (decrypt before passing)
    customer_id="8323936346",  # the account that owns the conversion actions
    login_customer_id=None,  # set if accessing via MCC
)

result = client.upload_click_conversions(
    [
        ClickConversion(
            conversion_action_id="9876543210",
            conversion_date_time="2026-04-19 14:30:00+00:00",
            conversion_value=200.0,
            currency_code="EUR",
            gclid="CjwK...",
        ),
        ClickConversion(
            conversion_action_id="9876543210",
            conversion_date_time="2026-04-19 14:31:00+00:00",
            conversion_value=200.0,
            currency_code="EUR",
            hashed_email="64-char-sha256-hex",  # enhanced fallback if no gclid
        ),
    ],
    partial_failure=True,
)
print(result.successes, result.failures)
# successes: list[int] — indices of accepted conversions
# failures:  list[ConversionFailure(index=int, error_message=str)]
```

## OAuth refresh-token flow

The SDK does not implement OAuth interactively — it expects a working refresh token. The recommended flow:

1. One-time interactive script (or a small admin endpoint) exchanges an authorization code for a refresh token via `google-auth-oauthlib`.
2. Persist the refresh token encrypted at rest — the consuming Django module is responsible for encryption.
3. Pass the decrypted token to `ConversionsClient(...)`.

## Partial failure semantics

`upload_click_conversions(..., partial_failure=True)` always returns an `UploadResult`. A whole-call failure (auth, network, malformed batch) raises `GoogleAdsUploadError`. Per-row failures are reported in `result.failures` keyed by input list index — callers can update their queue rows accordingly.

## Tests

```bash
uv run pytest
```

The `google-ads` SDK is mocked at the `client.get_service` boundary. No real account or network access is needed.
