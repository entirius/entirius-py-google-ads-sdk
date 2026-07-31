# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Builds a ``GoogleAdsClient`` from a flat credentials dict. See ``build_client``."""

from typing import Any

from google.ads.googleads.client import GoogleAdsClient as UpstreamClient
from google.auth.exceptions import GoogleAuthError

from google_ads_sdk.exceptions import GoogleAdsAuthError


def build_client(
    *,
    developer_token: str,
    oauth_client_id: str,
    oauth_client_secret: str,
    refresh_token: str,
    login_customer_id: str | None = None,
) -> UpstreamClient:
    if not developer_token:
        raise GoogleAdsAuthError("developer_token is required")
    if not oauth_client_id:
        raise GoogleAdsAuthError("oauth_client_id is required")
    if not oauth_client_secret:
        raise GoogleAdsAuthError("oauth_client_secret is required")
    if not refresh_token:
        raise GoogleAdsAuthError("refresh_token is required (complete OAuth flow first)")

    config: dict[str, Any] = {
        "developer_token": developer_token,
        "client_id": oauth_client_id,
        "client_secret": oauth_client_secret,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    if login_customer_id:
        config["login_customer_id"] = login_customer_id

    try:
        return UpstreamClient.load_from_dict(config)
    except (ValueError, GoogleAuthError) as exc:
        # Caller-actionable failures only: bad config / rejected credentials.
        # AttributeError / TypeError propagate — those are programmer bugs in
        # how this factory builds the dict, not auth issues.
        raise GoogleAdsAuthError(f"Failed to build Google Ads client: {exc}") from exc
