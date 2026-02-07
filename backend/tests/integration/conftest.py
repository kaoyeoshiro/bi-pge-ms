"""Fixtures para testes de integração com banco de dados real."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings


@pytest_asyncio.fixture
async def db_session():
    """Cria uma sessão async conectada ao banco pge_bi real."""
    engine = create_async_engine(
        settings.async_database_url,
        echo=False,
        pool_size=5,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    await engine.dispose()
