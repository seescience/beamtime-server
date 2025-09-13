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
from beamtime_server.services.doi import DOISchema, DOIService
from beamtime_server.utils import DOIConfig
from beamtime_server.utils.database import DatabaseManager
from beamtime_server.utils.logger import get_logger

__all__ = ["QueueProcessor"]


class QueueProcessor:
    """Queue processor with auto-initialization like DatabaseManager."""

    def __init__(self, db_manager: DatabaseManager, dry_run: bool = False):
        self._db_manager = db_manager
        self._logger = get_logger()
        self._doi_service = DOIService() if not dry_run else None
        self._dry_run = dry_run

        if dry_run:
            self._logger.info("QueueProcessor initialized in DRY-RUN mode (no DOI API calls)")
        else:
            self._logger.info("QueueProcessor initialized")

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
            create_doi = queue_item_data["create_doi"]

            self._logger.info(f"Processing queue item {queue_id}")

            # Create simple object for processing
            queue_data = type("QueueData", (), queue_item_data)()
            self._process_queue_item(queue_data)

            # Mark experiment as processed
            crud.update_experiment_status(self._db_manager, experiment_id, ProcessStatusEnum.PROCESSED)

            # Remove the queue item after successful processing
            crud.delete_queue_item(self._db_manager, queue_id)

            self._logger.info(f"Successfully processed queue item {queue_id}")
            return True

        except Exception as e:
            if "queue_id" in locals():
                # Mark experiment with error status and remove from queue
                crud.update_experiment_status(self._db_manager, experiment_id, ProcessStatusEnum.ERROR)
                crud.delete_queue_item(self._db_manager, queue_id)
                self._logger.error(f"Failed to process queue item {queue_id}: {e}")
            else:
                self._logger.error(f"Failed to get next queue item: {e}")
            return False

    def _process_queue_item(self, queue_item: QueueItem) -> None:
        """Process a single queue item."""
        self._logger.info(f"Processing queue item {queue_item.id} for experiment {queue_item.experiment_id}")

        # DOI Processing
        if queue_item.create_doi:
            self._process_doi(queue_item)

    def _process_doi(self, queue_item: QueueItem) -> None:
        """Process DOI creation for a queue item."""
        try:
            if self._dry_run:
                self._logger.info(f"[DRY-RUN] Simulating DOI creation for queue item {queue_item.id}")

                # Get metadata for DOI
                creators = crud.build_creators_from_spokesperson(self._db_manager, queue_item.experiment_id)
                pub_year = crud.get_publication_year_for_experiment(self._db_manager, queue_item.experiment_id)
                title = crud.get_experiment_title(self._db_manager, queue_item.experiment_id)

                # Generate DOI with correct format: {prefix}/data_{experiment_id}
                doi_config = DOIConfig()
                doi_id = f"{doi_config.prefix}/data_{queue_item.experiment_id}"

                self._logger.info(
                    f"[DRY-RUN] DOI metadata prepared - DOI: {doi_id}, Title: {title}, Year: {pub_year}, Creators: {len(creators) if creators else 0}"
                )
                self._logger.info(f"[DRY-RUN] DOI creation simulated successfully for queue item {queue_item.id}")
                return

            self._logger.info(f"Creating DOI for queue item {queue_item.id}")

            # Get metadata for DOI
            creators = crud.build_creators_from_spokesperson(self._db_manager, queue_item.experiment_id)
            pub_year = crud.get_publication_year_for_experiment(self._db_manager, queue_item.experiment_id)
            title = crud.get_experiment_title(self._db_manager, queue_item.experiment_id)

            # Generate DOI with correct format: {prefix}/data_{experiment_id}
            doi_config = DOIConfig()
            doi_id = f"{doi_config.prefix}/data_{queue_item.experiment_id}"

            # Build DOI metadata
            doi_metadata = DOISchema(
                creators=creators,
                titles=[{"title": f"{title}"}],
                publisher="The University of Chicago",
                publication_year=pub_year,
                types={"resourceType": "Dataset", "resourceTypeGeneral": "Dataset"},
                event="draft",
                doi=doi_id,
            )

            # Create the DOI
            result = self._doi_service.create_draft_doi(doi_metadata)
            doi_id = result.get("data", {}).get("id")

            if doi_id:
                self._logger.info(f"Successfully created DOI {doi_id} for queue item {queue_item.id}")
            else:
                raise Exception("DOI creation returned no ID")

        except Exception as e:
            self._logger.error(f"DOI processing failed for queue item {queue_item.id}: {e}")
            raise

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
