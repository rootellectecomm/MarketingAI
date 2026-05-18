from app.database.session import normalize_async_database_url


def test_normalizes_plain_postgres_url_to_asyncpg_with_sslmode():
    url, connect_args = normalize_async_database_url("postgresql://user:pass@example.neon.tech/rootellect?sslmode=require")

    assert url.drivername == "postgresql+asyncpg"
    assert "sslmode" not in url.query
    assert connect_args == {"ssl": True}


def test_preserves_asyncpg_url_without_ssl():
    url, connect_args = normalize_async_database_url("postgresql+asyncpg://user:pass@localhost/rootellect")

    assert url.drivername == "postgresql+asyncpg"
    assert connect_args == {}
