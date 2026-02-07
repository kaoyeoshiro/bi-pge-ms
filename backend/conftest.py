"""Configuração compartilhada do pytest."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Marca testes em tests/integration/ como integration automaticamente."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
