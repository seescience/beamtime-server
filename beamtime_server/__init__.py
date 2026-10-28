# SPDX-License-Identifier: MIT

from importlib.metadata import version

from beamtime_server.server import Server

__version__ = version("beamtime_server")


def main() -> None:
    Server(__version__)
