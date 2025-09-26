# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/utils/logger.py
# ----------------------------------------------------------------------------------
# Purpose:
# Centralized logging with rotating compressed log files.
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

from beamtime_server.utils.config import LoggingConfig


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
    """Centralized logger."""

    _instance: Optional["AppLogger"] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> "AppLogger":
        """Singleton pattern - ensure only one logger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the logging configuration."""
        if self._logger is not None:
            return

        # Use LoggingConfig to get log path, with fallback to default
        try:
            logging_config = LoggingConfig()
            if logging_config.log_file:
                log_file_path = Path(logging_config.log_file)
                log_directory = log_file_path.parent
                # Use the full log file path from config
                full_log_path = log_file_path
            else:
                log_directory = Path("./logs")
                full_log_path = log_directory / "beamtime_server.log"
        except Exception:
            log_directory = Path("./logs")
            full_log_path = log_directory / "beamtime_server.log"

        # Ensure log directory exists
        log_directory.mkdir(parents=True, exist_ok=True)

        # Set defaults
        effective_log_level = "INFO"

        # Create detailed formatter for file logs
        detailed_formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # Create rotating file handler (10MB, keep 10 backups)
        rotating_file_handler = CompressedRotatingFileHandler(
            str(full_log_path),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
        )
        rotating_file_handler.setFormatter(detailed_formatter)
        rotating_file_handler.setLevel(effective_log_level)

        # Create root logger for the application
        self._logger = logging.getLogger("beamtime_server")
        self._logger.setLevel(effective_log_level)
        self._logger.addHandler(rotating_file_handler)

        # Prevent duplicate logs
        self._logger.propagate = False

        self._logger.info(f"Logging initialized with level: {effective_log_level}")
        self._logger.info(f"Log file: {full_log_path}")

    def get_logger(self) -> logging.Logger:
        """Return the application logger."""
        return self._logger

    @classmethod
    def reset(cls) -> None:
        """Reset the logger (mainly for testing purposes)."""
        if cls._instance and cls._instance._logger:
            # Remove all handlers and close them properly
            for handler in cls._instance._logger.handlers[:]:
                cls._instance._logger.removeHandler(handler)
                handler.close()
        cls._instance = None


def get_logger() -> logging.Logger:
    """Get the application logger."""
    app_logger = AppLogger()
    return app_logger.get_logger()
