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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


class QueueItem(Base):
    """Model for queue items to be processed."""

    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    create_doi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    draft_doi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_path: Mapped[str] = mapped_column(Text, nullable=True)
    pvlog_path: Mapped[str] = mapped_column(Text, nullable=True)
    acknowledgments: Mapped[str] = mapped_column(Text, nullable=True)
    process_status_id: Mapped[int] = mapped_column(Integer, ForeignKey("process_status.id"), nullable=False)


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
    beamline_id: Mapped[int] = mapped_column(Integer, ForeignKey("beamline.id"), nullable=True)
    proposal_id: Mapped[int] = mapped_column(Integer, ForeignKey("proposal.id"), nullable=True)
    spokesperson_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.id"), nullable=True)
    beamline_contact_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.id"), nullable=True)
    process_status_id: Mapped[int] = mapped_column(Integer, ForeignKey("process_status.id"), nullable=True)


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
