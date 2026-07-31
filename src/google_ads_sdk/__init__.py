"""Volkanos wrapper around google-ads. Currently exposes click-conversion uploads."""

from google_ads_sdk.conversions import ConversionsClient
from google_ads_sdk.exceptions import GoogleAdsAuthError, GoogleAdsSDKError, GoogleAdsUploadError
from google_ads_sdk.types import ClickConversion, ConversionFailure, UploadResult

__all__ = [
    "ConversionsClient",
    "ClickConversion",
    "UploadResult",
    "ConversionFailure",
    "GoogleAdsSDKError",
    "GoogleAdsAuthError",
    "GoogleAdsUploadError",
]

__version__ = "1.0.1"
