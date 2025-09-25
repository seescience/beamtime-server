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

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beamtime_server.models import Acknowledgment, ExperimentItem, Info, ProcessStatus, QueueItem
from beamtime_server.utils.database import DBException


def get_info_value(db_manager, key: str) -> Optional[str]:
    """Get a value from the info table by key."""
    with db_manager.get_session() as session:
        try:
            result = session.execute(select(Info).where(Info.key == key)).scalar_one_or_none()
            return result.value if result else None
        except Exception as e:
            raise DBException(f"Error getting info value for key '{key}': {e}")


def get_next_queue_item(db_manager) -> Optional[dict]:
    """Get next queue item as dict for backward compatibility."""
    with db_manager.get_session() as session:
        try:
            queue_item = session.execute(
                select(QueueItem)
                .options(
                    selectinload(QueueItem.experiment).selectinload(ExperimentItem.spokesperson),
                    selectinload(QueueItem.experiment).selectinload(ExperimentItem.run),
                    selectinload(QueueItem.experiment).selectinload(ExperimentItem.process_status),
                    selectinload(QueueItem.experiment).selectinload(ExperimentItem.old_process_status),
                )
                .order_by(QueueItem.id)
                .limit(1)
            ).scalar_one_or_none()

            if not queue_item:
                return None

            # Extract all data while session is active
            return {
                "id": queue_item.id,
                "experiment_id": queue_item.experiment_id,
                "data_path": queue_item.data_path,
                "acknowledgments": queue_item.acknowledgments,
                "draft_doi": queue_item.draft_doi,
            }
        except Exception as e:
            raise DBException(f"Error getting next queue item: {e}")


def delete_queue_item(db_manager, queue_id: int) -> bool:
    """Delete queue item."""
    with db_manager.get_session() as session:
        try:
            queue_item = session.execute(select(QueueItem).where(QueueItem.id == queue_id)).scalar_one_or_none()

            if not queue_item:
                return False

            session.delete(queue_item)
            session.commit()
            return True

        except Exception:
            session.rollback()
            return False


def get_acknowledgments_by_ids(db_manager, acknowledgment_ids: str) -> list[dict]:
    """Get acknowledgment records by comma-separated IDs and return as dictionaries."""
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
            acknowledgments = session.execute(select(Acknowledgment).where(Acknowledgment.id.in_(ids)).order_by(Acknowledgment.id)).scalars().all()

            # Convert to dictionaries to avoid session binding issues
            return [{"id": ack.id, "title": ack.title, "text": ack.text} for ack in acknowledgments]
        except Exception as e:
            raise DBException(f"Error getting acknowledgments {acknowledgment_ids}: {e}")


def get_experiment_old_process_status(db_manager, experiment_id: int) -> Optional[int]:
    """Get experiment's old process status using relationships."""
    with db_manager.get_session() as session:
        try:
            experiment = session.execute(
                select(ExperimentItem).options(selectinload(ExperimentItem.old_process_status)).where(ExperimentItem.id == experiment_id)
            ).scalar_one_or_none()

            return experiment.old_process_status_id if experiment else None
        except Exception as e:
            raise DBException(f"Error getting experiment old process status: {e}")


def set_experiment_process_status(db_manager, experiment_id: int, status_name: str) -> bool:
    """Set experiment process status by name using relationships."""
    with db_manager.get_session() as session:
        try:
            # Get the status by name
            status = session.execute(select(ProcessStatus).where(ProcessStatus.name == status_name)).scalar_one_or_none()

            if not status:
                return False

            # Update the experiment
            experiment = session.execute(select(ExperimentItem).where(ExperimentItem.id == experiment_id)).scalar_one_or_none()

            if not experiment:
                return False

            experiment.process_status_id = status.id
            session.commit()
            return True

        except Exception:
            session.rollback()
            return False


def get_experiment_run_name(db_manager, experiment_id: int) -> Optional[str]:
    """Get experiment run name using relationships."""
    with db_manager.get_session() as session:
        try:
            result = session.execute(
                select(ExperimentItem).options(selectinload(ExperimentItem.run)).where(ExperimentItem.id == experiment_id)
            ).scalar_one_or_none()

            # Extract run name while still in session
            return result.run.name if result and result.run else None
        except Exception as e:
            raise DBException(f"Error getting run name for experiment {experiment_id}: {e}")
