"""Shared test fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_yaml() -> Path:
    return FIXTURES_DIR / "sample_domain.yaml"


@pytest.fixture
def sample_csv() -> Path:
    return FIXTURES_DIR / "sample_entities.csv"


@pytest.fixture
def sample_links_csv() -> Path:
    return FIXTURES_DIR / "sample_links.csv"
