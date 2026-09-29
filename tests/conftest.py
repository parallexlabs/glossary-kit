from pathlib import Path

import pytest
from tests.helpers import FIXTURES


@pytest.fixture
def minimal_glossary_path() -> Path:
    return FIXTURES / "minimal_glossary.yaml"


@pytest.fixture
def dictionary_csv_path() -> Path:
    return FIXTURES / "dictionary.csv"


@pytest.fixture
def table_schema_path() -> Path:
    return FIXTURES / "table_schema.yaml"


@pytest.fixture
def sample_glossary_path() -> Path:
    root = Path(__file__).parent.parent
    return root / "examples" / "sample_glossary.yaml"
