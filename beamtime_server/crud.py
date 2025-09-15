# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/crud.py
# ----------------------------------------------------------------------------------
# Purpose:
# Direct CRUD operations for the beamtime server, used by the queue processor.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from typing import Optional

from sqlalchemy import delete, select, update

from beamtime_server.models import ExperimentItem, Person, ProcessStatusEnum, QueueItem
from beamtime_server.utils.database import DBException

__all__ = ["get_next_queue_item", "update_experiment_status", "delete_queue_item", "get_experiment_title", "update_experiment_doi_link"]


def get_next_queue_item(db_manager) -> Optional[dict]:
    """Get the next pending queue item (status = PENDING)."""
    with db_manager.get_session() as session:
        try:
            queue_item = session.execute(
                select(QueueItem).where(QueueItem.process_status_id == ProcessStatusEnum.PENDING).order_by(QueueItem.id).limit(1)
            ).scalar_one_or_none()

            if queue_item:
                # Return dict with the data we need to avoid session issues
                return {
                    "id": queue_item.id,
                    "experiment_id": queue_item.experiment_id,
                    "create_doi": queue_item.create_doi,
                    "proposal_id": queue_item.proposal_id,
                    "data_path": queue_item.data_path,
                    "pvlog_path": queue_item.pvlog_path,
                    "acknowledgments": queue_item.acknowledgments,
                }
            return None
        except Exception as e:
            raise DBException(f"Error fetching next queue item: {e}")


def update_experiment_status(db_manager, experiment_id: int, status_id: int) -> bool:
    """Update experiment process_status_id."""
    with db_manager.get_session() as session:
        try:
            result = session.execute(update(ExperimentItem).where(ExperimentItem.id == experiment_id).values(process_status_id=status_id))
            return result.rowcount > 0
        except Exception as e:
            raise DBException(f"Error updating experiment {experiment_id} status: {e}")


def delete_queue_item(db_manager, queue_id: int) -> bool:
    """Delete a queue item after successful processing."""
    with db_manager.get_session() as session:
        try:
            result = session.execute(delete(QueueItem).where(QueueItem.id == queue_id))
            return result.rowcount > 0
        except Exception as e:
            raise DBException(f"Error deleting queue item {queue_id}: {e}")


def get_experiment_title(db_manager, experiment_id: int) -> Optional[str]:
    """Get experiment title by ID."""
    with db_manager.get_session() as session:
        try:
            experiment = session.execute(select(ExperimentItem).where(ExperimentItem.id == experiment_id)).scalar_one_or_none()

            if experiment and experiment.title:
                return experiment.title
            else:
                # Fallback title
                return f"Beamtime Data - Experiment {experiment_id}"

        except Exception as e:
            raise DBException(f"Error getting title for experiment {experiment_id}: {e}")


def build_creators_from_spokesperson(db_manager, experiment_id: int) -> Optional[list[dict]]:
    """Build DOI creators list from experiment spokesperson."""
    with db_manager.get_session() as session:
        try:
            # Get experiment with spokesperson
            experiment = session.execute(select(ExperimentItem).where(ExperimentItem.id == experiment_id)).scalar_one_or_none()

            if not experiment or not experiment.spokesperson_id:
                return None

            # Get spokesperson details
            spokesperson = session.execute(select(Person).where(Person.id == experiment.spokesperson_id)).scalar_one_or_none()

            if not spokesperson:
                return None

            # Build creator structure for DataCite
            creators = [
                {
                    "name": f"{spokesperson.last_name}, {spokesperson.first_name}",
                    "nameType": "Personal",
                    "givenName": spokesperson.first_name,
                    "familyName": spokesperson.last_name,
                }
            ]

            # Add ORCID if available
            if spokesperson.orcid:
                creators[0]["nameIdentifiers"] = [{"nameIdentifier": spokesperson.orcid, "nameIdentifierScheme": "ORCID", "schemeUri": "https://orcid.org"}]

            return creators

        except Exception as e:
            raise DBException(f"Error building creators for experiment {experiment_id}: {e}")


def get_publication_year_for_experiment(db_manager, experiment_id: int) -> Optional[int]:
    """Get publication year from experiment start date."""
    with db_manager.get_session() as session:
        try:
            experiment = session.execute(select(ExperimentItem).where(ExperimentItem.id == experiment_id)).scalar_one_or_none()

            if experiment and experiment.start_date:
                return experiment.start_date.year
            return None

        except Exception as e:
            raise DBException(f"Error getting publication year for experiment {experiment_id}: {e}")


def update_experiment_doi_link(db_manager, experiment_id: int, doi_link: str) -> bool:
    """Update experiment sees_doi field with the DOI link."""
    with db_manager.get_session() as session:
        try:
            result = session.execute(update(ExperimentItem).where(ExperimentItem.id == experiment_id).values(sees_doi=doi_link))
            return result.rowcount > 0
        except Exception as e:
            raise DBException(f"Error updating experiment {experiment_id} DOI link: {e}")
