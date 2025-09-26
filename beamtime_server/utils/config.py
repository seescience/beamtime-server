# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/utils/config.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module defines configuration classes for the Beamtime Server application.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BaseConfig:
    """Simple application configuration class - only essential variables."""

    # Database configuration
    DATABASE_URI = os.getenv("DATABASE_URI")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE"))
    DB_ECHO = os.getenv("DB_ECHO").lower() == "true"

    # DOI service configuration
    DOI_BASE_URL = os.getenv("DOI_BASE_URL")
    DOI_USERNAME = os.getenv("DOI_USERNAME")
    DOI_PASSWORD = os.getenv("DOI_PASSWORD")
    DOI_PREFIX = os.getenv("DOI_PREFIX")
    DOI_BASE_PATH = os.getenv("DOI_BASE_PATH")

    # Logging configuration
    LOG_FILE = os.getenv("LOG_FILE")

    # Beamtime folder configuration
    BEAMTIME_FOLDER = os.getenv("BEAMTIME_FOLDER")


@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration."""

    _database_uri: str = field(init=False, compare=False, repr=False, default=BaseConfig.DATABASE_URI)
    _pool_size: int = field(init=False, compare=False, repr=False, default=BaseConfig.DB_POOL_SIZE)
    _max_overflow: int = field(init=False, compare=False, repr=False, default=BaseConfig.DB_MAX_OVERFLOW)
    _pool_timeout: int = field(init=False, compare=False, repr=False, default=BaseConfig.DB_POOL_TIMEOUT)
    _pool_recycle: int = field(init=False, compare=False, repr=False, default=BaseConfig.DB_POOL_RECYCLE)
    _echo: bool = field(init=False, compare=False, repr=False, default=BaseConfig.DB_ECHO)

    @property
    def database_uri(self) -> str:
        """Get the database URI."""
        return self._database_uri

    @property
    def pool_size(self) -> int:
        """Get the database pool size."""
        return self._pool_size

    @property
    def max_overflow(self) -> int:
        """Get the database max overflow."""
        return self._max_overflow

    @property
    def pool_timeout(self) -> int:
        """Get the database pool timeout."""
        return self._pool_timeout

    @property
    def pool_recycle(self) -> int:
        """Get the database pool recycle time."""
        return self._pool_recycle

    @property
    def echo(self) -> bool:
        """Get the database echo setting."""
        return self._echo


@dataclass(frozen=True)
class DOIConfig:
    """DOI service configuration."""

    _base_url: str = field(init=False, compare=False, repr=False, default=BaseConfig.DOI_BASE_URL)
    _username: str = field(init=False, compare=False, repr=False, default=BaseConfig.DOI_USERNAME)
    _password: str = field(init=False, compare=False, repr=False, default=BaseConfig.DOI_PASSWORD)
    _prefix: str = field(init=False, compare=False, repr=False, default=BaseConfig.DOI_PREFIX)
    _doi_base_path: str = field(init=False, compare=False, repr=False, default=BaseConfig.DOI_BASE_PATH)

    @property
    def base_url(self) -> str:
        """Get the DOI service base URL."""
        return self._base_url

    @property
    def username(self) -> str:
        """Get the DOI service username."""
        return self._username

    @property
    def password(self) -> str:
        """Get the DOI service password."""
        return self._password

    @property
    def prefix(self) -> str:
        """Get the DOI prefix."""
        return self._prefix

    @property
    def doi_base_path(self) -> str:
        """Get the DOI base path."""
        return self._doi_base_path


@dataclass(frozen=True)
class BeamtimeConfig:
    """Beamtime folder configuration."""

    _beamtime_folder: str = field(init=False, compare=False, repr=False, default=BaseConfig.BEAMTIME_FOLDER)

    @property
    def beamtime_folder(self) -> str:
        """Get the beamtime folder path."""
        return self._beamtime_folder

    @property
    def esaf_folder(self) -> str:
        """Get the ESAF folder path (beamtime_folder/esaf)."""
        from pathlib import Path

        return str(Path(self._beamtime_folder) / "esaf")


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    _log_file: str = field(init=False, compare=False, repr=False, default=BaseConfig.LOG_FILE)

    @property
    def log_file(self) -> str:
        """Get the log file path."""
        return self._log_file
