# Beamtime Server Tests

This directory contains pytest-based tests for the Beamtime-Server codebase and is structured as a Python package.

## Structure

- `__init__.py` - Package initialization, shared test utilities, and test runner
- `test_doi.py` - Tests the DOI draft creation, update and deletion

## Running Tests

To run all tests using the PDS CLI:
```bash
python BeamtimeServer.py -t
```

To run all tests using pytest directly:
```bash
pytest tests/
```

To run with verbose output:
```bash
pytest -v tests/
```

To run specific test files:
```bash
pytest tests/test_doi.py
```

## General Test Information

The test suite provides general coverage of the Beamtime-Server modules. Tests validate the core functionality of the modules.