# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: beamtime_server/services/doi.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module provides a class for creating, updating, publishing and deleting DOIs.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Optional

import requests

from beamtime_server.utils import DOIConfig, get_logger


@dataclass
class DOISchema:
    """A dataclass representing the schema for a DOI that can generate DataCite API payloads."""

    # Required fields
    creators: list[dict[str, Any]]
    titles: list[dict[str, Any]]
    publisher: str
    publication_year: int
    types: dict[str, Any]

    # Semi-required fields (have defaults)
    event: str = "draft"
    doi: Optional[str] = None

    # Optional fields
    alternate_identifiers: Optional[list[dict[str, Any]]] = None
    subjects: Optional[list[dict[str, Any]]] = None
    contributors: Optional[list[dict[str, Any]]] = None
    dates: Optional[list[dict[str, Any]]] = None
    language: Optional[str] = None
    related_identifiers: Optional[list[dict[str, Any]]] = None
    sizes: Optional[list[str]] = None
    formats: Optional[list[str]] = None
    version: Optional[str] = None
    rights_list: Optional[list[dict[str, Any]]] = None
    descriptions: Optional[list[dict[str, Any]]] = None
    geo_locations: Optional[list[dict[str, Any]]] = None
    funding_references: Optional[list[dict[str, Any]]] = None
    url: Optional[str] = None
    content_url: Optional[list[str]] = None

    def to_datacite_payload(self, prefix: str, doi_id: Optional[str] = None) -> dict[str, Any]:
        """Generate a DataCite API payload from this schema."""
        # Build attributes dictionary
        attributes = {
            "event": self.event,
            "prefix": prefix,
            "schemaVersion": "http://datacite.org/schema/kernel-4",
            "creators": self.creators,
            "titles": self.titles,
            "publisher": self.publisher,
            "publicationYear": self.publication_year,
            "types": self.types,
        }

        # Add DOI if provided
        if self.doi:
            attributes["doi"] = self.doi

        # Add optional fields if they have values
        optional_fields = {
            "alternateIdentifiers": self.alternate_identifiers,
            "subjects": self.subjects,
            "contributors": self.contributors,
            "dates": self.dates,
            "language": self.language,
            "relatedIdentifiers": self.related_identifiers,
            "sizes": self.sizes,
            "formats": self.formats,
            "version": self.version,
            "rightsList": self.rights_list,
            "descriptions": self.descriptions,
            "geoLocations": self.geo_locations,
            "fundingReferences": self.funding_references,
            "url": self.url,
            "contentUrl": self.content_url,
        }

        # Only add non-None optional fields
        for key, value in optional_fields.items():
            if value is not None:
                attributes[key] = value

        # Build the data structure
        data = {"type": "dois", "attributes": attributes}

        # Add ID if provided (for updates)
        if doi_id:
            data["id"] = doi_id

        return {"data": data}


class DOIError(Exception):
    """Exception raised for DOI operations."""

    pass


@dataclass
class DOIService:
    """A class for creating, updating, publishing and deleting DOIs using DataCite API."""

    _session: requests.Session | None = field(default=None)
    _config: DOIConfig = field(init=False, compare=False, repr=False, default=DOIConfig())
    _logger: Logger = field(init=False, compare=False, repr=False, default=get_logger())

    def __post_init__(self) -> None:
        """Post-initialization to validate all required environment variables and set up session."""
        # Set up session if not provided
        if self._session is None:
            self._session = requests.Session()

    def create_draft_doi(self, metadata: DOISchema) -> dict:
        """Create a draft DOI with the provided metadata."""
        try:
            url = f"{self._config.base_url}/dois"
            auth = (self._config.username, self._config.password)
            headers = {"Content-Type": "application/vnd.api+json"}
            payload = metadata.to_datacite_payload(prefix=self._config.prefix)

            self._logger.info(f"Creating draft DOI {payload['data']['attributes'].get('doi')}")
            response = self._session.post(url, json=payload, headers=headers, auth=auth)

            if response.status_code == 201:
                doi_data = response.json()
                self._logger.info(f"Successfully created draft DOI: {doi_data['data']['id']}")
                return doi_data
            else:
                error_message = f"Failed to create draft DOI: HTTP {response.status_code} - {response.text}"
                self._logger.error(error_message)
                raise DOIError(error_message)

        except DOIError:
            # Re-raise DOIError as-is
            raise
        except (requests.exceptions.RequestException, ConnectionError) as e:
            message = f"Network error while creating draft DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e
        except Exception as e:
            message = f"Unexpected error while creating draft DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e

    def update_doi(self, doi_id: str, metadata: DOISchema) -> dict:
        """Update an existing DOI with new metadata."""
        try:
            url = f"{self._config.base_url}/dois/{doi_id}"
            auth = (self._config.username, self._config.password)
            headers = {"Content-Type": "application/vnd.api+json"}
            payload = metadata.to_datacite_payload(prefix=self._config.prefix, doi_id=doi_id)

            self._logger.info(f"Updating DOI: {doi_id}")
            response = self._session.put(url, json=payload, headers=headers, auth=auth)

            if response.status_code == 200:
                doi_data = response.json()
                self._logger.info(f"Successfully updated DOI: {doi_data['data']['id']}")
                return doi_data
            else:
                error_message = f"Failed to update DOI: HTTP {response.status_code} - {response.text}"
                self._logger.error(error_message)
                raise DOIError(error_message)

        except DOIError:
            # Re-raise DOIError as-is
            raise
        except (requests.exceptions.RequestException, ConnectionError) as e:
            message = f"Network error while updating DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e
        except Exception as e:
            message = f"Unexpected error while updating DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e

    def delete_doi(self, doi_id: str) -> bool:
        """Delete a draft DOI."""
        try:
            url = f"{self._config.base_url}/dois/{doi_id}"
            auth = (self._config.username, self._config.password)
            headers = {"Content-Type": "application/vnd.api+json"}

            self._logger.info(f"Deleting DOI: {doi_id}")
            response = self._session.delete(url, headers=headers, auth=auth)

            if response.status_code == 204:
                self._logger.info(f"Successfully deleted DOI: {doi_id}")
                return True
            else:
                error_message = f"Failed to delete DOI: HTTP {response.status_code} - {response.text}"
                self._logger.error(error_message)
                raise DOIError(error_message)

        except DOIError:
            # Re-raise DOIError as-is
            raise
        except (requests.exceptions.RequestException, ConnectionError) as e:
            message = f"Network error while deleting DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e
        except Exception as e:
            message = f"Unexpected error while deleting DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e

    def publish_doi(self, doi_id: str) -> dict:
        """Publish a DOI to make it findable (changes state from draft to findable).    DOIError: If the operation fails"""
        try:
            url = f"{self._config.base_url}/dois/{doi_id}"
            auth = (self._config.username, self._config.password)
            headers = {"Content-Type": "application/vnd.api+json"}

            # Create minimal payload with just the event change
            payload = {"data": {"type": "dois", "id": doi_id, "attributes": {"event": "publish"}}}

            self._logger.info(f"Publishing DOI to make it findable: {doi_id}")
            response = self._session.put(url, json=payload, headers=headers, auth=auth)

            if response.status_code == 200:
                doi_data = response.json()
                self._logger.info(f"Successfully published DOI: {doi_data['data']['id']} - now findable")
                return doi_data
            else:
                error_message = f"Failed to publish DOI: HTTP {response.status_code} - {response.text}"
                self._logger.error(error_message)
                raise DOIError(error_message)

        except DOIError:
            # Re-raise DOIError as-is
            raise
        except (requests.exceptions.RequestException, ConnectionError) as e:
            message = f"Network error while publishing DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e
        except Exception as e:
            message = f"Unexpected error while publishing DOI: {e}"
            self._logger.error(message)
            raise DOIError(message) from e

    def get_doi_status(self, doi_id: str) -> dict:
        """Get the current status/state of a DOI."""
        try:
            url = f"{self._config.base_url}/dois/{doi_id}"
            auth = (self._config.username, self._config.password)
            headers = {"Content-Type": "application/vnd.api+json"}

            self._logger.debug(f"Checking status of DOI: {doi_id}")
            response = self._session.get(url, headers=headers, auth=auth)

            if response.status_code == 200:
                doi_data = response.json()
                state = doi_data.get("data", {}).get("attributes", {}).get("state", "unknown")
                self._logger.debug(f"DOI {doi_id} current state: {state}")
                return doi_data
            else:
                error_message = f"Failed to get DOI status: HTTP {response.status_code} - {response.text}"
                self._logger.error(error_message)
                raise DOIError(error_message)

        except DOIError:
            # Re-raise DOIError as-is
            raise
        except (requests.exceptions.RequestException, ConnectionError) as e:
            message = f"Network error while getting DOI status: {e}"
            self._logger.error(message)
            raise DOIError(message) from e
        except Exception as e:
            message = f"Unexpected error while getting DOI status: {e}"
            self._logger.error(message)
            raise DOIError(message) from e

    def create_or_update_doi(self, metadata: DOISchema) -> dict:
        """Create a new DOI or update existing one if it already exists."""
        try:
            # First try to create the DOI
            return self.create_draft_doi(metadata)

        except DOIError as e:
            # Check if error is about DOI already existing (HTTP 422)
            if "422" in str(e) and "already been taken" in str(e):
                self._logger.info(f"DOI {metadata.doi} already exists, updating instead of creating")
                # Extract DOI ID from metadata
                doi_id = metadata.doi
                if not doi_id:
                    raise DOIError("Cannot update DOI: no DOI ID provided in metadata")

                # Update the existing DOI
                return self.update_doi(doi_id, metadata)
            else:
                # Re-raise other DOIErrors
                raise
