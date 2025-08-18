# ----------------------------------------------------------------------------------
# Project: Beamtime-Server
# File: test_doi.py
# ----------------------------------------------------------------------------------
# Purpose:
# This module provides tests for the DOI service functionality.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (c) 2025 GSECARS, The University of Chicago, USA
# Copyright (c) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import logging
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from beamtime_server.services.doi import DOIError, DOIService, DOISchema
from beamtime_server.utils.config import DOIConfig


class TestDOIService:
    """Test cases for DOI service functionality."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def doi_service(self, mock_logger):
        """Create a DOI service instance using DOI config."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
            return DOIService(logger=mock_logger, config=config)
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for DOI creation."""
        return DOISchema(
            titles=[{"title": "Test Experiment Dataset"}],
            creators=[{"name": "Doe, John", "nameType": "Personal"}],
            publisher="GSECARS",
            publication_year=2025,
            types={"resourceTypeGeneral": "Dataset"},
        )

    def test_doi_service_initialization_success(self, mock_logger):
        """Test successful DOI service initialization with DOI config."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")

            service = DOIService(logger=mock_logger, config=config)
            assert service.config.username == config.username
            assert service.config.password == config.password
            assert service.config.base_url == config.base_url
            assert service.config.prefix == config.prefix
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

    def test_doi_service_initialization_missing_base_url(self, mock_logger):
        """Test DOI service initialization with missing DOI_BASE_URL."""
        with patch.dict(os.environ, {"DOI_BASE_URL": ""}, clear=False):
            with pytest.raises((ValueError, FileNotFoundError)):
                config = DOIConfig()
                DOIService(logger=mock_logger, config=config)

    def test_doi_service_initialization_missing_username(self, mock_logger):
        """Test DOI service initialization with missing DOI_USERNAME."""
        with patch.dict(os.environ, {"DOI_USERNAME": ""}, clear=False):
            with pytest.raises((ValueError, FileNotFoundError)):
                config = DOIConfig()
                DOIService(logger=mock_logger, config=config)

    def test_doi_service_initialization_missing_password(self, mock_logger):
        """Test DOI service initialization with missing DOI_PASSWORD."""
        with patch.dict(os.environ, {"DOI_PASSWORD": ""}, clear=False):
            with pytest.raises((ValueError, FileNotFoundError)):
                config = DOIConfig()
                DOIService(logger=mock_logger, config=config)

    def test_doi_service_initialization_missing_prefix(self, mock_logger):
        """Test DOI service initialization with missing DOI_PREFIX."""
        with patch.dict(os.environ, {"DOI_PREFIX": ""}, clear=False):
            with pytest.raises((ValueError, FileNotFoundError)):
                config = DOIConfig()
                DOIService(logger=mock_logger, config=config)

    def test_create_draft_doi_success(self, mock_logger, sample_metadata):
        """Test successful draft DOI creation."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        test_doi_id = f"{config.prefix}/test-doi-123"

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"id": test_doi_id, "type": "dois", "attributes": {"doi": test_doi_id}}}
        mock_session.post.return_value = mock_response

        result = service.create_draft_doi(sample_metadata)

        # Verify the result
        assert result["data"]["id"] == test_doi_id

        # Verify the API call was made
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args

        # Verify URL
        assert call_args[0][0] == f"{service.config.base_url}/dois"

        # Verify auth and headers
        assert call_args[1]["auth"] == (service.config.username, service.config.password.get_secret_value())
        assert call_args[1]["headers"]["Content-Type"] == "application/vnd.api+json"

        # Verify payload structure
        payload = call_args[1]["json"]
        assert payload["data"]["type"] == "dois"
        assert payload["data"]["attributes"]["event"] == "draft"
        assert payload["data"]["attributes"]["titles"] == sample_metadata.titles

    def test_create_draft_doi_api_error(self, mock_logger, sample_metadata):
        """Test draft DOI creation with API error."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_session.post.return_value = mock_response

        with pytest.raises(DOIError, match="Failed to create draft DOI: HTTP 400"):
            service.create_draft_doi(sample_metadata)

    def test_create_draft_doi_network_error(self, mock_logger, sample_metadata):
        """Test draft DOI creation with network error."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock network error
        mock_session.post.side_effect = ConnectionError("Network error")

        with pytest.raises(DOIError, match="Network error while creating draft DOI"):
            service.create_draft_doi(sample_metadata)

    def test_update_doi_success(self, mock_logger, sample_metadata):
        """Test successful DOI update."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        test_doi_id = f"{config.prefix}/test-doi-123"

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": test_doi_id, "type": "dois", "attributes": {"doi": test_doi_id}}}
        mock_session.put.return_value = mock_response

        result = service.update_doi(test_doi_id, sample_metadata)

        # Verify the result
        assert result["data"]["id"] == test_doi_id

        # Verify the API call was made
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args

        # Verify URL
        assert call_args[0][0] == f"{service.config.base_url}/dois/{test_doi_id}"

        # Verify auth and headers
        assert call_args[1]["auth"] == (service.config.username, service.config.password.get_secret_value())
        assert call_args[1]["headers"]["Content-Type"] == "application/vnd.api+json"

        # Verify payload structure
        payload = call_args[1]["json"]
        assert payload["data"]["type"] == "dois"
        assert payload["data"]["id"] == test_doi_id
        assert payload["data"]["attributes"]["titles"] == sample_metadata.titles

    def test_update_doi_api_error(self, mock_logger, sample_metadata):
        """Test DOI update with API error."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        test_doi_id = f"{config.prefix}/test-doi-123"

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "DOI not found"
        mock_session.put.return_value = mock_response

        with pytest.raises(DOIError, match="Failed to update DOI: HTTP 404"):
            service.update_doi(test_doi_id, sample_metadata)

    def test_update_doi_network_error(self, mock_logger, sample_metadata):
        """Test DOI update with network error."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        test_doi_id = f"{config.prefix}/test-doi-123"

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock network error
        mock_session.put.side_effect = ConnectionError("Network error")

        with pytest.raises(DOIError, match="Network error while updating DOI"):
            service.update_doi(test_doi_id, sample_metadata)

    def test_delete_doi_success(self, mock_logger):
        """Test successful DOI deletion."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        test_doi_id = f"{config.prefix}/test-doi-123"

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock successful response (204 No Content)
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_session.delete.return_value = mock_response

        result = service.delete_doi(test_doi_id)

        # Verify the result
        assert result is True

        # Verify the API call was made
        mock_session.delete.assert_called_once()
        call_args = mock_session.delete.call_args

        # Verify URL
        assert call_args[0][0] == f"{service.config.base_url}/dois/{test_doi_id}"

        # Verify auth and headers
        assert call_args[1]["auth"] == (service.config.username, service.config.password.get_secret_value())
        assert call_args[1]["headers"]["Content-Type"] == "application/vnd.api+json"

    def test_delete_doi_api_error(self, mock_logger):
        """Test DOI deletion with API error."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        test_doi_id = f"{config.prefix}/test-doi-123"

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "DOI not found"
        mock_session.delete.return_value = mock_response

        with pytest.raises(DOIError, match="Failed to delete DOI: HTTP 404"):
            service.delete_doi(test_doi_id)

    def test_delete_doi_network_error(self, mock_logger):
        """Test DOI deletion with network error."""
        try:
            config = DOIConfig()
            if not all([config.base_url, config.username, config.password, config.prefix]):
                pytest.skip("DOI environment variables not configured")
        except (FileNotFoundError, ValueError):
            pytest.skip("DOI configuration not available")

        test_doi_id = f"{config.prefix}/test-doi-123"

        mock_session = MagicMock()
        service = DOIService(config=config, logger=mock_logger, session=mock_session)

        # Mock network error
        mock_session.delete.side_effect = ConnectionError("Network error")

        with pytest.raises(DOIError, match="Network error while deleting DOI"):
            service.delete_doi(test_doi_id)

    def test_doi_integration_create_update_delete(self, doi_service, sample_metadata):
        """Integration test: Create, update, and delete a DOI with delays for manual verification."""
        created_doi_id = None
        try:
            # 1. Create a draft DOI
            create_result = doi_service.create_draft_doi(sample_metadata)
            created_doi_id = create_result["data"]["id"]
            assert created_doi_id is not None

            # Wait 30 seconds for manual verification
            time.sleep(30)

            # 2. Update the same DOI
            updated_metadata = DOISchema(
                titles=[{"title": "Updated Test Dataset (CHANGED)"}],
                creators=sample_metadata.creators,
                publisher=sample_metadata.publisher,
                publication_year=sample_metadata.publication_year,
                types=sample_metadata.types,
            )
            update_result = doi_service.update_doi(created_doi_id, updated_metadata)
            assert update_result["data"]["id"] == created_doi_id
            assert update_result["data"]["attributes"]["titles"][0]["title"] == "Updated Test Dataset (CHANGED)"

            # Wait another 30 seconds for manual verification
            time.sleep(30)

            # 3. Delete the same DOI
            delete_result = doi_service.delete_doi(created_doi_id)
            assert delete_result is True
            created_doi_id = None

        except Exception as e:
            pytest.fail(f"DOI integration test failed: {e}")
        finally:
            # Cleanup: ensure DOI is deleted even if test fails
            if created_doi_id:
                try:
                    doi_service.delete_doi(created_doi_id)
                except DOIError:
                    pass  # Ignore cleanup errors

    def test_doi_integration_create_and_delete_only(self, doi_service, sample_metadata):
        """Integration test: Create and delete a DOI (simpler lifecycle)."""
        created_doi_id = None
        try:
            # Create a draft DOI
            create_result = doi_service.create_draft_doi(sample_metadata)
            created_doi_id = create_result["data"]["id"]
            assert created_doi_id is not None

            # Delete the DOI immediately
            delete_result = doi_service.delete_doi(created_doi_id)
            assert delete_result is True

            # Mark as successfully deleted
            created_doi_id = None

        except Exception as e:
            pytest.fail(f"Create-delete integration test failed: {e}")
        finally:
            # Cleanup
            if created_doi_id:
                try:
                    doi_service.delete_doi(created_doi_id)
                except DOIError:
                    pass
