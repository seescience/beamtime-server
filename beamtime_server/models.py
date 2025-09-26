# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/models.py
# ----------------------------------------------------------------------------------
# Purpose:
# Database models for the beamtime server queue processing system.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from datetime import datetime
from enum import IntEnum
from typing import Optional

from sqlalchemy import TIMESTAMP, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ProcessStatusEnum(IntEnum):
    """Enum for process status values."""

    NEW = 1
    PENDING = 2
    MODIFIED = 3
    PROCESSED = 4
    LOCKED = 5
    ERROR = 6


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class ProcessStatus(Base):
    """Model for process status lookup table."""

    __tablename__ = "process_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    experiments: Mapped[list["ExperimentItem"]] = relationship(
        "ExperimentItem", foreign_keys="ExperimentItem.process_status_id", back_populates="process_status"
    )
    old_status_experiments: Mapped[list["ExperimentItem"]] = relationship(
        "ExperimentItem", foreign_keys="ExperimentItem.old_process_status_id", back_populates="old_process_status"
    )


class QueueItem(Base):
    """Model for queue items to be processed."""

    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(Integer, ForeignKey("experiment.id"), nullable=False)
    create_doi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    draft_doi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_path: Mapped[str] = mapped_column(Text, nullable=True)
    pvlog_path: Mapped[str] = mapped_column(Text, nullable=True)
    acknowledgments: Mapped[str] = mapped_column(Text, nullable=True)

    experiment: Mapped["ExperimentItem"] = relationship("ExperimentItem", back_populates="queue_items")


class ExperimentItem(Base):
    """Model for the experiments."""

    __tablename__ = "experiment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    folder: Mapped[str] = mapped_column(Text, nullable=True)
    sees_doi: Mapped[str] = mapped_column(Text, nullable=True)
    esaf_pdf_file: Mapped[str] = mapped_column(Text, nullable=True)
    proposal_pdf_file: Mapped[str] = mapped_column(Text, nullable=True)
    time_request: Mapped[int] = mapped_column(Integer, nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    pvlog_file: Mapped[str] = mapped_column(Text, nullable=True)

    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("run.id"), nullable=True)
    esaf_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("esaf_type.id"), nullable=True)
    esaf_status_id: Mapped[int] = mapped_column(Integer, ForeignKey("esaf_status.id"), nullable=True)
    beamline_id: Mapped[int] = mapped_column(Integer, ForeignKey("apsbss_beamline.id"), nullable=True)
    proposal_id: Mapped[int] = mapped_column(Integer, ForeignKey("proposal.id"), nullable=True)
    spokesperson_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.id"), nullable=True)
    beamline_contact_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.id"), nullable=True)
    process_status_id: Mapped[int] = mapped_column(Integer, ForeignKey("process_status.id"), nullable=True)
    old_process_status_id: Mapped[int] = mapped_column(Integer, ForeignKey("process_status.id"), nullable=True)

    run: Mapped[Optional["Run"]] = relationship("Run", back_populates="experiments")
    spokesperson: Mapped[Optional["Person"]] = relationship("Person", foreign_keys=[spokesperson_id], back_populates="spokesperson_experiments")
    beamline_contact: Mapped[Optional["Person"]] = relationship("Person", foreign_keys=[beamline_contact_id], back_populates="contact_experiments")
    process_status: Mapped[Optional["ProcessStatus"]] = relationship("ProcessStatus", foreign_keys=[process_status_id], back_populates="experiments")
    old_process_status: Mapped[Optional["ProcessStatus"]] = relationship(
        "ProcessStatus", foreign_keys=[old_process_status_id], back_populates="old_status_experiments"
    )
    queue_items: Mapped[list["QueueItem"]] = relationship("QueueItem", back_populates="experiment")
    beamline: Mapped[Optional["Beamline"]] = relationship("Beamline", foreign_keys=[beamline_id], back_populates="experiments")
    proposal: Mapped[Optional["Proposal"]] = relationship("Proposal", back_populates="experiments")
    esaf_type: Mapped[Optional["EsafType"]] = relationship("EsafType")
    esaf_status: Mapped[Optional["EsafStatus"]] = relationship("EsafStatus")


class Acknowledgment(Base):
    """Model for acknowledgment records."""

    __tablename__ = "acknowledgment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)


class Info(Base):
    """Model for system configuration info (key-value pairs)."""

    __tablename__ = "info"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    modify_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    display_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Run(Base):
    """Model for experiment runs."""

    __tablename__ = "run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=True)

    experiments: Mapped[list["ExperimentItem"]] = relationship("ExperimentItem", back_populates="run")


class Person(Base):
    """Model for the persons."""

    __tablename__ = "person"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    badge: Mapped[int] = mapped_column(Integer)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    orcid: Mapped[str] = mapped_column(String(64))
    affiliation_id: Mapped[int] = mapped_column(Integer, ForeignKey("institution.id"))
    user_level_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_level.id"))

    spokesperson_experiments: Mapped[list["ExperimentItem"]] = relationship(
        "ExperimentItem", foreign_keys="ExperimentItem.spokesperson_id", back_populates="spokesperson"
    )
    contact_experiments: Mapped[list["ExperimentItem"]] = relationship(
        "ExperimentItem", foreign_keys="ExperimentItem.beamline_contact_id", back_populates="beamline_contact"
    )
    proposals: Mapped[list["Proposal"]] = relationship("Proposal", back_populates="spokesperson")
    affiliation: Mapped[Optional["Institution"]] = relationship("Institution")
    user_level: Mapped[Optional["UserLevel"]] = relationship("UserLevel")


class Institution(Base):
    """Model for institutions."""

    __tablename__ = "institution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(2048), nullable=True)
    city: Mapped[str] = mapped_column(String(512), nullable=True)
    country: Mapped[str] = mapped_column(String(512), nullable=True)


class UserLevel(Base):
    """Model for user levels."""

    __tablename__ = "user_level"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=True)


class EsafType(Base):
    """Model for ESAF types."""

    __tablename__ = "esaf_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=True)


class EsafStatus(Base):
    """Model for ESAF statuses."""

    __tablename__ = "esaf_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=True)


class Beamline(Base):
    """Model for beamlines."""

    __tablename__ = "apsbss_beamline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=True)

    experiments: Mapped[list["ExperimentItem"]] = relationship("ExperimentItem", back_populates="beamline")


class Proposal(Base):
    """Model for proposals."""

    __tablename__ = "proposal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=True)
    spokesperson_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.id"), nullable=True)

    spokesperson: Mapped[Optional["Person"]] = relationship("Person", back_populates="proposals")
    experiments: Mapped[list["ExperimentItem"]] = relationship("ExperimentItem", back_populates="proposal")
