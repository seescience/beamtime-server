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

from beamtime_server.models import ExperimentItem, Person, QueueItem
from beamtime_server.utils.database import DBException

__all__ = [
    "get_next_queue_item",
    "update_experiment_status",
    "delete_queue_item",
    "get_experiment_title",
    "update_experiment_doi_link",
    "update_experiment_folder",
    "update_experiment_esaf_file",
    "get_experiment_old_process_status",
    "get_experiment_start_date",
]


def get_next_queue_item(db_manager) -> Optional[dict]:
    """Get the next queue item to process."""
    with db_manager.get_session() as session:
        try:
            queue_item = session.execute(select(QueueItem).order_by(QueueItem.id).limit(1)).scalar_one_or_none()

            if queue_item:
                # Return dict with the data we need to avoid session issues
                return {
                    "id": queue_item.id,
                    "experiment_id": queue_item.experiment_id,
                    "create_doi": queue_item.create_doi,
                    "draft_doi": queue_item.draft_doi,
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


def update_experiment_folder(db_manager, experiment_id: int, folder_path: str) -> bool:
    """Update experiment folder field with the created folder path."""
    with db_manager.get_session() as session:
        try:
            result = session.execute(update(ExperimentItem).where(ExperimentItem.id == experiment_id).values(folder=folder_path))
            return result.rowcount > 0
        except Exception as e:
            raise DBException(f"Error updating experiment {experiment_id} folder path: {e}")


def update_experiment_esaf_file(db_manager, experiment_id: int, esaf_file_path: str) -> bool:
    """Update experiment esaf_pdf_file field with the beamtime ESAF file path."""
    with db_manager.get_session() as session:
        try:
            result = session.execute(update(ExperimentItem).where(ExperimentItem.id == experiment_id).values(esaf_pdf_file=esaf_file_path))
            return result.rowcount > 0
        except Exception as e:
            raise DBException(f"Error updating experiment {experiment_id} ESAF file path: {e}")


def get_experiment_old_process_status(db_manager, experiment_id: int) -> Optional[int]:
    """Get experiment old_process_status_id."""
    with db_manager.get_session() as session:
        try:
            experiment = session.execute(select(ExperimentItem).where(ExperimentItem.id == experiment_id)).scalar_one_or_none()
            return experiment.old_process_status_id if experiment else None
        except Exception as e:
            raise DBException(f"Error getting old process status for experiment {experiment_id}: {e}")


def get_experiment_start_date(db_manager, experiment_id: int) -> Optional[str]:
    """Get experiment start year for DOI metadata."""
    with db_manager.get_session() as session:
        try:
            experiment = session.execute(select(ExperimentItem).where(ExperimentItem.id == experiment_id)).scalar_one_or_none()

            if experiment and experiment.start_date:
                return str(experiment.start_date.year)
            return None

        except Exception as e:
            raise DBException(f"Error getting start date for experiment {experiment_id}: {e}")


def get_acknowledgments_by_ids(db_manager, acknowledgment_ids: str) -> list[dict]:
    """Get acknowledgment records by comma-separated IDs."""
    if not acknowledgment_ids or not acknowledgment_ids.strip():
        return []

    # Parse comma-separated IDs
    try:
        ids = [int(id_str.strip()) for id_str in acknowledgment_ids.split(",") if id_str.strip()]
    except ValueError:
        raise DBException(f"Invalid acknowledgment IDs format: {acknowledgment_ids}")

    if not ids:
        return []

    with db_manager.get_session() as session:
        try:
            from beamtime_server.models import Acknowledgment

            # Get acknowledgment records
            result = session.execute(select(Acknowledgment).where(Acknowledgment.id.in_(ids)).order_by(Acknowledgment.id)).scalars().all()

            return [{"id": ack.id, "title": ack.title, "text": ack.text} for ack in result]

        except Exception as e:
            raise DBException(f"Error getting acknowledgments {acknowledgment_ids}: {e}")


def get_esaf_pdf_folder(db_manager) -> Optional[str]:
    """Get the ESAF PDF folder path from info table."""
    with db_manager.get_session() as session:
        try:
            from beamtime_server.models import Info

            result = session.execute(select(Info).where(Info.key == "esaf_pdf_folder")).scalar_one_or_none()

            return result.value if result else None

        except Exception as e:
            raise DBException(f"Error getting ESAF PDF folder: {e}")


def get_experiment_run_name(db_manager, experiment_id: int) -> Optional[str]:
    """Get the run name for an experiment."""
    with db_manager.get_session() as session:
        try:
            from beamtime_server.models import ExperimentItem, Run

            result = session.execute(
                select(Run.name).select_from(ExperimentItem).join(Run, ExperimentItem.run_id == Run.id).where(ExperimentItem.id == experiment_id)
            ).scalar_one_or_none()

            return result

        except Exception as e:
            raise DBException(f"Error getting run name for experiment {experiment_id}: {e}")
