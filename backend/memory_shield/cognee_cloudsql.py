"""Patch Cognee Postgres URLs for Cloud Run unix-socket Cloud SQL.

Cognee builds ``postgresql+asyncpg://user:pass@host:port/db``. Cloud Run mounts
Cloud SQL at ``/cloudsql/INSTANCE`` — the working form is::

    postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/INSTANCE

SPROUT_DATABASE_URL already uses this; graph/vector dataset creation did not.
"""

from __future__ import annotations

import urllib.parse


def _cloudsql_url(username: str, password: str, db_name: str, socket_dir: str) -> str:
    user = urllib.parse.quote_plus(username)
    pw = urllib.parse.quote_plus(password)
    host_q = urllib.parse.quote(socket_dir, safe="/:")
    return f"postgresql+asyncpg://{user}:{pw}@/{db_name}?host={host_q}"


def apply_cloudsql_patches(socket_dir: str) -> None:
    """Monkey-patch Cognee postgres helpers to use unix-socket URLs."""
    from cognee.infrastructure.databases.graph.get_graph_engine import _create_graph_engine
    from cognee.infrastructure.databases.graph.postgres.adapter import PostgresAdapter
    from cognee.infrastructure.databases import postgres as pg_admin_mod

    _orig_engine = _create_graph_engine

    def _patched_create_graph_engine(
        graph_database_provider="",
        graph_database_url: str = "",
        graph_database_username: str = "",
        graph_database_password: str = "",
        graph_database_host: str = "",
        graph_database_port: str = "",
        graph_database_name: str = "",
        **kwargs,
    ):
        if (
            graph_database_provider == "postgres"
            and graph_database_host
            and graph_database_host.startswith("/cloudsql/")
        ):
            if not all([graph_database_username, graph_database_password, graph_database_name]):
                raise EnvironmentError("Missing required Postgres graph credentials.")
            conn = _cloudsql_url(
                graph_database_username,
                graph_database_password,
                graph_database_name,
                graph_database_host,
            )
            return PostgresAdapter(connection_string=conn)
        return _orig_engine(
            graph_database_provider=graph_database_provider,
            graph_database_url=graph_database_url,
            graph_database_username=graph_database_username,
            graph_database_password=graph_database_password,
            graph_database_host=graph_database_host,
            graph_database_port=graph_database_port,
            graph_database_name=graph_database_name,
            **kwargs,
        )

    import cognee.infrastructure.databases.graph.get_graph_engine as ge_mod

    ge_mod._create_graph_engine = _patched_create_graph_engine

    async def _patched_create_pg_database_if_not_exists(
        db_name: str,
        host: str,
        port,
        username: str,
        password: str,
    ) -> bool:
        if host and host.startswith("/cloudsql/"):
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(
                _cloudsql_url(username, password, "postgres", host),
            )
            try:
                connection = await engine.connect()
                try:
                    connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
                    result = await connection.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :db"),
                        {"db": db_name},
                    )
                    if result.scalar():
                        return False
                    await connection.execute(text(f'CREATE DATABASE "{db_name}";'))
                    return True
                finally:
                    await connection.close()
            finally:
                await engine.dispose()
        return await pg_admin_mod.create_pg_database_if_not_exists(
            db_name, host, port, username, password
        )

    async def _patched_drop_pg_database_if_exists(
        db_name: str,
        host: str,
        port,
        username: str,
        password: str,
    ) -> None:
        if host and host.startswith("/cloudsql/"):
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(
                _cloudsql_url(username, password, "postgres", host),
            )
            try:
                connection = await engine.connect()
                try:
                    connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
                    await connection.execute(
                        text(
                            "SELECT pg_terminate_backend(pid) "
                            "FROM pg_stat_activity "
                            "WHERE datname = :db AND pid <> pg_backend_pid()"
                        ),
                        {"db": db_name},
                    )
                    await connection.execute(text(f'DROP DATABASE IF EXISTS "{db_name}";'))
                finally:
                    await connection.close()
            finally:
                await engine.dispose()
            return
        await pg_admin_mod.drop_pg_database_if_exists(db_name, host, port, username, password)

    pg_admin_mod.create_pg_database_if_not_exists = _patched_create_pg_database_if_not_exists
    pg_admin_mod.drop_pg_database_if_exists = _patched_drop_pg_database_if_exists

    # pgvector uses the same host:port URL builder
    import cognee.infrastructure.databases.vector.create_vector_engine as ve_mod
    from cognee.infrastructure.databases.vector.pgvector.PGVectorAdapter import PGVectorAdapter
    from cognee.infrastructure.databases.vector.embeddings import get_embedding_engine

    _orig_vector = ve_mod._create_vector_engine

    def _patched_create_vector_engine(
        vector_db_provider,
        vector_db_url,
        vector_db_key,
        vector_db_name,
        vector_db_username,
        vector_db_password,
        vector_db_host,
        vector_db_port,
        **kwargs,
    ):
        if (
            str(vector_db_provider).lower() == "pgvector"
            and vector_db_host
            and str(vector_db_host).startswith("/cloudsql/")
            and vector_db_username
            and vector_db_password
            and vector_db_name
        ):
            conn = _cloudsql_url(
                vector_db_username, vector_db_password, vector_db_name, vector_db_host
            )
            return PGVectorAdapter(conn, vector_db_key, get_embedding_engine())
        return _orig_vector(
            vector_db_provider,
            vector_db_url,
            vector_db_key,
            vector_db_name,
            vector_db_username,
            vector_db_password,
            vector_db_host,
            vector_db_port,
            **kwargs,
        )

    ve_mod._create_vector_engine = _patched_create_vector_engine
