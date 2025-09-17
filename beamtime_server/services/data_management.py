# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/services/data_management.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module provides a service for managing experiment data folders and structure.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import glob
import shutil
from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path
from typing import Optional

from beamtime_server.utils import DatabaseManager, DOIConfig, get_logger
from beamtime_server.utils.config import BeamtimeConfig


class DataManagementError(Exception):
    """Exception raised for data management operations."""

    def __init__(self, message: str, operation: str, original_error: Exception = None):
        self.message = message
        self.operation = operation
        self.original_error = original_error
        super().__init__(self.message)


@dataclass
class DataManagementService:
    """A service for managing experiment data folders and structure."""

    db_manager: Optional[DatabaseManager] = None
    _logger: Logger = field(init=False, compare=False, repr=False, default=get_logger())
    _doi_config: DOIConfig = field(init=False, compare=False, repr=False, default=DOIConfig())
    _beamtime_config: BeamtimeConfig = field(init=False, compare=False, repr=False, default=BeamtimeConfig())

    def create_folders_at_path(self, path: str | Path, user_base_path: str, acknowledgments: list[dict] = None, experiment_id: int = None) -> Path:
        """Create folder structure directly at the specified path with default subfolders."""
        try:
            folder_path = Path(path) / Path(user_base_path)

            # Create the main folder
            folder_path.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"Created folder: {folder_path}")

            # Create default subfolders
            subfolders = ["info", "pvlog"]
            for subfolder in subfolders:
                subfolder_path = folder_path / subfolder
                subfolder_path.mkdir(parents=True, exist_ok=True)

            # Create acknowledgments subfolder and files if acknowledgments exist
            if acknowledgments:
                ack_folder = folder_path / "info" / "acknowledgments"
                ack_folder.mkdir(parents=True, exist_ok=True)

                self._create_acknowledgment_files(ack_folder, acknowledgments)
                self._logger.info(f"Created {len(acknowledgments)} acknowledgment files in: {ack_folder}")

            # Note: ESAF file copying is now handled by the queue processor

            self._logger.info(f"Created default subfolders (info, pvlog) in: {folder_path}")

            # Remove base path prefix and return with leading slash
            if user_base_path:
                try:
                    relative_path = folder_path.relative_to(Path(user_base_path))
                    return Path("/") / relative_path
                except ValueError:
                    # Path is not under base path, return full path
                    return folder_path

            return folder_path

        except (PermissionError, OSError) as e:
            message = f"Failed to create folders at {path}: {e}"
            self._logger.error(message)
            raise DataManagementError(message, operation="create_folders_at_path", original_error=e)

    def _create_acknowledgment_files(self, ack_folder: Path, acknowledgments: list[dict]) -> None:
        """Create text files for each acknowledgment in the acknowledgments folder."""
        for ack in acknowledgments:
            try:
                # Create safe filename from title or use ID
                title = ack.get("title", f"Acknowledgment_{ack['id']}")
                # Replace unsafe characters for filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).rstrip()
                filename = f"{safe_title}.txt"

                file_path = ack_folder / filename

                # Only create if file doesn't exist (never override)
                if not file_path.exists():
                    content = f"Title: {ack.get('title', 'N/A')}\n\n{ack.get('text', 'No content available')}"

                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    self._logger.info(f"Created acknowledgment file: {filename}")
                else:
                    self._logger.info(f"Acknowledgment file already exists, skipping: {filename}")

            except Exception as e:
                self._logger.warning(f"Failed to create acknowledgment file for ID {ack.get('id')}: {e}")

    def copy_esaf_file(self, experiment_id: int, info_folder: Path, user_base_path: str) -> Optional[str]:
        """Copy ESAF PDF file to the info folder and beamtime ESAF folder if it exists."""
        try:
            from beamtime_server import crud

            # Get ESAF PDF folder and run name
            esaf_folder = crud.get_esaf_pdf_folder(self.db_manager)
            run_name = crud.get_experiment_run_name(self.db_manager, experiment_id)

            if not esaf_folder or not run_name:
                self._logger.warning(f"Missing ESAF folder ({esaf_folder}) or run name ({run_name}) for experiment {experiment_id}")
                return None

            # Construct search path: esaf_folder/run_name/
            search_path = Path(esaf_folder) / run_name

            if not search_path.exists():
                self._logger.warning(f"ESAF search path does not exist: {search_path}")
                return None

            # Search for ESAF file: ESAF-{experiment_id}*.pdf in all subfolders
            pattern = f"ESAF-{experiment_id}*.pdf"
            search_pattern = str(search_path / "**" / pattern)

            matching_files = glob.glob(search_pattern, recursive=True)

            if not matching_files:
                self._logger.info(f"No ESAF file found matching pattern {pattern} in {search_path}")
                return None

            if len(matching_files) > 1:
                self._logger.warning(f"Multiple ESAF files found for experiment {experiment_id}: {matching_files}. Using first one.")

            source_file = Path(matching_files[0])
            beamtime_esaf_file_path = None

            # Copy to experiment info folder
            info_dest_file = info_folder / source_file.name
            if not info_dest_file.exists():
                shutil.copy2(source_file, info_dest_file)
                self._logger.info(f"Copied ESAF file to info folder: {source_file.name} -> {info_dest_file}")
            else:
                self._logger.info(f"ESAF file already exists in info folder, skipping: {info_dest_file.name}")

            # Copy to beamtime ESAF folder if configured
            if self._beamtime_config.beamtime_folder:
                try:
                    # Create destination with base path prepended: user_base_path/BEAMTIME_FOLDER/esaf/run_name/
                    beamtime_esaf_path = Path(user_base_path) / Path(self._beamtime_config.beamtime_folder) / "esaf" / run_name
                    beamtime_esaf_path.mkdir(parents=True, exist_ok=True)

                    beamtime_dest_file = beamtime_esaf_path / source_file.name

                    # Only copy if destination doesn't exist (never override)
                    if not beamtime_dest_file.exists():
                        shutil.copy2(source_file, beamtime_dest_file)
                        self._logger.info(f"Copied ESAF file to beamtime folder: {source_file.name} -> {beamtime_dest_file}")
                        beamtime_esaf_file_path = str(beamtime_dest_file)
                    else:
                        self._logger.info(f"ESAF file already exists in beamtime folder, skipping: {beamtime_dest_file.name}")
                        # Even if we didn't copy, the file exists so we can return its path
                        beamtime_esaf_file_path = str(beamtime_dest_file)

                except Exception as beamtime_error:
                    self._logger.warning(f"Failed to copy ESAF file to beamtime folder: {beamtime_error}")
            else:
                self._logger.info("BEAMTIME_FOLDER not configured, skipping beamtime ESAF copy")

            # Remove base path prefix and return with leading slash
            if user_base_path and beamtime_esaf_file_path:
                try:
                    relative_path = Path(beamtime_esaf_file_path).relative_to(Path(user_base_path))
                    return str(Path("/") / relative_path)
                except ValueError:
                    # Path is not under base path, return full path
                    return beamtime_esaf_file_path

            return beamtime_esaf_file_path

        except Exception as e:
            self._logger.warning(f"Failed to copy ESAF file for experiment {experiment_id}: {e}")
            return None

    def create_doi_public_folder(self, experiment_id: int, year: int, user_base_path: str, public_base_path: Optional[Path] = None) -> Path:
        """Create the public DOI folder structure matching the DOI URL path."""
        if public_base_path is None:
            # Use configured DOI base path from .env
            public_base_path = Path(self._doi_config.doi_base_path)

        try:
            # Create the public DOI folder structure: {year}/{experiment_id}
            public_doi_path = Path(user_base_path) / public_base_path / str(year) / str(experiment_id)

            if not public_doi_path.exists():
                public_doi_path.mkdir(parents=True, exist_ok=True)
                self._logger.info(f"Created DOI public folder: {public_doi_path}")

            return public_doi_path

        except (PermissionError, OSError) as e:
            message = f"Failed to create DOI public folder for experiment {experiment_id}: {e}"
            self._logger.error(message)
            raise DataManagementError(message, operation="create_doi_public_folder", original_error=e)

    def get_doi_public_path(self, experiment_id: int, year: int, user_base_path: str, public_base_path: Optional[Path] = None) -> Path:
        """Get the path to the DOI public folder."""
        if public_base_path is None:
            # Use configured DOI base path from .env
            public_base_path = Path(user_base_path) / Path(self._doi_config.doi_base_path)

        return public_base_path / str(year) / str(experiment_id)

    def _load_html_template(self) -> str:
        """Load the HTML template from file."""
        template_path = Path(__file__).parent.parent / "templates" / "doi_index.html"

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise DataManagementError(f"HTML template not found: {template_path}", operation="_load_html_template")
        except Exception as e:
            raise DataManagementError(f"Failed to load HTML template: {e}", operation="_load_html_template", original_error=e)

    def generate_doi_index_html(self, experiment_id: int, year: int, doi_id: str, title: str, creators: Optional[str] = None, version: str = "0.1") -> str:
        """Generate HTML content for DOI public folder index page using template."""

        # Load template
        template = self._load_html_template()

        # Format creators list
        authors = creators if creators else "Not specified"

        # No file checking for now - just create basic template
        file_info_rows = ""

        # Always include metadata file row since it's generated with DOI creation
        metadata_api_url = f"https://api.datacite.org/dois/application/vnd.datacite.datacite+json/{doi_id}"
        metadata_file_row = f'''
                <tr>
                    <td>DataCite Metadata</td>
                    <td><a href="{metadata_api_url}">Datacite_Metadata.json</a></td>
                </tr>'''

        # Format the template
        try:
            html_content = template.format(
                title=title,
                publisher="The University of Chicago",
                year=year,
                authors=authors,
                version=version,
                license_url="https://creativecommons.org/licenses/by/4.0/legalcode",
                license_name="CC-BY-4.0",
                file_info_rows=file_info_rows,
                doi_id=doi_id,
                metadata_file_row=metadata_file_row,
                experiment_id=experiment_id,
            )
            return html_content
        except KeyError as e:
            raise DataManagementError(f"Template formatting error - missing variable: {e}", operation="generate_doi_index_html")

    def create_doi_index_file(
        self,
        experiment_id: int,
        year: int,
        doi_id: str,
        title: str,
        user_base_path: str,
        creators: Optional[str] = None,
        version: str = "0.1",
        public_base_path: Optional[Path] = None,
    ) -> bool:
        """Create index.html file in the DOI public folder."""
        try:
            # Get the DOI public folder path
            public_folder_path = self.get_doi_public_path(experiment_id, year, user_base_path, public_base_path)

            # Generate HTML content
            html_content = self.generate_doi_index_html(experiment_id, year, doi_id, title, creators, version)

            # Write index.html file
            index_file_path = public_folder_path / "index.html"

            # Only create if it doesn't exist to avoid overwriting
            if not index_file_path.exists():
                with open(index_file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                self._logger.info(f"Created index.html for DOI: {index_file_path}")
                return True
            else:
                self._logger.info(f"Index.html already exists, skipping: {index_file_path}")
                return False

        except Exception as e:
            message = f"Failed to create index.html for experiment {experiment_id}: {e}"
            self._logger.error(message)
            raise DataManagementError(message, operation="create_doi_index_file", original_error=e)
