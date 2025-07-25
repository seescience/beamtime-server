# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: experiment_folder.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module provides a class for creating experiment folders.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------


import os
from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path


class ExperimentFolderError(Exception):
    """Exception raised for experiment folder operations."""

    def __init__(self, message: str, operation: str, original_error: Exception = None):
        self.message = message
        self.operation = operation
        self.original_error = original_error
        super().__init__(self.message)


@dataclass
class ExperimentFolderCreator:
    """A class for creating experiment folders with standardized structure."""

    base_path: Path | str
    experiment_name: str
    logger: Logger

    _experiment_path: Path = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization to set the experiment path and validate the experiment name."""
        self.base_path = Path(self.base_path).resolve()
        self.experiment_name = self.experiment_name.strip()
        self._experiment_path = self.base_path / self.experiment_name

        if not self._validate_experiment_name():
            raise ValueError(f"Invalid experiment name: {self.experiment_name}")

    def _validate_experiment_name(self) -> bool:
        """Validate that the experiment name is suitable for filesystem use."""
        # Check for invalid characters
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "/", "\\"]

        # Windows additional restrictions
        if os.name == "nt":
            invalid_chars.extend(["/", "\\"])
            # Reserved names in Windows
            reserved_names = ["CON", "PRN", "AUX", "NUL"] + [f"COM{i}" for i in range(1, 10)] + [f"LPT{i}" for i in range(1, 10)]
            if self.experiment_name.upper() in reserved_names:
                return False

        # Check for invalid characters
        if any(char in self.experiment_name for char in invalid_chars):
            return False

        # Check for empty name or just whitespace
        if not self.experiment_name.strip():
            return False

        # Check length (255 is typical filesystem limit)
        if len(self.experiment_name) > 255:
            return False

        return True

    def _exists(self) -> bool:
        """Check if the experiment folder already exists."""
        return self._experiment_path.exists() and self._experiment_path.is_dir()

    def create_experiment_folder(self) -> None:
        """Create the experiment folder."""
        try:
            # Ensure the experiment folder does not already exist before creating it
            if not self._exists():
                self._experiment_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created experiment folder: {self._experiment_path}")

        except (PermissionError, OSError) as e:
            message = f"Failed to create experiment folder: {e}"
            self.logger.error(message)
            raise ExperimentFolderError(message, operation="create_experiment_folder", original_error=e)

    def create_subfolders(self) -> None:
        """Create additional subfolders within the experiment folder."""
        # Ensure the experiment folder exists before creating subfolders
        if not self._exists():
            raise RuntimeError(f"Experiment folder does not exist: {self._experiment_path}")

        try:
            # Create info folder
            info_path = self._experiment_path / "info"
            info_path.mkdir(parents=True, exist_ok=True)

            # Create pvlogs folder
            pvlogs_path = self._experiment_path / "pvlogs"
            pvlogs_path.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Created subfolders in: {self._experiment_path}")

        except (PermissionError, OSError) as e:
            message = f"Failed to create subfolders: {e}"
            self.logger.error(message)
            raise ExperimentFolderError(message, operation="create_subfolders", original_error=e)
