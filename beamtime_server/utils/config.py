# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/utils/config.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module provides centralized configuration management for the beamtime server.
# It loads environment variables from .env files and makes them available to other
# modules using Pydantic for validation.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, SecretStr, field_validator, model_validator

__all__ = ["DOIConfig"]


# Set the configuration path relative to this file's location
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config"


class DOIConfig(BaseModel):
    """Configuration class for the Beamtime Server DOI service."""

    base_url: HttpUrl = Field(..., description="The base URL for the DOI service", alias="DOI_BASE_URL")
    username: str = Field(..., description="The username for authenticating with the DOI service.", alias="DOI_USERNAME")
    password: SecretStr = Field(..., description="The password for authenticating with the DOI service.", alias="DOI_PASSWORD")
    prefix: str = Field(..., description="The assigned DOI prefix (e.g., '10.12345').", alias="DOI_PREFIX")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, prefix: str) -> str:
        """Validate that the DOI prefix is in the correct format (e.g., '10.XXXX')."""
        if not prefix.startswith("10."):
            raise ValueError("DOI prefix must start with '10.'")
        # Check if there's content after "10."
        prefix_parts = prefix.split(".", 1)
        if len(prefix_parts) < 2 or not prefix_parts[1].strip():
            raise ValueError("DOI prefix must have format '10.XXXXX' with a valid suffix")
        return prefix

    @field_validator("username")
    @classmethod
    def validate_username(cls, username: str) -> str:
        """Validate that the username is not empty or just whitespace."""
        if not username.strip():
            raise ValueError("Username cannot be empty")
        return username.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: SecretStr) -> SecretStr:
        """Validate that the password is not empty or just whitespace."""
        password_value = password.get_secret_value()
        if not password_value.strip():
            raise ValueError("Password cannot be empty")
        return password

    @model_validator(mode="before")
    @classmethod
    def load_environment(cls, data: Any) -> dict[str, Any]:
        """Load environment variables from doi.env file before validation."""
        # Load the doi.env file from the project config directory
        doi_env_file = CONFIG_PATH / "doi.env"
        if not doi_env_file.is_file():
            raise FileNotFoundError(f"Configuration file not found: {doi_env_file}")

        # Load environment variables from the .env file
        load_dotenv(dotenv_path=doi_env_file)

        # Return environment variables for Pydantic to process
        return {
            "DOI_BASE_URL": os.getenv("DOI_BASE_URL"),
            "DOI_USERNAME": os.getenv("DOI_USERNAME"),
            "DOI_PASSWORD": os.getenv("DOI_PASSWORD"),
            "DOI_PREFIX": os.getenv("DOI_PREFIX"),
        }

    # Ensure immutability of the configuration
    model_config = {"str_strip_whitespace": True, "validate_assignment": True, "frozen": True}
