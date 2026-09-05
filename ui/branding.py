"""Local brand assets for the authentication screens."""

import base64
from functools import lru_cache
from pathlib import Path


BRANDING_DIRECTORY = Path(__file__).resolve().parents[1] / "assets" / "branding"


@lru_cache(maxsize=2)
def _asset_data_uri(file_name: str, media_type: str) -> str:
    """Embed a bundled asset without a static server or external request."""
    encoded = base64.b64encode((BRANDING_DIRECTORY / file_name).read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def brand_wordmark_html() -> str:
    """Keep the brand name as accessible text beside a three-portion plate mark."""
    logo_uri = _asset_data_uri("macrosense-mark.svg", "image/svg+xml")
    return (
        '<div class="auth-brand">'
        f'<img src="{logo_uri}" alt="" width="32" height="32">'
        '<span>MacroSense</span></div>'
    )


def welcome_background_html() -> str:
    """Return optional, non-interactive decoration for the login page only."""
    try:
        image_uri = _asset_data_uri("welcome-fruit.png", "image/png")
    except FileNotFoundError:
        return ""
    return (
        f'<img class="auth-welcome-art" src="{image_uri}" '
        'alt="" aria-hidden="true" draggable="false">'
    )
