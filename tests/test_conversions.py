# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from google_ads_sdk import (
    ClickConversion,
    ConversionFailure,
    ConversionsClient,
    GoogleAdsAuthError,
    GoogleAdsUploadError,
    UploadResult,
)
from google_ads_sdk.conversions import _SVC_ACTION, _SVC_UPLOAD, _operation_index

# Common test fixture values — kept as module-level constants so they don't drift
# across tests and so the intent of "this is a placeholder" is explicit.
_DEV_TOKEN = "dev"  # noqa: S105 — test placeholder, not a credential
_OAUTH_CLIENT_ID = "cid"
_OAUTH_CLIENT_SECRET = "csec"  # noqa: S105 — test placeholder, not a credential
_REFRESH = "refresh"
_CUSTOMER_ID = "1234567890"
_LOGIN_CUSTOMER_ID = "9876543210"
_ACTION_ID = "9999"
_CONVERSION_DT = "2026-04-19 10:00:00+00:00"


class _FakeUserIdentifier:
    def __init__(self):
        self.hashed_email = ""


class _FakeProtoConversion:
    """Stand-in for the google-ads ClickConversion proto. Attributes are set by the SDK."""

    def __init__(self):
        self.conversion_action = ""
        self.conversion_date_time = ""
        self.conversion_value = 0.0
        self.currency_code = ""
        self.gclid = ""
        self.order_id = ""
        self.user_identifiers: list[_FakeUserIdentifier] = []


class _FakeGoogleAdsFailure:
    """Stand-in for the GoogleAdsFailure proto. The SDK calls .Unpack(...) on the
    google.protobuf.Any wrapping it; the test injects errors directly on the
    returned instance via the `_failure_errors` slot."""

    _next_errors: list = []  # set by tests before each upload that should partial-fail

    def __init__(self):
        self.errors = list(_FakeGoogleAdsFailure._next_errors)


def _make_fake_client(*, types: dict | None = None) -> tuple[MagicMock, MagicMock]:
    """Build a fake google-ads client whose get_type / get_service return controllable mocks."""
    types = types or {
        "ClickConversion": _FakeProtoConversion,
        "UserIdentifier": _FakeUserIdentifier,
        "GoogleAdsFailure": _FakeGoogleAdsFailure,
    }
    fake_action_service = MagicMock()
    fake_action_service.conversion_action_path = lambda cid, aid: f"customers/{cid}/conversionActions/{aid}"
    fake_upload_service = MagicMock()

    client = MagicMock()
    client.get_type.side_effect = lambda name: types[name]()
    client.get_service.side_effect = lambda name: {_SVC_UPLOAD: fake_upload_service, _SVC_ACTION: fake_action_service}[
        name
    ]
    return client, fake_upload_service


def _stage_failure_errors(errors: list) -> None:
    """Inject errors that the next ``GoogleAdsFailure()`` will be initialised with."""
    _FakeGoogleAdsFailure._next_errors = errors


def _make_detail_for(errors: list) -> MagicMock:
    """Build a fake protobuf.Any whose .Unpack() seeds the failure proto with errors."""
    _stage_failure_errors(errors)
    detail = MagicMock()
    # Unpack writes nothing; the test's _FakeGoogleAdsFailure already pulled errors
    # from the staged class variable at __init__ time.
    detail.Unpack = MagicMock(return_value=True)
    return detail


def _make_client(
    fake_client: MagicMock, *, customer_id: str = _CUSTOMER_ID, login_customer_id: str | None = None
) -> ConversionsClient:
    with patch("google_ads_sdk.conversions.build_client", return_value=fake_client):
        return ConversionsClient(
            developer_token=_DEV_TOKEN,
            oauth_client_id=_OAUTH_CLIENT_ID,
            oauth_client_secret=_OAUTH_CLIENT_SECRET,
            refresh_token=_REFRESH,
            customer_id=customer_id,
            login_customer_id=login_customer_id,
        )


def _success_response() -> SimpleNamespace:
    return SimpleNamespace(partial_failure_error=SimpleNamespace(code=0, details=[]))


def _conv(action_id: str = _ACTION_ID, gclid: str | None = "ok", **kwargs) -> ClickConversion:
    return ClickConversion(
        conversion_action_id=action_id,
        conversion_date_time=_CONVERSION_DT,
        conversion_value=kwargs.pop("conversion_value", 200.0),
        currency_code=kwargs.pop("currency_code", "EUR"),
        gclid=gclid,
        **kwargs,
    )


# ---------------- ClickConversion.__post_init__ ----------------


def test_post_init_rejects_conversion_without_gclid_or_hashed_email():
    with pytest.raises(ValueError, match="requires gclid or hashed_email"):
        ClickConversion(
            conversion_action_id="999", conversion_date_time=_CONVERSION_DT, conversion_value=1.0, currency_code="EUR"
        )


def test_post_init_accepts_conversion_with_only_gclid():
    c = ClickConversion(
        conversion_action_id="999",
        conversion_date_time=_CONVERSION_DT,
        conversion_value=1.0,
        currency_code="EUR",
        gclid="x",
    )
    assert c.gclid == "x"


def test_post_init_accepts_conversion_with_only_hashed_email():
    c = ClickConversion(
        conversion_action_id="999",
        conversion_date_time=_CONVERSION_DT,
        conversion_value=1.0,
        currency_code="EUR",
        hashed_email="abc",
    )
    assert c.hashed_email == "abc"


# ---------------- ConversionsClient construction ----------------


def test_build_client_missing_developer_token_raises():
    with pytest.raises(GoogleAdsAuthError, match="developer_token"):
        ConversionsClient(
            developer_token="",
            oauth_client_id=_OAUTH_CLIENT_ID,
            oauth_client_secret=_OAUTH_CLIENT_SECRET,
            refresh_token=_REFRESH,
            customer_id=_CUSTOMER_ID,
        )


def test_build_client_missing_oauth_client_id_raises():
    with pytest.raises(GoogleAdsAuthError, match="oauth_client_id"):
        ConversionsClient(
            developer_token=_DEV_TOKEN,
            oauth_client_id="",
            oauth_client_secret=_OAUTH_CLIENT_SECRET,
            refresh_token=_REFRESH,
            customer_id=_CUSTOMER_ID,
        )


def test_build_client_missing_oauth_client_secret_raises():
    with pytest.raises(GoogleAdsAuthError, match="oauth_client_secret"):
        ConversionsClient(
            developer_token=_DEV_TOKEN,
            oauth_client_id=_OAUTH_CLIENT_ID,
            oauth_client_secret="",
            refresh_token=_REFRESH,
            customer_id=_CUSTOMER_ID,
        )


def test_build_client_missing_refresh_token_raises():
    with pytest.raises(GoogleAdsAuthError, match="refresh_token"):
        ConversionsClient(
            developer_token=_DEV_TOKEN,
            oauth_client_id=_OAUTH_CLIENT_ID,
            oauth_client_secret=_OAUTH_CLIENT_SECRET,
            refresh_token="",
            customer_id=_CUSTOMER_ID,
        )


def test_missing_customer_id_raises():
    with patch("google_ads_sdk.conversions.build_client", return_value=MagicMock()):
        with pytest.raises(ValueError):
            ConversionsClient(
                developer_token=_DEV_TOKEN,
                oauth_client_id=_OAUTH_CLIENT_ID,
                oauth_client_secret=_OAUTH_CLIENT_SECRET,
                refresh_token=_REFRESH,
                customer_id="",
            )


def test_build_client_load_from_dict_failure_wraps_to_auth_error():
    with patch(
        "google_ads_sdk._client_factory.UpstreamClient.load_from_dict", side_effect=ValueError("invalid config")
    ):
        with pytest.raises(GoogleAdsAuthError, match="Failed to build"):
            ConversionsClient(
                developer_token=_DEV_TOKEN,
                oauth_client_id=_OAUTH_CLIENT_ID,
                oauth_client_secret=_OAUTH_CLIENT_SECRET,
                refresh_token=_REFRESH,
                customer_id=_CUSTOMER_ID,
            )


def test_build_client_attribute_error_propagates_unwrapped():
    """Programmer bugs in factory dict construction must NOT be masked as auth errors."""
    with patch("google_ads_sdk._client_factory.UpstreamClient.load_from_dict", side_effect=AttributeError("oops")):
        with pytest.raises(AttributeError):
            ConversionsClient(
                developer_token=_DEV_TOKEN,
                oauth_client_id=_OAUTH_CLIENT_ID,
                oauth_client_secret=_OAUTH_CLIENT_SECRET,
                refresh_token=_REFRESH,
                customer_id=_CUSTOMER_ID,
            )


def test_login_customer_id_forwarded_to_load_from_dict():
    captured: dict = {}

    def capture(config):
        captured.update(config)
        return MagicMock()

    with patch("google_ads_sdk._client_factory.UpstreamClient.load_from_dict", side_effect=capture):
        ConversionsClient(
            developer_token=_DEV_TOKEN,
            oauth_client_id=_OAUTH_CLIENT_ID,
            oauth_client_secret=_OAUTH_CLIENT_SECRET,
            refresh_token=_REFRESH,
            customer_id=_CUSTOMER_ID,
            login_customer_id=_LOGIN_CUSTOMER_ID,
        )
    assert captured["login_customer_id"] == _LOGIN_CUSTOMER_ID


def test_login_customer_id_omitted_when_none():
    captured: dict = {}

    def capture(config):
        captured.update(config)
        return MagicMock()

    with patch("google_ads_sdk._client_factory.UpstreamClient.load_from_dict", side_effect=capture):
        ConversionsClient(
            developer_token=_DEV_TOKEN,
            oauth_client_id=_OAUTH_CLIENT_ID,
            oauth_client_secret=_OAUTH_CLIENT_SECRET,
            refresh_token=_REFRESH,
            customer_id=_CUSTOMER_ID,
        )
    assert "login_customer_id" not in captured


# ---------------- upload_click_conversions ----------------


def test_empty_input_returns_empty_result():
    fake_client, _ = _make_fake_client()
    client = _make_client(fake_client)
    result = client.upload_click_conversions([])
    assert result == UploadResult(successes=(), failures=())


def test_upload_with_gclid_builds_proto_correctly():
    fake_client, fake_upload = _make_fake_client()
    fake_upload.upload_click_conversions.return_value = _success_response()
    client = _make_client(fake_client)
    result = client.upload_click_conversions([_conv(gclid="CjwK-abc", order_id="order-7")])

    assert result.successes == (0,)
    assert result.failures == ()
    call_kwargs = fake_upload.upload_click_conversions.call_args.kwargs
    assert call_kwargs["customer_id"] == _CUSTOMER_ID
    assert call_kwargs["partial_failure"] is True
    sent = call_kwargs["conversions"][0]
    assert sent.conversion_action == f"customers/{_CUSTOMER_ID}/conversionActions/{_ACTION_ID}"
    assert sent.gclid == "CjwK-abc"
    assert sent.order_id == "order-7"
    assert sent.user_identifiers == []


def test_upload_with_hashed_email_appends_user_identifier():
    fake_client, fake_upload = _make_fake_client()
    fake_upload.upload_click_conversions.return_value = _success_response()
    client = _make_client(fake_client)
    client.upload_click_conversions(
        [
            ClickConversion(
                conversion_action_id=_ACTION_ID,
                conversion_date_time=_CONVERSION_DT,
                conversion_value=500.0,
                currency_code="EUR",
                hashed_email="abcdef" * 10,
            )
        ]
    )
    sent = fake_upload.upload_click_conversions.call_args.kwargs["conversions"][0]
    assert len(sent.user_identifiers) == 1
    assert sent.user_identifiers[0].hashed_email == "abcdef" * 10
    assert sent.gclid == ""


def test_upload_call_raising_googleadsexception_wraps_to_upload_error():
    from google.ads.googleads.errors import GoogleAdsException

    fake_client, fake_upload = _make_fake_client()
    fake_upload.upload_click_conversions.side_effect = GoogleAdsException(
        error=MagicMock(), call=MagicMock(), failure=MagicMock(), request_id="req-1"
    )
    client = _make_client(fake_client)
    with pytest.raises(GoogleAdsUploadError):
        client.upload_click_conversions([_conv()])


# ---------------- _parse_response (partial-failure paths) ----------------


def test_partial_failure_marks_correct_index_failed():
    fake_client, fake_upload = _make_fake_client()
    err = SimpleNamespace(
        message="GCLID expired", location=SimpleNamespace(field_path_elements=[SimpleNamespace(index=1)])
    )
    detail = _make_detail_for([err])
    fake_upload.upload_click_conversions.return_value = SimpleNamespace(
        partial_failure_error=SimpleNamespace(code=3, details=[detail])
    )
    client = _make_client(fake_client)
    result = client.upload_click_conversions([_conv(action_id="A", gclid="ok"), _conv(action_id="B", gclid="bad")])

    assert result.successes == (0,)
    assert result.failures == (ConversionFailure(index=1, error_message="GCLID expired"),)


def test_partial_failure_with_location_none_reported_with_index_minus_one():
    """If a failure has no location (batch-level error), it is reported with index=-1
    rather than silently dropped — caller sees the contract break."""
    fake_client, fake_upload = _make_fake_client()
    err = SimpleNamespace(message="batch quota exceeded", location=None)
    detail = _make_detail_for([err])
    fake_upload.upload_click_conversions.return_value = SimpleNamespace(
        partial_failure_error=SimpleNamespace(code=3, details=[detail])
    )
    client = _make_client(fake_client)
    result = client.upload_click_conversions([_conv()])

    assert result.successes == (0,)  # index 0 not in failed_indices because failure has -1
    assert result.failures == (ConversionFailure(index=-1, error_message="batch quota exceeded"),)


def test_partial_failure_with_out_of_bounds_index_reported_with_minus_one():
    """If Google reports index=99 for a 1-conversion call, surface as -1 not silently drop."""
    fake_client, fake_upload = _make_fake_client()
    err = SimpleNamespace(message="phantom", location=SimpleNamespace(field_path_elements=[SimpleNamespace(index=99)]))
    detail = _make_detail_for([err])
    fake_upload.upload_click_conversions.return_value = SimpleNamespace(
        partial_failure_error=SimpleNamespace(code=3, details=[detail])
    )
    client = _make_client(fake_client)
    result = client.upload_click_conversions([_conv()])

    assert result.successes == (0,)
    assert result.failures[0].index == -1


def test_partial_failure_reported_but_no_recoverable_error_raises():
    """If partial_failure_error.code != 0 but errors list is empty, surface as
    GoogleAdsUploadError instead of falsely reporting success."""
    fake_client, fake_upload = _make_fake_client()
    detail = _make_detail_for([])  # no errors despite partial-failure flag
    fake_upload.upload_click_conversions.return_value = SimpleNamespace(
        partial_failure_error=SimpleNamespace(code=3, details=[detail])
    )
    client = _make_client(fake_client)
    with pytest.raises(GoogleAdsUploadError, match="no operation index recoverable"):
        client.upload_click_conversions([_conv()])


# ---------------- _unpack_failure (now a method on ConversionsClient) ----------------


def test_unpack_failure_uses_client_get_type_and_calls_unpack():
    """Verifies _unpack_failure goes through the client's proto registry (not a
    versioned import) and actually calls Unpack on the wrapped Any."""
    fake_client, _ = _make_fake_client()
    client = _make_client(fake_client)

    detail = MagicMock()
    detail.Unpack = MagicMock(return_value=True)
    failure = client._unpack_failure(detail)
    assert isinstance(failure, _FakeGoogleAdsFailure)
    detail.Unpack.assert_called_once()


def test_unpack_failure_propagates_unpack_errors():
    """Drift in upstream proto schema should NOT be silently swallowed."""
    fake_client, _ = _make_fake_client()
    client = _make_client(fake_client)

    detail = MagicMock()
    detail.Unpack = MagicMock(side_effect=RuntimeError("proto schema drifted"))
    with pytest.raises(RuntimeError, match="proto schema drifted"):
        client._unpack_failure(detail)


# ---------------- _operation_index ----------------


def test_operation_index_handles_missing_location():
    err = SimpleNamespace(location=None)
    assert _operation_index(err) is None


def test_operation_index_handles_empty_elements():
    err = SimpleNamespace(location=SimpleNamespace(field_path_elements=[]))
    assert _operation_index(err) is None


def test_operation_index_returns_value():
    err = SimpleNamespace(location=SimpleNamespace(field_path_elements=[SimpleNamespace(index=7)]))
    assert _operation_index(err) == 7
