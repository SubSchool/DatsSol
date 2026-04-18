from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TickSnapshot(Base):
    __tablename__ = "tick_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tick_number: Mapped[int] = mapped_column(Integer, index=True)
    provider_key: Mapped[str] = mapped_column(String(64), index=True)
    strategy_key: Mapped[str] = mapped_column(String(64), index=True)
    phase: Mapped[str] = mapped_column(String(64), default="simulation")
    world_state: Mapped[dict] = mapped_column(JSON, default=dict)
    command_batch: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LogEvent(Base):
    __tablename__ = "log_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tick_number: Mapped[int] = mapped_column(Integer, index=True, default=0)
    level: Mapped[str] = mapped_column(String(24), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ManualDirectiveRecord(Base):
    __tablename__ = "manual_directives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    directive_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tick_number: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="active")
    note: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TeamStatsSnapshot(Base):
    __tablename__ = "team_stats_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_name: Mapped[str] = mapped_column(String(128), index=True)
    rank: Mapped[int] = mapped_column(Integer, index=True, default=0)
    total_players: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)
    ended_at: Mapped[str] = mapped_column(String(64), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class TeamRoundResult(Base):
    __tablename__ = "team_round_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_name: Mapped[str] = mapped_column(String(128), index=True)
    realm_name: Mapped[str] = mapped_column(String(128), index=True)
    realm_started_at: Mapped[str] = mapped_column(String(64), default="")
    realm_ended_at: Mapped[str] = mapped_column(String(64), default="")
    rank: Mapped[int] = mapped_column(Integer, index=True, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RoundArchive(Base):
    __tablename__ = "round_archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_key: Mapped[str] = mapped_column(String(64), index=True)
    strategy_key: Mapped[str] = mapped_column(String(64), index=True)
    build_id: Mapped[str] = mapped_column(String(128), index=True, default="")
    runtime_session_id: Mapped[str] = mapped_column(String(128), index=True, default="")
    round_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    round_ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    first_turn: Mapped[int] = mapped_column(Integer, default=0)
    last_turn: Mapped[int] = mapped_column(Integer, default=0)
    observed_turns: Mapped[int] = mapped_column(Integer, default=0)
    processed_turns: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
