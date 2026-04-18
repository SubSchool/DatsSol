from __future__ import annotations

from app.providers.base import ArenaProvider
from app.providers.datsol_live import DatsSolLiveProvider
from app.providers.datsol_mock import DatsSolMockProvider


def build_provider(provider_key: str) -> ArenaProvider:
    if provider_key == "datssol-live":
        return DatsSolLiveProvider()
    return DatsSolMockProvider()
