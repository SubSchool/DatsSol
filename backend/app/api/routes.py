from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.game import (
    LogsEnvelope,
    ManualDirective,
    ManualDirectiveCreate,
    ProviderSelectionRequest,
    RoundArchivesEnvelope,
    RuntimeSnapshot,
    ServerLogsEnvelope,
    StrategySelectionRequest,
    SubmitModeRequest,
    TeamStatsEnvelope,
    WeightsUpdateRequest,
    WorldSnapshot,
)
from app.services.runtime import runtime_service
from app.services.stats_tracker import stats_tracker_service

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/runtime", response_model=RuntimeSnapshot)
def get_runtime() -> RuntimeSnapshot:
    return runtime_service.snapshot()


@router.post("/runtime/start", response_model=RuntimeSnapshot)
async def start_runtime() -> RuntimeSnapshot:
    return await runtime_service.start()


@router.post("/runtime/stop", response_model=RuntimeSnapshot)
async def stop_runtime() -> RuntimeSnapshot:
    return await runtime_service.stop()


@router.post("/runtime/restart", response_model=RuntimeSnapshot)
async def restart_runtime() -> RuntimeSnapshot:
    return await runtime_service.restart()


@router.post("/runtime/tick", response_model=RuntimeSnapshot)
async def tick_runtime() -> RuntimeSnapshot:
    return await runtime_service.tick_once()


@router.post("/runtime/strategy", response_model=RuntimeSnapshot)
async def set_strategy(payload: StrategySelectionRequest) -> RuntimeSnapshot:
    return await runtime_service.set_strategy(payload)


@router.post("/runtime/weights", response_model=RuntimeSnapshot)
async def update_weights(payload: WeightsUpdateRequest) -> RuntimeSnapshot:
    return await runtime_service.update_weights(payload)


@router.post("/runtime/provider", response_model=RuntimeSnapshot)
async def set_provider(payload: ProviderSelectionRequest) -> RuntimeSnapshot:
    return await runtime_service.set_provider(payload)


@router.post("/runtime/submit-mode", response_model=RuntimeSnapshot)
async def set_submit_mode(payload: SubmitModeRequest) -> RuntimeSnapshot:
    return await runtime_service.set_submit_mode(payload)


@router.get("/world", response_model=WorldSnapshot)
def get_world() -> WorldSnapshot:
    return runtime_service.world()


@router.post("/world/directives", response_model=ManualDirective)
async def create_directive(payload: ManualDirectiveCreate) -> ManualDirective:
    return await runtime_service.enqueue_directive(payload)


@router.get("/server-logs", response_model=ServerLogsEnvelope)
def get_server_logs() -> ServerLogsEnvelope:
    return runtime_service.server_logs()


@router.get("/stats/team", response_model=TeamStatsEnvelope)
def get_team_stats(
    team_name: Optional[str] = Query(default=None),
    history_limit: int = Query(default=20, ge=1, le=200),
    rounds_limit: int = Query(default=20, ge=1, le=200),
) -> TeamStatsEnvelope:
    return stats_tracker_service.snapshot(team_name=team_name, history_limit=history_limit, rounds_limit=rounds_limit)


@router.post("/stats/refresh", response_model=TeamStatsEnvelope)
async def refresh_team_stats(
    team_name: Optional[str] = Query(default=None),
    history_limit: int = Query(default=20, ge=1, le=200),
    rounds_limit: int = Query(default=20, ge=1, le=200),
) -> TeamStatsEnvelope:
    await stats_tracker_service.refresh_once()
    return stats_tracker_service.snapshot(team_name=team_name, history_limit=history_limit, rounds_limit=rounds_limit)


@router.get("/round-archives", response_model=RoundArchivesEnvelope)
def get_round_archives(
    session: Session = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> RoundArchivesEnvelope:
    return runtime_service.list_round_archives(session=session, limit=limit, offset=offset)


@router.get("/logs", response_model=LogsEnvelope)
def get_logs(
    session: Session = Depends(get_session),
    level: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    tick_from: Optional[int] = Query(default=None),
    tick_to: Optional[int] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> LogsEnvelope:
    return runtime_service.list_logs(
        session=session,
        level=level,
        category=category,
        source=source,
        search=search,
        tick_from=tick_from,
        tick_to=tick_to,
        limit=limit,
        offset=offset,
    )


@router.get("/logs/export")
def export_logs(
    session: Session = Depends(get_session),
    level: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    tick_from: Optional[int] = Query(default=None),
    tick_to: Optional[int] = Query(default=None),
) -> StreamingResponse:
    content = runtime_service.export_logs_csv(
        session=session,
        level=level,
        category=category,
        source=source,
        search=search,
        tick_from=tick_from,
        tick_to=tick_to,
    )
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="dats-sol-logs.csv"'},
    )
