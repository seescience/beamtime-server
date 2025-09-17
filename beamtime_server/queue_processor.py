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
from pathlib import Path

from beamtime_server import crud
from beamtime_server.models import ProcessStatusEnum, QueueItem
from beamtime_server.services import DataManagementService, DOISchema, DOIService
from beamtime_server.utils import DatabaseManager, DOIConfig, get_logger

__all__ = ["QueueProcessor"]


class QueueProcessor:
    """Queue processor with auto-initialization like DatabaseManager."""

    def __init__(self, db_manager: DatabaseManager, dry_run: bool = False):
        self._db_manager = db_manager
        self._logger = get_logger()
        self._doi_service = DOIService() if not dry_run else None
        self._data_service = DataManagementService(db_manager=db_manager)
        self._dry_run = dry_run

        if dry_run:
            self._logger.info("QueueProcessor initialized in DRY-RUN mode (no DOI API calls or folder creation)")
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

            # Determine final status based on old_process_status_id
            old_status = crud.get_experiment_old_process_status(self._db_manager, experiment_id)
            if old_status == ProcessStatusEnum.NEW:
                final_status = ProcessStatusEnum.PROCESSED
                status_name = "PROCESSED"
            else:
                final_status = ProcessStatusEnum.MODIFIED
                status_name = "MODIFIED"

            # Update experiment status
            crud.update_experiment_status(self._db_manager, experiment_id, final_status)
            self._logger.info(f"Set experiment {experiment_id} status to {status_name} (old_process_status_id was {old_status})")

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

        # Folder Processing
        self._process_folders(queue_item)

        # DOI Processing
        if queue_item.create_doi:
            self._process_doi(queue_item)

    def _process_folders(self, queue_item: QueueItem) -> None:
        """Process folder creation for experiment data based on queue data_path."""
        try:
            # Only create folders if data_path is provided in the queue item
            if not queue_item.data_path:
                self._logger.info(f"No data path specified for experiment {queue_item.experiment_id}, skipping folder creation")
                return

            if self._dry_run:
                self._logger.info(f"[DRY-RUN] Simulating folder creation for queue item {queue_item.id}")
                self._logger.info(f"[DRY-RUN] Would create experiment folder structure at: {queue_item.data_path}")
                self._logger.info("[DRY-RUN] Would create subfolders: info, pvlog")
                self._logger.info(f"[DRY-RUN] Would update experiment {queue_item.experiment_id} folder field with: {queue_item.data_path}")

                # Simulate final status determination
                try:
                    old_status = crud.get_experiment_old_process_status(self._db_manager, queue_item.experiment_id)
                    if old_status == ProcessStatusEnum.NEW:
                        final_status_name = "PROCESSED"
                    else:
                        final_status_name = "MODIFIED"
                    self._logger.info(
                        f"[DRY-RUN] Would set experiment {queue_item.experiment_id} status to {final_status_name} (old_process_status_id is {old_status})"
                    )
                except Exception as e:
                    self._logger.warning(f"[DRY-RUN] Failed to get old process status: {e}")

                # Check for acknowledgments in dry-run mode
                if hasattr(queue_item, "acknowledgments") and queue_item.acknowledgments:
                    try:
                        acknowledgments = crud.get_acknowledgments_by_ids(self._db_manager, queue_item.acknowledgments)
                        if acknowledgments:
                            self._logger.info(f"[DRY-RUN] Would create acknowledgments subfolder with {len(acknowledgments)} files")
                            for ack in acknowledgments:
                                title = ack.get("title", f"Acknowledgment_{ack['id']}")
                                safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).rstrip()
                                self._logger.info(f"[DRY-RUN]   - {safe_title}.txt")
                    except Exception as e:
                        self._logger.warning(f"[DRY-RUN] Failed to retrieve acknowledgments: {e}")

                # Simulate ESAF file copying
                self._logger.info(f"[DRY-RUN] Would search for ESAF file for experiment {queue_item.experiment_id}")
                try:
                    esaf_folder = crud.get_esaf_pdf_folder(self._db_manager)
                    run_name = crud.get_experiment_run_name(self._db_manager, queue_item.experiment_id)
                    if esaf_folder and run_name:
                        search_path = f"{esaf_folder}/{run_name}"
                        pattern = f"ESAF-{queue_item.experiment_id}*.pdf"
                        self._logger.info(f"[DRY-RUN] Would search for {pattern} in {search_path}")
                        # Simulate the beamtime folder path where ESAF would be copied
                        from beamtime_server.utils.config import BeamtimeConfig

                        beamtime_config = BeamtimeConfig()
                        if beamtime_config.beamtime_folder:
                            simulated_beamtime_path = f"{beamtime_config.esaf_folder}/{run_name}/ESAF-{queue_item.experiment_id}.pdf"
                            self._logger.info(f"[DRY-RUN] Would copy ESAF to beamtime folder: {simulated_beamtime_path}")
                            self._logger.info(
                                f"[DRY-RUN] Would update experiment {queue_item.experiment_id} esaf_pdf_file field with: {simulated_beamtime_path}"
                            )
                    else:
                        self._logger.warning(f"[DRY-RUN] Missing ESAF folder or run name for experiment {queue_item.experiment_id}")
                except Exception as e:
                    self._logger.warning(f"[DRY-RUN] Failed to get ESAF info: {e}")

                return

            self._logger.info(f"Creating folder structure for experiment {queue_item.experiment_id} at: {queue_item.data_path}")

            try:
                # Get acknowledgments if any are specified
                acknowledgments = []
                if hasattr(queue_item, "acknowledgments") and queue_item.acknowledgments:
                    acknowledgments = crud.get_acknowledgments_by_ids(self._db_manager, queue_item.acknowledgments)
                    self._logger.info(f"Retrieved {len(acknowledgments)} acknowledgments for experiment {queue_item.experiment_id}")

                # Prepend base path to data_path if available
                data_path = queue_item.data_path
                base_path = crud.get_base_path(self._db_manager)

                # Use the data service to create folders
                folder_path = self._data_service.create_folders_at_path(data_path, base_path, acknowledgments, queue_item.experiment_id)
                self._logger.info(f"Successfully created folder structure at: {folder_path}")

                # Update experiment database with the folder path
                try:
                    crud.update_experiment_folder(self._db_manager, queue_item.experiment_id, str(folder_path))
                    self._logger.info(f"Updated experiment {queue_item.experiment_id} with folder path: {folder_path}")
                except Exception as db_error:
                    # Don't fail the entire process if database update fails
                    self._logger.warning(f"Failed to update experiment folder path in database: {db_error}")

                # Copy ESAF file and save beamtime path to database
                try:
                    info_folder = Path(base_path) / folder_path / "info"
                    esaf_beamtime_path = self._data_service.copy_esaf_file(queue_item.experiment_id, info_folder, base_path)
                    if esaf_beamtime_path:
                        crud.update_experiment_esaf_file(self._db_manager, queue_item.experiment_id, esaf_beamtime_path)
                        self._logger.info(f"Updated experiment {queue_item.experiment_id} with ESAF beamtime path: {esaf_beamtime_path}")
                    else:
                        self._logger.info(f"No ESAF file copied to beamtime folder for experiment {queue_item.experiment_id}")
                except Exception as esaf_error:
                    # Don't fail the entire process if ESAF update fails
                    self._logger.warning(f"Failed to update experiment ESAF file path in database: {esaf_error}")

            except Exception as folder_error:
                # Don't fail the entire process if folder creation fails
                self._logger.warning(f"Failed to create folders using DataManagementService: {folder_error}")

        except Exception as e:
            # Don't raise exception - folder creation failure shouldn't stop DOI processing
            self._logger.error(f"Folder processing failed for queue item {queue_item.id}: {e}")

    def _process_doi(self, queue_item: QueueItem) -> None:
        """Process DOI creation for a queue item."""
        try:
            if self._dry_run:
                self._logger.info(f"[DRY-RUN] Simulating DOI creation/update for queue item {queue_item.id}")

                # Get metadata for DOI
                creators = crud.build_creators_from_spokesperson(self._db_manager, queue_item.experiment_id)
                pub_year = crud.get_publication_year_for_experiment(self._db_manager, queue_item.experiment_id)
                title = crud.get_experiment_title(self._db_manager, queue_item.experiment_id)

                # Generate DOI with correct format: {prefix}/data_{experiment_id}
                doi_config = DOIConfig()
                doi_id = f"{doi_config.prefix}/data_{queue_item.experiment_id}"
                doi_link = f"https://doi.org/{doi_id}"
                public_data_url = f"https://public.seescience.org/data/{pub_year}/{queue_item.experiment_id}"

                # Determine DOI type based on draft_doi flag
                draft_mode = hasattr(queue_item, "draft_doi") and queue_item.draft_doi
                doi_type = "draft" if draft_mode else "findable (published)"

                self._logger.info(
                    f"[DRY-RUN] DOI metadata prepared - DOI: {doi_id}, Title: {title}, Year: {pub_year}, Creators: {len(creators) if creators else 0}"
                )
                self._logger.info(f"[DRY-RUN] DOI would be created/updated as: {doi_type}")
                self._logger.info("[DRY-RUN] DOI includes CC-BY-4.0 license: https://creativecommons.org/licenses/by/4.0/legalcode")
                self._logger.info(f"[DRY-RUN] DOI points to public data URL: {public_data_url}")
                self._logger.info(f"[DRY-RUN] Would update experiment {queue_item.experiment_id} with DOI link: {doi_link}")

                # Simulate DOI public folder creation
                public_folder_path = self._data_service.get_doi_public_path(queue_item.experiment_id, pub_year, crud.get_base_path(self._db_manager))
                self._logger.info(f"[DRY-RUN] Would create DOI public folder: {public_folder_path}")
                return

            self._logger.info(f"Creating or updating DOI for queue item {queue_item.id}")

            # Get metadata for DOI
            creators = crud.build_creators_from_spokesperson(self._db_manager, queue_item.experiment_id)
            pub_year = crud.get_publication_year_for_experiment(self._db_manager, queue_item.experiment_id)
            title = crud.get_experiment_title(self._db_manager, queue_item.experiment_id)
            start_date = crud.get_experiment_start_date(self._db_manager, queue_item.experiment_id)

            # Generate DOI with correct format: {prefix}/data_{experiment_id}
            doi_config = DOIConfig()
            doi_id = f"{doi_config.prefix}/data_{queue_item.experiment_id}"

            # Build public data URL
            public_data_url = f"https://public.seescience.org/data/{pub_year}/{queue_item.experiment_id}"

            # Determine event type based on draft_doi flag
            event_type = "draft" if hasattr(queue_item, "draft_doi") and queue_item.draft_doi else "publish"

            # Build DOI metadata
            doi_metadata = DOISchema(
                creators=creators,
                titles=[{"title": f"{title}"}],
                publisher="University of Chicago",
                publication_year=pub_year,
                types={"resourceType": "Dataset", "resourceTypeGeneral": "Dataset"},
                language="en",
                version="0.1",
                dates=[{"date": start_date, "dateType": "Issued"}],
                rights_list=[
                    {
                        "rights": "Creative Commons Attribution 4.0 International",
                        "rightsUri": "https://creativecommons.org/licenses/by/4.0/legalcode",
                        "rightsIdentifier": "CC-BY-4.0",
                        "rightsIdentifierScheme": "SPDX",
                        "schemeUri": "https://spdx.org/licenses/",
                    }
                ],
                url=public_data_url,
                event=event_type,
                doi=doi_id,
            )

            # Create or update the DOI (handles existing DOIs automatically)
            result = self._doi_service.create_or_update_doi(doi_metadata)
            doi_id = result.get("data", {}).get("id")

            if doi_id:
                # Update experiment with DOI link
                doi_link = f"https://doi.org/{doi_id}"
                crud.update_experiment_doi_link(self._db_manager, queue_item.experiment_id, doi_link)

                # Create DOI public folder (only creates if it doesn't exist)
                try:
                    public_folder_path = self._data_service.create_doi_public_folder(queue_item.experiment_id, pub_year, crud.get_base_path(self._db_manager))
                    self._logger.info(f"Created DOI public folder: {public_folder_path}")

                    # Create index.html file with DOI information
                    try:
                        creators_str = ", ".join([creator.get("name", "Unknown") for creator in creators]) if creators else None
                        self._data_service.create_doi_index_file(
                            experiment_id=queue_item.experiment_id,
                            year=pub_year,
                            doi_id=doi_id,
                            title=title,
                            user_base_path=crud.get_base_path(self._db_manager),
                            creators=creators_str,
                            version="0.1",
                        )
                    except Exception as html_error:
                        self._logger.warning(f"Failed to create index.html: {html_error}")
                        # Don't fail the entire process if HTML creation fails

                except Exception as folder_error:
                    self._logger.warning(f"Failed to create DOI public folder: {folder_error}")
                    # Don't fail the entire process if folder creation fails

                # Log based on whether it was created as draft or published
                doi_status = "draft DOI" if event_type == "draft" else "findable DOI"
                self._logger.info(f"Successfully processed {doi_status} {doi_id} pointing to {public_data_url}")
                self._logger.info(f"Updated experiment {queue_item.experiment_id} with DOI link: {doi_link}")
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

    def publish_draft_doi(self, doi_id: str) -> bool:
        """Publish an existing draft DOI to make it findable."""
        if self._dry_run:
            self._logger.info(f"[DRY-RUN] Would publish draft DOI to make it findable: {doi_id}")
            return True

        try:
            if not self._doi_service:
                self._logger.error("DOI service not available (dry-run mode or initialization error)")
                return False

            result = self._doi_service.publish_doi(doi_id)
            if result:
                self._logger.info(f"Successfully published DOI {doi_id} - now findable")
                return True
            else:
                self._logger.error(f"Failed to publish DOI {doi_id}")
                return False

        except Exception as e:
            self._logger.error(f"Error publishing DOI {doi_id}: {e}")
            return False
