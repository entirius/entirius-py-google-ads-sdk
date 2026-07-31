# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


class GoogleAdsSDKError(Exception):
    """Base for all errors this SDK raises."""


class GoogleAdsAuthError(GoogleAdsSDKError):
    """Refresh token rejected, developer token missing, or login_customer_id invalid."""


class GoogleAdsUploadError(GoogleAdsSDKError):
    """A whole upload call failed (not partial-failure — that's reported in UploadResult)."""
