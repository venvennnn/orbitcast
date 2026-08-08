"""Postgres helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

import config


def connect() -> psycopg.Connection:
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row)


@contextmanager
def db() -> Iterator[psycopg.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetchone(conn: psycopg.Connection, sql: str, params: tuple | list | None = None) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetchall(conn: psycopg.Connection, sql: str, params: tuple | list | None = None) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def execute(conn: psycopg.Connection, sql: str, params: tuple | list | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
