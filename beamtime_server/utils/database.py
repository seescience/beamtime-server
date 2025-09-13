# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/utils/database.py
# ----------------------------------------------------------------------------------
# Purpose:
# PostgreSQL database connection and session management using proper DatabaseManager.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from contextlib import contextmanager
from dataclasses import dataclass, field
from logging import Logger
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from beamtime_server.utils.logger import get_logger
from beamtime_server.utils.config import DatabaseConfig

__all__ = ["DatabaseManager", "DBException"]


@dataclass
class DatabaseManager:
    """PostgreSQL database connection and session management."""

    _config: DatabaseConfig = field(init=False, compare=False, repr=False, default=DatabaseConfig())
    _logger: Logger = field(init=False, compare=False, repr=False, default=get_logger())
    _engine: Engine | None = field(init=False, compare=False, repr=False, default=None)
    _session_factory: sessionmaker | None = field(init=False, compare=False, repr=False, default=None)

    def _get_engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _get_session(self) -> Session:
        """Get or create session factory and return a new session."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self._get_engine())
        return self._session_factory()

    def _create_engine(self) -> Engine:
        """Create PostgreSQL database engine with connection pooling."""
        database_url = self._config.database_uri
        self._logger.info(f"Creating database engine with pool_size={self._config.pool_size}")

        engine_kwargs = {
            "echo": self._config.echo,
            "poolclass": QueuePool,
            "pool_size": self._config.pool_size,
            "max_overflow": self._config.max_overflow,
            "pool_timeout": self._config.pool_timeout,
            "pool_recycle": self._config.pool_recycle,
        }

        engine = create_engine(database_url, **engine_kwargs)
        self._logger.info("Database engine created successfully")
        return engine

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self._get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            self._logger.error(f"Database session error, rolling back: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close database engine and connections."""
        if self._engine:
            self._logger.info("Disposing database engine and closing connections")
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


class DBException(Exception):
    """Database exception class."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message
