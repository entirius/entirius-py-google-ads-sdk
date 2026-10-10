# Usage

## OAuth refresh-token flow

The SDK does not implement OAuth interactively — it expects a working refresh token. The recommended flow:

1. One-time interactive script (or a small admin endpoint) exchanges an authorization code for a refresh token via `google-auth-oauthlib`.
2. Persist the refresh token encrypted at rest — the consuming Django module is responsible for encryption.
3. Pass the decrypted token to `ConversionsClient(...)`.

## Partial failure semantics

`upload_click_conversions(..., partial_failure=True)` always returns an `UploadResult`. A whole-call failure (auth, network, malformed batch) raises `GoogleAdsUploadError`. Per-row failures are reported in `result.failures` keyed by input list index — callers can update their queue rows accordingly.
