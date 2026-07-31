# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Click-conversion uploads via Google Ads ConversionUploadService."""

from collections.abc import Sequence
from typing import Any

from google.ads.googleads.errors import GoogleAdsException

from google_ads_sdk._client_factory import build_client
from google_ads_sdk.exceptions import GoogleAdsUploadError
from google_ads_sdk.types import ClickConversion, ConversionFailure, UploadResult

# Google Ads service / type names. Kept as constants so a single rename when the
# upstream library changes naming conventions is one place, not five.
_SVC_UPLOAD = "ConversionUploadService"
_SVC_ACTION = "ConversionActionService"
_TYPE_CLICK_CONVERSION = "ClickConversion"
_TYPE_USER_IDENTIFIER = "UserIdentifier"
_TYPE_GOOGLE_ADS_FAILURE = "GoogleAdsFailure"


class ConversionsClient:
    """Uploads offline click-conversions for a single Google Ads customer.

    ``__init__`` performs credential validation and may raise ``GoogleAdsAuthError``
    — instantiate inside a try/except at the call site.
    """

    def __init__(
        self,
        *,
        developer_token: str,
        oauth_client_id: str,
        oauth_client_secret: str,
        refresh_token: str,
        customer_id: str,
        login_customer_id: str | None = None,
    ) -> None:
        if not customer_id:
            raise ValueError("customer_id is required")
        self.customer_id = customer_id
        self._client = build_client(
            developer_token=developer_token,
            oauth_client_id=oauth_client_id,
            oauth_client_secret=oauth_client_secret,
            refresh_token=refresh_token,
            login_customer_id=login_customer_id,
        )
        # Resolve once — these services are stateless lookups; no need to fetch per upload.
        self._upload_service = self._client.get_service(_SVC_UPLOAD)
        self._action_service = self._client.get_service(_SVC_ACTION)

    def upload_click_conversions(
        self, conversions: Sequence[ClickConversion], *, partial_failure: bool = True
    ) -> UploadResult:
        if not conversions:
            return UploadResult(successes=(), failures=())

        proto_conversions = [self._build_proto(c) for c in conversions]

        try:
            response = self._upload_service.upload_click_conversions(
                customer_id=self.customer_id, conversions=proto_conversions, partial_failure=partial_failure
            )
        except GoogleAdsException as exc:
            raise GoogleAdsUploadError(f"upload_click_conversions failed: {exc}") from exc

        return self._parse_response(response, len(conversions))

    def _parse_response(self, response: Any, total: int) -> UploadResult:
        """Map google-ads response to UploadResult.

        On partial-failure, ``response.partial_failure_error.details`` contains
        ``GoogleAdsFailure`` protos. Each error inside has a
        ``location.field_path_elements[0].index`` pointing back to the source
        operation. Failures with a missing or out-of-range index are reported
        in ``failures`` with ``index=-1`` so callers can detect upstream
        contract breaks rather than silently treating the row as a success.
        """
        failures: list[ConversionFailure] = []
        failed_indices: set[int] = set()

        partial_error = getattr(response, "partial_failure_error", None)
        if partial_error and partial_error.code != 0:
            for detail in partial_error.details:
                failure_proto = self._unpack_failure(detail)
                for err in failure_proto.errors:
                    idx = _operation_index(err)
                    if idx is None or not (0 <= idx < total):
                        failures.append(ConversionFailure(index=-1, error_message=err.message))
                        continue
                    failed_indices.add(idx)
                    failures.append(ConversionFailure(index=idx, error_message=err.message))

            if not failures:
                # API said partial-failure occurred but we couldn't extract a single
                # actionable error — surface this as a hard failure rather than
                # silently reporting all rows as success.
                raise GoogleAdsUploadError("partial_failure_error reported but no operation index recoverable")

        successes = tuple(i for i in range(total) if i not in failed_indices)
        return UploadResult(successes=successes, failures=tuple(failures))

    def _unpack_failure(self, detail: Any) -> Any:
        """Unwrap a ``google.protobuf.Any`` carrying a ``GoogleAdsFailure``.

        The proto class is fetched via the client's type registry rather than
        imported directly, because google-ads moves it under a version-specific
        path (``google.ads.googleads.v{N}.errors.types.errors``) that varies
        across releases. Unpack errors propagate — a failure here means the
        upstream proto schema drifted, not "no failure to report".
        """
        failure = self._client.get_type(_TYPE_GOOGLE_ADS_FAILURE)
        detail.Unpack(failure._pb if hasattr(failure, "_pb") else failure)
        return failure

    def _build_proto(self, c: ClickConversion) -> Any:
        # ClickConversion.__post_init__ already enforces gclid OR hashed_email —
        # by the time we get here the invariant holds.
        proto = self._client.get_type(_TYPE_CLICK_CONVERSION)
        proto.conversion_action = self._action_service.conversion_action_path(self.customer_id, c.conversion_action_id)
        proto.conversion_date_time = c.conversion_date_time
        proto.conversion_value = c.conversion_value
        proto.currency_code = c.currency_code
        if c.gclid:
            proto.gclid = c.gclid
        if c.hashed_email:
            user_id = self._client.get_type(_TYPE_USER_IDENTIFIER)
            user_id.hashed_email = c.hashed_email
            proto.user_identifiers.append(user_id)
        if c.order_id:
            proto.order_id = c.order_id
        return proto


def _operation_index(err: Any) -> int | None:
    location = getattr(err, "location", None)
    if location is None:
        return None
    elements = getattr(location, "field_path_elements", None) or []
    if not elements:
        return None
    return getattr(elements[0], "index", None)
