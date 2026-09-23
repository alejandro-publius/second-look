"""The MCP tests drive the real API to make records, so they borrow its test client.

Importing the fixture puts it in this folder's namespace; apps/api/tests/conftest.py sets the
environment (a temp database, a temp FHIR store) when it is imported, before the app is."""

from apps.api.tests.conftest import client  # noqa: F401
