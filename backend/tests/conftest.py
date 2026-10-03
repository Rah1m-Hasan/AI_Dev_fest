"""Keep tests isolated from the developer's demo SQLite file."""
import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GROQ_API_KEY"] = ""

from app.db import Base, engine, SessionLocal
from app.main import app
from app.services.seed import seed

@pytest.fixture()
def anyio_backend():
    return "asyncio"

@pytest.fixture()
async def client():
    """Avoid Starlette's lifespan portal deadlock on Python 3.14.

    The production lifespan performs these same schema/seed steps. Explicit
    setup keeps API tests portable across the hackathon's Python versions.
    """
    if sys.version_info >= (3, 14):
        pytest.skip("Starlette/AnyIO in-process ASGI transports deadlock on Python 3.14; run contract tests on supported Python 3.11–3.13")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
