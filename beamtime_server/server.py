# SPDX-License-Identifier: MIT

from argparse import ArgumentParser

from beamtime_server.processors import QueueProcessor
from beamtime_server.utils import DatabaseManager, get_logger
from tests import run_all_tests


class Server:
    """Creates the Beamtime server application."""

    def __init__(self, version: str, dry_run: bool = False) -> None:
        """Initializes the Server application."""
        # set version and logger
        self._version = version
        self._logger = get_logger()

        # create the parser and run
        self._parser = self._make_parser()
        self._run()

    def _make_parser(self) -> ArgumentParser:
        """Creates the argument parser."""
        parser = ArgumentParser(description=f"Beamtime Server v{self._version}")
        parser.add_argument("-t", "--test", action="store_true", help="Run all tests")
        parser.add_argument("-q", "--queue", action="store_true", help="Start continuous queue processing")
        parser.add_argument("-b", "--batch", action="store_true", help="Process all pending queue items and exit")
        parser.add_argument("-d", "--dry-run", action="store_true", help="Run in dry-run mode (no external API calls)")
        parser.add_argument("-i", "--interval", type=int, default=300, help="Poll interval in seconds for continuous queue processing (default: 300)")

        return parser

    def _run(self) -> None:
        """Runs the application or tests based on the CLI arguments."""
        args = self._parser.parse_args()

        db_manager = DatabaseManager()
        queue_processor = QueueProcessor(db_manager, dry_run=args.dry_run)

        if args.test:
            self._logger.info("Running all tests")
            run_all_tests()
        elif args.queue:
            queue_processor.run_continuous(poll_interval=args.interval)
        elif args.batch:
            queue_processor.process_all_pending()
        else:
            print("No action specified. Use --help for available options.")
