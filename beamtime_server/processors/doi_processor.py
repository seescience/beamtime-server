# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/processors/doi_processor.py
# ----------------------------------------------------------------------------------
# Purpose:
# This file contains the DOIProcessor class, responsible for handling DOI-related
# operations. It works closely with the data service and DOI service to create,
# update, and publish DOIs for experiments. The processor builds DOI metadata
# schemas using relationships and ensures that the DOI information is correctly
# reflected in the experiment records and public data folders.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beamtime_server import crud
from beamtime_server.models import ExperimentItem, QueueItem
from beamtime_server.services import DOISchema
from beamtime_server.utils import DatabaseManager, DOIConfig, get_logger

__all__ = ["DOIProcessor"]


class DOIMetadataBuilder:
    """Builder class for constructing DOI metadata schemas using relationships."""

    def __init__(self, db_manager: DatabaseManager):
        self._db_manager = db_manager
        self._doi_config = DOIConfig()

    def build_from_queue_item(self, queue_item: QueueItem) -> DOISchema:
        """Build DOI metadata schema from a queue item using relationships."""
        with self._db_manager.get_session() as session:
            # Load the experiment with all needed relationships
            experiment = session.execute(
                select(ExperimentItem)
                .options(selectinload(ExperimentItem.spokesperson), selectinload(ExperimentItem.run))
                .where(ExperimentItem.id == queue_item.experiment_id)
            ).scalar_one()

            return self._build_doi_schema(experiment, queue_item)

    def _build_doi_schema(self, experiment: ExperimentItem, queue_item) -> DOISchema:
        """Build DOI schema from experiment data."""
        # Build creators from spokesperson relationship
        creators = self._build_creators_from_spokesperson(experiment.spokesperson)

        # Extract publication year from start date
        pub_year = self._get_publication_year_from_experiment(experiment)

        # Generate DOI with correct format
        doi_id = f"{self._doi_config.prefix}/data_{experiment.id}"

        # Build public data URL
        public_data_url = f"https://public.seescience.org/data/{pub_year}/{experiment.id}"

        # Determine event type based on draft_doi flag
        event_type = "draft" if hasattr(queue_item, "draft_doi") and queue_item.draft_doi else "publish"

        # Build and return DOI metadata
        return DOISchema(
            creators=creators,
            titles=[{"title": experiment.title}],
            publisher="University of Chicago",
            publication_year=pub_year,
            types={"resourceType": "Dataset", "resourceTypeGeneral": "Dataset"},
            language="en",
            version="0.1",
            dates=[{"date": experiment.start_date.isoformat() if experiment.start_date else None, "dateType": "Issued"}],
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

    def _build_creators_from_spokesperson(self, spokesperson) -> list[dict]:
        """Build DOI creators list from spokesperson relationship."""
        if not spokesperson:
            return []

        creator = {
            "name": f"{spokesperson.last_name}, {spokesperson.first_name}",
            "nameType": "Personal",
            "givenName": spokesperson.first_name,
            "familyName": spokesperson.last_name,
        }

        # Add ORCID if available
        if hasattr(spokesperson, "orcid") and spokesperson.orcid:
            creator["nameIdentifiers"] = [{"nameIdentifier": spokesperson.orcid, "nameIdentifierScheme": "ORCID", "schemeUri": "https://orcid.org"}]

        return [creator]

    def _get_publication_year_from_experiment(self, experiment: ExperimentItem) -> int:
        """Extract publication year from experiment start date."""
        if experiment.start_date:
            # Assuming start_date is a datetime or string in ISO format
            if hasattr(experiment.start_date, "year"):
                return experiment.start_date.year
            else:
                # If it's a string, try to parse the year
                return int(str(experiment.start_date)[:4])

        return datetime.now().year


class DOIProcessor:
    """Processor for handling DOI-related operations."""

    def __init__(self, db_manager: DatabaseManager, data_service, doi_service):
        self._db_manager = db_manager
        self._data_service = data_service
        self._doi_service = doi_service
        self._doi_metadata_builder = DOIMetadataBuilder(db_manager)
        self._logger = get_logger()

    def _build_doi_metadata(self, queue_item: QueueItem) -> DOISchema:
        """Build DOI metadata schema from experiment data."""
        return self._doi_metadata_builder.build_from_queue_item(queue_item)

    def process_doi(self, queue_item: QueueItem) -> None:
        """Process DOI creation for a queue item."""
        try:
            self._logger.info(f"Processing DOI for queue item {queue_item.id}")

            # Build DOI metadata
            doi_metadata = self._build_doi_metadata(queue_item)

            # Handle DOI creation and subsequent processing
            self._handle_doi_creation(queue_item, doi_metadata)

        except Exception as e:
            self._logger.error(f"DOI processing failed for queue item {queue_item.id}: {e}")
            raise

    def publish_draft_doi(self, doi_id: str) -> bool:
        """Publish an existing draft DOI to make it findable."""
        try:
            result = self._doi_service.publish_doi(doi_id)
            if result:
                self._logger.info(f"Successfully published DOI {doi_id}")
                return True
            else:
                self._logger.error(f"Failed to publish DOI {doi_id}")
                return False
        except Exception as e:
            self._logger.error(f"Error publishing DOI {doi_id}: {e}")
            return False

    def _handle_doi_creation(self, queue_item: QueueItem, doi_metadata: DOISchema) -> None:
        """Handle DOI creation/update and subsequent processing."""
        # Create or update the DOI using executor
        result = self._doi_service.create_or_update_doi(doi_metadata)
        self._logger.info("DOI creation completed")

        # Extract DOI ID from result (DataCite API format)
        actual_doi_id = result.get("data", {}).get("id") if result else doi_metadata.doi

        if not actual_doi_id:
            raise Exception("DOI creation returned no ID")

        # Update experiment with DOI link
        doi_link = f"https://doi.org/{actual_doi_id}"
        from beamtime_server import crud

        success = crud.update_experiment(self._db_manager, queue_item.experiment_id, sees_doi=doi_link)
        if not success:
            raise Exception("Failed to update experiment DOI link")
        self._logger.info("Updated experiment DOI link in database")

        # Create DOI public folder and index file
        self._create_doi_public_resources(queue_item, doi_metadata, actual_doi_id)

        # Log success
        event_type = doi_metadata.event
        doi_status = "draft DOI" if event_type == "draft" else "findable DOI"
        self._logger.info(f"Successfully processed {doi_status} {actual_doi_id} pointing to {doi_metadata.url}")
        self._logger.info(f"Updated experiment {queue_item.experiment_id} with DOI link: {doi_link}")

    def _create_doi_public_resources(self, queue_item: QueueItem, doi_metadata: DOISchema, doi_id: str) -> None:
        """Create DOI public folder and index.html file."""
        base_path = crud.get_info_value(self._db_manager, "base_path")
        pub_year = doi_metadata.publication_year

        # Create DOI public folder
        self._data_service.create_doi_public_folder(queue_item.experiment_id, pub_year, base_path)
        self._logger.info("DOI public folder created")

        # Create index.html file with DOI information
        title = doi_metadata.titles[0]["title"] if doi_metadata.titles else "Unknown"

        # Build creators string from DOI metadata
        creators_str = None
        if doi_metadata.creators:
            creators_list = [creator.get("name", "Unknown") for creator in doi_metadata.creators]
            creators_str = ", ".join(creators_list)

        self._data_service.create_doi_index_file(
            experiment_id=queue_item.experiment_id,
            year=pub_year,
            doi_id=doi_id,
            title=title,
            user_base_path=base_path,
            creators=creators_str,
            version=doi_metadata.version,
        )
        self._logger.info("DOI index.html file created")
