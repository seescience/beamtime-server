#!/bin/bash
# ----------------------------------------------------------------------------------
# Project: BeamtimeServer
# File: start_beamtime_server.sh
# ----------------------------------------------------------------------------------
# Purpose: 
# This script is used to start the BeamtimeServer backend application in continuous
# processing mode, using the default 5-minute polling interval.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (C) 2025 GSECARS, The University of Chicago, USA
# Copyright (C) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

uv run BeamtimeServer.py -q & > /dev/null 2>&1
