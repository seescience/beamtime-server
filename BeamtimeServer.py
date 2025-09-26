# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: BeamtimeServer.py
# ----------------------------------------------------------------------------------
# Purpose:
# This is the main application file for the Beamtime Server.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from argparse import ArgumentParser

from beamtime_server import DatabaseManager, QueueProcessor, get_logger
from tests import run_all_tests


class BeamtimeServer:
    """Main application class for the Beamtime Server."""

    def __init__(self, dry_run: bool = False):
        """Initialize the Beamtime Server."""

        # Initialize components
        self._logger = get_logger()
        self._db_manager = DatabaseManager()
        self._queue_processor = QueueProcessor(self._db_manager, dry_run=dry_run)

    def _run_tests(self) -> None:
        """Run all application tests."""
        self._logger.info("Running all tests")
        run_all_tests()

    def run(self, args) -> None:
        """Run the main application with parsed command line arguments."""
        self._logger.info("Starting Beamtime Server")

        if args.test:
            self._run_tests()
        elif args.queue:
            self._queue_processor.run_continuous(poll_interval=args.interval)
        elif args.batch:
            self._queue_processor.process_all_pending()
        else:
            print("No action specified. Use --help for available options.")


def main() -> None:
    """Main entry point for the Beamtime Server."""
    # Parse args first to get dry_run flag
    parser = ArgumentParser(description="Beamtime Server Command Line Interface")
    parser.add_argument("-t", "--test", action="store_true", help="Run all tests")
    parser.add_argument("-q", "--queue", action="store_true", help="Start continuous queue processing")
    parser.add_argument("-b", "--batch", action="store_true", help="Process all pending queue items and exit")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Run in dry-run mode (no external API calls)")
    parser.add_argument("-i", "--interval", type=int, default=300, help="Poll interval in seconds for continuous queue processing (default: 300)")
    args = parser.parse_args()

    server = BeamtimeServer(dry_run=args.dry_run)
    server.run(args)


if __name__ == "__main__":
    main()
