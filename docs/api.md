# Public API

| Symbol | Purpose |
|---|---|
| `ConversionsClient(developer_token, oauth_client_id, oauth_client_secret, refresh_token, customer_id, login_customer_id=None)` | Click-conversion upload client, single customer per instance |
| `.upload_click_conversions(conversions, partial_failure=True) -> UploadResult` | Batch upload — empty list returns empty result, never errors |
| `ClickConversion(conversion_action_id, conversion_date_time, conversion_value, currency_code, gclid=None, hashed_email=None, order_id=None)` | One conversion to upload (gclid OR hashed_email required) |
| `UploadResult(successes: tuple[int, ...], failures: tuple[ConversionFailure, ...])` | Indices into the input list |
| `ConversionFailure(index, error_message)` | One per-row failure |
| `GoogleAdsSDKError`, `GoogleAdsAuthError`, `GoogleAdsUploadError` | Typed exceptions |
