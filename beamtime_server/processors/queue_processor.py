# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/queue_processor.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module processes queue items for the Beamtime Server.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import time

from beamtime_server import crud
from beamtime_server.models import ProcessStatusEnum, QueueItem
from beamtime_server.processors import DOIProcessor, FolderProcessor
from beamtime_server.services import DataManagementService, DOIService
from beamtime_server.utils import DatabaseManager, get_logger

__all__ = ["QueueProcessor"]


class QueueProcessor:
    """Queue processor with auto-initialization like DatabaseManager."""

    def __init__(self, db_manager: DatabaseManager, dry_run: bool = False):
        self._db_manager = db_manager
        self._logger = get_logger()
        doi_service = DOIService(dry_run=dry_run)
        data_service = DataManagementService(db_manager=db_manager, dry_run=dry_run)
        self._doi_processor = DOIProcessor(db_manager=db_manager, data_service=data_service, doi_service=doi_service)
        self._folder_processor = FolderProcessor(db_manager=db_manager, data_service=data_service)

    def _process_queue_item(self, queue_item: QueueItem) -> None:
        """Process a single queue item."""
        self._logger.info(f"Processing queue item {queue_item.id} for experiment {queue_item.experiment_id}")

        # Folder Processing
        self._folder_processor.process_folders(queue_item)

        # DOI Processing
        if queue_item.create_doi:
            self._doi_processor.process_doi(queue_item)

    def process_next(self) -> bool:
        """Process the next queue item."""
        try:
            # Get next queue item (now returns dict)
            queue_item_data = crud.get_next_queue_item(self._db_manager)
            if not queue_item_data:
                return False

            # Extract data from dict
            queue_id = queue_item_data["id"]
            experiment_id = queue_item_data["experiment_id"]

            self._logger.info(f"Processing queue item {queue_id}")

            # Create simple object for processing
            queue_data = type("QueueData", (), queue_item_data)()
            self._process_queue_item(queue_data)

            # Determine final status based on old_process_status_id
            old_status = crud.get_experiment_old_process_status(self._db_manager, experiment_id)
            if old_status == ProcessStatusEnum.NEW:
                final_status = ProcessStatusEnum.PROCESSED
                status_name = "PROCESSED"
            else:
                final_status = ProcessStatusEnum.MODIFIED
                status_name = "MODIFIED"

            # Update experiment status
            crud.update_experiment(self._db_manager, experiment_id, process_status_id=final_status.value)
            self._logger.info(f"Set experiment {experiment_id} status to {status_name} (old_process_status_id was {old_status})")

            # Remove the queue item after successful processing
            crud.delete_queue_item(self._db_manager, queue_id)

            self._logger.info(f"Successfully processed queue item {queue_id}")
            return True

        except Exception as e:
            if "queue_id" in locals():
                # Mark experiment with error status and remove from queue
                crud.update_experiment(self._db_manager, experiment_id, process_status_id=ProcessStatusEnum.ERROR.value)
                crud.delete_queue_item(self._db_manager, queue_id)
                self._logger.error(f"Failed to process queue item {queue_id}: {e}")
            else:
                self._logger.error(f"Failed to get next queue item: {e}")
            return False

    def run_continuous(self, poll_interval: int) -> None:
        """Run continuous queue processing."""
        self._logger.info("Starting continuous queue processing")

        try:
            while True:
                processed = self.process_next()

                if not processed:
                    # No items to process, wait before checking again
                    time.sleep(poll_interval)

        except KeyboardInterrupt:
            self._logger.info("Queue processing stopped by user")
        except Exception as e:
            self._logger.error(f"Queue processing crashed: {e}")
            raise

    def process_all_pending(self) -> int:
        """Process all pending items (useful for batch processing)."""
        processed_count = 0

        while True:
            if not self.process_next():
                break
            processed_count += 1

        self._logger.info(f"Batch processing completed: {processed_count} items processed")
        return processed_count
