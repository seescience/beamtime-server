# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/utils/__init__.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module initializes the utils package for the Beamtime Server. It also
# provides centralized configuration management for the different services used.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from beamtime_server.utils.config import DOIConfig

__all__ = ["DOIConfig", "doi_config"]


# Initialize the centralized DOI configuration
doi_config = DOIConfig()
