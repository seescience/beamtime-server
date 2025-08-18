# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: BeamtimeServer.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module provides a class for creating, updating, publishing and deleting DOIs.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import argparse

from tests import run_all_tests


def main() -> None:
    """Main entry point for the Beamtime Server."""
    parser = argparse.ArgumentParser(description="Beamtime Server Command Line Interface")
    parser.add_argument("-t", "--test", action="store_true", help="Run all tests")
    args = parser.parse_args()

    if args.test:
        run_all_tests()


if __name__ == "__main__":
    main()
