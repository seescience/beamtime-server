# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/processors/folder_processor.py
# ----------------------------------------------------------------------------------
# Purpose:
# Dedicated processor for handling all folder-related operations. It provides folder
# processing capabilities.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from pathlib import Path
from typing import Optional

from beamtime_server import crud
from beamtime_server.models import QueueItem
from beamtime_server.utils import DatabaseManager, get_logger

__all__ = ["FolderProcessor"]


class FolderPathBuilder:
    """Builder class for constructing standardized folder paths."""

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = Path(base_path) if base_path else None

    def build_experiment_folder_path(self, data_path: str, base_path: Optional[str] = None) -> Path:
        """Build the full experiment folder path."""
        resolved_base_path = Path(base_path) if base_path else self._base_path
        if resolved_base_path:
            return resolved_base_path / data_path
        return Path(data_path)

    def build_info_folder_path(self, experiment_folder: Path) -> Path:
        """Build the info subfolder path within an experiment folder."""
        return experiment_folder / "info"

    def build_pvlog_folder_path(self, experiment_folder: Path) -> Path:
        """Build the pvlog subfolder path within an experiment folder."""
        return experiment_folder / "pvlog"

    def build_acknowledgments_folder_path(self, experiment_folder: Path) -> Path:
        """Build the acknowledgments subfolder path within an experiment folder."""
        return self.build_info_folder_path(experiment_folder) / "acknowledgments"

    def build_doi_public_path(self, experiment_id: int, year: int, base_path: Optional[str] = None) -> Path:
        """Build the DOI public folder path."""
        resolved_base_path = Path(base_path) if base_path else self._base_path
        if resolved_base_path:
            return resolved_base_path / "public" / str(year) / str(experiment_id)
        return Path("public") / str(year) / str(experiment_id)

    def build_esaf_target_path(self, info_folder: Path, experiment_id: int) -> Path:
        """Build the target path for ESAF file copying."""
        return info_folder / f"ESAF-{experiment_id}.pdf"

    def ensure_standard_structure(self, experiment_folder: Path) -> dict:
        """Ensure standard folder structure exists and return paths."""
        info_path = self.build_info_folder_path(experiment_folder)
        pvlog_path = self.build_pvlog_folder_path(experiment_folder)

        return {
            "experiment": experiment_folder,
            "info": info_path,
            "pvlog": pvlog_path,
            "acknowledgments": self.build_acknowledgments_folder_path(experiment_folder),
        }

    @staticmethod
    def normalize_folder_name(name: str) -> str:
        """Normalize folder names to be filesystem-safe."""
        return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()


class FolderProcessor:
    """Processor for handling folder-related operations."""

    def __init__(self, db_manager: DatabaseManager, data_service):
        self._db_manager = db_manager
        self._data_service = data_service
        self._logger = get_logger()
        self._folder_builder = FolderPathBuilder()

    def process_folders(self, queue_item: QueueItem) -> bool:
        """Process folder creation for experiment data based on queue data_path."""
        try:
            # Only create folders if data_path is provided in the queue item
            if not queue_item.data_path:
                self._logger.info(f"No data path specified for experiment {queue_item.experiment_id}, skipping folder creation")
                return True  # Not an error condition

            # Get base path
            base_path = crud.get_info_value(self._db_manager, "base_path")

            # Create beamtime folder structure
            folder_path = self._create_beamtime_folders(queue_item, base_path)
            if not folder_path:
                return False

            # Copy ESAF file
            self._copy_esaf_file(queue_item, base_path, folder_path)

            return True

        except Exception as e:
            # Don't raise exception - folder creation failure shouldn't stop DOI processing
            self._logger.error(f"Folder processing failed for queue item {queue_item.id}: {e}")
            return False

    def _create_beamtime_folders(self, queue_item: QueueItem, base_path: str) -> Optional[str]:
        """Create beamtime folder structure and return path."""
        # Get acknowledgments if available
        acknowledgments = None
        if hasattr(queue_item, "acknowledgments") and queue_item.acknowledgments:
            acknowledgments = crud.get_acknowledgments_by_ids(self._db_manager, queue_item.acknowledgments)

        # Create folder structure using data service
        folder_path = self._data_service.create_folders_at_path(path=queue_item.data_path, user_base_path=base_path, acknowledgments=acknowledgments)

        # Update experiment database with the folder path
        success = crud.update_experiment(self._db_manager, queue_item.experiment_id, folder=str(folder_path))

        if not success:
            self._logger.error(f"Failed to update experiment {queue_item.experiment_id} with folder path")
            return None

        self._logger.info(f"Created folder structure and updated experiment {queue_item.experiment_id}")
        return str(folder_path)

    def _copy_esaf_file(self, queue_item: QueueItem, base_path: str, folder_path: str) -> None:
        """Copy ESAF file using the data service."""
        try:
            # Build info folder path - ensure folder_path is treated as relative
            folder_path_str = str(folder_path).lstrip("/")
            info_folder = Path(base_path) / folder_path_str / "info"
            esaf_path = self._data_service.copy_esaf_file(experiment_id=queue_item.experiment_id, info_folder=info_folder, user_base_path=base_path)

            if esaf_path:
                # Update experiment with ESAF beamtime path
                success = crud.update_experiment(self._db_manager, queue_item.experiment_id, esaf_pdf_file=esaf_path)

                if success:
                    self._logger.info(f"Updated experiment {queue_item.experiment_id} with ESAF path: {esaf_path}")
                else:
                    self._logger.warning(f"Failed to update experiment {queue_item.experiment_id} ESAF path")
            else:
                self._logger.info(f"No ESAF file found for experiment {queue_item.experiment_id}")

        except Exception as e:
            self._logger.warning(f"Failed to process ESAF file: {e}")
