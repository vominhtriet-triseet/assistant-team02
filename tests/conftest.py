from datetime import date

import pytest

from assistant.service import Session

MONDAY = date(2026, 10, 26)


@pytest.fixture
def today() -> date:
    return MONDAY


@pytest.fixture
def session() -> Session:
    return Session()
