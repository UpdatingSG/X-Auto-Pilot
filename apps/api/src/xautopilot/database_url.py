"""Normalize Postgres URLs for asyncpg (Neon, Render, etc.)."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def prepare_asyncpg_url(database_url: str) -> tuple[str, dict]:
    """Return (url, connect_args) for create_async_engine with asyncpg.

    Neon and other hosts often append ``?sslmode=require``. psycopg2 understands
    that query param; asyncpg does not — SSL must be passed via connect_args.
    """
    url = database_url.strip()
    if not url.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
        return url, {}

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=False)

    connect_args: dict = {}
    sslmode = query.pop("sslmode", [None])[0]
    if sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True
    elif sslmode == "prefer":
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False

    # Params meant for libpq/psycopg2 only
    for key in ("channel_binding",):
        query.pop(key, None)

    flat = {k: values[0] for k, values in query.items() if values}
    clean_query = urlencode(flat)
    clean_url = urlunparse(parsed._replace(query=clean_query))
    return clean_url, connect_args
