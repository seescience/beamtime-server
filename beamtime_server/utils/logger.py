# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/utils/logger.py
# ----------------------------------------------------------------------------------
# Purpose:
# Simple centralized logging with rotating compressed log files.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import gzip
import logging
import logging.handlers
import shutil
from pathlib import Path
from typing import Optional


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A rotating file handler that compresses rotated files."""

    def doRollover(self) -> None:
        """Override doRollover to compress the rotated file."""
        if self.stream:
            self.stream.close()
            self.stream = None

        if self.backupCount > 0:
            # Rotate existing backup files (move .1.gz -> .2.gz, .2.gz -> .3.gz, etc.)
            for backup_number in range(self.backupCount - 1, 0, -1):
                source_backup_file = Path(self.rotation_filename(f"{self.baseFilename}.{backup_number}.gz"))
                destination_backup_file = Path(self.rotation_filename(f"{self.baseFilename}.{backup_number + 1}.gz"))

                if source_backup_file.exists():
                    if destination_backup_file.exists():
                        destination_backup_file.unlink()
                    source_backup_file.rename(destination_backup_file)

            # Compress the current log file to .1.gz
            compressed_backup_file = Path(self.rotation_filename(f"{self.baseFilename}.1.gz"))
            if compressed_backup_file.exists():
                compressed_backup_file.unlink()

            # Compress the current log file
            current_log_file = Path(self.baseFilename)
            with current_log_file.open("rb") as file_input:
                with gzip.open(compressed_backup_file, "wb") as compressed_output:
                    shutil.copyfileobj(file_input, compressed_output)

            # Remove the original uncompressed file
            current_log_file.unlink()

        if not self.delay:
            self.stream = self._open()


class AppLogger:
    """Simple centralized logger for the beamtime server application."""

    _initialized: bool = False

    @classmethod
    def initialize(cls, log_directory: Optional[str | Path]) -> None:
        """Initialize the logging configuration."""

        if cls._initialized:
            return

        # Set defaults with proper type handling
        effective_log_level = "INFO"
        effective_log_directory = Path(log_directory)

        # Ensure log directory exists
        effective_log_directory.mkdir(parents=True, exist_ok=True)

        # Create log file path
        log_file_path = effective_log_directory / "beamtime_server.log"

        # Create detailed formatter for file logs
        detailed_formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # Create rotating file handler (10MB, keep 10 backups)
        rotating_file_handler = CompressedRotatingFileHandler(
            str(log_file_path),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
        )
        rotating_file_handler.setFormatter(detailed_formatter)
        rotating_file_handler.setLevel(effective_log_level)

        # Create root logger for the application
        cls._logger = logging.getLogger("beamtime_server")
        cls._logger.setLevel(effective_log_level)
        cls._logger.addHandler(rotating_file_handler)

        # Prevent duplicate logs
        cls._logger.propagate = False

        cls._initialized = True
        cls._logger.info(f"Logging initialized with level: {effective_log_level}")
        cls._logger.info(f"Log file: {log_file_path}")

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Return the application logger, initializing if necessary."""

        if not cls._initialized:
            cls.initialize()
        return cls._logger

    @classmethod
    def reset(cls) -> None:
        """Reset the logger (mainly for testing purposes)."""

        if cls._logger:
            # Remove all handlers and close them properly
            for handler in cls._logger.handlers[:]:
                cls._logger.removeHandler(handler)
                handler.close()
        cls._initialized = False
        cls._logger = None


def get_logger() -> logging.Logger:
    """Get the application logger."""
    return AppLogger.get_logger()


def initialize_logging(log_dir: Optional[str | Path] = "./logs") -> None:
    """Initialize the logging configuration."""
    AppLogger.initialize(log_directory=log_dir)
