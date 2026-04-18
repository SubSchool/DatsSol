from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.game import ArenaObservation, GameServerLogEntry, PlayerCommandPayload, ProviderStatus, SubmitResultView


class ArenaProvider(ABC):
    key: str
    label: str

    @abstractmethod
    async def observe(self) -> ArenaObservation:
        raise NotImplementedError

    @abstractmethod
    async def submit(self, payload: PlayerCommandPayload, submit_mode: str) -> SubmitResultView:
        raise NotImplementedError

    @abstractmethod
    async def fetch_server_logs(self) -> list[GameServerLogEntry]:
        raise NotImplementedError

    @abstractmethod
    async def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> ProviderStatus:
        raise NotImplementedError

    async def close(self) -> None:
        return None
