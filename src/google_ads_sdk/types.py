# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass


@dataclass(frozen=True)
class ClickConversion:
    """One click-conversion to upload.

    At least one of ``gclid`` or ``hashed_email`` must be set:
    - ``gclid`` is the primary identifier (Google Click ID).
    - ``hashed_email`` (lower-cased, SHA-256-hex) is the enhanced-conversions fallback.

    The invariant is enforced in ``__post_init__`` so an invalid instance cannot
    be constructed in the first place.
    """

    conversion_action_id: str
    conversion_date_time: str  # "YYYY-MM-DD HH:MM:SS+TZ" — Google Ads format
    conversion_value: float
    currency_code: str
    gclid: str | None = None
    hashed_email: str | None = None
    order_id: str | None = None  # optional dedup key (Google Ads dedupes on this if present)

    def __post_init__(self) -> None:
        if not self.gclid and not self.hashed_email:
            raise ValueError(f"ClickConversion(action={self.conversion_action_id}) requires gclid or hashed_email")


@dataclass(frozen=True)
class ConversionFailure:
    """One operation in a partial-failure response.

    ``index`` matches the input list position. Index ``-1`` means the upstream
    response carried a failure with no recoverable index (location missing or
    out-of-range) — surfaced rather than silenced so callers see contract breaks.
    """

    index: int
    error_message: str


@dataclass(frozen=True)
class UploadResult:
    """Outcome of a single ``upload_click_conversions`` call.

    Tuple fields prevent the foot-gun where a frozen dataclass with mutable
    list fields appears immutable but isn't (caller doing ``result.successes
    .append(...)`` silently corrupts the result).
    """

    successes: tuple[int, ...]  # indices of accepted conversions
    failures: tuple[ConversionFailure, ...]  # indices + messages for rejected ones
